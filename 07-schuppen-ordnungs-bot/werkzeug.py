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
        "zink": 7.1, "blei": 11.34, "zinn": 7.3, "nickel": 8.9
    }

    # Erkennungsregeln: (Magnetisch, Dichte_Bereich, Farbe_Hinweis, Zeichen_Regex) -> Kategorie
    REGELN = [
        (True, (7.0, 8.0), None, r'\b(fe|eisen|stahl|guss)\b', "Ferro (Eisen/Stahl/Guss)"),
        (True, (7.5, 8.2), None, r'\b(edelstahl|v2a|v4a|nirosta)\b', "Edelstahl (magnetisch)"),
        (False, (2.5, 3.0), "silber/weiß", r'\b(al|alu|aluminium)\b', "Aluminium / Legierung"),
        (False, (1.7, 1.9), "silber/weiß", r'\b(mg|magnesium)\b', "Magnesium"),
        (False, (4.3, 4.7), "grau", r'\b(ti|titan)\b', "Titan"),
        (False, (8.8, 9.1), "rot/orange", r'\b(cu|kupfer)\b', "Kupfer"),
        (False, (8.3, 8.7), "gelb/gold", r'\b(ms|messing)\b', "Messing"),
        (False, (8.6, 9.0), "rot/braun", r'\b(bz|bronze)\b', "Bronze"),
        (False, (7.0, 7.3), "blau/weiß", r'\b(zn|zink)\b', "Zink"),
        (False, (11.0, 11.5), "blau/weiß", r'\b(pb|blei)\b', "Blei"),
        (False, (8.8, 9.0), "silber", r'\b(ni|nickel)\b', "Nickel"),
    ]

    @classmethod
    def _rate_material(cls, teil: Dict) -> str:
        """Versucht Material anhand Dichte, Magnet, Farbe, Zeichen zu erraten."""
        dichte = teil.get("dichte_g_cm3")
        magnet = teil.get("magnetisch", False)
        farbe = str(teil.get("farbe", "")).lower()
        zeichen = str(teil.get("zeichen", "")).lower()
        gewicht = teil.get("gewicht_g")
        volumen = teil.get("volumen_cm3")

        # Dichte berechnen falls fehlend aber Gewicht/Volumen da
        if dichte is None and gewicht and volumen and volumen > 0:
            try:
                dichte = float(gewicht) / float(volumen)
            except (ValueError, TypeError):
                pass

        best_score = 0
        best_kat = "Unbekannt / Mischschrott"

        for mag_req, dichte_range, farbe_hint, regex_str, kategorie in cls.REGELN:
            score = 0
            if magnet == mag_req:
                score += 3
            if dichte is not None and dichte_range:
                lo, hi = dichte_range
                if lo <= dichte <= hi:
                    score += 4
                elif lo - 0.5 <= dichte <= hi + 0.5:
                    score += 2
            if farbe_hint and farbe_hint in farbe:
                score += 1
            if regex_str and re.search(regex_str, zeichen):
                score += 5
            
            if score > best_score:
                best_score = score
                best_kat = kategorie
        
        # Fallback nur auf Dichte
        if best_score == 0 and dichte is not None:
            for name, d in cls.DICHTEN.items():
                if abs(d - dichte) < 0.3:
                    return name.capitalize() + " (vermutlich)"
        
        return best_kat if best_score > 0 else "Unbekannt / Mischschrott"

    @classmethod
    def sortieren(cls, teile: List[Dict]) -> Dict:
        """
        Hauptmethode: nimmt Liste von Teilen-Dicts.
        Gibt Dict mit Kategorien -> Liste Teile zurück.
        Alles JSON-sicher.
        """
        ergebnis: Dict[str, List[Dict]] = {}
        stats = {"gesamt": 0, "erkannte": 0, "unbekannt": 0}

        for teil in teile:
            if not isinstance(teil, dict):
                continue
            stats["gesamt"] += 1
            kategorie = cls._rate_material(teil)
            teil_kopie = _json_sicher(teil.copy())
            teil_kopie["kategorie_erkannt"] = kategorie
            
            if kategorie not in ergebnis:
                ergebnis[kategorie] = []
            ergebnis[kategorie].append(teil_kopie)
            
            if "Unbekannt" not in kategorie:
                stats["erkannte"] += 1
            else:
                stats["unbekannt"] += 1

        # Sortierung der Kategorien für stabile Ausgabe
        sortiert = {k: ergebnis[k] for k in sorted(ergebnis.keys())}
        return _json_sicher({"kategorien": sortiert, "statistik": stats})


