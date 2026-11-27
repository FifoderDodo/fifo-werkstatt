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
            dichte = self.gewicht_test(teil)  # Typo korrigiert
            
            # 1. Kakerlaken-Verdacht hat absolute Priorität
            if self.check_kakerlaken_gefahr(teil):
                self.kategorien["kakerlaken_verdaechtig"].append(teil)
                continue
            
            # 2. Magnet-Test: Eisenhaltig / Guss / Edelstahl (magnetisch)
            if self.magnet_test(teil):
                funken = self.funken_test(teil)
                if funken == "edelstahl":
                    self.kategorien["edelstahl"].append(teil)
                elif funken == "gusseisen":
                    self.kategorien["eisenhaltig"].append(teil)
                else:
                    self.kategorien["eisenhaltig"].append(teil)
                continue
            
            # 3. Nicht magnetisch: Dichte & Farbe entscheiden
            # Alu ~2.7, Titan ~4.5, Edelstahl (austenitisch) ~7.9, Messing ~8.5, Kupfer ~8.9
            if dichte < 3.5:  # Leichtmetalle (Alu, Mg, Ti)
                # Kupfer/Messing sind schwer, fallen nicht hier rein
                self.kategorien["aluminium"].append(teil)
            elif dichte > 8.0:  # Schwere Nichteisenmetalle
                if "gold" in farbe or "gelb" in farbe or "messing" in farbe:
                    self.kategorien["messing"].append(teil)
                elif "rot" in farbe or "kupfer" in farbe or "orange" in farbe:
                    self.kategorien["kupfer"].append(teil)
                else:
                    # Grau/Silber & schwer & nicht magnetisch -> Austenitischer Edelstahl
                    self.kategorien["edelstahl"].append(teil)
            elif 3.5 <= dichte <= 8.0:
                # Mittelere Dichte: Titan, spezielle Legierungen, verunreinigte Teile
                self.kategorien["sonstiges"].append(teil)
            else:
                # Dichte 0 oder Fehler
                self.kategorien["schrott"].append({"objekt": teil, "grund": f"Ungültige Dichte: {dichte}"})
    
    def get_bericht(self):
        """Gibt Zusammenfassung der Sortierung als Dict zurück."""
        return {k: len(v) for k, v in self.kategorien.items()}
    
    def export_kategorien(self):
        """Exportiert Kategorien als JSON-String (für Speicherung/Transfer)."""
        import json
        # Nicht-serialisierbare Objekte (falls doch mal reingerutscht) filtern
        safe_cat = {}
        for k, v in self.kategorien.items():
            safe_cat[k] = []
            for item in v:
                if isinstance(item, dict):
                    safe_cat[k].append(item)
                else:
                    safe_cat[k].append({"objekt": str(item), "grund": "Nicht-Dict-Objekt"})
        return json.dumps(safe_cat, ensure_ascii=False, indent=2)
    
    def speichern_als_json(self, pfad: str):
        """
        Validiert Pfad und simuliert Speichern.
        Kein echtes I/O (Regelkonform), gibt JSON-String zurück bei Erfolg.
        """
        ok, msg = validiere_dateipfad(pfad, (".json",))
        if not ok:
            raise ValueError(f"Ungültiger Pfad: {msg}")
        # Simulieren: Nur String zurückgeben, nicht schreiben
        return self.export_kategorien()


def validiere_dateipfad(pfad: str, erlaubte_endungen=(".json", ".txt", ".csv")) -> tuple[bool, str]:
    """
    Prüft Dateipfad-String auf Plausibilität & Sicherheit (in-memory).
    Kein Zugriff auf Dateisystem.
    Returns: (True, "") oder (False, "Fehlerbeschreibung")
    """
    if not pfad or not isinstance(pfad, str):
        return False, "Pfad leer oder kein String"
    
    pfad = pfad.strip()
    
    # 1. Keine Pfad-Traversierung
    if ".." in pfad:
        return False, "Pfad-Traversierung (..) nicht erlaubt"
    
    # 2. Keine absoluten Pfade (Unix/Win)
    if pfad.startswith("/") or (len(pfad) > 1 and pfad[1] == ":" and pfad[0].isalpha()):
        return False, "Absolute Pfade nicht erlaubt"
    
    # 3. Keine verbotenen Zeichen (basisch)
    verboten = ['<', '>', ':', '"', '|', '?', '*', '\x00']
    if any(c in pfad for c in verboten):
        return False, "Verbotene Zeichen im Pfad"
    
    # 4. Dateiendung prüfen
    if not any(pfad.lower().endswith(ext) for ext in erlaubte_endungen):
        return False, f"Endung muss eine von {erlaubte_endungen} sein"
    
    # 5. Länge & Tiefe begrenzen
    if len(pfad) > 260:
        return False, "Pfad zu lang (>260)"
    if pfad.count("/") > 5:  # Max 5 Ordner tief
        return False, "Pfad zu tief verschachtelt"
    
    # 6. Dateiname nicht leer
    name = pfad.split("/")[-1]
    if not name or name == "." or name == "..":
        return False, "Kein gültiger Dateiname"
    
    return True, ""


