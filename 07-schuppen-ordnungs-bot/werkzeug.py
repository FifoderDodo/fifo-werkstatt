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
        """Simuliert Magnet-Test. True = ferromagnetisch (Eisen/Stahl/Guss)."""
        material = teil.get("material", "").lower()
        return any(m in material for m in ["eisen", "stahl", "ferro", "guss"])
    
    def funken_test(self, teil):
        """Simuliert Funkenbild-Test (Grobe Klassifikation)."""
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
            dichte = self.gewicht_test(teil)  # Hier war der Abbruch
            magnetisch = self.magnet_test(teil)
            kakerlaken_alarm = self.check_kakerlaken_gefahr(teil)
            
            # Basis-Eintrag für verdächtige Teile (zusätzlich zur Material-Kategorie)
            if kakerlaken_alarm:
                self.kategorien["kakerlaken_verdaechtig"].append({
                    "name": name, "grund": "Fundort verdächtig", "original": teil
                })
            
            # 1. Magnet-Test: Ferromagnetisch -> Eisen/Stahl/Guss
            if magnetisch:
                # Ferritischer Edelstahl ist auch magnetisch, Dichte prüfen
                if 7.7 <= dichte <= 8.1:
                    # Heuristik: Edelstahl oft glänzender, unrostig
                    if "rost" not in farbe and "braun" not in farbe and "edel" in teil.get("material", "").lower():
                        self.kategorien["edelstahl"].append(teil)
                    else:
                        self.kategorien["eisenhaltig"].append(teil)
                else:
                    self.kategorien["eisenhaltig"].append(teil)
                continue
            
            # 2. Nicht magnetisch -> Dichte-Baum für NE-Metalle
            # Aluminium: ~2.7 g/cm³
            if 2.5 <= dichte <= 3.0:
                self.kategorien["aluminium"].append(teil)
            # Messing: ~8.4 - 8.7 g/cm³ (gelblich)
            elif 8.3 <= dichte <= 8.9:
                if "gelb" in farbe or "gold" in farbe or "messing" in teil.get("material", "").lower():
                    self.kategorien["messing"].append(teil)
                else:
                    # Könnte auch Kupfer sein, wenn rotlich, oder Edelstahl (austenitisch)
                    if "rot" in farbe or "kupfer" in teil.get("material", "").lower():
                        self.kategorien["kupfer"].append(teil)
                    else:
                        self.kategorien["edelstahl"].append(teil)  # Austenitisch
            # Kupfer: ~8.9 - 9.0 g/cm³ (rot/orange)
            elif 8.8 <= dichte <= 9.1:
                self.kategorien["kupfer"].append(teil)
            # Edelstahl (austenitisch): ~7.9 - 8.0 g/cm³, nicht magnetisch
            elif 7.8 <= dichte <= 8.1:
                self.kategorien["edelstahl"].append(teil)
            # Sonstiges Metall mit Dichte
            elif dichte > 0:
                self.kategorien["sonstiges"].append({"teil": teil, "dichte": round(dichte, 2)})
            else:
                self.kategorien["schrott"].append({"objekt": teil, "grund": "Keine Daten (Gewicht/Volumen)"})
        
        return self.kategorien
    
    def get_bericht(self):
        """Gibt Text-Zusammenfassung der Sortierung zurück."""
        gesamt = sum(len(v) for v in self.kategorien.values())
        if gesamt == 0:
            return "Nichts sortiert. Schuppen leer oder Bot schläft."
        lines = [f"Sortierbericht: {gesamt} Einträge insgesamt"]
        for kat, teile in self.kategorien.items():
            if teile:
                lines.append(f"  {kat}: {len(teile)} Stk")
        return "\n".join(lines)
    
    def export_kategorien(self):
        """Gibt Dict zurück für JSON-Speicherung oder Weiterverarbeitung."""
        # Kopie, damit Original unverändert bleibt
        return {k: list(v) for k, v in self.kategorien.items()}


if __name__ == "__main__":
    # Test-Daten für neuen_tag
    test_daten = {
        "gestern": {"think": 12, "eat": 3, "am_projekt_arbeiten": 5},
        "fehlschlaege": {"am_projekt_arbeiten": 2, "schrott_suchen": 1},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 2
    }
    print("=== Test neuer_tag ===")
    erg = neuer_tag(test_daten)
    print(f"Notiz: {erg['notiz']}")
    print(f"Plan: {erg['plan']}")
    
    # Test KI-Frage bei vielen Fehlschlägen
    test_daten_ki = {**test_daten, "fehlschlaege": {"am_projekt_arbeiten": 5}}
    print("\n=== Test KI-Frage ===")
    erg_ki = neuer_tag(test_daten_ki)
    print(f"Ergebnis: {erg_ki}")
    
    # Test MetallSortierer
    print("\n=== Test MetallSortierer ===")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "gewicht_g": 78, "volumen_cm3": 10, "farbe": "grau", "fundort": "Regal"},
        {"name": "Rohrstück", "material": "Edelstahl V2A", "gewicht_g": 160, "volumen_cm3": 20, "farbe": "silber", "fundort": "Ecke hinter Karton"},
        {"name": "Alu-Profil", "material": "Aluminium", "gewicht_g": 54, "volumen_cm3": 20, "farbe": "silber", "fundort": "Boden"},
        {"name": "Kupferleitung", "material": "Kupfer", "gewicht_g": 89, "volumen_cm3": 10, "farbe": "rot", "fundort": "Wand"},
        {"name": "Messing-Ventil", "material": "Messing", "gewicht_g": 170, "volumen_cm3": 20, "farbe": "gelb", "fundort": "Kasten"},
        {"name": "Guss-Eisen", "material": "Grauguss", "gewicht_g": 72, "volumen_cm3": 9, "farbe": "grau", "fundort": "Schrott-Haufen"},
        {"name": "Ferritischer Edelstahl", "material": "Edelstahl 1.4016 (ferritisch)", "gewicht_g": 79, "volumen_cm3": 10, "farbe": "silber", "fundort": "Regal"},
        "Kaputte Zeichenkette statt Dict",
        {"name": "Mysterie-Metall", "gewicht_g": 100, "volumen_cm3": 15, "farbe": "weiß", "fundort": "Dunkle feuchte Ecke"}  # Dichte 6.6 -> sonstiges, aber Kakerlaken
    ]
    result = sorter.sortiere_metall(test_teile)
    print(sorter.get_bericht())
    print("\nDetails Kakerlaken-Verdacht:")
    for v in result["kakerlaken_verdaechtig"]:
        print(f"  - {v['name']}: {v['grund']}")
    print("\nExport:")
    import json
    print(json.dumps(sorter.export_kategorien(), indent=2, ensure_ascii=False, default=str))