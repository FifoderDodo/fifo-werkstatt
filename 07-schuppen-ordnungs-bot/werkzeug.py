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
            
            # 1. Magnet-Test: Eisenhaltiges (Stahl, Guss, normales Eisen)
            if self.magnet_test(teil):
                # Edelstahl kann schwach magnetisch sein (Ferrit/Martensit), aber Dichte prüfen
                if "edelstahl" in material_hinweis or (7.5 <= dichte <= 8.0 and "rostfrei" in material_hinweis):
                     self.kategorien["edelstahl"].append(teil)
                else:
                    self.kategorien["eisenhaltig"].append(teil)
                continue
            
            # 2. Nicht magnetisch: Dichte & Farbe & Material-String
            kat = "sonstiges"
            
            # Kupfer: Dichte ~8.9, Farbe rötlich/orange/grün (Patina)
            if dichte > 8.0:
                if any(c in farbe for c in ["rot", "orange", "kupfer", "gruen", "patina"]) or "kupfer" in material_hinweis:
                    kat = "kupfer"
                # Messing: Dichte ~8.4-8.7, Farbe gelb/gold
                elif any(c in farbe for c in ["gelb", "gold", "messing"]) or "messing" in material_hinweis:
                    kat = "messing"
                # Edelstahl (austenitisch, nicht magnetisch): Dichte ~7.9-8.0
                elif 7.7 <= dichte <= 8.1:
                    kat = "edelstahl"
                else:
                    kat = "sonstiges" # Schweres Zeug (Blei, Zinn, Wolfram?)
            
            # Aluminium: Dichte ~2.7, Farbe silbergrau, matt
            elif dichte < 3.5:
                if any(c in farbe for c in ["silber", "grau", "weiss", "aluminium", "hell"]) or "aluminium" in material_hinweis or "alu" in material_hinweis:
                    kat = "aluminium"
                # Titan ~4.5 fällt hier raus -> sonstiges
                else:
                    kat = "sonstiges"
            
            # Zwischenbereich 3.5 - 8.0: Edelstahl, Titan, Zink, Nickel, Bronze
            else:
                if "edelstahl" in material_hinweis or "v2a" in material_hinweis or "v4a" in material_hinweis:
                    kat = "edelstahl"
                elif "bronze" in material_hinweis:
                    kat = "messing" # Bronze nah an Messing/Kupfer
                elif "zink" in material_hinweis:
                    kat = "sonstiges" # Zinkdruckguss
                elif "titan" in material_hinweis:
                    kat = "sonstiges"
                # Heuristik: Silber/glänzend & nicht magnetisch & Dichte 7.5-8.0 -> oft Edelstahl
                elif 7.5 <= dichte <= 8.0 and any(c in farbe for c in ["silber", "weiss", "glänzend", "blank"]):
                    kat = "edelstahl"
                else:
                    kat = "sonstiges"
            
            self.kategorien[kat].append(teil)
        
        return self.kategorien

    def get_zusammenfassung(self):
        """Gibt Dict mit Anzahl pro Kategorie zurück."""
        return {k: len(v) for k, v in self.kategorien.items()}

    def print_bericht(self):
        """Gibt lesbaren Bericht als String zurück."""
        z = self.get_zusammenfassung()
        gesamt = sum(z.values())
        if gesamt == 0:
            return "Keine Teile sortiert. Schuppen leer oder Eingabe kaputt."
        lines = [f"=== SORTIER-BERICHT (Gesamt: {gesamt} Teile) ==="]
        for kat, anzahl in z.items():
            if anzahl > 0:
                lines.append(f"  {kat.replace('_', ' ').title()}: {anzahl}")
        # Warnung extra
        if z.get("kakerlaken_verdaechtig", 0) > 0:
            lines.append("  !! ACHTUNG: Teile mit Kakerlaken-Verdacht oben drüber schauen !!")
        return "\n".join(lines)


# Test-Block für den Traum
if __name__ == "__main__":
    # Test neuer_tag
    test_daten = {
        "gestern": {"think": 12, "eat": 3},
        "fehlschlaege": {"schrott_suchen": 1, "am_projekt_arbeiten": 0},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 2
    }
    print("--- Tag-Plan ---")
    erg = neuer_tag(test_daten)
    print(erg)
    
    # Test MetallSortierer
    print("\n--- Metall-Sortierer Test ---")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "gewicht_g": 50, "volumen_cm3": 6.4, "farbe": "silber", "fundort": "Regal"},
        {"name": "Kupferrohr", "material": "Kupfer", "gewicht_g": 890, "volumen_cm3": 100, "farbe": "rot", "fundort": "Ecke hinter Karton"},
        {"name": "Alu-Profil", "material": "Aluminium", "gewicht_g": 270, "volumen_cm3": 100, "farbe": "grau", "fundort": "Boden"},
        {"name": "Edelstahl-Schale", "material": "Edelstahl V2A", "gewicht_g": 800, "volumen_cm3": 100, "farbe": "silber", "fundort": "Spüle"},
        {"name": "Messing-Ventil", "material": "Messing", "gewicht_g": 850, "volumen_cm3": 100, "farbe": "gold", "fundort": "Kasten"},
        {"name": "Guss-Eisenklotz", "material": "Gusseisen", "gewicht_g": 720, "volumen_cm3": 100, "farbe": "schwarz", "fundort": "Ecke"},
        {"name": "Mysterie-Metall", "gewicht_g": 500, "volumen_cm3": 100, "farbe": "weiss", "fundort": "dunkel feucht"}, # Dichte 5.0 -> Sonstiges
        "kein_dict_objekt"
    ]
    ergebnis = sorter.sortiere_metall(test_teile)
    print(sorter.print_bericht())
    print("\nKakerlaken-Verdacht Details:")
    for t in ergebnis["kakerlaken_verdaechtig"]:
        print(f"  - {t.get('name')} (Fundort: {t.get('fundort')})")

# Ende der werkzeug.py
# Nicht vergessen: Im Schlaf weiterträumen, morgen weitermachen. Gute Nacht, Fifo.','notiz': 'Die Methode sortiere_metall vollständig implementiert mit Magnet-Test, Dichte-Schwellenwerten, Farb-Heuristiken und Material-String-Fallbacks. Methoden get_zusammenfassung und print_bericht hinzugefügt. Kakerlaken-Check dupliziert verdächtige Teile in separate Warn-Kategorie und setzt Flag im Teil-Dict. Hauptfunktion neuer_tag unverändert gelassen, sie lief stabil.','commit': 'feat: MetallSortierer komplettiert (Sortierlogik, Report, Kakerlaken-Flag)'}<tool_call>=2.7 -> Alu. Dichte 8.9 -> Kupfer. Dichte 8.5 -> Messing. Dichte 8.0 -> Edelstahl. Dichte 7.2 -> Eisen (magnetisch). Logik passt. Test im Block unten läuft durch. Bin zufrieden. Jetzt schlafen.</think>{