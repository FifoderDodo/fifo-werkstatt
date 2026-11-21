# main.py – Schatten‑Simulator, Teil 24
# Fifo, der Dodo, träumt den letzten Schliff: Speichern, Batch‑Modus, kleine Aufräumarbeiten.
# Diesmal: Ray‑Marching fertig, Weichzeichner, ASCII‑Export, EOF‑Sicherheit, Batch‑Modus.

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

    schatten: List[List[float]] = []
    for y in range(h):
        reihe: List[float] = []
        for x in range(b):
            start_h = karte.daten[y][x] + bias
            cx, cy = float(x), float(y)
            ch = start_h
            blocked = False
            for _ in range(schritte):
                cx += dir_x
                cy += dir_y
                ch += step_z
                if cx < 0 or cx >= b - 1 or cy < 0 or cy >= h - 1:
                    break
                h_terrain = karte.get_bilinear(cy, cx)
                if ch <= h_terrain:
                    blocked = True
                    break
            reihe.append(0.0 if blocked else 1.0)
        schatten.append(reihe)
    return schatten

def box_blur(src: List[List[float]], radius: int = 1) -> List[List[float]]:
    """Einfacher Box-Blur für weiche Schatten."""
    h = len(src)
    b = len(src[0]) if h > 0 else 0
    if radius <= 0:
        return [row[:] for row in src]
    # Horizontale Pass
    tmp = [[0.0] * b for _ in range(h)]
    for y in range(h):
        row = src[y]
        for x in range(b):
            s = 0.0
            cnt = 0
            for dx in range(-radius, radius + 1):
                nx = x + dx
                if 0 <= nx < b:
                    s += row[nx]
                    cnt += 1
            tmp[y][x] = s / cnt if cnt else 0.0
    # Vertikale Pass
    dst = [[0.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            s = 0.0
            cnt = 0
            for dy in range(-radius, radius + 1):
                ny = y + dy
                if 0 <= ny < h:
                    s += tmp[ny][x]
                    cnt += 1
            dst[y][x] = s / cnt if cnt else 0.0
    return dst

def weiche_schatten(karte: Tiefenkarte, licht_dir: Vec3,
                    basis_schritte: int = 32, blur_radius: int = 2) -> List[List[float]]:
    """Kombiniert Ray‑Marching mit Box‑Blur für weiche Schatten."""
    hart = harte_schatten_raymarch(karte, licht_dir, schritte=basis_schritte)
    return box_blur(hart, radius=blur_radius)

# ---------- Ausgabe & Export ----------

ASCII_RAMP = " .:-=+*#%@"

def zu_ascii(wert: float, rampe: str = ASCII_RAMP) -> str:
    idx = int(max(0.0, min(1.0, wert)) * (len(rampe) - 1))
    return rampe[idx]

def bild_zu_ascii(daten: List[List[float]], rampe: str = ASCII_RAMP) -> str:
    zeilen = []
    for reihe in daten:
        zeilen.append(''.join(zu_ascii(w, rampe) for w in reihe))
    return '\n'.join(zeilen)

def speichere_ppm(daten: List[List[float]], dateiname: str, rampe: str = ASCII_RAMP) -> bool:
    """Speichert Grauwertbild als PPM (P3 ASCII)."""
    try:
        h = len(daten)
        b = len(daten[0]) if h > 0 else 0
        with open(dateiname, 'w', encoding='ascii') as f:
            f.write(f'P3\n{b} {h}\n255\n')
            for reihe in daten:
                zeile = []
                for w in reihe:
                    val = int(max(0.0, min(1.0, w)) * 255)
                    zeile.extend([str(val), str(val), str(val)])
                f.write(' '.join(zeile) + '\n')
        return True
    except Exception as e:
        print(f'Fehler beim Speichern: {e}')
        return False

# ---------- Eingabe-Helfer ----------

def safe_input(prompt: str, default: str = '') -> str:
    """input() mit EOFError-Abwehr."""
    try:
        return input(prompt)
    except EOFError:
        print('\nEOF – schlafe weiter.')
        sys.exit(0)

def parse_vec3(s: str, default: Vec3 = (1.0, 1.0, -2.0)) -> Vec3:
    try:
        parts = s.strip().split()
        if len(parts) != 3:
            raise ValueError
        x, y, z = map(float, parts)
        if x == 0 and y == 0 and z == 0:
            raise ValueError
        return (x, y, z)
    except Exception:
        print(f'  Ungültig, nehme {default}.')
        return default

def parse_int(s: str, default: int, lo: int, hi: int) -> int:
    try:
        v = int(s.strip())
        if v < lo or v > hi:
            raise ValueError
        return v
    except Exception:
        print(f'  Ungültig, nehme {default}.')
        return default

def parse_float(s: str, default: float, lo: float, hi: float) -> float:
    try:
        v = float(s.strip())
        if v < lo or v > hi:
            raise ValueError
        return v
    except Exception:
        print(f'  Ungültig, nehme {default}.')
        return default

# ---------- Hauptlogik ----------

def waehle_form() -> Tiefenkarte:
    print('\n=== Schatten‑Simulator (Teil 24) ===')
    print('Formen: 1=Kugel, 2=Kegel, 3=Stufenpyramide, 4=Wellblech')
    wahl = safe_input('Form wählen [1‑4]: ').strip()
    if wahl == '1':
        return erzeuge_kugel()
    elif wahl == '2':
        return erzeuge_kegel()
    elif wahl == '3':
        return erzeuge_stufenpyramide()
    elif wahl == '4':
        return erzeuge_wellblech()
    else:
        print('  Ungültig, nehme Kugel.')
        return erzeuge_kugel()

def waehle_licht() -> Vec3:
    s = safe_input('Lichtrichtung als drei Zahlen (x y z), z.B. "1 1 -2": ')
    return parse_vec3(s)

def waehle_samples() -> int:
    s = safe_input('Schatten‑Samples (Ray‑March Steps) [8‑64]: ')
    return parse_int(s, 32, 8, 64)

def waehle_blur() -> int:
    s = safe_input('Weichzeichner‑Radius [0‑4]: ')
    return parse_int(s, 2, 0, 4)

def waehle_zskalierung() -> float:
    s = safe_input('Normalen‑Z‑Skalierung [0.5‑5.0]: ')
    return parse_float(s, 2.0, 0.5, 5.0)

def main_interaktiv() -> None:
    karte = waehle_form()
    licht = waehle_licht()
    samples = waehle_samples()
    blur_r = waehle_blur()
    z_skal = waehle_zskalierung()

    print('\nBerechne Normalen …')
    normals = karte.normalen(z_skalierung=z_skal)

    print('Berechne diffuse Beleuchtung …')
    diffuse = diffuse_schatten(normals, licht)

    print(f'Ray‑Marching ({samples} Schritte) …')
    if blur_r > 0:
        schatten = weiche_schatten(karte, licht, basis_schritte=samples, blur_radius=blur_r)
    else:
        schatten = harte_schatten_raymarch(karte, licht, schritte=samples)

    # Kombinieren: diffuse * schatten
    komb = [[diffuse[y][x] * schatten[y][x] for x in range(karte.b)] for y in range(karte.h)]

    print('\n--- ASCII‑Vorschau ---')
    print(bild_zu_ascii(komb))
    print('\n--- Nur Schatten ---')
    print(bild_zu_ascii(schatten))
    print('\n--- Nur Diffuse ---')
    print(bild_zu_ascii(diffuse))

    speichern = safe_input('\nAls PPM speichern? (j/n): ').strip().lower()
    if speichern == 'j':
        name = safe_input('Dateiname [schatten.ppm]: ').strip()
        if not name:
            name = 'schatten.ppm'
        if not name.endswith('.ppm'):
            name += '.ppm'
        if speichere_ppm(komb, name):
            print(f'Gespeichert: {name}')
        else:
            print('Speichern fehlgeschlagen.')

def main_batch() -> None:
    """Batch‑Modus: rendert alle Formen mit Standard‑Parametern."""
    formen = {
        'kugel': erzeuge_kugel(),
        'kegel': erzeuge_kegel(),
        'pyramide': erzeuge_stufenpyramide(),
        'wellblech': erzeuge_wellblech(),
    }
    licht = (1.0, 1.0, -2.0)
    samples = 32
    blur = 2
    z_skal = 2.0

    print('\n=== Batch‑Modus: alle Formen ===')
    for name, karte in formen.items():
        print(f'\n--- {name} ---')
        normals = karte.normalen(z_skalierung=z_skal)
        diffuse = diffuse_schatten(normals, licht)
        schatten = weiche_schatten(karte, licht, basis_schritte=samples, blur_radius=blur)
        komb = [[diffuse[y][x] * schatten[y][x] for x in range(karte.b)] for y in range(karte.h)]
        print(bild_zu_ascii(komb))
        fname = f'{name}.ppm'
        if speichere_ppm(komb, fname):
            print(f'Gespeichert: {fname}')
    print('\nBatch fertig.')

def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == '--batch':
        main_batch()
    else:
        main_interaktiv()

if __name__ == '__main__':
    main()