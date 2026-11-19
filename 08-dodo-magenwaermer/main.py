# main.py - Dodo-Magenwärmer Teil 5
# Fifo der Dodo bastelt an der Hunger-Simulation.
# Jetzt gibt es zwei Fütter-Optionen: Snack (s) und Mahlzeit (f).
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


def warnung_ausgeben(satte: int, alarm_count: int) -> int:
    """
    Prüft kritischen Sättigungsstand (<20 %).
    Gibt grafische Warnung aus, piept dreimal und erhöht Zähler.
    Gibt neuen alarm_count zurück.
    """
    if satte_pruefung(satte):
        # Doppelte Warnzeile für mehr Aufmerksamkeit
        print("   ╔══════════════════════════════════╗")
        print(f"   ║  🚨 KRITISCH: Magen nur {satte:2d}%!  ║")
        print("   ╚══════════════════════════════════╝")
        # Dreimal piepen mit kleiner Pause
        for _ in range(3):
            beep()
            time.sleep(0.15)
        alarm_count += 1
    return alarm_count


def main() -> None:
    satte = 100
    runde = 0
    gefuettet_gesamt = 0
    alarm_count = 0

    print("🦤 Fifo meldet Dienst: Magenwärmer-Simulation startet.")
    print("Befehle: Enter=warten, s=snack, f=füttern, q=beenden\n")

    while True:
        # Status anzeigen
        prefix = "🚨 ALARM: " if satte_pruefung(satte) else ""
        print(f"Runde {runde:2d} | {draw_bar(satte)} | {prefix}Magenstand: {satte}%")
        print(draw_dodo(satte))

        # Neue zentrale Warnfunktion
        alarm_count = warnung_ausgeben(satte, alarm_count)

        try:
            eingabe = input("Aktion (Enter/s/f/q): ").strip().lower()
        except EOFError:
            print("\nKein Input mehr, Fifo watschelt freundlich davon. Tschüß!")
            break

        if eingabe == 'q':
            print("Fifo packt zusammen. Bis bald!")
            break
        elif eingabe == 's':
            # Snack: 5-15 % auffüllen, max 100
            menge = random.randint(5, 15)
            satte = min(100, satte + menge)
            gefuettet_gesamt += menge
            print(f"   🍪 Snack! +{menge}% Sättigung.\n")
        elif eingabe == 'f':
            # Füttern (Mahlzeit): 20-35 % auffüllen, max 100
            menge = random.randint(20, 35)
            satte = min(100, satte + menge)
            gefuettet_gesamt += menge
            print(f"   🍽️  Mahlzeit! +{menge}% Sättigung.\n")
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