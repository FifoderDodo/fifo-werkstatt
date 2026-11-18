"""Faden-Besen, Teil 1: doppelte Gedankenfäden aufsammeln."""


def entferne_doppelte(eintraege):
    """Behält den ersten Faden jeder Sorte und klickt spätere Dubletten weg."""
    gesehen = set()
    aufgeraeumt = []

    for eintrag in eintraege:
        if eintrag not in gesehen:
            gesehen.add(eintrag)
            aufgeraeumt.append(eintrag)

    return aufgeraeumt


def main():
    # Eine kleine erfundene Gedankenwelt, in der sich zwei Fäden doppelt verheddert haben.
    gedankenfaeden = [
        "Blauer Ideenfaden",
        "Knoten aus Wollstaub",
        "Leise Flügelfeder",
        "Blauer Ideenfaden",
        "Kleiner Korkenknoten",
        "Knoten aus Wollstaub",
    ]

    aufgeraeumt = entferne_doppelte(gedankenfaeden)
    entfernt = len(gedankenfaeden) - len(aufgeraeumt)

    print("Faden-Besen: Der erste kleine Besenstrich!")
    print("\nOrdentlich ausgelegte Gedankenfäden:")
    for nummer, faden in enumerate(aufgeraeumt, start=1):
        print(f"{nummer}. {faden}")

    print(f"\n{entfernt} doppelte Fäden weggeklickt. Flauschig aufgeräumt!")


if __name__ == "__main__":
    main()