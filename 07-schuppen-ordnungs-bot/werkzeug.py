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
        "blei": 11.34, "zink": 7.13, "nickel": 8.91, "zinn": 7.31,
        "unbekannt": 7.0
    }

    @classmethod
    def _rate_metall_typ(cls, name: str, dichte: float = None) -> str:
        """Heuristik: Bestimme Metall-Typ aus Name (Keywords) und/oder Dichte."""
        name_lower = (name or "").lower()
        # 1. Schlüsselwörter im Namen prüfen
        for k, v in cls.DICHTEN.items():
            if k != "unbekannt" and k in name_lower:
                return k
        # 2. Falls Dichte gegeben, nahestehenden Typ suchen
        if dichte is not None and isinstance(dichte, (int, float)):
            best = "unbekannt"
            min_diff = float('inf')
            for k, v in cls.DICHTEN.items():
                if k == "unbekannt":
                    continue
                diff = abs(v - dichte)
                if diff < min_diff:
                    min_diff = diff
                    best = k
            # Toleranz: 0.5 g/cm³
            if min_diff < 0.5:
                return best
        return "unbekannt"

    @classmethod
    def sortieren(cls, teile: List[Dict]) -> Dict:
        """
        Sortiert Liste von Teilen in Kategorien.
        Teil-Dict erwartet: {'name': str, 'gewicht_g': float, 'volumen_cm3': float, ...}
        Rückgabe: {'kategorien': {typ: [teil, ...]}, 'unsortiert': [teil, ...]}
        """
        kategorien = {}
        unsortiert = []

        for teil in teile:
            if not isinstance(teil, dict):
                unsortiert.append(teil)
                continue

            name = teil.get("name", "")
            gewicht = teil.get("gewicht_g")
            volumen = teil.get("volumen_cm3")
            
            dichte = None
            if isinstance(gewicht, (int, float)) and isinstance(volumen, (int, float)) and volumen > 0:
                dichte = gewicht / volumen
            
            typ = cls._rate_metall_typ(name, dichte)
            
            if typ == "unbekannt":
                unsortiert.append(teil)
            else:
                kategorien.setdefault(typ, []).append(teil)

        # JSON-sicher machen
        return _json_sicher({
            "kategorien": kategorien,
            "unsortiert": unsortiert
        })


if __name__ == "__main__":
    # Selbsttest für neuer_tag
    print("=== Test neuer_tag ===")
    # Runde 1: Keine KI-Antwort -> Frage
    daten1 = {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen": 2}, "stimmung": 10, "wetter": "regnerisch", "kakerlaken_level": 1}
    erg1 = neuer_tag(daten1)
    print(f"1. Runde 1 (KI fragen): {json.dumps(erg1, ensure_ascii=False)}")
    
    # Runde 2: KI antwortet leer (Limit) -> Fallback
    daten2 = {**daten1, "ki_antwort": ""}
    erg2 = neuer_tag(daten2)
    print(f"2. Runde 2 (Leere KI -> Fallback): {json.dumps(erg2, ensure_ascii=False)}")

    # Runde 2: KI antwortet valide
    daten3 = {**daten1, "ki_antwort": "think: Sortierlogik prüfen | schrott_suchen: Aluminiumhaufen | eat: Brotzeit"}
    erg3 = neuer_tag(daten3)
    print(f"3. Runde 2 (Valide KI): {json.dumps(erg3, ensure_ascii=False)}")

    # Kakerlaken-Notfall
    daten4 = {**daten1, "kakerlaken_level": 8}
    erg4 = neuer_tag(daten4)
    print(f"4. Notfall Kakerlaken: {json.dumps(erg4, ensure_ascii=False)}")

    print("\n=== Test MetallSortierer ===")
    test_teile = [
        {"name": "Aluprofil 2m", "gewicht_g": 1200, "volumen_cm3": 444},
        {"name": "Edelstahlschrauben", "gewicht_g": 500, "volumen_cm3": 63},
        {"name": "Kupferrohr", "gewicht_g": 896, "volumen_cm3": 100},
        {"name": "Mystery-Metall", "gewicht_g": 100, "volumen_cm3": 20}, # Dichte 5 -> Titan?
        {"name": "Plastikdeckel", "gewicht_g": 10, "volumen_cm3": 50}, # Dichte 0.2 -> Unbekannt
        "kein dict",
    ]
    ergebnis = MetallSortierer.sortieren(test_teile)
    print(json.dumps(ergebnis, ensure_ascii=False, indent=2))