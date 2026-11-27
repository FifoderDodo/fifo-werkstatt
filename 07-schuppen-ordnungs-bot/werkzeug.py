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

    def gewicht_test(self, teil: dict) -> float:
        """Dichte-Abschätzung über Gewicht/Volumen in g/cm³."""
        gewicht = teil.get("gewicht_g", 0.0)
        volumen = teil.get("volumen_cm3", 1.0)
        if volumen <= 0:
            return 0.0
        return gewicht / volumen

    def farbe_test(self, teil: dict) -> str:
        """Prüft die äußere Farbe des Fundstücks."""
        return teil.get("farbe", "unbekannt").lower()

    def dichte_test(self, teil: dict) -> float:
        """Alias für gewicht_test für lesbareren Code in Logik."""
        return self.gewicht_test(teil)

    def _kategorisiere_einzelteil(self, teil: dict) -> str:
        """Ermittelt Kategorie für ein einzelnes Teil. Gibt Key von self.kategorien zurück."""
        # 1. Kakerlaken-Check (Priorität hoch)
        if teil.get("kakerlaken_verdaechtig", False) or "kakerlake" in teil.get("name", "").lower():
            return "kakerlaken_verdaechtig"
        
        # 2. Magnet-Test
        magnetisch = self.magnet_test(teil)
        funken = self.funken_test(teil)
        dichte = self.dichte_test(teil)
        farbe = self.farbe_test(teil)
        material_hint = teil.get("material", "").lower()
        
        if magnetisch:
            # Ferromagnetisch: Eisen, Stahl, Guss
            if funken == "edelstahl": # Ferritischer Edelstahl
                return "edelstahl"
            if funken == "gusseisen" or "guss" in material_hint:
                return "eisenhaltig" # Guss landet bei Eisenhaltig/Schrott
            return "eisenhaltig"
        
        # 3. Nicht magnetisch -> Dichte & Farbe
        # Aluminium ~2.7
        if 2.5 <= dichte <= 3.0:
            return "aluminium"
        # Titan ~4.5 (selten im Schuppen) -> sonstiges
        # Edelstahl (austenitisch) ~7.9
        if 7.5 <= dichte <= 8.2:
            if "edelstahl" in material_hint or funken == "edelstahl":
                return "edelstahl"
            # Könnte auch Messing/Kupfer sein, aber Dichte passt besser zu Edelstahl/Stahl
            # Wir prüfen Farbe für Kupfer/Messing
        # Messing ~8.4 - 8.7, Kupfer ~8.9
        if 8.3 <= dichte <= 9.0:
            if "rot" in farbe or "kupfer" in farbe or "pink" in farbe:
                return "kupfer"
            if "gelb" in farbe or "gold" in farbe or "messing" in farbe:
                return "messing"
            # Fallback Dichtebereich
            if "kupfer" in material_hint: return "kupfer"
            if "messing" in material_hint: return "messing"
            return "sonstiges" # Unklar
        
        # Blei ~11.3, Zink ~7.1, Zinn ~7.3
        if dichte > 10:
            return "schrott" # Schwermetall-Schrott
        
        # 4. Fallback über Material-String
        if "aluminium" in material_hint or "alu" in material_hint:
            return "aluminium"
        if "kupfer" in material_hint:
            return "kupfer"
        if "messing" in material_hint:
            return "messing"
        if "edelstahl" in material_hint or "v2a" in material_hint or "v4a" in material_hint:
            return "edelstahl"
        
        return "sonstiges"

    def sortiere_metall(self, teile: List[dict]) -> Dict[str, List[dict]]:
        """
        Hauptmethode: Sortiert Liste von Teilen in self.kategorien.
        Gibt Dict mit Kategorien zurück (JSON-sicher).
        """
        self.reset()
        for teil in teile:
            if not isinstance(teil, dict):
                continue
            kat = self._kategorisiere_einzelteil(teil)
            # Anreichern mit Analyse-Daten für Debug/Log
            teil_angereichert = teil.copy()
            teil_angereichert["_analyse"] = {
                "magnetisch": self.magnet_test(teil),
                "dichte": round(self.dichte_test(teil), 2),
                "farbe": self.farbe_test(teil),
                "funken": self.funken_test(teil)
            }
            self.kategorien[kat].append(teil_angereichert)
        return _json_sicher(self.kategorien)

    def to_json(self) -> str:
        """Gibt aktuellen Stand der Kategorien als JSON-String zurück."""
        return json.dumps(_json_sicher(self.kategorien), ensure_ascii=False, indent=2)