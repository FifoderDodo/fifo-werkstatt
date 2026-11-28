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
        "unknown": 7.8  # Fallback: Eisen/Stahl
    }
    TOLERANZ = 0.08  # 8% Toleranz bei Dichte-Abgleich

    def __init__(self):
        self.ergebnis = {"kategorien": {}, "unsortiert": [], "fehler": []}

    def gewicht_schaetzen(self, teil: Dict) -> float:
        """Schätzt Gewicht in Gramm aus Volumen (cm³) und Material-Dichte."""
        try:
            vol = float(teil.get("volumen_cm3", 0))
            mat = str(teil.get("material_vermutung", "unknown")).lower()
            dichte = self.DICHTEN.get(mat, self.DICHTEN["unknown"])
            return round(vol * dichte, 1)
        except Exception:
            return 0.0

    def kategorie_bestimmen(self, teil: Dict, dichte: float) -> str:
        """Ordnet Teil Kategorie zu basierend auf gemessener/geschätzter Dichte."""
        if dichte <= 0:
            return "unbekannt"
        # Näherste bekannte Dichte suchen
        beste_kat = "unbekannt"
        min_diff = float('inf')
        for kat, d in self.DICHTEN.items():
            if d <= 0:
                continue
            diff = abs(dichte - d) / d
            if diff < min_diff:
                min_diff = diff
                beste_kat = kat
        if min_diff <= self.TOLERANZ:
            # Hauptkategorie zusammenfassen
            if beste_kat in ["aluminium", "aluminiumlegierung", "magnesium", "titan"]:
                return "leichtmetall"
            if beste_kat in ["stahl", "eisen", "guss", "ferro", "edelstahl"]:
                return "ferro"
            if beste_kat in ["kupfer", "messing", "bronze"]:
                return "kupfer_legierung"
            if beste_kat in ["blei", "zink", "nickel"]:
                return "schwer_metall"
            return beste_kat
        return "unbekannt"

    def sortieren(self, teile: List[Dict]) -> Dict:
        """Haupt-Einstieg: Liste von Teilen verarbeiten."""
        self.ergebnis = {"kategorien": {}, "unsortiert": [], "fehler": []}
        for i, teil in enumerate(teile):
            try:
                if not isinstance(teil, dict):
                    self.ergebnis["fehler"].append(f"Index {i}: Kein Dict")
                    continue
                # Dichte bestimmen: gemessen > geschätzt
                dichte = float(teil.get("dichte_g_cm3", 0))
                if dichte <= 0:
                    gewicht = self.gewicht_schaetzen(teil)
                    vol = float(teil.get("volumen_cm3", 1))
                    dichte = round(gewicht / vol, 2) if vol > 0 else 0
                kat = self.kategorie_bestimmen(teil, dichte)
                eintrag = {
                    "id": teil.get("id", f"teil_{i}"),
                    "dichte": dichte,
                    "gewicht_g": self.gewicht_schaetzen(teil) if dichte > 0 else teil.get("gewicht_g", 0),
                    "info": teil.get("beschreibung", "")[:100]
                }
                if kat not in self.ergebnis["kategorien"]:
                    self.ergebnis["kategorien"][kat] = []
                self.ergebnis["kategorien"][kat].append(eintrag)
            except Exception as e:
                self.ergebnis["fehler"].append(f"Index {i}: {e}")
        # JSON-sicher machen
        return _json_sicher(self.ergebnis)


if __name__ == "__main__":
    # Selbsttest für neuer_tag
    print("=== Test neuer_tag ===")
    # Test 1: KI wird gefragt
    daten1 = {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen": 2}, "stimmung": 10, "wetter": "sonnig"}
    erg1 = neuer_tag(daten1)
    print(f"1. Frag-Runde: {json.dumps(erg1, ensure_ascii=False)}")
    
    # Test 2: KI antwortet brav
    daten2 = {**daten1, "ki_antwort": "think: Sortierlogik prüfen | schrott_suchen: Kabel finden | einlagern: Kisten beschriften"}
    erg2 = neuer_tag(daten2)
    print(f"2. Antwort-Runde: {json.dumps(erg2, ensure_ascii=False)}")

    # Test 3: Kakerlaken-Alarm
    daten3 = {"gestern": {}, "fehlschlaege": {}, "stimmung": 50, "wetter": "regen", "kakerlaken_level": 8}
    erg3 = neuer_tag(daten3)
    print(f"3. Kakerlaken: {json.dumps(erg3, ensure_ascii=False)}")

    # Test 4: Fallback (leere KI-Antwort)
    daten4 = {"gestern": {}, "fehlschlaege": {}, "stimmung": -60, "wetter": "nebel", "ki_antwort": ""}
    erg4 = neuer_tag(daten4)
    print(f"4. Fallback: {json.dumps(erg4, ensure_ascii=False)}")

    # Selbsttest für MetallSortierer
    print("\n=== Test MetallSortierer ===")
    sorter = MetallSortierer()
    test_teile = [
        {"id": "A1", "material_vermutung": "aluminium", "volumen_cm3": 100, "beschreibung": "Leichtes Profil"},
        {"id": "B2", "material_vermutung": "kupfer", "volumen_cm3": 50, "beschreibung": "Dicker Draht"},
        {"id": "C3", "dichte_g_cm3": 7.8, "volumen_cm3": 200, "beschreibung": "Eisenplatte gemessen"},
        {"id": "D4", "material_vermutung": "gold", "volumen_cm3": 10, "beschreibung": "Unbekanntes Metall"},
        {"id": "E5", "volumen_cm3": -5, "beschreibung": "Kaputter Datensatz"}
    ]
    ergebnis = sorter.sortieren(test_teile)
    print(json.dumps(ergebnis, indent=2, ensure_ascii=False))

    print("\n=== Alle Tests durchgelaufen ===")