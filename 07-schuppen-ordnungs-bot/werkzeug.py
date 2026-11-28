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
        "blei": 11.34, "zink": 7.13, "nickel": 8.9,
        "zinn": 7.31, "gold": 19.3, "silber": 10.49
    }

    def _rate_metall_typ(self, teil: Dict) -> str:
        """Heuristik: Errate Metalltyp basierend auf Eigenschaften im Dict."""
        # Erwartete Keys: gewicht_g, volumen_cm3, magnetisch, farbe, Notizen
        gewicht = teil.get("gewicht_g")
        volumen = teil.get("volumen_cm3")
        magnetisch = teil.get("magnetisch", False)
        farbe = str(teil.get("farbe", "")).lower()
        hinweis = str(teil.get("hinweis", "")).lower()

        # Dichte berechnen, falls möglich
        dichte = None
        if isinstance(gewicht, (int, float)) and isinstance(volumen, (int, float)) and volumen > 0:
            dichte = gewicht / volumen

        # 1. Magnetisch -> Eisen/Stahl/Guss (außer Edelstahl oft nicht magnetisch)
        if magnetisch:
            if "rost" in hinweis or "rostig" in farbe:
                return "eisen"
            if dichte and dichte > 7.5:
                return "stahl"
            return "ferro"

        # 2. Farbe & Hinweise (Nicht-Magnetisch)
        if "kupfer" in farbe or "rotgold" in farbe or "kupfer" in hinweis:
            return "kupfer"
        if "gold" in farbe and dichte and dichte > 15:
            return "gold"
        if "silber" in farbe or "weiss" in farbe:
            if dichte and dichte > 10:
                return "silber"
            if dichte and 8.0 < dichte < 9.5:
                return "nickel"
            if "messing" in hinweis or "gelb" in farbe:
                return "messing"
            if "aluminium" in hinweis or "alu" in hinweis:
                return "aluminium"
            # Default hell/leicht
            if dichte and dichte < 3.5:
                return "aluminium"
            if dichte and dichte < 5.0:
                return "titan"

        # 3. Dichte-Schätzung als Fallback
        if dichte:
            # Naheliegendste Dichte suchen
            beste_typ = "unbekannt"
            min_diff = float('inf')
            for typ, d in self.DICHTEN.items():
                diff = abs(d - dichte)
                if diff < min_diff:
                    min_diff = diff
                    beste_typ = typ
            # Toleranz: 15% Abweichung
            if min_diff / self.DICHTEN[beste_typ] < 0.15:
                return beste_typ

        return "unbekannt"

    def sortieren(self, teile: List[Dict]) -> Dict:
        """Sortiert Liste von Teilen in Kategorien. Gibt JSON-sicheres Dict zurück."""
        kategorien = {}
        for i, teil in enumerate(teile):
            if not isinstance(teil, dict):
                continue
            typ = self._rate_metall_typ(teil)
            if typ not in kategorien:
                kategorien[typ] = []
            # Originalteil kopieren und Typ hinzufügen
            t = teil.copy()
            t["erkanntes_metall"] = typ
            t["index"] = i
            kategorien[typ].append(_json_sicher(t))

        # Zusammenfassung bauen
        ergebnis = {
            "kategorien": _json_sicher(kategorien),
            "anzahl_gesamt": len(teile),
            "anzahl_kategorien": len(kategorien),
            "unsortiert": len(kategorien.get("unbekannt", []))
        }
        return _json_sicher(ergebnis)


