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
        "blei": 11.34, "zink": 7.13, "nickel": 8.91,
        "zinn": 7.31, "gold": 19.3, "silber": 10.49,
        "standard": 7.8  # Fallback
    }

    def _rate_metall_typ(self, teil: Dict) -> str:
        """Heuristik: Markierung, Dichte, Magnetismus, Farbe -> Typ-String."""
        # 1. Explizite Markierung prüfen
        mark = str(teil.get("markierung", "")).lower().strip()
        for k in self.DICHTEN:
            if k in mark:
                return k
        
        # 2. Dichte berechnen, falls Masse & Volumen da
        masse = teil.get("masse_g")
        vol = teil.get("volumen_cm3")
        dichte = None
        if isinstance(masse, (int, float)) and isinstance(vol, (int, float)) and vol > 0:
            dichte = masse / vol
        
        magnetisch = bool(teil.get("magnetisch", False))
        farbe = str(teil.get("farbe", "")).lower()
        
        # 3. Entscheidungsbaum
        if dichte is not None:
            # Nächste Dichte finden
            best_match = min(self.DICHTEN.items(), key=lambda kv: abs(kv[1] - dichte))
            typ_guess = best_match[0]
            
            # Magnetismus als starkes Filter für Eisen/Stahl
            if magnetisch and typ_guess in ["aluminium", "magnesium", "titan", "kupfer", "messing", "bronze", "zink", "blei", "zinn", "gold", "silber"]:
                return "stahl" if dichte > 7.5 else "eisen"
            if not magnetisch and typ_guess in ["stahl", "eisen", "guss", "ferro", "edelstahl", "nickel"]:
                # Edelstahl kann amagnetisch sein, Nickel magnetisch
                if "edelstahl" in mark or (farbe in ["silber", "weiss", "grau"] and dichte > 7.5):
                     return "edelstahl"
                if farbe in ["rot", "orange", "gold"]:
                     return "kupfer" if dichte > 8.5 else "messing"
            return typ_guess
        
        # 4. Fallback nur über Magnetismus & Farbe
        if magnetisch:
            return "stahl" if farbe not in ["rot", "braun"] else "guss"
        if farbe in ["rot", "orange", "kupfer"]:
            return "kupfer"
        if farbe in ["gold", "gelb", "messing"]:
            return "messing"
        if farbe in ["weiss", "hellgrau", "silber"] and masse and masse < 500:
            return "aluminium"
        
        return "unbekannt"

    def sortieren(self, teile: List[Dict]) -> Dict:
        """Sortiert Teile in Kategorien, gibt JSON-sicheres Dict zurück."""
        kategorien = {}
        for i, teil in enumerate(teile):
            if not isinstance(teil, dict):
                continue
            typ = self._rate_metall_typ(teil)
            kat = typ.capitalize()
            if kat not in kategorien:
                kategorien[kat] = []
            # Anreichern mit Erkanntem Typ
            angereichert = dict(teil)
            angereichert["erkanntes_metall"] = typ
            angereichert["index"] = i
            kategorien[kat].append(_json_sicher(angereichert))
        
        # Zusammenfassung
        summary = {k: len(v) for k, v in kategorien.items()}
        return _json_sicher({"kategorien": kategorien, "zusammenfassung": summary, "anzahl_gesamt": len(teile)})


if __name__ == "__main__":
    # Selbsttest für neuer_tag
    print("=== Test neuer_tag ===")
    test_daten_1 = {
        "gestern": {"think": 12, "eat": 3},
        "fehlschlaege": {"schrott_suchen": 2},
        "stimmung": 10,
        "wetter": "sonnig",
        "kakerlaken_level": 0
    }
    erg1 = neuer_tag(test_daten_1)
    print("Runde 1 (Frage):", json.dumps(erg1, ensure_ascii=False, indent=2))
    
    # Simuliere KI-Antwort
    test_daten_1["ki_antwort"] = "think: Aluminium sortieren | schrott_suchen: Kisten durchwühlen | eat: Brötchen"
    erg2 = neuer_tag(test_daten_1)
    print("Runde 2 (Antwort):", json.dumps(erg2, ensure_ascii=False, indent=2))

    # Test Notfall Kakerlaken
    test_notfall = {"gestern": {}, "fehlschlaege": {}, "stimmung": 50, "wetter": "regen", "kakerlaken_level": 8}
    erg_not = neuer_tag(test_notfall)
    print("Notfall:", json.dumps(erg_not, ensure_ascii=False, indent=2))

    # Selbsttest für MetallSortierer
    print("\n=== Test MetallSortierer ===")
    sorter = MetallSortierer()
    test_teile = [
        {"markierung": "AlMg3", "masse_g": 270, "volumen_cm3": 100, "farbe": "silber"},
        {"markierung": "", "masse_g": 785, "volumen_cm3": 100, "magnetisch": True, "farbe": "grau"},
        {"markierung": "Cu", "masse_g": 896, "volumen_cm3": 100, "farbe": "rot"},
        {"masse_g": 100, "volumen_cm3": 50, "magnetisch": False, "farbe": "weiss"}, # Alu Verdacht
        {"masse_g": 500, "volumen_cm3": 50, "magnetisch": True, "farbe": "braun"},  # Guss/Eisen
        {"markierung": "V2A", "magnetisch": False, "farbe": "silber"}, # Edelstahl
        {"markierung": "Messing", "farbe": "gold"},
        {"farbe": "silber", "magnetisch": False, "masse_g": 10, "volumen_cm3": 1}, # Klein, leicht
        {"markierung": "Blei", "masse_g": 1134, "volumen_cm3": 100},
        {"markierung": "Unbekanntes Ding", "farbe": "grün"} # Müll
    ]
    ergebnis = sorter.sortieren(test_teile)
    print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
    print("\nTests durchgelaufen. Alles schick.")