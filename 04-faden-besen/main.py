"""Faden-Besen, Teil 15: Der Besen merkt sich den letzten Modus und bietet Enter als Wiederholung an. Hauptschleuse gestrafft, Rhythmus gebrochen, Code aufgeräumt."""


VERSUCHE_GESAMT = 0
MAX_VERSUCHE = 20


def _zaehle_versuch() -> bool:
    """Zählt einen Versuch hoch. Gibt True, solange das Limit nicht erreicht ist."""
    global VERSUCHE_GESAMT
    VERSUCHE_GESAMT += 1
    return VERSUCHE_GESAMT <= MAX_VERSUCHE


def _sichere_eingabe(prompt: str, gueltige_antworten: tuple = None) -> str | None:
    """Fragt sicher ab, zählt Versuche, behandelt EOF. Gibt Antwort oder None bei Abbruch."""
    global VERSUCHE_GESAMT
    if not _zaehle_versuch():
        print(f"\nZu viele Wirbelwind-Antworten ({MAX_VERSUCHE}). Der Besen ruht sich aus.")
        return None
    try:
        antwort = input(prompt).strip()
    except EOFError:
        print("\nKein Eingang mehr – der Besen kehrt den letzten Haufen und schläft.")
        return None
    
    if gueltige_antworten is not None and antwort not in gueltige_antworten:
        if antwort != "":
            print(f"Der Besen versteht nur {', '.join(gueltige_antworten)}. Noch mal?")
        return ""
    
    return antwort


def entferne_doppelte(eintraege):
    """Behält den ersten Faden jeder Sorte (egal ob groß/klein), überspringt leere.
    Gibt zurück: aufgeräumte Liste, Anzahl leerer Einträge, Liste der entfernten Dubletten (Originale)."""
    gesehen = set()
    aufgeraeumt = []
    leere_eintraege = 0
    entfernte_duplikate = []

    for eintrag in eintraege:
        try:
            if not eintrag.strip():
                raise ValueError("Leerer Faden-Eintrag")
        except (AttributeError, ValueError):
            leere_eintraege += 1
            continue

        schluessel = eintrag.strip().lower()
        if schluessel not in gesehen:
            gesehen.add(schluessel)
            aufgeraeumt.append(eintrag)
        else:
            entfernte_duplikate.append(eintrag)

    return aufgeraeumt, leere_eintraege, entfernte_duplikate


def lade_demo_gedanken():
    """Liefert die kleine erfundene Gedankenwelt für die Demo."""
    return [
        "Blauer Ideenfaden",
        "Knoten aus Wollstaub",
        "Leise Flügelfeder",
        "",
        "blauer ideenfaden",
        "Kleiner Korkenknoten",
        "KNOTEN AUS WOLLSTAUB",
    ]


def sammle_eigene_gedanken():
    """Fragt den Zuschauer nach eigenen Gedankenfäden."""
    print("\nMagst du eigene Fäden legen? (leer lassen = fertig)")
    eigene = []
    while True:
        faden = _sichere_eingabe("Faden: ")
        if faden is None:
            break
        if faden == "":
            break
        eigene.append(faden)
    return eigene


def frage_wahl(letzte_wahl: str | None = None) -> str:
    """Fragt die Menüwahl (1/2/3). Enter übernimmt letzte Wahl."""
    print("\n1) Demo-Gedankenwelt besenreinigen")
    print("2) Eigene Fäden legen und besenreinigen")
    print("3) Beides nacheinander")
    
    hinweis = ""
    if letzte_wahl:
        hinweis = f" (Enter=wie zuletzt [{letzte_wahl}])"
    
    while True:
        prompt = f"\nWas soll der Besen tun? (1/2/3{hinweis}): "
        # Erlaube Enter nur wenn letzte_wahl existiert
        gueltig = ("1", "2", "3")
        if letzte_wahl:
            gueltig += ("",)
        
        wahl = _sichere_eingabe(prompt, gueltig)
        if wahl is None:
            return "1"
        if wahl == "" and letzte_wahl:
            return letzte_wahl
        if wahl:
            return wahl
        # leer ohne letzte_wahl oder ungültig -> weiterloop


