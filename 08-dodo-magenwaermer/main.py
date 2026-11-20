# main.py - Dodo-Magenwärmer Teil 26 (Traum-Edition)
# Fifo der Dodo träumt weiter: Hauptschleife fertiggestellt, sanftes Aufwachen, Statistik robust.
# Fix: Unvollständige main() vervollständigt, EOF-Handling, Sättigungsklammern, Traum-Wetter.
# Neu: Eingabe-Limit nur für echte Aktionen, Enter wird nicht gezählt; Abschluss bei Sättigung 0.
# Fix Teil 26: traum_ereignis gibt immer Tupel zurück, main() komplett, kleine Polierarbeiten.

import random
import time
import sys

USE_ANSI = sys.stdout.isatty()
MAX_EINGABEN = 20


def pause(sekunden: float) -> None:
    """Macht eine Pause, im Nicht-TTY-Modus fast verzögerungsfrei."""
    if USE_ANSI:
        time.sleep(sekunden)
    else:
        time.sleep(min(sekunden, 0.02))


def satte_pruefung(wert: int) -> bool:
    """Prüft, ob der Magen leerer als 20 % ist."""
    return wert < 20


def clear_screen(schritt: int = None) -> None:
    """Löscht Terminal bei TTY oder druckt Trennzeile."""
    if USE_ANSI:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
    else:
        if schritt is not None:
            print(f"\n--- Schritt {schritt} ---")
        else:
            print()


def draw_bar(wert: int, breite: int = 24, waerme: int = 0) -> str:
    """Baut einen farbigen Balken für die Sättigung, gelber Rand bei Wärme."""
    voll = int((wert / 100) * breite)
    leer = breite - voll
    if USE_ANSI:
        if wert >= 75:
            farbe = "\033[92m"      # Grün
        elif wert >= 45:
            farbe = "\033[93m"      # Gelb
        elif wert >= 20:
            farbe = "\033[38;5;208m" # Orange
        else:
            farbe = "\033[91m"      # Rot
        
        rand = "\033[93m" if waerme > 0 else "\033[0m"
        reset = "\033[0m"
        return f"{rand}[{reset}{farbe}{'#' * voll}{'.' * leer}{rand}]{reset} {wert:3d}%"
    return f"[{'#' * voll}{'.' * leer}] {wert:3d}%"


