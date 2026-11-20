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
    Zeile 1-5: Magenwände mit Peristaltik-Sinus
    Füllhöhe basiert auf 'wert' (0-100).
    Wellen auf der Füllstandsoberfläche.
    Farbe der Füllung per interpolate_color.
    """
    lines = []
    reset = "\033[0m" if USE_ANSI else ""
    
    # Dampf über dem Magen (animiert)
    dampf_chars = ["   ~ ~ ~", "  ~ ~ ~ ~", " ~ ~ ~ ~ ~", "~ ~ ~ ~ ~ ~"]
    dampf_idx = int((schritt * 0.2) % len(dampf_chars))
    dampf = dampf_chars[dampf_idx]
    if USE_ANSI:
        dampf = f"\033[90m{dampf}{reset}"
    lines.append(f"      {dampf}")
    
    # Magen-Geometrie
    breite_innen = 20
    hoehe = 5
    fuell_hoehe = int((wert / 100) * hoehe)
    
    # Peristaltik: Horizontale Verschiebung der Wände (Sinus)
    # Zwei Phasen für oberes/unteres Drittel
    phase = schritt * 0.3
    
    for row in range(hoehe):
        # Wand-Offset berechnen
        # Stärker in der Mitte (Bauch)
        bauch_faktor = 1.0 - abs((row - hoehe / 2) / (hoehe / 2)) # 0 oben/unten, 1 mitte
        offset = int(math.sin(phase + row * 0.5) * 1.5 * bauch_faktor)
        
        links = "/" + " " * max(0, 2 + offset)
        rechts = " " * max(0, 2 - offset) + "\\"
        
        # Füllung
        if row >= (hoehe - fuell_hoehe):
            # Wir sind im Füllbereich
            fuell_ratio = (row - (hoehe - fuell_hoehe) + 0.5) / fuell_hoehe if fuell_hoehe > 0 else 0
            farbe = interpolate_color(fuell_ratio) if USE_ANSI else ""
            
            # Wellen auf der Oberfläche (oberste Füllzeile) und leichte Unruhe drunter
            is_surface = (row == hoehe - fuell_hoehe)
            wellen_phase = phase * 2 + row * 0.8
            
            inhalt = ""
            for col in range(breite_innen):
                wellen_offset = math.sin(wellen_phase + col * 0.6) * (0.4 if is_surface else 0.15)
                # Einfaches Rauschen für Blubbern
                blubber = random.random() < 0.05 * (1.0 - fuell_ratio) # Mehr Blubbern oben
                
                if is_surface and wellen_offset > 0.3:
                    ch = "≈"
                elif blubber:
                    ch = "⦿"
                else:
                    ch = "~" if is_surface else "█"
                inhalt += f"{farbe}{ch}{reset}" if USE_ANSI else ch
            
            line = f"{links}{inhalt}{rechts}"
        else:
            # Leer: Luft / Magenwand innen
            line = f"{links}{' ' * breite_innen}{rechts}"
        
        # Knurren-Effekt: Magenwand zittern
        if knurrt and random.random() < 0.3:
            line = line.replace("/", "{").replace("\\", "}")
        
        lines.append(f"    {line}")
    
    # Boden
    boden = "    \\" + "_" * (breite_innen + 4) + "/"
    if USE_ANSI and waerme > 0:
        boden = f"\033[93m{boden}{reset}"
    lines.append(boden)
    
    # Knurr-Text
    if knurrt:
        knurr_text = "  *** GRRRUUUU ***"
        if USE_ANSI:
            knurr_text = f"\033[91;1m{knurr_text}{reset}"
        lines.append(knurr_text)
    
    return "\n".join(lines)


def draw_dodo(schritt: int) -> str:
    """Zeichnet eine kleine Dodo-Figur mit überarbeitetem Schattenwurf.
    
    Lichtquelle rotiert langsam um die Figur (Kreisbahn).
    Schatten wird als versetzte Silhouette (Offset x, y) gerendert.
    Neu: Schatten-Härte (Sharpness) basierend auf Licht-Höhe (Höhenwinkel).
    Tiefstehende Sonne -> langer, weicher Schatten. Hohe Sonne -> kurzer, harter Schatten.
    """
    # Dodo ASCII Art (5 Zeilen hoch, ca 9 breit)
    #   __
    #  (o o)
    #  ( v )
    #  / ^ \
    # ^^   ^^
    dodo_art = [
        "   __   ",
        "  (o o) ",
        "  ( v ) ",
        "  / ^ \\ ",
        " ^^   ^^ "
    ]
    
    if not USE_ANSI:
        return "\n".join(dodo_art)
    
    # Lichtberechnung
    # Winkel um Figur (Azimut) -> rotiert
    azimut = (schritt * 0.05) % (2 * math.pi)
    # Höhenwinkel (Elevation) -> oszilliert leicht (Tag/Nacht Sim)
    elevation = 0.5 + 0.3 * math.sin(schritt * 0.02) # 0.2 bis 0.8 rad (~11° bis 45°)
    
    # Lichtvektor (gerichtet VON Licht ZU Objekt -> Schatten fällt ENTGEGENSETZT)
    # x: rechts, y: unten (Terminal Koordinaten)
    # Licht kommt aus Richtung azimut, elevation.
    # Schatten-Vektor zeigt weg von Lichtquelle am Boden.
    # dx = -cos(azimut) * cot(elevation)  (Laengenverhaeltnis)
    # dy = -sin(azimut) * cot(elevation) * aspect_ratio_korrektur
    # Terminal Zeichen sind ca 2x so hoch wie breit -> dy skalieren * 0.5
    
    cot_elev = 1.0 / math.tan(elevation) if elevation > 0.01 else 20.0
    
    # Schatten-Offset in Zeichen
    shadow_dx = -math.cos(azimut) * cot_elev
    shadow_dy = -math.sin(azimut) * cot_elev * 0.5 # Aspect Ratio Korrektur
    
    # Weichheit: Je flacher das Licht (kleines elevation), desto weicher (diffuser) der Schatten.
    # Wir simulieren Weichheit durch einen 'Grauwert' (ANSI 90 vs 37) und leichtes Verwischen (hier nur Alpha/Char).
    # Da wir kein Pixel-Blur können, nutzen wir dunklere Zeichen für harten, hellere für weichen Schatten.
    shadow_intensity = max(0.2, min(1.0, elevation / 0.5)) # Hohe Sonne -> Intensität 1 (dunkel), tiefe -> 0.4 (hell)
    shadow_char = "█" if shadow_intensity > 0.7 else ("▓" if shadow_intensity > 0.4 else "░")
    shadow_color = f"\033[38;5;{232 + int(20 * shadow_intensity)}m" # Graustufen 232-252
    
    # Runden auf ganzzahlige Offsets für Zeichengitter
    off_x = int(round(shadow_dx))
    off_y = int(round(shadow_dy))
    
    # Canvas erstellen (Dict: (y,x) -> (char, color, is_shadow))
    canvas = {}
    h = len(dodo_art)
    w = max(len(l) for l in dodo_art)
    
    # 1. Schatten zeichnen (hinten)
    for r, line in enumerate(dodo_art):
        for c, ch in enumerate(line):
            if ch != ' ':
                sy = r + off_y
                sx = c + off_x
                # Schatten nur wenn im sichtbaren Bereich (wir erweitern Canvas dynamisch)
                canvas[(sy, sx)] = (shadow_char, shadow_color, True)
    
    # 2. Dodo zeichnen (vorne, überlagert Schatten)
    dodo_color = "\033[38;2;139;115;85m" # Dodo-Braun
    for r, line in enumerate(dodo_art):
        for c, ch in enumerate(line):
            if ch != ' ':
                canvas[(r, c)] = (ch, dodo_color, False)
    
    # Canvas zu String rendern
    min_y = min(y for y, x in canvas.keys())
    max_y = max(y for y, x in canvas.keys())
    min_x = min(x for y, x in canvas.keys())
    max_x = max(x for y, x in canvas.keys())
    
    out_lines = []
    for y in range(min_y, max_y + 1):
        line_parts = []
        for x in range(min_x, max_x + 1):
            if (y, x) in canvas:
                ch, col, is_shad = canvas[(y, x)]
                line_parts.append(f"{col}{ch}\033[0m")
            else:
                line_parts.append(" ")
        out_lines.append("".join(line_parts).rstrip())
    
    return "\n".join(out_lines)


def main() -> None:
    """Hauptschleife: Füttern, Wärmen, Zuschauen."""
    saettigung = 50
    waerme = 0
    schritt = 0
    eingaben = 0
    
    print("🦤 Dodo-Magenwärmer v49 — Licht & Schatten")
    print("Befehle: f=füttern, w=wärmen, q=beenden, Enter=weiter")
    pause(1.0)
    
    while eingaben < MAX_EINGABEN:
        schritt += 1
        
        # Physik: Sättigung sinkt, Wärme sinkt
        saettigung = max(0, saettigung - random.randint(0, 2))
        waerme = max(0, waerme - (1 if random.random() < 0.3 else 0))
        
        knurrt = satte_pruefung(saettigung)
        
        clear_screen(schritt)
        
        # UI Zusammenbau
        # Links: Magen & Balken, Rechts: Dodo & Feder
        # Wir bauen zeilenweise, damit nebeneinander passt.
        
        magen_str = draw_stomach(saettigung, knurrt, waerme, schritt)
        bar_str = draw_bar(saettigung, waerme=waerme)
        waerme_str = draw_waerme_bar(waerme)
        feder_str = draw_feder(saettigung, schritt)
        dodo_str = draw_dodo(schritt)
        
        magen_lines = magen_str.split('\n')
        dodo_lines = dodo_str.split('\n')
        
        # Höhe angleichen
        max_h = max(len(magen_lines), len(dodo_lines))
        while len(magen_lines) < max_h: magen_lines.append("")
        while len(dodo_lines) < max_h: dodo_lines.append("")
        
        print(f"Schritt: {schritt}  Sättigung: {bar_str}  Wärme: {waerme_str}")
        print(f"Feder: {feder_str}")
        print()
        
        for ml, dl in zip(magen_lines, dodo_lines):
            print(f"{ml:<45}   {dl}")
        
        if knurrt:
            print("\n⚠ Magen knurrt laut! (Piep-Piep im Original-Hardware)")
        
        try:
            inp = input("\n> ").strip().lower()
        except EOFError:
            print("\n🦤 Kein Futter mehr da. Dodo schläft.")
            break
        
        eingaben += 1
        if inp == 'q':
            print("🦤 Tschüss! Dodo watschelt weg.")
            break
        elif inp == 'f':
            saettigung = min(100, saettigung + random.randint(15, 30))
            print("🦤 *schluck* Lecker!")
            pause(0.5)
        elif inp == 'w':
            waerme = min(10, waerme + random.randint(2, 4))
            print("🦤 *kuschel* Warm!")
            pause(0.5)
        elif inp == '':
            pass # Nur Zeit vergehen lassen
        else:
            print(f"🦤 Verstehe '{inp}' nicht. Versuch f, w oder q.")
            pause(0.5)
    
    print("\n--- Ende der Simulation ---")

if __name__ == "__main__":
    main()