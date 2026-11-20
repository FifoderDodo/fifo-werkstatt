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


def interpolate_color(ratio: float) -> str:
    """Interpoliert RGB-Farbe von Rot (0) über Orange/Gelb nach Grün (1). Gibt ANSI Escape zurück."""
    # Farbstützpunkte: Rot, Orange, Gelb, Hellgrün
    # Wir nutzen HSV-ähnliche Logik für sanften Übergang: Hue 0 (Rot) -> 120 (Grün)
    # Sättigung hoch, Wert hoch.
    hue = ratio * 120  # 0 bis 120 Grad
    # HSV zu RGB (vereinfacht, S=1, V=1)
    c = 1.0
    x = c * (1 - abs((hue / 60) % 2 - 1))
    m = 0.0
    
    if hue < 60:
        r, g, b = c, x, 0
    else:
        r, g, b = x, c, 0
    
    # Auf 0-255 skalieren und etwas abdunkeln für Lesbarkeit (V=0.9)
    r = int((r + m) * 230)
    g = int((g + m) * 230)
    b = int((b + m) * 230)
    return f"\033[38;2;{r};{g};{b}m"


def draw_feder(saettigung: int, schritt: int) -> str:
    """Zeichnet eine kleine leuchtende Feder als Sättigungs-Indikator.
    Farbe: Grün(>75) -> Gelb(>45) -> Orange(>20) -> Rot(>5) -> Grau(<=5).
    Nutzt Bézier-Easing für Pulsieren (Skalierung), horizontales Wackeln und Neigungs-Charakter."""
    if USE_ANSI:
        # Basisfarbe über Interpolation für sanften Übergang
        farbe = interpolate_color(saettigung / 100.0)
        reset = "\033[0m"
        
        # Zeichenwahl basierend auf Sättigung (grobe Stufen für Charakter)
        if saettigung > 75:
            base_char = "❈"
            bend_chars = ["❈", "✦", "✧"]
        elif saettigung > 45:
            base_char = "✦"
            bend_chars = ["✦", "✧", "❈"]
        elif saettigung > 20:
            base_char = "✧"
            bend_chars = ["✧", "❈", "✦"]
        elif saettigung > 5:
            base_char = "✦"
            bend_chars = ["✦", "·", "·"]
        else:
            base_char = "·"
            bend_chars = ["·", " ", " "]
        
        # Animations-Zyklen
        cycle_puls = (schritt * 0.07) % 1.0
        cycle_wackel = (schritt * 0.13) % 1.0
        cycle_bend = (schritt * 0.11) % 1.0
        
        # 1. Pulsieren
        p = ease_in_out_quad(cycle_puls)
        scale = 1 + 0.5 * p
        show_double = scale > 1.25
        
        # 2. Horizontales Wackeln
        wackel_amp = 1.0 if saettigung < 20 else (0.3 if saettigung < 50 else 0.0)
        w = ease_out_cubic(cycle_wackel) * wackel_amp
        wackel_str = " " if w > 0.5 else ""
        
        # 3. Neigung
        b = ease_in_out_quad(cycle_bend)
        bend_idx = int(b * (len(bend_chars) - 1))
        char = bend_chars[bend_idx]
        
        if show_double and saettigung > 5:
            return f"{wackel_str}{farbe}{char}{char}{reset}"
        return f"{wackel_str}{farbe}{char}{reset}"
    else:
        if saettigung > 75: return ">"
        if saettigung > 45: return "-~"
        if saettigung > 20: return "~"
        if saettigung > 5:  return "!"
        return "."


def draw_bar(wert: int, breite: int = 24, waerme: int = 0) -> str:
    """Baut einen farbigen Balken für die Sättigung mit sanftem Farbverlauf."""
    voll = int((wert / 100) * breite)
    leer = breite - voll
    if USE_ANSI:
        rand = "\033[93m" if waerme > 0 else "\033[0m"
        reset = "\033[0m"
        # Wir bauen den Balken Zeichen für Zeichen mit interpolierter Farbe
        bar_parts = []
        for i in range(breite):
            ratio = (i + 0.5) / breite  # Mitte des Zeichens
            if i < voll:
                farbe = interpolate_color(ratio)
                bar_parts.append(f"{farbe}█{reset}")
            else:
                bar_parts.append(f"{reset}░{reset}")
        return f"{rand}[{reset}{''.join(bar_parts)}{rand}]{reset} {wert:3d}%"
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
        return f"{farbe}[{'█' * voll}{'░' * leer}]{reset} {waerme}/{max_waerme}"
    return f"[{'#' * voll}{'.' * leer}] {waerme}/{max_waerme}"


