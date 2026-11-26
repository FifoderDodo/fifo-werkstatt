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
            
            # Kakerlaken-Check: Teile markieren, nicht automatisch wegwerfen
            if self.check_kakerlaken_gefahr(teil):
                teil["kakerlaken_warnung"] = True
                self.kategorien["kakerlaken_verdaechtig"].append(teil)
                # Trotzdem normal sortieren, aber Flag gesetzt
            
            # 1. Magnet-Test: Eisen/Stahl getrennt
            if self.magnet_test(teil):
                # Edelstahl kann magnetisch sein (ferritisch/martensitisch), aber oft nicht.
                # Wenn Material-String 'edelstahl' sagt, glauben wir dem Hinweis.
                if "edelstahl" in material_hinweis or "v2a" in material_hinweis or "v4a" in material_hinweis:
                    self.kategorien["edelstahl"].append(teil)
                else:
                    self.kategorien["eisenhaltig"].append(teil)
                continue
            
            # 2. Nicht magnetisch -> Dichte & Farbe prüfen
            # Kupfer: ~8.9 g/cm³, rot/orange
            # Messing: ~8.4-8.7 g/cm³, gelb/gold
            # Aluminium: ~2.7 g/cm³, grau/silber, leicht
            # Edelstahl (austenitisch): ~7.9 g/cm³, nicht magnetisch, silber
            
            if dichte >= 8.0:
                if "rot" in farbe or "orange" in farbe or "kupfer" in material_hinweis:
                    self.kategorien["kupfer"].append(teil)
                elif "gelb" in farbe or "gold" in farbe or "messing" in material_hinweis:
                    self.kategorien["messing"].append(teil)
                else:
                    # Schwere, nicht magnetische, nicht kupfer/messing-farben -> ev. Edelstahl oder Blei/Zink
                    if "edelstahl" in material_hinweis or farbe in ["silber", "grau", "weiß"]:
                        self.kategorien["edelstahl"].append(teil)
                    else:
                        self.kategorien["sonstiges"].append(teil)
            elif dichte >= 3.5 and dichte < 8.0:
                # Bereich Zink, Blei, Edelstahl (falls leicht), Titan
                if "edelstahl" in material_hinweis or "v2a" in material_hinweis:
                    self.kategorien["edelstahl"].append(teil)
                elif "blei" in material_hinweis or "zink" in material_hinweis:
                    self.kategorien["sonstiges"].append(teil)  # Extra Kategorie fehlt, landen hier
                else:
                    self.kategorien["sonstiges"].append(teil)
            elif dichte > 0.5 and dichte < 3.5:
                # Aluminium, Magnesium, Titan
                if "aluminium" in material_hinweis or "alu" in material_hinweis or farbe in ["grau", "silber", "weiß"]:
                    self.kategorien["aluminium"].append(teil)
                else:
                    self.kategorien["sonstiges"].append(teil)
            else:
                # Keine brauchbaren Daten (Gewicht/Volumen 0 oder fehlend)
                # Fallback über Material-String
                if "kupfer" in material_hinweis: self.kategorien["kupfer"].append(teil)
                elif "messing" in material_hinweis: self.kategorien["messing"].append(teil)
                elif "aluminium" in material_hinweis or "alu" in material_hinweis: self.kategorien["aluminium"].append(teil)
                elif "edelstahl" in material_hinweis: self.kategorien["edelstahl"].append(teil)
                elif "eisen" in material_hinweis or "stahl" in material_hinweis: self.kategorien["eisenhaltig"].append(teil)
                else:
                    self.kategorien["schrott"].append({"objekt": teil, "grund": "Keine Daten für Sortierung"})
    
    def get_zusammenfassung(self):
        """Gibt Dict mit Anzahl pro Kategorie zurück."""
        return {k: len(v) for k, v in self.kategorien.items()}
    
    def print_bericht(self):
        """Gibt formatierten Bericht auf Konsole aus."""
        print("=== Schuppen-Sortierbericht ===")
        gesamt = 0
        for kat, teile in self.kategorien.items():
            anzahl = len(teile)
            gesamt += anzahl
            if anzahl > 0:
                print(f"  {kat}: {anzahl} Teil(e)")
                # Erste 3 Namen als Beispiel
                for t in teile[:3]:
                    name = t.get('name', 'Unbekannt') if isinstance(t, dict) else str(t)
                    warn = " ⚠ KAKERLAKEN!" if isinstance(t, dict) and t.get('kakerlaken_warnung') else ""
                    print(f"    - {name}{warn}")
                if anzahl > 3:
                    print(f"    ... und {anzahl - 3} weitere")
        print(f"Gesamt: {gesamt} Teile")
        if self.kategorien["kakerlaken_verdaechtig"]:
            print("ACHTUNG: Teile aus verseuchten Zonen gefunden! Erst entseuchen, dann einlagern.")


if __name__ == "__main__":
    # Test neuer_tag
    print("--- Test neuer_tag ---")
    test_daten_1 = {
        "gestern": {"think": 12, "eat": 3},
        "fehlschlaege": {"schrott_suchen": 2},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 2
    }
    erg1 = neuer_tag(test_daten_1)
    print(f"Eingabe: {test_daten_1}")
    print(f"Ergebnis: {erg1}")
    
    test_daten_2 = {
        "gestern": {},
        "fehlschlaege": {"am_projekt_arbeiten": 3},
        "stimmung": -60,
        "wetter": "regen",
        "kakerlaken_level": 8
    }
    erg2 = neuer_tag(test_daten_2)
    print(f"Eingabe: {test_daten_2}")
    print(f"Ergebnis: {erg2}")

    # Test MetallSortierer
    print("\n--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Rostiger Nagel", "material": "Eisen", "gewicht_g": 10, "volumen_cm3": 1.3, "fundort": "Boden Ecke", "farbe": "braun"},
        {"name": "Blanker Kupferdraht", "material": "Kupfer", "gewicht_g": 89, "volumen_cm3": 10, "fundort": "Karton oben", "farbe": "rot"},
        {"name": "Alu-Profil Rest", "material": "Aluminium", "gewicht_g": 27, "volumen_cm3": 10, "fundort": "Regal", "farbe": "silber"},
        {"name": "Schraube V2A", "material": "Edelstahl V2A", "gewicht_g": 20, "volumen_cm3": 2.5, "fundort": "Schraubendose", "farbe": "silber"},
        {"name": "Messing-Ventil", "material": "Messing", "gewicht_g": 170, "volumen_cm3": 20, "fundort": "Hinter Ofen", "farbe": "gold"},
        {"name": "Unbekanntes Schweres Teil", "gewicht_g": 500, "volumen_cm3": 60, "fundort": "Dunkle Ecke", "farbe": "grau", "notiz": "feucht"},
        {"name": "Magnetischer Brocken", "material": "Stahl", "gewicht_g": 1000, "volumen_cm3": 127, "fundort": "Mitte Raum"},
        "Kein Dict Objekt",
        {"name": "Dünnes Blech", "material": "Edelstahl", "gewicht_g": 50, "volumen_cm3": 6.3, "fundort": "Karton feucht", "farbe": "silber"}
    ]
    sorter.sortiere_metall(test_teile)
    sorter.print_bericht()
    print(f"\nZusammenfassung: {sorter.get_zusammenfassung()}")