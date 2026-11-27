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
                self.kategorien["kakerlaken_verdaechtig"].append(teil)
            
            # 1. Magnetisch -> Eisen/Stahl/Guss
            if magnetisch:
                funken = self.funken_test(teil)
                if funken == "edelstahl" or "edelstahl" in material_hinweis:
                    self.kategorien["edelstahl"].append(teil)
                elif funken == "gusseisen" or "guss" in material_hinweis:
                    self.kategorien["eisenhaltig"].append(teil)  # Guss ist eisenhaltig
                else:
                    self.kategorien["eisenhaltig"].append(teil)
                continue
            
            # 2. Nicht magnetisch -> Dichte-Entscheidungsbaum
            # Alu ~2.7, Titan ~4.5, Edelstahl (austenitisch) ~7.9, Messing ~8.5, Kupfer ~8.9
            if dichte < 3.0:
                self.kategorien["aluminium"].append(teil)
            elif 3.0 <= dichte < 5.5:
                # Titan, evtl. Magnesium-Legierungen
                self.kategorien["sonstiges"].append(teil)  # Selten im Schuppen
            elif 5.5 <= dichte < 7.5:
                # Lücke, evtl. spezielle Bronzen/Stähle
                self.kategorien["sonstiges"].append(teil)
            elif 7.5 <= dichte < 8.2:
                # Austenitischer Edelstahl (nicht magnetisch)
                self.kategorien["edelstahl"].append(teil)
            elif 8.2 <= dichte < 8.7:
                # Messing / Rotguss
                if "gelb" in farbe or "gold" in farbe or "messing" in material_hinweis:
                    self.kategorien["messing"].append(teil)
                else:
                    self.kategorien["sonstiges"].append(teil)
            elif dichte >= 8.7:
                # Kupfer / Blei (Blei weicher, aber Dichte ~11)
                if "rot" in farbe or "kupfer" in material_hinweis or "orange" in farbe:
                    self.kategorien["kupfer"].append(teil)
                elif "grau" in farbe or "blei" in material_hinweis or dichte > 10.5:
                    self.kategorien["sonstiges"].append(teil)  # Blei separat wäre besser
                else:
                    self.kategorien["kupfer"].append(teil)  # Default schwer & nicht magnetisch
            else:
                self.kategorien["schrott"].append({"objekt": teil, "grund": "Dichte unplausibel"})
        
        return self.kategorien

    def get_bericht(self):
        """Gibt Zusammenfassung als Text zurück."""
        gesamt = sum(len(v) for v in self.kategorien.values())
        if gesamt == 0:
            return "Nix sortiert. Schuppen leer oder Bot kaputt."
        lines = [f"Sortier-Bericht: {gesamt} Teile bearbeitet"]
        for kat, teile in self.kategorien.items():
            if teile:
                lines.append(f"  {kat}: {len(teile)} Stk")
        # Warnung hervorheben
        if self.kategorien["kakerlaken_verdaechtig"]:
            lines.append(f"  >>> ACHTUNG: {len(self.kategorien['kakerlaken_verdaechtig'])} Teile aus verseuchten Zonen! <<<")
        return "\n".join(lines)

    def export_kategorien(self):
        """Gibt Dict zurück für JSON-Speicher oder Weiterverarbeitung."""
        # Kopie ohne interne Marker
        export = {}
        for kat, teile in self.kategorien.items():
            clean = []
            for t in teile:
                if isinstance(t, dict) and "objekt" in t and "grund" in t:  # Fehler-Objekte
                    clean.append(t)
                elif isinstance(t, dict):
                    # Kopie ohne temporäre Keys
                    ct = {k: v for k, v in t.items() if k != "kakerlaken_warnung"}
                    clean.append(ct)
                else:
                    clean.append(str(t))
            export[kat] = clean
        return export


if __name__ == "__main__":
    # Test-Daten: Realistischer Schuppen-Mix
    test_teile = [
        {"name": "Schraube M8", "material": "Stahl", "gewicht_g": 15, "volumen_cm3": 2, "fundort": "Werkzeugkasten", "farbe": "silber"},
        {"name": "Alu-Profil 1m", "material": "Aluminium", "gewicht_g": 800, "volumen_cm3": 300, "fundort": "Regal links", "farbe": "silber"},
        {"name": "Kupferrohr Rest", "material": "Kupfer", "gewicht_g": 1200, "volumen_cm3": 135, "fundort": "Ecke hinten feucht", "farbe": "rot", "notiz": "grünlich angelaufen"},
        {"name": "Messing-Ventil", "material": "Messing", "gewicht_g": 450, "volumen_cm3": 53, "fundort": "Karton oben", "farbe": "gold"},
        {"name": "Edelstahl-Schale (V2A)", "material": "Edelstahl austenitisch", "gewicht_g": 300, "volumen_cm3": 38, "fundort": "Spüle", "farbe": "silber"},
        {"name": "Eisenwinkel rostig", "material": "Gusseisen", "gewicht_g": 2500, "volumen_cm3": 320, "fundort": "Boden unterm Regal", "farbe": "braun"},
        {"name": "Mysterie-Teil schwer", "material": "Unbekannt", "gewicht_g": 900, "volumen_cm3": 100, "fundort": "Dunkle Ecke Karton", "farbe": "grau"},  # Dichte 9.0 -> Kupfer/Messing
        {"name": "Leichter Klumpen", "material": "Unbekannt", "gewicht_g": 50, "volumen_cm3": 20, "fundort": "Hinter Ofen", "farbe": "weiß"},  # Dichte 2.5 -> Alu
        "Kein Dict sondern String",  # Fehlerfall
        {"name": "Magnetischer Brocken", "material": "Stahl", "gewicht_g": 5000, "volumen_cm3": 640, "fundort": "Mitte Raum", "farbe": "schwarz"},
    ]
    
    print("=== Schuppen-Bot MetallSortierer Test ===")
    sorter = MetallSortierer()
    ergebnis = sorter.sortiere_metall(test_teile)
    print(sorter.get_bericht())
    print("\n--- Export Check ---")
    import json
    print(json.dumps(sorter.export_kategorien(), indent=2, ensure_ascii=False))
    
    # Test neuer_tag
    print("\n=== neuer_tag Test ===")
    test_daten = {
        "gestern": {"think": 12, "eat": 3},
        "fehlschlaege": {"schrott_suchen": 1, "am_projekt_arbeiten": 0},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 2
    }
    print(json.dumps(neuer_tag(test_daten), indent=2, ensure_ascii=False))