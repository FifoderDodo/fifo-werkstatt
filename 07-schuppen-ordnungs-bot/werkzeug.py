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
        "blei": 11.34, "zink": 7.13, "nickel": 8.91,
        "gold": 19.3, "silber": 10.49, "platin": 21.45,
        "unknown": 0.0
    }
    TOLERANZ = 0.08  # 8%

    def __init__(self):
        self.ergebnis = {"kategorien": {}, "unsortiert": [], "fehler": []}

    def magnet_test(self, teil: Dict) -> bool:
        """Prüft Magnetismus. Erwartet 'magnetisch' (bool) im Teil-Dict."""
        return bool(teil.get("magnetisch", False))

    def funken_test(self, teil: Dict) -> str:
        """Simuliert Funkenbild. Erwartet 'funken' (str) im Teil-Dict."""
        return str(teil.get("funken", "keine")).lower()

    def dichte_test(self, teil: Dict) -> float:
        """Berechnet Dichte aus Gewicht (g) und Volumen (cm³). Fallback 0.0."""
        try:
            gewicht = float(teil.get("gewicht_g", 0))
            volumen = float(teil.get("volumen_cm3", 0))
            if gewicht > 0 and volumen > 0:
                return round(gewicht / volumen, 2)
        except (ValueError, TypeError):
            pass
        return 0.0

    def _dichte_match(self, dichte: float) -> List[str]:
        """Findet Material-Namen mit Dichte in 8%-Toleranz."""
        if dichte <= 0:
            return []
        matches = []
        for name, d in self.DICHTEN.items():
            if d == 0:
                continue
            if abs(d - dichte) / d <= self.TOLERANZ:
                matches.append(name)
        return matches

    def material_pruefung(self, teil: Dict) -> Dict:
        """Führt Tests durch und gibt bestes Material-Match zurück."""
        magnetisch = self.magnet_test(teil)
        funken = self.funken_test(teil)
        dichte = self.dichte_test(teil)
        kandidaten = self._dichte_match(dichte)

        # Einfache Heuristik: Ferro magnetisch, NE-Metalle nicht
        if magnetich:
            kandidaten = [k for k in kandidaten if k in ("stahl", "eisen", "guss", "ferro", "edelstahl", "nickel")]
        else:
            kandidaten = [k for k in kandidaten if k not in ("stahl", "eisen", "guss", "ferro")]

        material = kandidaten[0] if kandidaten else "unknown"
        sicherheit = "hoch" if len(kandidaten) == 1 else ("mittel" if kandidaten else "gering")

        return {
            "material": material,
            "dichte_g_cm3": dichte,
            "magnetisch": magnetisch,
            "funken": funken,
            "kandidaten": kandidaten,
            "sicherheit": sicherheit
        }

    def sortiere(self, teile: List[Dict]) -> Dict:
        """Hauptmethode: Sortiert Liste von Teilen in Kategorien."""
        self.ergebnis = {"kategorien": {}, "unsortiert": [], "fehler": []}

        for i, teil in enumerate(teile):
            if not isinstance(teil, dict):
                self.ergebnis["fehler"].append({"index": i, "grund": "Kein Dict"})
                continue

            try:
                pruf = self.material_pruefung(teil)
                kat = pruf["material"]
                if kat not in self.ergebnis["kategorien"]:
                    self.ergebnis["kategorien"][kat] = []
                eintrag = {"original": teil, "analyse": pruf}
                self.ergebnis["kategorien"][kat].append(eintrag)
            except Exception as e:
                self.ergebnis["fehler"].append({"index": i, "grund": str(e)})

        # Teile mit Sicherheit 'gering' oder 'unknown' in unsortiert verschieben
        unsortiert = []
        for kat, liste in list(self.ergebnis["kategorien"].items()):
            behalten = []
            for eintrag in liste:
                if eintrag["analyse"]["sicherheit"] == "gering" or eintrag["analyse"]["material"] == "unknown":
                    unsortiert.append(eintrag)
                else:
                    behalten.append(eintrag)
            if behalten:
                self.ergebnis["kategorien"][kat] = behalten
            else:
                del self.ergebnis["kategorien"][kat]
        self.ergebnis["unsortiert"] = unsortiert

        return self.get_ergebnis()

    def get_ergebnis(self) -> Dict:
        """Liefert JSON-sicheres Ergebnis."""
        return _json_sicher(self.ergebnis)


# Test-Block für direkten Aufruf
if __name__ == "__main__":
    # Test neuer_tag
    print("--- Test neuer_tag ---")
    test_daten = {"gestern": {"think": 2, "eat": 1}, "fehlschlaege": {},
                  "stimmung": 30, "wetter": "sonnig", "kakerlaken_level": 1}
    print(json.dumps(neuer_tag(test_daten), ensure_ascii=False, indent=2))
    
    test_daten_ki = dict(test_daten, ki_antwort="think: Sortieren planen | schrott_suchen: Alte Kabel suchen | eat: Brotzeit")
    print(json.dumps(neuer_tag(test_daten_ki), ensure_ascii=False, indent=2))

    # Test MetallSortierer
    print("\n--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    test_teile = [
        {"id": 1, "gewicht_g": 785, "volumen_cm3": 100, "magnetisch": True, "funken": "gelb lang", "label": "Stahlstück"},
        {"id": 2, "gewicht_g": 270, "volumen_cm3": 100, "magnetisch": False, "funken": "keine", "label": "Alu-Profil"},
        {"id": 3, "gewicht_g": 896, "volumen_cm3": 100, "magnetisch": False, "funken": "grün kurz", "label": "Kupferrohr"},
        {"id": 4, "gewicht_g": 500, "volumen_cm3": 50, "magnetisch": True, "funken": "rot kurz", "label": "Guss-Ecke"},
        {"id": 5, "gewicht_g": 100, "volumen_cm3": 200, "magnetisch": False, "funken": "keine", "label": "Leichtes Etwas"},
    ]
    ergebnis = sorter.sortiere(test_teile)
    print(json.dumps(ergebnis, ensure_ascii=False, indent=2))