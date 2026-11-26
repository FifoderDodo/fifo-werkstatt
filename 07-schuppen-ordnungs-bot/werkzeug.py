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
        for k in self.kategorien:
            self.kategorien[k] = []
            
        for teil in teile_liste:
            if not isinstance(teil, dict):
                self.kategorien["schrott"].append({"objekt": teil, "grund": "Kein Dict"})
                continue
            
            name = teil.get("name", "Unbekannt")
            farbe = teil.get("farbe", "").lower()
            dichte = self.gewicht_test(teil)
            
            # Kakerlaken-Check: Teile markieren, nicht automatisch wegwerfen
            if self.check_kakerlaken_gefahr(teil):
                teil["kakerlaken_warnung"] = True
                self.kategorien["kakerlaken_verdaechtig"].append(teil)
                # Trotzdem normal sortieren, aber Flag gesetzt
            
            # 1. Magnet-Test
            if self.magnet_test(teil):
                self.kategorien["eisenhaltig"].append(teil)
                continue
            
            # 2. Nicht magnetisch -> Alu, Kupfer, Messing, Edelstahl (austenitisch)
            if dichte > 8.0:
                # Schwere NE-Metalle: Kupfer (~8.9), Messing (~8.4-8.7), Bronze
                if "rot" in farbe or "orange" in farbe or "rosa" in farbe or "kupfer" in farbe:
                    self.kategorien["kupfer"].append(teil)
                elif "gelb" in farbe or "gold" in farbe or "messing" in farbe:
                    self.kategorien["messing"].append(teil)
                else:
                    # Schwere, nicht magnetische, nicht eindeutig gefärbt -> evtl. Edelstahl oder Nickel
                    self.kategorien["edelstahl"].append(teil)
            elif dichte > 2.5:
                # Leichte Metalle: Aluminium (~2.7), Titan (~4.5), Magnesium (~1.7)
                if dichte < 3.0:
                    self.kategorien["aluminium"].append(teil)
                else:
                    # Dichte 3-8: Titan, evtl. spezielle Legierungen, oder einfach 'sonstiges'
                    self.kategorien["sonstiges"].append(teil)
            elif dichte > 0:
                # Sehr leicht (Magnesium, Kunststoffe mit Metallbeschichtung, Dreck)
                self.kategorien["sonstiges"].append(teil)
            else:
                # Keine Gewichtsangabe -> Fallback auf Farbe/Material-String
                mat = teil.get("material", "").lower()
                if "alu" in mat:
                    self.kategorien["aluminium"].append(teil)
                elif "kupfer" in mat:
                    self.kategorien["kupfer"].append(teil)
                elif "messing" in mat:
                    self.kategorien["messing"].append(teil)
                elif "edelstahl" in mat or "v2a" in mat or "v4a" in mat:
                    self.kategorien["edelstahl"].append(teil)
                else:
                    self.kategorien["schrott"].append(teil)
        
        return self.kategorien


if __name__ == "__main__":
    # Testlauf für neuer_tag
    print("=== Test neuer_tag ===")
    test_faelle = [
        {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen": 5}, "stimmung": 10, "wetter": "regen"},
        {"gestern": {}, "fehlschlaege": {}, "stimmung": 30, "wetter": "sonnig"},
        {"gestern": {"am_projekt_arbeiten": 1}, "fehlschlaege": {"am_projekt_arbeiten": 3}, "stimmung": 50, "wetter": "bewoelkt", "kakerlaken_level": 2},
        {"gestern": {"spazieren": 1}, "fehlschlaege": {}, "stimmung": -60, "wetter": "sonnig", "kakerlaken_level": 8},
    ]
    for i, daten in enumerate(test_faelle):
        ergebnis = neuer_tag(daten)
        print(f"Test {i+1}: {ergebnis}")
    
    # Testlauf für MetallSortierer
    print("\n=== Test MetallSortierer ===")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "farbe": "silber", "gewicht_g": 50, "volumen_cm3": 6.4, "fundort": "Werkbank"},
        {"name": "Alu-Profil", "material": "Aluminium", "farbe": "silber", "gewicht_g": 300, "volumen_cm3": 111, "fundort": "Boden hinter Karton"},
        {"name": "Kupferrohr", "material": "Kupfer", "farbe": "rot", "gewicht_g": 890, "volumen_cm3": 100, "fundort": "Regal"},
        {"name": "Messing-Ventil", "material": "Messing", "farbe": "gold", "gewicht_g": 200, "volumen_cm3": 23, "fundort": "Kiste"},
        {"name": "Edelstahl-Schale", "material": "V2A", "farbe": "silber", "gewicht_g": 500, "volumen_cm3": 64, "fundort": "Spüle"},
        {"name": "Magnetischer Schrott", "material": "Eisen", "farbe": "rostbraun", "gewicht_g": 1000, "volumen_cm3": 127, "fundort": "Ecke feucht"},
        {"name": "Unbekanntes Teil", "farbe": "grau", "gewicht_g": 50, "volumen_cm3": 10, "fundort": "Dunkel"},
        {"name": "Leichtes Ding", "material": "Titan", "farbe": "grau", "gewicht_g": 45, "volumen_cm3": 10, "fundort": "Boden"},
        "kein_dict_objekt",
    ]
    ergebnis = sorter.sortiere_metall(test_teile)
    for kat, teile in ergebnis.items():
        if teile:
            print(f"{kat} ({len(teile)}):")
            for t in teile:
                if isinstance(t, dict):
                    print(f"  - {t.get('name', t.get('objekt', '?'))} (Dichte: {sorter.gewicht_test(t):.1f} g/cm³, Warnung: {t.get('kakerlaken_warnung', False)})")
                else:
                    print(f"  - {t}")
    print("\nFertig.")