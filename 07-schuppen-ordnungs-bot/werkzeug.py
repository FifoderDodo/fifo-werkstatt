def neuer_tag(daten):
    """
    Entscheidungslogik für einen neuen Tag im Schuppen.
    Nimmt Status-Dict, gibt Plan-Dict zurück.
    """
    gestern = daten.get("gestern", {})
    fehlschlaege = daten.get("fehlschlaege", {})
    stimmung = daten.get("stimmung", 0)
    wetter = daten.get("wetter", "bewoelkt").lower()
    kakerlaken_level = daten.get("kakerlaken_level", 0)
    
    notiz = ""
    plan = []
    
    if "ki_antwort" in daten and daten["ki_antwort"]:
        notiz = (notiz + " | " if notiz else "") + f"KI rät: {daten['ki_antwort'][:100]}"
    
    if kakerlaken_level >= 7:
        notiz = "Achtung: Starke Kakerlaken-Aktivität! Erst Abwehr, dann Sortieren."
        plan.append({"aktion": "walk_to", "text": "Giftschrank holen: Sprühgift & Köder"})
        plan.append({"aktion": "nachsehen", "text": "Ecken, Kartons & Ritzen absprühen"})
        if len(plan) >= 2:
            plan.append({"aktion": "spazieren", "text": "Lüften & Kopf freibekommen nach Gift"})
        return {"notiz": notiz[:200], "plan": plan[:3]}
    elif kakerlaken_level >= 4:
        notiz = "Kakerlaken verdächtig. Checken bevor ich Metall anfasse."
        plan.append({"aktion": "nachsehen", "text": "Dunkle Ecken & alte Kartons kontrollieren"})
    
    if len(plan) < 3:
        if stimmung < -50:
            notiz = (notiz + " | " if notiz else "") + "Stimmung im Keller. Erst frische Luft schnappen."
            plan.append({"aktion": "spazieren", "text": "Kopf freibekommen vor dem Schuppen"})
        elif stimmung < 20:
            notiz = notiz or "Laune mittelmäßig. Kaffee wäre gut."
            plan.append({"aktion": "drink", "text": "Wasser oder Kaffee trinken"})
    
    if wetter in ["sonnig", "heiter"] and len(plan) < 3:
        if "spazieren" not in [p["aktion"] for p in plan]:
            if not plan or plan[-1]["aktion"] != "spazieren":
                 plan.append({"aktion": "spazieren", "text": "Gutes Wetter nutzen, kurz raus"})
    
    if len(plan) < 3 and stimmung > -70 and kakerlaken_level < 7:
        fehlschlaege_projekt = fehlschlaege.get("am_projekt_arbeiten", 0)
        
        if fehlschlaege_projekt > 3 and "ki_antwort" not in daten:
            return {"frage_an_ki": f"Projekt 'MetallSortierer' klemmt (Fehlschläge: {fehlschlaege_projekt}). Was ist der häufigste Grund, warum Magnet/Dichte-Tests in Python-Simulationen fehlschlagen? Kurz."}
        
        if fehlschlaege_projekt > 2:
            notiz = (notiz + " | " if notiz else "") + "Projekt klemmt. Erst nachdenken, dann coden."
            plan.append({"aktion": "think", "text": "Sortierlogik für Metallteile durchdenken"})
        else:
            notiz = notiz or "Ran an den Speck: Schuppen-Bot Grundstruktur fertig, polieren."
            plan.append({"aktion": "am_projekt_arbeiten", "text": "werkzeug.py: MetallSortierer verfeinern und testen"})
    
    if len(plan) >= 2 and len(plan) < 3 and "eat" not in [p["aktion"] for p in plan]:
        plan.append({"aktion": "eat", "text": "Frühstück machen"})
    
    plan = plan[:3]
    
    return {
        "notiz": notiz[:200],
        "plan": plan
    }


import json
import os
import re
from typing import Any, Dict, List


