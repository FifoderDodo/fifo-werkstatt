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
            dichte = self.gewicht_test(teil)
            material_hinweis = teil.get("material", "").lower()
            magnetisch = self.magnet_test(teil)
            
            # Kakerlaken-Check: Teile markieren, aber normal weiter sortieren
            kakerlaken_verdaechtig = self.check_kakerlaken_gefahr(teil)
            if kakerlaken_verdaechtig:
                teil_kopie = teil.copy()
                teil_kopie["kakerlaken_warnung"] = True
                self.kategorien["kakerlaken_verdaechtig"].append(teil_kopie)
            
            # 1. Magnetisch -> Eisenhaltig (Stahl, Guss, Eisen)
            if magnetisch:
                # Edelstahl kann magnetisch sein (ferritisch/martensitisch), aber Dichte prüfen
                if "edelstahl" in material_hinweis or (7.5 <= dichte <= 8.2 and "rostfrei" in material_hinweis):
                     self.kategorien["edelstahl"].append(teil)
                else:
                    self.kategorien["eisenhaltig"].append(teil)
                continue
            
            # 2. Nicht magnetisch -> Dichte-Baum
            # Alu: ~2.7 g/cm³
            if dichte < 3.5:
                if "aluminium" in material_hinweis or "alu" in material_hinweis or farbe in ["silber", "grau", "weiss"]:
                    self.kategorien["aluminium"].append(teil)
                else:
                    self.kategorien["sonstiges"].append(teil)
            # Edelstahl (austenitisch): ~7.9 g/cm³, nicht magnetisch
            elif 7.5 <= dichte <= 8.3:
                if "edelstahl" in material_hinweis or "rostfrei" in material_hinweis:
                    self.kategorien["edelstahl"].append(teil)
                # Messing/Bronze/Kupfer überschneiden sich hier, Farbe/Funken entscheiden
                elif "gelb" in farbe or "gold" in farbe or "messing" in material_hinweis:
                    self.kategorien["messing"].append(teil)
                elif "rot" in farbe or "kupfer" in material_hinweis or "kupferfarbig" in farbe:
                    self.kategorien["kupfer"].append(teil)
                else:
                    self.kategorien["edelstahl"].append(teil)  # Default für schwere nicht-magnetische
            # Kupfer: ~8.9 g/cm³
            elif 8.4 <= dichte <= 9.2:
                if "kupfer" in material_hinweis or "rot" in farbe or "orange" in farbe:
                    self.kategorien["kupfer"].append(teil)
                elif "messing" in material_hinweis or "gelb" in farbe:
                    self.kategorien["messing"].append(teil)
                else:
                    self.kategorien["kupfer"].append(teil)
            # Messing/Bronze: ~8.4 - 8.7 g/cm³ (oft Überlappung mit Kupfer)
            # Blei/Zink: ~7.1 / 11.3 -> Sonstiges/Schrott
            else:
                self.kategorien["sonstiges"].append(teil)
        
        return self.kategorien
    
    def get_bericht(self):
        """Gibt Zusammenfassung als Text zurück."""
        lines = ["=== Schuppen-Metall-Bericht ==="]
        total = 0
        for kat, teile in self.kategorien.items():
            anzahl = len(teile)
            total += anzahl
            if anzahl > 0:
                lines.append(f"{kat.capitalize()}: {anzahl} Stk")
                # Zeige erste 3 Namen
                namen = [t.get('name', '?') for t in teile[:3]]
                lines.append(f"  z.B.: {', '.join(namen)}")
        lines.append(f"Gesamt: {total} Teile sortiert.")
        return "\n".join(lines)
    
    def export_kategorien(self):
        """Gibt Dict zurück für JSON-Speicher/Weiterverarbeitung."""
        # Deepcopy vermeiden, aber Referenzen auf Original-Objekte sind okay für Export
        return {k: list(v) for k, v in self.kategorien.items()}


if __name__ == "__main__":
    # Test für neuer_tag
    print("--- Test neuer_tag ---")
    test_daten = {
        "gestern": {"think": 12, "eat": 3, "am_projekt_arbeiten": 1},
        "fehlschlaege": {"am_projekt_arbeiten": 4, "schrott_suchen": 1},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 2
    }
    ergebnis = neuer_tag(test_daten)
    print(f"Notiz: {ergebnis['notiz']}")
    print(f"Plan: {ergebnis['plan']}")
    
    # Test KI-Frage (simuliert 2. Aufruf mit Antwort)
    if "frage_an_ki" in ergebnis:
        print(f"FRAGE AN KI: {ergebnis['frage_an_ki']}")
        test_daten["ki_antwort"] = "Prüfe Dichte-Schwellenwerte & Material-Strings. Nutze Typ-Hints."
        ergebnis2 = neuer_tag(test_daten)
        print(f"Notiz 2: {ergebnis2['notiz']}")
        print(f"Plan 2: {ergebnis2['plan']}")

    print("\n--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "gewicht_g": 50, "volumen_cm3": 6.4, "fundort": "Regal A", "farbe": "silber"},
        {"name": "Alu-Profil 1m", "material": "Aluminium", "gewicht_g": 300, "volumen_cm3": 111, "fundort": "Boden Ecke", "farbe": "grau"},
        {"name": "Rohrstück", "material": "Edelstahl V2A", "gewicht_g": 200, "volumen_cm3": 25, "fundort": "Karton hinter Regal", "farbe": "silber"},
        {"name": "Kupferleitung", "material": "Kupfer", "gewicht_g": 150, "volumen_cm3": 17, "fundort": "Werkbank", "farbe": "rot"},
        {"name": "Messing-Ventil", "material": "Messing", "gewicht_g": 80, "volumen_cm3": 9.5, "fundort": "Schublade", "farbe": "gold"},
        {"name": "Rostiger Nagel", "material": "Eisen", "gewicht_g": 5, "volumen_cm3": 0.6, "fundort": "Boden", "farbe": "braun"},
        {"name": "Unbekanntes Teil", "material": "", "gewicht_g": 100, "volumen_cm3": 12, "fundort": "Dunkle Ecke", "farbe": "grau"},
        "Kein Dict Objekt",  # Fehlerfall
        {"name": "Magnetischer Edelstahl", "material": "Edelstahl 430", "gewicht_g": 50, "volumen_cm3": 6.3, "fundort": "Kiste", "farbe": "silber"},  # Ferritisch
    ]
    
    result = sorter.sortiere_metall(test_teile)
    print(sorter.get_bericht())
    
    # Export Test
    export = sorter.export_kategorien()
    print(f"\nExport Keys: {list(export.keys())}")
    print(f"Kakerlaken verdächtig: {len(export['kakerlaken_verdaechtig'])} Teile")
    for t in export['kakerlaken_verdaechtig']:
        print(f"  - {t['name']} (Fundort: {t['fundort']})")

    # Test Kakerlaken Level hoch
    print("\n--- Test Kakerlaken Alarm ---")
    alarm_daten = {**test_daten, "kakerlaken_level": 8}
    print(neuer_tag(alarm_daten))