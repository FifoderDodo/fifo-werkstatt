# werkzeug.py
# Fifo's Traumwerkzeug. Sortiert das Chaos von gestern in einen Plan für heute.
# Nur Standardbibliothek, schnell, ohne Schnickschnack.

def neuer_tag(daten: dict) -> dict:
    """
    Erzeugt einen Tagesplan basierend auf gestrigen Daten.
    Eingabe: {"gestern": {aktion: anzahl}, "fehlschlaege": {aktion: anzahl},
              "stimmung": -100..100, "wetter": "wort"}
    Ausgabe: {"notiz": "...", "plan": [{"aktion": "...", "text": "..."}]}
    """
    # Sicherung gegen kaputte Eingaben
    if not isinstance(daten, dict):
        daten = {}
    gestern = daten.get("gestern", {}) or {}
    fehlschlaege = daten.get("fehlschlaege", {}) or {}
    
    # Stimmung robust parsen (Typ-Sicherheit + Clamping)
    try:
        stimmung = int(daten.get("stimmung", 0))
    except (ValueError, TypeError):
        stimmung = 0
    stimmung = max(-100, min(100, stimmung))
    
    wetter = str(daten.get("wetter", "unbekannt")).lower()

    # Erlaubte Aktionen (Whitelist) - Schuppen ausmisten endlich offiziell
    ERLAUBT = {
        "think", "eat", "drink", "walk_to", "sitzen", "spazieren",
        "schrott_suchen", "aufheben", "verkaufen", "einlagern",
        "malen", "komponieren", "read_news", "muenze_werfen",
        "nachsehen", "am_projekt_arbeiten", "schuppen_ausmisten"
    }

    # Physische Aktionen, die 'nachsehen' als Reparatur brauchen
    PHYSISCH = {"schrott_suchen", "aufheben", "verkaufen", "einlagern", "schuppen_ausmisten"}

    plan = []
    notiz_teile = []

    # Helper: Fügt Aktion hinzu, wenn Platz und nicht schon drin
    def add_aktion(aktion: str, text: str, notiz: str = "") -> bool:
        if len(plan) >= 3:
            return False
        if aktion not in ERLAUBT:
            return False
        if any(p["aktion"] == aktion for p in plan):
            return False
        plan.append({"aktion": aktion, "text": text})
        if notiz:
            notiz_teile.append(notiz)
        return True

    # 1. Stimmung prüfen: Wenn mies, erst mal Basis versorgen (nur 1 Slot!)
    if stimmung < -30:
        add_aktion("drink", "Wasser trinken, Basis checken", "Stimmung tief. Basis first.")
    elif stimmung > 70:
        notiz_teile.append("Guter Start. Nutzen.")

    # 2. Fehlschläge analysieren: Top 2 häufigste -> Gegenmaßnahme (reparieren first!)
    if fehlschlaege and len(plan) < 3:
        # Sortiert absteigend nach Anzahl
        sortiert_fehler = sorted(fehlschlaege.items(), key=lambda x: x[1], reverse=True)
        for fehler_aktion, anzahl in sortiert_fehler[:2]:  # Max top 2 Fehler ansehen
            if len(plan) >= 3:
                break
            if fehler_aktion in ERLAUBT:
                if fehler_aktion in PHYSISCH:
                    add_aktion("nachsehen", f"Checken, warum '{fehler_aktion}' ({anzahl}x) schiefging", f"Reparatur: {fehler_aktion} ({anzahl}x).")
                else:
                    add_aktion("think", f"Nachdenken über '{fehler_aktion}' ({anzahl}x)", f"Top-Fehler: {fehler_aktion} ({anzahl}x).")
            else:
                notiz_teile.append(f"Unbekannter Fehler: {fehler_aktion} ({anzahl}x).")
                if len(plan) < 3:
                    add_aktion("think", f"Rätsel: {fehler_aktion} klären", f"Unbekannt: {fehler_aktion}.")

    # 3. Gestern häufiges wiederholen oder fortsetzen (Top 2, wenn Platz)
    if gestern and len(plan) < 3:
        sortiert_gestern = sorted(gestern.items(), key=lambda x: x[1], reverse=True)
        for aktion, anzahl in sortiert_gestern[:2]:
            if len(plan) >= 3:
                break
            if aktion in ERLAUBT and not any(p["aktion"] == aktion for p in plan):
                if aktion == "am_projekt_arbeiten":
                    add_aktion(aktion, "Projekt weitertreiben, ein Schritt", f"Gestern oft: {aktion} ({anzahl}x).")
                elif aktion in {"malen", "komponieren"}:
                    add_aktion(aktion, f"Kreativ weitermachen: {aktion}", f"Gestern oft: {aktion} ({anzahl}x).")
                elif aktion in PHYSISCH:
                    add_aktion(aktion, f"Routine: {aktion} fortsetzen", f"Gestern oft: {aktion} ({anzahl}x).")
                else:
                    add_aktion(aktion, f"Routine: {aktion}", f"Gestern oft: {aktion} ({anzahl}x).")
            elif aktion not in ERLAUBT:
                notiz_teile.append(f"Unbekannte Top-Aktion gestern: {aktion} ({anzahl}x).")

    # 4. Wetter-Reaktion (falls Platz)
    if len(plan) < 3:
        if "regen" in wetter or "sturm" in wetter:
            add_aktion("sitzen", "Drinnen bleiben, Tee, Projekt", "Wetter mies.")
        elif "sonne" in wetter or "klar" in wetter:
            add_aktion("spazieren", "Raus, Licht tanken, 20 Min.", "Wetter gut.")

    # 5. Fallback: Wenn Plan leer, Minimalprogramm
    if not plan:
        add_aktion("think", "Erst mal sortieren, was ansteht", "Leere Daten. Standard-Start.")
        add_aktion("drink", "Wasser", "")

    # Plan auf max 3 kürzen (Sicherheit)
    plan = plan[:3]

    # Notiz zusammenbauen, max 200 Zeichen
    notiz = ". ".join(filter(None, notiz_teile))
    if len(notiz) > 200:
        notiz = notiz[:197] + "..."

    return {"notiz": notiz, "plan": plan}


