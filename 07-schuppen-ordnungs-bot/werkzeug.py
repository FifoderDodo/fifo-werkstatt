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
        "blei": 11.34,
        "zink": 7.13,
        "nickel": 8.9,
        "zinn": 7.31,
        "gold": 19.3,
        "silber": 10.49,
        "platin": 21.45
    }

    @staticmethod
    def _rate_metall_typ(stueck: Dict) -> str:
        """Heuristik: Rät Metall-Typ basierend auf Dichte, Magnetismus, Farbe, Beschriftung."""
        # 1. Explizite Beschriftung prüfen
        label = str(stueck.get("label", "")).lower()
        for known in MetallSortierer.DICHTEN:
            if known in label:
                return known
        
        # 2. Dichte berechnen, falls Gewicht & Volumen da
        gewicht = stueck.get("gewicht_g")
        volumen = stueck.get("volumen_cm3")
        if gewicht and volumen and volumen > 0:
            dichte = float(gewicht) / float(volumen)
            # Nächsten bekannten Nachbarn suchen
            best_match = min(MetallSortierer.DICHTEN.items(), key=lambda kv: abs(kv[1] - dichte))
            if abs(best_match[1] - dichte) < 1.5:  # Toleranz 1.5 g/cm³
                return best_match[0]
        
        # 3. Magnetismus & Farbe als grobe Filter
        magnetisch = bool(stueck.get("magnetisch", False))
        farbe = str(stueck.get("farbe", "")).lower()
        
        if magnetisch:
            if "rost" in farbe or "braun" in farbe:
                return "eisen"
            return "stahl"  # Default ferromagnetisch
        else:
            if "rot" in farbe or "orange" in farbe or "kupfer" in farbe:
                return "kupfer"
            if "gelb" in farbe or "gold" in farbe:
                return "messing"
            if "weiß" in farbe or "silber" in farbe or "hell" in farbe:
                if stueck.get("gewicht_g", 0) < 100 and stueck.get("volumen_cm3", 1) > 20:
                    return "aluminium"  # Leicht & groß
                return "edelstahl"
            if "grau" in farbe or "dunkel" in farbe:
                return "zink"  # Oft Zinkdruckguss
        
        return "unbekannt"

    @classmethod
    def sortieren(cls, schrott_liste: List[Dict]) -> Dict:
        """Hauptmethode: Sortiert Liste in Kategorien, zählt, summiert Gewicht."""
        kategorien = {}
        gesamt_gewicht = 0.0
        
        for stueck in schrott_liste:
            if not isinstance(stueck, dict):
                continue
            typ = cls._rate_metall_typ(stueck)
            gewicht = float(stueck.get("gewicht_g", 0) or 0)
            
            if typ not in kategorien:
                kategorien[typ] = {"anzahl": 0, "gewicht_g": 0.0, "stuecke": []}
            
            kategorien[typ]["anzahl"] += 1
            kategorien[typ]["gewicht_g"] += gewicht
            kategorien[typ]["stuecke"].append(_json_sicher(stueck))
            gesamt_gewicht += gewicht
        
        # Aufbereiten für Ausgabe
        ergebnis = {
            "kategorien": _json_sicher(kategorien),
            "gesamt_stuecke": len(schrott_liste),
            "gesamt_gewicht_g": round(gesamt_gewicht, 2),
            "sortierzeit": "gerade eben"
        }
        return _json_sicher(ergebnis)


if __name__ == "__main__":
    # Selbsttest: neuer_tag
    print("=== Test neuer_tag ===")
    test_faelle = [
        {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen": 2}, "stimmung": 10, "wetter": "sonnig"},
        {"gestern": {}, "fehlschlaege": {}, "stimmung": -60, "wetter": "regen", "kakerlaken_level": 8},
        {"gestern": {"spazieren": 1}, "fehlschlaege": {},"stimmung": 50, "wetter": "bewoelkt", "ki_antwort": "think: Plan machen | eat: Brot | spazieren: Runde drehen"},
        {"gestern": {},"fehlschlaege": {},"stimmung": 5, "wetter": "nebel", "ki_antwort": ""},
    ]
    for i, daten in enumerate(test_faelle):
        out = neuer_tag(daten)
        print(f"Test {i+1}: {json.dumps(out, ensure_ascii=False)}")
        # Simuliere 2. Runde falls Frage kam
        if "frage_an_ki" in out:
            print(f"  -> Frage: {out['frage_an_ki'][:80]}...")
            daten2 = {**daten, "ki_antwort": "think: sortieren | walk_to: schuppen | schrott_suchen: metalle"}
            out2 = neuer_tag(daten2)
            print(f"  -> Antwort: {json.dumps(out2, ensure_ascii=False)}")

    # Selbsttest: MetallSortierer
    print("\n=== Test MetallSortierer ===")
    test_stuecke = [
        {"label": "Alu-Profil 1m", "gewicht_g": 810, "volumen_cm3": 300, "farbe": "silber", "magnetisch": False},
        {"label": "Eisenstab dick", "gewicht_g": 2500, "volumen_cm3": 318, "farbe": "rostbraun", "magnetisch": True},
        {"label": "Kupferrohr Rest", "gewicht_g": 450, "volumen_cm3": 50, "farbe": "rotgold", "magnetisch": False},
        {"label": "Messing-Ventil", "gewicht_g": 320, "volumen_cm3": 38, "farbe": "gelb", "magnetisch": False},
        {"label": "Edelstahl-Schrauben", "gewicht_g": 150, "volumen_cm3": 19, "farbe": "silber", "magnetisch": False},
        {"label": "Zink-Druckguss-Eck", "gewicht_g": 210, "volumen_cm3": 30, "farbe": "grau", "magnetisch": False},
        {"label": "Blei-Gewicht", "gewicht_g": 1134, "volumen_cm3": 100, "farbe": "blaugrau", "magnetisch": False},
        {"label": "Alte Dose", "gewicht_g": 30, "volumen_cm3": 40, "farbe": "weiss", "magnetisch": True},
        {"label": "Magnetischer Block", "gewicht_g": 500, "volumen_cm3": 65, "farbe": "schwarz", "magnetisch": True},
        {"label": "Mystery-Stück", "gewicht_g": 100, "volumen_cm3": 20, "farbe": "bunt", "magnetisch": False},
    ]
    sorter = MetallSortierer()
    ergebnis = sorter.sortieren(test_stuecke)
    print(json.dumps(ergebnis, indent=2, ensure_ascii=False))
    print(f"\nKategorien gefunden: {list(ergebnis['kategorien'].keys())}")
    print(f"Gesamt: {ergebnis['gesamt_stuecke']} Stücke, {ergebnis['gesamt_gewicht_g']}g")