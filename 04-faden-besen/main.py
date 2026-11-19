"""Faden-Besen, Teil 10: Der Besen fragt artig, ob er weiterkehren darf."""


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
        # Ungültige Antwort: Nicht meckern bei Leere, sonst kurz hinweisen.
        if antwort != "":
            print(f"Der Besen versteht nur {', '.join(gueltige_antworten)}. Noch mal?")
        return ""  # Leerer String signalisiert: noch mal fragen, aber Versuch wurde gezählt.
    
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

        schlüssel = eintrag.strip().lower()
        if schlüssel not in gesehen:
            gesehen.add(schlüssel)
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
        if faden is None:  # EOF oder Limit
            break
        if faden == "":
            # Leere Eingabe beim Faden-Sammeln = Ende der Eingabephase
            break
        eigene.append(faden)
    return eigene


def frage_wahl():
    """Fragt die Menüwahl (1/2/3)."""
    print("\n1) Demo-Gedankenwelt besenreinigen")
    print("2) Eigene Fäden legen und besenreinigen")
    print("3) Beides nacheinander")
    
    while True:
        wahl = _sichere_eingabe("\nWas soll der Besen tun? (1/2/3): ", ("1", "2", "3"))
        if wahl is None:
            return "1"  # Default bei Abbruch
        if wahl:
            return wahl
        # bei leerer Antwort (_sichere_eingabe gibt "" zurück) einfach weiterloop


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
        # leer -> weiterfragen


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


def main():
    global VERSUCHE_GESAMT
    VERSUCHE_GESAMT = 0  # Reset für sauberen Start (wenn als Modul importiert)
    
    print("Faden-Besen: Der zehnte kleine Besenstrich – jetzt mit höflichem Nachfragen!")
    
    runde = 1
    while True:
        wahl = frage_wahl()
        
        alle_faeden = []
        if wahl in ("1", "3"):
            alle_faeden.extend(lade_demo_gedanken())
        if wahl in ("2", "3"):
            eigene = sammle_eigene_gedanken()
            alle_faeden.extend(eigene)
        
        _bereinige_runde(alle_faeden, f"Runde {runde}")
        
        if not frage_weiter():
            print("\nDer Besen stellt sich in die Ecke. Tschüss!")
            break
        
        runde += 1


if __name__ == "__main__":
    main()