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
    
    # Auf 0-255 skalieren, V=0.9 (230) für angenehme Helligkeit
    r = int((r + m) * 230)
    g = int((g + m) * 230)
    b = int((b + m) * 230)
    return f"\033[38;2;{r};{g};{b}m"


def draw_feder(saettigung: int, schritt: int) -> str:
    """Zeichnet eine kleine leuchtende Feder als Sättigungs-Indikator.
    
    Farbe: Grün(>75) -> Gelb(>45) -> Orange(>20) -> Rot(>5) -> Grau(<=5).
    Nutzt Bézier-Easing für Pulsieren (Skalierung), horizontales Wackeln und Neigungs-Charakter.
    
    Args:
        saettigung: Aktueller Sättigungswert 0-100
        schritt: Animationsschritt für zyklische Effekte
    """
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
        
        # Animations-Zyklen mit verschiedenen Frequenzen
        cycle_puls = (schritt * 0.07) % 1.0
        cycle_wackel = (schritt * 0.13) % 1.0
        cycle_bend = (schritt * 0.11) % 1.0
        
        # 1. Pulsieren: ease_in_out_quad für sanftes An-/Abschwellten
        p = ease_in_out_quad(cycle_puls)
        scale = 1 + 0.5 * p
        show_double = scale > 1.25
        
        # 2. Horizontales Wackeln: nur bei niedriger Sättigung stark
        wackel_amp = 1.0 if saettigung < 20 else (0.3 if saettigung < 50 else 0.0)
        w = ease_out_cubic(cycle_wackel) * wackel_amp
        wackel_str = " " if w > 0.5 else ""
        
        # 3. Neigung: Zeichenwechsel für 'Biegen' der Feder
        b = ease_in_out_quad(cycle_bend)
        bend_idx = int(b * (len(bend_chars) - 1))
        char = bend_chars[bend_idx]
        
        if show_double and saettigung > 5:
            return f"{wackel_str}{farbe}{char}{char}{reset}"
        return f"{wackel_str}{farbe}{char}{reset}"
    else:
        # Fallback ohne ANSI
        if saettigung > 75: return ">"
        if saettigung > 45: return "-~"
        if saettigung > 20: return "~"
        if saettigung > 5:  return "!"
        return "."


def draw_bar(wert: int, breite: int = 24, waerme: int = 0) -> str:
    """Baut einen farbigen Balken für die Sättigung mit sanftem Farbverlauf.
    
    Jedes Zeichen wird einzeln per interpolate_color gefärbt,
    sodass ein kontinuierlicher Rot->Gelb->Grün Übergang entsteht.
    
    Args:
        wert: Sättigung 0-100
        breite: Balkenbreite in Zeichen
        waerme: Wenn >0, gelber Rand als Wärme-Indikator
    """
    voll = int((wert / 100) * breite)
    leer = breite - voll
    if USE_ANSI:
        rand = "\033[93m" if waerme > 0 else "\033[0m"
        reset = "\033[0m"
        bar_parts = []
        for i in range(breite):
            ratio = (i + 0.5) / breite  # Mitte des Zeichens für gleichmäßige Verteilung
            if i < voll:
                farbe = interpolate_color(ratio)
                bar_parts.append(f"{farbe}█{reset}")
            else:
                bar_parts.append(f"{reset}░{reset}")
        return f"{rand}[{reset}{''.join(bar_parts)}{rand}]{reset} {wert:3d}%"
    return f"[{'#' * voll}{'.' * leer}] {wert:3d}%"


