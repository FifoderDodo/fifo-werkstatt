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
        "zink": 7.13, "zinial": 6.7,
        "blei": 11.34,
        "nickel": 8.9,
        "gold": 19.3, "silber": 10.5
    }

    # Heuristiken: Magnetisch, Farbe, typische Zeichen/Stempel
    REGELN = {
        "aluminium": {"magnetisch": False, "farbe": ["silber", "grau", "weiss"], "zeichen": ["al", "alu", "6060", "6063", "7075"]},
        "magnesium": {"magnetisch": False, "farbe": ["grau", "silber"], "zeichen": ["mg", "az31", "az91"]},
        "titan": {"magnetisch": False, "farbe": ["grau", "dunkelgrau"], "zeichen": ["ti", "grade", "gr2", "gr5"]},
        "stahl": {"magnetisch": True, "farbe": ["grau", "schwarz", "blau", "rot"], "zeichen": ["st", "st37", "s235", "c45"]},
        "guss": {"magnetisch": True, "farbe": ["grau", "schwarz"], "zeichen": ["gg", "ggg", "guss"]},
        "edelstahl": {"magnetisch": False, "farbe": ["silber", "glänzend", "grau"], "zeichen": ["v2a", "v4a", "1.4301", "1.4404", "304", "316", "inox"]},
        "kupfer": {"magnetisch": False, "farbe": ["rot", "orange", "braun", "grün"], "zeichen": ["cu", "cu-ets"]},
        "messing": {"magnetisch": False, "farbe": ["gelb", "gold", "braun"], "zeichen": ["ms", "messing", "cuzn"]},
        "bronze": {"magnetisch": False, "farbe": ["braun", "rotbraun", "grün"], "zeichen": ["bz", "bronze", "cusn"]},
        "zink": {"magnetisch": False, "farbe": ["blaugrau", "weiss", "grau"], "zeichen": ["zn", "zink", "zinial"]},
        "blei": {"magnetisch": False, "farbe": ["blaugrau", "weiss", "dunkelgrau"], "zeichen": ["pb", "blei"]},
        "nickel": {"magnetisch": True, "farbe": ["silber", "weiss", "gelblich"], "zeichen": ["ni", "nickel"]},
    }

    @classmethod
    def _rate_material(cls, teil: Dict) -> Dict[str, float]:
        """Bewertet ein Teil gegen alle bekannten Materialien, gibt Scores 0-1 zurück."""
        scores = {}
        dichte = teil.get("dichte_g_cm3")
        magnet = teil.get("magnetisch")
        farbe = str(teil.get("farbe", "")).lower()
        text = str(teil.get("text", "")).lower()  # Stempel, Aufdruck

        for mat, props in cls.REGELN.items():
            score = 0.0
            max_score = 0.0

            # 1. Dichte (stärkstes Signal, falls vorhanden)
            if dichte is not None and isinstance(dichte, (int, float)):
                ziel = cls.DICHTEN.get(mat, 0)
                if ziel > 0:
                    abw = abs(dichte - ziel) / ziel
                    score += max(0.0, 1.0 - abw * 2) * 0.5  # Gewichtung 50%
                max_score += 0.5

            # 2. Magnetismus (Ausschlusskriterium oft)
            if magnet is not None and isinstance(magnet, bool):
                if magnet == props["magnetisch"]:
                    score += 0.25
                else:
                    score -= 0.5  # Hartes Mismatch
                max_score += 0.25

            # 3. Farbe (weich)
            if farbe:
                if any(f in farbe for f in props["farbe"]):
                    score += 0.15
                max_score += 0.15

            # 4. Zeichen/Stempel (stark, wenn vorhanden)
            if text:
                if any(z in text for z in props["zeichen"]):
                    score += 0.3
                max_score += 0.3

            # Normalisieren
            if max_score > 0:
                scores[mat] = max(0.0, score / max_score)
            else:
                scores[mat] = 0.0

        return scores

    @classmethod
    def sortieren(cls, teile: List[Dict]) -> Dict:
        """Hauptmethode: Nimmt Liste von Teilen, gibt sortierte Kategorien zurück."""
        kategorien = {mat: [] for mat in cls.REGELN.keys()}
        kategorien["unbekannt"] = []
        kategorien["gemischt"] = []

        for i, teil in enumerate(teile):
            if not isinstance(teil, dict):
                kategorien["unbekannt"].append({"index": i, "fehler": "Kein Dict"})
                continue

            scores = cls._rate_material(teil)
            if not scores:
                kategorien["unbekannt"].append({"index": i, "teil": teil})
                continue

            # Bestes Material finden
            bestes = max(scores, key=scores.get)
            best_score = scores[bestes]

            # Zweitbestes für 'gemischt' Erkennung
            sorted_scores = sorted(scores.values(), reverse=True)
            zweit_best = sorted_scores[1] if len(sorted_scores) > 1 else 0.0

            ergebnis = {"index": i, "teil": teil, "scores": scores, "vermutung": bestes, "sicherheit": round(best_score, 2)}

            if best_score >= 0.6 and (best_score - zweit_best) > 0.15:
                kategorien[bestes].append(ergebnis)
            elif best_score >= 0.4:
                kategorien["gemischt"].append(ergebnis)
            else:
                kategorien["unbekannt"].append(ergebnis)

        # Aufräumen: Leere Kategorien entfernen, Ausgabe JSON-sicher
        ergebnis = {k: v for k, v in kategorien.items() if v}
        return _json_sicher(ergebnis)