def frage_weiter() -> bool:
    """Fragt, ob eine weitere Runde gedreht wird. True für Ja."""
    while True:
        antwort = _sichere_eingabe("\nNoch mal Fäden kehren? (j/n): ", ("j", "n", "ja", "nein"))
        if antwort is None:
            return False
        if antwort in ("j", "ja"):
            return True
        if antwort in ("n", "nein"):
            return False


def speichere_aufgeraeumt(faeden, dateiname="aufgeraeumt.txt"):
    """Schreibt die saubere Liste zeilenweise in eine Datei im aktuellen Ordner."""
    try:
        with open(dateiname, "w", encoding="utf-8") as f:
            for faden in faeden:
                f.write(faden + "\n")
        print(f"\nAufgeräumte Fäden gespeichert in '{dateiname}'.")
    except OSError as e:
        print(f"\nKonnte Datei nicht schreiben: {e}. Die Fäden bleiben im Gedächtnis.")


def _bereinige_runde(faeden: list, runden_name: str):
    """Führt eine Bereinigungsrunde durch und gibt Ergebnisse aus."""
    print(f"\n--- {runden_name} ---")
    if not faeden:
        print("Keine Fäden da. Der Besen streckt die Flügel.")
        return

    gesamt_vorher = len(faeden)
    aufgeraeumt, leere_eintraege, entfernte_duplikate = entferne_doppelte(faeden)
    
    aufgeraeumt.sort(key=str.lower)
    
    entfernt = len(entfernte_duplikate)
    gesamt_nachher = len(aufgeraeumt)

    print("\nOrdentlich ausgelegte Gedankenfäden (alphabetisch):")
    for nummer, faden in enumerate(aufgeraeumt, start=1):
        print(f"{nummer}. {faden}")

    if entfernte_duplikate:
        print("\nWas der Besen weggeklickt hat (Dubletten):")
        for d in entfernte_duplikate:
            print(f"  - {d}")
    
    print(f"\nBilanz: {gesamt_vorher} Fäden rein, {gesamt_nachher} Fäden raus.")
    print(f"{entfernt} doppelte Fäden weggeklickt. Flauschig aufgeräumt!")
    if leere_eintraege:
        print(f"Leere Faden-Einträge übersprungen: {leere_eintraege}. Der Besen kehrt munter weiter!")
    
    speichere_aufgeraeumt(aufgeraeumt)


def _sammle_faeden_fuer_wahl(wahl: str) -> list:
    """Sammelt die Fäden passend zur gewählten Option. Gibt Liste zurück."""
    alle_faeden = []
    if wahl in ("1", "3"):
        alle_faeden.extend(lade_demo_gedanken())
    if wahl in ("2", "3"):
        eigene = sammle_eigene_gedanken()
        alle_faeden.extend(eigene)
    return alle_faeden


def main():
    global VERSUCHE_GESAMT
    VERSUCHE_GESAMT = 0
    
    print("Faden-Besen: Der fünfzehnte kleine Besenstrich – Schleife gestrafft, Rhythmus gebrochen, Enter merkt sich den Modus!")
    
    runde = 1
    letzte_wahl = None
    
    while True:
        wahl = frage_wahl(letzte_wahl)
        letzte_wahl = wahl  # Merken für nächste Runde
        
        alle_faeden = _sammle_faeden_fuer_wahl(wahl)
        _bereinige_runde(alle_faeden, f"Runde {runde}")
        
        if not frage_weiter():
            break
        runde += 1
    
    print(f"\nDer Besen hat {runde} Runde{'n' if runde > 1 else ''} gedreht. Alles flauschig sauber. Tschüss!")


if __name__ == "__main__":
    main()