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
        "zink": 7.13, "zinialloy": 6.8,
        "blei": 11.34,
        "nickel": 8.9,
    }
    TOLERANZ = 0.08  # 8%

    def __init__(self, teile: List[Dict[str, Any]]):
        self.teile = teile
        self.ergebnis = {"kategorien": {}, "unbekannt": []}

    def magnet_test(self, teil: Dict) -> bool:
        """Simuliert Magnet-Test: True wenn ferromagnetisch (Eisen, Stahl, Guss, Nickel)."""
        # In der Realität hier Sensor-Abfrage. Simuliere über Material-Hinweis oder Zufall für Demo.
        mat = str(teil.get("material_hinweis", "")).lower()
        magnetisch_stichwoerter = ["eisen", "stahl", "guss", "ferro", "nickel"]
        if any(w in mat for w in magnetisch_stichwoerter):
            return True
        # Fallback: ~50% Chance bei unbekannt, aber hier deterministisch für Test
        return hash(str(teil.get("id", ""))) % 2 == 0

    def funken_test(self, teil: Dict) -> str:
        """Simuliert Funkenbild: 'lang_gelb' (Stahl), 'kurz_rot' (Guss), 'keine' (Nichteisen), 'weiss' (Titan)."""
        mat = str(teil.get("material_hinweis", "")).lower()
        if "titan" in mat: return "weiss"
        if "guss" in mat: return "kurz_rot"
        if any(w in mat for w in ["stahl", "eisen", "ferro"]): return "lang_gelb"
        if any(w in mat for w in ["edelstahl"]): return "kurz_gelb"
        return "keine"

    def dichte_test(self, teil: Dict) -> float:
        """Berechnet Dichte aus Gewicht (g) / Volumen (cm3). Erwartet Keys 'gewicht_g', 'volumen_cm3'."""
        try:
            g = float(teil.get("gewicht_g", 0))
            v = float(teil.get("volumen_cm3", 0))
            if v <= 0: return 0.0
            return g / v
        except (ValueError, TypeError):
            return 0.0

    def _dichte_match(self, dichte: float) -> List[str]:
        """Gibt Liste möglicher Material-Namen für gemessene Dichte ± Toleranz."""
        if dichte <= 0: return []
        matches = []
        for name, d in self.DICHTEN.items():
            if abs(d - dichte) / d <= self.TOLERANZ:
                matches.append(name)
        return matches

    def material_pruefung(self, teil: Dict) -> Dict[str, Any]:
        """Führt Tests durch und schlägt Kategorie vor."""
        magnet = self.magnet_test(teil)
        funken = self.funken_test(teil)
        dichte = self.dichte_test(teil)
        kandidaten = self._dichte_match(dichte)

        # Logik: Magnetisch + Funken -> Ferro
        # Nicht magnetisch + Dichte -> NE-Metalle
        kategorie = "unbekannt"
        sicherheit = 0.0

        if magnet:
            if "stahl" in kandidaten or "eisen" in kandidaten or "ferro" in kandidaten:
                kategorie = "stahl_eisen"
                sicherheit = 0.9
            elif "edelstahl" in kandidaten:
                kategorie = "edelstahl"
                sicherheit = 0.8
            elif "nickel" in kandidaten:
                kategorie = "nickel"
                sicherheit = 0.7
            else:
                kategorie = "ferro_sonstiges"
                sicherheit = 0.5
        else:
            # Nicht magnetisch
            if "aluminium" in kandidaten or "magnesium" in kandidaten:
                kategorie = "aluminium_leicht"
                sicherheit = 0.85
            elif "kupfer" in kandidaten or "messing" in kandidaten or "bronze" in kandidaten:
                kategorie = "kupfer_rot"
                sicherheit = 0.85
            elif "zink" in kandidaten:
                kategorie = "zink"
                sicherheit = 0.7
            elif "blei" in kandidaten:
                kategorie = "blei"
                sicherheit = 0.9
            elif "titan" in kandidaten:
                kategorie = "titan"
                sicherheit = 0.8
            else:
                kategorie = "nichteisen_sonstiges"
                sicherheit = 0.3

        return {
            "kategorie": kategorie,
            "sicherheit": round(sicherheit, 2),
            "messwerte": {"magnetisch": magnet, "funken": funken, "dichte_g_cm3": round(dichte, 2)},
            "kandidaten": kandidaten
        }

    def sortiere(self) -> Dict[str, Any]:
        """Hauptmethode: iteriert Teile, prüft, sortiert in Ergebnis-Dict."""
        kat_map = {}
        for teil in self.teile:
            pruef = self.material_pruefung(teil)
            kat = pruef["kategorie"]
            eintrag = {"teil_id": teil.get("id"), "details": pruef, "original": teil}
            if kat not in kat_map:
                kat_map[kat] = []
            kat_map[kat].append(eintrag)
        self.ergebnis["kategorien"] = kat_map
        return _json_sicher(self.ergebnis)

    def get_ergebnis(self) -> Dict[str, Any]:
        """Gibt sortiertes Ergebnis zurück (löst Sortierung aus falls nötig)."""
        if not self.ergebnis.get("kategorien"):
            self.sortiere()
        return _json_sicher(self.ergebnis)


if __name__ == "__main__":
    # Test neuer_tag: 2-Runden-Simulation
    print("=== Test neuer_tag ===")
    # Runde 1: Keine KI-Antwort -> Frage
    daten1 = {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen": 2}, "stimmung": 10, "wetter": "sonnig", "kakerlaken_level": 1}
    r1 = neuer_tag(daten1)
    print(f"Runde 1 (Frage): {json.dumps(r1, ensure_ascii=False)}")
    
    # Runde 2: Mit KI-Antwort (simuliert gutes Format)
    daten1["ki_antwort"] = "think: Aluminium-Haufen prüfen | walk_to: Waage holen | schrott_suchen: Ecke links"
    r2 = neuer_tag(daten1)
    print(f"Runde 2 (Plan): {json.dumps(r2, ensure_ascii=False, indent=2)}")

    # Test Fallback (leere KI-Antwort)
    daten2 = {"gestern": {}, "fehlschlaege": {}, "stimmung": -60, "wetter": "regen", "kakerlaken_level": 0, "ki_antwort": ""}
    r3 = neuer_tag(daten2)
    print(f"Fallback (schlechte Stimmung): {json.dumps(r3, ensure_ascii=False, indent=2)}")

    # Test MetallSortierer
    print("\n=== Test MetallSortierer ===")
    test_teile = [
        {"id": "T001", "gewicht_g": 270, "volumen_cm3": 100, "material_hinweis": "Alu-Profil"},
        {"id": "T002", "gewicht_g": 785, "volumen_cm3": 100, "material_hinweis": "Stahl-Stange"},
        {"id": "T003", "gewicht_g": 896, "volumen_cm3": 100, "material_hinweis": "Kupfer-Rohr"},
        {"id": "T004", "gewicht_g": 500, "volumen_cm3": 100, "material_hinweis": "Unbekanntes Etwas"},
    ]
    sorter = MetallSortierer(test_teile)
    ergebnis = sorter.get_ergebnis()
    print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
    print("\nTests durchgelaufen.")