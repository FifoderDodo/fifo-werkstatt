from __future__ import annotations
import math
import sys
import random
from typing import List, Tuple, Optional

Vec3 = Tuple[float, float, float]
Color = Tuple[int, int, int]

# ---------- Vektor-Hilfsfunktionen ----------

def vec3_norm(v: Vec3) -> Vec3:
    x, y, z = v
    l = math.sqrt(x * x + y * y + z * z)
    if l < 1e-9:
        return (0.0, 0.0, 1.0)
    return (x / l, y / l, z / l)

def vec3_dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

def vec3_add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

def vec3_scale(v: Vec3, s: float) -> Vec3:
    return (v[0] * s, v[1] * s, v[2] * s)

def vec3_sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def vec3_mul(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] * b[0], a[1] * b[1], a[2] * b[2])

# ---------- Tiefenkarte und Normalen ----------

class Tiefenkarte:
    """Hält ein 2D-Höhenfeld und liefert Normalen, Statistik usw."""

    def __init__(self, daten: List[List[float]]):
        self.daten = [reihe[:] for reihe in daten]
        self.h = len(daten)
        self.b = len(daten[0]) if self.h > 0 else 0

    def get(self, y: int, x: int, default: float = 0.0) -> float:
        if 0 <= y < self.h and 0 <= x < self.b:
            return self.daten[y][x]
        return default

    def get_bilinear(self, y: float, x: float) -> float:
        y0 = max(0, min(self.h - 1, int(math.floor(y))))
        x0 = max(0, min(self.b - 1, int(math.floor(x))))
        y1 = max(0, min(self.h - 1, y0 + 1))
        x1 = max(0, min(self.b - 1, x0 + 1))
        dy = y - y0
        dx = x - x0
        h00 = self.daten[y0][x0]
        h01 = self.daten[y0][x1]
        h10 = self.daten[y1][x0]
        h11 = self.daten[y1][x1]
        h0 = h00 * (1.0 - dx) + h01 * dx
        h1 = h10 * (1.0 - dx) + h11 * dx
        return h0 * (1.0 - dy) + h1 * dy

    def setze(self, y: int, x: int, wert: float) -> bool:
        if 0 <= y < self.h and 0 <= x < self.b and 0.0 <= wert <= 1.0:
            self.daten[y][x] = wert
            return True
        return False

    def normalen(self, z_skalierung: float = 2.0) -> List[List[Vec3]]:
        normals: List[List[Vec3]] = []
        for y in range(self.h):
            reihe: List[Vec3] = []
            for x in range(self.b):
                hx = (self.get(y, x + 1) - self.get(y, x - 1)) * 0.5 * z_skalierung
                hy = (self.get(y + 1, x) - self.get(y - 1, x)) * 0.5 * z_skalierung
                reihe.append(vec3_norm((-hx, -hy, 1.0)))
            normals.append(reihe)
        return normals

    def statistik(self) -> Tuple[float, float, float]:
        flach = [w for reihe in self.daten for w in reihe]
        if not flach:
            return 0.0, 0.0, 0.0
        mn, mx = min(flach), max(flach)
        return mn, mx, mx - mn

# ---------- Formen erzeugen ----------

def erzeuge_kugel(h: int = 20, b: int = 40, r_rel: float = 0.42) -> Tiefenkarte:
    karte = [[0.0 for _ in range(b)] for _ in range(h)]
    cy, cx = (h - 1) / 2.0, (b - 1) / 2.0
    radius = min(h, b) * r_rel
    for y in range(h):
        for x in range(b):
            dy = y - cy
            dx = (x - cx) * 0.5
            dist_sq = dx * dx + dy * dy
            if dist_sq <= radius * radius:
                karte[y][x] = math.sqrt(radius * radius - dist_sq) / radius
    return Tiefenkarte(karte)