if __name__ == "__main__":
    # Selbsttest für neuer_tag
    print("=== Test neuer_tag ===")
    # Test 1: Notfall Kakerlaken
    daten_notfall = {"gestern": {}, "fehlschlaege": {}, "stimmung": 10, "wetter": "regen", "kakerlaken_level": 8}
    erg = neuer_tag(daten_notfall)
    print(f"Notfall: {json.dumps(erg, ensure_ascii=False)}")
    assert erg["plan"][0]["aktion"] == "walk_to"

    # Test 2: Runde 1 (KI fragen)
    daten_r1 = {"gestern": {"think": 2, "eat": 1}, "fehlschlaege": {"schrott_suchen": 1}, "stimmung": 30, "wetter": "sonnig", "kakerlaken_level": 1}
    erg = neuer_tag(daten_r1)
    print(f"Runde 1: {json.dumps(erg, ensure_ascii=False)}")
    assert "frage_an_ki" in erg

    # Test 3: Runde 2 mit guter KI-Antwort
    daten_r2 = {**daten_r1, "ki_antwort": "think: Sortierlogik prüfen | schrott_suchen: Kabelberge angehen | einlagern: Kupfer separat"}
    erg = neuer_tag(daten_r2)
    print(f"Runde 2 OK: {json.dumps(erg, ensure_ascii=False)}")
    assert len(erg["plan"]) == 3
    assert erg["plan"][0]["aktion"] == "think"

    # Test 4: Runde 2 mit Müll-Antwort -> Fallback
    daten_r2_muell = {**daten_r1, "ki_antwort": "blabla"}
    erg = neuer_tag(daten_r2_muell)
    print(f"Runde 2 Müll: {json.dumps(erg, ensure_ascii=False)}")
    assert "Fallback" in erg["notiz"]
    assert len(erg["plan"]) > 0

    # Test 5: Stimmung mies -> Spazieren Fallback
    daten_mies = {**daten_r1, "stimmung": -60, "ki_antwort": ""}
    erg = neuer_tag(daten_mies)
    print(f"Stimmung mies: {json.dumps(erg, ensure_ascii=False)}")
    assert erg["plan"][0]["aktion"] == "spazieren"

    print("\n=== Test MetallSortierer ===")
    sorter = MetallSortierer()
    test_teile = [
        {"gewicht_g": 785, "volumen_cm3": 100, "magnetisch": True, "farbe": "grau", "hinweis": "Stab"},
        {"gewicht_g": 270, "volumen_cm3": 100, "magnetisch": False, "farbe": "silber", "hinweis": "Alu-Profil"},
        {"gewicht_g": 896, "volumen_cm3": 100, "magnetisch": False, "farbe": "rotgold", "hinweis": "Kabel"},
        {"gewicht_g": 100, "volumen_cm3": 50, "magnetisch": False, "farbe": "gelb", "hinweis": "Messing-Schraube"},
        {"gewicht_g": 50, "volumen_cm3": 50, "magnetisch": False, "farbe": "weiss", "hinweis": "Unbekanntes Leichtmetall"},
        {"gewicht_g": 1134, "volumen_cm3": 100, "magnetisch": False, "farbe": "blaugrau", "hinweis": "Blei-Barren"},
        {"gewicht_g": 785, "volumen_cm3": 100, "magnetisch": True, "farbe": "braun", "hinweis": "Rostiges Rohr"},
        {"gewicht_g": 100, "volumen_cm3": 10, "magnetisch": False, "farbe": "gelb", "hinweis": "Gold? Zu schwer für Volumen"},
        {"gewicht_g": 0, "volumen_cm3": 0, "magnetisch": False, "farbe": "", "hinweis": "Kaputte Daten"},
        {"gewicht_g": 450, "volumen_cm3": 100, "magnetisch": False, "farbe": "grau", "hinweis": "Titan? Dichte 4.5"},
    ]
    ergebnis = sorter.sortieren(test_teile)
    print(json.dumps(ergebnis, indent=2, ensure_ascii=False))
    assert ergebnis["anzahl_gesamt"] == 10
    assert "stahl" in ergebnis["kategorien"] or "ferro" in ergebnis["kategorien"] or "eisen" in ergebnis["kategorien"]
    assert "aluminium" in ergebnis["kategorien"]
    assert "kupfer" in ergebnis["kategorien"]
    print("\nAlle Tests durchgelaufen. Schuppen-Logik steht.")