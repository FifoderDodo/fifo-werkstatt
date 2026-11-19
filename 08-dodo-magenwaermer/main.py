# main.py - Dodo-Magenwärmer Teil 3
# Fifo der Dodo bastelt an der Hunger-Simulation.
# Jetzt piept der PC bei Alarm und Fifo zeigt Gesichter.
# Immer noch nur Standardbibliothek, alles im Speicher, Dodo-Ehrenwort.

import random
import time
import sys

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


def draw_dodo(wert: int) -> str:
    """Gibt ein ASCII-Dodo-Gesicht zurück, passend zum Hungerlevel."""
    if wert <= 0:
        return "  ☠️  (x_x)  Fifo ist umgekippt."
    elif wert < 20:
        return "  🦤  (>_<)  Knurr!"
    elif wert < 50:
        return "  🦤  (o_o)  Mhh..."
    elif wert < 80:
        return "  🦤  (^_^)  Satt!"
    else:
        return "  🦤  (★_★)  Glücklich!"


def beep() -> None:
    """Lässt den Terminal piepen (ASCII BEL)."""
    sys.stdout.write('\a')
    sys.stdout.flush()


def main() -> None:
    satte = 100
    runde = 0
    gefuettet_gesamt = 0
    alarm_count = 0

    print("🦤 Fifo meldet Dienst: Magenwärmer-Simulation startet.")
    print("Befehle: Enter=warten, f=füttern, q=beenden\n")

    while True:
        # Status anzeigen
        alarm = satte_pruefung(satte)
        prefix = "🚨 ALARM: " if alarm else ""
        print(f"Runde {runde:2d} | {draw_bar(satte)} | {prefix}Magenstand: {satte}%")
        print(draw_dodo(satte))

        if alarm:
            print("   >>> Der Magen knurrt laut! Füttern nicht vergessen. <<<")
            beep()  # Piep beim Alarm
            alarm_count += 1

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
            gefuettet_gesamt += menge
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

    # Statistik am Ende
    print(f"\n--- Fifos Tagesbilanz ---")
    print(f"Runden überlebt:   {runde}")
    print(f"Gesamt gefüttert:  {gefuettet_gesamt}%")
    print(f"Alarm-Auslöser:    {alarm_count}")
    print("\nSimulation beendet. Fifo nickt zufrieden.")


if __name__ == "__main__":
    main()