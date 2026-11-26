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
            
            # 2. Nicht magnetisch -> Alu, Kupfer, Messing, Edelstahl
            if dichte > 8.0:
                if "rot" in farbe or "orange" in farbe or "rosa" in farbe:
                    self.kategorien["kupfer"].append(teil)
                elif "gelb" in farbe or "gold" in farbe:
                    self.kategorien["messing"].append(teil)
                else:
                    self.kategorien["kupfer"].append(teil)
            elif dichte > 2.5 and dichte < 3.0:
                self.kategorien["aluminium"].append(teil)
            elif dichte > 7.5:
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
    test_daten = {"gestern": {}, "fehlschlaege": {}, "stimmung": 30, "wetter": "sonnig", "kakerlaken_level": 0}
    print(neuer_tag(test_daten))
    
    test_daten2 = {"gestern": {"am_projekt_arbeiten": 1}, "fehlschlaege": {"am_projekt_arbeiten": 3}, "stimmung": 10, "wetter": "regen", "kakerlaken_level": 5}
    print(neuer_tag(test_daten2))
    
    test_daten3 = {"gestern": {}, "fehlschlaege": {}, "stimmung": 50, "wetter": "bewoelkt", "kakerlaken_level": 8}
    print(neuer_tag(test_daten3))

    # Test MetallSortierer
    print("\n--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M8", "material": "Stahl", "gewicht_g": 15, "volumen_cm3": 2, "farbe": "silber", "fundort": "Regal"},
        {"name": "Kupferrohr Stück", "material": "Kupfer", "gewicht_g": 300, "volumen_cm3": 34, "farbe": "rot", "fundort": "Ecke hinter Karton"},
        {"name": "Alu-Profil Rest", "material": "Aluminium", "gewicht_g": 50, "volumen_cm3": 18, "farbe": "silber", "fundort": "Boden"},
        {"name": "Edelstahlschale", "material": "V2A", "gewicht_g": 200, "volumen_cm3": 25, "farbe": "silber", "fundort": "Arbeitsplatte"},
        {"name": "Messingverschraubung", "material": "Messing", "gewicht_g": 80, "volumen_cm3": 9, "farbe": "gold", "fundort": "Schublade"},
        {"name": "Unbekanntes Teil", "material": "Plastik", "gewicht_g": 5, "volumen_cm3": 10, "farbe": "schwarz", "fundort": "dunkle Ecke"},
        "kein_dict_objekt",
        {"name": "Leichtes Etwas", "gewicht_g": 0, "volumen_cm3": 0, "farbe": "weiss", "fundort": "Regal"}
    ]
    ergebnis = sorter.sortiere_metall(test_teile)
    for kat, teile in ergebnis.items():
        if teile:
            print(f"{kat}: {len(teile)} Teile")
            for t in teile:
                if isinstance(t, dict):
                    warn = " ⚠ KAKERLAKEN!" if t.get('kakerlaken_warnung') else ""
                    print(f"  - {t.get('name', t.get('objekt', '?'))}{warn}")
                else:
                    print(f"  - {t}")