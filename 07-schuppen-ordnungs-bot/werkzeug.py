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
            dichte = self.gewicht_test(teil)  # Typo repariert: gewicht_t -> gewicht_test
            magnetisch = self.magnet_test(teil)
            kakerlaken_alarm = self.check_kakerlaken_gefahr(teil)
            
            # Erst Kakerlaken-Check: Verdächtige Teile isolieren
            if kakerlaken_alarm:
                self.kategorien["kakerlaken_verdaechtig"].append({
                    **teil, "kategorie_grund": "Fundort verseucht"
                })
                # Trotzdem weiter sortieren, aber markiert
            
            # Logik: Magnetisch -> Eisen/Stahl/Guss
            if magnetisch:
                # Spezialfall: Ferritischer Edelstahl ist magnetisch, austenitischer nicht
                if "edelstahl" in teil.get("material", "").lower() or "v2a" in teil.get("material", "").lower() or "v4a" in teil.get("material", "").lower():
                    # Dichte-Check: Edelstahl ~7.9, Stahl ~7.85. Schwer zu trennen.
                    # Wenn explizit 'ferritisch' im Material oder Notiz -> edelstahl
                    if "ferrit" in teil.get("material", "").lower() or "ferrit" in teil.get("notiz", "").lower():
                        self.kategorien["edelstahl"].append({**teil, "kategorie_grund": "Magnetisch & Ferritisch (Edelstahl)"})
                    else:
                        self.kategorien["eisenhaltig"].append({**teil, "kategorie_grund": "Magnetisch (Eisen/Stahl/Guss)"})
                else:
                    self.kategorien["eisenhaltig"].append({**teil, "kategorie_grund": "Magnetisch (Eisen/Stahl/Guss)"})
            
            # Nicht magnetisch: Dichte & Farbe prüfen
            else:
                # Kupfer: Dichte ~8.9, Farbe rot/orange
                if 8.5 <= dichte <= 9.2 and any(c in farbe for c in ["rot", "orange", "kupfer", "pink"]):
                    self.kategorien["kupfer"].append({**teil, "kategorie_grund": "Dichte/Farbe: Kupfer"})
                # Messing: Dichte ~8.4-8.7, Farbe gelb/gold
                elif 8.0 <= dichte <= 8.7 and any(c in farbe for c in ["gelb", "gold", "messing", "hell"]):
                    self.kategorien["messing"].append({**teil, "kategorie_grund": "Dichte/Farbe: Messing"})
                # Aluminium: Dichte ~2.7, Farbe silbergrau/matt
                elif 2.5 <= dichte <= 3.0 and any(c in farbe for c in ["silber", "grau", "weiss", "aluminium", "hell"]):
                    self.kategorien["aluminium"].append({**teil, "kategorie_grund": "Dichte/Farbe: Aluminium"})
                # Edelstahl (austenitisch, nicht magnetisch): Dichte ~7.9, Farbe silber/blank
                elif 7.7 <= dichte <= 8.1 and any(c in farbe for c in ["silber", "blank", "edelstahl", "chrom"]):
                    self.kategorien["edelstahl"].append({**teil, "kategorie_grund": "Dichte/Farbe: Austenitischer Edelstahl"})
                # Sonstiges Metall
                elif dichte > 3.0:
                    self.kategorien["sonstiges"].append({**teil, "kategorie_grund": f"Dichte {dichte:.1f}: Sonstiges Metall"})
                else:
                    self.kategorien["schrott"].append({**teil, "kategorie_grund": f"Dichte {dichte:.1f}: Kein Metall / Unbekannt"})
        
        return self.kategorien
    
    def get_bericht(self):
        """Gibt Text-Zusammenfassung zurück."""
        lines = ["=== Schuppen-Metall-Bericht ==="]
        for kat, teile in self.kategorien.items():
            if teile:
                lines.append(f"{kat.upper()} ({len(teile)}):")
                for t in teile[:5]:  # Max 5 pro Katze anzeigen
                    lines.append(f"  - {t.get('name', '?')} ({t.get('kategorie_grund', '')})")
                if len(teile) > 5:
                    lines.append(f"  ... und {len(teile)-5} weitere")
        return "\n".join(lines)
    
    def export_kategorien(self):
        """Gibt Dict zurück für JSON-Speicherung oder Weiterverarbeitung."""
        return {k: v for k, v in self.kategorien.items() if v}


if __name__ == "__main__":
    # Test-Durchlauf für Fifo's Traum-Debugging
    print("--- Test neuer_tag ---")
    test_daten = {
        "gestern": {"think": 12, "eat": 3},
        "fehlschlaege": {"am_projekt_arbeiten": 4},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 2
    }
    erg = neuer_tag(test_daten)
    print(erg)
    
    print("\n--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "gewicht_g": 78, "volumen_cm3": 10, "farbe": "silber", "fundort": "Regal A"},
        {"name": "Rohrstück", "material": "Edelstahl V2A ferritisch", "gewicht_g": 158, "volumen_cm3": 20, "farbe": "silber", "fundort": "Ecke hinten feucht"},
        {"name": "Alu-Profil", "material": "Aluminium", "gewicht_g": 54, "volumen_cm3": 20, "farbe": "silber", "fundort": "Boden"},
        {"name": "Kupferleitung", "material": "Kupfer", "gewicht_g": 89, "volumen_cm3": 10, "farbe": "rot", "fundort": "Karton oben"},
        {"name": "Messing-Ventil", "material": "Messing", "gewicht_g": 170, "volumen_cm3": 20, "farbe": "gold", "fundort": "Werkbank"},
        {"name": "Mülleimer", "material": "Kunststoff", "gewicht_g": 500, "volumen_cm3": 1000, "farbe": "blau", "fundort": "Ecke"},
        "Kein Dict Objekt",
        {"name": "Edelstahl-Schraube V4A", "material": "Edelstahl V4A austenitisch", "gewicht_g": 16, "volumen_cm3": 2, "farbe": "silber", "fundort": "Schublade"},
    ]
    res = sorter.sortiere_metall(test_teile)
    print(sorter.get_bericht())
    print("\nExport:", sorter.export_kategorien())