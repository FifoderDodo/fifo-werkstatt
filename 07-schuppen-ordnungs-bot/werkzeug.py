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
            
            # Kakerlaken-Check: Teile markieren, nicht automatisch wegwerfen
            if self.check_kakerlaken_gefahr(teil):
                teil["kakerlaken_warnung"] = True
                self.kategorien["kakerlaken_verdaechtig"].append(teil)
                # Trotzdem normal sortieren, aber Flag gesetzt
            
            # Entscheidungsbaum: Magnet -> Dichte -> Farbe
            ist_magnetisch = self.magnet_test(teil)
            
            if ist_magnetisch:
                # Ferromagnetisch: Eisen, Stahl, Gusseisen, manche Edelstähle (martensitisch)
                funken = self.funken_test(teil)
                if funken == "edelstahl" or "edelstahl" in material_hinweis:
                    self.kategorien["edelstahl"].append(teil)
                elif funken == "gusseisen" or "guss" in material_hinweis:
                    self.kategorien["eisenhaltig"].append(teil)  # Gusseisen ist eisenhaltig
                else:
                    self.kategorien["eisenhaltig"].append(teil)
            else:
                # Nicht magnetisch: Alu, Kupfer, Messing, Austenitischer Edelstahl, Zink, Blei
                if dichte < 3.5:  # Alu ~2.7, Titan ~4.5, Magnesium ~1.7
                    if dichte > 1.5:
                        self.kategorien["aluminium"].append(teil)
                    else:
                        self.kategorien["sonstiges"].append(teil)  # Zu leicht für Metall?
                elif 7.5 <= dichte <= 9.5:  # Kupfer ~8.96, Messing ~8.4-8.7, Edelstahl ~7.9
                    if "rot" in farbe or "kupfer" in farbe or "rotgold" in farbe:
                        self.kategorien["kupfer"].append(teil)
                    elif "gelb" in farbe or "gold" in farbe or "messing" in material_hinweis:
                        self.kategorien["messing"].append(teil)
                    elif "edelstahl" in material_hinweis or "v2a" in material_hinweis or "v4a" in material_hinweis:
                        self.kategorien["edelstahl"].append(teil)
                    else:
                        # Dichte passt zu Kupfer/Messing/Edelstahl, Farbe unklar
                        self.kategorien["sonstiges"].append(teil)
                elif dichte > 9.5:  # Blei, Wolfram, Gold, Platin
                    self.kategorien["sonstiges"].append(teil)
                else:
                    # Dichte zwischen Alu und Kupfer (z.B. Titan, Zink ~7.1, Nickel ~8.9)
                    self.kategorien["sonstiges"].append(teil)
        
        return self.kategorien


if __name__ == '__main__':
    # Test für neuer_tag
    print("=== Test neuer_tag ===")
    test_daten = {
        "gestern": {"think": 12, "eat": 3},
        "fehlschlaege": {"schrott_suchen": 2},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 2
    }
    ergebnis = neuer_tag(test_daten)
    print(f"Notiz: {ergebnis['notiz']}")
    print(f"Plan: {ergebnis['plan']}")
    
    # Test für MetallSortierer
    print("\n=== Test MetallSortierer ===")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "gewicht_g": 50, "volumen_cm3": 6.4, "farbe": "silber", "fundort": "Regal"},
        {"name": "Alu-Profil", "material": "Aluminium", "gewicht_g": 300, "volumen_cm3": 111, "farbe": "grau", "fundort": "Boden hinter Karton"},
        {"name": "Kupferrohr", "material": "Kupfer", "gewicht_g": 200, "volumen_cm3": 22.3, "farbe": "rot", "fundort": "Ecke feucht"},
        {"name": "Messing-Ventil", "material": "Messing", "gewicht_g": 150, "volumen_cm3": 17.6, "farbe": "gelb", "fundort": "Werkbank"},
        {"name": "Rostiger Nagel", "material": "Eisen", "gewicht_g": 5, "volumen_cm3": 0.6, "farbe": "braun", "fundort": "Boden"},
        {"name": "Edelstahl-Schale", "material": "Edelstahl V2A", "gewicht_g": 400, "volumen_cm3": 50, "farbe": "silber", "fundort": "Spüle"},
        "kein_dict_objekt",
        {"name": "Unbekanntes Ding", "gewicht_g": 100, "volumen_cm3": 20, "farbe": "blau", "fundort": "Karton dunkel"}
    ]
    result = sorter.sortiere_metall(test_teile)
    for kat, items in result.items():
        if items:
            print(f"{kat}: {len(items)} Teil(e)")
            for i in items:
                warn = " [KAKERLAKEN!]" if i.get('kakerlaken_warnung') else ""
                print(f"  - {i.get('name', i.get('objekt'))}{warn}")
    
    print("\nTestlauf abgeschlossen. Schuppen-Bot bereit.")