if __name__ == "__main__":
    print("=== Test neuer_tag ===")
    # Test 1: Notfall Kakerlaken
    daten_notfall = {"gestern": {}, "fehlschlaege": {}, "stimmung": 50, "wetter": "sonnig", "kakerlaken_level": 8}
    print("Notfall:", json.dumps(neuer_tag(daten_notfall), ensure_ascii=False, indent=2))

    # Test 2: Runde 1 (keine ki_antwort)
    daten_r1 = {"gestern": {"think": 2, "eat": 1}, "fehlschlaege": {"schrott_suchen": 1}, "stimmung": 10, "wetter": "regen", "kakerlaken_level": 2}
    print("Runde 1:", json.dumps(neuer_tag(daten_r1), ensure_ascii=False, indent=2))

    # Test 3: Runde 2 mit guter KI-Antwort
    daten_r2_good = {**daten_r1, "ki_antwort": "think: Kupfer sortieren | walk_to: Regal C | schrott_suchen: Kabelreste"}
    print("Runde 2 Gut:", json.dumps(neuer_tag(daten_r2_good), ensure_ascii=False, indent=2))

    # Test 4: Runde 2 mit Müll-Antwort -> Fallback
    daten_r2_bad = {**daten_r1, "ki_antwort": "blabla"}
    print("Runde 2 Schlecht:", json.dumps(neuer_tag(daten_r2_bad), ensure_ascii=False, indent=2))

    # Test 5: Kakerlaken Warnung Level 5
    daten_warn = {**daten_r1, "kakerlaken_level": 5, "ki_antwort": "think: Sortieren | eat: Brot"}
    print("Warnung Level 5:", json.dumps(neuer_tag(daten_warn), ensure_ascii=False, indent=2))

    print("\n=== Test MetallSortierer ===")
    test_teile = [
        {"dichte_g_cm3": 2.71, "magnetisch": False, "farbe": "silber", "text": "AL 6063"},
        {"dichte_g_cm3": 7.85, "magnetisch": True, "farbe": "grau", "text": "ST37"},
        {"dichte_g_cm3": 8.9, "magnetisch": False, "farbe": "rot", "text": "CU-ETP"},
        {"dichte_g_cm3": 8.5, "magnetisch": False, "farbe": "gelb", "text": "MS 58"},
        {"dichte_g_cm3": 7.9, "magnetisch": False, "farbe": "glänzend", "text": "1.4301"},
        {"dichte_g_cm3": 1.74, "magnetisch": False, "farbe": "grau", "text": "AZ91"},
        {"dichte_g_cm3": 4.5, "magnetisch": False, "farbe": "dunkelgrau", "text": "GR5"},
        {"dichte_g_cm3": 7.2, "magnetisch": True, "farbe": "schwarz", "text": "GGG40"},
        {"dichte_g_cm3": 11.3, "magnetisch": False, "farbe": "blaugrau", "text": "PB"},
        {"dichte_g_cm3": 3.0, "magnetisch": True, "farbe": "bunt", "text": "Müll"},  # Unbekannt / Gemischt
    ]
    ergebnis = MetallSortierer.sortieren(test_teile)
    print(json.dumps(ergebnis, ensure_ascii=False, indent=2))