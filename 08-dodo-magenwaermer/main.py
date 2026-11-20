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
    """Interpoliert RGB-Farbe von Rot (0) über Orange/Gelb nach Grün (1). Gibt ANSI Escape zurück.
    
    Farbstützpunkte: Rot (Hue 0) -> Gelb (Hue 60) -> Grün (Hue 120).
    Nutzt vereinfachte HSV->RGB Konvertierung mit S=1, V=0.9 für Lesbarkeit.
    """
    hue = ratio * 120  # 0 bis 120 Grad
    c = 1.0
    x = c * (1 - abs((hue / 60) % 2 - 1))
    m = 0.0
    if hue < 60:
        r, g, b = c, x, 0
    else:
        r, g, b = x, c, 0
    r = int((r + m) * 230)
    g = int((g + m) * 230)
    b = int((b + m) * 230)
    return f"\033[38;2;{r};{g};{b}m"


def draw_feder(saettigung: int, schritt: int) -> str:
    """Zeichnet eine kleine leuchtende Feder als Sättigungs‑Indikator.
    
    Farbe: Grün(>75) -> Gelb(>45) -> Orange(>20) -> Rot(>5) -> Grau(<=5).
    Nutzt Bézier‑Easing für Pulsieren (Skalierung), horizontales Wackeln und Neigungs‑Charakter.
    """
    if USE_ANSI:
        farbe = interpolate_color(saettigung / 100.0)
        reset = "\033[0m"
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
        cycle_puls = (schritt * 0.07) % 1.0
        cycle_wackel = (schritt * 0.13) % 1.0
        cycle_bend = (schritt * 0.11) % 1.0
        p = ease_in_out_quad(cycle_puls)
        scale = 1 + 0.5 * p
        show_double = scale > 1.25
        wackel_amp = 1.0 if saettigung < 20 else (0.3 if saettigung < 50 else 0.0)
        w = ease_out_cubic(cycle_wackel) * wackel_amp
        wackel_str = " " if w > 0.5 else ""
        b = ease_in_out_quad(cycle_bend)
        bend_idx = int(b * (len(bend_chars) - 1))
        char = bend_chars[bend_idx]
        if show_double and saettigung > 5:
            return f"{wackel_str}{farbe}{char}{char}{reset}"
        return f"{wackel_str}{farbe}{char}{reset}"
    else:
        if saettigung > 75:
            return ">"
        if saettigung > 45:
            return "-~"
        if saettigung > 20:
            return "~"
        if saettigung > 5:
            return "!"
        return "."


def draw_bar(wert: int, breite: int = 24, waerme: int = 0) -> str:
    """Baut einen farbigen Balken für die Sättigung mit sanftem Farbverlauf.
    
    Jedes Zeichen wird einzeln per interpolate_color gefärbt,
    sodass ein kontinuierlicher Rot->Gelb->Grün Übergang entsteht.
    """
    voll = int((wert / 100) * breite)
    leer = breite - voll
    if USE_ANSI:
        rand = "\033[93m" if waerme > 0 else "\033[0m"
        reset = "\033[0m"
        bar_parts = []
        for i in range(breite):
            ratio = (i + 0.5) / breite
            if i < voll:
                farbe = interpolate_color(ratio)
                bar_parts.append(f"{farbe}█{reset}")
            else:
                bar_parts.append(f"{reset}░{reset}")
        return f"{rand}[{reset}{''.join(bar_parts)}{rand}]{reset} {wert:3d}%"
    return f"[{'#' * voll}{'.' * leer}] {wert:3d}%"


def draw_waerme_bar(waerme: int, max_waerme: int = 10, breite: int = 12) -> str:
    """Visualisiert den Wärme‑Level als kleinen Balken."""
    if max_waerme <= 0:
        return ""
    voll = int((waerme / max_waerme) * breite)
    leer = breite - voll
    if USE_ANSI:
        farbe = "\033[93m"
        reset = "\033[0m"
        return f"{farbe}[{'█' * voll}{'░' * leer}]{reset} {waerme}/{max_waerme}"
    return f"[{'#' * voll}{'.' * leer}] {waerme}/{max_waerme}"


