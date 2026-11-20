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
    - Header: Dampf (Wärme), zufriedenes Atmen, oder Knurren
    - Zeilen 0-4: Magenkörper mit links/rechts Wand und Füllung
    - Zeile 5: Magenspitze (immer offen)
    
    Effekte:
    - Peristaltik: Sinusförmige horizontale Verschiebung der Wände (Wellenbewegung)
    - Füllwellen: Animierte ~ Wellen auf der Füllstandsoberfläche
    - Interpolierte Füllfarbe: Farbverlauf passend zum Sättigungsgrad
    - Knurren: Blinkender Header bei niedriger Sättigung
    
    Args:
        wert: Sättigung 0-100
        knurrt: Ob der Magen knurrt (Bool)
        waerme: Wärme-Level 0-10
        schritt: Animationsschritt
    """
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
    # Peristaltik: sinusförmige horizontale Verschiebung der Wände
    for i in range(6):  # 0 bis 5 (5 = Spitze)
        # Peristaltik-Welle: Phase verschoben pro Zeile für wandernde Welle
        phase = (schritt * 0.15) + (i * 0.8)
        wand_offset = int(math.sin(phase) * 1.5)  # -1 bis +1 Verschiebung
        
        # Wand-Zeichen mit Offset
        left_wall = " " * max(0, 2 + wand_offset) + "/"
        right_wall = "\\" + " " * max(0, 2 - wand_offset)
        
        if i == 5:
            # Magenspitze: immer offen
            line = f"{left_wall}      {right_wall}"
        elif i < (5 - fuell_zeilen):
            # Leerer Bereich über Füllstand
            line = f"{left_wall}      {right_wall}"
        else:
            # Gefüllter Bereich mit Wellen-Animation
            fuellhoehe = 5 - i  # 1 bis 5 (unten = 5)
            wellen_phase = (schritt * 0.2) + (fuellhoehe * 0.5)
            wellen_char = "~" if math.sin(wellen_phase) > 0 else "≈"
            
            # Füllfarbe interpoliert nach gesamtem Sättigungsgrad
            if USE_ANSI:
                fuell_farbe = interpolate_color(wert / 100.0)
                reset = "\033[0m"
                fuellung = f"{fuell_farbe}{wellen_char * 6}{reset}"
            else:
                fuellung = wellen_char * 6
            
            line = f"{left_wall}{fuellung}{right_wall}"
        
        lines.append(line)
    
    # Boden-Zeile
    lines.append("      V      ")
    
    return "\n".join(lines)


def main() -> None:
    """Hauptprogramm: Dodo-Magenwärmer Interaktion.
    
    Steuert den Simulationsloop:
    - Sättigung sinkt langsam
    - 'f' füttert (+15 Sättigung, +1 Wärme)
    - 'w' wärmt (+3 Wärme, max 10)
    - 'q' beendet
    - Knurren bei <20% Sättigung
    - Automatische Animation alle 0.3s
    """
    saettigung = 60
    waerme = 0
    schritt = 0
    eingaben = 0
    knurrt = False
    
    print("🦤 Dodo-Magenwärmer gestartet. (f=füttern, w=wärmen, q=beenden, Enter=weiter)")
    
    while eingaben < MAX_EINGABEN:
        # Sättigung sinkt pro Schritt leicht
        saettigung = max(0, saettigung - 1)
        # Wärme kühlt ab
        waerme = max(0, waerme - (1 if schritt % 5 == 0 else 0))
        
        knurrt = satte_pruefung(saettigung)
        
        clear_screen(schritt if not USE_ANSI else None)
        
        # Zeichne alle Komponenten
        bar = draw_bar(saettigung, waerme=waerme)
        feder = draw_feder(saettigung, schritt)
        waerme_bar = draw_waerme_bar(waerme)
        magen = draw_stomach(saettigung, knurrt, waerme, schritt)
        
        print(f"Sättigung: {bar}  Feder: {feder}")
        if waerme > 0:
            print(f"Wärme:     {waerme_bar}")
        print(f"Magen:\n{magen}")
        print(f"\nAktion (f=füttern, w=wärmen, q=beenden, Enter=weiter): ", end="", flush=True)
        
        try:
            eingabe = input().strip().lower()
        except EOFError:
            print("\n🦤 Keine Eingabe mehr. Dodo schläft ein. Gute Nacht!")
            break
        
        if eingabe == 'q':
            print("🦤 Dodo watschelt weg. Tschüss!")
            break
        elif eingabe == 'f':
            saettigung = min(100, saettigung + 15)
            waerme = min(10, waerme + 1)
            print("🦤 *schluck* Mhh, lecker!")
            pause(0.5)
        elif eingabe == 'w':
            waerme = min(10, waerme + 3)
            print("🦤 *kuschelt sich an die Wärmequelle*")
            pause(0.5)
        elif eingabe == '':
            # Nur weiter, Zeit vergeht
            pass
        else:
            print(f"🦤 Verstehe '{eingabe}' nicht. Versuch f, w oder q.")
            pause(0.5)
        
        schritt += 1
        eingaben += 1
        pause(0.3)
    
    if eingaben >= MAX_EINGABEN:
        print("\n🦤 Maximalzahl an Interaktionen erreicht. Dodo ist jetzt satt und müde.")


if __name__ == "__main__":
    main()