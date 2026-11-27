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
            
            # 1. Magnetisch -> Eisen/Stahl oder Edelstahl (manche sind magnetisch)
            if magnetisch:
                # Heuristik: Edelstahl oft nicht magnetisch (Austenitisch), aber martensitisch/ferritisch schon.
                # Wir nutzen Material-Hinweis & Funken/Fehlschlüsse.
                if "edelstahl" in material_hinweis or "v2a" in material_hinweis or "v4a" in material_hinweis:
                    self.kategorien["edelstahl"].append(teil)
                elif dichte > 7.0: # Typisch Stahl/Eisen ~7.85
                    self.kategorien["eisenhaltig"].append(teil)
                else:
                    self.kategorien["eisenhaltig"].append(teil) # Fallback
                continue
            
            # 2. Nicht magnetisch -> Alu, Kupfer, Messing, Edelstahl (austenitisch), Titan, etc.
            # Entscheidung über Dichte (g/cm³) & Farbe
            # Alu: ~2.7, Mg: ~1.7, Ti: ~4.5, Edelstahl: ~7.9, Messing: ~8.5, Kupfer: ~8.9
            
            if dichte < 3.0: # Leichtmetall
                if "aluminium" in material_hinweis or "alu" in material_hinweis or farbe in ["silber", "grau", "weiß"]:
                    self.kategorien["aluminium"].append(teil)
                elif "magnesium" in material_hinweis:
                    self.kategorien["sonstiges"].append(teil) # Selten, extra Kategorie?
                else:
                    self.kategorien["aluminium"].append(teil) # Wahrscheinlich Alu
            
            elif 4.0 <= dichte < 5.5: # Titan Bereich
                if "titan" in material_hinweis:
                    self.kategorien["sonstiges"].append(teil)
                else:
                    self.kategorien["sonstiges"].append(teil)
            
            elif 7.5 <= dichte < 8.2: # Edelstahl / Sonderlegierungen
                if "edelstahl" in material_hinweis or "rostfrei" in material_hinweis:
                    self.kategorien["edelstahl"].append(teil)
                else:
                    # Könnte schwerer Stahl sein der nicht magnetisch? Unwahrscheinlich.
                    self.kategorien["edelstahl"].append(teil) 
            
            elif 8.2 <= dichte < 8.7: # Messing / Bronze
                if "messing" in material_hinweis or farbe in ["gelb", "gold", "messing"]:
                    self.kategorien["messing"].append(teil)
                elif "bronze" in material_hinweis or farbe in ["braun", "rotbraun"]:
                    self.kategorien["messing"].append(teil) # Bronze zu Messing topf
                else:
                    self.kategorien["messing"].append(teil)
            
            elif dichte >= 8.7: # Kupfer
                if "kupfer" in material_hinweis or farbe in ["rot", "kupfer", "rotbraun", "grün" ]: # Grün = Patina
                    self.kategorien["kupfer"].append(teil)
                else:
                    self.kategorien["kupfer"].append(teil) # Schwere Metalle oft Kupfer
            
            else:
                # Dichte Lücken (3-4, 5.5-7.5) oder unklar
                self.kategorien["sonstiges"].append(teil)
        
        return self.kategorien

    def get_bericht(self):
        """Gibt Zusammenfassung als Text zurück."""
        lines = ["=== Schuppen-Metall-Bericht ==="]
        total = 0
        for kat, teile in self.kategorien.items():
            if teile:
                anzahl = len(teile)
                total += anzahl
                # Gewichte summieren für Verkaufswert-Schätzung
                gew_sum = sum(t.get("gewicht_g", 0) for t in teile)
                lines.append(f"{kat}: {anzahl} Stk (~{gew_sum/1000:.1f} kg)")
        lines.append(f"---\nGesamt: {total} Teile sortiert.")
        if self.kategorien["kakerlaken_verdaechtig"]:
            lines.append("ACHTUNG: Kakerlaken-verdächtige Teile dabei! Handschuhe waschen.")
        return "\n".join(lines)

    def export_kategorien(self):
        """Gibt Dict zurück für weitere Verarbeitung (verkaufen, einlagern)."""
        # Kopie ohne interne Marker
        export = {}
        for kat, teile in self.kategorien.items():
            if kat == "kakerlaken_verdaechtig": continue
            export[kat] = [
                {k: v for k, v in t.items() if k != "kakerlaken_warnung"} 
                for t in teile
            ]
        return export


if __name__ == "__main__":
    # Test-Daten
    test_teile = [
        {"name": "Rohr 1", "material": "Stahl", "gewicht_g": 785, "volumen_cm3": 100, "farbe": "grau", "fundort": "Regal links"},
        {"name": "Blech 1", "material": "Edelstahl V2A", "gewicht_g": 790, "volumen_cm3": 100, "farbe": "silber", "fundort": "Ecke hinten dunkel"},
        {"name": "Profil 1", "material": "Aluminium", "gewicht_g": 270, "volumen_cm3": 100, "farbe": "silber", "fundort": "Boden"},
        {"name": "Kabel 1", "material": "Kupfer", "gewicht_g": 890, "volumen_cm3": 100, "farbe": "rot", "fundort": "Karton oben"},
        {"name": "Armatur 1", "material": "Messing", "gewicht_g": 850, "volumen_cm3": 100, "farbe": "gelb", "fundort": "Schublade"},
        {"name": "Schraube 1", "material": "Eisen verzinkt", "gewicht_g": 10, "volumen_cm3": 1.3, "farbe": "silber", "fundort": "Dose"},
        {"name": "Unbekannt 1", "gewicht_g": 500, "volumen_cm3": 100, "farbe": "grau", "fundort": "hinter Ofen"}, # Dichte 5.0 -> Sonstiges
        {"name": "Titan Teil", "material": "Titan", "gewicht_g": 450, "volumen_cm3": 100, "farbe": "grau", "fundort": "Kiste"}, # Dichte 4.5 -> Sonstiges
        "Müllstring", # Fehlerfall
        {"name": "Edelstahl nicht magnetisch", "material": "Edelstahl 304", "gewicht_g": 795, "volumen_cm3": 100, "farbe": "silber", "fundort": "Spüle"},
    ]
    
    sorter = MetallSortierer()
    ergebnis = sorter.sortiere_metall(test_teile)
    print(sorter.get_bericht())
    print("\nExport-Keys:", list(sorter.export_kategorien().keys()))
    
    # Test neuer_tag
    print("\n--- neuer_tag Test ---")
    daten = {
        "gestern": {"am_projekt_arbeiten": 2, "think": 1},
        "fehlschlaege": {"am_projekt_arbeiten": 1},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 3
    }
    print(neuer_tag(daten))
    
    daten2 = {
        "gestern": {},
        "fehlschlaege": {},
        "stimmung": -60,
        "wetter": "regen",
        "kakerlaken_level": 8
    }
    print(neuer_tag(daten2))