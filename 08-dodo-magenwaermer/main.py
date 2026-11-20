import random
import time
import sys
import math

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


def ease_out_cubic(t: float) -> float:
    """Kubisches Auslaufen: t in [0,1] -> weicher Stopp."""
    return 1 - pow(1 - t, 3)


def ease_in_out_quad(t: float) -> float:
    """Quadratisches Ein/Aus: sanftes Anfahren und Abbremsen."""
    return 2 * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 2) / 2


def draw_feder(saettigung: int, schritt: int) -> str:
    """Zeichnet eine kleine leuchtende Feder als Sättigungs-Indikator.
    Farbe: Grün(>75) -> Gelb(>45) -> Orange(>20) -> Rot(>5) -> Grau(<=5).
    Nutzt Bézier-Easing für Pulsieren (Skalierung), horizontales Wackeln und Neigungs-Charakter."""
    # Farbstufen & Basis-Zeichen
    if USE_ANSI:
        if saettigung > 75:
            farbe = "\033[92m"      # Hellgrün
            base_char = "❈"
            bend_chars = ["❈", "✦", "✧"] # Leicht gebogen
        elif saettigung > 45:
            farbe = "\033[93m"      # Gelb
            base_char = "✦"
            bend_chars = ["✦", "✧", "❈"]
        elif saettigung > 20:
            farbe = "\033[38;5;208m" # Orange
            base_char = "✧"
            bend_chars = ["✧", "❈", "✦"]
        elif saettigung > 5:
            farbe = "\033[91m"      # Rot
            base_char = "✦"
            bend_chars = ["✦", "·", "·"]
        else:
            farbe = "\033[90m"      # Dunkelgrau
            base_char = "·"
            bend_chars = ["·", " ", " "]
        reset = "\033[0m"
        
        # Animations-Zyklus (0.0 - 1.0)
        # Unterschiedliche Frequenzen für organischen Look
        cycle_puls = (schritt * 0.07) % 1.0       # Langsam pulsieren
        cycle_wackel = (schritt * 0.13) % 1.0     # Wackeln
        cycle_bend = (schritt * 0.11) % 1.0       # Neigung
        
        # 1. Pulsieren (Skalierung 1.0 -> 1.5 -> 1.0)
        # Easing für weiches Aufblähen
        p = ease_in_out_quad(cycle_puls)
        scale = 1 + 0.5 * p # 1.0 bis 1.5
        # Da wir nur diskrete Zeichen haben: 1 Zeichen oder 2 Zeichen
        show_double = scale > 1.25
        
        # 2. Horizontales Wackeln (Offset 0 oder 1 Leerzeichen)
        # Nur bei niedriger Sättigung stark, sonst subtil
        wackel_amp = 1.0 if saettigung < 20 else (0.3 if saettigung < 50 else 0.0)
        w = ease_out_cubic(cycle_wackel) * wackel_amp
        wackel_str = " " if w > 0.5 else ""
        
        # 3. Neigung (Zeichenwechsel simuliert Biegung)
        b = ease_in_out_quad(cycle_bend)
        bend_idx = int(b * (len(bend_chars) - 1))
        char = bend_chars[bend_idx]
        
        # Zusammenbau
        if show_double and saettigung > 5:
            return f"{wackel_str}{farbe}{char}{char}{reset}"
        return f"{wackel_str}{farbe}{char}{reset}"
    else:
        # Fallback ASCII
        if saettigung > 75: return ">"
        if saettigung > 45: return "-~"
        if saettigung > 20: return "~"
        if saettigung > 5:  return "!"
        return "."


def draw_bar(wert: int, breite: int = 24, waerme: int = 0) -> str:
    """Baut einen farbigen Balken für die Sättigung, gelber Rand bei Wärme."""
    voll = int((wert / 100) * breite)
    leer = breite - voll
    if USE_ANSI:
        if wert >= 75:
            farbe = "\033[92m"
        elif wert >= 45:
            farbe = "\033[93m"
        elif wert >= 20:
            farbe = "\033[38;5;208m"
        else:
            farbe = "\033[91m"
        rand = "\033[93m" if waerme > 0 else "\033[0m"
        reset = "\033[0m"
        return f"{rand}[{reset}{farbe}{'#' * voll}{'.' * leer}{rand}]{reset} {wert:3d}%"
    return f"[{'#' * voll}{'.' * leer}] {wert:3d}%"


def draw_waerme_bar(waerme: int, max_waerme: int = 10, breite: int = 12) -> str:
    """Visualisiert den Wärme-Level als kleinen Balken."""
    if max_waerme <= 0:
        return ""
    voll = int((waerme / max_waerme) * breite)
    leer = breite - voll
    if USE_ANSI:
        farbe = "\033[93m"
        reset = "\033[0m"
        return f"{farbe}[{'#' * voll}{'.' * leer}]{reset} {waerme}/{max_waerme}"
    return f"[{'#' * voll}{'.' * leer}] {waerme}/{max_waerme}"


