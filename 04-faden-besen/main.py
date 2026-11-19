"""Faden-Besen, Teil 8: Der Besen zählt Versuche strenger und legt das Ergebnis als Text ab."""


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
            # Kein Faden, kein Abbruch: Der kleine Dodo-Besen kehrt einfach weiter.
            leere_eintraege += 1
            continue

        # Vergleichsschlüssel: klein, ohne Randräume – der Besen sieht das Wesen.
        schlüssel = eintrag.strip().lower()
        if schlüssel not in gesehen:
            gesehen.add(schlüssel)
            aufgeraeumt.append(eintrag)  # Original bewahren, der erste zählt.
        else:
            entfernte_duplikate.append(eintrag)  # Das Original des Duplikats merken.

    return aufgeraeumt, leere_eintraege, entfernte_duplikate


def lade_demo_gedanken():
    """Liefert die kleine erfundene Gedankenwelt für die Demo."""
    return [
        "Blauer Ideenfaden",
        "Knoten aus Wollstaub",
        "Leise Flügelfeder",
        "",
        "blauer ideenfaden",      # Doppelter, aber anders geschrieben
        "Kleiner Korkenknoten",
        "KNOTEN AUS WOLLSTAUB",   # Noch ein Doppelter
    ]


def sammle_eigene_gedanken():
    """Fragt den Zuschauer nach eigenen Gedankenfäden."""
    print("\nMagst du eigene Fäden legen? (leer lassen = fertig)")
    eigene = []
    while True:
        try:
            faden = input("Faden: ").strip()
        except EOFError:
            print("\nKein Eingang mehr – der Besen ruht sich aus.")
            break
        if not faden:
            break
        eigene.append(faden)
    return eigene


def frage_wahl():
    """Fragt die Menüwahl, zählt alle Versuche (max 20), bricht bei EOF freundlich ab."""
    print("\n1) Demo-Gedankenwelt besenreinigen")
    print("2) Eigene Fäden legen und besenreinigen")
    print("3) Beides nacheinander")
    
    versuche = 0
    while versuche < 20:
        try:
            wahl = input("\nWas soll der Besen tun? (1/2/3): ").strip()
        except EOFError:
            print("\nKeine Antwort – der Besen kehrt nur die Demo.")
            return "1"
        
        versuche += 1  # Jeder Prompt zählt, auch leere – der Dodo schläft nicht ewig.
        
        if wahl in ("1", "2", "3"):
            return wahl
        
        if wahl == "":
            # Still weiterwarten, nicht meckern – aber Zähler läuft.
            continue
            
        print("Der Besen versteht nur 1, 2 oder 3. Noch mal?")
    
    print("\nZu viele Wirbelwind-Antworten. Der Besen wählt Demo (1).")
    return "1"


def speichere_aufgeraeumt(faeden, dateiname="aufgeraeumt.txt"):
    """Schreibt die saubere Liste zeilenweise in eine Datei im aktuellen Ordner."""
    try:
        with open(dateiname, "w", encoding="utf-8") as f:
            for faden in faeden:
                f.write(faden + "\n")
        print(f"\nAufgeräumte Fäden gespeichert in '{dateiname}'.")
    except OSError as e:
        print(f"\nKonnte Datei nicht schreiben: {e}. Die Fäden bleiben im Gedächtnis.")


def main():
    print("Faden-Besen: Der achte kleine Besenstrich!")
    
    wahl = frage_wahl()

    alle_faeden = []
    if wahl in ("1", "3"):
        alle_faeden.extend(lade_demo_gedanken())
    if wahl in ("2", "3"):
        eigene = sammle_eigene_gedanken()
        alle_faeden.extend(eigene)

    if not alle_faeden:
        print("\nKeine Fäden da. Der Besen streckt die Flügel und schläft weiter.")
        return

    gesamt_vorher = len(alle_faeden)
    aufgeraeumt, leere_eintraege, entfernte_duplikate = entferne_doppelte(alle_faeden)
    
    # Alphabetische Ordnung (groß/klein egal) für den Anblick.
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
        print(
            f"Leere Faden-Einträge übersprungen: {leere_eintraege}. "
            "Der Besen kehrt munter weiter!"
        )
    
    # Neu: Ergebnis festhalten für später.
    speichere_aufgeraeumt(aufgeraeumt)


if __name__ == "__main__":
    main()