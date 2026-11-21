# main.py – Schatten‑Simulator, Teil 19
# Fifo, der Dodo, träumt weiter: Fehler behoben, Ray‑March‑Loop fertig, weiche Schatten, AO, Blinn‑Phong, Menü und Rendering.

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
    step_z = lz * inv_xy * step_xy * 0.1  # 0.1 ≈ Z‑Skalierung der Tiefenkarte

    schatten: List[List[float]] = [[1.0 for _ in range(b)] for _ in range(h)]
    for y in range(h):
        for x in range(b):
            h_here = karte.daten[y][x]
            if h_here <= 0.0:
                continue
            cx = x + bias * lx
            cy = y + bias * ly
            cz = h_here + bias * lz
            blocked = False
            for _ in range(schritte):
                cx += dir_x
                cy += dir_y
                cz += step_z
                if cx < 0 or cx >= b - 1 or cy < 0 or cy >= h - 1:
                    break
                h_sample = karte.get_bilinear(cy, cx)
                if cz <= h_sample:
                    blocked = True
                    break
            if blocked:
                schatten[y][x] = 0.0
    return schatten

def weiche_schatten(harte: List[List[float]], radius: int = 2) -> List[List[float]]:
    """Box‑Blur für weiche Schatten."""
    h = len(harte)
    b = len(harte[0])
    tmp = [[0.0] * b for _ in range(h)]
    # horizontal
    for y in range(h):
        s = 0.0
        for x in range(b):
            s += harte[y][x]
            if x - radius - 1 >= 0:
                s -= harte[y][x - radius - 1]
            if x + radius < b:
                s += harte[y][x + radius]
            tmp[y][x] = s / (min(x + radius, b - 1) - max(x - radius, 0) + 1)
    # vertical
    result = [[0.0] * b for _ in range(h)]
    for x in range(b):
        s = 0.0
        for y in range(h):
            s += tmp[y][x]
            if y - radius - 1 >= 0:
                s -= tmp[y - radius - 1][x]
            if y + radius < h:
                s += tmp[y + radius][x]
            result[y][x] = s / (min(y + radius, h - 1) - max(y - radius, 0) + 1)
    return result