# Kleiner Selbsttest beim direkten Aufruf
if __name__ == "__main__":
    import json
    
    def run_test(name, daten):
        print(f"--- {name} ---")
        erg = neuer_tag(daten)
        print(json.dumps(erg, ensure_ascii=False, indent=2))
        print()

    # Test 1: Normaler Tag mit Daten
    run_test("Test 1: Normal", {
        "gestern": {"am_projekt_arbeiten": 3, "schrott_suchen": 2, "spazieren": 1},
        "fehlschlaege": {"schrott_suchen": 2, "verkaufen": 1},
        "stimmung": 15,
        "wetter": "sonnig"
    })

    # Test 2: Leere Daten (Randfall)
    run_test("Test 2: Leer", {
        "gestern": {},
        "fehlschlaege": {},
        "stimmung": 30,
        "wetter": ""
    })

    # Test 3: Schlechte Stimmung (Prüfen ob nur 1 Basis-Aktion kommt, Rest frei für Fehler/Wetter)
    run_test("Test 3: Schlechte Laune", {
        "gestern": {"think": 5},
        "fehlschlaege": {},
        "stimmung": -50,
        "wetter": "regen"
    })

    # Test 4: Doppelte Fäden - Schuppen ausmisten oft & schiefgegangen
    run_test("Test 4: Schuppen-Doppel", {
        "gestern": {"schuppen_ausmisten": 5, "malen": 2},
        "fehlschlaege": {"schuppen_ausmisten": 3},
        "stimmung": 10,
        "wetter": "bewölkt"
    })

    # Test 5: Viele Fehler, peu Platz
    run_test("Test 5: Fehlerflut", {
        "gestern": {"think": 1, "eat": 1},
        "fehlschlaege": {"schrott_suchen": 4, "verkaufen": 3, "aufheben": 2},
        "stimmung": 0,
        "wetter": "sonne"
    })

    # Test 6: Unbekannte Aktionen in Input (Robustheit)
    run_test("Test 6: Müll im Input", {
        "gestern": {"fliegen": 10, "schlafen": 5, "think": 1},
        "fehlschlaege": {"kaputt_machen": 99},
        "stimmung": "viel",  # Falscher Typ
        "wetter": 123        # Falscher Typ
    })