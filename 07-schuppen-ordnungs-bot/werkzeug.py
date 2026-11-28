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
        "blei": 11.34, "zink": 7.13, "nickel": 8.9, "zinn": 7.31,
        "silber": 10.49, "gold": 19.32, "platin": 21.45
    }

    def _rate_metall_typ(self, teil: Dict) -> str:
        """Heuristik: Label, Dichte (Gewicht/Volumen), Magnetismus, Farbe."""
        label = str(teil.get("label", "")).lower()
        gewicht = float(teil.get("gewicht_g", 0))
        volumen = float(teil.get("volumen_cm3", 1))
        magnetisch = bool(teil.get("magnetisch", False))
        farbe = str(teil.get("farbe", "")).lower()

        # 1. Label-Keywords prüfen
        for name, dichte in self.DICHTEN.items():
            if name in label:
                return name

        # 2. Dichte berechnen & vergleichen
        if volumen > 0:
            dichte_ist = gewicht / volumen
            best_match = "unbekannt"
            min_diff = float('inf')
            for name, dichte_soll in self.DICHTEN.items():
                diff = abs(dichte_ist - dichte_soll)
                # Magnetismus als Filter: Eisen/Stahl/Guss sind magnetisch
                if magnetisch and name not in ("stahl", "eisen", "guss", "ferro", "nickel"):
                    diff += 2.0  # Strafe für nicht-magnetische Metalle bei Magnetismus
                if not magnetisch and name in ("stahl", "eisen", "guss", "ferro"):
                    diff += 2.0  # Strafe für magnetische Metalle ohne Magnetismus
                
                if diff < min_diff:
                    min_diff = diff
                    best_match = name
            
            # Toleranzschwellen
            if min_diff < 1.5:
                return best_match

        # 3. Farb-Hinweise als Fallback
        if "gold" in farbe or "gelb" in farbe:
            if dichte_ist > 15: return "gold"
            return "messing"
        if "rot" in farbe or "orange" in farbe:
            return "kupfer"
        if "weiss" in farbe or "silber" in farbe:
            if magnetisch: return "stahl"
            if dichte_ist < 3: return "aluminium"
            return "edelstahl"
        if "grau" in farbe or "dunkel" in farbe:
            if magnetisch: return "guss"
            return "zink"

        return "unbekannt"

    def sortieren(self, teile: List[Dict]) -> Dict:
        """Aggregiert Kategorien, zählt Stücke, summiert Gewicht."""
        kategorien = {}
        for teil in teile:
            typ = self._rate_metall_typ(teil)
            gewicht = float(teil.get("gewicht_g", 0))
            if typ not in kategorien:
                kategorien[typ] = {"anzahl": 0, "gesamt_gewicht_g": 0.0, "teile": []}
            kateg = kategorien[typ]
            kateg["anzahl"] += 1
            kateg["gesamt_gewicht_g"] += gewicht
            kateg["teile"].append(_json_sicher(teil))
        
        # Ergebnis aufbereiten
        ergebnis = {
            "kategorien": {},
            "gesamt_stueck": len(teile),
            "gesamt_gewicht_g": sum(float(t.get("gewicht_g", 0)) for t in teile)
        }
        for typ, daten in kategorien.items():
            ergebnis["kategorien"][typ] = {
                "anzahl": daten["anzahl"],
                "gesamt_gewicht_g": round(daten["gesamt_gewicht_g"], 2),
                "teile": daten["teile"]
            }
        return _json_sicher(ergebnis)


if __name__ == "__main__":
    # Selbsttest für neuer_tag
    print("=== Test neuer_tag ===")
    test_faelle = [
        {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen": 2}, "stimmung": 10, "wetter": "sonnig"},
        {"gestern": {}, "fehlschlaege": {}, "stimmung": -60, "wetter": "regen", "kakerlaken_level": 8},
        {"gestern": {"spazieren": 1}, "fehlschlaege": {}, "stimmung": 50, "wetter": "bewoelkt", "ki_antwort": "think: Sortieren | walk_to: Regal | aufheben: Schrauben"},
        {"gestern": {}, "fehlschlaege": {}, "stimmung": 0, "wetter": "nebel", "ki_antwort": "ungültiger mist"}
    ]
    for i, fall in enumerate(test_faelle):
        out = neuer_tag(fall)
        print(f"Fall {i+1}: {json.dumps(out, ensure_ascii=False)}")
        # Simuliere 2. Runde falls Frage gestellt wurde
        if "frage_an_ki" in out:
            print(f"  -> Frage an KI: {out['frage_an_ki'][:80]}...")
            fall2 = fall.copy()
            fall2["ki_antwort"] = "think: Plan machen | eat: Brot | spazieren: Kurz raus"
            out2 = neuer_tag(fall2)
            print(f"  -> Antwort: {json.dumps(out2, ensure_ascii=False)}")

    # Selbsttest für MetallSortierer
    print("\n=== Test MetallSortierer ===")
    sorter = MetallSortierer()
    test_teile = [
        {"label": "Alu-Profil 1m", "gewicht_g": 2700, "volumen_cm3": 1000, "farbe": "silber", "magnetisch": False},
        {"label": "Stahlschraube M10", "gewicht_g": 78.5, "volumen_cm3": 10, "farbe": "grau", "magnetisch": True},
        {"label": "Kupferrohr", "gewicht_g": 896, "volumen_cm3": 100, "farbe": "rot", "magnetisch": False},
        {"label": "Messing-Griff", "gewicht_g": 425, "volumen_cm3": 50, "farbe": "gold", "magnetisch": False},
        {"label": "Blei-Gewicht", "gewicht_g": 1134, "volumen_cm3": 100, "farbe": "grau", "magnetisch": False},
        {"label": "Edelstahl-Becher", "gewicht_g": 395, "volumen_cm3": 50, "farbe": "silber", "magnetisch": False},
        {"label": "Guss-Eisen Topf", "gewicht_g": 7200, "volumen_cm3": 1000, "farbe": "schwarz", "magnetisch": True},
        {"label": "Zink-Druckguss", "gewicht_g": 713, "volumen_cm3": 100, "farbe": "weiss", "magnetisch": False},
        {"label": "Nickel-Platte", "gewicht_g": 890, "volumen_cm3": 100, "farbe": "silber", "magnetisch": True},
        {"label": "Unbekanntes Teil", "gewicht_g": 500, "volumen_cm3": 200, "farbe": "bunt", "magnetisch": False},
    ]
    ergebnis = sorter.sortieren(test_teile)
    print(json.dumps(ergebnis, indent=2, ensure_ascii=False))