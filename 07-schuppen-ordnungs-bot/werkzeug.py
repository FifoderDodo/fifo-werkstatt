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
            material_hinweis = str(teil.get("material", "")).lower()
            # Starke Magnete ziehen Eisen, Stahl, Guss. Nicht Edelstahl (meist), Alu, Kupfer.
            ferro_keywords = ["eisen", "stahl", "guss", "ferro", "guß"]
            # Edelstahl ist oft schwach/non-magnetisch (Austenit), aber Martensit/Ferrit zieht.
            # Wir vereinfachen: Wenn 'edelstahl' im Namen, dann False (unsicher).
            if "edelstahl" in material_hinweis:
                return False 
            return any(kw in material_hinweis for kw in ferro_keywords)
        except Exception:
            return False
    
    def funken_test(self, teil: dict) -> str:
        """Simuliert Funkenbild-Test. Gibt Farb-Kategorie zurück."""
        try:
            material_hinweis = str(teil.get("material", "")).lower()
            if any(k in material_hinweis for k in ["stahl", "eisen", "guss", "ferro", "guß"]):
                if "edelstahl" in material_hinweis:
                    return "weiss_gelb_kurz" # Edelstahl Funken
                return "gelb_weiss_lang" # Stahl/Eisen Funken
            if any(k in material_hinweis for k in ["kupfer", "messing", "bronze", "rotguß"]):
                return "keine_funken" # NE-Metalle funken nicht
            if any(k in material_hinweis for k in ["aluminium", "alu", "magnesium", "titan"]):
                return "keine_funken"
            return "unbekannt"
        except Exception:
            return "fehler"
    
    def _dichte_match(self, gemessen: float, referenz: float) -> bool:
        """Prüft ob gemessene Dichte zur Referenz passt (relative Toleranz)."""
        if referenz <= 0 or gemessen <= 0:
            return False
        abweichung = abs(gemessen - referenz) / referenz
        return abweichung <= self.DICHTE_TOLERANZ
    
    def dichte_test(self, teil: dict) -> str:
        """Ermittelt Material anhand Dichte. Priorisiert Hinweis vor blindem Match."""
        try:
            masse = float(teil.get("masse_g", 0))
            volumen = float(teil.get("volumen_cm3", 0))
            if masse <= 0 or volumen <= 0:
                return "unbekannt"
            
            gemessen = masse / volumen
            material_hinweis = str(teil.get("material", "")).lower()
            
            # 1. Prüfen ob Hinweis in Tabelle existiert und passt
            for name, ref_dichte in self.DICHTEN.items():
                if name in material_hinweis:
                    if self._dichte_match(gemessen, ref_dichte):
                        return name
            
            # 2. Blinder Match: Bestes Match aus Tabelle
            best_match = "unbekannt"
            min_diff = float('inf')
            for name, ref_dichte in self.DICHTEN.items():
                if self._dichte_match(gemessen, ref_dichte):
                    diff = abs(gemessen - ref_dichte) / ref_dichte
                    if diff < min_diff:
                        min_diff = diff
                        best_match = name
            return best_match
        except (ValueError, TypeError, ZeroDivisionError):
            return "unbekannt"
    
    def material_pruefung(self, teil: dict) -> dict:
        """Führt alle Tests durch und gibt Dict mit Ergebnissen zurück."""
        magnetisch = self.magnet_test(teil)
        funken = self.funken_test(teil)
        dichte_est = self.dichte_test(teil)
        
        return {
            "magnetisch": magnetisch,
            "funken_typ": funken,
            "dichte_schaetzung": dichte_est,
            "original_hinweis": str(teil.get("material", "")).lower()
        }
    
    def sortiere(self, teile_liste: List[dict]):
        """Sortiert Liste von Teilen in self.kategorien ein."""
        self.reset()
        for teil in teile_liste:
            if not isinstance(teil, dict):
                self.kategorien["schrott"].append(_json_sicher(teil))
                continue
            
            # Kakerlaken-Check (Spass/Logik)
            if teil.get("kakerlaken_spuren", False) or "kakerlake" in str(teil.get("notiz", "")).lower():
                self.kategorien["kakerlaken_verdaechtig"].append(_json_sicher(teil))
                continue
            
            erg = self.material_pruefung(teil)
            dichte_key = erg["dichte_schaetzung"]
            magnet = erg["magnetisch"]
            
            # Entscheidungslogik
            kat = "schrott"
            
            if dichte_key in ["eisen", "stahl", "guss", "ferro", "guß"] and magnet:
                kat = "eisenhaltig"
            elif dichte_key == "edelstahl" and not magnet: # Austenitisch
                kat = "edelstahl"
            elif dichte_key == "edelstahl" and magnet: # Martensitisch/Ferritisch -> eher eisenhaltig behandeln aber Kennzeichnung
                kat = "edelstahl" 
            elif dichte_key in ["aluminium", "aluminiumlegierung", "magnesium", "titan"]:
                kat = "aluminium"
            elif dichte_key == "kupfer":
                kat = "kupfer"
            elif dichte_key in ["messing", "bronze", "zink", "zinn", "blei"]:
                kat = "messing" # Sammelkategorie für NE-Schwer
            elif dichte_key != "unbekannt":
                kat = "sonstiges"
            else:
                # Fallback über Magnet/Funken wenn Dichte fehlschlug
                if magnet and erg["funken_typ"] == "gelb_weiss_lang":
                    kat = "eisenhaltig"
                elif not magnet and erg["funken_typ"] == "keine_funken":
                    kat = "sonstiges" # Wahrscheinlich Alu/Kupfer aber Dichte unbekannt
                else:
                    kat = "schrott"
            
            self.kategorien[kat].append(_json_sicher(teil))
    
    def get_ergebnis(self) -> dict:
        """Gibt sortiertes Ergebnis als JSON-sicheres Dict zurück."""
        return {k: _json_sicher(v) for k, v in self.kategorien.items()}