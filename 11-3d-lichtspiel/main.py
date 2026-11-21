# 3D-Lichtspiel – Teil 2: Lichtkegel mit Gauß-Unschärfe (Box-Blur-Approximation)
# Fifo der Dodo feilt an der Streuung im Nebel

import math
import sys
import random


def gauß_gewichte(kernel_radius: int) -> list:
    """Erzeugt 1D-Gewichte für Box-Blur (näherungsweise Gauß). Summe = 1.0."""
    size = kernel_radius * 2 + 1
    # Einfacher Box-Filter: alle Gewichte gleich
    gewicht = 1.0 / size
    return [gewicht] * size


def box_blur_1d(puffer: list, gewichte: list, horizontal: bool = True) -> list:
    """Wendet 1D-Box-Blur auf 2D-Float-Puffer an (separabel)."""
    h = len(puffer)
    w = len(puffer[0])
    k_rad = len(gewichte) // 2
    ergebnis = [[0.0 for _ in range(w)] for __ in range(h)]
    
    if horizontal:
        for y in range(h):
            for x in range(w):
                acc = 0.0
                for i, gew in enumerate(gewichte):
                    xi = x - k_rad + i
                    if 0 <= xi < w:
                        acc += puffer[y][xi] * gew
                ergebnis[y][x] = acc
    else:
        for x in range(w):
            for y in range(h):
                acc = 0.0
                for i, gew in enumerate(gewichte):
                    yi = y - k_rad + i
                    if 0 <= yi < h:
                        acc += puffer[yi][x] * gew
                ergebnis[y][x] = acc
    return ergebnis


def intensitaet_zu_ascii(wert: float) -> str:
    """Mappt Float-Intensität (0.0-1.0+) auf ASCII-Stufen."""
    if wert <= 0.0:
        return ' '
    # Clamp und Gamma-Korrektur für perceptual linearity
    w = min(1.0, max(0.0, wert)) ** 0.6
    if w > 0.85:
        return '@'
    elif w > 0.65:
        return '#'
    elif w > 0.45:
        return '*'
    elif w > 0.25:
        return '+'
    elif w > 0.1:
        return '.'
    else:
        return ' '


