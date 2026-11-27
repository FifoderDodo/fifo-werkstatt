def neuer_tag(daten):
    """
    Entscheidungslogik für einen neuen Tag im Schuppen.
    Nimmt Status-Dict, gibt Plan-Dict zurück.
    """
    # Standardwerte falls Keys fehlen
    gestern = daten.get("gestern", {})
    fehlschlaege = daten.get("fehlschlaege", {})
    stimmung = daten.get("stimmung", 0)
    wetter = daten.get("wetter", "bewoelkt").lower()
    # Neu: Kakerlaken-Level 0-10 (0=keine, 10=Plage)
    kakerlaken_level = daten.get("kakerlaken_level", 0)
    
    notiz = ""
    plan = []
    
    # KI-Rat verarbeiten, falls vorhanden
    if "ki_antwort" in daten and daten["ki_antwort"]:
        notiz = (notiz + " | " if notiz else "") + f"KI rät: {daten['ki_antwort'][:100]}"
    
    # Kakerlaken-Abwehr hat Priorität, wenn Level hoch
    if kakerlaken_level >= 7:
        notiz = "Achtung: Starke Kakerlaken-Aktivität! Erst Abwehr, dann Sortieren."
        plan.append({"aktion": "walk_to", "text": "Giftschrank holen: Sprühgift & Köder"})
        plan.append({"aktion": "nachsehen", "text": "Ecken, Kartons & Ritzen absprühen"})
        # Bei Plage max 2 Aktionen dafür, dann Pause
        if len(plan) >= 2:
            plan.append({"aktion": "spazieren", "text": "Lüften & Kopf freibekommen nach Gift"})
            return {"notiz": notiz[:200], "plan": plan[:3]}
    elif kakerlaken_level >= 4:
        notiz = "Kakerlaken verdächtig. Checken bevor ich Metall anfasse."
        plan.append({"aktion": "nachsehen", "text": "Dunkle Ecken & alte Kartons kontrollieren"})
    
    # Erstmal Grundbedürfnisse prüfen (nur wenn nicht schon 3 Aktionen)
    if len(plan) < 3:
        if stimmung < -50:
            notiz = (notiz + " | " if notiz else "") + "Stimmung im Keller. Erst frische Luft schnappen."
            plan.append({"aktion": "spazieren", "text": "Kopf freibekommen vor dem Schuppen"})
        elif stimmung < 20:
            notiz = notiz or "Laune mittelmäßig. Kaffee wäre gut."
            plan.append({"aktion": "drink", "text": "Wasser oder Kaffee trinken"})
    
    # Wetter checken für Outdoor-Aktionen
    if wetter in ["sonnig", "heiter"] and len(plan) < 3:
        if "spazieren" not in [p["aktion"] for p in plan]:
            if not plan or plan[-1]["aktion"] != "spazieren":
                 plan.append({"aktion": "spazieren", "text": "Gutes Wetter nutzen, kurz raus"})
    
    # Projektarbeit: Metall-Sortierlogik basteln
    if len(plan) < 3 and stimmung > -70 and kakerlaken_level < 7:
        war_am_projekt = "am_projekt_arbeiten" in gestern
        fehlschlaege_projekt = fehlschlaege.get("am_projekt_arbeiten", 0)
        
        # Wenn Projekt oft scheitert, KI fragen (max 1x pro Tag)
        if fehlschlaege_projekt > 3 and "ki_antwort" not in daten:
            return {"frage_an_ki": f"Projekt 'MetallSortierer' klemmt (Fehlschläge: {fehlschlaege_projekt}). Was ist der häufigste Grund, warum Magnet/Dichte-Tests in Python-Simulationen fehlschlagen? Kurz."}
        
        if fehlschlaege_projekt > 2:
            notiz = (notiz + " | " if notiz else "") + "Projekt klemmt. Erst nachdenken, dann coden."
            plan.append({"aktion": "think", "text": "Sortierlogik für Metallteile durchdenken"})
        else:
            notiz = notiz or "Ran an den Speck: Schuppen-Bot Grundstruktur."
            plan.append({"aktion": "am_projekt_arbeiten", "text": "werkzeug.py: Sortierlogik Metall implementieren"})
    
    # Essen nicht vergessen, wenn lange Liste
    if len(plan) >= 2 and len(plan) < 3 and "eat" not in [p["aktion"] for p in plan]:
        plan.append({"aktion": "eat", "text": "Frühstück machen"})
    
    # Max 3 Aktionen
    plan = plan[:3]
    
    return {
        "notiz": notiz[:200],
        "plan": plan
    }


import json
import os
import re

def validiere_dateipfad(pfad: str, basis_verzeichnis: str = ".") -> str:
    """
    Prüft Pfad auf Directory Traversal und normalisiert ihn.
    Gibt absoluten Pfad zurück, wenn er sicher unter basis_verzeichnis liegt.
    Wirft ValueError bei Unsicherheit.
    """
    if not pfad or not isinstance(pfad, str):
        raise ValueError("Pfad leer oder ungültig")
    # Normalisieren (.. auflösen, symlinks ignorieren wir hier)
    abs_basis = os.path.abspath(basis_verzeichnis)
    abs_ziel = os.path.abspath(os.path.join(abs_basis, pfad))
    # Sicherheitscheck: Muss innerhalb Basis liegen
    if not abs_ziel.startswith(abs_basis):
        raise ValueError(f"Pfad führt aus Basis raus: {pfad}")
    # Verboten: Versteckte Systemdateien etc. (optional, hier locker)
    if re.search(r'[\x00-\x1f]', pfad):
        raise ValueError("Steuerzeichen im Pfad")
    return abs_ziel


