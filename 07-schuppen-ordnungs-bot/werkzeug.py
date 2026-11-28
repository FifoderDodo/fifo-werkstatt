def neuer_tag(daten):
    """
    Entscheidungslogik für einen neuen Tag im Schuppen.
    Nimmt Status-Dict, gibt Plan-Dict zurück.
    Zwei-Runden-KI: Erst fragen, dann mit Rat entscheiden.
    """
    try:
        gestern = daten.get("gestern", {})
        fehlschlaege = daten.get("fehlschlaege", {})
        stimmung = int(daten.get("stimmung", 0))
        wetter = str(daten.get("wetter", "bewoelkt")).lower()
        kakerlaken_level = int(daten.get("kakerlaken_level", 0))
    except (ValueError, TypeError) as e:
        return {"notiz": f"Fehlerhafte Eingabedaten: {e}", "plan": []}

    # 1. Hartes Sicherheitslimit: Kakerlaken-Plage -> Sofort-Aktion, keine KI-Frage
    if kakerlaken_level >= 7:
        notiz = "Achtung: Starke Kakerlaken-Aktivität! Erst Abwehr, dann Sortieren."
        plan = [
            {"aktion": "walk_to", "text": "Giftschrank holen: Sprühgift & Köder"},
            {"aktion": "nachsehen", "text": "Ecken, Kartons & Ritzen absprühen"},
            {"aktion": "spazieren", "text": "Lüften & Kopf freibekommen nach Gift"}
        ]
        return {"notiz": notiz[:200], "plan": plan[:3]}

    # 2. Runde 1: KI fragen, wenn noch keine Antwort da
    if "ki_antwort" not in daten:
        prompt = (
            f"Status: Stimmung {stimmung}, Wetter {wetter}, Kakerlaken-Level {kakerlaken_level}. "
            f"Gestern: {gestern}. Fehlschläge: {fehlschlaege}. "
            f"Erlaubte Aktionen: think, eat, drink, walk_to, sitzen, spazieren, "
            f"schrott_suchen, aufheben, verkaufen, einlagern, malen, komponieren, "
            f"read_news, muenze_werfen, nachsehen, am_projekt_arbeiten. "
            f"Antworte NUR mit Plan-Zeilen im Format: 'AKTION: text'. Max 3 Zeilen. "
            f"Beispiel: 'think: Sortierlogik verfeinern | eat: Frühstück | spazieren: Luft schnappen'"
        )
        return {"frage_an_ki": prompt[:1500]}

    # 3. Runde 2: KI-Antwort auswerten
    rat = daten.get("ki_antwort", "").strip()
    notiz = ""
    plan = []

    if rat:
        # Einfaches Parsen: 'aktion: text | aktion: text'
        try:
            teile = [t.strip() for t in rat.split('|')]
            for teil in teile[:3]:
                if ':' in teil:
                    akt, txt = teil.split(':', 1)
                    akt = akt.strip().lower()
                    txt = txt.strip()
                    # Validierung gegen erlaubte Aktionen
                    erlaubte = {"think", "eat", "drink", "walk_to", "sitzen", "spazieren",
                                "schrott_suchen", "aufheben", "verkaufen", "einlagern",
                                "malen", "komponieren", "read_news", "muenze_werfen",
                                "nachsehen", "am_projekt_arbeiten"}
                    if akt in erlaubte and txt:
                        plan.append({"aktion": akt, "text": txt[:100]})
        except Exception:
            pass  # Parsing fehlgeschlagen, Fallback unten

    # Fallback, falls KI nix Brauchbares lieferte oder Limit erreicht
    if not plan:
        notiz = "KI schweigt oder Format unklar. Fallback: Klein anfangen."
        if stimmung < -50:
            plan.append({"aktion": "spazieren", "text": "Kopf freibekommen vor dem Schuppen"})
        elif stimmung < 20:
            plan.append({"aktion": "drink", "text": "Wasser oder Kaffee trinken"})
        else:
            plan.append({"aktion": "think", "text": "Heutigen Schrott-Schwerpunkt festlegen"})
        if len(plan) < 2:
            plan.append({"aktion": "eat", "text": "Frühstück machen"})
        if len(plan) < 3 and wetter in ["sonnig", "heiter"]:
            plan.append({"aktion": "spazieren", "text": "Gutes Wetter nutzen, kurz raus"})
    else:
        notiz = f"KI-Plan: {rat[:150]}"

    # Kakerlaken-Warnung (Level 4-6) in Notiz aufnehmen, wenn nicht schon im Plan
    if 4 <= kakerlaken_level < 7 and not any(p["aktion"] == "nachsehen" for p in plan):
        notiz = (notiz + " | " if notiz else "") + "Kakerlaken verdächtig, Augen auf."

    return {
        "notiz": notiz[:200],
        "plan": plan[:3]
    }


