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
        "zink": 7.13, "zinklegierung": 6.8,
        "blei": 11.34, "zinn": 7.31,
        "nickel": 8.9, "wolfram": 19.25,
        "gold": 19.3, "silber": 10.49, "platin": 21.45
    }

    # Magnetische Eigenschaften (True = ferromagnetisch)
    MAGNETISCH = {
        "stahl": True, "eisen": True, "guss": True, "ferro": True,
        "edelstahl": False,  # Meist austenitisch, nicht magnetisch
        "nickel": True,
        "kupfer": False, "messing": False, "bronze": False,
        "aluminium": False, "magnesium": False, "titan": False,
        "zink": False, "blei": False, "zinn": False,
        "gold": False, "silber": False, "platin": False, "wolfram": False
    }

    # Farben / Optik Hinweise
    FARBEN = {
        "kupfer": ["rot", "rotbraun", "grünspan", "kupfer"],
        "messing": ["gelb", "goldgelb", "messing"],
        "bronze": ["braun", "rotbraun", "bronze"],
        "aluminium": ["silber", "grau", "weiß", "aluminium", "hell"],
        "edelstahl": ["silber", "grau", "spiegel", "edelstahl"],
        "stahl": ["grau", "schwarz", "dunkel", "rost", "stahl"],
        "blei": ["grau", "blaugrau", "schwer", "blei"],
        "zink": ["grau", "weiß", "zink"],
        "gold": ["gold", "gelb", "golden"],
        "silber": ["silber", "weiß", "silbern"]
    }

    def _rate_metall_typ(self, teil: Dict) -> str:
        """Heuristik: Rät Metall-Typ basierend auf Gewicht, Magnet, Farbe, Bezeichnung."""
        name = str(teil.get("name", "")).lower()
        farbe = str(teil.get("farbe", "")).lower()
        magnet = teil.get("magnetisch", None)
        gewicht_g = teil.get("gewicht_g", None)
        volumen_cm3 = teil.get("volumen_cm3", None)
        dichte = None
        if gewicht_g is not None and volumen_cm3 and volumen_cm3 > 0:
            try:
                dichte = float(gewicht_g) / float(volumen_cm3)
            except (ValueError, TypeError, ZeroDivisionError):
                pass

        # 1. Namens-Check (stärkstes Signal)
        for typ, keys in [
            ("gold", ["gold"]), ("silber", ["silber"]), ("kupfer", ["kupfer", "cu"]),
            ("messing", ["messing", "ms"]), ("bronze", ["bronze"]),
            ("aluminium", ["alu", "aluminium"]), ("edelstahl", ["edelstahl", "v2a", "v4a", "niro"]),
            ("stahl", ["stahl", "st"]), ("eisen", ["eisen", "fe"]), ("guss", ["guss", "guß"]),
            ("magnesium", ["magnesium", "mg"]), ("titan", ["titan", "ti"]),
            ("zink", ["zink", "zn", "zamak"]), ("blei", ["blei", "pb"]),
            ("nickel", ["nickel", "ni"]), ("wolfram", ["wolfram", "w"]),
            ("platin", ["platin", "pt"])
        ]:
            if any(k in name for k in keys):
                return typ

        # 2. Magnet-Check
        if magnet is not None:
            magnetische_typen = [t for t, m in self.MAGNETISCH.items() if m == magnet]
            if len(magnetische_typen) < 10:  # Eingrenzung
                # Wenn magnetisch -> eher Eisen/Stahl/Nickel
                # Wenn nicht magnetisch -> Alu, Kupfer, Messing, Edelstahl, etc.
                pass  # Wir nutzen es nur als Filter unten

        # 3. Dichte-Schätzung
        if dichte is not None:
            best_typ = None
            best_diff = float('inf')
            for typ, d in self.DICHTEN.items():
                diff = abs(d - dichte)
                if diff < best_diff:
                    best_diff = diff
                    best_typ = typ
            # Toleranz ca 15%
            if best_typ and best_diff / self.DICHTEN[best_typ] < 0.15:
                # Magnet-Check verfeinern
                if magnet is not None and self.MAGNETISCH.get(best_typ) != magnet:
                    pass  # Widerspruch, ignoriere Dichte oder warne
                else:
                    return best_typ

        # 4. Farb-Check
        for typ, farblist in self.FARBEN.items():
            if any(f in farbe for f in farblist):
                if magnet is None or self.MAGNETISCH.get(typ) == magnet:
                    return typ

        # 5. Fallback: Magnetisch -> Stahl/Eisen, Nicht magnetisch -> Aluminium (häufigster Leichtmetall-Schrott)
        if magnet is True:
            return "stahl"
        if magnet is False:
            return "aluminium"

        return "unbekannt"

    def _kategorie_fuer_typ(self, typ: str) -> str:
        """Ordnet Metall-Typ Lager-Kategorie zu."""
        if typ in ("gold", "silber", "platin"):
            return "Edelmetall-Verdacht (abwiegen!)"
        if typ in ("kupfer", "messing", "bronze"):
            return "NE-Metall: Kupfer-Legierungen (hoher Wert)"
        if typ in ("aluminium", "magnesium", "titan"):
            return "Leichtmetall: Alu/Mg/Ti (getrennt sammeln)"
        if typ in ("edelstahl",):
            return "Edelstahl (magnetisch prüfen!)"
        if typ in ("stahl", "eisen", "guss", "ferro"):
            return "Eisen/Stahl (Schrottcontainer)"
        if typ in ("zink", "zinklegierung", "blei", "zinn", "nickel", "wolfram"):
            return "Sonstige NE-Metalle (Zink, Blei, etc.)"
        return "Unbekannt (Hand-Sortierung nötig)"

    def sortieren(self, teile: List[Dict]) -> Dict:
        """Hauptmethode: Sortiert Liste von Teilen in Kategorien."""
        kategorien = {}
        stats = {"gesamt": 0, "erkannt": 0, "unbekannt": 0}

        for teil in teile:
            stats["gesamt"] += 1
            if not isinstance(teil, dict):
                continue

            typ = self._rate_metall_typ(teil)
            kategorie = self._kategorie_fuer_typ(typ)

            if typ == "unbekannt":
                stats["unbekannt"] += 1
            else:
                stats["erkannt"] += 1

            # Teil anreichern
            angereichert = dict(teil)
            angereichert["metall_typ_heuristik"] = typ
            angereichert["kategorie"] = kategorie

            # In Kategorie einsortieren
            kategorien.setdefault(kategorie, []).append(_json_sicher(angereichert))

        # Sortierung innerhalb der Kategorien: schwer/value nach oben
        for kat, liste in kategorien.items():
            liste.sort(key=lambda x: (x.get("gewicht_g", 0) or 0), reverse=True)

        return {
            "kategorien": _json_sicher(kategorien),
            "statistik": stats
        }


