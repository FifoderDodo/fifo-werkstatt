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
                # Kopie in Warn-Kategorie für Überblick
                self.kategorien["kakerlaken_verdaechtig"].append(teil.copy())
            
            # Entscheidungsbaum
            if magnetisch:
                # Magnetisch -> Eisen, Stahl, Gusseisen, evtl. magnetischer Edelstahl
                funken = self.funken_test(teil)
                if funken == "edelstahl" or "edelstahl" in material_hinweis:
                    self.kategorien["edelstahl"].append(teil)
                elif funken == "gusseisen" or dichte > 7.0: # Gusseisen oft ~7.2, Stahl ~7.8
                    self.kategorien["eisenhaltig"].append({**teil, "vermutung": "Gusseisen/Stahl"})
                else:
                    self.kategorien["eisenhaltig"].append({**teil, "vermutung": "Eisen/Stahl"})
            else:
                # Nicht magnetisch -> Alu, Kupfer, Messing, Edelstahl (austenitisch), Zink, Blei
                if dichte < 3.0: # Alu ~2.7, Titan ~4.5, Magnesium ~1.7
                    if dichte < 2.0:
                        self.kategorien["sonstiges"].append({**teil, "vermutung": "Sehr leicht (Mg/Titan?)"})
                    else:
                        self.kategorien["aluminium"].append({**teil, "vermutung": "Aluminium/Legierung"})
                elif 3.0 <= dichte < 5.0:
                    self.kategorien["sonstiges"].append({**teil, "vermutung": "Titan/Zink/Legierung (Dichte " + f"{dichte:.1f})"})
                elif 7.5 <= dichte < 8.2:
                    # Edelstahl (austenitisch) ~7.9, Zinn ~7.3
                    if "edelstahl" in material_hinweis or "v2a" in material_hinweis or "v4a" in material_hinweis:
                        self.kategorien["edelstahl"].append(teil)
                    else:
                        self.kategorien["sonstiges"].append({**teil, "vermutung": "Edelstahl/Zinn (Dichte " + f"{dichte:.1f})"})
                elif 8.2 <= dichte < 9.0:
                    # Messing ~8.4-8.7, Bronze ~8.8
                    if "messing" in material_hinweis or "gelb" in farbe or "gold" in farbe:
                        self.kategorien["messing"].append({**teil, "vermutung": "Messing"})
                    else:
                        self.kategorien["kupfer"].append({**teil, "vermutung": "Bronze/Kupfer-Leg"})
                elif dichte >= 8.9:
                    # Kupfer ~8.96, Blei ~11.3
                    if "kupfer" in material_hinweis or "rot" in farbe or "orange" in farbe or "grün" in farbe:
                        self.kategorien["kupfer"].append({**teil, "vermutung": "Kupfer"})
                    else:
                        self.kategorien["sonstiges"].append({**teil, "vermutung": "Schwermetall (Blei/Wolfram?)"})
                else:
                    self.kategorien["sonstiges"].append({**teil, "vermutung": "Dichte-Lücke " + f"{dichte:.1f}"})
        
        return self.kategorien
    
    def get_bericht(self):
        """Gibt Zusammenfassung als Text zurück."""
        lines = ["=== Schuppen-Metall-Bericht ==="]
        total = 0
        for kat, teile in self.kategorien.items():
            anzahl = len(teile)
            total += anzahl
            if anzahl > 0:
                lines.append(f"{kat}: {anzahl} Stück")
                # Zeige erste 3 Namen
                namen = [t.get('name', '?') for t in teile[:3]]
                lines.append(f"  z.B.: {', '.join(namen)}")
        lines.append(f"Gesamt: {total} Teile sortiert.")
        if self.kategorien["kakerlaken_verdaechtig"]:
            lines.append("!!! VORSICHT: Kakerlaken-verdächtige Teile dabei !!!")
        return "\n".join(lines)
    
    def export_kategorien(self):
        """Gibt sauberes Dict zurück (ohne interne Felder falls gewünscht)."""
        # Hier einfach das Raw-Dict, aber man könnte kopieren
        return {k: list(v) for k, v in self.kategorien.items()}


if __name__ == "__main__":
    # Test-Daten: Realistischer Schuppen-Mix
    test_teile = [
        {"name": "Nagel 10cm", "material": "Stahl", "gewicht_g": 15, "volumen_cm3": 2.0, "fundort": "Wandhaken", "farbe": "grau"},
        {"name": "Alu-Profil Fenster", "material": "Aluminium", "gewicht_g": 450, "volumen_cm3": 170, "fundort": "Boden hinter Karton", "farbe": "silber", "notiz": "feucht"},
        {"name": "Kupferrohr 15mm", "material": "Kupfer", "gewicht_g": 320, "volumen_cm3": 36, "fundort": "Regal oben", "farbe": "rotbraun"},
        {"name": "Messing-Schraube", "material": "Messing", "gewicht_g": 8, "volumen_cm3": 1.0, "fundort": "Schraubendose", "farbe": "goldgelb"},
        {"name": "Edelstahl-Becher", "material": "V2A Edelstahl", "gewicht_g": 120, "volumen_cm3": 15, "fundort": "Ecke dunkel", "farbe": "silber"},
        {"name": "Gusseisen-Deckel", "material": "Gusseisen", "gewicht_g": 2500, "volumen_cm3": 320, "fundort": "Boden", "farbe": "schwarz"},
        {"name": "Mysterie-Würfel", "material": "Unbekannt", "gewicht_g": 50, "volumen_cm3": 10, "fundort": "Karton Nachtrag", "farbe": "grau"},
        "Das ist ein String, kein Dict", # Fehlerfall
        {"name": "Bleiloten-Rest", "material": "Blei", "gewicht_g": 113, "volumen_cm3": 10, "fundort": "Lötstation", "farbe": "blaugrau"},
    ]
    
    print("--- Test neuer_tag ---")
    # Test 1: Kakerlaken-Alarm
    daten1 = {"gestern": {}, "fehlschlaege": {}, "stimmung": 10, "wetter": "sonnig", "kakerlaken_level": 8}
    print(f"Input: {daten1}")
    print(f"Output: {neuer_tag(daten1)}")
    
    # Test 2: Normaler Tag, Projekt klemmt
    daten2 = {"gestern": {"am_projekt_arbeiten": 1}, "fehlschlaege": {"am_projekt_arbeiten": 3}, "stimmung": 30, "wetter": "regen", "kakerlaken_level": 2}
    print(f"Input: {daten2}")
    print(f"Output: {neuer_tag(daten2)}")
    
    # Test 3: Guter Tag
    daten3 = {"gestern": {"schrott_suchen": 2}, "fehlschlaege": {}, "stimmung": 80, "wetter": "heiter", "kakerlaken_level": 0}
    print(f"Input: {daten3}")
    print(f"Output: {neuer_tag(daten3)}")

    print("\n--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    ergebnis = sorter.sortiere_metall(test_teile)
    print(sorter.get_bericht())
    
    # Export pruefen
    export = sorter.export_kategorien()
    print(f"\nExport Keys: {list(export.keys())}")
    print(f"Alu Count: {len(export['aluminium'])}")
    print(f"Kakerlaken Warn Count: {len(export['kakerlaken_verdaechtig'])}")
    
    print("\n--- Fertig. Werkzeug scharf. ---")