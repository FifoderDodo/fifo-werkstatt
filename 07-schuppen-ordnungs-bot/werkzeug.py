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
            
            # Kakerlaken-Check: Teile markieren, nicht automatisch wegwerfen
            if self.check_kakerlaken_gefahr(teil):
                teil["kakerlaken_warnung"] = True
                self.kategorien["kakerlaken_verdaechtig"].append(teil)
                # Trotzdem normal sortieren
            
            # Entscheidungsbaum
            if magnetisch:
                # Ferromagnetisch -> Eisen / normaler Stahl
                if "rost" in farbe or "schrott" in material_hinweis:
                    self.kategorien["schrott"].append(teil)
                else:
                    self.kategorien["eisenhaltig"].append(teil)
            else:
                # Nicht magnetisch: Alu, Kupfer, Messing, Edelstahl (austenitisch), Titan, etc.
                # Grobe Trennung über Dichte (g/cm³)
                if dichte < 3.5:  # ~2.7 Alu, ~1.7 Titan (selten), ~4.5 Titan
                    if "kupfer" in material_hinweis or "rot" in farbe or "orange" in farbe:
                        # Dünnes Kupferblech könnte leicht sein, aber meist schwerer
                        if dichte > 7.0:
                            self.kategorien["kupfer"].append(teil)
                        else:
                            self.kategorien["aluminium"].append(teil)  # Wahrscheinlich Alu oder lackiert
                    else:
                        self.kategorien["aluminium"].append(teil)
                elif 7.5 <= dichte <= 9.5:
                    # Schwere Nicht-Magnetische: Kupfer (8.96), Messing (8.4-8.7), Edelstahl (7.9), Nickel
                    if "edelstahl" in material_hinweis or "v2a" in material_hinweis or "v4a" in material_hinweis:
                        self.kategorien["edelstahl"].append(teil)
                    elif "messing" in material_hinweis or "gelb" in farbe or "gold" in farbe:
                        self.kategorien["messing"].append(teil)
                    elif "kupfer" in material_hinweis or "rot" in farbe or "gruen" in farbe:  # Grünspan
                        self.kategorien["kupfer"].append(teil)
                    else:
                        # Heuristik: Kupfer oft rötlich, Messing gelblich, Edelstahl grau/weiß glänzend
                        if "rot" in farbe or "orange" in farbe:
                            self.kategorien["kupfer"].append(teil)
                        elif "gelb" in farbe or "gold" in farbe:
                            self.kategorien["messing"].append(teil)
                        else:
                            self.kategorien["edelstahl"].append(teil)  # Default schwer & nicht magnetisch
                elif dichte > 0:
                    # Dichte dazwischen oder unplausibel
                    self.kategorien["sonstiges"].append(teil)
                else:
                    # Keine Gewichts/Volumen-Daten
                    if "aluminium" in material_hinweis or "alu" in material_hinweis:
                        self.kategorien["aluminium"].append(teil)
                    elif "edelstahl" in material_hinweis:
                        self.kategorien["edelstahl"].append(teil)
                    elif "kupfer" in material_hinweis:
                        self.kategorien["kupfer"].append(teil)
                    elif "messing" in material_hinweis:
                        self.kategorien["messing"].append(teil)
                    else:
                        self.kategorien["sonstiges"].append(teil)
        
        return self.kategorien
    
    def get_bericht(self):
        """Gibt Zusammenfassung der Sortierung zurück."""
        bericht = {}
        gesamt = 0
        for kat, teile in self.kategorien.items():
            anzahl = len(teile)
            gesamt += anzahl
            bericht[kat] = anzahl
        bericht["gesamt"] = gesamt
        return bericht


if __name__ == "__main__":
    # Test-Daten: Simulierter Schuppen-Fund
    test_teile = [
        {"name": "Schraube M8", "material": "Stahl", "gewicht_g": 15, "volumen_cm3": 2, "farbe": "silber", "fundort": "Werkbank"},
        {"name": "Alu-Profil 1m", "material": "Aluminium", "gewicht_g": 500, "volumen_cm3": 185, "farbe": "grau", "fundort": "Ecke hinter Karton"},
        {"name": "Kupferrohr Stück", "material": "Kupfer", "gewicht_g": 300, "volumen_cm3": 33, "farbe": "rot", "fundort": "Regal"},
        {"name": "Messing-Ventil", "material": "Messing", "gewicht_g": 200, "volumen_cm3": 23, "farbe": "gold", "fundort": "Boden bei Nässe"},
        {"name": "Edelstahl-Schraube", "material": "Edelstahl V2A", "gewicht_g": 20, "volumen_cm3": 2.5, "farbe": "silber", "fundort": "Kiste"},
        {"name": "Rostiger Nagel", "material": "Eisen", "gewicht_g": 5, "volumen_cm3": 0.6, "farbe": "braun", "fundort": "Boden"},
        {"name": "Unbekanntes Teil", "material": "", "gewicht_g": 100, "volumen_cm3": 37, "farbe": "grau", "fundort": "dunkle Ecke", "notiz": "lange liegen geblieben"},
        "Kein Dict Objekt",
    ]
    
    sorter = MetallSortierer()
    ergebnis = sorter.sortiere_metall(test_teile)
    bericht = sorter.get_bericht()
    
    print("=== Schuppen-Bot Sortierbericht ===")
    for kat, count in bericht.items():
        if kat != "gesamt":
            print(f"  {kat}: {count} Stück")
    print(f"  Gesamt: {bericht['gesamt']} Stück")
    
    # Detail-Ausgabe für Kakerlaken-Verdacht
    if ergebnis["kakerlaken_verdaechtig"]:
        print("\n!!! Kakerlaken-Verdacht bei: !!!")
        for t in ergebnis["kakerlaken_verdaechtig"]:
            print(f"  - {t.get('name', 'Unbekannt')} (Fundort: {t.get('fundort', '?')})")
    
    # Test neuer_tag
    print("\n=== neuer_tag Test ===")
    test_daten = {
        "gestern": {"think": 12, "eat": 3},
        "fehlschlaege": {"schrott_suchen": 2, "am_projekt_arbeiten": 1},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 3
    }
    print(neuer_tag(test_daten))