def draw_stomach(wert: int, knurrt: bool, waerme: int = 0, schritt: int = 0) -> str:
    """Zeichnet den ASCII-Magen mit Füllung, Knurren, animiertem Dampf, Peristaltik und Wellen."""
    level = max(0, min(5, int(wert / 20)))
    wave_chars = "~~~"
    
    # 1. Header Animation (Dampf / Knurren / Zufrieden)
    if waerme > 0:
        # Dampf blubbert nach links/rechts
        if (schritt // 2) % 2 == 0:
            header = "    ( ~ )"
        else:
            header = "   ( ~ ) "
    elif wert >= 50:
        # Zufriedenes Glucksen (leichtes Wackeln)
        if (schritt // 3) % 2 == 0:
            header = "    ( ~ )"
        else:
            header = "    (~ ) "
    elif knurrt:
        # Knurren schüttelt den Magen
        if (schritt // 1) % 2 == 0:
            header = "  * GRRR *"
        else:
            header = " * GRRRR *"
    else:
        header = "           "
    
    magen_farbe = "\033[38;5;208m" if (waerme > 0 and USE_ANSI) else ""
    reset = "\033[0m" if USE_ANSI else ""
    
    # Basis-Linien des Magens
    base_lines = [
        "  \\       //",
        "   \\     //",
        "    \\   //",
        "     \\ //",
        "      \\//",
        "       V"
    ]
    
    # 2. Peristaltik / Atmung: Horizontales Wackeln der Wände
    # Stärke hängt von Sättigung ab (voller Magen bewegt sich weniger stark, aber sichtbar)
    # Frequenz langsamer als Feder
    breath_cycle = (schritt * 0.05) % 1.0
    breath_intensity = ease_in_out_quad(breath_cycle) # 0.0 -> 1.0 -> 0.0
    # Max Offset 1 Zeichen links/rechts
    wall_offset = int(round((breath_intensity - 0.5) * 0.8)) # -0.4 bis 0.4 -> gerundet -0, 0, 0, 1... besser: sinus
    # Einfacher Sinus für Wackeln:
    wall_wobble = int(round(math.sin(schritt * 0.3) * 0.5)) # -1, 0, 1
    
    # 3. Füllstands-Wellen Animation
    wave_offset = (schritt * 2) % len(wave_chars) # Scrollt die Welle
    
    fill_start = 5 - level
    result = [header]
    
    for i, line in enumerate(base_lines):
        # Wende Wand-Wackeln an (Einrückung ändern)
        # Wir manipulieren den String: führende Leerzeichen +/- wall_wobble
        # Aber Vorsicht: Zeichenbreite. Einfacher: Prefix Leerzeichen anpassen.
        # Die Linien haben unterschiedliche Einrückung. Wir parsen den Prefix.
        stripped = line.lstrip()
        prefix_len = len(line) - len(stripped)
        new_prefix_len = max(0, prefix_len + wall_wobble)
        animated_line = " " * new_prefix_len + stripped
        
        # Füllung zeichnen
        if i >= fill_start and level > 0 and i < 5: # Nur die 5 Schalen-Linien, nicht die Spitze V
            # Finde die inneren Grenzen \ und //
            # In animated_line sind die Backslashes evtl. verschoben.
            left = animated_line.find('\\')
            right = animated_line.find('//')
            
            if left != -1 and right != -1 and right > left:
                mid_content = animated_line[left+2:right]
                # Animierte Welle generieren
                filled = ""
                for k in range(len(mid_content)):
                    idx = (k + wave_offset) % len(wave_chars)
                    filled += wave_chars[idx]
                
                line = animated_line[:left+2] + filled + animated_line[right:]
            else:
                line = animated_line
        else:
            line = animated_line
            
        result.append(line)
    
    return f"{magen_farbe}{'\n'.join(result)}{reset}"


def main() -> None:
    """Hauptschleife: Dodo-Magenwärmer Simulation."""
    saettigung = 50
    waerme = 0
    schritt = 0
    eingaben = 0
    
    print("🦤 Dodo-Magenwärmer v0.46 gestartet. Strg+C oder 'q' zum Beenden.")
    pause(0.5)
    
    while eingaben < MAX_EINGABEN:
        schritt += 1
        clear_screen(schritt)
        
        # Simulation: Verdauung & Abkühlung
        saettigung = max(0, saettigung - random.randint(0, 2))
        if waerme > 0:
            waerme = max(0, waerme - 1)
        
        # Zufälliges Knurren bei Hunger
        knurrt = saettigung < 30 and random.random() < 0.3
        
        # Anzeige
        print(f"Schritt: {schritt}/20")
        print(f"Sättigung: {draw_bar(saettigung, waerme=waerme)}")
        print(f"Feder:     {draw_feder(saettigung, schritt)}")
        print(f"Wärme:     {draw_waerme_bar(waerme)}")
        print(f"Magen:\n{draw_stomach(saettigung, knurrt, waerme, schritt)}")
        
        if satte_pruefung(saettigung):
            print("\n⚠️  Magen knurrt leer! Füttern nicht vergessen.")
        
        try:
            aktion = input("\nAktion (f=füttern, w=wärmen, q=beenden, Enter=weiter): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n\n🦤 Dodo watschelt schlafend davon. Tschüss!")
            break
        
        eingaben += 1
        
        if aktion == 'q':
            print("\n🦤 Dodo watschelt zufrieden davon. Bis bald!")
            break
        elif aktion == 'f':
            saettigung = min(100, saettigung + random.randint(15, 30))
            print("🦤 *schluck* *gluck* ... lecker!")
            pause(0.5)
        elif aktion == 'w':
            waerme = min(10, waerme + random.randint(2, 4))
            print("🦤 *kuschelt sich an die Wärmflasche* 🔥")
            pause(0.5)
        elif aktion == '':
            pass # Nur Zeit verstreichen lassen
        else:
            print(f"🦤 Verstehe '{aktion}' nicht. Versuch f, w oder q.")
            pause(0.3)
    
    if eingaben >= MAX_EINGABEN:
        print("\n🦤 Maximaler Simulationsschritt erreicht. Dodo schläft ein.")

if __name__ == "__main__":
    main()