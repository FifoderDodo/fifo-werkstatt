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
        "blei": 11.34, "zinn": 7.31,
        "nickel": 8.91, "nickellegierung": 8.5,
        "gold": 19.3, "silber": 10.49,
        "platin": 21.45
    }

    def __init__(self, teile: List[Dict]):
        self.teile = teile if isinstance(teile, list) else []
        self.ergebnis = {"kategorien": {}, "unbekannt": [], "fehler": []}
        self._kategorien_initialisieren()

    def _kategorien_initialisieren(self):
        kat = ["eisenhaltig", "edelstahl", "aluminium", "kupfer_messing_bronze",
               "magnesium", "titan", "zink", "blei_zinn", "edelmetall", "sonstiges"]
        for k in kat:
            self.ergebnis["kategorien"][k] = []

    def magnet_test(self, teil: Dict) -> bool:
        """Simuliert Magnet-Test: True = magnetisch (Eisen/Stahl/Guss)."""
        # In echter Hardware: Sensor lesen. Hier: Heuristik aus Daten.
        material = str(teil.get("material_vermutung", "")).lower()
        magnetisch = teil.get("magnetisch", None)
        if magnetisch is not None:
            return bool(magnetisch)
        # Fallback: Namens-Heuristik
        return any(w in material for w in ["eisen", "stahl", "guss", "ferro"]) and "edel" not in material

    def funken_test(self, teil: Dict) -> str:
        """Simuliert Funkenbild-Test: 'lang_weiss', 'kurz_rot', 'keine', 'weiss_verzweigt'."""
        # Heuristik basierend auf Material-Verdacht
        mat = str(teil.get("material_vermutung", "")).lower()
        if any(w in mat for w in ["stahl", "eisen", "guss"]):
            return "lang_weiss" if "legiert" not in mat else "weiss_verzweigt"
        if "edelstahl" in mat:
            return "weiss_verzweigt"
        if any(w in mat for w in ["kupfer", "messing", "bronze", "aluminium", "zink"]):
            return "keine"
        return "unbekannt"

    def dichte_test(self, teil: Dict) -> float:
        """Berechnet Dichte aus Gewicht (g) und Volumen (cm³) oder schätzt."""
        try:
            gewicht = float(teil.get("gewicht_g", 0))
            volumen = float(teil.get("volumen_cm3", 0))
            if gewicht > 0 and volumen > 0:
                return round(gewicht / volumen, 2)
        except (ValueError, TypeError):
            pass
        # Fallback: Keine Messdaten -> 0.0 signalisiert 'unbekannt'
        return 0.0

    def _dichte_match(self, dichte: float, toleranz: float = 0.08) -> List[str]:
        """Findet Material-Keys in DICHTEN, die zur gemessenen Dichte passen (± Toleranz)."""
        if dichte <= 0:
            return []
        treffer = []
        for material, d in self.DICHTEN.items():
            if abs(d - dichte) / d <= toleranz:
                treffer.append(material)
        return treffer

    def material_pruefung(self, teil: Dict) -> str:
        """Entscheidet Kategorie für ein Teil basierend auf Tests."""
        magnet = self.magnet_test(teil)
        funken = self.funken_test(teil)
        dichte = self.dichte_test(teil)
        mat_vermutung = str(teil.get("material_vermutung", "")).lower()
        dichte_treffer = self._dichte_match(dichte)

        # Logik-Kette: Magnetisch stark -> Eisen/Stahl
        if magnet:
            if "edel" in mat_vermutung or funken == "weiss_verzweigt":
                return "edelstahl"
            return "eisenhaltig"

        # Nicht magnetisch -> Dichte & Funken entscheiden
        if dichte_treffer:
            # Beste Dichte-Übereinstimmung nehmen
            best = dichte_treffer[0]
            if best in ("aluminium", "aluminiumlegierung", "magnesium"):
                return "aluminium" if "aluminium" in best else "magnesium"
            if best in ("kupfer", "messing", "bronze"):
                return "kupfer_messing_bronze"
            if best in ("zink", "zinklegierung"):
                return "zink"
            if best in ("blei", "zinn"):
                return "blei_zinn"
            if best in ("gold", "silber", "platin"):
                return "edelmetall"
            if best == "titan":
                return "titan"

        # Fallback über Funkenbild / Vermutung
        if funken == "keine":
            if any(w in mat_vermutung for w in ["alu", "magnesium"]):
                return "aluminium"
            if any(w in mat_vermutung for w in ["kupfer", "messing", "bronze"]):
                return "kupfer_messing_bronze"
            if any(w in mat_vermutung for w in ["zink"]):
                return "zink"
            if any(w in mat_vermutung for w in ["titan"]):
                return "titan"

        return "sonstiges"

    def sortiere(self) -> Dict:
        """Hauptmethode: Iteriert Teile, prüft, sortiert in Kategorien."""
        for idx, teil in enumerate(self.teile):
            if not isinstance(teil, dict):
                self.ergebnis["fehler"].append({"index": idx, "grund": "Kein Dict"})
                continue
            try:
                kat = self.material_pruefung(teil)
                eintrag = {"id": teil.get("id", f"teil_{idx}"),
                           "gewicht_g": teil.get("gewicht_g"),
                           "notiz": teil.get("notiz", "")[:100]}
                self.ergebnis["kategorien"][kat].append(eintrag)
            except Exception as e:
                self.ergebnis["fehler"].append({"index": idx, "grund": str(e)})

        # Leere Kategorien entfernen für sauberes JSON
        self.ergebnis["kategorien"] = {k: v for k, v in self.ergebnis["kategorien"].items() if v}
        return _json_sicher(self.ergebnis)

    def get_ergebnis(self) -> Dict:
        """Gibt aktuelles Ergebnis (falls sortiere schon lief) oder startet Sortierung."""
        if not self.ergebnis["kategorien"] and not self.ergebnis["fehler"] and self.teile:
            return self.sortiere()
        return _json_sicher(self.ergebnis)