def draw_stomach(wert: int, knurrt: bool, waerme: int = 0, schritt: int = 0) -> str:
    """Zeichnet den ASCII-Magen mit Füllung, Knurren, animiertem Dampf, Peristaltik und Wellen."""
    # Füllhöhe: 5 Zeilen Körper (Index 0-4), Spitze (5) ist immer leer/offen
    fuell_zeilen = max(0, min(5, int((wert / 100) * 5)))
    
    # Header Animation
    if waerme > 0:
        header = "    ( ~ )" if (schritt // 2) % 2 == 0 else "   ( ~ ) "
    elif wert >= 50:
        header = "    ( ~ )" if (schritt // 3) % 2 == 0 else "    (~ ) "
    elif knurrt:
        header = "  * GRRR *" if (schritt // 1) % 2 == 0 else " * GRRRR *"
    else:
        header = "           "
    
    lines = [header]
    
    # Basis-Geometrie: links/rechts Wand, Mitte Füllung
    # Wir nutzen Peristaltik: sinusförmige horizontale Verschiebung der Wände
    for i in range(6):  # 0 bis 5
        # Peristaltik-Welle läuft von oben (0) nach unten (5) über die Zeit
        # Phase hängt von Schritt und Zeilenindex ab
        phase = (schritt * 0.3) + (i * 0.8)
        # Amplitude nimmt nach unten zu (Magen verengt sich)
        amp = 0.5 + (i * 0.3)
        offset = int(math.sin(phase) * amp)
        
        # Wand-Zeichen
        left_wall = "\\"
        right_wall = "//"
        if i == 5:  # Spitze
            left_wall = " "
            right_wall = "V"
        
        # Horizontale Positionierung
        # Basis-Einrückung: 2 Leerzeichen links, dann Wand
        # Wir schieben die *gesamte* Zeile oder nur die Wände? 
        # Einfacher: Wir schieben die rechte Wand relativ zur linken.
        # Breite der Öffnung: ca 7 Zeichen bei i=0, 1 Zeichen bei i=4.
        base_width = 7 - i
        current_width = max(1, base_width + offset)
        
        left_pad = "  "  # Fester linker Rand
        left_str = left_pad + left_wall
        
        # Mitte
        middle = ""
        if i < 5:
            if i < fuell_zeilen:
                # Wellen-Animation im Füllstand
                wave_phase = (schritt * 0.5) + (i * 1.2)
                wave_char = "~" if math.sin(wave_phase) > 0 else "≈"
                # Farbe für Füllung
                if USE_ANSI:
                    fill_color = interpolate_color(wert / 100.0)
                    reset = "\033[0m"
                    middle = f"{fill_color}{wave_char * current_width}{reset}"
                else:
                    middle = wave_char * current_width
            else:
                middle = " " * current_width
        else:
            middle = ""
        
        right_str = right_wall
        lines.append(f"{left_str}{middle}{right_str}")
    
    return "\n".join(lines)


def main() -> None:
    """Hauptschleife: Magen füttern, wärmen, beobachten."""
    saettigung = 50
    waerme = 0
    schritt = 0
    eingaben = 0
    
    print("🦤 Dodo-Magenwärmer v0.47 — Sanfte Farbverläufe & Atmung")
    print("Befehle: f=füttern, w=wärmen, q=beenden, Enter=weiter\n")
    
    while eingaben < MAX_EINGABEN:
        clear_screen(schritt)
        
        # Logik-Updates
        knurrt = satte_pruefung(saettigung)
        
        # Passiver Verbrauch
        if schritt % 3 == 0:
            saettigung = max(0, saettigung - 1)
        if waerme > 0 and schritt % 5 == 0:
            waerme = max(0, waerme - 1)
        
        # Ausgabe
        print(f"Sättigung: {draw_bar(saettigung, waerme=waerme)}")
        print(f"Feder:     {draw_feder(saettigung, schritt)}")
        print(f"Wärme:     {draw_waerme_bar(waerme)}")
        print(f"Magen:\n{draw_stomach(saettigung, knurrt, waerme, schritt)}")
        
        if knurrt and waerme == 0:
            print("\n⚠ Der Magen knurrt bedrohlich...")
        elif waerme > 0:
            print("\n🔥 Die Wärmflasche wirkt beruhigend.")
        elif saettigung >= 90:
            print("\n😌 Der Dodo ist rundum zufrieden.")
        
        print(f"\nAktion (f=füttern, w=wärmen, q=beenden, Enter=weiter): ", end="", flush=True)
        
        try:
            cmd = input().strip().lower()
        except EOFError:
            print("\n🦤 Kein Eingang mehr. Dodo schläft ein. Gute Nacht!")
            break
        
        eingaben += 1
        schritt += 1
        
        if cmd == 'f':
            saettigung = min(100, saettigung + random.randint(10, 25))
            print("🦤 *schluck* *knusper* ... lecker!")
            pause(0.5)
        elif cmd == 'w':
            waerme = min(10, waerme + 3)
            print("🦤 *kuschel* Die Wärmflasche wird aufgelegt.")
            pause(0.5)
        elif cmd == 'q':
            print("🦤 Dodo watschelt weg. Tschüss!")
            break
        elif cmd == '':
            pass  # Nur Zeit verstreichen lassen
        else:
            print(f"🦤 Verstehe '{cmd}' nicht. Versuch f, w oder q.")
            pause(0.5)
    
    if eingaben >= MAX_EINGABEN:
        print("\n🦤 Maximale Eingaben erreicht. Dodo muss nun verdauen.")

if __name__ == "__main__":
    main()