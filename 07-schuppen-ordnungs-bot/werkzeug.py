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
            return any(m in material for m in ["eisen", "stahl", "ferro", "guss"])
        except Exception:
            return False
    
    def funken_test(self, teil: dict) -> str:
        """Simuliert Funkenbild-Test. Gibt Kategorie zurück: 'stahl', 'edelstahl', 'guss', 'keine', 'unbekannt'."""
        try:
            material = str(teil.get("material", "")).lower()
            if "edelstahl" in material or "v2a" in material or "v4a" in material:
                return "edelstahl"  # Wenig, kurze, gabelnde Funken
            if "stahl" in material or "eisen" in material:
                return "stahl"      # Viele, lange, gelbe Funken
            if "guss" in material:
                return "guss"       # Kurze, rote Funken
            if any(m in material for m in ["aluminium", "kupfer", "messing", "bronze", "zink", "titan"]):
                return "keine"      # Keine Funken
            return "unbekannt"
        except Exception:
            return "unbekannt"
    
    def dichte_test(self, teil: dict) -> float | None:
        """Berechnet Dichte aus Gewicht (g) und Volumen (cm³). None bei Fehler."""
        try:
            gewicht = float(teil.get("gewicht_g", 0))
            volumen = float(teil.get("volumen_cm3", 0))
            if gewicht <= 0 or volumen <= 0:
                return None
            return round(gewicht / volumen, 2)
        except (ValueError, TypeError, ZeroDivisionError):
            return None
    
    def _dichte_match(self, dichte: float, material_hinweis: str) -> str:
        """Vergleicht gemessene Dichte mit Tabelle. Gibt bestes Match zurück."""
        if dichte is None:
            return "unbekannt"
        
        # Erst schauen, was der Hinweis sagt (Priorität)
        hinweis = material_hinweis.lower()
        for name, ziel in self.DICHTEN.items():
            if name in hinweis:
                if abs(dichte - ziel) / ziel <= self.DICHTE_TOLERANZ:
                    return name
        
        # Sonst bestes Match aus Tabelle
        best_match = "unbekannt"
        min_diff = float('inf')
        for name, ziel in self.DICHTEN.items():
            diff = abs(dichte - ziel) / ziel
            if diff < min_diff and diff <= self.DICHTE_TOLERANZ:
                min_diff = diff
                best_match = name
        return best_match
    
    def material_pruefung(self, teil: dict) -> dict:
        """Führt alle Tests durch, gibt Dict mit Ergebnissen zurück."""
        ergebnis = {
            "magnetisch": False,
            "funken": "unbekannt",
            "dichte": None,
            "dichte_match": "unbekannt",
            "verdaechtig": False
        }
        try:
            ergebnis["magnetisch"] = self.magnet_test(teil)
            ergebnis["funken"] = self.funken_test(teil)
            ergebnis["dichte"] = self.dichte_test(teil)
            ergebnis["dichte_match"] = self._dichte_match(ergebnis["dichte"], str(teil.get("material", "")))
            
            # Kakerlaken-Check: Teile, die in verdächtigen Kartons lagen
            if teil.get("fundort", "").lower() in ["karton_ecke", "feuchte_ecke", "alter_karton"]:
                ergebnis["verdaechtig"] = True
        except Exception:
            pass
        return ergebnis
    
    def sortiere(self, teile: List[dict]):
        """Hauptsortierung: Verteilt Teile auf Kategorien."""
        self.reset()
        for teil in teile:
            try:
                if not isinstance(teil, dict):
                    continue
                
                pruef = self.material_pruefung(teil)
                kategorie = "schrott"
                
                # Kakerlaken-Verdacht hat Vorrang
                if pruef["verdaechtig"]:
                    kategorie = "kakerlaken_verdaechtig"
                # Logik: Magnet + Funken + Dichte
                elif pruef["magnetisch"]:
                    if pruef["funken"] == "edelstahl" or pruef["dichte_match"] == "edelstahl":
                        kategorie = "edelstahl"
                    else:
                        kategorie = "eisenhaltig"
                elif pruef["dichte_match"] in ["aluminium", "aluminiumlegierung", "magnesium", "titan"]:
                    kategorie = "aluminium"
                elif pruef["dichte_match"] == "kupfer":
                    kategorie = "kupfer"
                elif pruef["dichte_match"] in ["messing", "bronze"]:
                    kategorie = "messing"
                elif pruef["dichte_match"] != "unbekannt":
                    kategorie = "sonstiges"
                
                self.kategorien[kategorie].append(_json_sicher(teil))
            except Exception:
                self.kategorien["schrott"].append(_json_sicher(teil))
    
    def get_ergebnis(self) -> dict:
        """Liefert sortiertes Ergebnis als JSON-sicheres Dict."""
        return _json_sicher(self.kategorien)