# --- Test-Block ---
if __name__ == "__main__":
    print("=== Test neuer_tag (Runde 1: KI fragen) ===")
    eingabe1 = {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen": 2}, "stimmung": 10, "wetter": "sonnig", "kakerlaken_level": 1}
    ausgabe1 = neuer_tag(eingabe1)
    print(json.dumps(ausgabe1, indent=2, ensure_ascii=False))

    print("\n=== Test neuer_tag (Runde 2: KI antwortet) ===")
    eingabe2 = {**eingabe1, "ki_antwort": "think: Aluminium-Haufen prüfen | walk_to: Waage holen | schrott_suchen: Kiste 4"}
    ausgabe2 = neuer_tag(eingabe2)
    print(json.dumps(ausgabe2, indent=2, ensure_ascii=False))

    print("\n=== Test neuer_tag (Kakerlaken-Alarm Level 7) ===")
    eingabe3 = {"gestern": {}, "fehlschlaege": {}, "stimmung": -10, "wetter": "regen", "kakerlaken_level": 7}
    ausgabe3 = neuer_tag(eingabe3)
    print(json.dumps(ausgabe3, indent=2, ensure_ascii=False))

    print("\n=== Test MetallSortierer ===")
    test_teile = [
        {"id": "A1", "gewicht_g": 270, "volumen_cm3": 100, "material_vermutung": "Aluminium-Profil", "magnetisch": False},
        {"id": "B2", "gewicht_g": 785, "volumen_cm3": 100, "material_vermutung": "Stahlstab", "magnetisch": True},
        {"id": "C3", "gewicht_g": 896, "volumen_cm3": 100, "material_vermutung": "Kupferrohr", "magnetisch": False},
        {"id": "D4", "gewicht_g": 500, "volumen_cm3": 100, "material_vermutung": "Unbekanntes Metall", "magnetisch": False}, # Dichte 5.0 -> nix genaues
        {"id": "E5", "gewicht_g": 1930, "volumen_cm3": 100, "material_vermutung": "Schweres Gelb", "magnetisch": False}, # Dichte 19.3 -> Gold
        {"id": "F6", "material_vermutung": "Keine Messdaten"}, # Keine Dichte
    ]
    sorter = MetallSortierer(test_teile)
    ergebnis = sorter.sortiere()
    print(json.dumps(ergebnis, indent=2, ensure_ascii=False))