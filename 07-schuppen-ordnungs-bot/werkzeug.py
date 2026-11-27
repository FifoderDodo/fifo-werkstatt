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
            kakerlaken_verdacht = self.check_kakerlaken_gefahr(teil)
            
            kategorie = "sonstiges"
            
            # 1. Magnetisch -> Eisenhaltig (Stahl, Guss, ferritischer Edelstahl)
            if magnetisch:
                kategorie = "eisenhaltig"
                # Feinschliff: Guss oder Edelstahl ferritisch?
                if "guss" in teil.get("material", "").lower():
                    kategorie = "eisenhaltig"  # Bleibt eisenhaltig, aber Notiz möglich
                elif "edelstahl" in teil.get("material", "").lower():
                    kategorie = "edelstahl" # Ferritischer Edelstahl ist magnetisch
            
            # 2. Nicht magnetisch -> Dichte-Baum
            else:
                if dichte < 3.0:  # Alu ~2.7
                    kategorie = "aluminium"
                elif dichte > 8.5:  # Kupfer ~8.96
                    kategorie = "kupfer"
                elif 8.3 <= dichte <= 8.7:  # Messing ~8.4-8.7
                    kategorie = "messing"
                elif 7.7 <= dichte <= 8.1:  # Edelstahl (austenitisch) ~7.9-8.0
                    kategorie = "edelstahl"
                else:
                    kategorie = "sonstiges"
            
            # Eintragen
            eintrag = {"name": name, "dichte": round(dichte, 2), "magnetisch": magnetisch, "fundort": teil.get("fundort", "?")}
            self.kategorien[kategorie].append(eintrag)
            
            # Kakerlaken-Duplizierung: Wenn verdächtig, AUCH in die Warnliste
            if kakerlaken_verdacht:
                self.kategorien["kakerlaken_verdaechtig"].append({**eintrag, "ursprung_kategorie": kategorie})
    
    def get_bericht(self):
        """Gibt Zusammenfassung als String zurück."""
        lines = ["=== Schuppen-Metall-Bericht ==="]
        total = 0
        for kat, teile in self.kategorien.items():
            if teile:
                lines.append(f"{kat}: {len(teile)} Stk.")
                total += len(teile)
        lines.append(f"---\nGesamt sortiert: {total} (inkl. Duplikate Kakerlaken-Liste)")
        return "\n".join(lines)
    
    def export_kategorien(self):
        """Gibt das Kategorien-Dict zurück (für JSON/Weiterverarbeitung)."""
        return self.kategorien


if __name__ == "__main__":
    # Test neuer_tag
    print("--- Test neuer_tag ---")
    test_daten = {
        "gestern": {"think": 12, "eat": 3, "am_projekt_arbeiten": 5},
        "fehlschlaege": {"am_projekt_arbeiten": 4, "schrott_suchen": 1},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 2
    }
    ergebnis = neuer_tag(test_daten)
    print(f"Notiz: {ergebnis['notiz']}")
    print(f"Plan: {ergebnis['plan']}")
    
    # Test KI-Frage Trigger
    test_daten_ki = {**test_daten, "fehlschlaege": {"am_projekt_arbeiten": 5}}
    ergebnis_ki = neuer_tag(test_daten_ki)
    print(f"KI-Trigger Test: {ergebnis_ki}")
    
    # Test MetallSortierer
    print("\n--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "gewicht_g": 78, "volumen_cm3": 10, "fundort": "Regal A", "farbe": "silber"},
        {"name": "Rohrstück", "material": "Edelstahl V2A (austenitisch)", "gewicht_g": 158, "volumen_cm3": 20, "fundort": "Ecke hinten links", "farbe": "silber matt"},
        {"name": "Blechstreifen", "material": "Edelstahl 430 (ferritisch)", "gewicht_g": 156, "volumen_cm3": 20, "fundort": "Boden bei Kartons", "farbe": "silber"},
        {"name": "Alu-Profil", "material": "Aluminium 6060", "gewicht_g": 54, "volumen_cm3": 20, "fundort": "Wandhalterung", "farbe": "grau"},
        {"name": "Kupferleitung", "material": "Kupfer", "gewicht_g": 89, "volumen_cm3": 10, "fundort": "Kabelkiste", "farbe": "rotgold"},
        {"name": "Messing-Verschraubung", "material": "Messing", "gewicht_g": 85, "volumen_cm3": 10, "fundort": "Schublade oben", "farbe": "gelblich"},
        {"name": "Guss-Ecke", "material": "Grauguss", "gewicht_g": 72, "volumen_cm3": 10, "fundort": "Schwerecke", "farbe": "dunkelgrau"},
        "Kein Dict sondern String",  # Fehlerfall
        {"name": "Mysterie-Metall", "material": "Titan", "gewicht_g": 45, "volumen_cm3": 10, "fundort": "Dunkle Ecke hinter Ofen", "farbe": "grau"}  # Kakerlakenverdacht + Sonstiges
    ]
    sorter.sortiere_metall(test_teile)
    print(sorter.get_bericht())
    print("\nKakerlaken-Verdachtsfälle:")
    for v in sorter.kategorien["kakerlaken_verdaechtig"]:
        print(f"  - {v['name']} (aus {v['ursprung_kategorie']}, Fundort: {v['fundort']})")
    
    # Export Test
    import json
    print("\nExport JSON:")
    print(json.dumps(sorter.export_kategorien(), indent=2, ensure_ascii=False)[:500] + "...")