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
            funken = self.funken_test(teil)
            kakerlaken_verdacht = self.check_kakerlaken_gefahr(teil)
            
            # Kakerlaken-Check: Duplikat in Verdachts-Kategorie, aber normal weiter sortieren
            if kakerlaken_verdacht:
                self.kategorien["kakerlaken_verdaechtig"].append(teil.copy())
            
            # 1. Magnet-Test: Ferromagnetisch -> Eisen, Stahl, Guss (oder ferritischer Edelstahl)
            if magnetisch:
                if funken == "edelstahl" or "edelstahl" in teil.get("material", "").lower():
                    self.kategorien["edelstahl"].append(teil)
                elif funken == "gusseisen":
                    self.kategorien["eisenhaltig"].append(teil)
                else:
                    self.kategorien["eisenhaltig"].append(teil)
                continue
            
            # 2. Nicht magnetisch: Dichte-Baum für NE-Metalle & austenitischen Edelstahl
            # Dichten: Alu ~2.7, Titan ~4.5, Edelstahl ~7.9, Messing ~8.5, Kupfer ~8.9, Blei ~11.3
            if dichte < 3.5:
                self.kategorien["aluminium"].append(teil)
            elif 3.5 <= dichte < 6.0:
                self.kategorien["sonstiges"].append(teil)  # Titan, Magnesium etc.
            elif 6.0 <= dichte < 8.2:
                # Grauzone: könnte Edelstahl sein (7.9) oder schweres Alu-Legierung
                if "edelstahl" in teil.get("material", "").lower() or funken == "edelstahl":
                    self.kategorien["edelstahl"].append(teil)
                else:
                    self.kategorien["sonstiges"].append(teil)
            elif 8.2 <= dichte < 8.7:
                # Messing Bereich
                if "gelb" in farbe or "gold" in farbe or "messing" in teil.get("material", "").lower():
                    self.kategorien["messing"].append(teil)
                else:
                    self.kategorien["sonstiges"].append(teil)
            elif 8.7 <= dichte < 9.3:
                # Kupfer Bereich
                if "rot" in farbe or "orange" in farbe or "kupfer" in teil.get("material", "").lower():
                    self.kategorien["kupfer"].append(teil)
                else:
                    self.kategorien["sonstiges"].append(teil)
            elif dichte >= 9.3:
                self.kategorien["sonstiges"].append(teil)  # Blei, Zinn, etc.
            else:
                self.kategorien["schrott"].append({"objekt": teil, "grund": "Keine Dichte/Material ermittelbar"})
        
        return self.kategorien
    
    def get_bericht(self):
        """Gibt einen lesbaren Zusammenfassungs-String zurück."""
        linien = ["=== Schuppen-Sortier-Bericht ==="]
        gesamt = 0
        for kat, teile in self.kategorien.items():
            anzahl = len(teile)
            gesamt += anzahl
            if anzahl > 0:
                linien.append(f"{kat.capitalize()}: {anzahl} Stück")
                # Zeige erste 3 Namen als Beispiel
                beispiele = [t.get('name', '?') for t in teile[:3]]
                linien.append(f"  z.B.: {', '.join(beispiele)}")
        linien.append(f"-------------------------------")
        linien.append(f"Gesamt sortiert: {gesamt}")
        return "\n".join(linien)
    
    def export_kategorien(self):
        """Gibt das reine Kategorien-Dict zurück (für JSON/Weiterverarbeitung)."""
        return {k: v for k, v in self.kategorien.items() if v}


if __name__ == "__main__":
    # Test für neuer_tag
    test_daten = {
        "gestern": {"think": 12, "eat": 3},
        "fehlschlaege": {"schrott_suchen": 2, "am_projekt_arbeiten": 4},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 2
    }
    print("--- Test neuer_tag (Fehlschläge > 3 -> KI Frage) ---\n")
    ergebnis = neuer_tag(test_daten)
    print(ergebnis)
    
    # Simuliere KI-Antwort
    test_daten["ki_antwort"] = "Prüfe Volumen != 0. Nutze try/except bei Dichte. Ferritischer Edelstahl ist magnetisch."
    print("\n--- Test neuer_tag (mit KI Antwort) ---")
    ergebnis2 = neuer_tag(test_daten)
    print(ergebnis2)

    # Test für MetallSortierer
    print("\n=== Test MetallSortierer ===")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "gewicht_g": 50, "volumen_cm3": 6.4, "fundort": "Regal", "farbe": "silber"},
        {"name": "Rohrstück", "material": "Edelstahl V2A", "gewicht_g": 300, "volumen_cm3": 38, "fundort": "Ecke hinter Karton", "farbe": "silber", "notiz": "feucht"},
        {"name": "Alu-Profil", "material": "Aluminium", "gewicht_g": 150, "volumen_cm3": 55, "fundort": "Boden", "farbe": "grau"},
        {"name": "Kupferleitung", "material": "Kupfer", "gewicht_g": 200, "volumen_cm3": 22.5, "fundort": "Kasten", "farbe": "rot"},
        {"name": "Messing-Ventil", "material": "Messing", "gewicht_g": 180, "volumen_cm3": 21, "fundort": "Schublade", "farbe": "gold"},
        {"name": "Guss-Eisenstück", "material": "Grauguss", "gewicht_g": 500, "volumen_cm3": 64, "fundort": "Palette", "farbe": "grau"},
        {"name": "Ferritischer Edelstahl", "material": "Edelstahl ferritisch", "gewicht_g": 100, "volumen_cm3": 12.7, "fundort": "Regal", "farbe": "silber"},
        "Kein Dict Objekt",
        {"name": "Unbekanntes Teil", "material": "Plastik", "gewicht_g": 10, "volumen_cm3": 20, "fundort": "Müll", "farbe": "bunt"}
    ]
    
    ergebnis_kategorien = sorter.sortiere_metall(test_teile)
    print(sorter.get_bericht())
    
    # Export Test
    print("\n--- Export (nur gefüllte Kategorien) ---")
    export = sorter.export_kategorien()
    for k, v in export.items():
        print(f"{k}: {len(v)}")