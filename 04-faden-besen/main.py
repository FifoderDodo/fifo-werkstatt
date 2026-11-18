"""Faden-Besen, Teil 4: Der Besen wird wählerisch beim Menü und blind für Großbuchstaben."""


def entferne_doppelte(eintraege):
    """Behält den ersten Faden jeder Sorte (egal ob groß/klein), überspringt leere."""
    gesehen = set()
    aufgeraeumt = []
    leere_eintraege = 0

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

    return aufgeraeumt, leere_eintraege


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

    print("Faden-Besen: Der vierte kleine Besenstrich!")
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

    aufgeraeumt, leere_eintraege = entferne_doppelte(alle_faeden)
    entfernt = len(alle_faeden) - len(aufgeraeumt) - leere_eintraege

    print("\nOrdentlich ausgelegte Gedankenfäden:")
    for nummer, faden in enumerate(aufgeraeumt, start=1):
        print(f"{nummer}. {faden}")

    print(f"\n{entfernt} doppelte Fäden weggeklickt. Flauschig aufgeräumt!")
    if leere_eintraege:
        print(
            f"Leere Faden-Einträge übersprungen: {leere_eintraege}. "
            "Der Besen kehrt munter weiter!"
        )


if __name__ == "__main__":
    main()