if __name__ == "__main__":
    # Test neuer_tag
    test_daten = {
        "gestern": {"think": 12, "eat": 3},
        "fehlschlaege": {"schrott_suchen": 2, "am_projekt_arbeiten": 4},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 2
    }
    print("=== neuer_tag Test ===")
    ergebnis = neuer_tag(test_daten)
    print(f"Notiz: {ergebnis.get('notiz')}")
    print(f"Plan: {ergebnis.get('plan')}")
    
    # Test KI-Frage Trigger
    if "frage_an_ki" in ergebnis:
        print(f"KI FRAGE: {ergebnis['frage_an_ki']}")
        # Simuliere 2. Aufruf mit Antwort
        test_daten["ki_antwort"] = "Meistens fehlen Volumen-Daten oder Material-Strings sind inkonsistent. Validierung einbauen."
        ergebnis2 = neuer_tag(test_daten)
        print(f"Mit KI-Rat: {ergebnis2.get('notiz')}")
    
    # Test MetallSortierer
    print("\n=== MetallSortierer Test ===")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "gewicht_g": 50, "volumen_cm3": 6.4, "farbe": "silber", "fundort": "Regal A"},
        {"name": "Alu-Profil", "material": "Aluminium", "gewicht_g": 300, "volumen_cm3": 111, "farbe": "grau", "fundort": "Boden hinter Karton"},  # Kakerlaken
        {"name": "Kupferrohr", "material": "Kupfer", "gewicht_g": 890, "volumen_cm3": 100, "farbe": "rot", "fundort": "Kiste links"},
        {"name": "Messing-Ventil", "material": "Messing", "gewicht_g": 400, "volumen_cm3": 47, "farbe": "gold", "fundort": "Schublade"},
        {"name": "Edelstahl-Becher", "material": "Edelstahl V2A", "gewicht_g": 200, "volumen_cm3": 25, "farbe": "silber", "fundort": "Spüle"},
        {"name": "Guss-Eisen", "material": "Grauguss", "gewicht_g": 700, "volumen_cm3": 90, "farbe": "schwarz", "fundort": "Ecke feucht"},  # Kakerlaken + Magnet
        {"name": "Unbekanntes Teil", "material": "Plastik", "gewicht_g": 10, "volumen_cm3": 20, "farbe": "blau", "fundort": "Müll"},
        "Kein Dict",  # Schrott
    ]
    sorter.sortiere_metall(test_teile)
    print(f"Bericht: {sorter.get_bericht()}")
    
    # Test Pfad-Validierung
    print("\n=== Pfad-Validierung Test ===")
    test_pfade = [
        "daten/export.json",
        "../etc/passwd",
        "/home/user/daten.json",
        "daten/bericht.txt",
        "daten/sehr/tief/verschachtelt/struktur/datei.json",
        "daten/keine_endung",
        "",
    ]
    for p in test_pfade:
        ok, msg = validiere_dateipfad(p)
        print(f"  '{p}' -> OK: {ok} ({msg})" if not ok else f"  '{p}' -> OK")
    
    # Test Speichern Simulation
    print("\n=== Speichern Simulation ===")
    try:
        json_out = sorter.speichern_als_json("schuppen_inventar.json")
        print(f"Simulierter Export (erste 200 Zeichen):\n{json_out[:200]}...")
    except ValueError as e:
        print(f"Fehler: {e}")
    
    try:
        sorter.speichern_als_json("../../böse.json")
    except ValueError as e:
        print(f"Erwarteter Fehler bei böse Pfad: {e}")