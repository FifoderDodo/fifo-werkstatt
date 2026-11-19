def neuer_tag(daten):
    """
    Entscheidungslogik für einen neuen Tag im Schuppen.
    Nimmt Status-Dict, gibt Plan-Dict zurück.
    """
    # Standardwerte falls Keys fehlen
    gestern = daten.get("gestern", {})
    fehlschlaege = daten.get("fehlschlaege", {})
    stimmung = daten.get("stimmung", 0)
    wetter = daten.get("wetter", "bewoelkt").lower()  # Fix: Case-insensitive
    
    notiz = ""
    plan = []
    
    # Erstmal Grundbedürfnisse prüfen
    if stimmung < -50:
        notiz = "Stimmung im Keller. Erst frische Luft schnappen."
        plan.append({"aktion": "spazieren", "text": "Kopf freibekommen vor dem Schuppen"})
    elif stimmung < 20:
        notiz = "Laune mittelmäßig. Kaffee wäre gut."
        plan.append({"aktion": "drink", "text": "Wasser oder Kaffee trinken"})
    
    # Wetter checken für Outdoor-Aktionen (Fix: Limit beachten)
    if wetter in ["sonnig", "heiter"] and len(plan) < 3:
        if "spazieren" not in [p["aktion"] for p in plan]:
            if not plan or plan[-1]["aktion"] != "spazieren":
                 plan.append({"aktion": "spazieren", "text": "Gutes Wetter nutzen, kurz raus"})
    
    # Projektarbeit: Metall-Sortierlogik basteln
    # Nur wenn nicht total frustriert und nicht schon 3 Aktionen
    if len(plan) < 3 and stimmung > -70:
        # Prüfen ob gestern schon am Projekt war
        war_am_projekt = "am_projekt_arbeiten" in gestern
        fehlschlaege_projekt = fehlschlaege.get("am_projekt_arbeiten", 0)
        
        if fehlschlaege_projekt > 2:
            # Fix: Notiz anhängen statt überschreiben
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
            "schrott": []
        }
    
    def magnet_test(self, teil):
        """Simuliert Magnet-Test. True = ferromagnetisch (Eisen/Stahl)."""
        # Platzhalter: Später echte Sensor-Logik oder DB-Lookup
        material = teil.get("material", "").lower()
        return any(m in material for m in ["eisen", "stahl", "ferro"])
    
    def funken_test(self, teil):
        """Simuliert Funkenbild-Test (Grobe Klassifikation)."""
        # Platzhalter für spätere Expansion
        return "unbekannt"
    
    def gewicht_test(self, teil):
        """Dichte-Abschätzung über Gewicht/Volumen. Gibt Dichte in g/cm³ zurück."""
        gewicht = teil.get("gewicht_g", 0)
        volumen = teil.get("volumen_cm3", 1)
        return gewicht / volumen if volumen > 0 else 0.0
    
    def sortiere_metall(self, teile_liste):
        """Hauptlogik: Iteriert Teile, sortiert in Kategorien."""
        # Reset Kategorien für neuen Durchlauf
        for k in self.kategorien:
            self.kategorien[k] = []
            
        for teil in teile_liste:
            if not isinstance(teil, dict):
                self.kategorien["schrott"].append({"objekt": teil, "grund": "Kein Dict"})
                continue
            
            name = teil.get("name", "Unbekannt")
            farbe = teil.get("farbe", "").lower()
            dichte = self.gewicht_test(teil)
            
            # 1. Magnet-Test
            if self.magnet_test(teil):
                # Magnetisch -> Eisen/Stahl (oder ferritischer Edelstahl, aber egal, Schrottplatz zahlt nach Magnet)
                self.kategorien["eisenhaltig"].append(teil)
                continue
            
            # 2. Nicht magnetisch -> Alu, Kupfer, Messing, Edelstahl (austenitisch V2A/V4A)
            # Entscheidung über Dichte & Farbe
            if dichte > 8.0:  # Kupfer ~8.9, Messing ~8.4-8.7
                if "rot" in farbe or "orange" in farbe or "rosa" in farbe:
                    self.kategorien["kupfer"].append(teil)
                elif "gelb" in farbe or "gold" in farbe:
                    self.kategorien["messing"].append(teil)
                else:
                    self.kategorien["kupfer"].append(teil)  # Default schwer & nicht magnetisch
            elif dichte > 2.5 and dichte < 3.0:  # Alu ~2.7
                self.kategorien["aluminium"].append(teil)
            elif dichte > 7.5:  # Edelstahl ~7.9 (schwer, nicht magnetisch)
                self.kategorien["edelstahl"].append(teil)
            elif dichte > 0:
                self.kategorien["sonstiges"].append(teil)
            else:
                self.kategorien["schrott"].append({"objekt": teil, "grund": "Keine Masse/Dichte"})
        
        return self.kategorien


# Hilfsfunktion für schnellen Test
if __name__ == "__main__":
    # Test neuer_tag
    print("--- Test neuer_tag ---")
    test_daten = {"gestern": {}, "fehlschlaege": {}, "stimmung": 30, "wetter": "sonnig"}
    print(neuer_tag(test_daten))
    
    test_daten2 = {"gestern": {"am_projekt_arbeiten": 1}, "fehlschlaege": {"am_projekt_arbeiten": 3}, "stimmung": 10, "wetter": "regen"}
    print(neuer_tag(test_daten2))

    # Test MetallSortierer
    print("\n--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "farbe": "silber", "gewicht_g": 50, "volumen_cm3": 6.4},
        {"name": "Kupferrohr", "material": "Kupfer", "farbe": "rot", "gewicht_g": 200, "volumen_cm3": 22.5},
        {"name": "Alu-Profil", "material": "Aluminium", "farbe": "silber", "gewicht_g": 135, "volumen_cm3": 50.0},
        {"name": "Edelstahl-Schraube V2A", "material": "Edelstahl", "farbe": "silber", "gewicht_g": 30, "volumen_cm3": 3.8},
        {"name": "Messing-Verschraubung", "material": "Messing", "farbe": "gold", "gewicht_g": 80, "volumen_cm3": 9.5},
        {"name": "Plastikteil", "material": "Kunststoff", "farbe": "schwarz", "gewicht_g": 10, "volumen_cm3": 20.0},
        "kein_dict_objekt",
        {"name": "Defektes Teil", "material": "Stahl", "farbe": "rost", "gewicht_g": 100}  # volumen fehlt
    ]
    ergebnis = sorter.sortiere_metall(test_teile)
    for kat, teile in ergebnis.items():
        if teile:
            print(f"{kat}: {[t.get('name', t) for t in teile]}")