# main.py - Dodo-Magenwärmer Teil 12
# Fifo der Dodo bastelt weiter im Traum.
# Fix: Abgebrochener Code am Ende repariert (Syntaxfehler 'p').
# Neu: Dampf-Animation wechselt Rahmen bei Wärme, Traum-Ende mit Statistik,
#      Entry-Point hinzugefügt, kleine Farb-Akzente für warmen Magen.

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
        
        # Wärme-Rahmen für den Balken
        rand = "\033[93m" if waerme > 0 else "\033[0m"
        reset = "\033[0m"
        return f"{rand}[{reset}{farbe}{'#' * voll}{'.' * leer}{rand}]{reset} {wert:3d}%"
    return f"[{'#' * voll}{'.' * leer}] {wert:3d}%"

def draw_stomach(wert: int, knurrt: bool, waerme: int = 0, schritt: int = 0) -> str:
    """Zeichnet den ASCII-Magen mit Füllung, Knurren und animiertem Dampf bei Wärme."""
    level = max(0, min(5, int(wert / 20)))
    wave = "~~~"
    
    # Dampf-Animation: zwei Rahmen wechseln sich ab
    dampf_rahmen = ["    ( ~ )", "    ( ~ )"] # Basis
    if waerme > 0:
        # Leichtes Wackeln beim Dampf
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
    
    # Magen-Farbe bei Wärme
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
        # Farbe nur auf die Magenwand anwenden, nicht auf Füllung
        if magen_farbe and waerme > 0:
             # Einfaches Einfärben der Strukturzeichen
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
    return f"   /\\/\\\n   {augen}\n   ({mund}){notiz}"

def main() -> None:
    saettigung = 100
    schritt = 0
    eingaben_zaehler = 0
    fuetterungen = 0
    waerme = 0          # Wärme durch Tee (Schritte)
    start_time = time.time()
    
    print("🦤 Dodo-Magenwärmer erwacht im Traum... (q = Ende)")
    pause(0.8)
    
    while saettigung > 0 and eingaben_zaehler < MAX_EINGABEN:
        schritt += 1
        clear_screen(schritt)
        
        # Natürlicher Hungeranstieg pro Zeiteinheit
        saettigung = max(0, saettigung - random.randint(3, 8))
        knurrt = satte_pruefung(saettigung)
        
        # Wärme abbauen
        if waerme > 0:
            waerme -= 1
        
        # Magen, Balken und Dodo anzeigen
        print(draw_stomach(saettigung, knurrt, waerme, schritt))
        print(draw_bar(saettigung, waerme=waerme))
        print(draw_dodo(saettigung, schritt))
        
        # Statuszeile mit Wärme-Anzeige
        waerme_str = f" | Wärme: {waerme}" if waerme > 0 else ""
        print(f"\nSchritt: {schritt} | Eingaben: {eingaben_zaehler}/{MAX_EINGABEN} | Fütterungen: {fuetterungen}{waerme_str}")
        
        if knurrt:
            if USE_ANSI:
                sys.stdout.write("\a")
                sys.stdout.flush()
            print("\n⚠️  *KNURR!* Dodo braucht Futter!")
            print("[1/f] Beere (+20%) | [2] Magenwärmer-Tee (+40%) | [Enter] Snacken | [q] Ende")
        else:
            print("\n[1] Beere naschen | [2] Warmer Kräutertee | [Enter] Weiterträumen | [q] Ende")
        
        try:
            eingabe = input("> ").strip().lower()
            eingaben_zaehler += 1
        except EOFError:
            print("\nTraum verblasst leise. Schlaf gut, kleiner Dodo.")
            break
            
        if eingabe in ('q', 'quit', 'exit', 'ende'):
            print("Dodo kuschelt sich ins Nest. Bis bald!")
            break
        elif eingabe in ('1', 'b', 'beere', 'ja', 'j', 'f', 'füttern') or (knurrt and eingabe == ''):
            gewinn = random.randint(18, 26)
            saettigung = min(100, saettigung + gewinn)
            fuetterungen += 1
            print(f"🫐 Saftige Waldbeere verputzt! (+{gewinn}%)")
            pause(0.4)
        elif eingabe in ('2', 'tee', 'magenwärmer', 'warm'):
            gewinn = random.randint(35, 45)
            saettigung = min(100, saettigung + gewinn)
            fuetterungen += 1
            waerme = 3                     # Tee wärmt für 3 Schritte
            print(f"🍵 Warmer Dodo-Kräutertee geschlürft! Magen wird mollig warm. (+{gewinn}%)")
            pause(0.4)
        elif eingabe in ('', 'w', 'weiter', 'nein', 'n'):
            # Weiterträumen ohne Füttern
            pass
        else:
            # Unbekannte Kost: Probierbiss
            print(f"Dodo beäugt '{eingabe}' skeptisch und knabbert kurz daran...")
            saettigung = min(100, saettigung + 5)
            pause(0.3)
    
    # Traum-Ende
    clear_screen()
    dauer = time.time() - start_time
    print("🦤 Der Traum neigt sich dem Ende zu...")
    pause(0.5)
    print(f"\nEndstand nach {schritt} Schritten ({dauer:.1f}s):")
    print(f"  Sättigung: {saettigung}%")
    print(f"  Fütterungen: {fuetterungen}")
    print(f"  Eingaben: {eingaben_zaehler}/{MAX_EINGABEN}")
    if saettigung <= 0:
        print("  Dodo ist vor Hunger aufgewacht... nächstes Mal mehr Beeren!")
    elif eingaben_zaehler >= MAX_EINGABEN:
        print("  Maximale Träumereien erreicht. Dodo schläft satt weiter.")
    else:
        print("  Dodo wacht glücklich auf. Guter Traum!")
    print("\nGute Nacht! 🌙")

if __name__ == "__main__":
    main()