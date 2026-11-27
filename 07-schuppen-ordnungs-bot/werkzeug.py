def neuer_tag(daten):
    """
    Entscheidungslogik für einen neuen Tag im Schuppen.
    Nimmt Status-Dict, gibt Plan-Dict zurück.
    """
    try:
        gestern = daten.get("gestern", {})
        fehlschlaege = daten.get("fehlschlaege", {})
        stimmung = int(daten.get("stimmung", 0))
        wetter = str(daten.get("wetter", "bewoelkt")).lower()
        kakerlaken_level = int(daten.get("kakerlaken_level", 0))
    except (ValueError, TypeError) as e:
        return {"notiz": f"Fehlerhafte Eingabedaten: {e}", "plan": []}

    notiz = ""
    plan = []
    
    if "ki_antwort" in daten and daten["ki_antwort"]:
        notiz = (notiz + " | " if notiz else "") + f"KI rät: {str(daten['ki_antwort'])[:100]}"
    
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
    try:
        if not pfad or not isinstance(pfad, str):
            raise ValueError("Pfad leer oder ungültig")
        abs_basis = os.path.abspath(basis_verzeichnis)
        abs_ziel = os.path.abspath(os.path.join(abs_basis, pfad))
        if not abs_ziel.startswith(abs_basis):
            raise ValueError(f"Pfad führt aus Basis raus: {pfad}")
        if re.search(r'[\x00-\x1f]', pfad):
            raise ValueError("Steuerzeichen im Pfad")
        return abs_ziel
    except Exception as e:
        raise ValueError(f"Pfadvalidierung fehlgeschlagen: {e}") from e