def erzeuge_kegel(h: int = 20, b: int = 40, r_rel: float = 0.45) -> Tiefenkarte:
    karte = [[0.0 for _ in range(b)] for _ in range(h)]
    cy, cx = (h - 1) / 2.0, (b - 1) / 2.0
    radius = min(h, b) * r_rel
    for y in range(h):
        for x in range(b):
            dy = y - cy
            dx = (x - cx) * 0.5
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= radius:
                karte[y][x] = 1.0 - (dist / radius)
    return Tiefenkarte(karte)

def erzeuge_stufenpyramide(h: int = 20, b: int = 40) -> Tiefenkarte:
    karte = [[0.0 for _ in range(b)] for _ in range(h)]
    cy, cx = (h - 1) / 2.0, (b - 1) / 2.0
    for y in range(h):
        for x in range(b):
            dy = abs(y - cy) / (h * 0.45)
            dx = abs(x - cx) / (b * 0.45)
            dist = max(dx, dy)
            if dist < 1.0:
                karte[y][x] = math.floor((1.0 - dist) * 4.0) / 4.0
    return Tiefenkarte(karte)

def erzeuge_wellblech(h: int = 20, b: int = 40, wellen: int = 8) -> Tiefenkarte:
    """Wellförmiges Höhenfeld (ähnlich Wellblech)."""
    karte = [[0.0 for _ in range(b)] for _ in range(h)]
    for y in range(h):
        for x in range(b):
            val = 0.5 + 0.5 * math.sin(2.0 * math.pi * wellen * x / b + 0.5 * math.sin(2.0 * math.pi * y / h))
            karte[y][x] = val
    return Tiefenkarte(karte)

# ---------- Beleuchtungs- und Schatten-Funktionen ----------

def diffuse_schatten(normals: List[List[Vec3]], licht_dir: Vec3) -> List[List[float]]:
    lx, ly, lz = vec3_norm(licht_dir)
    result: List[List[float]] = []
    for reihe in normals:
        rreihe: List[float] = []
        for nx, ny, nz in reihe:
            dot = nx * lx + ny * ly + nz * lz
            rreihe.append(max(0.0, dot))
        result.append(rreihe)
    return result

def harte_schatten_raymarch(karte: Tiefenkarte, licht_dir: Vec3,
                            schritte: int = 32, bias: float = 0.005) -> List[List[float]]:
    """Einfacher harte Schatten per Ray-Marching entlang Licht-Richtung."""
    lx, ly, lz = vec3_norm(licht_dir)
    h, b = karte.h, karte.b
    # Licht kommt von oben (lz > 0). Wir marschieren von Oberfläche zur Lichtquelle.
    # Wenn lz <= 0, Licht kommt von unten/seiten -> kein Schattenwurf nach oben hin in diesem Modell.
    if lz <= 1e-6:
        return [[1.0] * b for _ in range(h)]

    max_d = math.sqrt(h * h + b * b)
    step_xy = max_d / schritte
    l_xy = math.sqrt(lx * lx + ly * ly)
    
    result: List[List[float]] = []
    for y in range(h):
        reihe: List[float] = []
        for x in range(b):
            h_hier = karte.daten[y][x]
            if h_hier <= 0.0:
                reihe.append(1.0)
                continue
            
            # Startpunkt leicht über Oberfläche (Bias)
            cur_x = x + lx * bias * 10
            cur_y = y + ly * bias * 10
            cur_z = h_hier + bias
            
            # Schrittweite in Weltkoordinaten (xy pro Schritt, z pro Schritt)
            # Wir wollen 'schritte' Schritte bis zum Rand oder Licht.
            step_x = lx * step_xy
            step_y = ly * step_xy
            step_z = lz * step_xy * (max_d / max(h, b)) * 0.5 # Heuristik für Z-Skalierung
            
            blocked = False
            for _ in range(schritte):
                cur_x += step_x
                cur_y += step_y
                cur_z += step_z
                
                if cur_z > 1.0: # Über max Höhe -> raus
                    break
                if not (0 <= cur_x < b - 1 and 0 <= cur_y < h - 1):
                    break
                
                terrain_h = karte.get_bilinear(cur_y, cur_x)
                if terrain_h > cur_z:
                    blocked = True
                    break
            
            reihe.append(0.0 if blocked else 1.0)
        result.append(reihe)
    return result

