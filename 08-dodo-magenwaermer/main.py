# main.py - Dodo-Magenwärmer Teil 23 (Traum-Edition)
# Fifo der Dodo träumt weiter: Hauptschleife fertiggestellt, sanftes Aufwachen, Statistik robust.
# Fix: Unvollständige main() vervollständigt, EOF-Handling, Sättigungsklammern, Traum-Wetter.

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
                mid = line[left+2:right] # skip escaped backslash
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
    print("╔════════════════════════════════════════════════════╗")
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
    schritt = 0
    eingaben_zaehler = 0
    waerme = 0          # Wärme durch Tee (Schritte)
    start = time.time()
    
    stats = {
        'beeren': 0,
        'tee': 0,
        'knurren': 0,
        'max_sat': 100,
        'min_sat': 100,
        'events': 0
    }
    
    nachricht = "💤 Traum beginnt..."
    
    while eingaben_zaehler < MAX_EINGABEN and saettigung > 0:
        schritt += 1
        
        # Natürlicher Verbrauch
        saettigung -= 1
        if waerme > 0:
            waerme -= 1
        
        # Traum-Ereignis
        delta_sat, delta_waerme, event_msg = traum_ereignis(stats)
        if event_msg:
            nachricht = event_msg
        saettigung += delta_sat
        waerme += delta_waerme
        
        # Klammern
        saettigung = max(0, min(100, saettigung))
        
        # Stats aktualisieren
        stats['max_sat'] = max(stats['max_sat'], saettigung)
        stats['min_sat'] = min(stats['min_sat'], saettigung)
        
        # Knurren prüfen
        knurrt = satte_pruefung(saettigung)
        if knurrt:
            stats['knurren'] += 1
        
        # Zeichnen
        clear_screen(schritt)
        print(draw_bar(saettigung, waerme=waerme))
        print(draw_stomach(saettigung, knurrt, waerme, schritt))
        print(draw_dodo(saettigung, schritt, waerme))
        print(f"\nSättigung: {saettigung}%  |  Wärme: {waerme} Schritte  |  Schritt {schritt}  |  Eingaben {eingaben_zaehler}/{MAX_EINGABEN}")
        if nachricht:
            print(f"{nachricht}")
        print("----------------------------------------")
        print("[1] Beere essen  [2] Tee trinken  [Enter] Träumen  [q] Aufwachen")
        
        try:
            eingabe = input("> ").strip().lower()
        except EOFError:
            print("\n🌙 Eingabe-Schluss. Dodo wacht sanft auf.")
            break
        
        nachricht = "" # Nachricht nur einmal anzeigen
        
        if eingabe == 'q':
            print("🌅 Dodo streckt die Flügel. Aufwachen!")
            break
        elif eingabe == '1':
            saettigung = min(100, saettigung + 15)
            stats['beeren'] += 1
            nachricht = "🍇 Mmmh, saftige Traum-Beere! +15%"
            eingaben_zaehler += 1
        elif eingabe == '2':
            waerme += 4
            stats['tee'] += 1
            nachricht = "🍵 Heißer Tee wärmt den Bauch. +4 Wärme"
            eingaben_zaehler += 1
        elif eingabe == '':
            nachricht = "💭 Dodo träumt weiter..."
            # Enter zählt nicht als 'Eingabe' für Zähler, aber Schritt vergeht
        else:
            nachricht = "❓ Dodo versteht nur 1, 2, Enter oder q."
            # Kein Zähler-Inkrement bei Falscheingabe
            continue # Schritt nicht zählen? Nein, Schritt schon passiert. Nur Input-Zähler nicht.
            
        pause(0.3)
    
    # Ende-Schleife (Sättigung 0 oder Max Eingaben)
    if saettigung <= 0:
        clear_screen()
        print(draw_stomach(0, True, 0, schritt))
        print(draw_dodo(0, schritt, 0))
        print("\n💥 Der Magen ist ganz leer! Dodo wacht hungrig auf.\n")
        pause(1)
    
    dauer = time.time() - start
    print_zertifikat(stats, dauer)


if __name__ == "__main__":
    main()