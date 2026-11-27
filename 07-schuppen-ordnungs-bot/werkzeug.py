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
            magnetisch = self.magnet_test(teil)
            kakerlaken_alarm = self.check_kakerlaken_gefahr(teil)
            
            # Basis-Eintrag für verdächtige Teile (duplizieren in kakerlaken_verdaechtig)
            basis_eintrag = {"name": name, "dichte": round(dichte, 2), "magnet": magnetisch, "farbe": farbe, "fundort": teil.get("fundort", "?")}
            
            if kakerlaken_alarm:
                self.kategorien["kakerlaken_verdaechtig"].append(basis_eintrag)
            
            # Entscheidungsbaum
            if magnetisch:
                # Ferromagnetisch: Eisen, Stahl, Guss, *ferritischer* Edelstahl
                funken = self.funken_test(teil)
                if funken == "edelstahl" or ("edelstahl" in teil.get("material", "").lower() and dichte > 7.0):
                    self.kategorien["edelstahl"].append(basis_eintrag)
                elif funken == "gusseisen" or "guss" in teil.get("material", "").lower():
                    self.kategorien["eisenhaltig"].append({**basis_eintrag, "typ": "Gusseisen"})
                else:
                    self.kategorien["eisenhaltig"].append({**basis_eintrag, "typ": "Stahl/Eisen"})
            else:
                # Nicht magnetisch: Alu, Kupfer, Messing, austenitischer Edelstahl, Sonstiges
                if dichte < 3.0:  # Alu ~2.7
                    self.kategorien["aluminium"].append(basis_eintrag)
                elif 3.0 <= dichte < 7.5:  # Lücke: Titan, Magnesium, Legierungen
                    self.kategorien["sonstiges"].append({**basis_eintrag, "vermutung": "Leichtmetall-Legierung?"})
                elif 7.5 <= dichte < 8.5:  # Edelstahl (austenitisch) ~7.9, Eisen (wenn nicht magnetisch? unwahrscheinlich)
                    if "edelstahl" in teil.get("material", "").lower() or farbe in ["silber", "grau", "blank"]:
                        self.kategorien["edelstahl"].append(basis_eintrag)
                    else:
                        self.kategorien["sonstiges"].append({**basis_eintrag, "vermutung": "Dicht wie Stahl, aber nicht magnetisch?"})
                elif 8.5 <= dichte < 9.0:  # Messing ~8.4 - 8.7
                    if farbe in ["gelb", "gold", "messing"]:
                        self.kategorien["messing"].append(basis_eintrag)
                    else:
                        self.kategorien["sonstiges"].append({**basis_eintrag, "vermutung": "Kupfer-Legierung?"})
                elif dichte >= 8.9:  # Kupfer ~8.96
                    if farbe in ["rot", "kupfer", "braun", "grün"]: # Grün = Patina
                        self.kategorien["kupfer"].append(basis_eintrag)
                    else:
                        self.kategorien["sonstiges"].append({**basis_eintrag, "vermutung": "Schwermetall?"})
                else:
                    self.kategorien["schrott"].append({**basis_eintrag, "grund": "Keine Zuordnung möglich"})
        
        return self.kategorien
    
    def get_bericht(self):
        """Gibt Text-Zusammenfassung der Sortierung zurück."""
        lines = ["=== Schuppen-Sortier-Bericht ==="]
        total = 0
        for kat, teile in self.kategorien.items():
            if teile:
                lines.append(f"{kat.upper()} ({len(teile)}):")
                for t in teile[:5]: # Max 5 pro Katze anzeigen
                    lines.append(f"  - {t.get('name', '?')} (Dichte: {t.get('dichte', '?')}, Magnet: {t.get('magnet', '?')})")
                if len(teile) > 5:
                    lines.append(f"  ... und {len(teile)-5} weitere")
                total += len(teile)
        lines.append(f"\nGesamt sortierte Einträge: {total} (inkl. Duplikate Kakerlaken-Check)")
        if self.kategorien["kakerlaken_verdaechtig"]:
            lines.append("\nACHTUNG: Teile aus verseuchten Zonen gefunden! Handschuhe waschen.")
        return "\n".join(lines)
    
    def export_kategorien(self):
        """Gibt Dict zurück für JSON-Speicher oder Weiterverarbeitung."""
        # Kopie ohne interne Logik
        return {k: list(v) for k, v in self.kategorien.items()}


if __name__ == "__main__":
    # Test neuer_tag
    print("--- Test neuer_tag ---")
    test_daten = {
        "gestern": {"think": 12, "eat": 3, "am_projekt_arbeiten": 1},
        "fehlschlaege": {"am_projekt_arbeiten": 4, "schrott_suchen": 1},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 2
    }
    erg = neuer_tag(test_daten)
    print(f"Notiz: {erg.get('notiz')}")
    print(f"Plan: {erg.get('plan')}")
    
    # Test KI-Frage Trigger
    if "frage_an_ki" in erg:
        print(f"FRAGE AN KI: {erg['frage_an_ki']}")
        # Simuliere KI-Antwort
        test_daten["ki_antwort"] = "Prüfe Volumen != 0 und Material-Strings auf Tippfehler. Nutze .get() mit Defaults."
        erg2 = neuer_tag(test_daten)
        print(f"Nach KI-Rat: {erg2.get('notiz')}")
        print(f"Plan: {erg2.get('plan')}")

    print("\n--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "gewicht_g": 50, "volumen_cm3": 6.4, "farbe": "silber", "fundort": "Regal links"},
        {"name": "Alu-Profil", "material": "Aluminium", "gewicht_g": 300, "volumen_cm3": 111, "farbe": "grau", "fundort": "Boden hinter Karton"},
        {"name": "Kupferrohr", "material": "Kupfer", "gewicht_g": 890, "volumen_cm3": 100, "farbe": "rot", "fundort": "Ecke feucht"},
        {"name": "Messing-Ventil", "material": "Messing", "gewicht_g": 420, "volumen_cm3": 50, "farbe": "gold", "fundort": "Schublade"},
        {"name": "Edelstahl-Schraube (ferritisch)", "material": "Edelstahl 430", "gewicht_g": 20, "volumen_cm3": 2.5, "farbe": "silber", "fundort": "Kasten"},
        {"name": "Edelstahl-Topf (austenitisch)", "material": "Edelstahl 304", "gewicht_g": 500, "volumen_cm3": 63, "farbe": "blank", "fundort": "Spüle"},
        {"name": "Guss-Eisenstück", "material": "Grauguss", "gewicht_g": 1200, "volumen_cm3": 150, "farbe": "grau", "fundort": "dunkle Ecke"},
        "kein dict", # Fehlerfall
        {"name": "Mysterie-Metall", "material": "Unobtainium", "gewicht_g": 100, "volumen_cm3": 10, "farbe": "lila", "fundort": "Karton"}
    ]
    res = sorter.sortiere_metall(test_teile)
    print(sorter.get_bericht())
    # print(json.dumps(sorter.export_kategorien(), indent=2, ensure_ascii=False))