def ssao(karte: Tiefenkarte, normals: List[List[Vec3]], samples: int = 8, radius: float = 0.5) -> List[List[float]]:
    """Screen‑Space Ambient Occlusion – sehr vereinfacht."""
    h, b = karte.h, karte.b
    ao = [[1.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            if karte.daten[y][x] <= 0.0:
                continue
            n = normals[y][x]
            occ = 0
            for _ in range(samples):
                # zufällige Richtung in Hemisphäre
                u = random.random()
                v = random.random()
                phi = 2.0 * math.pi * u
                cos_theta = math.sqrt(1.0 - v)
                sin_theta = math.sqrt(v)
                # tangent space -> world
                # wir nutzen einfach die Normalen als Up‑Vektor
                # und bauen ein orthonormales System
                if abs(n[2]) < 0.9:
                    tangent = vec3_norm(vec3_sub((0, 0, 1), vec3_scale(n, n[2])))
                else:
                    tangent = vec3_norm(vec3_sub((0, 1, 0), vec3_scale(n, n[1])))
                bitangent = (n[1] * tangent[2] - n[2] * tangent[1],
                             n[2] * tangent[0] - n[0] * tangent[2],
                             n[0] * tangent[1] - n[1] * tangent[0])
                dir_vec = vec3_add(vec3_add(vec3_scale(tangent, sin_theta * math.cos(phi)),
                                            vec3_scale(bitangent, sin_theta * math.sin(phi))),
                                   vec3_scale(n, cos_theta))
                # sample
                sx = x + dir_vec[0] * radius
                sy = y + dir_vec[1] * radius
                if 0 <= sx < b - 1 and 0 <= sy < h - 1:
                    h_sample = karte.get_bilinear(sy, sx)
                    if h_sample > karte.daten[y][x] + 0.01:
                        occ += 1
            ao[y][x] = 1.0 - occ / samples
    return ao

def blinn_phong(normals: List[List[Vec3]], licht_dir: Vec3, view_dir: Vec3,
                diffuse: List[List[float]], shadow: List[List[float]], ao: List[List[float]],
                shininess: float = 32.0) -> List[List[float]]:
    """Blinn‑Phong Shading kombiniert mit Schatten und AO."""
    l = vec3_norm(licht_dir)
    v = vec3_norm(view_dir)
    h_vec = vec3_norm(vec3_add(l, v))
    h, b = len(normals), len(normals[0])
    out = [[0.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            n = normals[y][x]
            ndotl = max(0.0, vec3_dot(n, l))
            ndoth = max(0.0, vec3_dot(n, h_vec))
            spec = ndoth ** shininess if ndotl > 0 else 0.0
            diff = diffuse[y][x] * shadow[y][x] * ao[y][x]
            out[y][x] = min(1.0, diff + 0.5 * spec)
    return out

def zu_ascii(werte: List[List[float]], palette: str = " .'`^\":;~!><{}[]()#&@$") -> List[str]:
    """Wandelt 0‑1 Werte in ASCII‑Zeilen um."""
    h, b = len(werte), len(werte[0])
    lines = []
    for y in range(h):
        line = []
        for x in range(b):
            v = max(0.0, min(1.0, werte[y][x]))
            idx = int(v * (len(palette) - 1))
            line.append(palette[idx])
        lines.append(''.join(line))
    return lines

# ---------- Interaktives Menü ----------

def menue() -> None:
    print("=== Schatten‑Simulator (Teil 19) ===")
    print("Formen: 1=Kugel, 2=Kegel, 3=Stufenpyramide, 4=Wellblech")
    try:
        wahl = input("Form wählen [1‑4]: ").strip()
    except EOFError:
        print("\nKeine Eingabe – Tschüss!")
        return
    if wahl == '1':
        karte = erzeuge_kugel()
    elif wahl == '2':
        karte = erzeuge_kegel()
    elif wahl == '3':
        karte = erzeuge_stufenpyramide()
    elif wahl == '4':
        karte = erzeuge_wellblech()
    else:
        print("Ungültig, nehme Kugel.")
        karte = erzeuge_kugel()

    print('Lichtrichtung als drei Zahlen (x y z), z.B. "1 1 -2":')
    try:
        lx, ly, lz = map(float, input("> ").split())
    except (ValueError, EOFError):
        print("Ungültig, nehme Standard (1, 1, -2).")
        lx, ly, lz = 1.0, 1.0, -2.0
    licht = (lx, ly, lz)

    print("Schatten‑Samples (Ray‑March Steps) [8‑64, Standard 32]:")
    try:
        schritte = int(input("> ").strip() or "32")
    except (ValueError, EOFError):
        schritte = 32

    print("Weichzeichner‑Radius für weiche Schatten [0‑5, Standard 2]:")
    try:
        blur_r = int(input("> ").strip() or "2")
    except (ValueError, EOFError):
        blur_r = 2

    print("Berechne Normalen …")
    normals = karte.normalen()
    print("Diffuse Beleuchtung …")
    diffuse = diffuse_schatten(normals, licht)
    print("Harte Schatten (Ray‑March) …")
    harte = harte_schatten_raymarch(karte, licht, schritte=schritte)
    print("Weiche Schatten …")
    weiche = weiche_schatten(harte, radius=blur_r)
    print("SSAO …")
    ao = ssao(karte, normals)
    print("Blinn‑Phong Shading …")
    view = (0.0, 0.0, 1.0)  # Kamera schaut von oben
    shaded = blinn_phong(normals, licht, view, diffuse, weiche, ao)
    print("ASCII‑Art …")
    ascii_lines = zu_ascii(shaded)
    for line in ascii_lines:
        print(line)
    print("\nFertig. Drücke Enter für Ende.")
    try:
        input()
    except EOFError:
        pass

if __name__ == "__main__":
    menue()