def zeichne_lichtkegel(breite: int, hoehe: int, quellen: list, blur_radius: int = 3) -> list:
    """Erzeugt 2D-Gitter mit volumetric Licht: Float-Puffer -> Blur -> ASCII."""
    # 1. Float-Intensitätspuffer (additive Überlagerung)
    float_buf = [[0.0 for _ in range(breite)] for __ in range(hoehe)]
    
    for qx, qy, radius, richtung_x, richtung_y in quellen:
        r2 = radius * radius
        # Bounding Box für Optimierung
        x0 = max(0, int(qx - radius))
        x1 = min(breite, int(qx + radius) + 1)
        y0 = max(0, int(qy - radius))
        y1 = min(hoehe, int(qy + radius) + 1)
        
        for y in range(y0, y1):
            dy = y - qy
            for x in range(x0, x1):
                dx = x - qx
                dist2 = dx*dx + dy*dy
                if dist2 > r2:
                    continue
                dist = math.sqrt(dist2)
                
                # Richtungs-Check (Kegel)
                if dist > 0.1:
                    punkt_rx = dx / dist
                    punkt_ry = dy / dist
                    cos_winkel = punkt_rx * richtung_x + punkt_ry * richtung_y
                    if cos_winkel < 0.5:  # ~60°
                        continue
                    # Winkel-Abschwächung: cos^2 für weichere Kanten
                    winkel_faktor = cos_winkel * cos_winkel
                else:
                    winkel_faktor = 1.0
                
                # Radialer Abfall: Gauß-ähnlich (exp(-dist^2))
                # Normiert auf Radius
                norm_dist = dist / radius
                radial_faktor = math.exp(-4.0 * norm_dist * norm_dist)
                
                beitrag = radial_faktor * winkel_faktor
                float_buf[y][x] += beitrag
    
    # 2. Clampen (HDR -> LDR)
    for y in range(hoehe):
        for x in range(breite):
            if float_buf[y][x] > 1.0:
                float_buf[y][x] = 1.0
    
    # 3. Separabler Box-Blur (approximiert Gauß)
    gewichte = gauß_gewichte(blur_radius)
    float_buf = box_blur_1d(float_buf, gewichte, horizontal=True)
    float_buf = box_blur_1d(float_buf, gewichte, horizontal=False)
    
    # 4. ASCII-Mapping & Hintergrund
    bild = [[' ' for _ in range(breite)] for __ in range(hoehe)]
    
    # Herstlaub (statisch, damit es nicht verwischt)
    random.seed(1337)
    for _ in range(breite * hoehe // 40):
        x = random.randint(0, breite - 1)
        y = random.randint(hoehe // 2, hoehe - 1)
        bild[y][x] = random.choice(['.', ',', '`'])
    
    # Licht darüber legen
    for y in range(hoehe):
        for x in range(breite):
            zeichen = intensitaet_zu_ascii(float_buf[y][x])
            if zeichen != ' ':
                # Helligstes gewinnt
                aktuell = bild[y][x]
                ordnung = ' .,`+*#@'
                if ordnung.index(zeichen) > ordnung.index(aktuell):
                    bild[y][x] = zeichen
    
    return bild


def main():
    print("🍂 3D-Lichtspiel – Herbstpark-Simulator (Volumetric Blur) 🍂")
    print("Fifo der Dodo justiert die Streuungskernel...\n")
    
    try:
        # Robuste Eingabe mit Defaults
        def frage_int(prompt, default, min_v, max_v):
            while True:
                try:
                    val = input(prompt) or str(default)
                    val = int(val)
                    return max(min_v, min(max_v, val))
                except ValueError:
                    print("  Fifo braucht eine Zahl. Nochmal! 🦤")
        
        breite = frage_int("Parkbreite (Spalten, 40-120) [80]: ", 80, 40, 120)
        hoehe = frage_int("Parkhöhe (Zeilen, 20-60) [30]: ", 30, 20, 60)
        anzahl_quellen = frage_int("Anzahl Lichtquellen (1-5) [3]: ", 3, 1, 5)
        
        tageszeit = input("Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]: ") or "dämmerung"
        blur_staerke = frage_int("Blur-Radius (1-5, Streuung) [3]: ", 3, 1, 5)
        
        print(f"\nFifo malt {anzahl_quellen} Lichtkegel in den {breite}x{hoehe} Park (Blur={blur_staerke})...\n")
        
        quellen = []
        random.seed(42)
        for i in range(anzahl_quellen):
            qx = random.randint(breite // 4, 3 * breite // 4)
            qy = random.randint(2, hoehe // 3)
            radius = random.randint(min(breite, hoehe) // 3, min(breite, hoehe) // 2)
            richtung_x = random.uniform(-0.3, 0.3)
            richtung_y = random.uniform(0.7, 1.0)
            rlen = math.hypot(richtung_x, richtung_y)
            richtung_x /= rlen
            richtung_y /= rlen
            quellen.append((qx, qy, radius, richtung_x, richtung_y))
            print(f"  Laterne {i+1}: ({qx},{qy}) R={radius} Dir=({richtung_x:.2f},{richtung_y:.2f})")
        
        bild = zeichne_lichtkegel(breite, hoehe, quellen, blur_radius=blur_staerke)
        
        print("\n" + "=" * breite)
        for zeile in bild:
            print(''.join(zeile))
        print("=" * breite)
        
        hell_pixels = sum(1 for row in bild for c in row if c in '@#*+')
        print(f"\nFifo zählt {hell_pixels} beleuchtete Pixel – der Nebel glüht volumetric. 🌫️")
        print("Teil 2 fertig. Nächster Schritt: Schattenwürfe durch Baumkronen... 🦤")
        
    except EOFError:
        print("\nFifo wird müde. Gute Nacht im Herbstpark. 🍂")
    except KeyboardInterrupt:
        print("\nFifo flattert weg. Tschüss! 🍂")


if __name__ == "__main__":
    main()