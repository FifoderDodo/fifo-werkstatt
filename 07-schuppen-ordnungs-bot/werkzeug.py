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
            dichte = self.gewicht_test(teil)  # Typo gefixt: gewicht_t -> gewicht_test
            
            # 1. Kakerlaken-Check hat Vorrang: verdächtige Teile isolieren
            if self.check_kakerlaken_gefahr(teil):
                self.kategorien["kakerlaken_verdaechtig"].append({
                    "name": name,
                    "grund": "Fundort/Notiz deutet auf Verseuchung hin",
                    "original_teil": teil
                })
                continue
            
            # 2. Magnet-Test
            if self.magnet_test(teil):
                # Ferromagnetisch: Eisen, Stahl, Guss, ferritischer Edelstahl
                funken = self.funken_test(teil)
                if funken == "gusseisen" or "guss" in teil.get("material", "").lower():
                    self.kategorien["eisenhaltig"].append({"name": name, "typ": "Gusseisen", "dichte": round(dichte, 2)})
                elif funken == "edelstahl" or (dichte > 7.5 and dichte < 8.1 and "edelstahl" in teil.get("material", "").lower()):
                    # Ferritischer Edelstahl ist magnetisch, Dichte ~7.7
                    self.kategorien["edelstahl"].append({"name": name, "typ": "ferritisch (magnetisch)", "dichte": round(dichte, 2)})
                else:
                    self.kategorien["eisenhaltig"].append({"name": name, "typ": "Stahl/Eisen", "dichte": round(dichte, 2)})
                continue
            
            # 3. Nicht magnetisch -> Dichte & Farbe prüfen
            if dichte > 0:
                if 2.5 <= dichte <= 3.0:  # Aluminium ~2.7
                    self.kategorien["aluminium"].append({"name": name, "dichte": round(dichte, 2), "farbe": farbe})
                elif 8.7 <= dichte <= 9.1:  # Kupfer ~8.96
                    self.kategorien["kupfer"].append({"name": name, "dichte": round(dichte, 2), "farbe": farbe})
                elif 8.3 <= dichte <= 8.7:  # Messing ~8.4-8.7
                    self.kategorien["messing"].append({"name": name, "dichte": round(dichte, 2), "farbe": farbe})
                elif 7.7 <= dichte <= 8.1:  # Austenitischer Edelstahl ~7.9-8.0 (nicht magnetisch)
                    self.kategorien["edelstahl"].append({"name": name, "typ": "austenitisch (nicht magnetisch)", "dichte": round(dichte, 2)})
                else:
                    self.kategorien["sonstiges"].append({"name": name, "dichte": round(dichte, 2), "farbe": farbe, "magnetisch": False})
            else:
                # Fallback: Farb-Check wenn keine Dichte da
                if "gold" in farbe or "gelb" in farbe:
                    self.kategorien["messing"].append({"name": name, "vermutung": "Farbe Messing", "farbe": farbe})
                elif "rot" in farbe or "orange" in farbe:
                    self.kategorien["kupfer"].append({"name": name, "vermutung": "Farbe Kupfer", "farbe": farbe})
                elif "weiss" in farbe or "silber" in farbe or "grau" in farbe:
                    self.kategorien["aluminium"].append({"name": name, "vermutung": "Farbe Alu/Edelstahl", "farbe": farbe})
                else:
                    self.kategorien["sonstiges"].append({"name": name, "farbe": farbe, "grund": "Keine Dichte, Farbe unklar"})
    
    def get_bericht(self):
        """Gibt Zusammenfassung als Text zurück."""
        lines = ["=== Schuppen-Metall-Bericht ==="]
        for kat, teile in self.kategorien.items():
            if teile:
                lines.append(f"\n{kat.upper()} ({len(teile)}):")
                for t in teile[:5]:  # Max 5 pro Kategorie anzeigen
                    lines.append(f"  - {t.get('name', '?')}: {t}")
                if len(teile) > 5:
                    lines.append(f"  ... und {len(teile)-5} weitere")
        return "\n".join(lines)
    
    def export_kategorien(self):
        """Gibt Dict mit Kategorien für Weiterverarbeitung zurück."""
        return {k: v for k, v in self.kategorien.items() if v}


if __name__ == "__main__":
    # Selbsttest für neuen_tag
    test_daten = {
        "gestern": {"think": 12, "eat": 3},
        "fehlschlaege": {"schrott_suchen": 2},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 2
    }
    print("--- Test neuer_tag ---")
    print(neuer_tag(test_daten))
    
    # Test MetallSortierer
    print("\n--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "gewicht_g": 50, "volumen_cm3": 6.4, "farbe": "silber", "fundort": "Regal"},
        {"name": "Alu-Profil", "material": "Aluminium", "gewicht_g": 270, "volumen_cm3": 100, "farbe": "silber", "fundort": "Boden hinter Karton"},
        {"name": "Kupferrohr", "material": "Kupfer", "gewicht_g": 896, "volumen_cm3": 100, "farbe": "rot", "fundort": "Ecke feucht"},
        {"name": "Edelstahlschraube V2A", "material": "Edelstahl austenitisch", "gewicht_g": 79, "volumen_cm3": 10, "farbe": "silber", "fundort": "Kiste"},
        {"name": "Messingdüse", "material": "Messing", "gewicht_g": 85, "volumen_cm3": 10, "farbe": "gold", "fundort": "Schublade"},
        {"name": "Rostiger Nagel", "material": "Eisen", "gewicht_g": 10, "volumen_cm3": 1.3, "farbe": "braun", "fundort": "Boden"},
        {"name": "Unbekanntes Teil", "gewicht_g": 50, "volumen_cm3": 20, "farbe": "grün", "fundort": "Dunkelheit"},
        "kein_dict_objekt",
    ]
    sorter.sortiere_metall(test_teile)
    print(sorter.get_bericht())
    print("\n--- Export ---")
    print(sorter.export_kategorien())