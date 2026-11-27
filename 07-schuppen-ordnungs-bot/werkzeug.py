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
    
    def magnet_test(self, teil):
        """Simuliert Magnet-Test. True = ferromagnetisch (Eisen/Stahl)."""
        material = teil.get("material", "").lower()
        return any(m in material for m in ["eisen", "stahl", "ferro"])
    
    def funken_test(self, teil):
        """Simuliert Funkenbild-Test (Grobe Klassifikation)."""
        # Platzhalter: In echt bräuchte man Funkenbild-Atlas.
        # Hier nur Mock basierend auf Material-String falls vorhanden.
        mat = teil.get("material", "").lower()
        if "edelstahl" in mat: return "edelstahl"
        if "guss" in mat: return "gusseisen"
        return "unbekannt"
    
    def gewicht_test(self, teil):
        """Dichte-Abschätzung über Gewicht/Volumen. Gibt Dichte in g/cm³ zurück."""
        gewicht = teil.get("gewicht_g", 0)
        volumen = teil.get("volumen_cm3", 1)
        return gewicht / volumen if volumen > 0 else 0.0
    
    def check_kakerlaken_gefahr(self, teil):
        """Prüft ob Teil aus verseuchter Zone kommt (Position/Notiz)."""
        ort = teil.get("fundort", "").lower()
        notiz = teil.get("notiz", "").lower()
        gefahr_woerter = ["ecke", "karton", "dunkel", "feucht", "hinter", "boden", "nest"]
        return any(w in ort or w in notiz for w in gefahr_woerter)
    
    def sortiere_metall(self, teile_liste):
        """Hauptlogik: Iteriert Teile, sortiert in Kategorien."""
        self.reset()
            
        for teil in teile_liste:
            if not isinstance(teil, dict):
                self.kategorien["schrott"].append({"objekt": teil, "grund": "Kein Dict"})
                continue
            
            name = teil.get("name", "Unbekannt")
            farbe = teil.get("farbe", "").lower()
            dichte = self.gewicht_test(teil)
            material_hinweis = teil.get("material", "").lower()
            magnetisch = self.magnet_test(teil)
            
            # Kakerlaken-Check: Teile markieren, aber normal weiter sortieren
            kakerlaken_verdaechtig = self.check_kakerlaken_gefahr(teil)
            if kakerlaken_verdaechtig:
                teil["kakerlaken_warnung"] = True
                # Kopie in Warn-Kategorie für Übersicht
                self.kategorien["kakerlaken_verdaechtig"].append(teil.copy())
            
            # Entscheidungsbaum: Erst Magnet, dann Dichte/Farbe
            if magnetisch:
                # Ferromagnetisch: Eisen, Stahl, Gusseisen, magnetischer Edelstahl
                funken = self.funken_test(teil)
                if funken == "edelstahl" or "edelstahl" in material_hinweis:
                    self.kategorien["edelstahl"].append(teil)
                elif funken == "gusseisen" or dichte > 7.2:
                    self.kategorien["eisenhaltig"].append(teil)  # Gusseisen landet hier
                else:
                    self.kategorien["eisenhaltig"].append(teil)  # Standard Stahl/Eisen
            else:
                # Nicht magnetisch: Alu, Kupfer, Messing, Austenitischer Edelstahl, Zink, Blei
                if dichte < 3.0:
                    # Leichtmetall -> Aluminium (ca 2.7) oder Magnesium (1.7)
                    if "weiss" in farbe or "silber" in farbe or "grau" in farbe:
                        self.kategorien["aluminium"].append(teil)
                    else:
                        self.kategorien["sonstiges"].append(teil)
                elif 8.0 <= dichte <= 9.0:
                    # Schwermetalle: Kupfer (8.9), Messing (8.4-8.7), Bronze
                    if "rot" in farbe or "orange" in farbe or "kupfer" in material_hinweis:
                        self.kategorien["kupfer"].append(teil)
                    elif "gelb" in farbe or "gold" in farbe or "messing" in material_hinweis:
                        self.kategorien["messing"].append(teil)
                    else:
                        self.kategorien["kupfer"].append(teil)  # Default Kupfer-Gruppe
                elif 7.7 <= dichte <= 8.1:
                    # Austenitischer Edelstahl (ca 7.9) oder Nickel
                    if "edelstahl" in material_hinweis or "rostfrei" in material_hinweis:
                        self.kategorien["edelstahl"].append(teil)
                    else:
                        self.kategorien["sonstiges"].append(teil)
                else:
                    # Alles andere (Blei, Zink, Zinn, Unknown)
                    self.kategorien["sonstiges"].append(teil)
        
        return self.kategorien

    def get_bericht(self):
        """Gibt Text-Zusammenfassung der Sortierung zurück."""
        lines = ["=== Schuppen-Metall-Bericht ==="]
        total = 0
        for kat, teile in self.kategorien.items():
            anzahl = len(teile)
            total += anzahl
            if anzahl > 0:
                lines.append(f"{kat.capitalize()}: {anzahl} Stück")
                # Zeige erste 3 Namen als Beispiel
                beispiele = [t.get('name', '?') for t in teile[:3]]
                lines.append(f"  z.B.: {', '.join(beispiele)}")
        lines.append(f"---\nGesamt: {total} Teile sortiert.")
        if self.kategorien["kakerlaken_verdaechtig"]:
            lines.append("!!! VORSICHT: Kakerlaken-verdächtige Teile gefunden! Handschuhe waschen. !!!")
        return "\n".join(lines)

    def export_kategorien(self):
        """Gibt Dict zurück für JSON-Speicherung oder Weiterverarbeitung."""
        # Deepcopy wäre sauberer, aber Stdlib only -> dict comprehension
        return {k: [dict(t) for t in v] for k, v in self.kategorien.items()}


