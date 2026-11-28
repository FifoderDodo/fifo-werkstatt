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
        "zink": 7.1, "zinklegierung": 6.8,
        "blei": 11.34,
        "zinn": 7.31,
        "nickel": 8.91,
        "gold": 19.32,
        "silber": 10.49,
    }

    def _rate_metall_typ(self, teil: Dict) -> str:
        """Heuristik: Bestimme Metall-Typ aus Teil-Dict."""
        # 1. Dichte berechnen oder lesen
        dichte = None
        if "dichte" in teil and isinstance(teil["dichte"], (int, float)):
            dichte = float(teil["dichte"])
        elif "gewicht" in teil and "volumen" in teil:
            try:
                g = float(teil["gewicht"])
                v = float(teil["volumen"])
                if v > 0:
                    dichte = g / v
            except (ValueError, TypeError):
                pass

        # 2. Magnetismus
        magnetisch = bool(teil.get("magnetisch", False))

        # 3. Farbe / Optik
        farbe = str(teil.get("farbe", "")).lower()

        # 4. Markierungen (Stempel, Aufdruck)
        markierung = str(teil.get("markierung", "")).lower()

        # Entscheidungshilfe via Markierung (stärkstes Signal)
        if re.search(r'\b(al|alu|aluminium)\b', markierung):
            return "aluminium"
        if re.search(r'\b(cu|kupfer)\b', markierung):
            return "kupfer"
        if re.search(r'\b(ms|messing)\b', markierung):
            return "messing"
        if re.search(r'\b(fe|st|stahl|eisen)\b', markierung):
            return "stahl"
        if re.search(r'\b(ss|edelstahl|v2a|v4a)\b', markierung):
            return "edelstahl"
        if re.search(r'\b(pb|blei)\b', markierung):
            return "blei"
        if re.search(r'\b(zn|zink)\b', markierung):
            return "zink"
        if re.search(r'\b(ti|titan)\b', markierung):
            return "titan"
        if re.search(r'\b(mg|magnesium)\b', markierung):
            return "magnesium"

        # Entscheidung via Dichte (wenn vorhanden)
        if dichte is not None:
            # Nächste bekannte Dichte suchen
            beste_typ = "unbekannt"
            min_diff = float('inf')
            for typ, d in self.DICHTEN.items():
                diff = abs(d - dichte)
                # Magnetismus als Tiebreaker für ferro vs non-ferro bei ähnlicher Dichte
                if magnetisch and typ in ["stahl", "eisen", "guss", "ferro", "edelstahl"]:
                    diff *= 0.5  # Bevorzuge magnetische Typen
                elif not magnetisch and typ not in ["stahl", "eisen", "guss", "ferro", "edelstahl", "nickel"]:
                    diff *= 0.5  # Bevorzuge nicht-magnetische Typen
                if diff < min_diff:
                    min_diff = diff
                    beste_typ = typ
            # Toleranz: wenn Diff sehr groß, eher unbekannt
            if min_diff < 1.5:  # g/cm³ Toleranz
                return beste_typ

        # Heuristik ohne Dichte
        if magnetisch:
            if "rost" in farbe or "braun" in farbe:
                return "eisen"
            if "grau" in farbe or "dunkel" in farbe:
                return "stahl"
            return "ferro"  # Generisch magnetisch
        else:
            # Nicht magnetisch
            if "kupfer" in farbe or "orange" in farbe or "rot" in farbe:
                if "gelb" in farbe or "gold" in farbe:
                    return "messing"
                return "kupfer"
            if "gelb" in farbe or "gold" in farbe:
                return "messing"
            if "weiß" in farbe or "silber" in farbe or "hell" in farbe or "grau" in farbe:
                # Alu vs Mg vs Zink vs Edelstahl (nicht magnetisch)
                # Ohne Dichte raten wir Alu als häufigsten Schrott
                return "aluminium"
            if "blau" in farbe or "violett" in farbe:
                return "titan"  # Titanoxid-Schicht oft bläulich

        return "unbekannt"

    def sortieren(self, teile: List[Dict]) -> Dict:
        """Sortiert Liste von Teilen in Kategorien, liefert Zusammenfassung."""
        kategorien = {}
        for i, teil in enumerate(teile):
            if not isinstance(teil, dict):
                continue
            typ = self._rate_metall_typ(teil)
            gewicht = 0.0
            try:
                gewicht = float(teil.get("gewicht", 0.0))
            except (ValueError, TypeError):
                pass

            if typ not in kategorien:
                kategorien[typ] = {"anzahl": 0, "gesamt_gewicht": 0.0, "teile": []}
            kat = kategorien[typ]
            kat["anzahl"] += 1
            kat["gesamt_gewicht"] += gewicht
            # Nur Referenz/ID speichern, nicht ganzes Objekt (Platz)
            teil_info = {
                "index": i,
                "gewicht": gewicht,
                "magnetisch": bool(teil.get("magnetisch", False)),
                "farbe": str(teil.get("farbe", ""))[:20]
            }
            kat["teile"].append(teil_info)

        # Ergebnis JSON-sicher machen
        ergebnis = {
            "kategorien": {},
            "gesamt_anzahl": len(teile),
            "gesamt_gewicht": sum(float(t.get("gewicht", 0)) for t in teile if isinstance(t, dict))
        }
        for typ, daten in kategorien.items():
            ergebnis["kategorien"][typ] = {
                "anzahl": daten["anzahl"],
                "gesamt_gewicht": round(daten["gesamt_gewicht"], 2),
                "teile": daten["teile"]
            }
        return _json_sicher(ergebnis)


