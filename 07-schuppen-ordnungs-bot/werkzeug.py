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
        "gold": 19.3, "silber": 10.5,
        "nickel": 8.9
    }

    def __init__(self, teile: List[Dict]):
        self.teile = teile
        self.ergebnis = {}

    def magnet_test(self, teil: Dict) -> bool:
        """Simuliert Magnet-Test: True = ferromagnetisch (Stahl/Eisen/Guss)."""
    # Heuristik: Wenn Material-String Hinweise enthält oder Dichte > 7.5 & kein Edelstahl/Nickel
        mat = str(teil.get("material", "")).lower()
        if any(k in mat for k in ["stahl", "eisen", "guss", "ferro"]):
            return True
        if "edelstahl" in mat or "austenit" in mat:
            return False  # Meist nicht magnetisch
        dichte = teil.get("dichte")
        if dichte and dichte > 7.5:
            return True
        return False

    def funken_test(self, teil: Dict) -> str:
        """Simuliert Funkenbild: 'lang_weiss' (Stahl), 'kurz_rot' (Guss), 'keine' (NE-Metalle)."""
        mat = str(teil.get("material", "")).lower()
        if any(k in mat for k in ["stahl", "eisen"]):
            return "lang_weiss"
        if "guss" in mat:
            return "kurz_rot"
        return "keine"

    def dichte_test(self, teil: Dict) -> float:
        """Gibt Dichte zurück (gemessen oder Default 0)."""
        return float(teil.get("dichte", 0) or 0)

    def _dichte_match(self, gemessen: float, ziel: float, toleranz: float = 0.08) -> bool:
        """Prüft ob gemessene Dichte im Toleranzbereich (Default 8%) liegt."""
        if gemessen <= 0 or ziel <= 0:
            return False
        return abs(gemessen - ziel) / ziel <= toleranz

    def material_pruefung(self, teil: Dict) -> str:
        """Bestimmt Material-Kategorie für ein Teil."""
        magnetisch = self.magnet_test(teil)
        funken = self.funken_test(teil)
        dichte = self.dichte_test(teil)
        mat_hinweis = str(teil.get("material", "")).lower()

        # 1. Expliziter Hinweis im Input
        for k, v in self.DICHTEN.items():
            if k in mat_hinweis:
                return k

        # 2. Logik-Baum
        if magnetisch:
            if funken == "kurz_rot" or "guss" in mat_hinweis:
                return "guss"
            if self._dichte_match(dichte, self.DICHTEN["edelstahl"]):
                return "edelstahl"
            return "stahl"  # Default ferromagnetisch

        # Nicht magnetisch -> NE-Metalle
        if funken != "keine":
            # Seltsam, aber Sicherheit
            pass

        # Dichte-Abgleich
        kandidaten = []
        for name, d in self.DICHTEN.items():
            if name in ["stahl", "eisen", "guss", "ferro", "edelstahl"]:
                continue
            if self._dichte_match(dichte, d):
                kandidaten.append((abs(dichte - d), name))
        
        if kandidaten:
            kandidaten.sort()
            return kandidaten[0][1]

        # Fallback nach grober Dichte
        if dichte > 0:
            if dichte < 3.0:
                return "aluminium"
            if dichte < 5.0:
                return "titan"
            if dichte < 8.0:
                return "zinial"  # Zink/Alu Legierungen
            if dichte < 9.5:
                return "kupfer"
            if dichte < 12.0:
                return "blei"
            return "schwer_metall"
        
        return "unbekannt"

    def sortiere(self) -> Dict[str, List[Dict]]:
        """Sortiert alle Teile in Kategorien."""
        kategorien = {}
        for teil in self.teile:
            kat = self.material_pruefung(teil)
            teil_kopie = teil.copy()
            teil_kopie["kategorie"] = kat
            kategorien.setdefault(kat, []).append(teil_kopie)
        self.ergebnis = kategorien
        return kategorien

    def get_ergebnis(self) -> Dict:
        """Liefert JSON-sicheres Zusammenfassungs-Dict."""
        if not self.ergebnis:
            self.sortiere()
        summary = {}
        for kat, liste in self.ergebnis.items():
            gewicht = sum(float(t.get("gewicht", 0) or 0) for t in liste)
            summary[kat] = {
                "anzahl": len(liste),
                "gewicht_kg": round(gewicht, 2),
                "teile": [_json_sicher(t) for t in liste]
            }
        return _json_sicher({
            "kategorien": summary,
            "gesamt_teile": len(self.teile),
            "gesamt_gewicht_kg": round(sum(float(t.get("gewicht", 0) or 0) for t in self.teile), 2)
        })


if __name__ == "__main__":
    # Test neuer_tag
    print("=== Test neuer_tag ===")
    test_daten_1 = {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen": 2}, "stimmung": 10, "wetter": "regen", "kakerlaken_level": 2}
    erg1 = neuer_tag(test_daten_1)
    print("Runde 1 (Frage):", json.dumps(erg1, ensure_ascii=False))
    
    # Simuliere KI-Antwort
    test_daten_1["ki_antwort"] = "think: Sortierlogik verfeinern | eat: Frühstück | spazieren: Luft schnappen"
    erg2 = neuer_tag(test_daten_1)
    print("Runde 2 (Plan):", json.dumps(erg2, ensure_ascii=False))

    test_daten_2 = {"gestern": {}, "fehlschlaege": {}, "stimmung": 30, "wetter": "sonnig", "kakerlaken_level": 0}
    erg3 = neuer_tag(test_daten_2)
    print("Runde 1 (Frage 2):", json.dumps(erg3, ensure_ascii=False))
    test_daten_2["ki_antwort"] = ""
    erg4 = neuer_tag(test_daten_2)
    print("Runde 2 (Fallback):", json.dumps(erg4, ensure_ascii=False))

    # Test MetallSortierer
    print("\n=== Test MetallSortierer ===")
    test_teile = [
        {"id": 1, "material": "Aluminium Profil", "gewicht": 1.5, "dichte": 2.71},
        {"id": 2, "material": "Schrauben rostig", "gewicht": 0.5, "dichte": 7.8},
        {"id": 3, "material": "Kupferrohr", "gewicht": 2.0, "dichte": 8.9},
        {"id": 4, "material": "Messing Ventil", "gewicht": 0.8, "dichte": 8.4},
        {"id": 5, "material": "Unbekanntes Schweres", "gewicht": 5.0, "dichte": 11.3},
        {"id": 6, "material": "Edelstahl V2A", "gewicht": 3.0, "dichte": 7.95},
    ]
    sorter = MetallSortierer(test_teile)
    ergebnis = sorter.get_ergebnis()
    print(json.dumps(ergebnis, indent=2, ensure_ascii=False))