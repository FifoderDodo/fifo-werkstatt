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
    lines.append(" " * offset_x + dim + shadow_color + " " * 3 + shadow_char + reset)
    # Körper-Zeilen mit Füllung basierend auf Sättigung
    voll_breite = 24
    voll = int((wert / 100) * voll_breite)
    shadow_fill = shadow_char * voll + " " * (voll_breite - voll)
    # Körper-Zeilen 1-3 mit leicht variierendem Schatten-Charakter
    for row in range(3):
        fill_char = shadow_char_dark if row == 1 and voll > 0 else shadow_char
        current_fill = fill_char * voll + " " * (voll_breite - voll)
        lines.append(" " * offset_x + dim + shadow_color + " " + current_fill + " " + reset)
    # Boden-Schatten
    lines.append(" " * offset_x + dim + shadow_color + " " + shadow_char * (voll_breite + 2) + " " + reset)
    return lines


def draw_magen(saettigung: int, schritt: int, waerme: int = 0) -> list:
    """Zeichnet den Magen als ASCII-Art mit Animation.
    
    Rückgabe: Liste von Strings (Zeilen).
    """
    feder = draw_feder(saettigung, schritt)
    bar = draw_bar(saettigung, waerme=waerme)
    waerme_bar = draw_waerme_bar(waerme)
    
    # Dampf-Animation
    dampf_chars = ["☁", "☁", "  ", " .", "  "]
    dampf = dampf_chars[(schritt // 2) % len(dampf_chars)]
    
    # Magen-Form basierend auf Sättigung
    if saettigung > 75:
        bauch = "(/~~~\\)"
        mund = "\\-~-/"
    elif saettigung > 45:
        bauch = "(/~~\\)"
        mund = "\\-~-/"
    elif saettigung > 20:
        bauch = "(/~\\)"
        mund = "\\_/_"
    elif saettigung > 5:
        bauch = "(\\_/)\\"
        mund = "\\_/_"
    else:
        bauch = "(.)"
        mund = "\\_/_"
    
    linien = []
    linien.append(f"   {dampf}   {feder}")
    linien.append(f"  {bauch}")
    linien.append(f" |{bar}| {waerme_bar}")
    linien.append(f"  {mund}")
    linien.append(f" ‾‾‾")
    return linien


def main() -> None:
    """Hauptschleife: Magen füttern, wärmen, warten."""
    saettigung = 50
    waerme = 0
    schritt = 0
    eingaben = 0
    
    print("Dodo-Magenwärmer gestartet. Strg+C oder 'q' zum Beenden.")
    pause(0.5)
    
    while eingaben < MAX_EINGABEN:
        try:
            clear_screen(schritt if not USE_ANSI else None)
            
            # Schatten-Layer zeichnen
            shadow_lines = draw_shadow_layer(saettigung, schritt)
            for line in shadow_lines:
                print(line)
            
            # Cursor nach oben bewegen um Magen über Schatten zu legen
            if USE_ANSI and shadow_lines:
                sys.stdout.write(f"\033[{len(shadow_lines)}A")
                sys.stdout.flush()
            
            # Magen zeichnen
            magen_lines = draw_magen(saettigung, schritt, waerme)
            for line in magen_lines:
                print(line)
            
            # Status-Zeile
            print(f"--------------^--------------------------------------------- {saettigung}%")
            print(f"Eingaben: {eingaben}/{MAX_EINGABEN}")
            print("Optionen: [f]üttern, [w]ärmen, [Enter]warten, [q]uit")
            
            if USE_ANSI:
                sys.stdout.write("> ")
                sys.stdout.flush()
            
            eingabe = input().strip().lower()
            eingaben += 1
            schritt += 1
            
            if eingabe == 'q':
                print("Tschüss! Der Dodo schläft weiter.")
                break
            elif eingabe == 'f':
                saettigung = min(100, saettigung + random.randint(15, 30))
                print("*schluck* *gluck* Der Magen freut sich!")
                pause(0.4)
            elif eingabe == 'w':
                waerme = min(10, waerme + random.randint(2, 4))
                saettigung = max(0, saettigung - 2)  # Wärmen kostet etwas Energie
                print("*wärme* Der Bauch glüht behaglich.")
                pause(0.4)
            elif eingabe == '':
                saettigung = max(0, saettigung - random.randint(1, 4))
                waerme = max(0, waerme - 1)
                print("*knurr* Der Magen wird leerer...")
                pause(0.3)
            else:
                print("Unbekannte Eingabe, bitte f, w, <Enter> oder q.")
                pause(0.3)
                continue
            
            # Natürlicher Verfall pro Schritt
            saettigung = max(0, saettigung - 1)
            waerme = max(0, waerme - (1 if schritt % 3 == 0 else 0))
            
            if saettigung <= 0:
                clear_screen(schritt if not USE_ANSI else None)
                print("💀 Der Magen ist vollkommen leer. Der Dodo ist ohnmächtig geworden.")
                print("Spiel zu Ende.")
                break
        except EOFError:
            print("\nEingabe Ende. Tschüss!")
            break
        except KeyboardInterrupt:
            print("\nAbbruch. Tschüss!")
            break
    
    if eingaben >= MAX_EINGABEN:
        print(f"\nMaximale Eingaben ({MAX_EINGABEN}) erreicht. Bis bald!")

if __name__ == "__main__":
    main()