def box_blur(src: List[List[float]], radius: int) -> List[List[float]]:
    """Trennbare Box-Blur (horizontal + vertikal)."""
    if radius <= 0:
        return src
    h = len(src)
    b = len(src[0]) if h > 0 else 0
    tmp = [[0.0] * b for _ in range(h)]
    # Horizontal
    for y in range(h):
        row = src[y]
        sum_val = 0.0
        for x in range(b):
            sum_val += row[x]
            if x - radius - 1 >= 0:
                sum_val -= row[x - radius - 1]
            tmp[y][x] = sum_val / (min(x + radius, b - 1) - max(x - radius, 0) + 1)
    # Vertikal
    dst = [[0.0] * b for _ in range(h)]
    for x in range(b):
        sum_val = 0.0
        for y in range(h):
            sum_val += tmp[y][x]
            if y - radius - 1 >= 0:
                sum_val -= tmp[y - radius - 1][x]
            dst[y][x] = sum_val / (min(y + radius, h - 1) - max(y - radius, 0) + 1)
    return dst

def mische_schatten(hart: List[List[float]], weich: List[List[float]], mischung: float = 0.5) -> List[List[float]]:
    h = len(hart)
    b = len(hart[0]) if h > 0 else 0
    return [[hart[y][x] * (1.0 - mischung) + weich[y][x] * mischung for x in range(b)] for y in range(h)]

# ---------- Farb-Mapping (NEU) ----------

def hoehe_zu_farbe(h: float) -> Color:
    """Einfaches Farb-Gradient-Mapping: Tief=Blau, Mittel=Grün/Braun, Hoch=Weiß."""
    h = max(0.0, min(1.0, h))
    if h < 0.25: # Wasser/Tief
        t = h / 0.25
        r = int(0 + t * 30)
        g = int(50 + t * 100)
        b = int(150 + t * 100)
    elif h < 0.5: # Strand/Flachland
        t = (h - 0.25) / 0.25
        r = int(180 + t * 60)
        g = int(160 + t * 40)
        b = int(80 - t * 30)
    elif h < 0.75: # Wald/Berg
        t = (h - 0.5) / 0.25
        r = int(60 + t * 60)
        g = int(120 + t * 40)
        b = int(30 + t * 20)
    else: # Schnee/Gipfel
        t = (h - 0.75) / 0.25
        r = int(180 + t * 75)
        g = int(180 + t * 75)
        b = int(180 + t * 75)
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

def wende_licht_farbe(farbe: Color, intensitaet: float, licht_farbe: Color = (255, 240, 220), umgebung: Color = (30, 30, 50)) -> Color:
    """Mischt Oberflächenfarbe mit Lichtfarbe und Umgebungslicht."""
    i = max(0.0, min(1.0, intensitaet))
    r = int(farbe[0] * i * (licht_farbe[0] / 255.0) + farbe[0] * (1.0 - i) * (umgebung[0] / 255.0))
    g = int(farbe[1] * i * (licht_farbe[1] / 255.0) + farbe[1] * (1.0 - i) * (umgebung[1] / 255.0))
    b = int(farbe[2] * i * (licht_farbe[2] / 255.0) + farbe[2] * (1.0 - i) * (umgebung[2] / 255.0))
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

# ---------- ASCII & Export ----------

ASCII_RAMP = "@%#*+=-:. "

def ascii_art(wissen: List[List[float]]) -> str:
    h = len(wissen)
    b = len(wissen[0]) if h > 0 else 0
    zeilen = []
    for y in range(h):
        zeile = []
        for x in range(b):
            v = max(0.0, min(1.0, wissen[y][x]))
            idx = int(v * (len(ASCII_RAMP) - 1))
            zeile.append(ASCII_RAMP[idx])
        zeilen.append(''.join(zeile))
    return '\n'.join(zeilen)