if __name__ == "__main__":
    # --- Tests für neuer_tag ---
    print("=== Test neuer_tag ===")
    
    # 1. Notfall Kakerlaken
    daten_notfall = {"gestern": {}, "fehlschlaege": {}, "stimmung": 10, "wetter": "sonnig", "kakerlaken_level": 8}
    print("1. Notfall:", json.dumps(neuer_tag(daten_notfall), ensure_ascii=False, indent=2))

    # 2. Runde 1: Frage an KI
    daten_runde1 = {"gestern": {"think": 5, "schrott_suchen": 2}, "fehlschlaege": {"verkaufen": 1}, "stimmung": 30, "wetter": "regen", "kakerlaken_level": 2}
    print("2. Runde 1:", json.dumps(neuer_tag(daten_runde1), ensure_ascii=False, indent=2))

    # 3. Runde 2: Gute KI-Antwort
    daten_runde2_good = {**daten_runde1, "ki_antwort": "think: Sortierlogik prüfen | schrott_suchen: Alu-Haufen angehen | einlagern: Kisten beschriften"}
    print("3. Runde 2 Gut:", json.dumps(neuer_tag(daten_runde2_good), ensure_ascii=False, indent=2))

    # 4. Runde 2: Schlechte KI-Antwort -> Fallback
    daten_runde2_bad = {**daten_runde1, "ki_antwort": "bla bla"}
    print("4. Runde 2 Schlecht:", json.dumps(neuer_tag(daten_runde2_bad), ensure_ascii=False, indent=2))

    # 5. Stimmung mies -> Spazieren Fallback
    daten_mies = {"gestern": {}, "fehlschlaege": {}, "stimmung": -60, "wetter": "bewoelkt", "kakerlaken_level": 1, "ki_antwort": ""}
    print("5. Stimmung mies:", json.dumps(neuer_tag(daten_mies), ensure_ascii=False, indent=2))

    # 6. Kakerlaken Warnung Level 5
    daten_warn = {"gestern": {}, "fehlschlaege": {}, "stimmung": 50, "wetter": "sonnig", "kakerlaken_level": 5, "ki_antwort": "think: Planen | eat: Brot"}
    print("6. Kakerlaken Warnung:", json.dumps(neuer_tag(daten_warn), ensure_ascii=False, indent=2))

    print("\n=== Test MetallSortierer ===")
    test_teile = [
        {"id": 1, "gewicht_g": 270, "volumen_cm3": 100, "magnetisch": False, "farbe": "silber", "zeichen": "Alu Profil 6060"},
        {"id": 2, "gewicht_g": 785, "volumen_cm3": 100, "magnetisch": True, "farbe": "grau", "zeichen": "Stahl Träger"},
        {"id": 3, "gewicht_g": 896, "volumen_cm3": 100, "magnetisch": False, "farbe": "rot", "zeichen": "Cu Rohr"},
        {"id": 4, "gewicht_g": 850, "volumen_cm3": 100, "magnetisch": False, "farbe": "gold", "zeichen": "Messing Ventil"},
        {"id": 5, "gewicht_g": 1134, "volumen_cm3": 100, "magnetisch": False, "farbe": "blau", "zeichen": "Blei Platte"},
        {"id": 6, "gewicht_g": 450, "volumen_cm3": 100, "magnetisch": False, "farbe": "grau", "zeichen": "Ti Schraube"},
        {"id": 7, "gewicht_g": 174, "volumen_cm3": 100, "magnetisch": False, "farbe": "weiß", "zeichen": "Mg Block"},
        {"id": 8, "gewicht_g": 790, "volumen_cm3": 100, "magnetisch": True, "farbe": "silber", "zeichen": "Edelstahl V2A"},
        {"id": 9, "gewicht_g": 710, "volumen_cm3": 100, "magnetisch": False, "farbe": "blau", "zeichen": "Zink Druckguss"},
        {"id": 10, "gewicht_g": 500, "volumen_cm3": 100, "magnetisch": False, "farbe": "bunt", "zeichen": "Unbekanntes Teil"},
    ]
    ergebnis = MetallSortierer.sortieren(test_teile)
    print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
    
    # Quick Check: Sind alle 10 drin?
    assert ergebnis["statistik"]["gesamt"] == 10
    print("\nAlle Tests durchgelaufen. Schuppen bereit.")