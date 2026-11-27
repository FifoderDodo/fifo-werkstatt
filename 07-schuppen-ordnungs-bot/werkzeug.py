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
            basis_eintrag = {"name": name, "dichte": round(dichte, 2), "magnetisch": magnetisch, "fundort": teil.get("fundort", "?")}
            
            if kakerlaken_alarm:
                self.kategorien["kakerlaken_verdaechtig"].append({**basis_eintrag, "warnung": "Möglicherweise kontaminiert"})
            
            # Entscheidungsbaum: Magnet -> Dichte -> Farbe
            if magnetisch:
                # Ferromagnetisch: Eisen, Stahl, Guss, ferritischer Edelstahl
                if dichte > 7.5:
                    # Schwere magnetische Metalle
                    if "chrom" in teil.get("material", "").lower() or "edelstahl" in teil.get("material", "").lower():
                        self.kategorien["edelstahl"].append({**basis_eintrag, "typ": "ferritisch/martensitisch"})
                    else:
                        self.kategorien["eisenhaltig"].append({**basis_eintrag, "typ": "stahl/eisen/guss"})
                else:
                    # Leicht magnetisch? Eher unwahrscheinlich für reines Metall, aber Sicherheit
                    self.kategorien["eisenhaltig"].append({**basis_eintrag, "typ": "leicht_magnetisch"})
            else:
                # Nicht magnetisch: Alu, Kupfer, Messing, austenitischer Edelstahl
                if dichte < 3.0:
                    self.kategorien["aluminium"].append({**basis_eintrag, "typ": "leichtmetall"})
                elif dichte > 8.5:
                    # Schwere Nicht-Eisen-Metalle
                    if farbe in ["rot", "rotbraun", "kupfer"]:
                        self.kategorien["kupfer"].append({**basis_eintrag, "typ": "kupfer"})
                    elif farbe in ["gelb", "gold", "messing"]:
                        self.kategorien["messing"].append({**basis_eintrag, "typ": "messing"})
                    else:
                        # Grau/silber & schwer & nicht magnetisch -> Austenitischer Edelstahl
                        self.kategorien["edelstahl"].append({**basis_eintrag, "typ": "austenitisch (vermutlich)"})
                elif 3.0 <= dichte <= 8.5:
                    # Mittlere Dichte: Titan, Messing (manchmal), spezielle Legierungen
                    if farbe in ["gelb", "gold"]:
                        self.kategorien["messing"].append({**basis_eintrag, "typ": "messing/legierung"})
                    else:
                        self.kategorien["sonstiges"].append({**basis_eintrag, "typ": "mittlere_dichte"})
                else:
                    self.kategorien["schrott"].append({**basis_eintrag, "grund": "Dichte unplausibel"})
        
        return self.kategorien
    
    def get_bericht(self):
        """Gibt Text-Zusammenfassung der Sortierung zurück."""
        lines = ["=== Schuppen-Sortier-Bericht ==="]
        total = 0
        for kat, teile in self.kategorien.items():
            anzahl = len(teile)
            total += anzahl
            if anzahl > 0:
                lines.append(f"{kat.replace('_', ' ').title()}: {anzahl} Stück")
                for t in teile[:3]:  # Nur erste 3 anzeigen
                    lines.append(f"  - {t.get('name', '?')} (Dichte: {t.get('dichte', '?')}, Mag: {t.get('magnetisch', '?')})")
                if anzahl > 3:
                    lines.append(f"  ... und {anzahl - 3} weitere")
        lines.append(f"---\nGesamt sortiert: {total} Teile")
        if self.kategorien["kakerlaken_verdaechtig"]:
            lines.append("!!! ACHTUNG: Kakerlaken-verdächtige Teile gefunden! Handschuhe waschen! !!!")
        return "\n".join(lines)
    
    def export_kategorien(self):
        """Gibt Dict zurück für JSON-Speicher oder Weiterverarbeitung."""
        return {k: v for k, v in self.kategorien.items() if v}  # Nur nicht-leere


if __name__ == "__main__":
    # Test-Daten für neuen Tag
    test_daten = {
        "gestern": {"think": 12, "eat": 3, "am_projekt_arbeiten": 1},
        "fehlschlaege": {"am_projekt_arbeiten": 2, "schrott_suchen": 1},
        "stimmung": 15,
        "wetter": "sonnig",
        "kakerlaken_level": 3
    }
    print("=== Test neuer_tag ===")
    erg = neuer_tag(test_daten)
    print(f"Notiz: {erg['notiz']}")
    print(f"Plan: {erg['plan']}")
    
    # Test mit KI-Antwort (Simuliert zweiten Aufruf)
    test_daten_ki = {**test_daten, "ki_antwort": "Prüfe Volumen != 0 und Material-Strings auf Tippfehler. Nutze .get mit Defaults."}
    erg2 = neuer_tag(test_daten_ki)
    print(f"\nMit KI-Rat: {erg2['notiz']}")
    
    # Test MetallSortierer
    print("\n=== Test MetallSortierer ===")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "gewicht_g": 50, "volumen_cm3": 6.4, "farbe": "silber", "fundort": "Regal links"},
        {"name": "Rohrstück", "material": "Edelstahl V2A", "gewicht_g": 300, "volumen_cm3": 38, "farbe": "silber", "fundort": "Ecke hinten feucht"},  # Austenitisch, nicht magnetisch, dicht ~7.9
        {"name": "Blechstreifen", "material": "Edelstahl 430 (ferritisch)", "gewicht_g": 200, "volumen_cm3": 25.3, "farbe": "silber", "fundort": "Boden bei Kartons"},  # Ferritisch, magnetisch
        {"name": "Alu-Profil", "material": "Aluminium 6060", "gewicht_g": 150, "volumen_cm3": 55.5, "farbe": "grau", "fundort": "Regal rechts"},
        {"name": "Kupferleitung", "material": "Kupfer", "gewicht_g": 400, "volumen_cm3": 44.7, "farbe": "rot", "fundort": "Kasten oben"},
        {"name": "Messing-Verschraubung", "material": "Messing", "gewicht_g": 120, "volumen_cm3": 15.2, "farbe": "gelb", "fundort": "Schublade"},
        {"name": "Guss-Eisenstück", "material": "Grauguss", "gewicht_g": 500, "volumen_cm3": 64, "farbe": "grau", "fundort": "Ecke dunkel"},
        "Kein Dict sondern String",  # Fehlerfall
        {"name": "Mysterie-Teil", "material": "Titan", "gewicht_g": 100, "volumen_cm3": 22, "farbe": "grau", "fundort": "Hinter dem Ofen"}  # Dichte ~4.5 -> sonstiges
    ]
    ergebnis = sorter.sortiere_metall(test_teile)
    print(sorter.get_bericht())
    print("\nExport (JSON-ready):")
    import json
    print(json.dumps(sorter.export_kategorien(), indent=2, ensure_ascii=False))
    
    # Test Kakerlaken-Level hoch
    print("\n=== Test Kakerlaken-Alarm (Level 8) ===")
    test_alarm = {**test_daten, "kakerlaken_level": 8}
    print(neuer_tag(test_alarm))