def validiere_dateipfad(pfad: str, basis_verzeichnis: str = ".") -> str:
    """
    Prüft Pfad auf Directory Traversal und normalisiert ihn.
    Gibt absoluten Pfad zurück, wenn er sicher unter basis_verzeichnis liegt.
    Wirft ValueError bei Unsicherheit.
    """
    if not pfad or not isinstance(pfad, str):
        raise ValueError("Pfad leer oder ungültig")
    abs_basis = os.path.abspath(basis_verzeichnis)
    abs_ziel = os.path.abspath(os.path.join(abs_basis, pfad))
    if not abs_ziel.startswith(abs_basis):
        raise ValueError(f"Pfad führt aus Basis raus: {pfad}")
    if re.search(r'[\x00-\x1f]', pfad):
        raise ValueError("Steuerzeichen im Pfad")
    return abs_ziel


def _json_sicher(obj: Any) -> Any:
    """Rekursiver Helfer: macht Objekte JSON-sicher (Standardbibliothek only)."""
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, dict):
        return {str(k): _json_sicher(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_json_sicher(v) for v in obj]
    return str(obj)


class MetallSortierer:
    """
    Metall-Sortierlogik für den Schuppen-Bot.
    Nimmt Liste von Schrott-Teilen (Dicts), sortiert in Kategorien.
    Liefert JSON-sicheres Ergebnis-Dict.
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
            "kakerlaken_verdaechtig": []
        }
    
    def reset(self):
        """Leert alle Kategorien für neuen Durchlauf."""
        for k in self.kategorien:
            self.kategorien[k] = []
    
    def magnet_test(self, teil: dict) -> bool:
        """Simuliert Magnet-Test. True = ferromagnetisch (Eisen/Stahl/Guss)."""
        material = teil.get("material", "").lower()
        return any(m in material for m in ["eisen", "stahl", "ferro", "guss"])
    
    def funken_test(self, teil: dict) -> str:
        """Simuliert Funkenbild-Test."""
        mat = teil.get("material", "").lower()
        if "edelstahl" in mat: return "edelstahl"
        if "guss" in mat: return "gusseisen"
        return "unbekannt"

    def dichte_test(self, teil: dict) -> float:
        """Dichte-Abschätzung über Gewicht/Volumen in g/cm³."""
        gewicht = teil.get("gewicht_g", 0.0)
        volumen = teil.get("volumen_cm3", 1.0)
        if volumen <= 0:
            return 0.0
        return round(gewicht / volumen, 2)

    def farbe_test(self, teil: dict) -> str:
        """Prüft die äußere Farbe des Fundstücks."""
        return teil.get("farbe", "unbekannt").lower()

    def _kategorisiere_einzelteil(self, teil: dict) -> str:
        """Entscheidet Kategorie für ein einzelnes Teil basierend auf Tests."""
        name = teil.get("name", "Unbekannt")
        magnetisch = self.magnet_test(teil)
        dichte = self.dichte_test(teil)
        farbe = self.farbe_test(teil)
        funken = self.funken_test(teil)
        material_hint = teil.get("material", "").lower()
        
        # Kakerlaken-Check (Priorität hoch)
        if teil.get("kakerlaken_spuren", False) or "kot" in name.lower():
            return "kakerlaken_verdaechtig"
        
        # Explizite Material-Hinweise nutzen
        if "kupfer" in material_hint or (farbe in ["rot", "orange", "kupfer"] and 8.5 <= dichte <= 9.5):
            return "kupfer"
        if "messing" in material_hint or (farbe in ["gelb", "gold", "messing"] and 8.0 <= dichte <= 8.8):
            return "messing"
        if "aluminium" in material_hint or (not magnetisch and 2.5 <= dichte <= 3.0):
            return "aluminium"
        if "edelstahl" in material_hint or funken == "edelstahl":
            return "edelstahl"
        
        # Magnetisch & Dichte -> Eisen/Stahl/Guss
        if magnetisch:
            if dichte > 7.0: # Typisch Stahl/Eisen
                return "eisenhaltig"
            return "eisenhaltig" # Fallback magnetisch
        
        # Nicht magnetisch, Dichte-Check
        if dichte > 8.0:
            if farbe in ["rot", "orange"]: return "kupfer"
            if farbe in ["gelb", "gold"]: return "messing"
            return "sonstiges" # Schwermetall unklar
        if dichte > 2.0:
            return "aluminium" # Leichtmetall Verdacht
        
        return "schrott"

    def _kombiniere_kategorien_und_filter(self, ergebnis: dict) -> dict:
        """
        Post-Processing: Kombiniert ähnliche Kategorien, filtert leere,
        und markiert Auffälligkeiten (z.B. viele Kakerlaken-Teile).
        """
        combined = {}
        # Mapping für Zusammenführung
        merge_map = {
            "eisenhaltig": ["eisenhaltig", "guss", "stahl"],
            "nichteisen_metalle": ["kupfer", "messing", "aluminium", "edelstahl"],
            "problemfall": ["kakerlaken_verdaechtig", "schrott", "sonstiges"]
        }
        
        for ziel_kategorie, quellen in merge_map.items():
            gesammelt = []
            for q in quellen:
                if q in ergebnis and ergebnis[q]:
                    gesammelt.extend(ergebnis[q])
            if gesammelt:
                combined[ziel_kategorie] = gesammelt
        
        # Originale Kategorien auch behalten für Details, aber gefiltert (nur non-empty)
        for k, v in ergebnis.items():
            if v:
                combined[f"detail_{k}"] = v
        
        # Statistik & Warnungen
        stats = {k: len(v) for k, v in ergebnis.items() if v}
        combined["_stats"] = stats
        
        if stats.get("kakerlaken_verdaechtig", 0) > 2:
            combined["_warnung"] = "Mehrere Teile mit Kakerlaken-Spuren. Schuppenbereich säubern!"
        
        return combined

    def sortiere_metall(self, teile_liste: List[dict]) -> dict:
        """Hauptmethode: Sortiert Liste von Teilen in self.kategorien."""
        self.reset()
        for teil in teile_liste:
            kat = self._kategorisiere_einzelteil(teil)
            if kat in self.kategorien:
                self.kategorien[kat].append(teil)
            else:
                self.kategorien["sonstiges"].append(teil)
        
        # Roh-Ergebnis kopieren
        roh_ergebnis = {k: list(v) for k, v in self.kategorien.items()}
        
        # Neue Kombinations-Logik anwenden
        finales_ergebnis = self._kombiniere_kategorien_und_filter(roh_ergebnis)
        
        return finales_ergebnis

    def to_json(self) -> str:
        """Gibt sortiertes Ergebnis als JSON-String zurück."""
        # Nutzt den letzten Stand von self.kategorien (roh) oder ruft sortiere_metall nochmal? 
        # Sicherer: wir geben die aktuellen Kategorien + Stats zurück.
        ausgabe = {k: list(v) for k, v in self.kategorien.items()}
        ausgabe["_stats"] = {k: len(v) for k, v in self.kategorien.items()}
        return json.dumps(_json_sicher(ausgabe), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # Selbsttests
    print("=== Test neuer_tag ===")
    test_daten = {
        "gestern": {"think": 12, "eat": 3},
        "fehlschlaege": {"schrott_suchen": 2},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 0
    }
    print(json.dumps(neuer_tag(test_daten), ensure_ascii=False, indent=2))
    
    print("\n=== Test MetallSortierer ===")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Rostiger Nagel", "material": "Eisen", "gewicht_g": 10, "volumen_cm3": 1.3, "farbe": "braun"},
        {"name": "Kupferrohr", "material": "Kupfer", "gewicht_g": 500, "volumen_cm3": 56, "farbe": "rot", "kakerlaken_spuren": True},
        {"name": "Alu-Profil", "material": "Aluminium", "gewicht_g": 200, "volumen_cm3": 74, "farbe": "silber"},
        {"name": "Schraube VA", "material": "Edelstahl V2A", "gewicht_g": 20, "volumen_cm3": 2.5, "farbe": "silber"},
        {"name": "Unbekanntes Stück", "gewicht_g": 100, "volumen_cm3": 50, "farbe": "grau"},
    ]
    ergebnis = sorter.sortiere_metall(test_teile)
    print(json.dumps(_json_sicher(ergebnis), ensure_ascii=False, indent=2))