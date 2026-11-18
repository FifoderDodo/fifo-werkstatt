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
    stimmung = daten.get("stimmung", 0)
    wetter = daten.get("wetter", "unbekannt")

    # Erlaubte Aktionen (Whitelist)
    ERLAUBT = {
        "think", "eat", "drink", "walk_to", "sitzen", "spazieren",
        "schrott_suchen", "aufheben", "verkaufen", "einlagern",
        "malen", "komponieren", "read_news", "muenze_werfen",
        "nachsehen", "am_projekt_arbeiten"
    }

    plan = []
    notiz_teile = []

    # 1. Stimmung prüfen: Wenn mies, erst mal Basis versorgen (nur 1 Slot!)
    if stimmung < -30:
        plan.append({"aktion": "drink", "text": "Wasser trinken, Basis checken"})
        notiz_teile.append("Stimmung tief. Basis first.")
    elif stimmung > 70:
        notiz_teile.append("Guter Start. Nutzen.")

    # 2. Fehlschläge analysieren: häufigste -> Gegenmaßnahme
    if fehlschlaege:
        top_fehler = max(fehlschlaege.items(), key=lambda x: x[1])[0]
        if top_fehler in ERLAUBT:
            if top_fehler in {"schrott_suchen", "aufheben", "verkaufen", "einlagern"}:
                plan.append({"aktion": "nachsehen", "text": f"Checken, warum '{top_fehler}' schiefging"})
            else:
                plan.append({"aktion": "think", "text": f"Nachdenken über '{top_fehler}'"})
            notiz_teile.append(f"Top-Fehler: {top_fehler}.")

    # 3. Gestern häufiges wiederholen oder fortsetzen (max 1 Slot, wenn Platz)
    if gestern and len(plan) < 3:
        top_gestern = max(gestern.items(), key=lambda x: x[1])[0]
        if top_gestern in ERLAUBT and top_gestern not in [p["aktion"] for p in plan]:
            if top_gestern == "am_projekt_arbeiten":
                plan.append({"aktion": "am_projekt_arbeiten", "text": "Projekt weitertreiben, ein Schritt"})
            elif top_gestern in {"malen", "komponieren"}:
                plan.append({"aktion": top_gestern, "text": f"Kreativ weitermachen: {top_gestern}"})
            else:
                plan.append({"aktion": top_gestern, "text": f"Routine: {top_gestern}"})
            notiz_teile.append(f"Gestern oft: {top_gestern}.")

    # 4. Wetter-Reaktion (falls Platz)
    if len(plan) < 3:
        if "regen" in wetter.lower() or "sturm" in wetter.lower():
            plan.append({"aktion": "sitzen", "text": "Drinnen bleiben, Tee, Projekt"})
            notiz_teile.append("Wetter mies.")
        elif "sonne" in wetter.lower() or "klar" in wetter.lower():
            plan.append({"aktion": "spazieren", "text": "Raus, Licht tanken, 20 Min."})
            notiz_teile.append("Wetter gut.")

    # 5. Fallback: Wenn Plan leer, Minimalprogramm
    if not plan:
        plan.append({"aktion": "think", "text": "Erst mal sortieren, was ansteht"})
        plan.append({"aktion": "drink", "text": "Wasser"})
        notiz_teile.append("Leere Daten. Standard-Start.")

    # Plan auf max 3 kürzen
    plan = plan[:3]

    # Notiz zusammenbauen, max 200 Zeichen
    notiz = ". ".join(notiz_teile)
    if len(notiz) > 200:
        notiz = notiz[:197] + "..."

    return {"notiz": notiz, "plan": plan}


# Kleiner Selbsttest beim direkten Aufruf
if __name__ == "__main__":
    import json
    
    # Test 1: Normaler Tag mit Daten
    test_daten_1 = {
        "gestern": {"am_projekt_arbeiten": 3, "schrott_suchen": 2, "spazieren": 1},
        "fehlschlaege": {"schrott_suchen": 2, "verkaufen": 1},
        "stimmung": 15,
        "wetter": "sonnig"
    }
    print("--- Test 1 ---")
    print(json.dumps(neuer_tag(test_daten_1), ensure_ascii=False, indent=2))

    # Test 2: Leere Daten (Randfall)
    test_daten_2 = {
        "gestern": {},
        "fehlschlaege": {},
        "stimmung": 30,
        "wetter": ""
    }
    print("\n--- Test 2 ---")
    print(json.dumps(neuer_tag(test_daten_2), ensure_ascii=False, indent=2))

    # Test 3: Schlechte Stimmung (Prüfen ob nur 1 Basis-Aktion kommt)
    test_daten_3 = {
        "gestern": {"think": 5},
        "fehlschlaege": {},
        "stimmung": -50,
        "wetter": "regen"
    }
    print("\n--- Test 3 (Tiefstimmung) ---")
    print(json.dumps(neuer_tag(test_daten_3), ensure_ascii=False, indent=2))