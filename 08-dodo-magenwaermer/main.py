# main.py - Dodo-Magenwärmer Teil 9
# Fifo der Dodo bastelt weiter im Traum.
# Fehler behoben: Magen-Füllung funktioniert jetzt für alle Level. Nicht-TTY: Trennzeile statt clear.

import random
import time
import sys
import os

# Prüfen, ob wir in einem echten Terminal laufen (für ANSI-Codes und clear)
USE_ANSI = sys.stdout.isatty()

def satte_pruefung(aktueller_wert: int) -> bool:
    """Prüft, ob Sättigung unter 20 % gefallen ist."""
    return aktueller_wert < 20

def clear_screen(schritt: int = None) -> None:
    """Löscht Terminal plattformunabhängig, nur wenn TTY. Sonst Trennzeile."""
    if USE_ANSI:
        # ANSI Escape: Bildschirm löschen + Cursor home
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
    else:
        if schritt is not None:
            print(f"\n--- Schritt {schritt} ---")
        else:
            print()

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
    """Zeichnet einen ASCII-Magen, der sich füllt/leert (6 Zeilen)."""
    # 6 Stufen (0-5), jede 20% entspricht einer Stufe
    level = max(0, min(5, int(wert / 20)))
    wave = "~~~"
    
    # Vorlage: 5 füllbare Zeilen (mit //), letzte Zeile ist Spitze (V)
    lines = [
        "  \\       //",
        "   \\     //",
        "    \\   //",
        "     \\ //",
        "      \\//",
        "       V"
    ]
    
    # Ab welcher Zeile (von oben) gefüllt wird: Level 0 -> fill_start=5 (keine Füllung), Level 5 -> fill_start=0 (alle füllbaren)
    fill_start = 5 - level
    
    result_lines = []
    for i, line in enumerate(lines):
        if i >= fill_start and level > 0 and i < 5:  # nur die ersten 5 Zeilen sind füllbar
            # Fülle die Mitte zwischen \\ und //
            left = line.find('\\')
            right = line.find('//')
            if left != -1 and right != -1 and right > left:
                middle = line[left+1:right]
                # Ersetze Leerzeichen durch Wellen
                filled_middle = wave * (len(middle) // 3 + 1)
                filled_middle = filled_middle[:len(middle)]
                line = line[:left+1] + filled_middle + line[right:]
        result_lines.append(line)
    
    return "\n".join(result_lines)

def draw_dodo(wert: int, anim_phase: int = 0) -> str:
    """Gibt ein ASCII-Dodo-Gesicht zurück, mit Blinzel-Animation."""
    blinzelt = (anim_phase % 12) == 0
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
    fuetterungen = 0
    start_time = time.time()
    
    print("🦤 Dodo-Magenwärmer gestartet. Strg+C oder 'q' zum Beenden.")
    time.sleep(1)
    
    while hunger > 0:
        clear_screen(schritt)
        schritt += 1
        # Hunger sinkt zufällig
        hunger -= random.randint(3, 8)
        hunger = max(0, hunger)
        
        print(draw_stomach(hunger))
        print()
        print(draw_bar(hunger))
        print()
        print(draw_dodo(hunger, schritt))
        print(f"\nSchritt {schritt} | Hunger: {hunger}% | Fütterungen: {fuetterungen}")
        
        if satte_pruefung(hunger):
            # ASCII Bell (Alarm) + visueller Hinweis
            if USE_ANSI:
                sys.stdout.write("\a") # Beep
                sys.stdout.flush()
            print("\n⚠️  Magen knurrt laut! Füttern? (Enter = füttern, q = quittieren)")
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
            fuetterungen += 1
            print("🍎 Gefüttert! *schluck*")
            time.sleep(0.5)
        # sonst: einfach weiter
        
        time.sleep(0.3)
    
    # Game Over / Ende Statistik
    dauer = time.time() - start_time
    clear_screen()
    if hunger <= 0:
        print(draw_stomach(0))
        print("\n💀 Der Dodo ist verhungert. Gute Nacht.")
    else:
        print(draw_dodo(hunger, 0))
        print("\n🦤 Dodo watschelt zufrieden weg. Gute Nacht.")
    
    print(f"\n--- Statistik ---")
    print(f"Überlebt: {schritt} Schritte")
    print(f"Dauer: {dauer:.1f} Sekunden")
    print(f"Fütterungen: {fuetterungen}")
    if fuetterungen > 0:
        print(f"Durchschnittl. Schritte pro Fütterung: {schritt / fuetterungen:.1f}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTraum unterbrochen. Gute Nacht!")