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
        "nickel": 8.91,
        "gold": 19.3, "silber": 10.49,
        "platinum": 21.45
    }

    def __init__(self):
        self.kategorien = {
            "leichtmetall": [],
            "schwerimetall": [],
            "edelmetall": [],
            "ferromagnetisch": [],
            "unbekannt": []
        }

    def _dichte_schaetzen(self, teil: Dict) -> float:
        """Berechnet Dichte aus Masse/Volumen oder nutzt Material-Hinweis."""
        # 1. Explizites Material-Feld
        material = str(teil.get("material", "")).lower().strip()
        if material in self.DICHTEN:
            return self.DICHTEN[material]
        # 2. Berechnung aus Masse (g) und Volumen (cm^3)
        try:
            masse = float(teil.get("masse_g", 0))
            vol = float(teil.get("volumen_cm3", 0))
            if masse > 0 and vol > 0:
                return masse / vol
        except (ValueError, TypeError):
            pass
        return 0.0

    def _ist_magnetisch(self, teil: Dict) -> bool:
        """Prüft Magnet-Feld oder Vermutung bei Eisen/Stahl."""
        if teil.get("magnetisch"):
            return True
        material = str(teil.get("material", "")).lower()
        return any(m in material for m in ["eisen", "stahl", "guss", "ferro"])

    def erkennen(self, teil: Dict) -> str:
        """Ordnet Einzelteil einer Kategorie zu."""
        dichte = self._dichte_schaetzen(teil)
        magnetisch = self._ist_magnetisch(teil)
        material = str(teil.get("material", "")).lower()

        # Edelmetalle (hohe Dichte, spezifische Namen)
        if any(m in material for m in ["gold", "silber", "platinum", "platin"]) or dichte > 15:
            return "edelmetall"
        # Leichtmetalle
        if dichte > 0 and dichte < 5.0:
            return "leichtmetall"
        # Ferromagnetisch (Eisen/Stahl) - oft überschneidung mit Schwer
        if magnetisch:
            return "ferromagnetisch"
        # Schwermetalle (Kupfer, Messing, Blei, Zink > 5)
        if dichte >= 5.0:
            return "schwerimetall"
        return "unbekannt"

    def sortieren(self, teile: List[Dict]) -> Dict:
        """Hauptmethode: Nimmt Liste von Teilen, gibt sortiertes Dict zurück."""
        # Reset
        for k in self.kategorien:
            self.kategorien[k].clear()

        for teil in teile:
            if not isinstance(teil, dict):
                continue
            kat = self.erkennen(teil)
            # Anreichern mit berechneter Dichte für Ausgabe
            teil_kopie = teil.copy()
            teil_kopie["_dichte_g_cm3"] = round(self._dichte_schaetzen(teil), 2)
            teil_kopie["_kategorie"] = kat
            self.kategorien[kat].append(teil_kopie)

        # Zusammenfassung
        ergebnis = {
            "kategorien": {k: v for k, v in self.kategorien.items() if v},
            "anzahl_gesamt": len(teile),
            "verteilung": {k: len(v) for k, v in self.kategorien.items()}
        }
        return _json_sicher(ergebnis)


if __name__ == "__main__":
    # --- Tests für neuer_tag ---
    print("=== Test neuer_tag ===")
    # 1. Kakerlaken-Notfall
    d1 = {"gestern": {}, "fehlschlaege": {}, "stimmung": 50, "wetter": "sonnig", "kakerlaken_level": 8}
    print("Test 1 (Kakerlaken >= 7):", json.dumps(neuer_tag(d1), ensure_ascii=False, indent=2))

    # 2. Runde 1: KI fragen
    d2 = {"gestern": {"think": 2, "eat": 1}, "fehlschlaege": {"schrott_suchen": 1}, "stimmung": 10, "wetter": "regen", "kakerlaken_level": 2}
    print("Test 2 (Runde 1):", json.dumps(neuer_tag(d2), ensure_ascii=False, indent=2))

    # 3. Runde 2: Gute KI-Antwort
    d3 = {**d2, "ki_antwort": "think: Kupfer sortieren | schrott_suchen: Kabel suchen | einlagern: Kisten beschriften"}
    print("Test 3 (Runde 2 OK):", json.dumps(neuer_tag(d3), ensure_ascii=False, indent=2))

    # 4. Runde 2: Schlechte KI-Antwort -> Fallback
    d4 = {**d2, "ki_antwort": "blabla"}
    print("Test 4 (Runde 2 Fail):", json.dumps(neuer_tag(d4), ensure_ascii=False, indent=2))

    # 5. Stimmung mies -> Spazieren Fallback
    d5 = {"gestern": {}, "fehlschlaege": {}, "stimmung": -60, "wetter": "bewoelkt", "kakerlaken_level": 1, "ki_antwort": ""}
    print("Test 5 (Stimmung < -50):", json.dumps(neuer_tag(d5), ensure_ascii=False, indent=2))

    # 6. Kakerlaken Warnlevel (4-6)
    d6 = {"gestern": {}, "fehlschlaege": {}, "stimmung": 80, "wetter": "sonnig", "kakerlaken_level": 5, "ki_antwort": "think: Sortieren | eat: Brot | spazieren: Sonne"}
    print("Test 6 (Kakerlaken 4-6):", json.dumps(neuer_tag(d6), ensure_ascii=False, indent=2))

    # --- Tests für MetallSortierer ---
    print("\n=== Test MetallSortierer ===")
    sorter = MetallSortierer()
    test_teile = [
        {"id": 1, "material": "Aluminium", "masse_g": 270, "volumen_cm3": 100},  # 2.7 -> Leicht
        {"id": 2, "material": "Kupferrohr", "masse_g": 896, "volumen_cm3": 100},   # 8.96 -> Schwer
        {"id": 3, "material": "Stahlträger", "magnetisch": True, "masse_g": 7850, "volumen_cm3": 1000}, # Ferro
        {"id": 4, "material": "Goldbarren", "masse_g": 1930, "volumen_cm3": 100},  # 19.3 -> Edel
        {"id": 5, "material": "Messing", "masse_g": 850, "volumen_cm3": 100},       # 8.5 -> Schwer
        {"id": 6, "material": "Unbekanntes Metall", "masse_g": 500, "volumen_cm3": 200}, # 2.5 -> Leicht
        {"id": 7, "material": "Blei", "masse_g": 1134, "volumen_cm3": 100},         # 11.34 -> Schwer
        {"id": 8, "material": "Platin", "masse_g": 2145, "volumen_cm3": 100},       # 21.45 -> Edel
        {"id": 9, "material": "Titan", "masse_g": 450, "volumen_cm3": 100},         # 4.5 -> Leicht (Grenze)
        {"id": 10, "material": "Schrott", "masse_g": 100, "volumen_cm3": 0},         # Fehlerhaft -> Unbekannt
    ]
    ergebnis = sorter.sortieren(test_teile)
    print(json.dumps(ergebnis, ensure_ascii=False, indent=2))

    # Validierung Pfad Test
    print("\n=== Test Pfadvalidierung ===")
    try:
        print("OK:", validiere_dateipfad("daten/test.json"))
    except Exception as e:
        print("Fehler:", e)
    try:
        validiere_dateipfad("../../etc/passwd")
    except Exception as e:
        print("Erwarteter Fehler:", e)