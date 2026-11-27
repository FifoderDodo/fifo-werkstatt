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
            # Eisen, Stahl, Guss sind magnetisch. Edelstahl oft nicht (austenitisch).
            magnetisch_stichwoerter = ["eisen", "stahl", "guss", "ferro"]
            # Edelstahl explizit ausschließen, falls im String
            if "edelstahl" in material or "rostfrei" in material:
                return False
            return any(w in material for w in magnetisch_stichwoerter)
        except Exception:
            return False
    
    def funken_test(self, teil: dict) -> str:
        """Simuliert Funkenbild-Test. Gibt Kategorie-Hinweis zurück."""
        try:
            material = str(teil.get("material", "")).lower()
            if "edelstahl" in material or "rostfrei" in material:
                return "edelstahl"
            if any(w in material for w in ["eisen", "stahl", "guss", "ferro"]):
                return "eisenhaltig"
            if any(w in material for w in ["aluminium", "alu", "magnesium"]):
                return "aluminium"
            if "kupfer" in material:
                return "kupfer"
            if any(w in material for w in ["messing", "bronze"]):
                return "messing"
            return "unbekannt"
        except Exception:
            return "unbekannt"
    
    def dichte_test(self, teil: dict) -> float:
        """Berechnet Dichte aus Masse/Volumen. Gibt 0.0 bei Fehler."""
        try:
            masse = float(teil.get("masse_g", 0))
            volumen = float(teil.get("volumen_cm3", 0))
            if masse <= 0 or volumen <= 0:
                return 0.0
            return round(masse / volumen, 2)
        except (ValueError, TypeError, ZeroDivisionError):
            return 0.0
    
    def _dichte_match(self, dichte: float) -> List[str]:
        """Findet Material-Kandidaten basierend auf Dichte mit Toleranz."""
        if dichte <= 0:
            return []
        kandidaten = []
        for material, ref_dichte in self.DICHTEN.items():
            if ref_dichte == 0:
                continue
            abweichung = abs(dichte - ref_dichte) / ref_dichte
            if abweichung <= self.DICHTE_TOLERANZ:
                kandidaten.append(material)
        return kandidaten
    
    def material_pruefung(self, teil: dict) -> dict:
        """Führt alle Tests durch und gibt Dict mit Ergebnissen zurück."""
        magnetisch = self.magnet_test(teil)
        funken = self.funken_test(teil)
        dichte = self.dichte_test(teil)
        kandidaten = self._dichte_match(dichte)
        
        return {
            "magnetisch": magnetisch,
            "funken_typ": funken,
            "dichte": dichte,
            "dichte_kandidaten": kandidaten
        }
    
    def sortiere(self, teile: List[dict]) -> dict:
        """Sortiert Liste von Teilen in Kategorien."""
        self.reset()
        for teil in teile:
            if not isinstance(teil, dict):
                self.kategorien["schrott"].append({"fehler": "Kein Dict", "original": str(teil)[:50]})
                continue
            
            # Kakerlaken-Check: Teile, die verdächtig riechen oder aus dunklen Ecken kommen
            if teil.get("kakerlaken_verdaechtig", False):
                self.kategorien["kakerlaken_verdaechtig"].append(teil)
                continue
            
            pruef = self.material_pruefung(teil)
            kategorie = "schrott"  # Default
            
            # Priorität 1: Material-Hinweis aus Daten (falls verlässlich)
            material_hinweis = str(teil.get("material", "")).lower()
            if "edelstahl" in material_hinweis or "rostfrei" in material_hinweis:
                kategorie = "edelstahl"
            elif any(w in material_hinweis for w in ["eisen", "stahl", "guss", "ferro"]):
                kategorie = "eisenhaltig"
            elif any(w in material_hinweis for w in ["aluminium", "alu"]):
                kategorie = "aluminium"
            elif "kupfer" in material_hinweis:
                kategorie = "kupfer"
            elif any(w in material_hinweis for w in ["messing", "bronze"]):
                kategorie = "messing"
            # Priorität 2: Test-Logik
            elif pruef["magnetisch"]:
                if pruef["funken_typ"] == "edelstahl":
                    kategorie = "edelstahl"
                else:
                    kategorie = "eisenhaltig"
            elif pruef["funken_typ"] != "unbekannt":
                kategorie = pruef["funken_typ"]
            elif pruef["dichte_kandidaten"]:
                # Ersten passenden Kandidaten nehmen
                erster = pruef["dichte_kandidaten"][0]
                if erster in ["aluminium", "aluminiumlegierung", "magnesium"]:
                    kategorie = "aluminium"
                elif erster in ["stahl", "eisen", "guss", "ferro"]:
                    kategorie = "eisenhaltig"
                elif erster == "edelstahl":
                    kategorie = "edelstahl"
                elif erster == "kupfer":
                    kategorie = "kupfer"
                elif erster in ["messing", "bronze"]:
                    kategorie = "messing"
                else:
                    kategorie = "sonstiges"
            
            self.kategorien[kategorie].append(teil)
        
        return self.get_ergebnis()
    
    def get_ergebnis(self) -> dict:
        """Liefert JSON-sicheres Ergebnis mit Zusammenfassung."""
        ergebnis = {}
        gesamt = 0
        for kat, liste in self.kategorien.items():
            ergebnis[kat] = _json_sicher(liste)
            gesamt += len(liste)
        ergebnis["_meta"] = {
            "gesamt_teile": gesamt,
            "kategorien_gefunden": len([k for k, v in self.kategorien.items() if v])
        }
        return _json_sicher(ergebnis)