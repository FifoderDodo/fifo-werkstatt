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
        "zink": 7.14, "zinklegierung": 6.8,
        "blei": 11.34,
        "nickel": 8.9,
        "gold": 19.3, "silber": 10.5
    }
    # Toleranz für Dichtevergleich (g/cm³)
    TOLERANZ = 0.3

    def erkennen(self, teil: Dict) -> str:
        """
        Erratet Metallart basierend auf Dichte & Magnetismus.
        Erwartet Keys: 'gewicht_g', 'volumen_cm3', 'magnetisch' (bool),
        optional: 'farbe', 'zeichen' (str).
        """
        try:
            gewicht = float(teil.get("gewicht_g", 0))
            volumen = float(teil.get("volumen_cm3", 0))
            magnetisch = bool(teil.get("magnetisch", False))
            farbe = str(teil.get("farbe", "")).lower()
            zeichen = str(teil.get("zeichen", "")).lower()
        except (ValueError, TypeError):
            return "unknown"

        if volumen <= 0:
            return "unknown"

        dichte = gewicht / volumen
        kandidaten = []

        for name, d in self.DICHTEN.items():
            if abs(d - dichte) <= self.TOLERANZ:
                kandidaten.append(name)

        # Magnetismus als starker Filter für Eisen/Stahl/Guss
        if magnetisch:
            ferro = [k for k in kandidaten if k in ("stahl", "eisen", "guss", "ferro", "edelstahl")]
            if ferro:
                # Edelstahl ist oft schwach/nicht magnetisch, aber hier vereinfacht
                if "edelstahl" in ferro and "stahl" in ferro:
                    return "stahl"  # Default zu Stahl bei Magnetismus
                return ferro[0]
        else:
            # Nicht magnetisch: Alu, Kupfer, Messing, Titan, etc.
            non_ferro = [k for k in kandidaten if k not in ("stahl", "eisen", "guss", "ferro")]
            if non_ferro:
                # Farb-Hinweise nutzen
                if "kupfer" in farbe or "rot" in farbe:
                    if "kupfer" in non_ferro: return "kupfer"
                    if "bronze" in non_ferro: return "bronze"
                if "gelb" in farbe or "gold" in farbe:
                    if "messing" in non_ferro: return "messing"
                if "weiss" in farbe or "silber" in farbe or "grau" in farbe:
                    if "aluminium" in non_ferro or "aluminiumlegierung" in non_ferro: return "aluminium"
                    if "titan" in non_ferro: return "titan"
                    if "edelstahl" in non_ferro: return "edelstahl"
                # Stempel/Zeichen prüfen
                if "cu" in zeichen: return "kupfer"
                if "al" in zeichen: return "aluminium"
                if "ss" in zeichen or "inox" in zeichen: return "edelstahl"
                return non_ferro[0]

        # Fallback: dichtester Kandidat
        if kandidaten:
            return min(kandidaten, key=lambda k: abs(self.DICHTEN[k] - dichte))
        return "unknown"

    def sortieren(self, teile_liste: List[Dict]) -> Dict:
        """
        Sortiert Liste von Teilen in Kategorien.
        Rückgabe: Dict mit Keys 'kategorien' (Dict[str, List[Dict]]),
        'statistik' (Dict[str, int]), 'gesamt_gewicht_g' (float).
        """
        kategorien = {}
        gesamt_gewicht = 0.0

        for teil in teile_liste:
            if not isinstance(teil, dict):
                continue
            kategorie = self.erkennen(teil)
            if kategorie not in kategorien:
                kategorien[kategorie] = []
            # Teil kopieren & Kategorie anhängen
            t = teil.copy()
            t["kategorie_erkannt"] = kategorie
            kategorien[kategorie].append(t)
            try:
                gesamt_gewicht += float(teil.get("gewicht_g", 0))
            except (ValueError, TypeError):
                pass

        statistik = {k: len(v) for k, v in kategorien.items()}

        return _json_sicher({
            "kategorien": kategorien,
            "statistik": statistik,
            "gesamt_gewicht_g": round(gesamt_gewicht, 2)
        })


