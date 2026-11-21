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
            shadow[y][x] = 0.0 if blocked else 1.0
    return shadow

def box_blur(bild: List[List[float]], radius: int = 1) -> List[List[float]]:
    """Einfacher Box‑Blur für weichere Schatten."""
    h = len(bild)
    b = len(bild[0]) if h > 0 else 0
    if radius <= 0:
        return bild
    result = [[0.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            s = 0.0
            cnt = 0
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    ny = y + dy
                    nx = x + dx
                    if 0 <= ny < h and 0 <= nx < b:
                        s += bild[ny][nx]
                        cnt += 1
            result[y][x] = s / cnt if cnt > 0 else 0.0
    return result

def ascii_export(bild: List[List[float]], zeichen: str = " .:-=+*#%@") -> str:
    h = len(bild)
    b = len(bild[0]) if h > 0 else 0
    if h == 0 or b == 0:
        return ""
    max_val = max(max(row) for row in bild)
    min_val = min(min(row) for row in bild)
    if max_val == min_val:
        max_val = min_val + 1.0
    scale = (len(zeichen) - 1) / (max_val - min_val)
    lines = []
    for y in range(h):
        line = []
        for x in range(b):
            val = bild[y][x]
            idx = int((val - min_val) * scale + 0.5)
            idx = max(0, min(len(zeichen) - 1, idx))
            line.append(zeichen[idx])
        lines.append(''.join(line))
    return '\n'.join(lines)

def save_ppm(bild: List[List[float]], dateiname: str) -> None:
    h = len(bild)
    b = len(bild[0]) if h > 0 else 0
    with open(dateiname, 'wb') as f:
        f.write(f"P5\n{b} {h}\n255\n".encode())
        for y in range(h):
            for x in range(b):
                val = bild[y][x]
                val = max(0.0, min(1.0, val))
                f.write(bytes([int(val * 255)]))

def main():
    print("Schatten‑Simulator – Interaktiv")
    print("Formen: 1=Kugel, 2=Kegel, 3=Stufenpyramide, 4=Wellblech")
    try:
        while True:
            try:
                form = input("Form wählen (1‑4, Enter=Kugel): ").strip()
            except EOFError:
                print("\nTschüss!")
                break
            if form == '':
                form = '1'
            if form not in ('1', '2', '3', '4'):
                print("Ungültige Form.")
                continue
            h = 20
            b = 40
            if form == '1':
                karte = erzeuge_kugel(h, b)
            elif form == '2':
                karte = erzeuge_kegel(h, b)
            elif form == '3':
                karte = erzeuge_stufenpyramide(h, b)
            else:
                karte = erzeuge_wellblech(h, b)
            print("Lichtrichtung (x y z) oder Enter für Standard (1, -1, 2):")
            try:
                licht_str = input().strip()
            except EOFError:
                print("\nTschüss!")
                break
            if licht_str == '':
                licht_dir = (1.0, -1.0, 2.0)
            else:
                parts = licht_str.split()
                if len(parts) != 3:
                    print("Drei Zahlen erwartet.")
                    continue
                try:
                    licht_dir = tuple(float(p) for p in parts)
                except ValueError:
                    print("Ungültige Zahlen.")
                    continue
            normals = karte.normalen()
            diffuse = diffuse_schatten(normals, licht_dir)
            hard = harte_schatten_raymarch(karte, licht_dir)
            # Neu: optionaler Blur für weiche Schatten
            try:
                blur_str = input("Blur‑Radius für weiche Schatten (0=kein, Enter=1): ").strip()
            except EOFError:
                print("\nTschüss!")
                break
            blur_radius = 1
            if blur_str != '':
                try:
                    blur_radius = int(blur_str)
                except ValueError:
                    print("Ungültige Zahl, nutze 1.")
            if blur_radius > 0:
                hard = box_blur(hard, blur_radius)
            # Kombinieren: diffuse * hard
            combined = [[diffuse[y][x] * hard[y][x] for x in range(b)] for y in range(h)]
            print("\nDiffuse Schatten:")
            print(ascii_export(diffuse))
            print("\nHarte Schatten (Raymarching):")
            print(ascii_export(hard))
            print("\nKombiniert:")
            print(ascii_export(combined))
            try:
                save_as = input("\nAls PPM speichern? (Dateiname oder Enter zum Überspringen): ").strip()
            except EOFError:
                print("\nTschüss!")
                break
            if save_as:
                save_ppm(combined, save_as)
                print(f"Gespeichert unter {save_as}")
            print("\n--- Nächster Durchlauf ---")
    except KeyboardInterrupt:
        print("\nAbbruch.")
    except Exception as e:
        print(f"Fehler: {e}")

if __name__ == "__main__":
    main()