if __name__ == "__main__":
    # Testlauf für neuen Tag
    print("--- Test neuer_tag ---")
    test_daten_1 = {
        "gestern": {"think": 12, "eat": 3},
        "fehlschlaege": {"schrott_suchen": 2},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 2
    }
    erg1 = neuer_tag(test_daten_1)
    print(f"Notiz: {erg1['notiz']}")
    print(f"Plan: {erg1['plan']}")
    
    test_daten_2 = {
        "gestern": {"am_projekt_arbeiten": 4},
        "fehlschlaege": {"am_projekt_arbeiten": 3},
        "stimmung": -10,
        "wetter": "regen",
        "kakerlaken_level": 8
    }
    erg2 = neuer_tag(test_daten_2)
    print(f"Notiz: {erg2['notiz']}")
    print(f"Plan: {erg2['plan']}")

    # Testlauf MetallSortierer
    print("\n--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Rostiger Nagel", "material": "Eisen", "gewicht_g": 10, "volumen_cm3": 1.3, "fundort": "Boden links", "farbe": "braun"},
        {"name": "Blanker Schrauben", "material": "Stahl", "gewicht_g": 50, "volumen_cm3": 6.4, "fundort": "Regal", "farbe": "silber"},
        {"name": "Alu-Profil", "material": "Aluminium", "gewicht_g": 300, "volumen_cm3": 111, "fundort": "Ecke hinten", "farbe": "silber"},
        {"name": "Kupferrohr", "material": "Kupfer", "gewicht_g": 500, "volumen_cm3": 56, "fundort": "Karton oben", "farbe": "rot"},
        {"name": "Messing-Ventil", "material": "Messing", "gewicht_g": 200, "volumen_cm3": 23, "fundort": "Werkbank", "farbe": "gold"},
        {"name": "Edelstahl-Schraube", "material": "Edelstahl V2A", "gewicht_g": 20, "volumen_cm3": 2.5, "fundort": "Schublade", "farbe": "silber"},
        {"name": "Guss-Eisenstück", "material": "Gusseisen", "gewicht_g": 1000, "volumen_cm3": 128, "fundort": "Dunkle Ecke", "farbe": "grau"},
        {"name": "Unbekanntes Teil", "material": "", "gewicht_g": 50, "volumen_cm3": 10, "fundort": "Mitte", "farbe": "weiss"},
        "Fehlerhafter Eintrag",  # String statt Dict -> Schrott
    ]
    
    ergebnis = sorter.sortiere_metall(test_teile)
    print(sorter.get_bericht())
    
    # Export Test
    export = sorter.export_kategorien()
    print(f"\nExport Keys: {list(export.keys())}")
    print(f"Kakerlaken Warnungen: {len(export['kakerlaken_verdaechtig'])}")