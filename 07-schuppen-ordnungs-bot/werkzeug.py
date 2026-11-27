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
        "zink": 7.1, "blei": 11.34, "zinn": 7.3
    }
    
    # Toleranzen für Dichtevergleich (relativ)
    DICHTE_TOLERANZ = 0.08  # 8% Puffer für Schmutz, Legierungen, Messfehler
    
    def __init__(self):
        self.kategorien = {
            "eisenhaltig": [],
            "edelstahl": [],
            "aluminium": [],
            "kupfer": [],
            "messing": [],
            "sonstiges": [],
            "schrott": [],
            "kakerlaken_verdaechtig": []
        }
    
    def reset(self):
        """Leert alle Kategorien für neuen Durchlauf."""
        for k in self.kategorien:
            self.kategorien[k] = []
    
    def magnet_test(self, teil: dict) -> bool:
        """Simuliert Magnet-Test. True = ferromagnetisch (Eisen/Stahl/Guss)."""
        try:
            material = str(teil.get("material", "")).lower()
            # Ferromagnetisch: Eisen, Stahl, Guss, Ferro-Legierungen
            ferromagnetisch = any(k in material for k in ["eisen", "stahl", "guss", "ferro"])
            # Edelstahl oft nicht magnetisch (austenitisch), aber manche sind es.
            # Hier vereinfacht: 'edelstahl' im Namen -> nicht magnetisch, außer 'magnetisch' im Namen.
            if "edelstahl" in material and "magnetisch" not in material:
                return False
            return ferromagnetisch
        except Exception:
            return False
    
    def funken_test(self, teil: dict) -> str:
        """Simuliert Funkenbild-Test. Gibt Kategorie-Hinweis zurück."""
        try:
            material = str(teil.get("material", "")).lower()
            if any(k in material for k in ["stahl", "eisen", "guss"]):
                return "gelb_weiss_verzweigt"  # Kohlenstoffstahl
            if "edelstahl" in material:
                return "gelb_kurz_keine_verzweigung"  # Edelstahl
            if any(k in material for k in ["kupfer", "messing", "bronze"]):
                return "keine_funken_rot_schmelze"  # NE-Metalle
            if any(k in material for k in ["aluminium", "magnesium", "titan"]):
                return "keine_funken_weiss_oxid"   # Leichmetalle
            return "unbekannt"
        except Exception:
            return "fehler"
    
    def dichte_test(self, teil: dict) -> float:
        """Berechnet/Schätzt Dichte aus Masse/Volumen oder Material-Namen."""
        try:
            # 1. Versuch: Explizite Masse/Volumen im Dict
            if "masse_g" in teil and "volumen_cm3" in teil:
                v = float(teil["volumen_cm3"])
                if v > 0:
                    return float(teil["masse_g"]) / v
            # 2. Versuch: Material-Name -> Lookup
            material = str(teil.get("material", "")).lower()
            for k, d in self.DICHTEN.items():
                if k in material:
                    return d
            # 3. Fallback: Grobe Schätzung nach Farbe/Gewicht-Text
            if "schwer" in str(teil.get("notizen", "")).lower():
                return 8.0
            if "leicht" in str(teil.get("notizen", "")).lower():
                return 2.8
            return 7.0  # Default Eisen-Verdacht
        except Exception:
            return 7.0
    
    def _dichte_match(self, gemessen: float, ziel: float) -> bool:
        """Prüft ob gemessene Dichte im Toleranzbereich zur Zieldichte liegt."""
        if ziel <= 0:
            return False
        diff = abs(gemessen - ziel) / ziel
        return diff <= self.DICHTE_TOLERANZ
    
    def material_pruefung(self, teil: dict) -> str:
        """Kombiniert Tests zu Material-Kategorie."""
        magnetisch = self.magnet_test(teil)
        funken = self.funken_test(teil)
        dichte = self.dichte_test(teil)
        lagerort = str(teil.get("lagerort", "")).lower()
        
        # Kakerlaken-Verdacht prüfen
        if any(k in lagerort for k in ["ecke", "karton", "ritze", "dunkel", "boden"]):
            return "kakerlaken_verdaechtig"
        
        # Logik-Baum
        if magnetisch:
            # Ferromagnetisch: Eisen, Stahl, Guss
            if self._dichte_match(dichte, self.DICHTEN["edelstahl"]) and "edelstahl" in str(teil.get("material", "")).lower():
                return "edelstahl"
            if funken == "gelb_kurz_keine_verzweigung":
                return "edelstahl"
            return "eisenhaltig"
        
        # Nicht magnetisch: NE-Metalle
        if self._dichte_match(dichte, self.DICHTEN["aluminium"]) or self._dichte_match(dichte, self.DICHTEN["magnesium"]):
            return "aluminium"
        if self._dichte_match(dichte, self.DICHTEN["kupfer"]):
            return "kupfer"
        if self._dichte_match(dichte, self.DICHTEN["messing"]) or self._dichte_match(dichte, self.DICHTEN["bronze"]):
            return "messing"
        if self._dichte_match(dichte, self.DICHTEN["titan"]):
            return "sonstiges"  # Titan extra
        if self._dichte_match(dichte, self.DICHTEN["zink"]) or self._dichte_match(dichte, self.DICHTEN["zinn"]) or self._dichte_match(dichte, self.DICHTEN["blei"]):
            return "sonstiges"
        
        # Fallback über Funkenbild
        if funken == "keine_funken_rot_schmelze":
            return "kupfer"
        if funken == "keine_funken_weiss_oxid":
            return "aluminium"
        
        return "schrott"
    
    def sortiere(self, teile: List[dict]) -> Dict[str, List[dict]]:
        """Hauptmethode: Sortiert Liste von Teilen in self.kategorien."""
        self.reset()
        for teil in teile:
            if not isinstance(teil, dict):
                continue
            kat = self.material_pruefung(teil)
            if kat in self.kategorien:
                self.kategorien[kat].append(_json_sicher(teil))
            else:
                self.kategorien["schrott"].append(_json_sicher(teil))
        return self.kategorien
    
    def get_ergebnis(self) -> dict:
        """Gibt JSON-sicheres Ergebnis mit Counts zurück."""
        return {
            "kategorien": {k: _json_sicher(v) for k, v in self.kategorien.items()},
            "anzahlen": {k: len(v) for k, v in self.kategorien.items()},
            "gesamt": sum(len(v) for v in self.kategorien.values())
        }


