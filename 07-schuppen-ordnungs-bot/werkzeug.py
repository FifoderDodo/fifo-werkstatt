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
        "zink": 7.13, "zinklegierung": 7.0,
        "blei": 11.34,
        "nickel": 8.91,
        "gold": 19.3, "silber": 10.5,
    }

    def __init__(self, teile: List[Dict]):
        self.teile = teile if isinstance(teile, list) else []
        self.ergebnisse = []

    def magnet_test(self, teil: Dict) -> bool:
        """Simuliert Magnet-Test: Ferro-magnetisch (Stahl/Eisen/Guss) -> True."""
        material = str(teil.get("material", "")).lower()
        return any(k in material for k in ["stahl", "eisen", "guss", "ferro", "nickel"])

    def funken_test(self, teil: Dict) -> str:
        """Simuliert Funkenbild: 'lang' (Stahl), 'kurz' (Guss), 'keine' (NE-Metalle)."""
        material = str(teil.get("material", "")).lower()
        if "guss" in material:
            return "kurz"
        if any(k in material for k in ["stahl", "eisen", "ferro"]):
            return "lang"
        return "keine"

    def dichte_test(self, teil: Dict) -> float:
        """Berechnet Dichte aus Gewicht (g) / Volumen (cm3). Fallback auf Schätzung."""
        try:
            gewicht = float(teil.get("gewicht_g", 0))
            vol = float(teil.get("volumen_cm3", 0))
            if gewicht > 0 and vol > 0:
                return round(gewicht / vol, 2)
        except (ValueError, TypeError):
            pass
        # Fallback: grob nach Material-String schätzen
        material = str(teil.get("material", "")).lower()
        for k, v in self.DICHTEN.items():
            if k in material:
                return v
        return 0.0

    def _dichte_match(self, gemessen: float, referenz: float, toleranz: float = 0.08) -> bool:
        """Prüft ob gemessene Dichte in Toleranz (Default 8%) zur Referenz liegt."""
        if referenz <= 0 or gemessen <= 0:
            return False
        return abs(gemessen - referenz) / referenz <= toleranz

    def material_pruefung(self, teil: Dict) -> Dict:
        """Führt Tests durch und bestimmt wahrscheinlichstes Material."""
        magnetisch = self.magnet_test(teil)
        funken = self.funken_test(teil)
        dichte = self.dichte_test(teil)

        kandidaten = []
        for name, ref_dichte in self.DICHTEN.items():
            score = 0
            # Magnet-Check
            ist_ferro = name in ["stahl", "eisen", "guss", "ferro", "nickel", "edelstahl"]
            if magnetisch == ist_ferro:
                score += 2
            # Funken-Check
            if funken == "lang" and name in ["stahl", "eisen", "ferro"]:
                score += 2
            elif funken == "kurz" and name == "guss":
                score += 2
            elif funken == "keine" and name not in ["stahl", "eisen", "guss", "ferro"]:
                score += 1
            # Dichte-Check
            if self._dichte_match(dichte, ref_dichte):
                score += 3
            elif ref_dichte > 0 and dichte > 0:
                # Teilpunkte für Nähe
                abw = abs(dichte - ref_dichte) / ref_dichte
                if abw < 0.15:
                    score += 1
            if score > 0:
                kandidaten.append((name, score, ref_dichte))

        # Besten Kandidaten wählen
        if kandidaten:
            kandidaten.sort(key=lambda x: (-x[1], abs(x[2] - dichte) if dichte > 0 else 99))
            best_name, best_score, _ = kandidaten[0]
            kategorie = "NE-Metall" if best_name not in ["stahl", "eisen", "guss", "ferro", "edelstahl"] else "Stahl/Eisen"
            if best_name in ["gold", "silber"]:
                kategorie = "Edelmetall"
        else:
            best_name = "unbekannt"
            kategorie = "Mischschrott"
            best_score = 0

        return {
            "teil_id": teil.get("id", "?"),
            "vermutung": best_name,
            "kategorie": kategorie,
            "sicherheit": min(best_score, 7),  # Max 7 Punkte
            "details": {
                "magnetisch": magnetisch,
                "funken": funken,
                "dichte_gemessen": dichte
            }
        }

    def sortiere(self) -> List[Dict]:
        """Sortiert alle Teile und speichert Ergebnisse."""
        self.ergebnisse = [self.material_pruefung(t) for t in self.teile]
        return self.ergebnisse

    def get_ergebnis(self) -> Dict:
        """Liefert Zusammenfassung als JSON-sicheres Dict."""
        if not self.ergebnisse:
            self.sortiere()
        stats = {}
        for e in self.ergebnisse:
            kat = e["kategorie"]
            stats[kat] = stats.get(kat, 0) + 1
        return _json_sicher({
            "anzahl_teile": len(self.teile),
            "kategorien": stats,
            "details": self.ergebnisse
        })


# --- Test-Block ---
if __name__ == "__main__":
    print("=== Test neuer_tag (Runde 1: KI fragen) ===")
    eingabe1 = {"gestern": {"think": 2, "eat": 1}, "fehlschlaege": {},"stimmung": 10, "wetter": "sonnig", "kakerlaken_level": 2}
    out1 = neuer_tag(eingabe1)
    print(json.dumps(out1, ensure_ascii=False, indent=2))

    print("\n=== Test neuer_tag (Runde 2: KI antwortet) ===")
    eingabe2 = {**eingabe1, "ki_antwort": "think: Aluminium-Haufen prüfen | schrott_suchen: Kiste 3 leer räumen | eat: Brotzeit"}
    out2 = neuer_tag(eingabe2)
    print(json.dumps(out2, ensure_ascii=False, indent=2))

    print("\n=== Test neuer_tag (Kakerlaken-Alarm Level 7) ===")
    eingabe3 = {"gestern": {}, "fehlschlaege": {},"stimmung": -10, "wetter": "regen", "kakerlaken_level": 7}
    out3 = neuer_tag(eingabe3)
    print(json.dumps(out3, ensure_ascii=False, indent=2))

    print("\n=== Test MetallSortierer ===")
    test_teile = [
        {"id": "A1", "gewicht_g": 270, "volumen_cm3": 100, "material": "Aluminium-Profil"},
        {"id": "B2", "gewicht_g": 785, "volumen_cm3": 100, "material": "Stahl-Stange"},
        {"id": "C3", "gewicht_g": 896, "volumen_cm3": 100, "material": "Kupfer-Rohr"},
        {"id": "D4", "gewicht_g": 500, "volumen_cm3": 70, "material": "Unbekanntes Metall"},
        {"id": "E5", "gewicht_g": 720, "volumen_cm3": 100, "material": "Grauguss-Flansch"},
    ]
    sorter = MetallSortierer(test_teile)
    ergebnis = sorter.get_ergebnis()
    print(json.dumps(ergebnis, ensure_ascii=False, indent=2))

    print("\n=== Test Pfadvalidierung ===")
    try:
        print("OK:", validiere_dateipfad("daten/schrott.json"))
    except ValueError as e:
        print("Fehler:", e)
    try:
        validiere_dateipfad("../../etc/passwd")
    except ValueError as e:
        print("Erwarteter Fehler:", e)