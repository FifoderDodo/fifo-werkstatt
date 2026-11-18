"""Faden-Besen, Teil 5: Der Besen zeigt, was er weggekehrt hat – transparent und flauschig."""


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


def main():
    # Eine kleine erfundene Gedankenwelt mit Dubletten, Leere und Schreibweisen.
    gedankenfaeden = [
        "Blauer Ideenfaden",
        "Knoten aus Wollstaub",
        "Leise Flügelfeder",
        "",
        "blauer ideenfaden",      # Doppelter, aber anders geschrieben
        "Kleiner Korkenknoten",
        "KNOTEN AUS WOLLSTAUB",   # Noch ein Doppelter
    ]

    print("Faden-Besen: Der fünfte kleine Besenstrich!")
    print("\n1) Demo-Gedankenwelt besenreinigen")
    print("2) Eigene Fäden legen und besenreinigen")
    print("3) Beides nacheinander")
    
    wahl = ""
    while wahl not in ("1", "2", "3"):
        try:
            wahl = input("\nWas soll der Besen tun? (1/2/3): ").strip()
        except EOFError:
            print("\nKeine Antwort – der Besen kehrt nur die Demo.")
            wahl = "1"
            break
        if wahl not in ("1", "2", "3"):
            print("Der Besen versteht nur 1, 2 oder 3. Noch mal?")

    alle_faeden = []
    if wahl in ("1", "3"):
        alle_faeden.extend(gedankenfaeden)
    if wahl in ("2", "3"):
        eigene = sammle_eigene_gedanken()
        alle_faeden.extend(eigene)

    if not alle_faeden:
        print("\nKeine Fäden da. Der Besen streckt die Flügel und schläft weiter.")
        return

    aufgeraeumt, leere_eintraege, entfernte_duplikate = entferne_doppelte(alle_faeden)
    entfernt = len(entfernte_duplikate)

    print("\nOrdentlich ausgelegte Gedankenfäden:")
    for nummer, faden in enumerate(aufgeraeumt, start=1):
        print(f"{nummer}. {faden}")

    if entfernte_duplikate:
        print("\nWas der Besen weggeklickt hat (Dubletten):")
        for d in entfernte_duplikate:
            print(f"  - {d}")
    
    print(f"\n{entfernt} doppelte Fäden weggeklickt. Flauschig aufgeräumt!")
    if leere_eintraege:
        print(
            f"Leere Faden-Einträge übersprungen: {leere_eintraege}. "
            "Der Besen kehrt munter weiter!"
        )


if __name__ == "__main__":
    main()