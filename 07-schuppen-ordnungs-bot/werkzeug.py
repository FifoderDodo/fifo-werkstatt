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
            return any(m in material for m in ["eisen", "stahl", "ferro", "guss"])
        except Exception:
            return False
    
    def funken_test(self, teil: dict) -> str:
        """Simuliert Funkenbild-Test mit hartem Fallback."""
        try:
            mat = str(teil.get("material", "")).lower()
            if "edelstahl" in mat: 
                return "edelstahl"
            if "guss" in mat: 
                return "gusseisen"
            if "stahl" in mat: 
                return "stahl"
            if "eisen" in mat: 
                return "eisen"
            return "keine_funken"
        except Exception:
            return "fehler"
    
    def dichte_test(self, teil: dict) -> float:
        """Simuliert Dichte-Messung (Archimedes). Gibt geschätzte Dichte zurück."""
        try:
            mat = str(teil.get("material", "")).lower()
            # Suche passenden Schlüssel in DICHTEN
            for key, val in self.DICHTEN.items():
                if key in mat:
                    # Etwas Rauschen simulieren
                    return round(val * (1 + (hash(str(teil)) % 100 - 50) / 10000), 2)
            # Fallback: Masse/Volumen wenn vorhanden, sonst 0.0
            masse = float(teil.get("masse_g", 0))
            vol = float(teil.get("volumen_cm3", 0))
            if vol > 0:
                return round(masse / vol, 2)
            return 0.0
        except Exception:
            return 0.0
    
    def material_pruefung(self, teil: dict) -> str:
        """Kombiniert Tests zu einer Kategorie."""
        try:
            magnet = self.magnet_test(teil)
            funken = self.funken_test(teil)
            dichte = self.dichte_test(teil)
            mat = str(teil.get("material", "")).lower()
            
            # Kakerlaken-Check (Easteregg/Feature)
            if teil.get("kakerlaken_spuren", False) or "kot" in mat or "nest" in mat:
                return "kakerlaken_verdaechtig"
            
            # Logik: Magnet + Funken + Dichte
            if magnet:
                if "edelstahl" in funken or dichte > 7.7: # Edelstahl oft schwach magnetisch oder nicht, aber Dichte hoch
                    # Unterschied Edelstahl/Stahl über Funken/Dichte
                    if "edelstahl" in mat or funken == "edelstahl":
                        return "edelstahl"
                    return "eisenhaltig"
                return "eisenhaltig"
            
            # Nicht magnetisch
            if dichte > 8.0: # Kupfer, Messing, Bronze, Blei
                if "kupfer" in mat or "cu" in mat:
                    return "kupfer"
                if "messing" in mat or "ms" in mat:
                    return "messing"
                if "bronze" in mat:
                    return "sonstiges" # Bronze separat? Geht nach sonstiges.
                if "blei" in mat:
                    return "schrott" # Blei ist Sondermüll
                return "kupfer" # Default für schweres NE-Metall
            
            if 2.5 < dichte < 3.0: # Aluminium, Magnesium, Titan
                if "alu" in mat or "aluminium" in mat:
                    return "aluminium"
                if "titan" in mat:
                    return "sonstiges"
                if "magnesium" in mat:
                    return "sonstiges"
                return "aluminium" # Default leicht
            
            if dichte > 0:
                return "sonstiges"
            
            return "schrott" # Unbekannt, keine Daten
        except Exception:
            return "schrott"
    
    def sortiere(self, teile: List[dict]) -> Dict[str, List[dict]]:
        """Hauptmethode: sortiert Liste von Teilen in self.kategorien."""
        self.reset()
        if not isinstance(teile, list):
            return _json_sicher(self.kategorien)
        
        for teil in teile:
            if not isinstance(teil, dict):
                continue
            kat = self.material_pruefung(teil)
            if kat in self.kategorien:
                self.kategorien[kat].append(_json_sicher(teil))
            else:
                self.kategorien["schrott"].append(_json_sicher(teil))
        
        return _json_sicher(self.kategorien)
    
    def get_ergebnis(self) -> Dict[str, List[dict]]:
        """Gibt aktuellen Stand JSON-sicher zurück."""
        return _json_sicher(self.kategorien)