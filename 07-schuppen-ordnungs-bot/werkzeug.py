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
                self.kategorien["kakerlaken_verdaechtig"].append(teil)
            
            # 1. Magnetische Teile: Eisen/Stahl (außer Edelstahl oft nicht magnetisch)
            if magnetisch:
                # Grobe Unterscheidung: Gusseisen vs Stahl via Funken/Hinweis
                if "guss" in material_hinweis or "gusseisen" in material_hinweis:
                    self.kategorien["eisenhaltig"].append({**teil, "kategorie_detail": "Gusseisen"})
                elif "edelstahl" in material_hinweis:
                    # Manche Edelstähle sind magnetisch (ferritisch/martensitisch)
                    self.kategorien["edelstahl"].append({**teil, "kategorie_detail": "Edelstahl (magnetisch)"})
                else:
                    self.kategorien["eisenhaltig"].append({**teil, "kategorie_detail": "Stahl/Eisen"})
                continue
            
            # 2. Nicht-magnetisch: Dichte & Farbe entscheiden
            # Dichte-Bereiche (g/cm³): Alu ~2.7, Messing ~8.5, Kupfer ~8.9, Edelstahl ~7.9, Blei ~11.3, Zink ~7.1
            
            # Explizite Material-Hinweise nutzen
            if "aluminium" in material_hinweis or "alu" in material_hinweis:
                self.kategorien["aluminium"].append(teil)
            elif "kupfer" in material_hinweis or "cu" == material_hinweis.strip():
                self.kategorien["kupfer"].append(teil)
            elif "messing" in material_hinweis or "ms" == material_hinweis.strip():
                self.kategorien["messing"].append(teil)
            elif "edelstahl" in material_hinweis or "v2a" in material_hinweis or "v4a" in material_hinweis:
                self.kategorien["edelstahl"].append(teil)
            # Heuristik über Dichte & Farbe falls kein Hinweis
            elif dichte > 0:
                if dichte < 3.5: # Leichtmetall
                    if any(c in farbe for c in ["silber", "grau", "weiss", "blank"]):
                        self.kategorien["aluminium"].append(teil)
                    else:
                        self.kategorien["sonstiges"].append({**teil, "vermutung": "Leichtmetall (ev. Mg/Ti)"})
                elif 7.0 <= dichte < 8.2: # Edelstahl / Zink / Zinn
                    if "gelb" in farbe or "gold" in farbe:
                        self.kategorien["messing"].append(teil) # Messing kann leichter sein
                    else:
                        self.kategorien["edelstahl"].append({**teil, "kategorie_detail": "Edelstahl/Zink (Dichte ~7.9)"})
                elif 8.2 <= dichte <= 9.5: # Kupfer / Messing / Bronze
                    if "rot" in farbe or "orange" in farbe or "braun" in farbe:
                        self.kategorien["kupfer"].append(teil)
                    elif "gelb" in farbe or "gold" in farbe:
                        self.kategorien["messing"].append(teil)
                    else:
                        self.kategorien["kupfer"].append({**teil, "kategorie_detail": "Kupfer/Bronze (Dichte ~8.9)"})
                elif dichte > 9.5: # Blei, Wolfram, Gold
                    self.kategorien["sonstiges"].append({**teil, "vermutung": f"Schwermetall (Dichte {dichte:.1f})"})
                else: # Lücke 3.5 - 7.0 (Titan, Magnesiumlegierungen, etc.)
                    self.kategorien["sonstiges"].append({**teil, "vermutung": f"Dichte {dichte:.1f} unklar"})
            else:
                # Keine Daten -> Schrott/Unbekannt
                self.kategorien["schrott"].append({**teil, "grund": "Keine Messdaten, nicht magnetisch"})
        
        return self.kategorien

    def get_bericht(self):
        """Gibt einen lesbaren Zusammenfassungs-String zurück."""
        zeilen = ["=== Schuppen-Metall-Bericht ==="]
        gesamt = 0
        for kat, teile in self.kategorien.items():
            anzahl = len(teile)
            gesamt += anzahl
            if anzahl > 0:
                zeilen.append(f"{kat.replace('_', ' ').title()}: {anzahl} Stück")
                # Zeige erste 3 Namen als Beispiel
                beispiele = [t.get('name', '?') for t in teile[:3]]
                zeilen.append(f"  z.B.: {', '.join(beispiele)}")
        zeilen.append(f"-------------------------")
        zeilen.append(f"Gesamt sortiert: {gesamt}")
        if self.kategorien["kakerlaken_verdaechtig"]:
            zeilen.append("⚠️ ACHTUNG: Teile mit Kakerlaken-Verdacht gefunden! Handschuhe waschen.")
        return "\n".join(zeilen)


if __name__ == "__main__":
    # Test-Daten für einen Durchlauf
    test_teile = [
        {"name": "Rostiger Nagel", "material": "Stahl", "gewicht_g": 5, "volumen_cm3": 0.6, "fundort": "Boden Ecke", "farbe": "braun"},
        {"name": "Alu-Profil Rest", "material": "Aluminium", "gewicht_g": 150, "volumen_cm3": 55, "fundort": "Regal oben", "farbe": "silber"},
        {"name": "Kupferrohr Stück", "material": "Kupfer", "gewicht_g": 300, "volumen_cm3": 34, "fundort": "Hinter Karton", "farbe": "rot"},
        {"name": "Messing-Schraube", "material": "Messing", "gewicht_g": 20, "volumen_cm3": 2.4, "fundort": "Schublade", "farbe": "gold"},
        {"name": "Edelstahl-Schale", "material": "V2A Edelstahl", "gewicht_g": 400, "volumen_cm3": 50, "fundort": "Spüle", "farbe": "silber"},
        {"name": "Magnetischer Brocken", "material": "Eisen", "gewicht_g": 1000, "volumen_cm3": 127, "fundort": "Mitte Raum", "farbe": "grau"},
        {"name": "Unbekanntes Ding", "gewicht_g": 50, "volumen_cm3": 10, "fundort": "Dunkle feuchte Ecke", "farbe": "grau"}, # Kein Material, Kakerlaken-Verdacht
        "Kein Dict Objekt",
    ]
    
    print("--- Test neuer_tag ---")
    test_daten = {
        "gestern": {"am_projekt_arbeiten": 2, "think": 1},
        "fehlschlaege": {"am_projekt_arbeiten": 1},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 3
    }
    ergebnis = neuer_tag(test_daten)
    print(f"Notiz: {ergebnis['notiz']}")
    print(f"Plan: {ergebnis['plan']}")
    
    print("\n--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    ergebnis_sort = sorter.sortiere_metall(test_teile)
    print(sorter.get_bericht())
    
    # Prüfen ob Kakerlaken-Teile auch in Material-Kategorie gelandet sind
    print("\n--- Prüfung Kakerlaken-Logik ---")
    kaker_teile = ergebnis_sort["kakerlaken_verdaechtig"]
    for t in kaker_teile:
        print(f"Verdächtig: {t['name']} -> Auch in: {[k for k,v in ergebnis_sort.items() if t in v and k != 'kakerlaken_verdaechtig']}")