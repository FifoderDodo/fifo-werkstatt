# main.py – Schatten‑Simulator, Teil 18
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

    schatten: List[List[float]] = [[1.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            height = karte.daten[y][x]
            if height <= 0.0:
                continue
            cx = x + dir_x
            cy = y + dir_y
            cz = height + step_z + bias
            blocked = False
            for _ in range(schritte):
                if cx < 0 or cx >= b or cy < 0 or cy >= h:
                    break
                sample_h = karte.get_bilinear(cy, cx)
                if sample_h > cz:
                    blocked = True
                    break
                cx += dir_x
                cy += dir_y
                cz += step_z
            if blocked:
                schatten[y][x] = 0.0
    return schatten

def box_blur(src: List[List[float]], radius: int = 1) -> List[List[float]]:
    """Einfacher Box‑Blur für weiche Schatten."""
    h = len(src)
    b = len(src[0]) if h > 0 else 0
    if radius <= 0:
        return src
    # horizontal
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
            tmp[y][x] = s / cnt
    # vertical
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
            dst[y][x] = s / cnt
    return dst

def ssao(karte: Tiefenkarte, normals: List[List[Vec3]],
         samples: int = 8, radius: float = 0.5) -> List[List[float]]:
    """Screen‑Space Ambient Occlusion – sehr vereinfacht."""
    h, b = karte.h, karte.b
    ao = [[1.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            n = normals[y][x]
            occ = 0.0
            for _ in range(samples):
                # zufälliger Vektor im Hemisphere
                u = random.random()
                v = random.random()
                theta = 2.0 * math.pi * u
                phi = math.acos(2.0 * v - 1.0)
                rx = math.sin(phi) * math.cos(theta)
                ry = math.sin(phi) * math.sin(theta)
                rz = math.cos(phi)
                # in Tangentenraum rotieren (vereinfacht: wir nutzen Normalen als Up)
                # hier nur dot mit Normalen als Approximation
                dot = n[0] * rx + n[1] * ry + n[2] * rz
                if dot <= 0:
                    continue
                sx = x + rx * radius
                sy = y + ry * radius
                sample_h = karte.get_bilinear(sy, sx)
                if sample_h > karte.daten[y][x] + 0.01:
                    occ += 1.0
            ao[y][x] = 1.0 - min(1.0, occ / samples)
    return ao

def blinn_phong(normals: List[List[Vec3]],
                light_dir: Vec3,
                view_dir: Vec3,
                shadow: List[List[float]],
                ao: List[List[float]],
                kd: float = 0.7,
                ks: float = 0.3,
                shininess: float = 32.0,
                ambient: float = 0.1) -> List[List[float]]:
    """Blinn‑Phong Beleuchtung mit Schatten und AO."""
    l = vec3_norm(light_dir)
    v = vec3_norm(view_dir)
    h_vec = vec3_norm(vec3_add(l, v))
    h, b = len(normals), len(normals[0])
    out = [[0.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            n = normals[y][x]
            ndotl = max(0.0, vec3_dot(n, l))
            ndoth = max(0.0, vec3_dot(n, h_vec))
            spec = (ndoth ** shininess) if ndotl > 0 else 0.0
            diff = kd * ndotl
            spe = ks * spec
            ao_val = ao[y][x]
            sh = shadow[y][x]
            out[y][x] = ambient * ao_val + (diff + spe) * sh * ao_val
    return out

def ascii_art(values: List[List[float]], ramp: str = " .'`^\":;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$") -> str:
    """Wandelt 2D‑Float‑Array in ASCII‑Art um."""
    lines = []
    for row in values:
        line = []
        for v in row:
            idx = int(max(0.0, min(1.0, v)) * (len(ramp) - 1))
            line.append(ramp[idx])
        lines.append(''.join(line))
    return '\n'.join(lines)

def wähle_form() -> Tiefenkarte:
    print("\n=== Formen ===")
    print("1: Kugel")
    print("2: Kegel")
    print("3: Stufenpyramide")
    print("4: Wellblech")
    while True:
        try:
            choice = input("Wähle (1‑4): ").strip()
        except EOFError:
            print("\nTschüss!")
            sys.exit(0)
        if choice == '1':
            return erzeuge_kugel()
        elif choice == '2':
            return erzeuge_kegel()
        elif choice == '3':
            return erzeuge_stufenpyramide()
        elif choice == '4':
            return erzeuge_wellblech()
        else:
            print("Ungültig, nochmal.")

def wähle_licht() -> Vec3:
    print("\n=== Lichtrichtung ===")
    print("1: Von oben (0,0,1)")
    print("2: Von vorne‑links (1,1,2)")
    print("3: Von der Seite (1,0,1)")
    print("4: Eigenes (x y z)")
    while True:
        try:
            choice = input("Wähle (1‑4): ").strip()
        except EOFError:
            print("\nTschüss!")
            sys.exit(0)
        if choice == '1':
            return (0.0, 0.0, 1.0)
        elif choice == '2':
            return (1.0, 1.0, 2.0)
        elif choice == '3':
            return (1.0, 0.0, 1.0)
        elif choice == '4':
            try:
                vals = input("x y z: ").split()
                if len(vals) == 3:
                    return (float(vals[0]), float(vals[1]), float(vals[2]))
            except ValueError:
                pass
            print("Ungültig, nochmal.")
        else:
            print("Ungültig, nochmal.")

def main() -> None:
    random.seed(42)
    print("=== Schatten‑Simulator ===")
    karte = wähle_form()
    licht = wähle_licht()
    view = (0.0, 0.0, 1.0)  # feste View‑Richtung

    print("\nBerechne Normalen …")
    normals = karte.normalen()

    print("Berechne harte Schatten …")
    hart = harte_schatten_raymarch(karte, licht)

    print("Weiche Schatten (Blur) …")
    weich = box_blur(hart, radius=2)

    print("SSAO …")
    ao = ssao(karte, normals)

    print("Blinn‑Phong Shading …")
    shading = blinn_phong(normals, licht, view, weich, ao)

    print("\n=== Ergebnis ===")
    print(ascii_art(shading))

    # Optional: Tiefenkarte als ASCII
    print("\n=== Tiefenkarte ===")
    print(ascii_art(karte.daten))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbbruch.")
    except Exception as e:
        print(f"Fehler: {e}")
        sys.exit(1)