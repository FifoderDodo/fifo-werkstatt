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
        "zink": 7.13, "zinklegierung": 6.8,
        "blei": 11.34,
        "nickel": 8.9,
        "zinnober": 8.1, "lot": 8.5
    }

    @staticmethod
    def _schaetze_dichte(teil: Dict) -> float:
        """Berechnet Dichte aus Gewicht(g) / Volumen(cm³) falls vorhanden."""
        try:
            gewicht = float(teil.get("gewicht_g", 0))
            vol = float(teil.get("volumen_cm3", 0))
            if gewicht > 0 and vol > 0:
                return gewicht / vol
        except (ValueError, TypeError):
            pass
        return 0.0

    @classmethod
    def erkenne_metall(cls, teil: Dict) -> str:
        """Heuristik: Magnetisch, Farbe, Zeichen, Dichte -> Kategorie."""
        magnetisch = bool(teil.get("magnetisch", False))
        farbe = str(teil.get("farbe", "")).lower()
        zeichen = str(teil.get("zeichen", "")).lower()
        dichte = cls._schaetze_dichte(teil)

        # 1. Magnetisch -> Eisen/Stahl/Guss (außer Edelstahl oft nicht magnetisch)
        if magnetisch:
            if dichte > 7.5:
                return "ferro_schwer"  # Stahl, Guss, Eisen
            return "ferro_leicht"     # Selten, aber möglich

        # 2. Sehr leicht (Alu, Mg, Ti)
        if 1.5 < dichte < 3.0:
            if "mg" in zeichen or "magnesium" in zeichen:
                return "magnesium"
            if "ti" in zeichen or "titan" in zeichen:
                return "titan"
            return "aluminium"

        # 3. Schwermetalle (Cu, Zn, Pb, Ni)
        if dichte > 7.0:
            if "cu" in zeichen or "kupfer" in zeichen or farbe in ["rot", "orange", "kupfer"]:
                return "kupfer"
            if "pb" in zeichen or "blei" in zeichen or farbe == "blaugrau":
                return "blei"
            if "ni" in zeichen or "nickel" in zeichen:
                return "nickel"
            if "zn" in zeichen or "zink" in zeichen:
                return "zink"
            # Messing/Bronze oft gelblich/rotlich, nicht magnetisch, dicht ~8.5
            if farbe in ["gelb", "gold", "messing"] or "ms" in zeichen:
                return "messing"
            if farbe in ["braun", "bronze"] or "bz" in zeichen:
                return "bronze"
            return "schwermetall_unbekannt"

        # 4. Edelstahl (nicht magnetisch, dicht ~7.9, oft silber/glänzend)
        if 7.5 < dichte < 8.2 and farbe in ["silber", "grau", "edelstahl"]:
            return "edelstahl"

        return "unbekannt"

    @classmethod
    def sortieren(cls, teile: List[Dict]) -> Dict:
        """Hauptmethode: Sortiert Liste von Teilen in Kategorien."""
        kategorien = {}
        for idx, teil in enumerate(teile):
            if not isinstance(teil, dict):
                continue
            kat = cls.erkenne_metall(teil)
            kategorie_key = kat
            if kategorie_key not in kategorien:
                kategorien[kategorie_key] = []
            # Teil anreichern mit Erkennung
            angereichert = {**teil, "kategorie": kat, "index": idx}
            kategorien[kategorie_key].append(_json_sicher(angereichert))
        
        # Zusammenfassung
        summary = {k: len(v) for k, v in kategorien.items()}
        return _json_sicher({"kategorien": kategorien, "summary": summary, "gesamt": len(teile)})


if __name__ == "__main__":
    # Tests für neuer_tag
    print("=== Test neuer_tag ===")
    # 1. Notfall Kakerlaken
    test1 = {"gestern": {}, "fehlschlaege": {}, "stimmung": 10, "wetter": "sonnig", "kakerlaken_level": 8}
    print("Test1 (Notfall):", json.dumps(neuer_tag(test1), ensure_ascii=False, indent=2))

    # 2. Runde 1: KI fragen
    test2 = {"gestern": {"think": 5}, "fehlschlaege": {"schrott_suchen": 1}, "stimmung": 20, "wetter": "regen", "kakerlaken_level": 2}
    print("Test2 (Runde 1):", json.dumps(neuer_tag(test2), ensure_ascii=False, indent=2))

    # 3. Runde 2: Gute KI-Antwort
    test3 = {**test2, "ki_antwort": "think: Sortierlogik prüfen | schrott_suchen: Alu-Haufen angehen | eat: Brotzeit"}
    print("Test3 (Runde 2 OK):", json.dumps(neuer_tag(test3), ensure_ascii=False, indent=2))

    # 4. Runde 2: Schlechte KI-Antwort -> Fallback
    test4 = {**test2, "ki_antwort": "quatsch"}
    print("Test4 (Runde 2 Fail):", json.dumps(neuer_tag(test4), ensure_ascii=False, indent=2))

    # 5. Kakerlaken Warnung Level 5
    test5 = {**test2, "kakerlaken_level": 5, "ki_antwort": "think: Planen | eat: Essen"}
    print("Test5 (Warnung):", json.dumps(neuer_tag(test5), ensure_ascii=False, indent=2))

    # Tests für MetallSortierer
    print("\n=== Test MetallSortierer ===")
    teile = [
        {"id": 1, "gewicht_g": 270, "volumen_cm3": 100, "magnetisch": False, "farbe": "silber", "zeichen": "AL"},
        {"id": 2, "gewicht_g": 785, "volumen_cm3": 100, "magnetisch": True, "farbe": "grau", "zeichen": "ST37"},
        {"id": 3, "gewicht_g": 896, "volumen_cm3": 100, "magnetisch": False, "farbe": "rot", "zeichen": "CU"},
        {"id": 4, "gewicht_g": 850, "volumen_cm3": 100, "magnetisch": False, "farbe": "gelb", "zeichen": "MS63"},
        {"id": 5, "gewicht_g": 1134, "volumen_cm3": 100, "magnetisch": False, "farbe": "blaugrau", "zeichen": "PB"},
        {"id": 6, "gewicht_g": 174, "volumen_cm3": 100, "magnetisch": False, "farbe": "silber", "zeichen": "MG"},
        {"id": 7, "gewicht_g": 450, "volumen_cm3": 100, "magnetisch": False, "farbe": "grau", "zeichen": "TI"},
        {"id": 8, "gewicht_g": 790, "volumen_cm3": 100, "magnetisch": False, "farbe": "silber", "zeichen": "V2A"},
        {"id": 9, "gewicht_g": 713, "volumen_cm3": 100, "magnetisch": False, "farbe": "blauweiss", "zeichen": "ZN"},
        {"id": 10, "gewicht_g": 500, "volumen_cm3": 100, "magnetisch": False, "farbe": "weiss", "zeichen": "?"},  # Dichte 5 -> unbekannt
    ]
    ergebnis = MetallSortierer.sortieren(teile)
    print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
    print(f"\nGesamt sortiert: {ergebnis.get('gesamt')}")
    print(f"Kategorien: {ergebnis.get('summary')}")