def draw_stomach(wert: int, knurrt: bool, waerme: int = 0, schritt: int = 0) -> str:
    """Zeichnet den ASCII-Magen mit Füllung, Knurren und animiertem Dampf bei Wärme."""
    level = max(0, min(5, int(wert / 20)))
    wave = "~~~"
    
    if waerme > 0:
        if (schritt // 2) % 2 == 0:
            header = "    ( ~ )"
        else:
            header = "   ( ~ ) "
    elif wert >= 50:
        header = "    ( ~ )"
    elif knurrt:
        header = "   *GRRRR*"
    else:
        header = "           "
    
    magen_farbe = "\033[38;5;208m" if (waerme > 0 and USE_ANSI) else ""
    reset = "\033[0m" if USE_ANSI else ""
    
    lines = [
        "  \\       //",
        "   \\     //",
        "    \\   //",
        "     \\ //",
        "      \\//",
        "       V"
    ]
    fill_start = 5 - level
    result = [header]
    
    for i, line in enumerate(lines):
        # Füllung zeichnen
        if i >= fill_start and level > 0 and i < 5:
            left = line.find('\\')
            right = line.find('//')
            if left != -1 and right != -1 and right > left:
                mid = line[left+2:right]
                filled = (wave * (len(mid) // 3 + 1))[:len(mid)]
                line = line[:left+2] + filled + line[right:]
        # Farbe anwenden
        if magen_farbe and waerme > 0:
            line = line.replace('\\', magen_farbe + '\\' + reset).replace('//', magen_farbe + '//' + reset).replace('V', magen_farbe + 'V' + reset)
        result.append(line)
    return "\n".join(result)


def draw_dodo(wert: int, schritt: int, waerme: int = 0) -> str:
    """Zeigt das Dodo-Gesicht mit Federkamm, Blinzeln und Wärmelächeln."""
    blinzelt = (schritt % 10) == 0
    augen = "-.- " if blinzelt else "o.o "
    
    if waerme > 0:
        mund = "^_^"
        notiz = " (Warm & kuschelig)"
    elif wert < 20:
        mund = ">_<"
        notiz = " (Magen knurrt!)"
    elif wert < 50:
        mund = "._."
        notiz = " (Könnte 'ne Beere vertragen)"
    else:
        mund = "^_^"
        notiz = " (Pummelig & warm)"
    return f"""   /\\/\\
   {augen}
   ({mund}){notiz}"""


def print_zertifikat(stats: dict, dauer: float) -> None:
    """Druckt ein kleines Abschluss-Zertifikat im Traum-Stil."""
    clear_screen()
    name = "Fifo der Dodo"
    print("╔══════════════════════════════════════════════════════╗")
    print("║        🦤 TRAUM-URKUNDE MAGENWÄRMER 🦤        ║")
    print("╠═══════════════════════════════════════════════╣")
    print(f"║ Träumer: {name:<30} ║")
    print(f"║ Traumuhr: {dauer:>5.1f} Sek{' ' * 23}║")
    print("╠═══════════════════════════════════════════════╣")
    print(f"║ Beeren genascht:     {stats['beeren']:>3}                     ║")
    print(f"║ Tassen Tee getrunken: {stats['tee']:>3}                    ║")
    print(f"║ Traum-Ereignisse:     {stats.get('events', 0):>3}                    ║")
    print(f"║ Magenknurren gehört: {stats['knurren']:>3}                    ║")
    print(f"║ Höchste Sättigung:   {stats['max_sat']:>3}%                    ║")
    print(f"║ Tiefste Sättigung:   {stats['min_sat']:>3}%                    ║")
    print("╠═══════════════════════════════════════════════╣")
    # Bewertung
    if stats['knurren'] == 0 and stats['min_sat'] > 50:
        grad = "🌟 MEISTER DES SCHLAFES 🌟"
    elif stats['knurren'] < 3:
        grad = "🌙 Guter Traumwächter"
    else:
        grad = "💤 Unruhiger Schläfer"
    print(f"║ {grad:<38} ║")
    print("╚═══════════════════════════════════════════════╝")
    print("\nDodo kuschelt sich ins Nest. Bis bald!\n")


def traum_ereignis(stats: dict) -> tuple[int, int, str]:
    """Würfelt ein Traum-Ereignis. Gibt (delta_sat, delta_waerme, nachricht)."""
    if random.random() < 0.15:  # 15% Chance pro Schritt
        stats['events'] = stats.get('events', 0) + 1
        r = random.random()
        if r < 0.4:
            return (10, 0, "✨ Traum-Beere gefunden! +10% Sättigung")
        elif r < 0.7:
            return (0, 3, "🍵 Dampfender Traum-Tee erscheint! +3 Wärme")
        elif r < 0.9:
            return (-5, 0, "👻 Albtraum! Magen zieht sich zusammen -5%")
        else:
            return (5, 2, "🌈 Goldener Traum: +5% Sättigung, +2 Wärme")
    return (0, 0, "")


def main() -> None:
    """Hauptprogramm: Dodo-Magenwärmer Traum-Schleife."""
    sat = 80          # Start-Sättigung
    waerme = 0        # Wärme-Level (0-10)
    schritt = 0       # Schrittzähler
    eingaben = 0      # Echte Aktionen (1,2), Enter nicht gezählt
    stats = {
        'beeren': 0,
        'tee': 0,
        'knurren': 0,
        'max_sat': sat,
        'min_sat': sat,
        'events': 0
    }
    startzeit = time.time()
    
    clear_screen()
    print("🦤 Dodo-Magenwärmer — Traum-Edition 🦤")
    print("Drücke 1 für Beere, 2 für Tee, Enter für Weiterträumen, q zum Aufwachen.")
    pause(1.5)
    
    while True:
        schritt += 1
        
        # Sättigung sinkt langsam
        sat = max(0, sat - random.randint(1, 3))
        # Wärme baut ab
        if waerme > 0:
            waerme = max(0, waerme - 1)
        
        # Traum-Ereignis würfeln
        delta_sat, delta_waerme, msg = traum_ereignis(stats)
        sat = max(0, min(100, sat + delta_sat))
        waerme = min(10, waerme + delta_waerme)
        
        # Statistik aktualisieren
        stats['max_sat'] = max(stats['max_sat'], sat)
        stats['min_sat'] = min(stats['min_sat'], sat)
        
        # Knurren prüfen
        knurrt = satte_pruefung(sat)
        if knurrt:
            stats['knurren'] += 1
        
        # Bildschirm zeichnen
        clear_screen(schritt)
        print(draw_dodo(sat, schritt, waerme))
        print()
        print(draw_stomach(sat, knurrt, waerme, schritt))
        print()
        print(f"Sättigung: {draw_bar(sat, waerme=waerme)}")
        print(f"Wärme: {waerme}/10")
        print(f"Schritt {schritt} | Eingaben {eingaben}/{MAX_EINGABEN}")
        
        if msg:
            print(f"{msg}")
        
        print("----------------------------------------")
        
        # Ende-Bedingungen
        if sat <= 0:
            print("💤 Magen ganz leer... Dodo wacht sanft auf.")
            break
        if eingaben >= MAX_EINGABEN:
            print("🌙 Traumzeit vorbei. Dodo streckt die Flügel.")
            break
        
        # Eingabe
        try:
            cmd = input("Deine Wahl (1/2/Enter/q): ").strip().lower()
        except EOFError:
            print("\n🌙 Eingabe-Ende. Dodo schläft weiter.")
            break
        
        if cmd == 'q':
            print("👋 Dodo wacht auf. Bis zum nächsten Traum!")
            break
        elif cmd == '1':
            sat = min(100, sat + 15)
            waerme = min(10, waerme + 1)
            stats['beeren'] += 1
            eingaben += 1
            print("🍓 Beere genascht! +15% Sättigung, +1 Wärme")
        elif cmd == '2':
            sat = min(100, sat + 5)
            waerme = min(10, waerme + 3)
            stats['tee'] += 1
            eingaben += 1
            print("🍵 Tee getrunken! +5% Sättigung, +3 Wärme")
        elif cmd == '':
            # Enter = nur weitertickern, nicht zählen
            pass
        else:
            print("❓ Unbekannter Befehl.")
        
        pause(0.3)
    
    # Abschluss
    dauer = time.time() - startzeit
    print_zertifikat(stats, dauer)


if __name__ == "__main__":
    main()