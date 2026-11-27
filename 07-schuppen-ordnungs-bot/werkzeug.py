def neuer_tag(daten):
    """
    Entscheidungslogik für einen neuen Tag im Schuppen.
    Nimmt Status-Dict, gibt Plan-Dict zurück.
    """
    gestern = daten.get("gestern", {})
    fehlschlaege = daten.get("fehlschlaege", {})
    stimmung = daten.get("stimmung", 0)
    wetter = daten.get("wetter", "bewoelkt").lower()
    kakerlaken_level = daten.get("kakerlaken_level", 0)
    
    notiz = ""
    plan = []
    
    if "ki_antwort" in daten and daten["ki_antwort"]:
        notiz = (notiz + " | " if notiz else "") + f"KI rät: {daten['ki_antwort'][:100]}"
    
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

def validiere_dateipfad(pfad: str, basis_verzeichnis: str = ".") -> str:
    """
    Prüft Pfad auf Directory Traversal und normalisiert ihn.
    Gibt absoluten Pfad zurück, wenn er sicher unter basis_verzeichnis liegt.
    Wirft ValueError bei Unsicherheit.
    """
    if not pfad or not isinstance(pfad, str):
        raise ValueError("Pfad leer oder ungültig")
    abs_basis = os.path.abspath(basis_verzeichnis)
    abs_ziel = os.path.abspath(os.path.join(abs_basis, pfad))
    if not abs_ziel.startswith(abs_basis):
        raise ValueError(f"Pfad führt aus Basis raus: {pfad}")
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
            "kakerlaken_verdaechtig": []
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
        """Simuliert Funkenbild-Test."""
        mat = teil.get("material", "").lower()
        if "edelstahl" in mat: return "edelstahl"
        if "guss" in mat: return "gusseisen"
        return "unbekannt"

    def gewicht_test(self, teil: dict) -> float:
        """Dichte-Abschätzung über Gewicht/Volumen in g/cm³."""
        gewicht = teil.get("gewicht_g", 0.0)
        volumen = teil.get("volumen_cm3", 1.0)
        if volumen <= 0:
            return 0.0
        return gewicht / volumen

    def farbe_test(self, teil: dict) -> str:
        """Prüft die äußere Farbe des Fundstücks."""
        return teil.get("farbe", "unbekannt").lower()

    def kakerlaken_check(self, teil: dict) -> bool:
        """Checkt ob Spuren von Krabbeltieren dran sind."""
        return teil.get("kakerlaken_spuren", False)

    def sortiere_metall(self, teile_liste: list):
        """Sortiert eine Liste von Schrottteilen in die Kategorien ein."""
        self.reset()
        for teil in teile_liste:
            if self.kakerlaken_check(teil):
                self.kategorien["kakerlaken_verdaechtig"].append(teil)
                continue

            dichte = self.gewicht_test(teil)
            farbe = self.farbe_test(teil)
            ist_magnetisch = self.magnet_test(teil)

            if ist_magnetisch:
                if "edelstahl" in self.funken_test(teil):
                    self.kategorien["edelstahl"].append(teil)
                else:
                    self.kategorien["eisenhaltig"].append(teil)
            else:
                if farbe in ["kupferfarben", "rotgold"] or (7.8 <= dichte <= 9.2):
                    self.kategorien["kupfer"].append(teil)
                elif farbe in ["messingfarben", "gelbgold"] or (8.4 <= dichte <= 8.8):
                    self.kategorien["messing"].append(teil)
                elif (2.5 <= dichte <= 2.9) or "alu" in teil.get("material", "").lower():
                    self.kategorien["aluminium"].append(teil)
                else:
                    self.kategorien["sonstiges"].append(teil)

    def speichern_als_json(self, dateipfad: str, basis_verzeichnis: str = "."):
        """Speichert das Sortierergebnis sicher als JSON."""
        sicherer_pfad = validiere_dateipfad(dateipfad, basis_verzeichnis)
        with open(sicherer_pfad, "w", encoding="utf-8") as f:
            json.dump(self.kategorien, f, indent=2, ensure_ascii=False)