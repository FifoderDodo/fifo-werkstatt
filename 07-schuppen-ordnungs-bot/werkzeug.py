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
            
            # Kakerlaken-Verdacht: Duplizieren in Quarantäne-Kategorie
            if kakerlaken_alarm:
                self.kategorien["kakerlaken_verdaechtig"].append({
                    **teil, "kategorie_vermutung": "prüfen", "grund": "Fundort verdächtig"
                })
            
            # 1. Magnet-Test trennt Ferro von Non-Ferro
            if magnetisch:
                # Funken-Test oder Material-String verfeinert: Ferritischer Edelstahl ist magnetisch!
                funken = self.funken_test(teil)
                mat_str = teil.get("material", "").lower()
                if "edelstahl" in mat_str or funken == "edelstahl":
                    self.kategorien["edelstahl"].append({**teil, "kategorie": "edelstahl (ferritisch/martensitisch)", "dichte": round(dichte, 2)})
                elif funken == "gusseisen" or "guss" in mat_str:
                    self.kategorien["eisenhaltig"].append({**teil, "kategorie": "gusseisen", "dichte": round(dichte, 2)})
                else:
                    self.kategorien["eisenhaltig"].append({**teil, "kategorie": "eisen/stahl", "dichte": round(dichte, 2)})
            else:
                # 2. Non-Ferro: Dichte-Baum entscheidet
                if dichte < 3.5:  # Alu ~2.7, Titan ~4.5 (selten im Schuppen)
                    self.kategorien["aluminium"].append({**teil, "kategorie": "aluminium", "dichte": round(dichte, 2)})
                elif dichte > 8.7:  # Kupfer ~8.96
                    self.kategorien["kupfer"].append({**teil, "kategorie": "kupfer", "dichte": round(dichte, 2)})
                elif dichte > 8.3:  # Messing ~8.4 - 8.7
                    self.kategorien["messing"].append({**teil, "kategorie": "messing", "dichte": round(dichte, 2)})
                elif 7.5 <= dichte <= 8.2:  # Edelstahl (austenitisch) ~7.9
                    self.kategorien["edelstahl"].append({**teil, "kategorie": "edelstahl (austenitisch)", "dichte": round(dichte, 2)})
                else:
                    self.kategorien["sonstiges"].append({**teil, "kategorie": "unbekannt non-ferro", "dichte": round(dichte, 2)})
        
        return self.kategorien
    
    def get_bericht(self):
        """Gibt Text-Zusammenfassung der Sortierung zurück."""
        lines = ["=== Schuppen-Metall-Bericht ==="]
        total = 0
        for kat, teile in self.kategorien.items():
            if teile:
                lines.append(f"{kat.upper()} ({len(teile)}):")
                for t in teile[:5]:  # Max 5 Beispiele pro Kat
                    lines.append(f"  - {t.get('name', '?')} (Dichte: {t.get('dichte', '?')}, Grund: {t.get('kategorie', '?')})")
                if len(teile) > 5:
                    lines.append(f"  ... und {len(teile)-5} weitere")
                total += len(teile)
        lines.append(f"\nGesamt sortiert: {total} Teile")
        if self.kategorien["kakerlaken_verdaechtig"]:
            lines.append("\nACHTUNG: Teile mit Kakerlaken-Verdacht in Quarantäne!")
        return "\n".join(lines)
    
    def export_kategorien(self):
        """Gibt Dict zurück für JSON-Speicher/Weiterverarbeitung."""
        return {k: v for k, v in self.kategorien.items() if v}


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
    print("Eingabe:", test_daten)
    print("Ausgabe:", erg)
    
    # Test KI-Frage bei hohen Fehlschlägen
    print("\n--- Test KI-Frage ---")
    test_daten_ki = {**test_daten, "fehlschlaege": {"am_projekt_arbeiten": 5}}
    erg_ki = neuer_tag(test_daten_ki)
    print("Bei 5 Fehlschlägen:", erg_ki)
    
    # Test MetallSortierer
    print("\n--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "gewicht_g": 50, "volumen_cm3": 6.4, "fundort": "Werkbank", "farbe": "silber"},
        {"name": "Alu-Profil", "material": "Aluminium", "gewicht_g": 300, "volumen_cm3": 111, "fundort": "Ecke hinter Karton", "farbe": "grau"},
        {"name": "Kupferrohr", "material": "Kupfer", "gewicht_g": 890, "volumen_cm3": 100, "fundort": "Regal", "farbe": "rotbraun"},
        {"name": "Messing-Ventil", "material": "Messing", "gewicht_g": 420, "volumen_cm3": 50, "fundort": "Kasten", "farbe": "goldgelb"},
        {"name": "Edelstahl-Schraube (V2A)", "material": "Edelstahl austenitisch", "gewicht_g": 20, "volumen_cm3": 2.5, "fundort": "Schublade", "farbe": "silber"},
        {"name": "Edelstahl-Schraube (V4A ferritisch)", "material": "Edelstahl ferritisch", "gewicht_g": 22, "volumen_cm3": 2.8, "fundort": "Schublade", "farbe": "silber"},
        {"name": "Guss-Eisenstück", "material": "Gusseisen", "gewicht_g": 500, "volumen_cm3": 64, "fundort": "Boden nähe Nest", "farbe": "schwarz"},
        {"name": "Unbekanntes Teil", "material": "Plastik", "gewicht_g": 10, "volumen_cm3": 20, "fundort": "Müllhaufen", "farbe": "bunt"},
        "Kein Dict sondern String",  # Fehlerfall
    ]
    result = sorter.sortiere_metall(test_teile)
    print(sorter.get_bericht())
    
    # Export testen
    export = sorter.export_kategorien()
    print(f"\nExport Keys: {list(export.keys())}")
    print(f"Kakerlaken verdächtig: {len(export.get('kakerlaken_verdaechtig', []))} Teile")