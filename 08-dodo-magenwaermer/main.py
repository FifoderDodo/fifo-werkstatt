# main.py - Dodo-Magenwärmer Teil 7
# Fifo der Dodo bastelt weiter im Traum.
# Fehler behoben: TERM-Variable nicht gesetzt -> Terminal-Funktionen nur bei echtem TTY nutzen.
# Kleiner Schritt: Hauptschleife mit Hunger-Simulation, Füttern per Eingabe, sauberes Beenden.

import random
import time
import sys
import os

# Prüfen, ob wir in einem echten Terminal laufen (für ANSI-Codes und clear)
USE_ANSI = sys.stdout.isatty()

def satte_pruefung(aktueller_wert: int) -> bool:
    """Prüft, ob Sättigung unter 20 % gefallen ist."""
    return aktueller_wert < 20

def clear_screen() -> None:
    """Löscht Terminal plattformunabhängig, nur wenn TTY."""
    if not USE_ANSI:
        return
    # ANSI Escape: Bildschirm löschen + Cursor home
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def draw_bar(wert: int, breite: int = 25) -> str:
    """Baut einen ASCII-Balken mit Farbverlauf (nur bei TTY)."""
    voll = int(wert / 100 * breite)
    leer = breite - voll
    if USE_ANSI:
        if wert >= 80:
            farbe = "\033[92m"      # Grün
        elif wert >= 50:
            farbe = "\033[93m"      # Gelb
        elif wert >= 20:
            farbe = "\033[38;5;208m" # Orange
        else:
            farbe = "\033[91m"      # Rot
        reset = "\033[0m"
        return f"{farbe}[{'#' * voll}{'.' * leer}]{reset} {wert:3d}%"
    else:
        return f"[{'#' * voll}{'.' * leer}] {wert:3d}%"

def draw_stomach(wert: int) -> str:
    """Zeichnet einen ASCII-Magen, der sich füllt/leert."""
    level = max(0, min(5, int(wert / 20)))  # 0-5 Stufen
    stages = [
        "  \\       //\n   \\     //\n    \\   //\n     \\ //\n      \\V/",  # 0%
        "  \\~~~~~~~//\n   \\     //\n    \\   //\n     \\ //\n      \\V/",  # 20%
        "  \\~~~~~~~//\n   \\~~~~~//\n    \\   //\n     \\ //\n      \\V/",  # 40%
        "  \\~~~~~~~//\n   \\~~~~~//\n    \\~~~//\n     \\ //\n      \\V/",  # 60%
        "  \\~~~~~~~//\n   \\~~~~~//\n    \\~~~//\n     \\~/\n      \\V/",  # 80%
        "  \\~~~~~~~//\n   \\~~~~~//\n    \\~~~//\n     \\~/\n      \\~"   # 100%
    ]
    return stages[level]

def draw_dodo(wert: int, anim_phase: int = 0) -> str:
    """Gibt ein ASCII-Dodo-Gesicht zurück, mit Blinzel-Animation."""
    blinzelt = (anim_phase % 10) == 0
    if blinzelt:
        augen = "-.-"
    else:
        augen = "o.o"
    if wert < 20:
        mund = ">_<"
    elif wert < 50:
        mund = "._."
    else:
        mund = "^_^"
    return f"   {augen}\n   ({mund})"

def main() -> None:
    hunger = 100
    schritt = 0
    print("🦤 Dodo-Magenwärmer gestartet. Strg+C oder 'q' zum Beenden.")
    time.sleep(1)
    
    while hunger > 0:
        clear_screen()
        schritt += 1
        # Hunger sinkt zufällig
        hunger -= random.randint(3, 8)
        hunger = max(0, hunger)
        
        print(draw_stomach(hunger))
        print()
        print(draw_bar(hunger))
        print()
        print(draw_dodo(hunger, schritt))
        print(f"\nSchritt {schritt} | Hunger: {hunger}%")
        
        if satte_pruefung(hunger):
            print("\n⚠️  Magen knurrt! Füttern? (Enter = füttern, q = quittieren)")
        else:
            print("\nAlles gut. Enter für nächsten Schritt, q zum Beenden.")
        
        try:
            eingabe = input("> ").strip().lower()
        except EOFError:
            print("\nKeine Eingabe möglich. Schlaf gut, kleiner Dodo.")
            break
        
        if eingabe == 'q':
            print("Bis zum nächsten Traum!")
            break
        elif eingabe == '':
            hunger = min(100, hunger + random.randint(15, 30))
            print("🍎 Gefüttert!")
            time.sleep(0.5)
        # sonst: einfach weiter
        
        time.sleep(0.3)
    
    if hunger <= 0:
        clear_screen()
        print(draw_stomach(0))
        print("\n💀 Der Dodo ist verhungert. Gute Nacht.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTraum unterbrochen. Gute Nacht!")