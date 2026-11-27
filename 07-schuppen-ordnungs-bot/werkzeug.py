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
                # Trotzdem normal sortieren, aber Flag gesetzt
            
            # Entscheidungsbaum: Magnet -> Dichte -> Farbe
            kategorie = "schrott"
            
            if magnetisch:
                # Ferromagnetisch: Eisen, Stahl, Gusseisen, manche Nickel-Legierungen
                if "guss" in material_hinweis or dichte > 7.0:
                    kategorie = "eisenhaltig"  # Gusseisen/Stahl
                else:
                    kategorie = "eisenhaltig"
            else:
                # Nicht magnetisch: Edelstahl (austenitisch), Alu, Kupfer, Messing, Blei, Zink
                if dichte > 7.5: # Schwere Nicht-Eisen-Metalle
                    if "edelstahl" in material_hinweis or (7.7 < dichte < 8.1):
                        kategorie = "edelstahl"
                    elif 8.9 < dichte < 9.0:
                        kategorie = "kupfer"
                    elif 8.4 < dichte < 8.7:
                        kategorie = "messing"
                    else:
                        kategorie = "sonstiges"
                elif 2.5 < dichte < 3.0: # Leichtmetalle
                    kategorie = "aluminium"
                elif dichte > 10.0: # Sehr schwer (Blei, Wolfram, Gold?)
                    kategorie = "sonstiges"
                else:
                    # Farb-Check als Fallback
                    if "rot" in farbe or "orange" in farbe or "rosa" in farbe:
                        if 8.0 < dichte < 9.0: kategorie = "kupfer"
                        else: kategorie = "messing"
                    elif "gelb" in farbe or "gold" in farbe:
                        kategorie = "messing"
                    elif "weiss" in farbe or "silber" in farbe or "grau" in farbe:
                        if dichte < 3.0: kategorie = "aluminium"
                        elif dichte > 7.5: kategorie = "edelstahl"
                        else: kategorie = "sonstiges"
                    else:
                        kategorie = "sonstiges"
            
            # Sicherheitsnetz: Wenn Material-Hinweis stark widerspricht, lieber 'sonstiges'
            if kategorie == "eisenhaltig" and not magnetisch:
                kategorie = "sonstiges"
            
            self.kategorien[kategorie].append(teil)
        
        return self.kategorien

    def get_bericht(self):
        """Gibt eine Zusammenfassung der Sortierung als String zurück."""
        zeilen = ["=== Metall-Sortier-Bericht ==="]
        gesamt = 0
        for kat, teile in self.kategorien.items():
            anzahl = len(teile)
            gesamt += anzahl
            if anzahl > 0:
                zeilen.append(f"  {kat}: {anzahl} Stück")
                # Zeige erste 3 Namen als Beispiel
                beispiele = [t.get('name', '?') for t in teile[:3]]
                zeilen.append(f"    z.B.: {', '.join(beispiele)}")
        zeilen.append(f"------------------------------\nGesamt: {gesamt} Teile")
        return "\n".join(zeilen)


if __name__ == '__main__':
    # Lokaler Test für neuer_tag
    print("--- Test neuer_tag ---")
    test_da = [
        {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen": 2}, "stimmung": 10, "wetter": "sonnig"},
        {"gestern": {}, "fehlschlaege": {}, "stimmung": 30, "wetter": "regen", "kakerlaken_level": 5},
        {"gestern": {"am_projekt_arbeiten": 1}, "fehlschlaege": {"am_projekt_arbeiten": 3}, "stimmung": -60, "wetter": "bewoelkt"},
    ]
    for i, d in enumerate(test_da):
        erg = neuer_tag(d)
        print(f"Test {i+1}: {erg}")
    
    # Lokaler Test für MetallSortierer
    print("\n--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "gewicht_g": 50, "volumen_cm3": 6.4, "farbe": "silber", "fundort": "Werkbank"},
        {"name": "Alu-Profil", "material": "Aluminium", "gewicht_g": 300, "volumen_cm3": 111, "farbe": "grau", "fundort": "Boden hinter Karton"},
        {"name": "Kupferrohr", "material": "Kupfer", "gewicht_g": 890, "volumen_cm3": 100, "farbe": "rot", "fundort": "Regal"},
        {"name": "Messing-Ventil", "material": "Messing", "gewicht_g": 200, "volumen_cm3": 23, "farbe": "gelb", "fundort": "Kasten"},
        {"name": "Edelstahl-Schale", "material": "Edelstahl V2A", "gewicht_g": 500, "volumen_cm3": 63, "farbe": "silber", "fundort": "Spüle"},
        {"name": "Rostiger Nagel", "material": "Eisen", "gewicht_g": 10, "volumen_cm3": 1.3, "farbe": "braun", "fundort": "dunkle Ecke"},
        {"name": "Unbekanntes Teil", "material": "Plastik", "gewicht_g": 5, "volumen_cm3": 10, "farbe": "blau", "fundort": "Müll"},
    ]
    ergebnis = sorter.sortiere_metall(test_teile)
    print(sorter.get_bericht())
    
    # Prüfen auf Kakerlaken-Warnung
    print("\n--- Kakerlaken Check ---")
    for kat, teile in ergebnis.items():
        for t in teile:
            if t.get("kakerlaken_warnung"):
                print(f"WARNUNG: '{t['name']}' in '{kat}' kommt aus verseuchter Zone!")