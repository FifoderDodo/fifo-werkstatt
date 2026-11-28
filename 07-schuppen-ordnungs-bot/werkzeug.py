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
        "zink": 7.13, "zinial": 6.7,
        "blei": 11.34,
        "nickel": 8.9,
        "gold": 19.3, "silber": 10.5
    }

    def __init__(self, teile: List[Dict]):
        self.teile = teile
        self.ergebnis = {
            "eisenhaltig": [],
            "edelstahl": [],
            "aluminium": [],
            "kupfer_messing": [],
            "sonstiges_metall": [],
            "unbekannt": [],
            "fehler": []
        }

    def magnet_test(self, teil: Dict) -> bool:
        """Simuliert Magnet-Test. True = magnetisch (Eisen/Stahl/Guss)."""
    # In der Realität: Hardware-Abfrage. Hier: Heuristik aus Dict.
        material = str(teil.get("material", "")).lower()
        if any(k in material for k in ["eisen", "stahl", "guss", "ferro"]):
            return True
        if "edelstahl" in material:
            return teil.get("magnetisch", False)  # Manche Edelstähle sind magnetisch
        return False

    def funken_test(self, teil: Dict) -> str:
        """Simuliert Funkenbild-Test. Return: 'stahl', 'edelstahl', 'guss', 'keine', 'unbekannt'."""
        material = str(teil.get("material", "")).lower()
        if "stahl" in material and "edel" not in material:
            return "stahl"
        if "edelstahl" in material:
            return "edelstahl"
        if "guss" in material:
            return "guss"
        if any(k in material for k in ["aluminium", "kupfer", "messing", "bronze", "zink"]):
            return "keine"
        return "unbekannt"

    def dichte_test(self, teil: Dict) -> float:
        """Berechnet Dichte aus Gewicht/Volumen falls vorhanden, sonst -1.0."""
        try:
            gewicht = float(teil.get("gewicht_g", 0))
            volumen = float(teil.get("volumen_cm3", 0))
            if gewicht > 0 and volumen > 0:
                return round(gewicht / volumen, 2)
        except (ValueError, TypeError):
            pass
        return -1.0

    def _dichte_match(self, dichte: float, toleranz: float = 0.08) -> List[str]:
        """Findet Material-Namen in DICHTEN, die zur gemessenen Dichte passen (± Toleranz)."""
        if dichte <= 0:
            return []
        matches = []
        for name, d in self.DICHTEN.items():
            if abs(d - dichte) / d <= toleranz:
                matches.append(name)
        return matches

    def material_pruefung(self, teil: Dict) -> str:
        """Entscheidet Kategorie für ein Teil."""
        magnet = self.magnet_test(teil)
        funken = self.funken_test(teil)
        dichte = self.dichte_test(teil)
        matches = self._dichte_match(dichte)

        # Logik-Kette
        if magnet:
            if funken == "edelstahl" or "edelstahl" in matches:
                return "edelstahl"
            if funken == "guss" or "guss" in matches:
                return "eisenhaltig"  # Guss geht zu Eisenhaltig
            return "eisenhaltig"

        # Nicht magnetisch
        if funken == "keine" or dichte > 0:
            if any(m in ["aluminium", "aluminiumlegierung", "magnesium", "titan"] for m in matches):
                return "aluminium"
            if any(m in ["kupfer", "messing", "bronze"] for m in matches):
                return "kupfer_messing"
            if any(m in ["zink", "zinial", "blei", "nickel", "gold", "silber"] for m in matches):
                return "sonstiges_metall"
            # Dichte da, aber kein Match
            if dichte > 0:
                return "sonstiges_metall"

        return "unbekannt"

    def sortiere(self) -> Dict:
        """Läuft über alle Teile und befüllt self.ergebnis."""
        for i, teil in enumerate(self.teile):
            if not isinstance(teil, dict):
                self.ergebnis["fehler"].append({"index": i, "grund": "Kein Dict"})
                continue
            try:
                kat = self.material_pruefung(teil)
                eintrag = {"index": i, "daten": teil}
                if kat in self.ergebnis:
                    self.ergebnis[kat].append(eintrag)
                else:
                    self.ergebnis["unbekannt"].append(eintrag)
            except Exception as e:
                self.ergebnis["fehler"].append({"index": i, "grund": str(e)})
        return _json_sicher(self.ergebnis)

    def get_ergebnis(self) -> Dict:
        """Gibt sortiertes Ergebnis zurück, führt sortiere aus falls nötig."""
        if not any(self.ergebnis.values()):
            return self.sortiere()
        return _json_sicher(self.ergebnis)


if __name__ == "__main__":
    # Test neuer_tag: 2 Runden simuliert
    print("=== Test neuer_tag ===")
    # Runde 1: Keine ki_antwort -> Frage
    daten1 = {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen": 2}, "stimmung": 10, "wetter": "sonnig", "kakerlaken_level": 1}
    out1 = neuer_tag(daten1)
    print("Runde 1 (Frage):", json.dumps(out1, ensure_ascii=False)[:200])
    
    # Runde 2: Mit ki_antwort (simuliert gute KI)
    daten2 = {**daten1, "ki_antwort": "think: Sortierlogik für Aluminium prüfen | schrott_suchen: Kiste links durchsuchen | eat: Brotzeit"}
    out2 = neuer_tag(daten2)
    print("Runde 2 (Plan):", json.dumps(out2, ensure_ascii=False, indent=2))

    # Test Fallback (leere KI-Antwort)
    daten3 = {**daten1, "ki_antwort": "", "stimmung": -60}
    out3 = neuer_tag(daten3)
    print("Fallback (schlechte Laune):", json.dumps(out3, ensure_ascii=False, indent=2))

    # Test MetallSortierer
    print("\n=== Test MetallSortierer ===")
    test_teile = [
        {"material": "Aluminiumlegierung", "gewicht_g": 270, "volumen_cm3": 100},  # Dichte 2.7 -> Alu
        {"material": "Stahl", "gewicht_g": 785, "volumen_cm3": 100},              # Dichte 7.85 -> Eisenhaltig
        {"material": "Edelstahl V2A", "gewicht_g": 790, "volumen_cm3": 100, "magnetisch": False}, # Dichte 7.9 -> Edelstahl
        {"material": "Messing", "gewicht_g": 850, "volumen_cm3": 100},             # Dichte 8.5 -> Kupfer/Messing
        {"material": "Unbekanntes Schweres", "gewicht_g": 1134, "volumen_cm3": 100}, # Dichte 11.34 -> Blei (Sonstiges)
        {"material": "Holz", "gewicht_g": 50, "volumen_cm3": 100},                  # Dichte 0.5 -> Unbekannt
        {"gewicht_g": "schwer"}, # Fehlerhaft
    ]
    sorter = MetallSortierer(test_teile)
    ergebnis = sorter.get_ergebnis()
    print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
    print("\nTests durchgelaufen.")