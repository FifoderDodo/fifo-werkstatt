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
    # Grobe Dichten in g/cm³ für Schätzung
    DICHTEN = {
        "aluminium": 2.7, "aluminiumlegierung": 2.7,
        "magnesium": 1.74,
        "titan": 4.5,
        "stahl": 7.85, "eisen": 7.87, "guss": 7.2, "ferro": 7.8,
        "edelstahl": 7.9,
        "kupfer": 8.96, "messing": 8.5, "bronze": 8.8,
        "zink": 7.1, "blei": 11.34, "zinn": 7.3
    }
    
    # Toleranzen für Dichtevergleich (relativ)
    DICHTE_TOLERANZ = 0.08  # 8% Puffer für Schmutz, Legierungen, Messfehler
    
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
            # Ferromagnetisch: Eisen, Stahl, Guss, Ferro-Legierungen
            ferromagnetisch = ["eisen", "stahl", "guss", "ferro", "carbon", "baustahl"]
            # Edelstahl ist oft NICHT magnetisch (austenitisch), aber manche sind es.
            # Wir treaten Edelstahl separat.
            return any(m in material for m in ferromagnetisch)
        except Exception:
            return False
    
    def funken_test(self, teil: dict) -> str:
        """Simuliert Funkenbild-Test. Gibt Typ zurück: 'lang_gelb', 'kurz_rot', 'keine', 'weiss_hell'."""
        try:
            material = str(teil.get("material", "")).lower()
            kohlenstoff = float(teil.get("kohlenstoff_gehalt", 0.0))
            
            if "edelstahl" in material:
                return "keine"  # Austenitisch = keine Funken
            if "guss" in material or kohlenstoff > 2.0:
                return "kurz_rot"  # Gusseisen: kurze, rote Funken (Kohlenstoff)
            if "stahl" in material or "eisen" in material or "ferro" in material:
                if kohlenstoff > 0.6:
                    return "lang_gelb"  # Hochkohlenstoff: lange, gelbe Funkenstrahlen
                return "kurz_rot"  # Baustahl: kurze, rötliche Funken
            return "keine"  # NE-Metalle: keine Funken
        except Exception:
            return "keine"
    
    def dichte_test(self, teil: dict) -> float:
        """Berechnet/Schätzt Dichte in g/cm³ aus Masse/Volumen oder Material-Namen."""
        try:
            # 1. Versuch: Masse / Volumen falls vorhanden
            masse = teil.get("masse_g")
            volumen = teil.get("volumen_cm3")
            if masse is not None and volumen is not None and volumen > 0:
                return float(masse) / float(volumen)
            
            # 2. Fallback: Material-Name gegen Tabelle
            material = str(teil.get("material", "")).lower()
            for name, dichte in self.DICHTEN.items():
                if name in material:
                    # Kleine zufällige Variation simulieren (Messfehler)
                    import random
                    return dichte * random.uniform(0.97, 1.03)
            
            return 0.0
        except Exception:
            return 0.0
    
    def _dichte_match(self, gemessene_dichte: float, ziel_dichte: float) -> bool:
        """Prüft ob gemessene Dichte innerhalb 8% Toleranz zur Zieldichte liegt."""
        if ziel_dichte <= 0 or gemessene_dichte <= 0:
            return False
        abweichung = abs(gemessene_dichte - ziel_dichte) / ziel_dichte
        return abweichung <= self.DICHTE_TOLERANZ
    
    def material_pruefung(self, teil: dict) -> dict:
        """Führt alle Tests durch, bestimmt Kategorie."""
        ergebnis = {
            "kategorie": "schrott",
            "magnetisch": False,
            "funken": "keine",
            "dichte": 0.0,
            "verdaechtig": False
        }
        
        # Kakerlaken-Check: Teile aus dunklen Ecken, Kartons, lange liegend
        quelle = str(teil.get("quelle", "")).lower()
        if any(w in quelle for w in ["ecke", "karton", "kiste", "boden", "lager"]):
            ergebnis["verdaechtig"] = True
        
        ergebnis["magnetisch"] = self.magnet_test(teil)
        ergebnis["funken"] = self.funken_test(teil)
        ergebnis["dichte"] = round(self.dichte_test(teil), 2)
        
        # Entscheidungslogik
        mat = str(teil.get("material", "")).lower()
        dichte = ergebnis["dichte"]
        mag = ergebnis["magnetisch"]
        funken = ergebnis["funken"]
        
        # 1. Kupfer / Messing / Bronze (nicht magnetisch, hohe Dichte, keine Funken)
        if not mag and funken == "keine":
            if self._dichte_match(dichte, self.DICHTEN["kupfer"]):
                ergebnis["kategorie"] = "kupfer"
            elif self._dichte_match(dichte, self.DICHTEN["messing"]):
                ergebnis["kategorie"] = "messing"
            elif self._dichte_match(dichte, self.DICHTEN["bronze"]):
                ergebnis["kategorie"] = "messing"  # Bronze -> Messing-Kategorie
            elif self._dichte_match(dichte, self.DICHTEN["zink"]):
                ergebnis["kategorie"] = "sonstiges"
            elif self._dichte_match(dichte, self.DICHTEN["aluminium"]):
                ergebnis["kategorie"] = "aluminium"
            elif self._dichte_match(dichte, self.DICHTEN["magnesium"]):
                ergebnis["kategorie"] = "sonstiges"
            elif self._dichte_match(dichte, self.DICHTEN["titan"]):
                ergebnis["kategorie"] = "sonstiges"
            elif self._dichte_match(dichte, self.DICHTEN["blei"]):
                ergebnis["kategorie"] = "sonstiges"
            elif self._dichte_match(dichte, self.DICHTEN["zinn"]):
                ergebnis["kategorie"] = "sonstiges"
        
        # 2. Magnetisch (Eisen, Stahl, Guss)
        if mag:
            if "edelstahl" in mat or (funken == "keine" and dichte > 7.5):
                # Austenitischer Edelstahl ist nicht magnetisch, aber falls doch magnetisch & keine Funken -> evtl. ferritisch
                # Wenn explizit 'edelstahl' im Namen: Edelstahl-Kategorie
                ergebnis["kategorie"] = "edelstahl"
            elif "guss" in mat or funken == "kurz_rot":
                ergebnis["kategorie"] = "eisenhaltig"  # Guss ist eisenhaltig
            else:
                ergebnis["kategorie"] = "eisenhaltig"
        
        # 3. Kakerlaken-Verdacht überwiegt
        if ergebnis["verdaechtig"]:
            ergebnis["kategorie"] = "kakerlaken_verdaechtig"
        
        return ergebnis
    
    def sortiere(self, teile: list) -> dict:
        """Haupt-Einstieg: sortiert Liste von Teilen in Kategorien."""
        self.reset()
        for teil in teile:
            if not isinstance(teil, dict):
                continue
            pruef = self.material_pruefung(teil)
            kat = pruef["kategorie"]
            # Teil mit Prüfergebnis anreichern
            teil_mit_info = {**teil, "pruefung": pruef}
            if kat in self.kategorien:
                self.kategorien[kat].append(teil_mit_info)
            else:
                self.kategorien["schrott"].append(teil_mit_info)
        return self.get_ergebnis()
    
    def get_ergebnis(self) -> dict:
        """Liefert JSON-sicheres Zusammenfassung-Dict."""
        summary = {}
        for kat, liste in self.kategorien.items():
            summary[kat] = {
                "anzahl": len(liste),
                "teile": [_json_sicher(t) for t in liste]
            }
        return _json_sicher(summary)