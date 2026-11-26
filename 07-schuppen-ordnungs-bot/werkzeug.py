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
            
            # 1. Magnet-Test: Eisen/Stahl getrennt
            if self.magnet_test(teil):
                # Edelstahl kann magnetisch sein (ferritisch/martensitisch) oder nicht (austenitisch).
                # Heuristik: Wenn 'edelstahl' im Material-String ODER (nicht magnetisch aber dicht & silber) -> schwierig ohne Funken.
                # Wir nutzen Material-Hinweis + Dichte.
                if "edelstahl" in material_hinweis or (3.5 <= dichte <= 8.5 and "rostfrei" in material_hinweis):
                     self.kategorien["edelstahl"].append(teil)
                else:
                    self.kategorien["eisenhaltig"].append(teil)
                continue
            
            # 2. Nicht magnetisch -> Dichte & Farbe prüfen
            # Kupfer: ~8.9 g/cm³, Farbe rot/orange
            # Messing: ~8.4-8.7 g/cm³, Farbe gelb/gold
            # Aluminium: ~2.7 g/cm³, Farbe silbergrau/matt
            # Edelstahl (austenitisch): ~7.9 g/cm³, nicht magnetisch, silber/weißlich
            
            if dichte >= 8.0:
                # Schwere Nicht-Magnetische: Kupfer, Messing, Bronze, evtl. Blei
                if any(c in farbe for c in ["rot", "orange", "kupfer"]):
                    self.kategorien["kupfer"].append(teil)
                elif any(c in farbe for c in ["gelb", "gold", "messing"]):
                    self.kategorien["messing"].append(teil)
                elif "kupfer" in material_hinweis:
                    self.kategorien["kupfer"].append(teil)
                elif "messing" in material_hinweis or "bronze" in material_hinweis:
                    self.kategorien["messing"].append(teil)
                else:
                    # Unklare schwere Metalle
                    self.kategorien["sonstiges"].append(teil)
            elif 3.5 <= dichte < 8.0:
                # Mittlere Dichte: Edelstahl (aust.), Titan, evtl. dichte Alu-Legierungen
                if "edelstahl" in material_hinweis or "rostfrei" in material_hinweis:
                    self.kategorien["edelstahl"].append(teil)
                elif any(c in farbe for c in ["silber", "weiss", "grau", "metallisch"]):
                    # Typisch Edelstahl-Optik
                    self.kategorien["edelstahl"].append(teil)
                else:
                    self.kategorien["sonstiges"].append(teil)
            elif dichte > 0 and dichte < 3.5:
                # Leichte Metalle: Alu, Magnesium, Titan (leicht)
                if "aluminium" in material_hinweis or "alu" in material_hinweis:
                    self.kategorien["aluminium"].append(teil)
                elif any(c in farbe for c in ["silber", "grau", "weiss", "matt"]):
                    self.kategorien["aluminium"].append(teil)
                else:
                    self.kategorien["sonstiges"].append(teil)
            else:
                # Keine Gewichts/Volumen-Daten oder Dichte 0
                # Fallback nur auf Material-String
                if "aluminium" in material_hinweis or "alu" in material_hinweis:
                    self.kategorien["aluminium"].append(teil)
                elif "kupfer" in material_hinweis:
                    self.kategorien["kupfer"].append(teil)
                elif "messing" in material_hinweis or "bronze" in material_hinweis:
                    self.kategorien["messing"].append(teil)
                elif "edelstahl" in material_hinweis or "rostfrei" in material_hinweis:
                    self.kategorien["edelstahl"].append(teil)
                else:
                    self.kategorien["schrott"].append({"objekt": teil, "grund": "Keine Daten für Klassifikation"})
        
        return self.kategorien

    def get_zusammenfassung(self):
        """Gibt kurzes Dict mit Counts zurück."""
        return {k: len(v) for k, v in self.kategorien.items()}

    def print_bericht(self):
        """Druckt formatierten Bericht auf Konsole."""
        print("=== Schuppen-Metall-Sortierbericht ===")
        gesamt = 0
        for kat, teile in self.kategorien.items():
            anzahl = len(teile)
            gesamt += anzahl
            if anzahl > 0:
                print(f"  {kat.replace('_', ' ').title()}: {anzahl} Stück")
                # Erste 3 Namen anzeigen
                namen = [t.get('name', '?') for t in teile[:3]]
                print(f"    z.B.: {', '.join(namen)}")
        print(f"-----------------------------------")
        print(f"  Gesamt: {gesamt} Teile")
        if self.kategorien["kakerlaken_verdaechtig"]:
            print("  !!! ACHTUNG: Kakerlaken-verdächtige Teile gefunden! Handschuhe waschen! !!!")


if __name__ == "__main__":
    # Test für neuer_tag
    print("--- Test neuer_tag ---")
    test_daten = {
        "gestern": {"think": 12, "eat": 3},
        "fehlschlaege": {"schrott_suchen": 1},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 2
    }
    ergebnis = neuer_tag(test_daten)
    print(f"Notiz: {ergebnis['notiz']}")
    print(f"Plan: {ergebnis['plan']}")
    
    # Test für MetallSortierer
    print("\n--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Rostiger Nagel", "material": "Eisen", "farbe": "braun", "gewicht_g": 10, "volumen_cm3": 1.3, "fundort": "Boden"},
        {"name": "Blanker Schraubendreher", "material": "Stahl", "farbe": "silber", "gewicht_g": 150, "volumen_cm3": 20, "fundort": "Werkzeugkasten"},
        {"name": "Alu-Profil Rest", "material": "Aluminium", "farbe": "silber", "gewicht_g": 50, "volumen_cm3": 18.5, "fundort": "Ecke hinter Karton"},
        {"name": "Kupferrohr Stück", "material": "Kupfer", "farbe": "rot", "gewicht_g": 300, "volumen_cm3": 33.7, "fundort": "Regal"},
        {"name": "Messing-Ventil", "material": "Messing", "farbe": "gold", "gewicht_g": 200, "volumen_cm3": 23.5, "fundort": "Karton unten"},
        {"name": "Edelstahl-Schraube M8", "material": "Edelstahl V2A", "farbe": "silber", "gewicht_g": 20, "volumen_cm3": 2.5, "fundort": "Schraubendose"},
        {"name": "Unbekanntes Ding", "material": "", "farbe": "grau", "gewicht_g": 0, "volumen_cm3": 0, "fundort": "dunkle Ecke"},
        {"name": "Magnetischer Brocken", "material": "Ferrolegierung", "farbe": "schwarz", "gewicht_g": 500, "volumen_cm3": 63, "fundort": "Boden"},
    ]
    result = sorter.sortiere_metall(test_teile)
    sorter.print_bericht()
    print(f"\nZusammenfassung Dict: {sorter.get_zusammenfassung()}")
    
    # Prüfen ob Kakerlaken-Flag gesetzt wurde (Alu-Profil & Unbekanntes Ding)
    print("\nKakerlaken-Check:")
    for t in test_teile:
        if t.get("kakerlaken_warnung"):
            print(f"  Flag gesetzt: {t['name']} (Fundort: {t['fundort']})")