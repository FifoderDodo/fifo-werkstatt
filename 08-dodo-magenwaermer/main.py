# main.py - Dodo-Magenwärmer Teil 25 (Traum-Edition)
# Fifo der Dodo träumt weiter: Hauptschleife fertiggestellt, sanftes Aufwachen, Statistik robust.
# Fix: Unvollständige main() vervollständigt, EOF-Handling, Sättigungsklammern, Traum-Wetter.
# Neu: Eingabe-Limit nur für echte Aktionen, Enter wird nicht gezählt; Abschluss bei Sättigung 0.

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
    print("╔═════════════════════════════════════════════════════╗")
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
    saettigung = 100
    waerme = 0
    schritt = 0
    eingaben = 0
    startzeit = time.time()
    
    stats = {
        'beeren': 0,
        'tee': 0,
        'knurren': 0,
        'max_sat': 100,
        'min_sat': 100,
        'events': 0
    }
    
    clear_screen()
    print("🦤 Dodo-Magenwärmer — Träum weiter, Fifo…\n")
    pause(1.0)
    
    while eingaben < MAX_EINGABEN and saettigung > 0:
        schritt += 1
        
        # Natürlicher Sättigungsverlust
        saettigung -= random.randint(1, 3)
        saettigung = max(0, saettigung)
        
        # Wärme nimmt langsam ab
        if waerme > 0:
            waerme -= 1
        
        # Traum-Ereignis
        delta_sat, delta_waerme, msg = traum_ereignis(stats)
        saettigung = max(0, min(100, saettigung + delta_sat))
        waerme = max(0, waerme + delta_waerme)
        
        # Stats aktualisieren
        stats['max_sat'] = max(stats['max_sat'], saettigung)
        stats['min_sat'] = min(stats['min_sat'], saettigung)
        knurrt = satte_pruefung(saettigung)
        if knurrt:
            stats['knurren'] += 1
        
        # Bildschirm zeichnen
        clear_screen(schritt)
        print(draw_dodo(saettigung, schritt, waerme))
        print()
        print(draw_stomach(saettigung, knurrt, waerme, schritt))
        print()
        print(f"Sättigung: {draw_bar(saettigung, waerme=waerme)}")
        print(f"Wärme:     {waerme}")
        print(f"Schritt {schritt} | Eingaben {eingaben}/{MAX_EINGABEN}")
        if msg:
            print(f"\n{msg}")
        print("----------------------------------------")
        print("[1] Beere essen  [2] Tee trinken  [Enter] Weiter  [q] Aufwachen")
        
        # Eingabe
        try:
            choice = input("> ").strip().lower()
        except EOFError:
            print("\n🌙 Traum endet sanft (EOF).")
            break
        
        if choice == '1':
            saettigung = min(100, saettigung + 15)
            stats['beeren'] += 1
            eingaben += 1
        elif choice == '2':
            waerme += 5
            stats['tee'] += 1
            eingaben += 1
        elif choice == 'q':
            print("\n🌅 Fifo wacht auf…")
            break
        elif choice == '':
            # Enter wird nicht gezählt
            pass
        else:
            print("❓ Unbekannter Befehl.")
            pause(0.5)
        
        pause(0.2)
    
    # Ende
    dauer = time.time() - startzeit
    print_zertifikat(stats, dauer)


if __name__ == "__main__":
    main()