import json
import os
import re
from typing import Any, Dict, List


def validiere_dateipfad(pfad: str, basis_verzeichnis: str = ".") -> str:
    """
    Prüft Pfad auf Directory Traversal und normalisiert ihn.
    Gibt absoluten Pfad zurück, wenn er sicher unter basis_verzeichnis liegt.
    Wirft ValueError bei Unsicherheit.
    """
    try:
        if not pfad or not isinstance(pfad, str):
            raise ValueError("Pfad leer oder ungültig")
        abs_basis = os.path.abspath(basis_verzeichnis)
        abs_ziel = os.path.abspath(os.path.join(abs_basis, pfad))
        if not abs_ziel.startswith(abs_basis):
            raise ValueError(f"Pfad führt aus Basis raus: {pfad}")
        if re.search(r'[\x00-\x1f]', pfad):
            raise ValueError("Steuerzeichen im Pfad")
        return abs_ziel
    except Exception as e:
        raise ValueError(f"Pfadvalidierung fehlgeschlagen: {e}") from e


def _json_sicher(obj: Any) -> Any:
    """Rekursiver Helfer: macht Objekte JSON-sicher (Standardbibliothek only)."""
    try:
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        if isinstance(obj, dict):
            return {str(k): _json_sicher(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [_json_sicher(v) for v in obj]
        return str(obj)
    except Exception:
        return "<nicht serialisierbar>"


class MetallSortierer:
    """
    Metall-Sortierlogik für den Schuppen-Bot.
    Nimmt Liste von Schrott-Teilen (Dicts), sortiert in Kategorien.
    Liefert JSON-sicheres Ergebnis-Dict.
    """
    # Grobe Dichten in g/cm³ für Schätzung
    DICHTEN = {
        "aluminium": 2.7, "aluminiumlegierung": 2.7,
        "magnesium": 1.74,
        "titan": 4.5,
        "stahl": 7.85, "eisen": 7.87, "guss": 7.2, "ferro": 7.8,
        "edelstahl": 7.9,
        "kupfer": 8.96, "messing": 8.5, "bronze": 8.8,
        "blei": 11.34, "bleilegierung": 11.0,
        "zink": 7.13, "zinklegierung": 7.0,
        "zinn": 7.31,
        "nickel": 8.9,
        "kabel_kupfer": 8.9, "kabel_aluminium": 2.7,
        "batterie_blei": 11.0, "batterie_liion": 2.5,
        "gemischt": 7.0
    }

    # Kategorien für Ausgabe
    KATEGORIEN = [
        "NE_Metall_hochwertig",  # Cu, Messing, Alu, Kabel
        "NE_Metall_sonstiges",   # Zn, Sn, Ni, Mg, Ti
        "FE_Metall",             # Stahl, Eisen, Guss, Edelstahl
        "Sondermuell",           # Blei, Batterien, Quecksilber
        "Unbekannt"
    ]

    @classmethod
    def _rate_metall_typ(cls, teil: Dict) -> str:
        """Heuristik: Errate Metall-Typ aus Namen, Beschreibung, Dichte."""
        name = str(teil.get("name", "")).lower()
        beschreibung = str(teil.get("beschreibung", "")).lower()
        text = f"{name} {beschreibung}"

        # Explizite Schlüsselwörter
        if any(w in text for w in ["kupfer", "cu", "kabel", "leitung", "draht", "rohr"]):
            if "aluminium" in text or "alu" in text:
                return "kabel_aluminium"
            return "kupfer"
        if any(w in text for w in ["messing", "ms", "messingdraht"]):
            return "messing"
        if any(w in text for w in ["bronze", "bronzelegierung"]):
            return "bronze"
        if any(w in text for w in ["aluminium", "alu", "aluguss", "profil", "felge"]):
            return "aluminium"
        if any(w in text for w in ["edelstahl", "v2a", "v4a", "rostfrei", "niro"]):
            return "edelstahl"
        if any(w in text for w in ["stahl", "eisen", "fe", "guss", "schraube", "nagel", "blech", "träger", "welle"]):
            return "stahl"
        if any(w in text for w in ["blei", "pb", "batterie", "akku", "bleiakku", "strahlenschutz"]):
            return "blei"
        if any(w in text for w in ["zink", "zn", "zinkdruckguss", "druckguss"]):
            return "zink"
        if any(w in text for w in ["zinn", "sn", "lot"]):
            return "zinn"
        if any(w in text for w in ["nickel", "ni"]):
            return "nickel"
        if any(w in text for w in ["magnesium", "mg", "magnesiumlegierung"]):
            return "magnesium"
        if any(w in text for w in ["titan", "ti"]):
            return "titan"

        # Dichte-Schätzung falls Gewicht & Volumen da
        gewicht = teil.get("gewicht_g")
        volumen = teil.get("volumen_cm3")
        if isinstance(gewicht, (int, float)) and isinstance(volumen, (int, float)) and volumen > 0:
            dichte = gewicht / volumen
            # Nächste Dichte finden
            beste = min(cls.DICHTEN.items(), key=lambda kv: abs(kv[1] - dichte))
            if abs(beste[1] - dichte) < 1.5:  # Toleranz
                return beste[0]

        return "gemischt"

    @classmethod
    def _kategorie_fuer_typ(cls, typ: str) -> str:
        """Ordnet internen Typ Hauptkategorie zu."""
        if typ in {"kupfer", "messing", "bronze", "aluminium", "kabel_kupfer", "kabel_aluminium"}:
            return "NE_Metall_hochwertig"
        if typ in {"zink", "zinn", "nickel", "magnesium", "titan", "zinklegierung"}:
            return "NE_Metall_sonstiges"
        if typ in {"stahl", "eisen", "guss", "edelstahl", "ferro"}:
            return "FE_Metall"
        if typ in {"blei", "bleilegierung", "batterie_blei", "batterie_liion"}:
            return "Sondermuell"
        return "Unbekannt"

    @classmethod
    def sortieren(cls, teile: List[Dict]) -> Dict:
        """
        Hauptmethode: Sortiert Liste von Teilen in Kategorien.
        Rückgabe: Dict mit Kategorien als Keys, Listen von Teilen als Values.
        Jedes Teil bekommt Feld '_metall_typ' und '_kategorie'.
        """
        ergebnis = {kat: [] for kat in cls.KATEGORIEN}
        statistik = {kat: 0 for kat in cls.KATEGORIEN}
        statistik["gesamt"] = len(teile)

        for teil in teile:
            if not isinstance(teil, dict):
                continue
            typ = cls._rate_metall_typ(teil)
            kat = cls._kategorie_fuer_typ(typ)
            angereichert = dict(teil)  # Kopie
            angereichert["_metall_typ"] = typ
            angereichert["_kategorie"] = kat
            ergebnis[kat].append(angereichert)
            statistik[kat] += 1

        return _json_sicher({
            "sortiert": ergebnis,
            "statistik": statistik
        })


if __name__ == "__main__":
    # Selbsttest für neuer_tag
    print("=== Test neuer_tag ===")
    test_faelle = [
        {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen": 2}, "stimmung": 10, "wetter": "sonnig"},
        {"gestern": {}, "fehlschlaege": {}, "stimmung": 30, "wetter": ""},
        {"gestern": {"spazieren": 1}, "fehlschlaege": {}, "stimmung": -60, "wetter": "regen", "kakerlaken_level": 2},
        {"gestern": {}, "fehlschlaege": {}, "stimmung": 0, "wetter": "bewoelkt", "kakerlaken_level": 8},
    ]
    for i, daten in enumerate(test_faelle, 1):
        print(f"\n--- Fall {i} ---")
        print(f"Input: {json.dumps(daten, ensure_ascii=False)}")
        # Runde 1
        r1 = neuer_tag(daten)
        print(f"Runde 1: {json.dumps(r1, ensure_ascii=False)}")
        # Simuliere KI-Antwort (nur für Demo)
        if "frage_an_ki" in r1:
            fake_ki = "think: Plan machen | eat: Brot essen | spazieren: Kurz raus"
            daten_mit_ki = dict(daten)
            daten_mit_ki["ki_antwort"] = fake_ki
            r2 = neuer_tag(daten_mit_ki)
            print(f"Runde 2 (mit Fake-KI): {json.dumps(r2, ensure_ascii=False)}")
        else:
            print("Keine KI-Frage (Sofort-Plan oder Fehler).")

    # Selbsttest für MetallSortierer
    print("\n=== Test MetallSortierer ===")
    test_stuecke = [
        {"name": "Kupferrohr", "gewicht_g": 896, "volumen_cm3": 100},
        {"name": "Alu-Felge", "gewicht_g": 2700, "volumen_cm3": 1000},
        {"name": "Stahlschrauben", "beschreibung": "Karton voll Eisen Schrauben M8"},
        {"name": "Messinghahn", "gewicht_g": 850, "volumen_cm3": 100},
        {"name": "Bleiakkumulator", "beschreibung": "Auto-Batterie alt"},
        {"name": "Zinkdruckguss", "gewicht_g": 713, "volumen_cm3": 100},
        {"name": "Edelstahlrohr V2A", "gewicht_g": 790, "volumen_cm3": 100},
        {"name": "Kupferkabel dick", "beschreibung": "Erdkabel 16mm2"},
        {"name": "Unbekanntes Teil", "gewicht_g": 500, "volumen_cm3": 100},
        {"name": "Alu-Kabel", "beschreibung": "Freileitung Al/St"},
    ]
    ergebnis = MetallSortierer.sortieren(test_stuecke)
    print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
    print("\nTests durchgelaufen.")