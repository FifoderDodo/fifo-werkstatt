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
        "nickel": 8.91
    }
    TOLERANZ = 0.08  # 8%

    def __init__(self, teile: List[Dict[str, Any]]):
        self.teile = teile
        self.ergebnis = {}

    def magnet_test(self, teil: Dict[str, Any]) -> bool:
        """Simuliert Magnet-Test: Eisen, Stahl, Guss, Nickel sind magnetisch."""
        material = str(teil.get("material", "")).lower()
        magnetisch = {"eisen", "stahl", "guss", "ferro", "nickel"}
        return any(m in material for m in magnetisch)

    def funken_test(self, teil: Dict[str, Any]) -> str:
        """Simuliert Funkenbild: gibt grobe Kategorie zurück."""
        material = str(teil.get("material", "")).lower()
        if any(m in material for m in ["stahl", "eisen", "ferro"]):
            return "lang_golden"
        if "edelstahl" in material:
            return "kurz_rot"
        if "guss" in material:
            return "keine_funken"
        return "keine"  # NE-Metalle

    def dichte_test(self, teil: Dict[str, Any]) -> float:
        """Berechnet Dichte aus Gewicht/Volumen falls vorhanden, sonst Schätzung."""
        try:
            gewicht = float(teil.get("gewicht_g", 0))
            volumen = float(teil.get("volumen_cm3", 0))
            if gewicht > 0 and volumen > 0:
                return gewicht / volumen
        except (ValueError, TypeError):
            pass
        # Fallback: named density
        material = str(teil.get("material", "")).lower()
        for k, v in self.DICHTEN.items():
            if k in material:
                return v
        return 0.0

    def _dichte_match(self, gemessen: float, referenz: float) -> bool:
        if referenz == 0:
            return False
        return abs(gemessen - referenz) / referenz <= self.TOLERANZ

    def material_pruefung(self, teil: Dict[str, Any]) -> str:
        """Kombiniert Tests zu Material-Verdacht."""
        magnet = self.magnet_test(teil)
        funken = self.funken_test(teil)
        dichte = self.dichte_test(teil)

        if magnet:
            if funken == "kurz_rot":
                return "edelstahl"
            if funken == "keine_funken":
                return "guss"
            # Dichte prüfen für Stahl/Eisen/Nickel
            if self._dichte_match(dichte, self.DICHTEN.get("nickel", 8.91)):
                return "nickel"
            return "stahl_eisen"
        else:
            # NE-Metalle über Dichte
            for name, ref in self.DICHTEN.items():
                if name in ["eisen", "stahl", "guss", "ferro", "edelstahl", "nickel"]:
                    continue
                if self._dichte_match(dichte, ref):
                    return name
            return "unbekannt"

    def sortiere(self) -> Dict[str, List[Dict[str, Any]]]:
        """Sortiert alle Teile in Kategorien."""
        kats = {}
        for teil in self.teile:
            kat = self.material_pruefung(teil)
            kats.setdefault(kat, []).append(teil)
        self.ergebnis = kats
        return kats

    def get_ergebnis(self) -> Dict[str, Any]:
        """Liefert JSON-sicheres Zusammenfassungsergebnis."""
        if not self.ergebnis:
            self.sortiere()
        summary = {kat: len(teile) for kat, teile in self.ergebnis.items()}
        return _json_sicher({
            "kategorien": summary,
            "details": self.ergebnis,
            "gesamt": len(self.teile)
        })