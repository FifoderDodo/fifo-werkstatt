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
        "zinn": 7.3, "blei": 11.34, "zink": 7.13, "nickel": 8.91
    }

    # Heuristische Regeln: Magnetisch, Farbe, typische Zeichen/Stempel
    REGELN = {
        "magnetisch": {"stahl", "eisen", "guss", "ferro", "nickel"},
        "nicht_magnetisch": {"aluminium", "aluminiumlegierung", "magnesium", "titan", "kupfer", "messing", "bronze", "zinn", "blei", "zink", "edelstahl"},
        "farben": {
            "silber_weiss": {"aluminium", "magnesium", "titan", "edelstahl", "zinn", "zink", "nickel"},
            "rot_gold": {"kupfer", "messing", "bronze"},
            "dunkel_grau": {"stahl", "eisen", "guss", "ferro", "blei"}
        },
        "zeichen": {
            "al": {"aluminium", "aluminiumlegierung"},
            "mg": {"magnesium"},
            "ti": {"titan"},
            "cu": {"kupfer", "messing", "bronze"},
            "pb": {"blei"},
            "sn": {"zinn"},
            "zn": {"zink"},
            "ni": {"nickel"},
            "fe": {"stahl", "eisen", "guss", "ferro"},
            "ss": {"edelstahl"}, "inox": {"edelstahl"}
        }
    }

    @classmethod
    def _rate_material(cls, teil: Dict) -> Dict[str, float]:
        """Bewertet Wahrscheinlichkeiten für Materialien basierend auf Teil-Daten."""
        score = {mat: 0.0 for mat in cls.DICHTEN}
        dichte = teil.get("dichte_g_cm3")
        magnet = teil.get("magnetisch")
        farbe = str(teil.get("farbe", "")).lower()
        zeichen = str(teil.get("zeichen", "")).lower()
        gewicht = teil.get("gewicht_g")
        volumen = teil.get("volumen_cm3")

        # 1. Dichte (stärkstes Signal, falls plausibel)
        if dichte and isinstance(dichte, (int, float)) and dichte > 0:
            for mat, d in cls.DICHTEN.items():
                diff = abs(d - dichte)
                if diff < 0.5:
                    score[mat] += 10 - diff * 10
                elif diff < 1.0:
                    score[mat] += 5 - diff * 5
        # Fallback: Dichte aus Gewicht/Volumen schätzen
        elif gewicht and volumen and isinstance(gewicht, (int, float)) and isinstance(volumen, (int, float)) and volumen > 0:
            est_dichte = gewicht / volumen
            for mat, d in cls.DICHTEN.items():
                diff = abs(d - est_dichte)
                if diff < 0.8:
                    score[mat] += 5 - diff * 3

        # 2. Magnetismus
        if isinstance(magnet, bool):
            if magnet:
                for m in cls.REGELN["magnetisch"]:
                    score[m] += 8
                for m in cls.REGELN["nicht_magnetisch"]:
                    score[m] -= 5
            else:
                for m in cls.REGELN["nicht_magnetisch"]:
                    score[m] += 5
                for m in cls.REGELN["magnetisch"]:
                    score[m] -= 3  # Edelstahl kann schwach magnetisch sein, aber selten

        # 3. Farbe
        for farb_key, mats in cls.REGELN["farben"].items():
            if farb_key.replace("_", " ") in farbe or farbe in farb_key:
                for m in mats:
                    score[m] += 3

        # 4. Zeichen / Stempel
        for key, mats in cls.REGELN["zeichen"].items():
            if key in zeichen:
                for m in mats:
                    score[m] += 15  # Stempel sind sehr verlässlich

        # Negative Scores abfangen
        return {k: max(0.0, v) for k, v in score.items()}

    @classmethod
    def sortieren(cls, teile: List[Dict]) -> Dict:
        """
        Sortiert Liste von Schrott-Teilen in Kategorien.
        Erwartet Dicts mit Keys: id, dichte_g_cm3?, magnetisch?, farbe?, zeichen?, gewicht_g?, volumen_cm3?
        Gibt Dict: {kategorie: [teil_ids], 'unsicher': [teil_ids], 'details': {teil_id: {material: score}}}
        """
        kategorien = {}
        unsicher = []
        details = {}

        for teil in teile:
            tid = str(teil.get("id", "unbekannt"))
            scores = cls._rate_material(teil)
            details[tid] = _json_sicher(scores)

            if not scores or max(scores.values()) < 1.0:
                unsicher.append(tid)
                continue

            bestes = max(scores, key=scores.get)
            # Kategorie = Oberkategorie (NE-Metall, Eisen, Sonder)
            if bestes in ("aluminium", "aluminiumlegierung", "magnesium", "titan"):
                kat = "NE_Leichtmetall"
            elif bestes in ("kupfer", "messing", "bronze", "zinn", "zink", "nickel", "blei"):
                kat = "NE_Schwer_Edel"
            elif bestes in ("stahl", "eisen", "guss", "ferro"):
                kat = "Eisen_Stahl"
            elif bestes == "edelstahl":
                kat = "Edelstahl"
            else:
                kat = "Sonstiges"

            kategorie_liste = kat
            if kategorie_liste not in kategorien:
                kategorien[kategorie_liste] = []
            kategorien[kategorie_liste].append(tid)

        return _json_sicher({
            "kategorien": kategorien,
            "unsicher": unsicher,
            "details": details
        })