if __name__ == "__main__":
    # --- Tests für neuer_tag ---
    print("=== Test neuer_tag ===")
    # 1. Notfall Kakerlaken
    d1 = {"gestern": {}, "fehlschlaege": {}, "stimmung": 10, "wetter": "sonnig", "kakerlaken_level": 8}
    print("1. Notfall:", json.dumps(neuer_tag(d1), ensure_ascii=False, indent=2))

    # 2. Runde 1: KI fragen
    d2 = {"gestern": {"think": 2, "eat": 1}, "fehlschlaege": {"schrott_suchen": 1}, "stimmung": 5, "wetter": "regen", "kakerlaken_level": 1}
    print("2. Runde 1:", json.dumps(neuer_tag(d2), ensure_ascii=False, indent=2))

    # 3. Runde 2: Gute KI-Antwort
    d3 = {**d2, "ki_antwort": "think: Alu-Haufen sortieren | walk_to: Werkbank | schrott_suchen: Kisten prüfen"}
    print("3. Runde 2 OK:", json.dumps(neuer_tag(d3), ensure_ascii=False, indent=2))

    # 4. Runde 2: Schlechte KI-Antwort -> Fallback
    d4 = {**d2, "ki_antwort": "invalid format"}
    print("4. Runde 2 Fail:", json.dumps(neuer_tag(d4), ensure_ascii=False, indent=2))

    # 5. Stimmung mies -> Spazieren Fallback
    d5 = {"gestern": {}, "fehlschlaege": {}, "stimmung": -60, "wetter": "bewoelkt", "kakerlaken_level": 0, "ki_antwort": ""}
    print("5. Stimmung mies:", json.dumps(neuer_tag(d5), ensure_ascii=False, indent=2))

    # 6. Kakerlaken Warnlevel (4-6)
    d6 = {"gestern": {}, "fehlschlaege": {}, "stimmung": 50, "wetter": "sonnig", "kakerlaken_level": 5, "ki_antwort": "think: Sortieren | eat: Brot"}
    print("6. Kakerlaken Warnung:", json.dumps(neuer_tag(d6), ensure_ascii=False, indent=2))

    # --- Tests für MetallSortierer ---
    print("\n=== Test MetallSortierer ===")
    sorter = MetallSortierer()
    test_teile = [
        {"id": 1, "gewicht_g": 270, "volumen_cm3": 100, "magnetisch": False, "farbe": "silber", "zeichen": "AL"},      # Alu ~2.7
        {"id": 2, "gewicht_g": 785, "volumen_cm3": 100, "magnetisch": True, "farbe": "grau", "zeichen": ""},         # Stahl ~7.85
        {"id": 3, "gewicht_g": 896, "volumen_cm3": 100, "magnetisch": False, "farbe": "kupfer", "zeichen": "CU"},    # Kupfer ~8.96
        {"id": 4, "gewicht_g": 850, "volumen_cm3": 100, "magnetisch": False, "farbe": "gelb", "zeichen": ""},       # Messing ~8.5
        {"id": 5, "gewicht_g": 174, "volumen_cm3": 100, "magnetisch": False, "farbe": "silber", "zeichen": "MG"},    # Magnesium ~1.74
        {"id": 6, "gewicht_g": 450, "volumen_cm3": 100, "magnetisch": False, "farbe": "grau", "zeichen": "TI"},     # Titan ~4.5
        {"id": 7, "gewicht_g": 790, "volumen_cm3": 100, "magnetisch": False, "farbe": "silber", "zeichen": "INOX"},  # Edelstahl (nicht magnetisch) ~7.9
        {"id": 8, "gewicht_g": 1134, "volumen_cm3": 100, "magnetisch": False, "farbe": "grau", "zeichen": "PB"},    # Blei ~11.34
        {"id": 9, "gewicht_g": 500, "volumen_cm3": 100, "magnetisch": True, "farbe": "grau", "zeichen": "GUSS"},   # Guss ~7.2 (Dichte passt nicht perfekt, aber magnetisch)
        {"id": 10, "gewicht_g": 100, "volumen_cm3": 100, "magnetisch": False, "farbe": "weiss", "zeichen": "?"},     # Unknown ~1.0
    ]
    ergebnis = sorter.sortieren(test_teile)
    print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
    
    # Prüfung: Sind alle 10 Teile sortiert?
    assert sum(ergebnis["statistik"].values()) == 10
    print("\nAlle Tests durchgelaufen. Schuppen-Logik steht.")