# Test-Block für manuellen Lauf (wird vom Test-Harness ignoriert)
if __name__ == "__main__":
    # 1. Test neuer_tag Runde 1
    daten1 = {"gestern": {"think": 2}, "fehlschlaege": {}, "stimmung": 10, "wetter": "sonnig", "kakerlaken_level": 2}
    print("Runde 1:", json.dumps(neuer_tag(daten1), ensure_ascii=False, indent=2))
    
    # 2. Test neuer_tag Runde 2 (simulierte KI-Antwort)
    daten2 = {**daten1, "ki_antwort": "think: MetallSortierer testen | eat: Brot essen | spazieren: Sonne geniessen"}
    print("Runde 2:", json.dumps(neuer_tag(daten2), ensure_ascii=False, indent=2))

    # 3. Test MetallSortierer
    sorter = MetallSortierer()
    test_teile = [
        {"id": 1, "material": "Stahl Schraube", "masse_g": 78.5, "volumen_cm3": 10.0, "lagerort": "Regal A"},
        {"id": 2, "material": "Aluminium Profil", "masse_g": 27.0, "volumen_cm3": 10.0, "lagerort": "Boden Karton"},
        {"id": 3, "material": "Kupfer Rohr", "masse_g": 89.6, "volumen_cm3": 10.0, "lagerort": "Ecke hinten"},
        {"id": 4, "material": "Edelstahl V2A", "lagerort": "Regal B"},
        {"id": 5, "material": "Messing Ventil", "masse_g": 85.0, "volumen_cm3": 10.0, "lagerort": "Kiste"},
    ]
    ergebnis = sorter.sortiere(test_teile)
    print("Sortierer:", json.dumps(sorter.get_ergebnis(), ensure_ascii=False, indent=2))