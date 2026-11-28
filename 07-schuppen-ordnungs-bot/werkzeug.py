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
        "zink": 7.13, "zinialloy": 6.6,
        "blei": 11.34,
        "nickel": 8.9,
        "gold": 19.3, "silber": 10.5,
        "unbekannt": 7.0
    }

    @classmethod
    def _erkenne_metall(cls, name: str, magnetisch: bool, farbe: str, gewicht_g: float, volumen_cm3: float) -> str:
        """Einfache Heuristik basierend auf Eigenschaften."""
        name_lower = name.lower()
        dichte = gewicht_g / volumen_cm3 if volumen_cm3 > 0 else 0

        # Namens-Checks zuerst
        for k in cls.DICHTEN:
            if k in name_lower:
                return k

        # Magnetisch -> Eisen/Stahl/Guss
        if magnetisch:
            if dichte > 7.5:
                return "stahl" if dichte > 7.7 else "guss"
            return "eisen"

        # Nicht magnetisch, Dichte prüfen
        if dichte < 2.0:
            return "magnesium"
        if 2.5 <= dichte <= 3.0:
            return "aluminium"
        if 4.0 <= dichte <= 5.0:
            return "titan"
        if 8.0 <= dichte <= 9.5:
            if "rot" in farbe or "orange" in farbe:
                return "kupfer"
            if "gelb" in farbe:
                return "messing"
            return "bronze"
        if dichte > 10:
            return "blei"

        return "unbekannt"

    @classmethod
    def sortieren(cls, teile: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Erwartet Liste von Dicts mit Keys:
        - name (str)
        - magnetisch (bool)
        - farbe (str)
        - gewicht_g (float)
        - volumen_cm3 (float)
        Gibt Dict mit Kategorien und Statistik zurück.
        """
        kategorien = {k: [] for k in cls.DICHTEN.keys()}
        kategorien["unbekannt"] = []
        fehler = []

        for i, teil in enumerate(teile):
            try:
                name = str(teil.get("name", f"Teil_{i}"))
                magnetisch = bool(teil.get("magnetisch", False))
                farbe = str(teil.get("farbe", "grau")).lower()
                gewicht = float(teil.get("gewicht_g", 0))
                volumen = float(teil.get("volumen_cm3", 1))

                if gewicht <= 0 or volumen <= 0:
                    fehler.append(f"{name}: Ungültige Masse/Volumen")
                    kategorien["unbekannt"].append(_json_sicher(teil))
                    continue

                kategorie = cls._erkenne_metall(name, magnetisch, farbe, gewicht, volumen)
                eintrag = _json_sicher(teil)
                eintrag["erkannt_als"] = kategorie
                eintrag["dichte_g_cm3"] = round(gewicht / volumen, 2)
                kategorien[kategorie].append(eintrag)
            except Exception as e:
                fehler.append(f"{teil.get('name', '?')}: {e}")
                kategorien["unbekannt"].append(_json_sicher(teil))

        # Leere Kategorien entfernen für sauberes JSON
        ergebnis = {k: v for k, v in kategorien.items() if v}
        ergebnis["_meta"] = {
            "gesamt_teile": len(teile),
            "kategorien_gefunden": len(ergebnis) - 1,
            "fehler": fehler
        }
        return _json_sicher(ergebnis)


if __name__ == "__main__":
    # Test-Suite für neuen_tag
    print("=== Test neuer_tag ===")
    # 1. Kakerlaken-Alarm (keine KI-Frage)
    d1 = {"gestern": {"think": 5}, "fehlschlaege": {},"stimmung": 10, "wetter": "regen", "kakerlaken_level": 8}
    print("Test 1 (Kakerlaken >= 7):", json.dumps(neuer_tag(d1), ensure_ascii=False, indent=2))

    # 2. Runde 1: KI fragen
    d2 = {"gestern": {"schrott_suchen": 3}, "fehlschlaege": {"aufheben": 1}, "stimmung": 30, "wetter": "sonnig", "kakerlaken_level": 2}
    print("\nTest 2 (Runde 1 - Frage):", json.dumps(neuer_tag(d2), ensure_ascii=False, indent=2))

    # 3. Runde 2: Gute KI-Antwort
    d3 = {**d2, "ki_antwort": "think: Sortierlogik prüfen | schrott_suchen: Alu-Haufen angehen | einlagern: Kisten beschriften"}
    print("\nTest 3 (Runde 2 - Gute Antwort):", json.dumps(neuer_tag(d3), ensure_ascii=False, indent=2))

    # 4. Runde 2: Schlechte KI-Antwort -> Fallback
    d4 = {**d2, "ki_antwort": "blabla"}
    print("\nTest 4 (Runde 2 - Fallback):", json.dumps(neuer_tag(d4), ensure_ascii=False, indent=2))

    # 5. Stimmungstest Fallback
    d5 = {"gestern": {}, "fehlschlaege": {}, "stimmung": -60, "wetter": "nebel", "kakerlaken_level": 0, "ki_antwort": ""}
    print("\nTest 5 (Stimmung < -50):", json.dumps(neuer_tag(d5), ensure_ascii=False, indent=2))

    # Test MetallSortierer
    print("\n=== Test MetallSortierer ===")
    test_teile = [
        {"name": "Alu-Profil 1m", "magnetisch": False, "farbe": "silber", "gewicht_g": 2700, "volumen_cm3": 1000},
        {"name": "Eisenstab dick", "magnetisch": True, "farbe": "schwarz", "gewicht_g": 7850, "volumen_cm3": 1000},
        {"name": "Kupferrohr Alt", "magnetisch": False, "farbe": "rot", "gewicht_g": 8960, "volumen_cm3": 1000},
        {"name": "Messingschrauben", "magnetisch": False, "farbe": "gelb", "gewicht_g": 850, "volumen_cm3": 100},
        {"name": "Mysterie-Metall", "magnetisch": False, "farbe": "grau", "gewicht_g": 500, "volumen_cm3": 100},
        {"name": "Kaputtes Teil", "magnetisch": True, "farbe": "braun", "gewicht_g": -10, "volumen_cm3": 10}, # Fehlerfall
    ]
    ergebnis = MetallSortierer.sortieren(test_teile)
    print(json.dumps(ergebnis, ensure_ascii=False, indent=2))