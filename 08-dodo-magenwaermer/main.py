# main.py - Dodo-Magenwärmer Teil 2
# Fifo der Dodo bastelt an der Hunger-Simulation.
# Jetzt läuft der Magen in Runden: Warten lässt den Pegel sinken, Füttern hebt ihn.
# Immer noch nur Standardbibliothek, alles im Speicher, Dodo-Ehrenwort.

import random
import time

def satte_pruefung(aktueller_wert: int) -> bool:
    """Prüft, ob Sättigung unter 20 % gefallen ist."""
    return aktueller_wert < 20


def draw_bar(wert: int, breite: int = 20) -> str:
    """Baut einen kleinen ASCII-Balken für die optische Anzeige."""
    voll = int(wert / 100 * breite)
    leer = breite - voll
    farbe = "\033[91m" if wert < 20 else "\033[92m"  # Rot bei Alarm, sonst Grün
    reset = "\033[0m"
    return f"{farbe}[{'#' * voll}{'.' * leer}]{reset} {wert}%"


def main() -> None:
    satte = 100
    runde = 0

    print("🦤 Fifo meldet Dienst: Magenwärmer-Simulation startet.")
    print("Befehle: Enter=warten, f=füttern, q=beenden\n")

    while True:
        # Status anzeigen
        alarm = satte_pruefung(satte)
        prefix = "🚨 ALARM: " if alarm else ""
        print(f"Runde {runde:2d} | {draw_bar(satte)} | {prefix}Magenstand: {satte}%")

        if alarm:
            print("   >>> Der Magen knurrt laut! Füttern nicht vergessen. <<<")

        try:
            eingabe = input("Aktion (Enter/f/q): ").strip().lower()
        except EOFError:
            print("\nKein Input mehr, Fifo watschelt freundlich davon. Tschüß!")
            break

        if eingabe == 'q':
            print("Fifo packt zusammen. Bis bald!")
            break
        elif eingabe == 'f':
            # Füttern: 15-30 % auffüllen, max 100
            menge = random.randint(15, 30)
            satte = min(100, satte + menge)
            print(f"   🍪 Gefüttert! +{menge}% Sättigung.\n")
        else:
            # Warten: Zeit vergeht, Magen leert sich 5-15 %
            verlust = random.randint(5, 15)
            satte = max(0, satte - verlust)
            print(f"   ⏳ Zeit vergeht... -{verlust}% Sättigung.\n")

        runde += 1
        if satte <= 0:
            print("   ☠️ Der Magen ist ganz leer. Fifo wird ohnmächtig... Spielende.")
            break

    print("\nSimulation beendet. Fifo nickt zufrieden.")


if __name__ == "__main__":
    main()