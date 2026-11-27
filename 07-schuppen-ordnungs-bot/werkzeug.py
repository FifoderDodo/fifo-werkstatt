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
            
            # Kakerlaken-Check: Teile markieren, nicht automatisch wegwerfen
            if self.check_kakerlaken_gefahr(teil):
                teil["kakerlaken_warnung"] = True
                self.kategorien["kakerlaken_verdaechtig"].append(teil)
                # Trotzdem normal sortieren
            
            # Entscheidungsbaum: Magnetisch -> Eisen/Stahl
            if magnetisch:
                # Edelstahl kann magnetisch sein (ferritisch), aber oft nicht (austenitisch).
                # Prüfen wir Material-Hinweis oder Funken/ Dichte.
                if "edelstahl" in material_hinweis or "v2a" in material_hinweis or "v4a" in material_hinweis:
                    self.kategorien["edelstahl"].append(teil)
                elif dichte > 7.5: # Typisch Stahl/Eisen
                    self.kategorien["eisenhaltig"].append(teil)
                else:
                    self.kategorien["eisenhaltig"].append(teil) # Fallback
            
            # Nicht magnetisch: Alu, Kupfer, Messing, Edelstahl (austenitisch), Sonstiges
            else:
                # Kupfer: rötlich, hohe Dichte ~8.9
                if "kupfer" in material_hinweis or ("rot" in farbe or "kupfer" in farbe) and dichte > 8.0:
                    self.kategorien["kupfer"].append(teil)
                # Messing: gelblich, Dichte ~8.4-8.7
                elif "messing" in material_hinweis or ("gelb" in farbe or "gold" in farbe) and 8.0 < dichte < 8.8:
                    self.kategorien["messing"].append(teil)
                # Aluminium: silbrig/weiß, niedrige Dichte ~2.7
                elif "aluminium" in material_hinweis or "alu" in material_hinweis or dichte < 3.5:
                    self.kategorien["aluminium"].append(teil)
                # Edelstahl (austenitisch): nicht magnetisch, Dichte ~7.9, silbrig
                elif "edelstahl" in material_hinweis or (dichte > 7.5 and dichte < 8.2 and "silber" in farbe):
                    self.kategorien["edelstahl"].append(teil)
                # Titan? Selten im Schuppen. Dichte ~4.5
                elif 4.0 < dichte < 5.0:
                    self.kategorien["sonstiges"].append(teil)
                # Blei/Zink? Dichte hoch, weich
                elif dichte > 10.0:
                    self.kategorien["sonstiges"].append(teil)
                else:
                    self.kategorien["sonstiges"].append(teil)
        
        return self.kategorien
    
    def get_bericht(self):
        """Gibt Zusammenfassung als Text zurück."""
        lines = ["=== Schuppen-Metall-Bericht ==="]
        total = 0
        for kat, teile in self.kategorien.items():
            anzahl = len(teile)
            total += anzahl
            if anzahl > 0:
                lines.append(f"{kat.capitalize()}: {anzahl} Stück")
                # Zeige erste 3 Namen
                namen = [t.get('name', '?') for t in teile[:3]]
                lines.append(f"  z.B.: {', '.join(namen)}")
        lines.append(f"Gesamt: {total} Teile sortiert.")
        return "\n".join(lines)


if __name__ == "__main__":
    # Test für neuer_tag
    print("--- Test neuer_tag ---")
    test_daten_1 = {
        "gestern": {"think": 12, "eat": 3},
        "fehlschlaege": {"schrott_suchen": 2},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 2
    }
    ergebnis_1 = neuer_tag(test_daten_1)
    print(f"Input: {test_daten_1}")
    print(f"Output: {ergebnis_1}")
    print()
    
    test_daten_2 = {
        "gestern": {},
        "fehlschlaege": {},
        "stimmung": -60,
        "wetter": "regen",
        "kakerlaken_level": 8
    }
    ergebnis_2 = neuer_tag(test_daten_2)
    print(f"Input: {test_daten_2}")
    print(f"Output: {ergebnis_2}")
    print()
    
    # Test für MetallSortierer
    print("--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "farbe": "silber", "gewicht_g": 50, "volumen_cm3": 6.5, "fundort": "Werkzeugkasten"},
        {"name": "Alu-Profil", "material": "Aluminium", "farbe": "silber", "gewicht_g": 200, "volumen_cm3": 74, "fundort": "Boden hinter Regal"},
        {"name": "Kupferrohr", "material": "Kupfer", "farbe": "rot", "gewicht_g": 300, "volumen_cm3": 33, "fundort": "Ecke feucht"},
        {"name": "Messing-Ventil", "material": "Messing", "farbe": "gelb", "gewicht_g": 150, "volumen_cm3": 18, "fundort": "Karton oben"},
        {"name": "Edelstahl-Schale", "material": "V2A Edelstahl", "farbe": "silber", "gewicht_g": 400, "volumen_cm3": 50, "fundort": "Spüle"},
        {"name": "Guss-Eisenstück", "material": "Gusseisen", "farbe": "schwarz", "gewicht_g": 500, "volumen_cm3": 64, "fundort": "Schwere Kiste"},
        {"name": "Unbekanntes Teil", "material": "", "farbe": "grau", "gewicht_g": 100, "volumen_cm3": 20, "fundort": "Dunkle Ecke"},
        "kein_dict_objekt", 
    ]
    ergebnis_sort = sorter.sortiere_metall(test_teile)
    print(sorter.get_bericht())
    print()
    print("Kakerlaken-verdächtige Items:")
    for item in ergebnis_sort["kakerlaken_verdaechtig"]:
        print(f"  - {item.get('name')} (Warnung: {item.get('kakerlaken_warnung')})")