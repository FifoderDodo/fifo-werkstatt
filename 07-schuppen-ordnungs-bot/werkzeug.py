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
            
            # 1. Kakerlaken-Verdacht hat absolute Priorität
            if self.check_kakerlaken_gefahr(teil):
                self.kategorien["kakerlaken_verdaechtig"].append({
                    "name": name, "grund": "Fundort verseucht", "teil": teil
                })
                continue
            
            # 2. Magnet-Test: Eisenhaltiges (Stahl, Guss, Eisen)
            if self.magnet_test(teil):
                # Edelstahl kann magnetisch sein (ferritisch), aber Funken-test/Dichte prüfen
                funken = self.funken_test(teil)
                if funken == "edelstahl" or (dichte > 7.5 and "chrom" in teil.get("material", "").lower()):
                    self.kategorien["edelstahl"].append({"name": name, "dichte": round(dichte, 2), "teil": teil})
                else:
                    self.kategorien["eisenhaltig"].append({"name": name, "dichte": round(dichte, 2), "teil": teil})
                continue
            
            # 3. Nicht-magnetisch: Dichte & Farbe für NE-Metalle
            # Kupfer: ~8.9 g/cm³, rot/orange
            if 8.5 <= dichte <= 9.3 and any(c in farbe for c in ["rot", "orange", "kupfer", "pink"]):
                self.kategorien["kupfer"].append({"name": name, "dichte": round(dichte, 2), "teil": teil})
                continue
            
            # Messing: ~8.4-8.7 g/cm³, gelb/gold
            if 8.2 <= dichte <= 8.8 and any(c in farbe for c in ["gelb", "gold", "messing", "hell"]):
                self.kategorien["messing"].append({"name": name, "dichte": round(dichte, 2), "teil": teil})
                continue
            
            # Aluminium: ~2.7 g/cm³, silbrig/weiß/matt
            if 2.5 <= dichte <= 3.0 and any(c in farbe for c in ["silber", "weiss", "weiß", "grau", "matt", "aluminium"]):
                self.kategorien["aluminium"].append({"name": name, "dichte": round(dichte, 2), "teil": teil})
                continue
            
            # Edelstahl (austenitisch, nicht magnetisch): ~7.9 g/cm³, silbrig/glänzend
            if 7.7 <= dichte <= 8.1 and any(c in farbe for c in ["silber", "glanz", "edel", "chrom"]):
                self.kategorien["edelstahl"].append({"name": name, "dichte": round(dichte, 2), "teil": teil})
                continue
            
            # 4. Fallback
            self.kategorien["sonstiges"].append({
                "name": name, "dichte": round(dichte, 2), "farbe": farbe, "grund": "Keine Regel getroffen", "teil": teil
            })
        
        return self.kategorien
    
    def get_bericht(self):
        """Gibt Zusammenfassung als Text zurück."""
        lines = ["=== SCHUPPEN-SORTIER-BERICHT ==="]
        total = 0
        for kat, teile in self.kategorien.items():
            anzahl = len(teile)
            total += anzahl
            if anzahl > 0:
                lines.append(f"{kat.upper()}: {anzahl} Stück")
                for t in teile[:3]:  # Nur erste 3 zeigen
                    lines.append(f"  - {t.get('name', '?')} (Dichte: {t.get('dichte', '?')}) {t.get('grund', '')}")
                if anzahl > 3:
                    lines.append(f"  ... und {anzahl - 3} weitere")
        lines.append(f"GESAMT: {total} Teile sortiert.")
        return "\n".join(lines)
    
    def export_kategorien(self):
        """Gibt Dict zurück für JSON-Speicherung oder Weiterverarbeitung."""
        # Nur relevante Infos, keine Referenzen auf Original-Objekte
        export = {}
        for kat, teile in self.kategorien.items():
            export[kat] = [
                {k: v for k, v in t.items() if k != "teil"} for t in teile
            ]
        return export


if __name__ == "__main__":
    # Test-Daten für neuen_tag
    test_daten = {
        "gestern": {"think": 12, "eat": 3},
        "fehlschlaege": {"schrott_suchen": 1, "am_projekt_arbeiten": 4},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 2
    }
    print("--- Test neuer_tag ---\n", neuer_tag(test_daten))
    
    # Test MetallSortierer
    print("\n--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "gewicht_g": 50, "volumen_cm3": 6.5, "fundort": "Regal", "farbe": "silber"},
        {"name": "Alu-Profil", "material": "Aluminium", "gewicht_g": 300, "volumen_cm3": 110, "fundort": "Boden hinter Karton", "farbe": "grau", "notiz": "staubig"},
        {"name": "Kupferrohr", "material": "Kupfer", "gewicht_g": 890, "volumen_cm3": 100, "fundort": "Ecke feucht", "farbe": "rot"},
        {"name": "Messing-Ventil", "material": "Messing", "gewicht_g": 400, "volumen_cm3": 46, "fundort": "Werkzeugkasten", "farbe": "gold"},
        {"name": "Edelstahl-Schale", "material": "Edelstahl V2A", "gewicht_g": 500, "volumen_cm3": 63, "fundort": "Spüle", "farbe": "silber glänzend"},
        {"name": "Guss-Eisenstück", "material": "Grauguss", "gewicht_g": 1200, "volumen_cm3": 150, "fundort": "dunkel hinter Ofen", "farbe": "grau schwarz"},
        {"name": "Unbekanntes Teil", "material": "Plastik", "gewicht_g": 10, "volumen_cm3": 20, "fundort": "Mitte", "farbe": "blau"},
        {"name": "Magnetischer Brocken", "material": "Eisen", "gewicht_g": 2000, "volumen_cm3": 250, "fundort": "Karton oben", "farbe": "rostbraun"},
    ]
    ergebnis = sorter.sortiere_metall(test_teile)
    print(sorter.get_bericht())
    print("\nExport:", sorter.export_kategorien())