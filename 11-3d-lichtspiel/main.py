# 3D-Lichtspiel – Teil 3: Robuste Eingabe für Blur & Tageszeit, Ambient-Licht
# Fifo der Dodo poliert die Bedienung, damit keine Tippfehler den Nebel lichten

import math
import sys
import random


def gauß_gewichte(kernel_radius: int) -> list:
    """Erzeugt 1D-Gewichte für Box-Blur (näherungsweise Gauß). Summe = 1.0."""
    size = kernel_radius * 2 + 1
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


def zeichne_lichtkegel(breite: int, hoehe: int, quellen: list, blur_radius: int = 3, ambient: float = 0.0) -> list:
    """Erzeugt 2D-Gitter mit volumetric Licht: Float-Puffer -> Blur -> ASCII."""
    float_buf = [[ambient for _ in range(breite)] for __ in range(hoehe)]
    
    for qx, qy, radius, richtung_x, richtung_y in quellen:
        r2 = radius * radius
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
                
                if dist > 0.1:
                    punkt_rx = dx / dist
                    punkt_ry = dy / dist
                    cos_winkel = punkt_rx * richtung_x + punkt_ry * richtung_y
                    if cos_winkel < 0.5:
                        continue
                    winkel_faktor = cos_winkel * cos_winkel
                else:
                    winkel_faktor = 1.0
                
                norm_dist = dist / radius
                radial_faktor = math.exp(-4.0 * norm_dist * norm_dist)
                
                beitrag = radial_faktor * winkel_faktor
                float_buf[y][x] += beitrag
    
    for y in range(hoehe):
        for x in range(breite):
            if float_buf[y][x] > 1.0:
                float_buf[y][x] = 1.0
    
    gewichte = gauß_gewichte(blur_radius)
    float_buf = box_blur_1d(float_buf, gewichte, horizontal=True)
    float_buf = box_blur_1d(float_buf, gewichte, horizontal=False)
    
    bild = [[' ' for _ in range(breite)] for __ in range(hoehe)]
    
    random.seed(1337)
    for _ in range(breite * hoehe // 40):
        x = random.randint(0, breite - 1)
        y = random.randint(hoehe // 2, hoehe - 1)
        bild[y][x] = random.choice(['.', ',', '`'])
    
    for y in range(hoehe):
        for x in range(breite):
            zeichen = intensitaet_zu_ascii(float_buf[y][x])
            if zeichen != ' ':
                aktuell = bild[y][x]
                ordnung = ' .,`+*#@'
                if ordnung.index(zeichen) > ordnung.index(aktuell):
                    bild[y][x] = zeichen
    
    return bild


def frage_int(prompt: str, default: int, min_v: int, max_v: int) -> int:
    """Fragt robust eine Ganzzahl ab, fängt EOFError ab."""
    while True:
        try:
            val = input(prompt) or str(default)
            val = int(val)
            return max(min_v, min(max_v, val))
        except ValueError:
            print("  Fifo braucht eine Zahl. Nochmal! 🦤")
        except EOFError:
            print("\nEingabeende – Fifo watschelt nach Hause. 🦤")
            sys.exit(0)


def frage_wahl(prompt: str, default: str, optionen: list) -> str:
    """Fragt robust eine Option ab (case-insensitiv), fängt EOFError ab."""
    opt_lower = [o.lower() for o in optionen]
    while True:
        try:
            val = (input(prompt) or default).strip().lower()
            if val in opt_lower:
                return optionen[opt_lower.index(val)]  # Original-Schreibweise zurückgeben
            print(f"  Fifo kennt nur: {', '.join(optionen)}. Nochmal! 🦤")
        except EOFError:
            print("\nEingabeende – Fifo watschelt nach Hause. 🦤")
            sys.exit(0)


def main():
    print("🍂 3D-Lichtspiel – Herbstpark-Simulator (Volumetric Blur) 🍂")
    print("Fifo der Dodo justiert die Streuungskernel...\n")
    
    breite = frage_int("Parkbreite (Spalten, 40-120) [80]: ", 80, 40, 120)
    hoehe = frage_int("Parkhöhe (Zeilen, 20-60) [30]: ", 30, 20, 60)
    anzahl_quellen = frage_int("Anzahl Lichtquellen (1-5) [3]: ", 3, 1, 5)
    
    tageszeit = frage_wahl(
        "Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]: ",
        "dämmerung",
        ["dämmerung", "nacht", "herbsttag"]
    )
    
    blur_staerke = frage_int("Blur-Radius (1-5, Streuung) [3]: ", 3, 1, 5)
    
    # Tageszeit beeinflusst Ambient-Licht und Quell-Intensität
    if tageszeit == "nacht":
        ambient = 0.02
        quell_staerke_faktor = 1.2
    elif tageszeit == "herbsttag":
        ambient = 0.15
        quell_staerke_faktor = 0.7
    else:  # dämmerung
        ambient = 0.05
        quell_staerke_faktor = 1.0
    
    print(f"\nFifo malt {anzahl_quellen} Lichtkegel in den {breite}x{hoehe} Park (Blur={blur_staerke}, {tageszeit})...\n")
    
    quellen = []
    random.seed(42)
    for i in range(anzahl_quellen):
        qx = random.randint(breite // 4, 3 * breite // 4)
        qy = random.randint(hoehe // 4, 3 * hoehe // 4)
        radius = random.randint(min(breite, hoehe) // 6, min(breite, hoehe) // 3)
        winkel = random.uniform(0, 2 * math.pi)
        richtung_x = math.cos(winkel)
        richtung_y = math.sin(winkel)
        # Radius leicht skalieren je nach Tageszeit für gefühlte Helligkeit
        quellen.append((qx, qy, radius, richtung_x, richtung_y))
        print(f"  Laterne {i+1}: ({qx},{qy}) R={radius} Dir=({richtung_x:.2f},{richtung_y:.2f})")
    
    bild = zeichne_lichtkegel(breite, hoehe, quellen, blur_staerke, ambient)
    
    print()
    for zeile in bild:
        print(''.join(zeile))
    print()
    print("Fifo nickt zufrieden. Das Licht ruht auf dem Laub. 🦤")

if __name__ == "__main__":
    main()