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
    # Fallback für alles andere (z.B. custom Objects, datetime): String-Repräsentation
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
        # Kakerlaken-Check vorab
        if teil.get("kakerlaken_spuren", False):
            return "kakerlaken_verdaechtig"
        
        magnetisch = self.magnet_test(teil)
        dichte = self.dichte_test(teil)
        farbe = self.farbe_test(teil)
        material_hint = teil.get("material", "").lower()
        
        # Logik: Magnetisch + Dichte ~7.8 -> Eisen/Stahl
        if magnetisch and 7.0 <= dichte <= 8.5:
            if "edelstahl" in material_hint or "v2a" in material_hint or "v4a" in material_hint:
                return "edelstahl"
            return "eisenhaltig"
        
        # Nicht magnetisch, Dichte prüfen
        if not magnetisch:
            if 2.5 <= dichte <= 3.0: # Aluminium ~2.7
                return "aluminium"
            if 8.5 <= dichte <= 9.5: # Kupfer ~8.96
                if "rosa" in farbe or "rot" in farbe or "kupfer" in material_hint:
                    return "kupfer"
            if 8.3 <= dichte <= 8.7: # Messing ~8.5
                if "gelb" in farbe or "gold" in farbe or "messing" in material_hint:
                    return "messing"
            if dichte > 9.5: # Schwermetall, evtl. Blei/Wolfram -> Sonstiges
                return "sonstiges"
        
        # Fallback: Wenn magnetisch aber Dichte komisch, oder gar nix passt
        if magnetisch:
            return "eisenhaltig" # Best guess
        
        return "schrott"

    def sortiere_metall(self, teile_liste: List[dict]) -> Dict[str, List[dict]]:
        """Hauptschleife: nimmt Liste, befüllt self.kategorien, gibt Dict zurück."""
        self.reset()
        for teil in teile_liste:
            if not isinstance(teil, dict):
                continue
            kat = self._kategorisiere_einzelteil(teil)
            # Anreichern mit Testergebnissen für Transparenz
            angereichert = teil.copy()
            angereichert["_magnetisch"] = self.magnet_test(teil)
            angereichert["_dichte"] = self.dichte_test(teil)
            angereichert["_farbe"] = self.farbe_test(teil)
            angereichert["_kategorie"] = kat
            self.kategorien[kat].append(angereichert)
        return self.kategorien

    def to_json(self) -> str:
        """Gibt Kategorien als JSON-String zurück (ASCII-safe, sortiert)."""
        sicher = _json_sicher(self.kategorien)
        return json.dumps(sicher, ensure_ascii=False, indent=2, sort_keys=True)


# --- Selbsttest beim direkten Aufruf ---
if __name__ == "__main__":
    # Test neuer_tag
    print("=== Test neuer_tag ===")
    test_daten_1 = {
        "gestern": {"think": 12, "eat": 3},
        "fehlschlaege": {"schrott_suchen": 2},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 0
    }
    print(json.dumps(neuer_tag(test_daten_1), ensure_ascii=False, indent=2))
    
    test_daten_2 = {
        "gestern": {},
        "fehlschlaege": {},
        "stimmung": 30,
        "wetter": "",
        "kakerlaken_level": 0
    }
    print(json.dumps(neuer_tag(test_daten_2), ensure_ascii=False, indent=2))

    # Test MetallSortierer
    print("\n=== Test MetallSortierer ===")
    sorter = MetallSortierer()
    test_teile = [
        {"id": 1, "material": "Eisenstab", "gewicht_g": 780, "volumen_cm3": 100, "farbe": "grau"},
        {"id": 2, "material": "Alu-Profil", "gewicht_g": 270, "volumen_cm3": 100, "farbe": "silber"},
        {"id": 3, "material": "Kupferrohr", "gewicht_g": 896, "volumen_cm3": 100, "farbe": "rot"},
        {"id": 4, "material": "Messing-Schraube", "gewicht_g": 85, "volumen_cm3": 10, "farbe": "gold"},
        {"id": 5, "material": "Edelstahl V2A", "gewicht_g": 790, "volumen_cm3": 100, "farbe": "silber", "kakerlaken_spuren": True},
        {"id": 6, "material": "Plastik", "gewicht_g": 50, "volumen_cm3": 50, "farbe": "bunt"},
    ]
    ergebnis = sorter.sortiere_metall(test_teile)
    print(sorter.to_json())