def _json_sicher(obj: Any) -> Any:
    """Rekursiver Helfer: macht Objekte JSON-sicher (Standardbibliothek only)."""
    try:
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        if isinstance(obj, dict):
            return {str(k): _json_sicher(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [_json_sicher(v) for v in obj]
        return str(obj)
    except Exception:
        return "<nicht serialisierbar>"


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
        try:
            material = str(teil.get("material", "")).lower()
            return any(m in material for m in ["eisen", "stahl", "ferro", "guss"])
        except Exception:
            return False
    
    def funken_test(self, teil: dict) -> str:
        """Simuliert Funkenbild-Test."""
        try:
            mat = str(teil.get("material", "")).lower()
            if "edelstahl" in mat: return "edelstahl"
            if "guss" in mat: return "gusseisen"
            return "unbekannt"
        except Exception:
            return "fehler"

    def dichte_test(self, teil: dict) -> float:
        """Dichte-Abschätzung über Gewicht/Volumen in g/cm³."""
        try:
            gewicht = float(teil.get("gewicht_g", 0.0))
            volumen = float(teil.get("volumen_cm3", 1.0))
            if volumen <= 0:
                return 0.0
            return round(gewicht / volumen, 2)
        except (ValueError, TypeError, ZeroDivisionError):
            return 0.0

    def farbe_test(self, teil: dict) -> str:
        """Prüft die äußere Farbe des Fundstücks."""
        try:
            return str(teil.get("farbe", "unbekannt")).lower()
        except Exception:
            return "unbekannt"

    def _kategorisiere_einzelteil(self, teil: dict) -> str:
        """Entscheidet Kategorie für ein einzelnes Teil."""
        try:
            if not isinstance(teil, dict):
                return "schrott"
            
            name = str(teil.get("name", "unbekannt"))
            
            if teil.get("kakerlaken_verdaechtig", False):
                return "kakerlaken_verdaechtig"
            
            magnetisch = self.magnet_test(teil)
            dichte = self.dichte_test(teil)
            farbe = self.farbe_test(teil)
            funken = self.funken_test(teil)
            
            if magnetisch:
                if "edelstahl" in funken or (7.5 <= dichte <= 8.0 and "rostfrei" in str(teil.get("material", "")).lower()):
                    return "edelstahl"
                return "eisenhaltig"
            
            if 2.5 <= dichte <= 3.0 and farbe in ["silber", "grau", "weiß"]:
                return "aluminium"
            if 8.5 <= dichte <= 9.0 and farbe in ["rot", "orange", "braun"]:
                return "kupfer"
            if 8.3 <= dichte <= 8.7 and farbe in ["gelb", "gold", "messing"]:
                return "messing"
            
            if dichte > 0:
                return "sonstiges"
            
            return "schrott"
        except Exception:
            return "schrott"

    def sortiere_metall(self, teile_liste: List[dict]) -> Dict[str, List[dict]]:
        """Sortiert eine Liste von Teilen in die Kategorien."""
        self.reset()
        if not isinstance(teile_liste, list):
            return self.kategorien
        
        for teil in teile_liste:
            try:
                kat = self._kategorisiere_einzelteil(teil)
                if kat in self.kategorien:
                    self.kategorien[kat].append(teil)
                else:
                    self.kategorien["schrott"].append(teil)
            except Exception:
                self.kategorien["schrott"].append(teil)
        return self.kategorien

    def _kombiniere_kategorien_und_filter(self) -> Dict[str, Any]:
        """Aggregiert Kategorien zu Gruppen, fügt Statistiken und Warnungen hinzu."""
        try:
            eisen_gruppe = self.kategorien["eisenhaltig"] + self.kategorien["edelstahl"]
            nichteisen_gruppe = (
                self.kategorien["aluminium"] + self.kategorien["kupfer"] + 
                self.kategorien["messing"] + self.kategorien["sonstiges"]
            )
            problem_faelle = self.kategorien["kakerlaken_verdaechtig"] + self.kategorien["schrott"]
            
            gesamt = sum(len(v) for v in self.kategorien.values())
            
            warnungen = []
            if len(self.kategorien["kakerlaken_verdaechtig"]) > 0:
                warnungen.append(f"{len(self.kategorien['kakerlaken_verdaechtig'])} Teile kakerlakenverdächtig - Handschuhe an!")
            if len(self.kategorien["schrott"]) > gesamt * 0.5 and gesamt > 0:
                warnungen.append("Viel unidentifizierbarer Schrott - Sensoren prüfen.")
            
            return {
                "gruppen": {
                    "eisen_metalle": eisen_gruppe,
                    "nichteisen_metalle": nichteisen_gruppe,
                    "problem_faelle": problem_faelle
                },
                "statistik": {
                    "gesamt_teile": gesamt,
                    "kategorien": {k: len(v) for k, v in self.kategorien.items()}
                },
                "warnungen": warnungen
            }
        except Exception as e:
            return {"gruppen": {}, "statistik": {"gesamt_teile": 0}, "warnungen": [f"Aggregation fehlgeschlagen: {e}"]}

    def to_json(self) -> str:
        """Gibt kompletten Sortierstand als JSON-String zurück."""
        try:
            daten = {
                "kategorien": self.kategorien,
                "auswertung": self._kombiniere_kategorien_und_filter()
            }
            return json.dumps(_json_sicher(daten), ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"fehler": f"JSON-Serialisierung fehlgeschlagen: {e}"})


if __name__ == "__main__":
    # Test neuer_tag
    print("=== Test neuer_tag ===")
    test1 = {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen": 2}, "stimmung": -10, "wetter": "sonnig"}
    print(json.dumps(neuer_tag(test1), ensure_ascii=False, indent=2))
    
    test2 = {"gestern": {}, "fehlschlaege": {}, "stimmung": 30, "wetter": "regen", "kakerlaken_level": 5}
    print(json.dumps(neuer_tag(test2), ensure_ascii=False, indent=2))
    
    # Test MetallSortierer
    print("\n=== Test MetallSortierer ===")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Rostiger Nagel", "material": "Eisen", "gewicht_g": 5.0, "volumen_cm3": 0.64, "farbe": "braun"},
        {"name": "Blanker Alu-Winkel", "material": "Aluminium", "gewicht_g": 27.0, "volumen_cm3": 10.0, "farbe": "silber"},
        {"name": "Kupferrohr Stück", "material": "Kupfer", "gewicht_g": 89.0, "volumen_cm3": 10.0, "farbe": "rot"},
        {"name": "Merwürdiges Etwas", "material": "Plastik", "gewicht_g": 10, "volumen_cm3": 20, "farbe": "bunt", "kakerlaken_verdaechtig": True},
        {"name": "Kaputtes Teil", "material": "Unbekannt", "gewicht_g": 0, "volumen_cm3": 0, "farbe": "grau"},
    ]
    sorter.sortiere_metall(test_teile)
    print(sorter.to_json())