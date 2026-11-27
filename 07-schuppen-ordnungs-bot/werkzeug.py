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
            kakerlaken = self.check_kakerlaken_gefahr(teil)
            
            # Kakerlaken-Verdacht: Duplizieren in Extra-Kategorie
            if kakerlaken:
                self.kategorien["kakerlaken_verdaechtig"].append({
                    "name": name, "grund": "Fundort verdächtig", "original": teil
                })
            
            # 1. Magnet-Test: Ferromagnetisches (Eisen, Stahl, Guss)
            if magnetisch:
                funken = self.funken_test(teil)
                if funken == "gusseisen":
                    self.kategorien["eisenhaltig"].append({"name": name, "typ": "Gusseisen", "dichte": round(dichte, 2)})
                else:
                    self.kategorien["eisenhaltig"].append({"name": name, "typ": "Stahl/Eisen", "dichte": round(dichte, 2)})
                continue
            
            # 2. Nicht magnetisch -> Dichte-Baum
            # Aluminium ~2.7
            if 2.5 <= dichte <= 3.0:
                self.kategorien["aluminium"].append({"name": name, "dichte": round(dichte, 2), "farbe": farbe})
            # Kupfer ~8.9, Messing ~8.4-8.7, Bronze ~8.8
            elif 8.0 <= dichte <= 9.2:
                if "gelb" in farbe or "gold" in farbe or "messing" in farbe:
                    self.kategorien["messing"].append({"name": name, "dichte": round(dichte, 2), "farbe": farbe})
                elif "rot" in farbe or "orange" in farbe or "kupfer" in farbe:
                    self.kategorien["kupfer"].append({"name": name, "dichte": round(dichte, 2), "farbe": farbe})
                else:
                    # Unklar Kupfer/Messing/Bronze -> sonstiges
                    self.kategorien["sonstiges"].append({"name": name, "dichte": round(dichte, 2), "farbe": farbe, "vermutung": "Kupferlegierung"})
            # Edelstahl (austenitisch) ~7.9, Titan ~4.5, Nickel ~8.9
            elif 7.5 <= dichte <= 8.2:
                # Heuristik: Wenn 'edelstahl' im Material-String oder silber/weiß glänzend
                mat_str = teil.get("material", "").lower()
                if "edelstahl" in mat_str or ("silber" in farbe or "weiß" in farbe or "grau" in farbe):
                     self.kategorien["edelstahl"].append({"name": name, "dichte": round(dichte, 2), "farbe": farbe})
                else:
                     self.kategorien["sonstiges"].append({"name": name, "dichte": round(dichte, 2), "farbe": farbe, "vermutung": "Edelstahl/Nickel?"})
            # Titan, Zink, Blei, Zinn etc.
            else:
                self.kategorien["sonstiges"].append({"name": name, "dichte": round(dichte, 2), "farbe": farbe, "magnetisch": magnetisch})
        
        return self.kategorien
    
    def get_bericht(self):
        """Gibt Text-Zusammenfassung der Sortierung zurück."""
        lines = ["=== Schuppen-Metall-Bericht ==="]
        total = 0
        for kat, teile in self.kategorien.items():
            if teile:
                lines.append(f"{kat.upper()} ({len(teile)}):")
                for t in teile[:5]:  # Max 5 pro Katze anzeigen
                    lines.append(f"  - {t.get('name', '?')}: Dichte {t.get('dichte', '?')}, Farbe {t.get('farbe', '?')}")
                if len(teile) > 5:
                    lines.append(f"  ... und {len(teile)-5} weitere")
                total += len(teile)
        lines.append(f"---\nGesamt sortiert: {total} Teile")
        if self.kategorien["kakerlaken_verdaechtig"]:
            lines.append("!!! ACHTUNG: Kakerlaken-verdächtige Teile gefunden !!!")
        return "\n".join(lines)
    
    def export_kategorien(self):
        """Gibt Dict zurück für JSON-Speicherung/Weiterverarbeitung."""
        return {k: v for k, v in self.kategorien.items() if v}


if __name__ == "__main__":
    # Test-Daten für neuen_tag
    test_daten = [
        {
            "gestern": {"think": 12, "eat": 3},
            "fehlschlaege": {"schrott_suchen": 2, "am_projekt_arbeiten": 5},
            "stimmung": -10,
            "wetter": "sonnig",
            "kakerlaken_level": 3
        },
        {
            "gestern": {},
            "fehlschlaege": {},
            "stimmung": 80,
            "wetter": "regen",
            "kakerlaken_level": 8
        }
    ]
    
    print("--- Test neuer_tag ---")
    for i, d in enumerate(test_daten):
        print(f"\nTest {i+1}: {d}")
        erg = neuer_tag(d)
        print(f"Notiz: {erg.get('notiz')}")
        print(f"Plan: {erg.get('plan')}")
        if "frage_an_ki" in erg:
            print(f"KI-FRAGE: {erg['frage_an_ki']}")
            # Simuliere KI-Antwort
            d["ki_antwort"] = "Meistens fehlen Volumen-Daten oder Material-Strings sind inkonsistent. Prüfe Input-Validierung."
            erg2 = neuer_tag(d)
            print(f"Nach KI: {erg2.get('notiz')}")
            print(f"Plan: {erg2.get('plan')}")
    
    # Test MetallSortierer
    print("\n--- Test MetallSortierer ---")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Schraube M10", "material": "Stahl", "gewicht_g": 50, "volumen_cm3": 6.4, "farbe": "silber", "fundort": "Regal A"},
        {"name": "Alu-Profil", "material": "Aluminium", "gewicht_g": 300, "volumen_cm3": 111, "farbe": "silber", "fundort": "Ecke hinten"},
        {"name": "Kupferrohr", "material": "Kupfer", "gewicht_g": 890, "volumen_cm3": 100, "farbe": "rot", "fundort": "Karton feucht"},
        {"name": "Messing-Ventil", "material": "Messing", "gewicht_g": 420, "volumen_cm3": 50, "farbe": "gold", "fundort": "Werkbank"},
        {"name": "Edelstahl-Schale (V2A)", "material": "Edelstahl austenitisch", "gewicht_g": 790, "volumen_cm3": 100, "farbe": "weiß", "fundort": "Spüle"},
        {"name": "Guss-Eisenstück", "material": "Grauguss", "gewicht_g": 720, "volumen_cm3": 92, "farbe": "grau", "fundort": "Boden nähe Nest"},
        {"name": "Unbekanntes Teil", "material": "Plastik", "gewicht_g": 10, "volumen_cm3": 20, "farbe": "blau", "fundort": "Müll"},
        "Kein Dict sondern String",
        {"name": "Ferritischer Edelstahl (Magnetisch)", "material": "Edelstahl ferritisch", "gewicht_g": 780, "volumen_cm3": 100, "farbe": "silber", "fundort": "Magnet-Schublade"}
    ]
    
    ergebnis = sorter.sortiere_metall(test_teile)
    print(sorter.get_bericht())
    print("\nExport-Keys:", list(sorter.export_kategorien().keys()))