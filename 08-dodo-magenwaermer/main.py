# main.py - Dodo-Magenwärmer Teil 1
# Fifo der Dodo bastelt an der Hunger-Logik.
# Wenn der Magen knurrt (< 20%), soll später die Anzeige blinken.
# Heute: nur die Abfrage bauen, schön sauber und mit Beispieldaten.

def satte_pruefung(aktueller_wert: int) -> bool:
    """Prüft, ob Sättigung unter 20 % gefallen ist."""
    return aktueller_wert < 20


def main() -> None:
    # Kleiner Vorrat an Beispieldaten, damit wir nicht nur eine Zahl testen.
    beispiel_werte = [100, 55, 19, 0, 20, 21]
    index = 0

    print("🦤 Fifo meldet Dienst: Magenwärmer-Logik startet.")
    print("Drück Enter für nächsten Testwert oder 'q' zum Beenden.")

    while index < len(beispiel_werte):
        try:
            # Im Browser kann der Zuschauer tippen, im Test kommen Beispiel-Antworten.
            eingabe = input(f"Testwert {beispiel_werte[index]}% – Enter für Prüfen, 'q' für Ende: ").strip().lower()
        except EOFError:
            print("\nKein Input mehr, Fifo watschelt freundlich davon. Tschüß!")
            break

        if eingabe == 'q':
            print("Fifo packt zusammen. Bis bald!")
            break

        wert = beispiel_werte[index]
        alarm = satte_pruefung(wert)
        status = "🚨 ALARM: Magen knurrt!" if alarm else "✅ Alles im grünen Bereich."
        print(f"Sättigung: {wert}% -> {status}\n")
        index += 1

    if index >= len(beispiel_werte):
        print("Alle Beispieldurchläufe erledigt. Fifo nickt zufrieden.")


if __name__ == "__main__":
    main()