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
            
            # 1. Magnet-Test
            if self.magnet_test(teil):
                self.kategorien["eisenhaltig"].append(teil)
                continue
            
            # 2. Kein Magnet -> Dichte & Farbe & Material-String
            kategorie = "sonstiges"
            
            if dichte > 8.0:  # Kupfer, Messing, Bronze
                if any(c in farbe for c in ["gelb", "gold", "messing"]) or "messing" in material_hinweis or "zink" in material_hinweis:
                    kategorie = "messing"
                elif any(c in farbe for c in ["rot", "orange", "kupfer"]) or "kupfer" in material_hinweis:
                    kategorie = "kupfer"
                else:
                    kategorie = "kupfer"  # Default schwer & nicht magnetisch
            elif dichte < 3.0 and dichte > 0.5:  # Alu, Magnesium, Titan (Titan ~4.5)
                if "titan" in material_hinweis:
                    kategorie = "edelstahl"  # Titanschrott oft zu Edelstahl
                else:
                    kategorie = "aluminium"
            elif 4.0 <= dichte <= 8.0:  # Edelstahl, Titan, Nickel
                if "edelstahl" in material_hinweis or "rostfrei" in material_hinweis or dichte > 7.5:
                    kategorie = "edelstahl"
                elif "titan" in material_hinweis:
                    kategorie = "edelstahl"
                else:
                    kategorie = "edelstahl"  # Best guess
            
            # Fallback über Material-String wenn Dichte 0/fehlt
            if kategorie == "sonstiges" and material_hinweis:
                if "aluminium" in material_hinweis or "alu" in material_hinweis:
                    kategorie = "aluminium"
                elif "kupfer" in material_hinweis:
                    kategorie = "kupfer"
                elif "messing" in material_hinweis:
                    kategorie = "messing"
                elif "edelstahl" in material_hinweis or "rostfrei" in material_hinweis:
                    kategorie = "edelstahl"
            
            # Fallback über Farbe wenn alles fehlt
            if kategorie == "sonstiges":
                if any(c in farbe for c in ["silber", "grau", "weiss"]) and dichte > 2.5:
                    kategorie = "aluminium"
                elif any(c in farbe for c in ["rot", "orange"]):
                    kategorie = "kupfer"
                elif any(c in farbe for c in ["gelb", "gold"]):
                    kategorie = "messing"
            
            self.kategorien[kategorie].append(teil)
        
        return self.kategorien
    
    def get_zusammenfassung(self):
        """Gibt Dict mit Anzahl pro Kategorie zurück."""
        return {k: len(v) for k, v in self.kategorien.items()}
    
    def print_bericht(self):
        """Konsolen-Ausgabe der Sortier-Ergebnisse."""
        print("=== Schuppen-Metall-Bericht ===")
        gesamt = 0
        for kat, teile in self.kategorien.items():
            anzahl = len(teile)
            gesamt += anzahl
            if anzahl > 0:
                namen = [t.get('name', '?') for t in teile[:3]]
                mehr = f" ... (+{anzahl-3} weitere)" if anzahl > 3 else ""
                print(f"  {kat}: {anzahl} Stk. [{', '.join(namen)}{mehr}]")
        print(f"-----------------------------\n  Gesamt: {gesamt} Teile")
        if self.kategorien["kakerlaken_verdaechtig"]:
            print("  !!! WARNUNG: Teile mit Kakerlaken-Verdacht vorhanden !!!")


if __name__ == "__main__":
    # Test neuer_tag
    print("--- Test neuer_tag ---")
    test_daten_1 = {
        "gestern": {"think": 12, "eat": 3},
        "fehlschlaege": {"schrott_suchen": 2},
        "stimmung": 10,
        "wetter": "regen",
        "kakerlaken_level": 2
    }
    erg1 = neuer_tag(test_daten_1)
    print(f"Notiz: {erg1['notiz']}")
    print(f"Plan: {erg1['plan']}")
    
    test_daten_2 = {
        "gestern": {},
        "fehlschlaege": {},
        "stimmung": 30,
        "wetter": "sonnig",
        "kakerlaken_level": 0
    }
    erg2 = neuer_tag(test_daten_2)
    print(f"Notiz: {erg2['notiz']}")
    print(f"Plan: {erg2['plan']}")
    
    test_daten_3 = {
        "gestern": {},
        "fehlschlaege": {},
        "stimmung": -60,
        "wetter": "bewoelkt",
        "kakerlaken_level": 8
    }
    erg3 = neuer_tag(test_daten_3)
    print(f"Notiz: {erg3['notiz']}")
    print(f"Plan: {erg3['plan']}")

    # Test MetallSortierer
    print("\n--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "gewicht_g": 50, "volumen_cm3": 6.4, "farbe": "silber", "fundort": "Regal A"},
        {"name": "Kupferrohr", "material": "Kupfer", "gewicht_g": 300, "volumen_cm3": 33.7, "farbe": "rot", "fundort": "Ecke hinten feucht"},
        {"name": "Alu-Profil", "material": "Aluminium", "gewicht_g": 150, "volumen_cm3": 55.5, "farbe": "grau", "fundort": "Boden Karton"},
        {"name": "Edelstahl-Schale", "material": "Edelstahl V2A", "gewicht_g": 200, "volumen_cm3": 25.6, "farbe": "silber", "fundort": "Spüle"},
        {"name": "Messing-Ventil", "material": "Messing", "gewicht_g": 180, "volumen_cm3": 20.0, "farbe": "gold", "fundort": "Werkzeugkasten"},
        {"name": "Unbekanntes Teil", "gewicht_g": 100, "volumen_cm3": 12.5, "farbe": "grau", "fundort": "Dunkel hinter Schrank"},
        "kein dict",
    ]
    ergebnis = sorter.sortiere_metall(test_teile)
    sorter.print_bericht()
    print(f"\nZusammenfassung Dict: {sorter.get_zusammenfassung()}")
    
    # Check Kakerlaken-Flag
    for kat, teile in ergebnis.items():
        for t in teile:
            if isinstance(t, dict) and t.get("kakerlaken_warnung"):
                print(f"  Flag gesetzt: {t.get('name')} in {kat}")