if __name__ == "__main__":
    # Selbsttest für neuer_tag
    print("=== Test neuer_tag ===")
    test_faelle = [
        {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen": 2}, "stimmung": 10, "wetter": "sonnig"},
        {"gestern": {}, "fehlschlaege": {}, "stimmung": -60, "wetter": "regen", "kakerlaken_level": 2},
        {"gestern": {"spazieren": 1}, "fehlschlaege": {}, "stimmung": 50, "wetter": "bewoelkt", "kakerlaken_level": 7},
        {"gestern": {"think": 5}, "fehlschlaege": {"verkaufen": 1}, "stimmung": 0, "wetter": "heiter", "ki_antwort": "think: MetallSortierer testen | schrott_suchen: Alu-Haufen prüfen | einlagern: Kupferkiste füllen"}
    ]
    for i, fall in enumerate(test_faelle):
        print(f"\nFall {i+1}: {fall}")
        ergebnis = neuer_tag(fall)
        print(f"  -> {json.dumps(ergebnis, ensure_ascii=False, indent=2)}")
        # Simuliere 2. Runde falls Frage gestellt wurde
        if "frage_an_ki" in ergebnis:
            print(f"     [Frage an KI: {ergebnis['frage_an_ki'][:80]}...]")
            # Dummy-Antwort für Demo
            fall["ki_antwort"] = "think: Plan machen | eat: Brot | spazieren: Kurz raus"
            ergebnis2 = neuer_tag(fall)
            print(f"  -> 2. Runde: {json.dumps(ergebnis2, ensure_ascii=False, indent=2)}")

    # Selbsttest für MetallSortierer
    print("\n=== Test MetallSortierer ===")
    sorter = MetallSortierer()
    test_teile = [
        {"name": "Alu-Profil 1m", "gewicht_g": 810, "volumen_cm3": 300, "farbe": "silber", "magnetisch": False},
        {"name": "Kupferrohr Bogen", "gewicht_g": 450, "volumen_cm3": 50, "farbe": "rotbraun", "magnetisch": False},
        {"name": "Messing-Ventil", "gewicht_g": 320, "volumen_cm3": 38, "farbe": "gelb", "magnetisch": False},
        {"name": "Stahl-Schraube M10", "gewicht_g": 45, "volumen_cm3": 5.7, "farbe": "grau", "magnetisch": True},
        {"name": "Edelstahl-Becher", "gewicht_g": 220, "volumen_cm3": 28, "farbe": "spiegel", "magnetisch": False},
        {"name": "Schweres Teil", "gewicht_g": 1134, "volumen_cm3": 100, "farbe": "grau", "magnetisch": False},  # Blei?
        {"name": "Goldkette?", "gewicht_g": 20, "volumen_cm3": 1.0, "farbe": "gold", "magnetisch": False},
        {"name": "Magnetischer Klumpen", "gewicht_g": 500, "volumen_cm3": 64, "farbe": "rost", "magnetisch": True},
        {"name": "Weißes Leichtmetall", "gewicht_g": 100, "volumen_cm3": 57, "farbe": "weiß", "magnetisch": False},  # Mg?
        {"name": "Unbekannter Brocken", "gewicht_g": 200, "volumen_cm3": 30, "farbe": "grün", "magnetisch": False}
    ]
    ergebnis = sorter.sortieren(test_teile)
    print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
    print(f"\nStatistik: {ergebnis['statistik']}")
    print("\nFertig. Werkzeug scharf.")