def draw_shadow_layer(wert: int, schritt: int, offset_x: int = 2, offset_y: int = 1) -> list:
    """Erzeugt Schatten-Layer für den Magen als Liste von Zeilen (Prototyp).
    
    Zeichnet eine stark abgedunkelte, leicht versetzte Silhouette des Magens.
    Nutzt ANSI dim (\033[2m) und dunkles Grau für subtilen Tiefeneindruck.
    Kontrast angehoben: leicht bläulicher Schatten (kühler Ton) für mehr Tiefe,
    Helligkeit auf 85/85/100 für bessere Sichtbarkeit gegen dunkle Hintergründe.
    Gibt Liste von Strings zurück – eine pro Zeile des Schattens.
    """
    if not USE_ANSI:
        return []
    
    dim = "\033[2m"
    # Kühlerer Schatten-Ton (leicht bläulich) für mehr Tiefenwirkung
    shadow_color = "\033[38;2;85;85;110m"
    reset = "\033[0m"
    shadow_char = "░"
    shadow_char_dark = "▓"
    
    def welle(row: int) -> str:
        chars = ["~", "-", "_"]
        idx = (row + schritt) % len(chars)
        return chars[idx]
    
    lines = []
    # Header-Schatten
    lines.append(" " * offset_x + dim + shadow_color + " " * 3 + shadow_char * 3 + " " * 3 + reset)
    # Dampf-Schatten (einfach)
    lines.append(" " * offset_x + dim + shadow_color + " " * 3 + shadow_char + " " + shadow_char + " " * 2 + reset)
    # Körper-Schatten: 3 Zeilen, mittlere dunkler bei gefülltem Magen
    for row in range(3):
        fill_ratio = wert / 100.0
        middle = row == 1
        char = shadow_char_dark if (middle and fill_ratio > 0.5) else shadow_char
        wave = welle(row)
        lines.append(" " * offset_x + dim + shadow_color + f"({wave}{char}{char}{char}{wave})" + reset)
    # Boden-Schatten
    lines.append(" " * offset_x + dim + shadow_color + " " + shadow_char * 7 + " " + reset)
    return lines


def draw_magen(saettigung: int, schritt: int, waerme: int = 0) -> list:
    """Zeichnet den kompletten Magen mit Schatten-Layer und Rückgabe als Zeilen-Liste."""
    shadow_lines = draw_shadow_layer(saettigung, schritt)
    
    if USE_ANSI:
        reset = "\033[0m"
        # Dampf über dem Magen
        dampf_chars = ["☁", "☁", "☁"]
        dampf_idx = schritt % len(dampf_chars)
        dampf = f"  {dampf_chars[dampf_idx]} "
        # Magen-Öffnung
        feder = draw_feder(saettigung, schritt)
        opening = f"({feder}~~~{feder})"
        # Magen-Körper mit Füllstand
        bar = draw_bar(saettigung, 24, waerme)
        # Boden
        boden = "  \_____/ "
        
        # Kombiniere mit Schatten (versetzt)
        result = []
        max_lines = max(len(shadow_lines), 5)
        for i in range(max_lines):
            shadow = shadow_lines[i] if i < len(shadow_lines) else ""
            if i == 0:
                main = dampf
            elif i == 1:
                main = opening
            elif i == 2:
                main = f" |{bar}| "
            elif i == 3:
                main = f" |{bar}| "
            elif i == 4:
                main = boden
            else:
                main = ""
            # Schatten leicht nach rechts/unten versetzt darstellen
            if shadow and i < len(shadow_lines) - 1:
                result.append(shadow + "  " + main)
            else:
                result.append(main)
        return result
    else:
        # Fallback ohne ANSI
        feder = draw_feder(saettigung, schritt)
        bar = draw_bar(saettigung, 24, waerme)
        return [
            "  ~  ",
            f"({feder}~~~{feder})",
            f" |{bar}| ",
            f" |{bar}| ",
            "  \_____/ "
        ]


def main() -> None:
    """Hauptschleife: Dodo-Magenwärmer Simulation."""
    saettigung = 50
    waerme = 0
    schritt = 0
    eingaben = 0
    
    print("🦤 Dodo-Magenwärmer – Teil 57/58")
    print("Befehle: [f]ressen, [w]asser, [Enter]warten, [q]uit")
    print()
    
    while eingaben < MAX_EINGABEN:
        clear_screen(schritt)
        
        # Magen zeichnen
        magen_lines = draw_magen(saettigung, schritt, waerme)
        for line in magen_lines:
            print(line)
        
        # Wärme-Balken
        if waerme > 0:
            print(draw_waerme_bar(waerme))
        
        # Status
        if satte_pruefung(saettigung):
            print("\033[91m⚠ Magen knurrt!\033[0m" if USE_ANSI else "⚠ Magen knurrt!")
        
        print(f"\nSättigung: {saettigung}% | Wärme: {waerme}/10 | Schritt: {schritt}")
        print("[f]ressen  [w]asser  [Enter]warten  [q]uit")
        
        try:
            eingabe = input("> ").strip().lower()
        except EOFError:
            print("\nKeine Eingabe mehr – Tschüss!")
            break
        
        if eingabe == 'q':
            print("Dodo watschelt davon. Tschüss!")
            break
        elif eingabe == 'f':
            saettigung = min(100, saettigung + random.randint(15, 25))
            waerme = min(10, waerme + 1)
            print("Mmmh, lecker!")
        elif eingabe == 'w':
            waerme = min(10, waerme + 2)
            saettigung = max(0, saettigung - 2)
            print("Gluck, gluck – wärmt von innen.")
        elif eingabe == '':
            saettigung = max(0, saettigung - random.randint(1, 5))
            waerme = max(0, waerme - 1)
            print("Der Magen arbeitet vor sich hin...")
        else:
            print("Unbekannte Eingabe, bitte f, w, <Enter> oder q.")
            continue
        
        eingaben += 1
        schritt += 1
        pause(0.3)
    
    if eingaben >= MAX_EINGABEN:
        print(f"\nMaximal {MAX_EINGABEN} Eingaben erreicht. Dodo ist satt und zufrieden.")

if __name__ == "__main__":
    main()