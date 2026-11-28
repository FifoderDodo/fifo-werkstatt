def neuer_tag(daten):
    """
    Entscheidungslogik für einen neuen Tag im Schuppen.
    Nimmt Status-Dict, gibt Plan-Dict zurück.
    Zwei-Runden-KI: Erst fragen, dann mit Rat entscheiden.
    """
    try:
        gestern = daten.get("gestern", {})
        fehlschlaege = daten.get("fehlschlaege", {})
        stimmung = int(daten.get("stimmung", 0))
        wetter = str(daten.get("wetter", "bewoelkt")).lower()
        kakerlaken_level = int(daten.get("kakerlaken_level", 0))
    except (ValueError, TypeError) as e:
        return {"notiz": f"Fehlerhafte Eingabedaten: {e}", "plan": []}

    # 1. Hartes Sicherheitslimit: Kakerlaken-Plage -> Sofort-Aktion, keine KI-Frage
    if kakerlaken_level >= 7:
        notiz = "Achtung: Starke Kakerlaken-Aktivität! Erst Abwehr, dann Sortieren."
        plan = [
            {"aktion": "walk_to", "text": "Giftschrank holen: Sprühgift & Köder"},
            {"aktion": "nachsehen", "text": "Ecken, Kartons & Ritzen absprühen"},
            {"aktion": "spazieren", "text": "Lüften & Kopf freibekommen nach Gift"}
        ]
        return {"notiz": notiz[:200], "plan": plan[:3]}

    # 2. Runde 1: KI fragen, wenn noch keine Antwort da
    if "ki_antwort" not in daten:
        prompt = (
            f"Status: Stimmung {stimmung}, Wetter {wetter}, Kakerlaken-Level {kakerlaken_level}. "
            f"Gestern: {gestern}. Fehlschläge: {fehlschlaege}. "
            f"Erlaubte Aktionen: think, eat, drink, walk_to, sitzen, spazieren, "
            f"schrott_suchen, aufheben, verkaufen, einlagern, malen, komponieren, "
            f"read_news, muenze_werfen, nachsehen, am_projekt_arbeiten. "
            f"Antworte NUR mit Plan-Zeilen im Format: 'AKTION: text'. Max 3 Zeilen. "
            f"Beispiel: 'think: Sortierlogik verfeinern | eat: Frühstück | spazieren: Luft schnappen'"
        )
        return {"frage_an_ki": prompt[:1500]}

    # 3. Runde 2: KI-Antwort auswerten
    rat = daten.get("ki_antwort", "").strip()
    notiz = ""
    plan = []

    if rat:
        # Einfaches Parsen: 'aktion: text | aktion: text'
        try:
            teile = [t.strip() for t in rat.split('|')]
            for teil in teile[:3]:
                if ':' in teil:
                    akt, txt = teil.split(':', 1)
                    akt = akt.strip().lower()
                    txt = txt.strip()
                    # Validierung gegen erlaubte Aktionen
                    erlaubte = {"think", "eat", "drink", "walk_to", "sitzen", "spazieren",
                                "schrott_suchen", "aufheben", "verkaufen", "einlagern",
                                "malen", "komponieren", "read_news", "muenze_werfen",
                                "nachsehen", "am_projekt_arbeiten"}
                    if akt in erlaubte and txt:
                        plan.append({"aktion": akt, "text": txt[:100]})
        except Exception:
            pass  # Parsing fehlgeschlagen, Fallback unten

    # Fallback, falls KI nix Brauchbares lieferte oder Limit erreicht
    if not plan:
        notiz = "KI schweigt oder Format unklar. Fallback: Klein anfangen."
        if stimmung < -50:
            plan.append({"aktion": "spazieren", "text": "Kopf freibekommen vor dem Schuppen"})
        elif stimmung < 20:
            plan.append({"aktion": "drink", "text": "Wasser oder Kaffee trinken"})
        else:
            plan.append({"aktion": "think", "text": "Heutigen Schrott-Schwerpunkt festlegen"})
        if len(plan) < 2:
            plan.append({"aktion": "eat", "text": "Frühstück machen"})
        if len(plan) < 3 and wetter in ["sonnig", "heiter"]:
            plan.append({"aktion": "spazieren", "text": "Gutes Wetter nutzen, kurz raus"})
    else:
        notiz = f"KI-Plan: {rat[:150]}"

    # Kakerlaken-Warnung (Level 4-6) in Notiz aufnehmen, wenn nicht schon im Plan
    if 4 <= kakerlaken_level < 7 and not any(p["aktion"] == "nachsehen" for p in plan):
        notiz = (notiz + " | " if notiz else "") + "Kakerlaken verdächtig, Augen auf."

    return {
        "notiz": notiz[:200],
        "plan": plan[:3]
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
        "zink": 7.1, "zinial": 6.7,
        "blei": 11.34, "zinn": 7.3,
        "nickel": 8.9
    }

    # Heuristik-Regeln: (Material-Key, Magnetisch?, Farb-Hinweise, Zeichen-Regex)
    REGELN = [
        ("magnesium", False, ["grau", "weiss", "matt"], r"mg|mag"),
        ("aluminium", False, ["silber", "grau", "hell", "leicht"], r"al|alu|aw-"),
        ("titan", False, ["grau", "dunkel", "sehr fest"], r"ti|titan"),
        ("edelstahl", False, ["silber", "glänzend", "rostfrei"], r"v2a|v4a|1\.43|1\.44|edel"),
        ("stahl", True, ["grau", "schwarz", "rostig", "schwer"], r"st\d+|s\d+|stahl|fe360|fe510"),
        ("guss", True, ["grau", "schwarz", "spröde", "gusshaut"], r"gg|gt|guss"),
        ("kupfer", False, ["rot", "orange", "grünspan"] , r"cu|cu-"),
        ("messing", False, ["gelb", "gold", "messing"] , r"ms|mess|cuzn"),
        ("bronze", False, ["braun", "rotbraun", "bronze"] , r"bz|bronze|cusn"),
        ("zink", False, ["blaugrau", "zink", "weissrost"] , r"zn|zink|zinial"),
        ("blei", False, ["blaugrau", "sehr schwer", "weich", "blei"] , r"pb|blei"),
        ("nickel", True, ["silber", "glänzend", "magnetisch"] , r"ni|nickel"),
    ]

    @classmethod
    def _rate_material(cls, teil: Dict) -> str:
        """Schätzt Material anhand Dichte, Magnet, Farbe, Zeichen."""
        gewicht = float(teil.get("gewicht_g", 0))
        volumen = float(teil.get("volumen_cm3", 1))
        magnetisch = bool(teil.get("magnetisch", False))
        farbe = str(teil.get("farbe", "")).lower()
        zeichen = str(teil.get("zeichen", "")).lower()
        
        if volumen <= 0:
            return "unbekannt"
        
        dichte = gewicht / volumen
        
        best_score = -1
        best_mat = "unbekannt"
        
        for mat, mag, farben, regex in cls.REGELN:
            score = 0
            # Dichte (Gewichtung 40%)
            ziel_dichte = cls.DICHTEN.get(mat, 7.8)
            if ziel_dichte > 0:
                abweichung = abs(dichte - ziel_dichte) / ziel_dichte
                if abweichung < 0.15: score += 40
                elif abweichung < 0.30: score += 20
                elif abweichung < 0.50: score += 5
            
            # Magnetismus (Gewichtung 30%)
            if magnetisch == mag:
                score += 30
            elif magnetisch and not mag:
                score -= 20  # Aluminium/Magnesium sind nie magnetisch
            elif not magnetisch and mag:
                score -= 10  # Stahl könnte rostig/nicht magnetisch sein (selten)
            
            # Farbe (Gewichtung 20%)
            for f in farben:
                if f in farbe:
                    score += 20
                    break
            
            # Zeichen/Stempel (Gewichtung 10%)
            if regex and re.search(regex, zeichen):
                score += 10
            
            if score > best_score:
                best_score = score
                best_mat = mat
        
        return best_mat if best_score > 30 else "unbekannt"

    @classmethod
    def sortieren(cls, teile: List[Dict]) -> Dict:
        """Hauptmethode: Sortiert Liste von Teilen in Kategorien."""
        kategorien = {
            "aluminium": [], "stahl": [], "edelstahl": [], "kupfer": [],
            "messing": [], "bronze": [], "guss": [], "magnesium": [],
            "titan": [], "zink": [], "blei": [], "nickel": [],
            "unbekannt": [], "mix_fehlerhaft": []
        }
        
        for i, teil in enumerate(teile):
            if not isinstance(teil, dict):
                kategorien["mix_fehlerhaft"].append({"index": i, "fehler": "Kein Dict"})
                continue
            
            # Plausibilitätsprüfung
            if teil.get("gewicht_g", 0) <= 0 or teil.get("volumen_cm3", 0) <= 0:
                kategorien["mix_fehlerhaft"].append({"index": i, "fehler": "Gewicht/Volumen <= 0", "daten": teil})
                continue
            
            material = cls._rate_material(teil)
            ergebnis = {
                "index": i,
                "material": material,
                "dichte_g_cm3": round(teil["gewicht_g"] / teil["volumen_cm3"], 2),
                "magnetisch": teil.get("magnetisch"),
                "farbe": teil.get("farbe"),
                "zeichen": teil.get("zeichen"),
                "gewicht_g": teil["gewicht_g"],
                "volumen_cm3": teil["volumen_cm3"]
            }
            
            if material in kategorien:
                kategorien[material].append(ergebnis)
            else:
                kategorien["unbekannt"].append(ergebnis)
        
        # Leere Kategorien entfernen für sauberes JSON
        return {k: v for k, v in kategorien.items() if v}


