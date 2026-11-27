def neuer_tag(daten):
    """
    Entscheidungslogik für einen neuen Tag im Schuppen.
    Nimmt Status-Dict, gibt Plan-Dict zurück.
    """
    try:
        gestern = daten.get("gestern", {})
        fehlschlaege = daten.get("fehlschlaege", {})
        stimmung = int(daten.get("stimmung", 0))
        wetter = str(daten.get("wetter", "bewoelkt")).lower()
        kakerlaken_level = int(daten.get("kakerlaken_level", 0))
    except (ValueError, TypeError) as e:
        return {"notiz": f"Fehlerhafte Eingabedaten: {e}", "plan": []}

    notiz = ""
    plan = []
    
    if "ki_antwort" in daten and daten["ki_antwort"]:
        notiz = (notiz + " | " if notiz else "") + f"KI rät: {str(daten['ki_antwort'])[:100]}"
    
    if kakerlaken_level >= 7:
        notiz = "Achtung: Starke Kakerlaken-Aktivität! Erst Abwehr, dann Sortieren."
        plan.append({"aktion": "walk_to", "text": "Giftschrank holen: Sprühgift & Köder"})
        plan.append({"aktion": "nachsehen", "text": "Ecken, Kartons & Ritzen absprühen"})
        if len(plan) >= 2:
            plan.append({"aktion": "spazieren", "text": "Lüften & Kopf freibekommen nach Gift"})
        return {"notiz": notiz[:200], "plan": plan[:3]}
    elif kakerlaken_level >= 4:
        notiz = "Kakerlaken verdächtig. Checken bevor ich Metall anfasse."
        plan.append({"aktion": "nachsehen", "text": "Dunkle Ecken & alte Kartons kontrollieren"})
    
    if len(plan) < 3:
        if stimmung < -50:
            notiz = (notiz + " | " if notiz else "") + "Stimmung im Keller. Erst frische Luft schnappen."
            plan.append({"aktion": "spazieren", "text": "Kopf freibekommen vor dem Schuppen"})
        elif stimmung < 20:
            notiz = notiz or "Laune mittelmäßig. Kaffee wäre gut."
            plan.append({"aktion": "drink", "text": "Wasser oder Kaffee trinken"})
    
    if wetter in ["sonnig", "heiter"] and len(plan) < 3:
        if "spazieren" not in [p["aktion"] for p in plan]:
            if not plan or plan[-1]["aktion"] != "spazieren":
                 plan.append({"aktion": "spazieren", "text": "Gutes Wetter nutzen, kurz raus"})
    
    if len(plan) < 3 and stimmung > -70 and kakerlaken_level < 7:
        fehlschlaege_projekt = fehlschlaege.get("am_projekt_arbeiten", 0)
        
        if fehlschlaege_projekt > 3 and "ki_antwort" not in daten:
            return {"frage_an_ki": f"Projekt 'MetallSortierer' klemmt (Fehlschläge: {fehlschlaege_projekt}). Was ist der häufigste Grund, warum Magnet/Dichte-Tests in Python-Simulationen fehlschlagen? Kurz."}
        
        if fehlschlaege_projekt > 2:
            notiz = (notiz + " | " if notiz else "") + "Projekt klemmt. Erst nachdenken, dann coden."
            plan.append({"aktion": "think", "text": "Sortierlogik für Metallteile durchdenken"})
        else:
            notiz = notiz or "Ran an den Speck: Schuppen-Bot Grundstruktur fertig, polieren."
            plan.append({"aktion": "am_projekt_arbeiten", "text": "werkzeug.py: MetallSortierer verfeinern und testen"})
    
    if len(plan) >= 2 and len(plan) < 3 and "eat" not in [p["aktion"] for p in plan]:
        plan.append({"aktion": "eat", "text": "Frühstück machen"})
    
    plan = plan[:3]
    
    return {
        "notiz": notiz[:200],
        "plan": plan
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
            # Ferromagnetisch: Eisen, Stahl, Guss, Ferro
            ferro_keys = ["eisen", "stahl", "guss", "ferro"]
            # Edelstahl ist oft schwach/non-magnetisch (Austenitisch), hier: False
            if any(k in material for k in ferro_keys):
                # Zufallskomponente für Realismus (Schmutz, Legierung)
                return True
            return False
        except Exception:
            return False
    
    def funken_test(self, teil: dict) -> str:
        """Simuliert Funkenbild-Test. Gibt Kategorie-Hinweis zurück."""
        try:
            material = str(teil.get("material", "")).lower()
            if "stahl" in material or "eisen" in material or "guss" in material:
                if "edel" in material:
                    return "edelstahl"  # Wenige, kurze, rote Funken
                elif "guss" in material:
                    return "guss"        # Keine Funken, nur Glühen
                return "stahl"           # Viele, lange, gelbe/weiße Funken mit Verzweigung
            elif "kupfer" in material or "messing" in material or "bronze" in material:
                return "kupfer_leg"      # Keine Funken, grün/blau Flamme
            elif "aluminium" in material or "magnesium" in material:
                return "aluminium"       # Keine Funken, weiße Flamme
            return "unbekannt"
        except Exception:
            return "fehler"
    
    def dichte_test(self, teil: dict) -> float:
        """Berechnet Dichte aus Masse/Volumen. Fallback auf Material-Schätzung."""
        try:
            masse = float(teil.get("masse_g", 0))
            volumen = float(teil.get("volumen_cm3", 0))
            if masse > 0 and volumen > 0:
                return masse / volumen
        except (ValueError, TypeError, ZeroDivisionError):
            pass
        # Fallback: Material-Namen basiert
        material = str(teil.get("material", "")).lower()
        for key, density in self.DICHTEN.items():
            if key in material:
                return density
        return 0.0
    
    def _dichte_match(self, gemessen: float, ziel_dichte: float) -> bool:
        """Prüft ob gemessene Dichte im Toleranzbereich liegt."""
        if gemessen <= 0 or ziel_dichte <= 0:
            return False
        diff = abs(gemessen - ziel_dichte) / ziel_dichte
        return diff <= self.DICHTE_TOLERANZ
    
    def material_pruefung(self, teil: dict) -> str:
        """Führt Tests durch und gibt wahrscheinlichste Kategorie zurück."""
        magnetisch = self.magnet_test(teil)
        funken = self.funken_test(teil)
        dichte = self.dichte_test(teil)
        
        # Kakerlaken-Check (Easteregg / Feature)
        if teil.get("kakerlaken_spuren", False):
            return "kakerlaken_verdaechtig"
        
        # Logik-Baum
        if magnetisch:
            if funken == "edelstahl" or self._dichte_match(dichte, self.DICHTEN["edelstahl"]):
                return "edelstahl"
            if funken == "guss" or self._dichte_match(dichte, self.DICHTEN["guss"]):
                return "eisenhaltig" # Guss landet bei Eisenhaltig/Schrott
            return "eisenhaltig"
        
        # Nicht magnetisch
        if funken == "kupfer_leg":
            if self._dichte_match(dichte, self.DICHTEN["kupfer"]):
                return "kupfer"
            if self._dichte_match(dichte, self.DICHTEN["messing"]) or self._dichte_match(dichte, self.DICHTEN["bronze"]):
                return "messing"
            # Fallback Kupfer-Legierung
            return "kupfer"
        
        if funken == "aluminium":
            if self._dichte_match(dichte, self.DICHTEN["aluminium"]) or self._dichte_match(dichte, self.DICHTEN["magnesium"]):
                return "aluminium"
            return "aluminium" # Auch wenn Dichte nicht passt, Funkenbild stark
        
        # Dichte-basiert falls Funken unklar
        if self._dichte_match(dichte, self.DICHTEN["aluminium"]) or self._dichte_match(dichte, self.DICHTEN["magnesium"]):
            return "aluminium"
        if self._dichte_match(dichte, self.DICHTEN["kupfer"]):
            return "kupfer"
        if self._dichte_match(dichte, self.DICHTEN["messing"]) or self._dichte_match(dichte, self.DICHTEN["bronze"]):
            return "messing"
        if self._dichte_match(dichte, self.DICHTEN["zink"]) or self._dichte_match(dichte, self.DICHTEN["zinn"]) or self._dichte_match(dichte, self.DICHTEN["blei"]):
            return "sonstiges"
            
        return "schrott"
    
    def sortiere(self, teile: List[dict]) -> Dict[str, List[dict]]:
        """Hauptmethode: sortiert Liste von Teilen in self.kategorien."""
        self.reset()
        for teil in teile:
            if not isinstance(teil, dict):
                continue
            kat = self.material_pruefung(teil)
            if kat in self.kategorien:
                self.kategorien[kat].append(teil)
            else:
                self.kategorien["schrott"].append(teil)
        return self.kategorien
    
    def get_ergebnis(self) -> dict:
        """Liefert JSON-sicheres Ergebnis-Dict mit Counts und Details."""
        ergebnis = {}
        for kat, liste in self.kategorien.items():
            ergebnis[kat] = {
                "anzahl": len(liste),
                "teile": _json_sicher(liste)
            }
        return _json_sicher(ergebnis)