class MetallSortierer:
    """
    Grundstruktur für die Metall-Sortierlogik im Schuppen-Bot.
    Nimmt Liste von Schrott-Teilen, gibt Kategorien zurück.
    """
    def __init__(self):
        self.kategorien = {
            "eisenhaltig": [],
            "edelstahl": [],
            "aluminium": [],
            "kupfer": [],
            "messing": [],
            "sonstiges": [],
            "schrott": [],
            "kakerlaken_verdaechtig": []  # Neu: Teile aus verseuchten Ecken
        }
    
    def reset(self):
        """Leert alle Kategorien für neuen Durchlauf."""
        for k in self.kategorien:
            self.kategorien[k] = []
    
    def magnet_test(self, teil: dict) -> bool:
        """Simuliert Magnet-Test. True = ferromagnetisch (Eisen/Stahl/Guss)."""
        material = teil.get("material", "").lower()
        return any(m in material for m in ["eisen", "stahl", "ferro", "guss"])
    
    def funken_test(self, teil: dict) -> str:
        """Simuliert Funkenbild-Test (Grobe Klassifikation)."""
        mat = teil.get("material", "").lower()
        if "edelstahl" in mat: return "edelstahl"
        if "guss" in mat: return "gusseisen"
        return "unbekannt"
    
    def gewicht_test(self, teil: dict) -> float:
        """Dichte-Abschätzung über Gewicht/Volumen. Gibt Dichte in g/cm³ zurück."""
        gewicht = teil.get("gewicht_g", 0)
        volumen = teil.get("volumen_cm3", 0)
        if volumen <= 0:
            # Fallback: Schätzung über typische Dichten falls Volumen fehlt
            mat = teil.get("material", "").lower()
            if "aluminium" in mat: return 2.7
            if "edelstahl" in mat or "stahl" in mat: return 7.9
            if "kupfer" in mat: return 8.96
            if "messing" in mat: return 8.5
            return 7.8 # Default Eisen
        return gewicht / volumen
    
    def farbe_test(self, teil: dict) -> str:
        """Einfache Farbprüfung für Kupfer/Messing/Alu."""
        farbe = teil.get("farbe", "").lower()
        if "rot" in farbe or "orange" in farbe: return "kupfer_verdaechtig"
        if "gelb" in farbe or "gold" in farbe: return "messing_verdaechtig"
        if "weiss" in farbe or "silber" in farbe or "grau" in farbe: return "hellmetall"
        return "dunkel"
    
    def kakerlaken_check(self, teil: dict, level: int) -> bool:
        """Prüft ob Fundort verseucht war."""
        if level < 4:
            return False
        fundort = teil.get("fundort", "").lower()
        return any(x in fundort for x in ["ecke", "karton", "ritze", "boden"])
    
    def sortiere_metall(self, teile: list, kakerlaken_level: int = 0) -> dict:
        """Hauptlogik: Sortiert Liste von Teilen in Kategorien."""
        self.reset()
        for teil in teile:
            # Kakerlaken-Check zuerst
            if self.kakerlaken_check(teil, kakerlaken_level):
                self.kategorien["kakerlaken_verdaechtig"].append(teil)
                continue
            
            magnetisch = self.magnet_test(teil)
            dichte = self.gewicht_test(teil)
            farbe = self.farbe_test(teil)
            funken = self.funken_test(teil)
            
            # Logik: Magnetisch -> Eisen/Stahl (außer Edelstahl oft nicht magnetisch)
            if magnetisch:
                if "edelstahl" in teil.get("material", "").lower() or funken == "edelstahl":
                    self.kategorien["edelstahl"].append(teil)
                else:
                    self.kategorien["eisenhaltig"].append(teil)
            # Nicht magnetisch: Dichte & Farbe
            else:
                if dichte < 3.5: # Alu ~2.7
                    self.kategorien["aluminium"].append(teil)
                elif dichte > 8.5: # Kupfer ~8.9, Messing ~8.5
                    if farbe == "kupfer_verdaechtig":
                        self.kategorien["kupfer"].append(teil)
                    elif farbe == "messing_verdaechtig":
                        self.kategorien["messing"].append(teil)
                    else:
                        self.kategorien["kupfer"].append(teil) # Default schwer
                elif dichte > 7.5: # Edelstahl Bereich
                    self.kategorien["edelstahl"].append(teil)
                else:
                    self.kategorien["sonstiges"].append(teil)
        
        # Schrott-Kategorie: Alles was kaputt/klein ist (Platzhalterlogik)
        # Hier einfach: wenn material 'schrott' enthält
        for kat in list(self.kategorien.keys()):
            self.kategorien[kat] = [t for t in self.kategorien[kat] if "schrott" not in t.get("material", "").lower()]
            # Die rausgefilterten landen in schrott (vereinfacht)
        
        return self.kategorien
    
    def speichern_als_json(self, pfad: str, basis_verzeichnis: str = ".") -> bool:
        """Speichert Kategorien als JSON, nutzt Pfadvalidierung."""
        try:
            sicherer_pfad = validiere_dateipfad(pfad, basis_verzeichnis)
            with open(sicherer_pfad, 'w', encoding='utf-8') as f:
                json.dump(self.kategorien, f, ensure_ascii=False, indent=2)
            return True
        except (ValueError, IOError, TypeError) as e:
            # Fehlerbehandlung: Einfach False zurück, Bot merkt sich in Notiz
            return False