def draw_waerme_bar(waerme: int, max_waerme: int = 10, breite: int = 12) -> str:
    """Visualisiert den Wärme-Level als kleinen Balken.
    
    Args:
        waerme: Aktueller Wärme-Wert
        max_waerme: Maximale Kapazität (default 10)
        breite: Anzeigebreite in Zeichen
    """
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
    """Zeichnet den ASCII-Magen mit Füllung, Knurren, animiertem Dampf, Peristaltik und Wellen.
    
    Struktur (6 Zeilen Körper + Header):
     Zeile 0: Deckel / Dampf
     Zeile 1-4: Magenwände mit Füllstands-Welle & Peristaltik
     Zeile 5: Boden
    Farbe der Füllung nutzt interpolate_color für Tiefe.
    """
    reset = "\033[0m" if USE_ANSI else ""
    lines = []
    
    # Dampf über dem Magen (animiert, Farbe basiert auf Wärme)
    dampf_chars = ["~", "∼", "∿", "⤳", "⤴"]
    dampf_line = "      "
    if waerme > 0:
        for i in range(5):
            phase = (schritt * 0.2 + i * 0.3) % 1.0
            if phase < 0.6:
                char = dampf_chars[int(phase * len(dampf_chars))]
                if USE_ANSI:
                    # Dampf: Weiß -> Gelb bei hoher Wärme
                    steam_ratio = min(waerme / 10.0, 1.0)
                    r = 255
                    g = int(200 + 55 * steam_ratio)
                    b = int(150 * (1 - steam_ratio))
                    dampf_line += f"\033[38;2;{r};{g};{b}m{char}{reset} "
                else:
                    dampf_line += f"{char} "
            else:
                dampf_line += "  "
    lines.append(dampf_line.rstrip())
    
    # Magen-Geometrie
    width = 20  # Innenbreite
    fill_height = int((wert / 100) * 4)  # 4 Zeilen Füllung max
    
    # Peristaltik-Welle (sinusbasiert, läuft von oben nach unten)
    peristaltik_phase = (schritt * 0.15) % (2 * math.pi)
    
    for row in range(4):  # 4 Inhaltszeilen
        # Wand-Links/Rechts
        left_wall = "("
        right_wall = ")"
        
        # Peristaltik-Versatz für diese Zeile
        wave_offset = math.sin(peristaltik_phase - row * 0.8) * 1.5
        inner_width = width + int(wave_offset)
        inner_width = max(10, min(24, inner_width))  # Clamp
        
        # Füllung in dieser Zeile? (row 0 ist oben, row 3 unten)
        fill_row = (3 - row) < fill_height
        
        content = ""
        if fill_row:
            # Wellen auf der Flüssigkeitsoberfläche (nur oberste gefüllte Zeile)
            is_surface = (3 - row) == (fill_height - 1)
            for col in range(inner_width):
                ratio = col / max(1, inner_width - 1)
                # Farbverlauf horizontal + vertikal für Tiefe
                color_ratio = (ratio + (row / 4.0)) / 2.0
                if USE_ANSI:
                    farbe = interpolate_color(color_ratio)
                    if is_surface and random.random() < 0.1:
                        char = random.choice(["≈", "∼", "∿", "~"])
                    else:
                        char = "█"
                    content += f"{farbe}{char}{reset}"
                else:
                    content += "#"
        else:
            # Leer: Magenwand-Textur oder Knurren
            if knurrt and row == 3 and (schritt // 2) % 2 == 0:
                content = "\033[91m~~KNURR~~\033[0m" if USE_ANSI else "~~KNURR~~"
                content = content.center(inner_width)
            else:
                content = " " * inner_width
        
        lines.append(f"     {left_wall}{content}{right_wall}")
    
    # Boden
    lines.append(f"      \\{'_' * (width + 2)}//")
    
    return "\n".join(lines)


def draw_dodo(schritt: int, saettigung: int) -> str:
    """Zeichnet den Dodo mit rotierender Lichtquelle und dynamischem Schatten.
    
    Lichtquelle rotiert um den Dodo (Azimut) und ändert Höhenwinkel.
    Schattenlänge via Cotangens(Höhe), Aspect-Ratio-Korrektur (Zeichen sind ~2x hoch).
    Dodo blinzelt alle paar Sekunden.
    """
    reset = "\033[0m" if USE_ANSI else ""
    
    # Animation: Blinzeln
    blink = (schritt // 30) % 2 == 0 and (schritt % 60) > 55
    eye_l = "⚬" if not blink else "─"
    eye_r = "⚬" if not blink else "─"
    
    # Hunger-Ausdruck
    if saettigung < 15:
        mouth = "ᗒ"
        brow = "⸢  ⸣"
    elif saettigung < 40:
        mouth = "ᗕ"
        brow = "⸣  ⸢"
    else:
        mouth = "◡"
        brow = "   "
    
    # Dodo Body (vereinfacht, aber mit Schichten für Schatten)
    # Wir rendern den Dodo in ein 2D-Array (List of Lists) für Schatten-Projektion
    canvas_w, canvas_h = 20, 12
    canvas = [[' ' for _ in range(canvas_w)] for _ in range(canvas_h)]
    
    # Dodo Pixel Art (relativ zum Zentrum ~10, 6)
    # Body
    body_parts = [
        (0, -3, "  __  "),
        (-3, -2, " /  \\ "),
        (-2, -1, f"( {eye_l} {eye_r} )"),
        (-3, 0, " /    \\ "),
        (-2, 1, f"(  {mouth}  )"),
        (-3, 2, " /    \\ "),
        (-1, 3, "/ ^^ ^^ \\"),
        (0, 4, " \\  // "),
    ]
    
    for dx, dy, line in body_parts:
        x_start = 10 + dx
        y_pos = 6 + dy
        for i, ch in enumerate(line):
            if 0 <= y_pos < canvas_h and 0 <= x_start + i < canvas_w:
                canvas[y_pos][x_start + i] = ch
    
    # Lichtberechnung
    # Azimut: rotiert langsam
    azimut = (schritt * 0.02) % (2 * math.pi)
    # Elevation: schwankt sanft (sonnenauf/untergang)
    elev = 0.5 + 0.3 * math.sin(schritt * 0.01)  # 0.2 bis 0.8 rad (~11° bis 45°)
    
    # Lichtvektor (x, y, z) -> y ist Bildschirm-hoch, z ist tiefe
    # Aspect Ratio Korrektur: Zeichen sind doppelt so hoch wie breit -> y-Skalierung 0.5
    lx = math.cos(azimut) * math.cos(elev)
    ly = -math.sin(elev) * 0.5  # Negativ, da y nach unten wächst im Array
    # lz = math.sin(azimut) * math.cos(elev) # Nicht direkt für 2D Schatten nötig
    
    # Schattenlänge ~ Cotangens(Elevation) * Objekt-Höhe
    # Cot = cos/sin. Bei flachem Licht (kleines elev) -> langer Schatten.
    shadow_len = max(2, int((math.cos(elev) / max(0.1, math.sin(elev))) * 4))
    
    # Schattenrichtung (Gegensatz zu Lichtquelle horizontal)
    sx = -lx * shadow_len
    # sy = -ly * shadow_len # Schatten