def speichere_ppm(dateiname: str, daten: List[List[Color]]):
    h = len(daten)
    b = len(daten[0]) if h > 0 else 0
    with open(dateiname, 'wb') as f:
        f.write(f'P6\n{b} {h}\n255\n'.encode('ascii'))
        for y in range(h):
            for x in range(b):
                r, g, b_ = daten[y][x]
                f.write(bytes([r, g, b_]))
    print(f'PPM gespeichert: {dateiname} ({b}x{h})')

# ---------- Hauptprogramm ----------

def waehle_form() -> Tiefenkarte:
    print('\nForm wählen:')
    print('  1: Kugel')
    print('  2: Kegel')
    print('  3: Stufenpyramide')
    print('  4: Wellblech')
    print('  5: Zufällige Hügel (Perlin-ish)')
    while True:
        try:
            w = input('> ').strip()
            if w == '1': return erzeuge_kugel()
            if w == '2': return erzeuge_kegel()
            if w == '3': return erzeuge_stufenpyramide()
            if w == '4': return erzeuge_wellblech()
            if w == '5':
                # Einfache zufällige Hügel via Sinus-Overlay
                h, b = 20, 40
                karte = [[0.0]*b for _ in range(h)]
                for _ in range(5):
                    cx, cy = random.random()*b, random.random()*h
                    r = 5 + random.random()*10
                    for y in range(h):
                        for x in range(b):
                            d = math.hypot(x-cx, y-cy)
                            if d < r:
                                karte[y][x] += (1.0 - d/r) * 0.5
                # Clamp
                for y in range(h):
                    for x in range(b):
                        karte[y][x] = min(1.0, karte[y][x])
                return Tiefenkarte(karte)
            print('Ungültig. 1-5.')
        except EOFError:
            print('\nTschüss!')
            sys.exit(0)

def waehle_licht() -> Vec3:
    print('\nLichtrichtung (x y z), z>0 heißt von oben. Enter = Standard (1, -1, 2):')
    try:
        s = input('> ').strip()
        if not s:
            return (1.0, -1.0, 2.0)
        parts = s.split()
        if len(parts) == 3:
            return (float(parts[0]), float(parts[1]), float(parts[2]))
    except (ValueError, EOFError):
        pass
    return (1.0, -1.0, 2.0)

def main() -> None:
    random.seed(42)
    print('=== Schatten-Simulator (Teil 32) ===')
    print('Träume von Tiefe...')
    
    karte = waehle_form()
    licht = waehle_licht()
    
    print('\nBerechne Normalen...')
    normals = karte.normalen(z_skalierung=2.0)
    
    print('Berechne diffuses Licht (Lambert)...')
    diff = diffuse_schatten(normals, licht)
    
    print('Ray-Marching für harte Schatten...')
    hart = harte_schatten_raymarch(karte, licht, schritte=64, bias=0.01)
    
    print('Box-Blur für weiche Schatten (Radius 2)...')
    weich = box_blur(hart, radius=2)
    
    print('Mische Schatten (50/50)...')
    schatten = mische_schatten(hart, weich, 0.5)
    
    print('Kombiniere: Diffus * Schatten...')
    h, b = karte.h, karte.b
    final_grau = [[diff[y][x] * schatten[y][x] for x in range(b)] for y in range(h)]
    
    # NEU: Farb-Rendering für PPM
    print('Rendere Farbbild (PPM)...')
    farb_bild: List[List[Color]] = []
    for y in range(h):
        reihe: List[Color] = []
        for x in range(b):
            basis_farbe = hoehe_zu_farbe(karte.daten[y][x])
            intensitaet = final_grau[y][x]
            pixel_farbe = wende_licht_farbe(basis_farbe, intensitaet)
            reihe.append(pixel_farbe)
        farb_bild.append(reihe)
    
    print('\n--- ASCII Vorschau (Grauwert) ---')
    print(ascii_art(final_grau))
    
    try:
        name = input('\nDateiname für PPM (Enter = shadow.ppm): ').strip()
        if not name:
            name = 'shadow.ppm'
        speichere_ppm(name, farb_bild)
    except EOFError:
        print('\nKein Dateiname, überspringe Speichern.')
    
    print('\nFertig. Gute Nacht!')

if __name__ == '__main__':
    main()