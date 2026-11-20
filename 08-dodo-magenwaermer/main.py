# main.py - Dodo-Magenwärmer Teil 19 (Final+++)
# Fifo der Dodo träumt den Code zu Ende: Hauptschleife, Input, Stats, Zertifikat.
# Fix: Wärme-Abbau mit Bonus, Eingabe-Handling (1/2/Enter/q/EOF), Sättigungs-Clamping, sauberes Ende.

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
        if i >= fill_start and level > 0 and i < 5:
            left = line.find('\\')
            right = line.find('//')
            if left != -1 and right != -1 and right > left:
                mid = line[left+1:right]
                filled = (wave * (len(mid) // 3 + 1))[:len(mid)]
                line = line[:left+1] + filled + line[right:]
        if magen_farbe and waerme > 0:
             line = line.replace('\\', magen_farbe + '\\' + reset).replace('//', magen_farbe + '//' + reset).replace('V', magen_farbe + 'V' + reset)
        result.append(line)
    return "\n".join(result)

def draw_dodo(wert: int, schritt: int) -> str:
    """Zeigt das Dodo-Gesicht mit Federkamm und Blinzeln."""
    blinzelt = (schritt % 10) == 0
    augen = "-.- " if blinzelt else "o.o "
    if wert < 20:
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
    print("╔══════════════════════════════════════════════════╗")
    print("║        🦤 TRAUM-URKUNDE MAGENWÄRMER 🦤        ║")
    print("╠═══════════════════════════════════════════════╣")
    print(f"║ Träumer: {name:<30} ║")
    print(f"║ Traumuhr: {dauer:>5.1f} Sek{' ' * 23}║")
    print("╠═══════════════════════════════════════════════╣")
    print(f"║ Beeren genascht:     {stats['beeren']:>3}                     ║")
    print(f"║ Tassen Tee getrunken: {stats['tee']:>3}                    ║")
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

def main() -> None:
    saettigung = 100
    schritt = 0
    eingaben_zaehler = 0
    fuetterungen = 0
    waerme = 0          # Wärme durch Tee (Schritte)
    start_time = time.time()
    
    # Statistik für Zertifikat
    stats = {
        'beeren': 0,
        'tee': 0,
        'knurren': 0,
        'max_sat': 100,
        'min_sat': 100
    }
    
    print("🦤 Dodo-Magenwärmer erwacht im Traum... (q = Ende)")
    pause(0.8)
    
    while saettigung > 0 and eingaben_zaehler < MAX_EINGABEN:
        schritt += 1
        clear_screen(schritt)
        
        # Natürlicher Hungeranstieg pro Zeiteinheit
        saettigung = max(0, saettigung - random.randint(3, 8))
        knurrt = satte_pruefung(saettigung)
        
        # Stats aktualisieren
        stats['max_sat'] = max(stats['max_sat'], saettigung)
        stats['min_sat'] = min(stats['min_sat'], saettigung)
        if knurrt:
            stats['knurren'] += 1
        
        # Wärme abbauen & Effekt (Bonus-Sättigung wenn warm)
        if waerme > 0:
            waerme -= 1
            saettigung = min(100, saettigung + 2)  # Wärme wärmt weiter
        
        # Anzeige
        print(draw_stomach(saettigung, knurrt, waerme, schritt))
        print(f"Sättigung: {draw_bar(saettigung, waerme=waerme)}")
        if waerme > 0:
            print(f"   ♨ Wärme noch {waerme} Schritt(e)")
        print(draw_dodo(saettigung, schritt))
        print()
        
        # Eingabe
        try:
            prompt = "[1] Beere  [2] Tee  [Enter] Weiterträumen  [q] Aufwachen > "
            eingabe = input(prompt).strip().lower()
        except EOFError:
            print("\n🌙 Traumeingang geschlossen. Dodo wacht sanft auf.")
            break
        
        eingaben_zaehler += 1
        
        if eingabe == 'q':
            print("\n👋 Dodo zwinkert und wacht auf. Bis zum nächsten Traum!")
            break
        elif eingabe == '1':
            # Beere: +15-25%
            menge = random.randint(15, 25)
            saettigung = min(100, saettigung + menge)
            stats['beeren'] += 1
            fuetterungen += 1
            print(f"🍇 Beere genascht! +{menge}% Sättigung.")
            pause(0.5)
        elif eingabe == '2':
            # Tee: Wärme für 3 Schritte
            waerme = 3
            stats['tee'] += 1
            print("🍵 Tee getrunken. Wärmt den Magen für 3 Schritte.")
            pause(0.5)
        elif eingabe == '':
            # Enter: nur träumen
            print("💤 Dodo träumt weiter...")
            pause(0.3)
        else:
            print(f"❓ Dodo versteht '{eingabe}' nicht. Versuche 1, 2, Enter oder q.")
            pause(0.5)
    
    # Ende der Schleife
    dauer = time.time() - start_time
    print_zertifikat(stats, dauer)

if __name__ == "__main__":
    main()