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
        "zinn": 7.31,
        "nickel": 8.9,
        "gold": 19.3,
        "silber": 10.49,
        "platin": 21.45
    }

    def __init__(self):
        self.kategorien = {}

    def _rate_metall_typ(self, teil: Dict) -> str:
        """Heuristik: Erratet Metalltyp basierend auf Eigenschaften."""
        gewicht = float(teil.get("gewicht", 0))
        volumen = float(teil.get("volumen", 1))
        farbe = str(teil.get("farbe", "")).lower()
        magnetisch = bool(teil.get("magnetisch", False))
        leiter = bool(teil.get("leiter", False))
        dichte = gewicht / volumen if volumen > 0 else 0

        # Starke Heuristiken zuerst
        if magnetisch and dichte > 7.0:
            if "rost" in farbe or "braun" in farbe:
                return "eisen"
            return "stahl"
        if not magnetisch and leiter and dichte > 8.5:
            if "rot" in farbe or "orange" in farbe:
                return "kupfer"
            if "gelb" in farbe or "gold" in farbe:
                return "messing"
            return "bronze"
        if not magnetisch and dichte < 3.0:
            return "aluminium"
        if not magnetisch and 3.0 <= dichte < 5.0:
            return "titan"
        if magnetisch and dichte > 7.5 and "edel" in farbe:
            return "edelstahl"
        if dichte > 15:
            return "blei"  # oder gold/platin, aber blei ist häufiger Schrott

        # Näherung über Dichte
        best_match = "unbekannt"
        min_diff = float('inf')
        for name, d in self.DICHTEN.items():
            diff = abs(d - dichte)
            if diff < min_diff:
                min_diff = diff
                best_match = name
        return best_match

    def sortieren(self, teile: List[Dict]) -> Dict:
        """Sortiert Teile in Kategorien, gibt Statistik zurück."""
        ergebnis = {}
        for teil in teile:
            typ = self._rate_metall_typ(teil)
            if typ not in ergebnis:
                ergebnis[typ] = {"teile": [], "gesamt_gewicht": 0.0, "anzahl": 0}
            ergebnis[typ]["teile"].append(_json_sicher(teil))
            ergebnis[typ]["gesamt_gewicht"] += float(teil.get("gewicht", 0))
            ergebnis[typ]["anzahl"] += 1
        return _json_sicher(ergebnis)


if __name__ == "__main__":
    # Selbsttest für neuer_tag
    print("=== Test neuer_tag ===")
    test1 = {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen": 2}, "stimmung": 10, "wetter": "sonnig", "kakerlaken_level": 1}
    print("Test 1 (Runde 1):", neuer_tag(test1))
    test1_antwort = {"ki_antwort": "think: Sortierlogik verfeinern | eat: Frühstück | spazieren: Luft schnappen"}
    test1.update(test1_antwort)
    print("Test 1 (Runde 2):", neuer_tag(test1))

    test2 = {"gestern": {}, "fehlschlaege": {}, "stimmung": -60, "wetter": "regen", "kakerlaken_level": 5}
    print("Test 2 (Notfall Kakerlaken):", neuer_tag(test2))

    test3 = {"gestern": {"walk_to": 1}, "fehlschlaege": {}, "stimmung": 50, "wetter": "bewoelkt", "kakerlaken_level": 0, "ki_antwort": ""}
    print("Test 3 (KI leer -> Fallback):", neuer_tag(test3))

    # Selbsttest für MetallSortierer
    print("\n=== Test MetallSortierer ===")
    sorter = MetallSortierer()
    test_teile = [
        {"id": 1, "gewicht": 270, "volumen": 100, "farbe": "silber", "magnetisch": False, "leiter": True},   # Alu
        {"id": 2, "gewicht": 785, "volumen": 100, "farbe": "grau", "magnetisch": True, "leiter": True},      # Stahl
        {"id": 3, "gewicht": 896, "volumen": 100, "farbe": "rot", "magnetisch": False, "leiter": True},      # Kupfer
        {"id": 4, "gewicht": 1134, "volumen": 100, "farbe": "grau", "magnetisch": False, "leiter": True},    # Blei
        {"id": 5, "gewicht": 450, "volumen": 100, "farbe": "silber", "magnetisch": False, "leiter": True},   # Titan
        {"id": 6, "gewicht": 790, "volumen": 100, "farbe": "glänzend", "magnetisch": False, "leiter": True}, # Edelstahl
        {"id": 7, "gewicht": 850, "volumen": 100, "farbe": "gelb", "magnetisch": False, "leiter": True},    # Messing
        {"id": 8, "gewicht": 270, "volumen": 100, "farbe": "weiß", "magnetisch": False, "leiter": True},    # Magnesium/Alu
        {"id": 9, "gewicht": 720, "volumen": 100, "farbe": "braun", "magnetisch": True, "leiter": True},    # Guss/Eisen
        {"id": 10, "gewicht": 1930, "volumen": 100, "farbe": "gold", "magnetisch": False, "leiter": True},   # Gold (selten aber test)
    ]
    ergebnis = sorter.sortieren(test_teile)
    print(json.dumps(ergebnis, indent=2, ensure_ascii=False))
    print("\nAlle Tests durchgelaufen.")