if __name__ == "__main__":
    # Tests für neuer_tag
    print("=== Test neuer_tag ===")
    # 1. Notfall Kakerlaken
    test1 = {"gestern": {}, "fehlschlaege": {}, "stimmung": 10, "wetter": "sonnig", "kakerlaken_level": 8}
    print("Test1 (Notfall):", json.dumps(neuer_tag(test1), ensure_ascii=False, indent=2))
    
    # 2. Runde 1: KI fragen
    test2 = {"gestern": {"think": 5, "eat": 2}, "fehlschlaege": {"schrott_suchen": 1}, "stimmung": 20, "wetter": "regen", "kakerlaken_level": 2}
    print("Test2 (Runde 1):", json.dumps(neuer_tag(test2), ensure_ascii=False, indent=2))
    
    # 3. Runde 2: Gute KI-Antwort
    test3 = {**test2, "ki_antwort": "think: Kupfer sortieren | schrott_suchen: Kabelkiste prüfen | walk_to: Waage holen"}
    print("Test3 (Runde 2 OK):", json.dumps(neuer_tag(test3), ensure_ascii=False, indent=2))
    
    # 4. Runde 2: Schlechte KI-Antwort -> Fallback
    test4 = {**test2, "ki_antwort": "nonsense"}
    print("Test4 (Runde 2 Fail):", json.dumps(neuer_tag(test4), ensure_ascii=False, indent=2))
    
    # 5. Kakerlaken Warnung Level 5
    test5 = {**test2, "kakerlaken_level": 5, "ki_antwort": "think: Planen | eat: Brot"}
    print("Test5 (Kakerlaken Warnung):", json.dumps(neuer_tag(test5), ensure_ascii=False, indent=2))

    # Tests für MetallSortierer
    print("\n=== Test MetallSortierer ===")
    test_teile = [
        {"gewicht_g": 270, "volumen_cm3": 100, "magnetisch": False, "farbe": "silber matt", "zeichen": "ALU 6060"},      # Alu ~2.7
        {"gewicht_g": 785, "volumen_cm3": 100, "magnetisch": True, "farbe": "grau rostig", "zeichen": "ST37"},           # Stahl ~7.85
        {"gewicht_g": 896, "volumen_cm3": 100, "magnetisch": False, "farbe": "rot glänzend", "zeichen": "CU-ETP"},        # Kupfer ~8.96
        {"gewicht_g": 850, "volumen_cm3": 100, "magnetisch": False, "farbe": "gelb gold", "zeichen": "MS58"},           # Messing ~8.5
        {"gewicht_g": 174, "volumen_cm3": 100, "magnetisch": False, "farbe": "grau weiss", "zeichen": "MG AZ31"},       # Magnesium ~1.74
        {"gewicht_g": 790, "volumen_cm3": 100, "magnetisch": False, "farbe": "silber glänzend", "zeichen": "V2A 1.4301"},   # Edelstahl ~7.9
        {"gewicht_g": 720, "volumen_cm3": 100, "magnetisch": True, "farbe": "grau gusshaut", "zeichen": "GG25"},          # Guss ~7.2
        {"gewicht_g": 450, "volumen_cm3": 100, "magnetisch": False, "farbe": "grau dunkel", "zeichen": "TI GR2"},        # Titan ~4.5
        {"gewicht_g": 1134, "volumen_cm3": 100, "magnetisch": False, "farbe": "blaugrau weich", "zeichen": "PB"},        # Blei ~11.34
        {"gewicht_g": 500, "volumen_cm3": 10, "magnetisch": True, "farbe": "kaputt", "zeichen": ""},                  # Fehlerhaft (Dichte 50)
    ]
    
    ergebnis = MetallSortierer.sortieren(test_teile)
    print(json.dumps(_json_sicher(ergebnis), ensure_ascii=False, indent=2))