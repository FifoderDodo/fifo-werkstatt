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
            
            # Eigentliche Sortierlogik
            magnetisch = self.magnet_test(teil)
            funken = self.funken_test(teil)
            
            kategorisiert = False
            
            # 1. Magnetisch -> Eisenhaltig (Stahl, Gusseisen)
            if magnetisch:
                if "guss" in material_hinweis or funken == "gusseisen":
                    self.kategorien["eisenhaltig"].append({**teil, "typ": "gusseisen"})
                else:
                    self.kategorien["eisenhaltig"].append({**teil, "typ": "stahl_eisen"})
                kategorisiert = True
            
            # 2. Nicht magnetisch -> Dichte & Farbe prüfen
            if not kategorisiert:
                # Kupfer: Dichte ~8.9, Farbe rot/orange
                if 8.5 <= dichte <= 9.5 and any(c in farbe for c in ["rot", "orange", "kupfer", "braun"]):
                    self.kategorien["kupfer"].append(teil)
                    kategorisiert = True
                # Messing: Dichte ~8.4-8.7, Farbe gelb/gold
                elif 8.0 <= dichte <= 8.8 and any(c in farbe for c in ["gelb", "gold", "messing"]):
                    self.kategorien["messing"].append(teil)
                    kategorisiert = True
                # Aluminium: Dichte ~2.7, Farbe grau/weiss/matt
                elif 2.5 <= dichte <= 3.0 and not magnetisch:
                    self.kategorien["aluminium"].append(teil)
                    kategorisiert = True
                # Edelstahl (austenitisch): Dichte ~7.9, nicht magnetisch, grau
                elif 7.5 <= dichte <= 8.2 and not magnetisch:
                    if "edelstahl" in material_hinweis or funken == "edelstahl":
                        self.kategorien["edelstahl"].append(teil)
                    else:
                        self.kategorien["edelstahl"].append({**teil, "vermutung": "edelstahl_304_316"})
                    kategorisiert = True
            
            # 3. Fallback
            if not kategorisiert:
                if material_hinweis or farbe or dichte > 0:
                    self.kategorien["sonstiges"].append(teil)
                else:
                    self.kategorien["schrott"].append({**teil, "grund": "Keine Merkmale erkennbar"})
        
        return self.kategorien


if __name__ == "__main__":
    # Kleiner Selbsttest für die Sortierlogik
    print("--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "gewicht_g": 50, "volumen_cm3": 6.3, "fundort": "Regal"},
        {"name": "Kupferrohr", "material": "Kupfer", "farbe": "rot", "gewicht_g": 890, "volumen_cm3": 100, "fundort": "Ecke hinter Karton"},
        {"name": "Alu-Profil", "material": "Aluminium", "farbe": "grau", "gewicht_g": 270, "volumen_cm3": 100, "fundort": "Boden"},
        {"name": "Edelstahlbecken", "material": "Edelstahl 304", "farbe": "silber", "gewicht_g": 790, "volumen_cm3": 100, "fundort": "Arbeitsplatte"},
        {"name": "Messingventil", "material": "Messing", "farbe": "gold", "gewicht_g": 850, "volumen_cm3": 100, "fundort": "Kasten"},
        {"name": "Rostiges Blech", "material": "Eisen", "farbe": "braun", "gewicht_g": 780, "volumen_cm3": 100, "fundort": "Feuchte Ecke"},
        "Kein Dict",
        {}
    ]
    ergebnis = sorter.sortiere_metall(test_teile)
    for kat, teile in ergebnis.items():
        if teile:
            print(f"{kat}: {len(teile)} Teile")
            for t in teile:
                print(f"  - {t.get('name', t.get('objekt', 'Unbekannt'))}")
    
    # Test neuer_tag
    print("\n--- Test neuer_tag ---")
    test_daten = {
        "gestern": {"think": 12, "eat": 3},
        "fehlschlaege": {"schrott_suchen": 1},
        "stimmung": 30,
        "wetter": "sonnig",
        "kakerlaken_level": 2
    }
    print(neuer_tag(test_daten))