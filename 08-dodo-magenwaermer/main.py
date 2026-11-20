# main.py - Dodo-Magenwärmer Teil 10
# Fifo der Dodo bastelt weiter im Traum.
# Neu: Fütterungslogik entwirrt (Enter füttert nur bei Hunger automatisch),
# Menü für Beeren & Magenwärmer-Tee (Zahlen 1/2, ja/f), Dampf- & Knurranzeige am Magen.

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

def draw_bar(wert: int, breite: int = 24) -> str:
    """Baut einen farbigen Balken für die Sättigung."""
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
        reset = "\033[0m"
        return f"{farbe}[{'#' * voll}{'.' * leer}]{reset} {wert:3d}%"
    return f"[{'#' * voll}{'.' * leer}] {wert:3d}%"

def draw_stomach(wert: int, knurrt: bool) -> str:
    """Zeichnet den ASCII-Magen mit Füllung und Knurr-/Dampfeffekten."""
    level = max(0, min(5, int(wert / 20)))
    wave = "~~~"
    
    # Dampf bei Wärme/Sättigung oder Knurrgeräusch
    header = "      ( ~ )" if wert >= 50 else ("   *GRRRR*" if knurrt else "           ")
    
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
    start_time = time.time()
    
    print("🦤 Dodo-Magenwärmer erwacht im Traum... (q = Ende)")
    pause(0.8)
    
    while saettigung > 0 and eingaben_zaehler < MAX_EINGABEN:
        schritt += 1
        clear_screen(schritt)
        
        # Natürlicher Hungeranstieg pro Zeiteinheit
        saettigung = max(0, saettigung - random.randint(3, 8))
        knurrt = satte_pruefung(saettigung)
        
        # Magen, Balken und Dodo anzeigen
        print(draw_stomach(saettigung, knurrt))
        print(draw_bar(saettigung))
        print(draw_dodo(saettigung, schritt))
        print(f"\nSchritt: {schritt} | Eingaben: {eingaben_zaehler}/{MAX_EINGABEN} | Fütterungen: {fuetterungen}")
        
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
            
        pause(0.2)
        
    dauer = time.time() - start_time
    clear_screen()
    if saettigung <= 0:
        print(draw_stomach(0, True))
        print("\n💀 Der Magen ist gänzlich leergefegt. Fifo schlummert ein.")
    else:
        print(draw_dodo(saettigung, schritt))
        print("\n🦤 Dodo watschelt wohlig gewärmt durch den Morgentau.")
        
    print("\n--- Dodo-Schlafstatistik ---")
    print(f"Gelebte Schritte:    {schritt}")
    print(f"Traum-Eingaben:      {eingaben_zaehler}")
    print(f"Mahlzeiten gewärmt:  {fuetterungen}")
    print(f"End-Magenfüllung:    {saettigung}%")
    print(f"Dauer im Traum:      {dauer:.1f} s")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nSanft aufgewacht aus dem Traum.")