if __name__ == "__main__":
    # --- Tests für neuer_tag ---
    print("=== Test neuer_tag ===")
    # 1. Notfall Kakerlaken >= 7
    test1 = {"gestern": {}, "fehlschlaege": {}, "stimmung": 10, "wetter": "sonnig", "kakerlaken_level": 8}
    erg1 = neuer_tag(test1)
    print(f"Notfall: {erg1['notiz'][:40]}... Plan: {[p['aktion'] for p in erg1['plan']]}")
    assert erg1["plan"][0]["aktion"] == "walk_to"

    # 2. Runde 1: KI fragen
    test2 = {"gestern": {"think": 2}, "fehlschlaege": {}, "stimmung": 50, "wetter": "regen", "kakerlaken_level": 1}
    erg2 = neuer_tag(test2)
    print(f"Runde 1: {erg2.get('frage_an_ki', '')[:60]}...")
    assert "frage_an_ki" in erg2

    # 3. Runde 2: Gute KI-Antwort
    test3 = {**test2, "ki_antwort": "think: Sortieren | schrott_suchen: Kabel | eat: Brot"}
    erg3 = neuer_tag(test3)
    print(f"Runde 2 OK: {erg3['notiz'][:40]}... Plan: {[p['aktion'] for p in erg3['plan']]}")
    assert len(erg3["plan"]) == 3
    assert erg3["plan"][0]["aktion"] == "think"

    # 4. Runde 2: Schlechte KI-Antwort -> Fallback
    test4 = {**test2, "ki_antwort": "blabla"}
    erg4 = neuer_tag(test4)
    print(f"Runde 2 Fail: {erg4['notiz'][:40]}... Plan: {[p['aktion'] for p in erg4['plan']]}")
    assert "Fallback" in erg4["notiz"]
    assert len(erg4["plan"]) >= 1

    # 5. Stimmung niedrig -> Spazieren Fallback
    test5 = {**test2, "stimmung": -60, "ki_antwort": ""}
    erg5 = neuer_tag(test5)
    print(f"Stimmung tief: {erg5['notiz'][:40]}... Plan: {[p['aktion'] for p in erg5['plan']]}")
    assert any(p["aktion"] == "spazieren" for p in erg5["plan"])

    # 6. Kakerlaken Warnung Level 5
    test6 = {**test2, "kakerlaken_level": 5, "ki_antwort": "think: Planen | eat: Essen"}
    erg6 = neuer_tag(test6)
    print(f"Kakerlaken Warn: {erg6['notiz']}")
    assert "Kakerlaken verdächtig" in erg6["notiz"]

    # --- Tests für MetallSortierer ---
    print("\n=== Test MetallSortierer ===")
    teile = [
        {"id": 1, "dichte_g_cm3": 2.7, "magnetisch": False, "farbe": "silber", "zeichen": "AL"},
        {"id": 2, "dichte_g_cm3": 7.85, "magnetisch": True, "farbe": "dunkelgrau", "zeichen": "FE"},
        {"id": 3, "dichte_g_cm3": 8.9, "magnetisch": False, "farbe": "rotgold", "zeichen": "CU"},
        {"id": 4, "gewicht_g": 785, "volumen_cm3": 100, "magnetisch": True, "farbe": "grau"},  # Dichte ~7.85
        {"id": 5, "magnetisch": False, "farbe": "weiss", "zeichen": "TI"},
        {"id": 6, "dichte_g_cm3": 7.9, "magnetisch": False, "farbe": "silber", "zeichen": "INOX"},
        {"id": 7, "dichte_g_cm3": 11.3, "magnetisch": False, "farbe": "blaugrau", "zeichen": "PB"},
        {"id": 8, "dichte_g_cm3": 8.5, "magnetisch": False, "farbe": "gelb", "zeichen": "MS"},  # Messing
        {"id": 9, "dichte_g_cm3": 1.74, "magnetisch": False, "farbe": "silber", "zeichen": "MG"},
        {"id": 10, "farbe": "bunt", "zeichen": "XYZ"},  # Müll/Unbekannt
    ]
    ergebnis = MetallSortierer.sortieren(teile)
    print(json.dumps(ergebnis, indent=2, ensure_ascii=False))

    assert "NE_Leichtmetall" in ergebnis["kategorien"]
    assert "Eisen_Stahl" in ergebnis["kategorien"]
    assert "NE_Schwer_Edel" in ergebnis["kategorien"]
    assert "Edelstahl" in ergebnis["kategorien"]
    assert 1 in ergebnis["kategorien"]["NE_Leichtmetall"] or "1" in ergebnis["kategorien"]["NE_Leichtmetall"]
    assert 10 in ergebnis["unsicher"] or "10" in ergebnis["unsicher"]
    print("\nAlle Tests durchgelaufen. Schuppen-Bot bereit.")