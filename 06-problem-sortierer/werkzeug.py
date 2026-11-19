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

    # Erlaubte Aktionen (Whitelist)
    ERLAUBT = {
        "think", "eat", "drink", "walk_to", "sitzen", "spazieren",
        "schrott_suchen", "aufheben", "verkaufen", "einlagern",
        "malen", "komponieren", "read_news", "muenze_werfen",
        "nachsehen", "am_projekt_arbeiten", "schuppen_ausmisten"
    }

    # Aktionen mit Sinn für 'Wiederholung lohnt sich' (Priorität)
    SINNVOLL_WIEDERHOLEN = {
        "am_projekt_arbeiten", "malen", "komponieren", 
        "schuppen_ausmisten", "spazieren", "read_news"
    }
    # Grind-Aktionen: nicht blind wiederholen
    GRIND = {"schrott_suchen", "aufheben", "einlagern", "verkaufen"}

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

    # 2. Fehlschläge analysieren: Top 2 -> Nachdenken (reparieren = verstehen)
    if fehlschlaege and len(plan) < 3:
        sortiert_fehler = sorted(fehlschlaege.items(), key=lambda x: x[1], reverse=True)
        for fehler_aktion, anzahl in sortiert_fehler[:2]:
            if len(plan) >= 3:
                break
            if fehler_aktion in ERLAUBT:
                # nachsehen ist für Events, nicht für Debugging. think ist sicher.
                add_aktion("think", f"Analyse: Warum '{fehler_aktion}' ({anzahl}x) scheiterte", f"Fehler-Fokus: {fehler_aktion} ({anzahl}x).")
            else:
                notiz_teile.append(f"Unbekannter Fehler: {fehler_aktion} ({anzahl}x).")
                if len(plan) < 3:
                    add_aktion("think", f"Rätsel: {fehler_aktion} klären", f"Unbekannt: {fehler_aktion}.")

    # 3. Gestern sinnvolles fortsetzen (Priorität: Projekt, Kreativ, Schuppen, Bewegung)
    if gestern and len(plan) < 3:
        # Sortieren: Priorität hoch -> runter, dann Häufigkeit
        def sort_key(item):
            aktion, anzahl = item
            prio = 0
            if aktion == "am_projekt_arbeiten": prio = 100
            elif aktion in {"malen", "komponieren"}: prio = 90
            elif aktion == "schuppen_ausmisten": prio = 80
            elif aktion == "spazieren": prio = 70
            elif aktion == "read_news": prio = 60
            elif aktion in GRIND: prio = 10  # niedrig
            else: prio = 50
            return (-prio, -anzahl)
        
        sortiert_gestern = sorted(gestern.items(), key=sort_key)
        
        for aktion, anzahl in sortiert_gestern:
            if len(plan) >= 3:
                break
            if aktion not in ERLAUBT:
                notiz_teile.append(f"Unbekannte Aktion gestern: {aktion} ({anzahl}x).")
                continue
            if any(p["aktion"] == aktion for p in plan):
                continue
            
            # walk_to braucht Ziel. Wenn häufig -> essladen (Standard) oder spazieren
            if aktion == "walk_to":
                add_aktion("walk_to", "walk_to essladen", f"Weg fortsetzen: {aktion} ({anzahl}x).")
            elif aktion in SINNVOLL_WIEDERHOLEN:
                if aktion == "am_projekt_arbeiten":
                    add_aktion(aktion, "Projekt weitertreiben, ein Schritt", f"Gestern wichtig: {aktion} ({anzahl}x).")
                elif aktion in {"malen", "komponieren"}:
                    add_aktion(aktion, f"Kreativ weitermachen: {aktion}", f"Gestern oft: {aktion} ({anzahl}x).")
                elif aktion == "schuppen_ausmisten":
                    add_aktion(aktion, "Schuppen weiter ausmisten, eine Ecke", f"Dranbleiben: {aktion} ({anzahl}x).")
                else:
                    add_aktion(aktion, f"Routine: {aktion}", f"Gestern gut: {aktion} ({anzahl}x).")
            # Grind nur wenn Platz und nix Besseres da (wird durch Sortierung automatisch hintenan gestellt)
            elif aktion in GRIND and len(plan) < 2: # Max 1 Grind wenn sonst leer
                 add_aktion(aktion, f"Routine: {aktion}", f"Gestern viel: {aktion} ({anzahl}x).")

    # 4. Wetter-Reaktion (echte Wetter-Arten)
    if len(plan) < 3:
        if wetter in {"regen", "gewitter", "sturm"}:
            add_aktion("sitzen", "Drinnen bleiben, Tee, Projekt", "Wetter mies.")
        elif wetter in {"schnee", "nebel"}:
            add_aktion("spazieren", "Kurze Runde, warm anziehen", "Wetter frisch.")
        elif wetter in {"klar", "sonne", "sonnig"}:
            add_aktion("spazieren", "Raus, Licht tanken, 20 Min.", "Wetter gut.")
        elif wetter == "wolken":
            add_aktion("read_news", "Wolken gucken, Nachrichten checken", "Wetter grau.")
        else:
            # Unbekanntes Wetter -> Think als Fallback
            add_aktion("think", "Wetter unklar, kurz orientieren", "Wetter unbekannt.")

    # Notiz zusammenbauen, max 200 Zeichen, keine doppelten Punkte
    notiz = ". ".join(filter(None, notiz_teile))
    if notiz and not notiz.endswith("."):
        notiz += "."
    notiz = notiz[:200]

    return {"notiz": notiz, "plan": plan}