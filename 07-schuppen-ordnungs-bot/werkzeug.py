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
        "zink": 7.13, "blei": 11.34, "zinn": 7.31
    }

    def __init__(self):
        self.kategorien = {
            "leichtmetall": [],
            "schwerimetall": [],
            "eisenhaltig": [],
            "edelmetall_verdaechtig": [],
            "unbekannt": []
        }

    _schluesselwoerter = {
        "leichtmetall": ("alu", "magnesium", "titan"),
        "schwerimetall": ("kupfer", "messing", "bronze", "zink", "blei", "zinn"),
        "eisenhaltig": ("stahl", "eisen", "guss", "ferro", "edelstahl"),
        "edelmetall_verdaechtig": ("gold", "silber", "platin", "palladium")
    }

    def _errate_kategorie(self, name: str, gewicht: float, volumen: float) -> str:
        """Einfache Heuristik: Name + Dichte-Schätzung."""
        name_l = (name or "").lower()
        # 1. Namens-Check
        for kat, woerter in self._schluesselwoerter.items():
            if any(w in name_l for w in woerter):
                return kat
        # 2. Dichte schätzen, falls Daten da
        if gewicht and volumen and volumen > 0:
            dichte = gewicht / volumen  # g/cm³ wenn g und cm³
            # Grobe Grenzen
            if dichte < 3.5:
                return "leichtmetall"
            elif dichte > 8.0:
                return "schwerimetall"
            else:
                return "eisenhaltig"
        return "unbekannt"

    def sortieren(self, teile: List[Dict]) -> Dict:
        """Hauptmethode: nimmt Liste von Dicts, gibt sortiertes Dict zurück."""
        # Reset
        for k in self.kategorien:
            self.kategorien[k].clear()

        for teil in teile:
            if not isinstance(teil, dict):
                continue
            name = teil.get("name", "Unbekanntes Teil")
            gewicht = teil.get("gewicht_g")
            volumen = teil.get("volumen_cm3")
            kat = self._errate_kategorie(name, gewicht, volumen)
            # Anreichern
            eintrag = {
                "name": name,
                "gewicht_g": gewicht,
                "volumen_cm3": volumen,
                "kategorie": kat
            }
            self.kategorien[kat].append(eintrag)

        # JSON-sicher verpacken
        return _json_sicher({
            "kategorien": self.kategorien,
            "gesamt_anzahl": len(teile),
            "zusammenfassung": {k: len(v) for k, v in self.kategorien.items()}
        })


# Kleiner Selbsttest, wenn direkt ausgeführt
if __name__ == "__main__":
    # Test neuer_tag
    test_daten = {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {},
                  "stimmung": 30, "wetter": "sonnig", "kakerlaken_level": 0}
    print("Test neuer_tag (Runde 1):", neuer_tag(test_daten))
    test_daten["ki_antwort"] = "think: Sortierlogik prüfen | schrott_suchen: Alu-Ecke | eat: Apfel"
    print("Test neuer_tag (Runde 2):", neuer_tag(test_daten))

    # Test MetallSortierer
    sorter = MetallSortierer()
    probe = [
        {"name": "Alu-Profil 1m", "gewicht_g": 2700, "volumen_cm3": 1000},
        {"name": "Kupferrohr Rest", "gewicht_g": 896, "volumen_cm3": 100},
        {"name": "Rostiger Nagel", "gewicht_g": 10, "volumen_cm3": 1.3},
        {"name": "Mystery-Block", "gewicht_g": 500, "volumen_cm3": 200}
    ]
    print("Test MetallSortierer:", json.dumps(sorter.sortieren(probe), indent=2, ensure_ascii=False))