if __name__ == "__main__":
    # Selbsttest für neuer_tag (Runden-Logik)
    print("=== Test neuer_tag ===")
    # Test 1: Runde 1 -> fragt KI
    daten1 = {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen": 2}, "stimmung": 10, "wetter": "sonnig", "kakerlaken_level": 1}
    erg1 = neuer_tag(daten1)
    print(f"Runde 1 (ohne ki_antwort): {json.dumps(erg1, ensure_ascii=False)}")
    assert "frage_an_ki" in erg1

    # Test 2: Runde 2 -> KI antwortet gut
    daten2 = {**daten1, "ki_antwort": "think: Sortierlogik prüfen | schrott_suchen: Alu-Haufen angehen | eat: Apfel"}
    erg2 = neuer_tag(daten2)
    print(f"Runde 2 (mit Plan): {json.dumps(erg2, ensure_ascii=False)}")
    assert "plan" in erg2 and len(erg2["plan"]) == 3
    assert erg2["plan"][0]["aktion"] == "think"

    # Test 3: Runde 2 -> KI antwortet Müll -> Fallback
    daten3 = {**daten1, "ki_antwort": "blabla"}
    erg3 = neuer_tag(daten3)
    print(f"Runde 2 (Müll -> Fallback): {json.dumps(erg3, ensure_ascii=False)}")
    assert "plan" in erg3 and len(erg3["plan"]) > 0
    assert erg3["plan"][0]["aktion"] in ["think", "drink", "spazieren"]

    # Test 4: Notfall Kakerlaken
    daten4 = {"gestern": {}, "fehlschlaege": {}, "stimmung": 50, "wetter": "regen", "kakerlaken_level": 8}
    erg4 = neuer_tag(daten4)
    print(f"Notfall Kakerlaken: {json.dumps(erg4, ensure_ascii=False)}")
    assert erg4["plan"][0]["aktion"] == "walk_to"
    assert "Giftschrank" in erg4["plan"][0]["text"]

    # Test 5: Stimmung sehr schlecht
    daten5 = {"gestern": {}, "fehlschlaege": {}, "stimmung": -80, "wetter": "bewoelkt", "kakerlaken_level": 0, "ki_antwort": ""}
    erg5 = neuer_tag(daten5)
    print(f"Schlechte Stimmung: {json.dumps(erg5, ensure_ascii=False)}")
    assert erg5["plan"][0]["aktion"] == "spazieren"

    print("\n=== Test MetallSortierer ===")
    sorter = MetallSortierer()
    test_teile = [
        {"gewicht": 100, "volumen": 37, "magnetisch": False, "farbe": "silber", "markierung": "AL 6063"},  # Alu ~2.7
        {"gewicht": 500, "volumen": 64, "magnetisch": True, "farbe": "dunkelgrau", "markierung": "ST 37"},   # Stahl ~7.8
        {"gewicht": 200, "volumen": 22, "magnetisch": False, "farbe": "kupfer", "markierung": ""},        # Kupfer ~8.9
        {"gewicht": 150, "volumen": 17, "magnetisch": False, "farbe": "gelblich", "markierung": "MS 58"},   # Messing ~8.5
        {"gewicht": 50, "volumen": 29, "magnetisch": False, "farbe": "weiß", "markierung": ""},           # Alu/Mg Verdacht
        {"gewicht": 1000, "volumen": 127, "magnetisch": True, "farbe": "rostbraun", "markierung": ""},    # Eisen/Guss
        {"gewicht": 10, "volumen": 1, "magnetisch": False, "farbe": "gold", "markierung": "AU 999"},      # Gold
        {"gewicht": 300, "magnetisch": False, "farbe": "silber", "markierung": "TI"},                     # Titan (kein Volumen)
        {"gewicht": 400, "magnetisch": True, "farbe": "grau", "markierung": "V2A"},                       # Edelstahl
        {"gewicht": 50, "magnetisch": False, "farbe": "blau", "markierung": ""},                         # Unbekannt/Blau
    ]
    ergebnis = sorter.sortieren(test_teile)
    print(json.dumps(ergebnis, indent=2, ensure_ascii=False))
    
    # Prüfungen
    assert ergebnis["gesamt_anzahl"] == 10
    cats = ergebnis["kategorien"]
    assert "aluminium" in cats
    assert "stahl" in cats or "ferro" in cats or "eisen" in cats
    assert "kupfer" in cats
    assert "messing" in cats
    assert "gold" in cats
    assert "titan" in cats
    assert "edelstahl" in cats
    print("\nAlle Tests bestanden. Werkzeug scharf.")