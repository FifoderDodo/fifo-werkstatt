from __future__ import annotations
import math
import sys
import random
from typing import List, Tuple, Optional

Vec3 = Tuple[float, float, float]

# ---------- Vektor‑Hilfsfunktionen ----------

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
    """Hält ein 2D‑Höhenfeld und liefert Normalen, Statistik usw."""

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

# ---------- Beleuchtungs‑ und Schatten‑Funktionen ----------

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
    """Einfacher harte Schatten per Ray‑Marching entlang Licht‑Richtung."""
    lx, ly, lz = vec3_norm(licht_dir)
    h, b = karte.h, karte.b
    l_xy = math.sqrt(lx * lx + ly * ly)
    if l_xy < 1e-6:
        return [[1.0] * b for _ in range(h)]

    max_d = math.sqrt(h * h + b * b)
    step_xy = max_d / schritte
    inv_xy = 1.0 / l_xy
    dir_x = -lx * inv_xy * step_xy
    dir_y = -ly * inv_xy * step_xy
    step_z = lz * inv_xy * step_xy * 0.1

    shadow = [[1.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            h0 = karte.daten[y][x]
            cx = x + 0.5
            cy = y + 0.5
            cz = h0 + bias
            blocked = False
            for _ in range(schritte):
                cx += dir_x
                cy += dir_y
                cz += step_z
                if cx < 0 or cx >= b or cy < 0 or cy >= h:
                    break
                h_here = karte.get_bilinear(cy, cx)
                if cz <= h_here:
                    blocked = True
                    break
            if blocked:
                shadow[y][x] = 0.0
    return shadow

def box_blur(src: List[List[float]], radius: int) -> List[List[float]]:
    """Einfacher Box‑Blur für weiche Schatten."""
    if radius <= 0:
        return src
    h = len(src)
    b = len(src[0]) if h > 0 else 0
    # Horizontale Pass
    tmp = [[0.0] * b for _ in range(h)]
    for y in range(h):
        row = src[y]
        sum_val = 0.0
        for x in range(b):
            sum_val += row[x]
            if x - radius - 1 >= 0:
                sum_val -= row[x - radius - 1]
            if x + radius < b:
                sum_val += row[x + radius]
            count = min(b, x + radius + 1) - max(0, x - radius)
            tmp[y][x] = sum_val / count
    # Vertikale Pass
    dst = [[0.0] * b for _ in range(h)]
    for x in range(b):
        sum_val = 0.0
        for y in range(h):
            sum_val += tmp[y][x]
            if y - radius - 1 >= 0:
                sum_val -= tmp[y - radius - 1][x]
            if y + radius < h:
                sum_val += tmp[y + radius][x]
            count = min(h, y + radius + 1) - max(0, y - radius)
            dst[y][x] = sum_val / count
    return dst

# ---------- Ausgabe‑Helfer ----------

def schatten_zu_ascii(shadow: List[List[float]]) -> str:
    """Wandelt Schattenkarte (0..1) in ASCII‑Art um."""
    zeichen = " .'`^\":;~!><[]{}()|/\\=+*#@$%&"
    n = len(zeichen) - 1
    lines = []
    for row in shadow:
        line = ''.join(zeichen[min(n, max(0, int(v * n)))] for v in row)
        lines.append(line)
    return '\n'.join(lines)

def speichere_ppm(shadow: List[List[float]], dateiname: str) -> None:
    """Speichert Schattenkarte als Graustufen‑PPM (P6)."""
    h = len(shadow)
    b = len(shadow[0]) if h > 0 else 0
    with open(dateiname, 'wb') as f:
        f.write(f'P6\n{b} {h}\n255\n'.encode())
        for row in shadow:
            for v in row:
                val = int(max(0.0, min(1.0, v)) * 255)
                f.write(bytes([val, val, val]))

# ---------- Hauptprogramm ----------

def forms_waehlen(name: str) -> Tiefenkarte:
    name = name.strip().lower()
    if name == 'kugel':
        return erzeuge_kugel()
    elif name == 'kegel':
        return erzeuge_kegel()
    elif name == 'pyramide':
        return erzeuge_stufenpyramide()
    elif name == 'wellblech':
        return erzeuge_wellblech()
    else:
        print(f'Unbekannte Form: {name}, nehme Kugel.')
        return erzeuge_kugel()

def parse_licht(s: str) -> Vec3:
    try:
        parts = s.strip().split()
        if len(parts) != 3:
            raise ValueError
        x, y, z = map(float, parts)
        if x == 0 and y == 0 and z == 0:
            raise ValueError
        return (x, y, z)
    except Exception:
        print('Ungültig, nutze Standard (1, -1, 1).')
        return (1.0, -1.0, 1.0)

def interaktiv() -> None:
    print('Schatten‑Simulator – Interaktiver Modus')
    print('Verfügbare Formen: kugel, kegel, pyramide, wellblech')
    try:
        form_name = input('Form wählen: ').strip()
    except EOFError:
        print('\nKeine Eingabe – Tschüss!')
        return
    karte = forms_waehlen(form_name)
    try:
        licht_str = input('Lichtrichtung als drei Zahlen (x y z), z.B. 1 -1 1: ').strip()
    except EOFError:
        print('\nAbbruch.')
        return
    licht = parse_licht(licht_str)
    try:
        blur_str = input('Weichzeichner‑Radius (0 für aus): ').strip()
        blur_r = int(blur_str) if blur_str else 0
    except EOFError:
        print('\nAbbruch.')
        return
    except ValueError:
        blur_r = 0

    print('Berechne harte Schatten …')
    hart = harte_schatten_raymarch(karte, licht)
    if blur_r > 0:
        print(f'Wende Box‑Blur mit Radius {blur_r} an …')
        weich = box_blur(hart, blur_r)
    else:
        weich = hart

    print('\nASCII‑Vorschau:')
    print(schatten_zu_ascii(weich))

    try:
        speichern = input('Als PPM speichern? (Dateiname oder Enter zum Überspringen): ').strip()
    except EOFError:
        speichern = ''
    if speichern:
        speichere_ppm(weich, speichern)
        print(f'Gespeichert unter {speichern}')

def batch() -> None:
    """Führt ein paar Beispiel‑Kombinationen aus und speichert PPMs."""
    print('Batch‑Modus: Erzeuge Beispielbilder …')
    configs = [
        ('kugel', (1, -1, 1), 2, 'kugel_weich.ppm'),
        ('kegel', (-1, 0.5, 1), 3, 'kegel_weich.ppm'),
        ('pyramide', (0, -1, 2), 1, 'pyramide_weich.ppm'),
        ('wellblech', (1, 1, 1), 0, 'wellblech_hart.ppm'),
    ]
    for form, licht, blur, fname in configs:
        karte = forms_waehlen(form)
        hart = harte_schatten_raymarch(karte, licht)
        weich = box_blur(hart, blur) if blur > 0 else hart
        speichere_ppm(weich, fname)
        print(f'  {form} mit Licht {licht}, Blur {blur} -> {fname}')
    print('Batch fertig.')

def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == '--batch':
        batch()
    else:
        interaktiv()

if __name__ == '__main__':
    main()