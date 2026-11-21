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
    step_z = lz * inv_xy * step_xy * 0.1  # Skalierung, weil Höhenwerte 0‑1, xy in Pixeln

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
                h_sample = karte.get_bilinear(cy, cx)
                if cz <= h_sample:
                    blocked = True
                    break
            if blocked:
                shadow[y][x] = 0.0
    return shadow

def box_blur(image: List[List[float]], radius: int) -> List[List[float]]:
    """Einfacher Box‑Blur (separabel) für weiche Schatten."""
    if radius <= 0:
        return image
    h = len(image)
    b = len(image[0])
    # horizontale Pass
    temp = [[0.0] * b for _ in range(h)]
    for y in range(h):
        row = image[y]
        prefix = [0.0] * (b + 1)
        for x in range(b):
            prefix[x + 1] = prefix[x] + row[x]
        for x in range(b):
            x0 = max(0, x - radius)
            x1 = min(b - 1, x + radius)
            total = prefix[x1 + 1] - prefix[x0]
            count = x1 - x0 + 1
            temp[y][x] = total / count
    # vertikale Pass
    result = [[0.0] * b for _ in range(h)]
    for x in range(b):
        prefix = [0.0] * (h + 1)
        for y in range(h):
            prefix[y + 1] = prefix[y] + temp[y][x]
        for y in range(h):
            y0 = max(0, y - radius)
            y1 = min(h - 1, y + radius)
            total = prefix[y1 + 1] - prefix[y0]
            count = y1 - y0 + 1
            result[y][x] = total / count
    return result

def ascii_art(shadow: List[List[float]]) -> str:
    """Wandelt Schattenwerte in ASCII‑Art um."""
    chars = " .:-=+*#%@"
    h = len(shadow)
    b = len(shadow[0])
    lines = []
    for y in range(h):
        line = ''.join(chars[min(int(shadow[y][x] * (len(chars) - 1)), len(chars) - 1)] for x in range(b))
        lines.append(line)
    return '\n'.join(lines)

def save_ppm(shadow: List[List[float]], filename: str = "shadow.ppm") -> None:
    """Speichert das Schattenbild als Graustufen‑PPM (P5)."""
    h = len(shadow)
    b = len(shadow[0])
    with open(filename, 'wb') as f:
        f.write(f"P5\n{b} {h}\n255\n".encode())
        for y in range(h):
            for x in range(b):
                val = int(max(0.0, min(1.0, shadow[y][x])) * 255)
                f.write(bytes([val]))

# ---------- Interaktiver Hauptloop ----------

def main() -> None:
    print("Schatten-Simulator – Interaktiv")
    print("Formen: 1=Kugel, 2=Kegel, 3=Stufenpyramide, 4=Wellblech")
    while True:
        try:
            shape_input = input("Form wählen (1‑4, Enter=Kugel): ").strip()
        except EOFError:
            print("\nTschüss!")
            break
        if shape_input == '':
            shape = 1
        elif shape_input in ('1', '2', '3', '4'):
            shape = int(shape_input)
        else:
            print("Ungültige Form.")
            continue
        if shape == 1:
            karte = erzeuge_kugel()
        elif shape == 2:
            karte = erzeuge_kegel()
        elif shape == 3:
            karte = erzeuge_stufenpyramide()
        else:
            karte = erzeuge_wellblech()
        # Lichtrichtung
        try:
            light_input = input("Lichtrichtung (x y z) oder Enter für Standard (1, -1, 2): ").strip()
        except EOFError:
            print("\nTschüss!")
            break
        if light_input == '':
            licht_dir = (1.0, -1.0, 2.0)
        else:
            parts = light_input.split()
            if len(parts) != 3:
                print("Ungültige Lichtrichtung, verwende Standard.")
                licht_dir = (1.0, -1.0, 2.0)
            else:
                try:
                    licht_dir = (float(parts[0]), float(parts[1]), float(parts[2]))
                except ValueError:
                    print("Ungültige Zahlen, verwende Standard.")
                    licht_dir = (1.0, -1.0, 2.0)
        # Blur‑Radius
        try:
            blur_input = input("Blur-Radius für weiche Schatten (Enter=0): ").strip()
        except EOFError:
            print("\nTschüss!")
            break
        if blur_input == '':
            blur_radius = 0
        else:
            try:
                blur_radius = int(blur_input)
            except ValueError:
                print("Ungültiger Radius, verwende 0.")
                blur_radius = 0
        # Berechnungen
        normals = karte.normalen()
        diffuse = diffuse_schatten(normals, licht_dir)
        hard = harte_schatten_raymarch(karte, licht_dir)
        soft_hard = box_blur(hard, blur_radius)
        combined = [[diffuse[y][x] * soft_hard[y][x] for x in range(karte.b)] for y in range(karte.h)]
        # Ausgabe
        print("\nSchatten (ASCII):")
        print(ascii_art(combined))
        save_ppm(combined)
        print("PPM gespeichert als shadow.ppm")
        print()

if __name__ == "__main__":
    main()