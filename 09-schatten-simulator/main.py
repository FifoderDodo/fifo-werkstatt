from __future__ import annotations
import math
import sys
import random
from typing import List, Tuple, Optional

Vec3 = Tuple[float, float, float]

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
    # Lichtrichtung zeigt von der Oberfläche zur Lichtquelle.
    # Wir marschieren von der Oberfläche in Richtung Lichtquelle.
    # Schrittweite in xy-Ebene so, dass wir maximal schritte Schritte bis zum Rand machen.
    max_d = math.sqrt(h * h + b * b)
    step_xy = max_d / schritte
    # Normierte xy-Komponente der Lichtrichtung
    l_xy = math.sqrt(lx * lx + ly * ly)
    if l_xy < 1e-6:
        # Licht kommt von genau oben -> keine Schatten
        return [[1.0] * b for _ in range(h)]
    inv_xy = 1.0 / l_xy
    dir_x = lx * inv_xy * step_xy
    dir_y = ly * inv_xy * step_xy
    step_z = lz * inv_xy * step_xy  # Höhenänderung pro Schritt (Höhenwerte 0-1, xy in Pixeln)

    shadow = [[1.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            h0 = karte.daten[y][x]
            # Startpunkt leicht versetzt (bias) um Selbstschatten-Artefakte zu vermeiden
            cx = x + 0.5 + dir_x * bias
            cy = y + 0.5 + dir_y * bias
            cz = h0 + step_z * bias
            blocked = False
            for _ in range(schritte):
                cx += dir_x
                cy += dir_y
                cz += step_z
                if cx < 0.5 or cx >= b - 0.5 or cy < 0.5 or cy >= h - 0.5:
                    break
                h_map = karte.get_bilinear(cy, cx)
                if h_map > cz:
                    blocked = True
                    break
            if blocked:
                shadow[y][x] = 0.0
    return shadow

def box_blur(src: List[List[float]], radius: int) -> List[List[float]]:
    """Einfacher Box-Blur (separabel) für weiche Schatten."""
    if radius <= 0:
        return src
    h = len(src)
    b = len(src[0]) if h > 0 else 0
    # Horizontale Pass
    tmp = [[0.0] * b for _ in range(h)]
    for y in range(h):
        row = src[y]
        sum_val = 0.0
        # Initialer Fensterbereich
        for x in range(-radius, radius + 1):
            ix = max(0, min(b - 1, x))
            sum_val += row[ix]
        for x in range(b):
            tmp[y][x] = sum_val / (2 * radius + 1)
            # Fenster verschieben
            left = max(0, x - radius)
            right = min(b - 1, x + radius + 1)
            if right < b:
                sum_val += row[right] - row[left]
    # Vertikale Pass
    dst = [[0.0] * b for _ in range(h)]
    for x in range(b):
        sum_val = 0.0
        for y in range(-radius, radius + 1):
            iy = max(0, min(h - 1, y))
            sum_val += tmp[iy][x]
        for y in range(h):
            dst[y][x] = sum_val / (2 * radius + 1)
            top = max(0, y - radius)
            bottom = min(h - 1, y + radius + 1)
            if bottom < h:
                sum_val += tmp[bottom][x] - tmp[top][x]
    return dst

def ascii_export(werte: List[List[float]], zeichen: str = "@%#*+=-:. ") -> str:
    """Wandelt ein 2D-Array von 0-1 Werten in ASCII-Art um."""
    h = len(werte)
    if h == 0:
        return ""
    b = len(werte[0])
    n = len(zeichen) - 1
    lines = []
    for y in range(h):
        line_chars = []
        for x in range(b):
            v = max(0.0, min(1.0, werte[y][x]))
            idx = int(v * n)
            line_chars.append(zeichen[idx])
        lines.append(''.join(line_chars))
    return '\n'.join(lines)

def save_ppm(dateiname: str, werte: List[List[float]], farbton: Tuple[int, int, int] = (255, 255, 255)) -> None:
    """Speichert ein Grauwertbild als PPM (P3 ASCII)."""
    h = len(werte)
    if h == 0:
        return
    b = len(werte[0])
    r_mult, g_mult, b_mult = farbton
    with open(dateiname, 'w') as f:
        f.write(f'P3\n{b} {h}\n255\n')
        for y in range(h):
            line_vals = []
            for x in range(b):
                v = max(0.0, min(1.0, werte[y][x]))
                r = int(v * r_mult)
                g = int(v * g_mult)
                b_val = int(v * b_mult)
                line_vals.extend([str(r), str(g), str(b_val)])
            f.write(' '.join(line_vals) + '\n')

# ---------- Hauptprogramm ----------

def main() -> None:
    print("Schatten-Simulator – Teil 31")
    print("Formen: 1=Kugel, 2=Kegel, 3=Stufenpyramide, 4=Wellblech")
    while True:
        try:
            eingabe = input("Form wählen (1-4, Enter=Kugel): ").strip()
        except EOFError:
            print("\nTschüss!")
            break
        if eingabe == '':
            form = 1
        else:
            try:
                form = int(eingabe)
            except ValueError:
                print("Ungültige Eingabe, versuch's nochmal.")
                continue
        if form not in (1, 2, 3, 4):
            print("Ungültige Form, versuch's nochmal.")
            continue

        if form == 1:
            karte = erzeuge_kugel()
        elif form == 2:
            karte = erzeuge_kegel()
        elif form == 3:
            karte = erzeuge_stufenpyramide()
        else:
            karte = erzeuge_wellblech()

        # Lichtrichtung
        try:
            licht_eingabe = input("Lichtrichtung (x y z) oder Enter für Standard (1, -1, 2): ").strip()
        except EOFError:
            print("\nTschüss!")
            break
        if licht_eingabe == '':
            licht_dir = (1.0, -1.0, 2.0)
        else:
            parts = licht_eingabe.split()
            if len(parts) != 3:
                print("Ungültige Lichtrichtung, verwende Standard.")
                licht_dir = (1.0, -1.0, 2.0)
            else:
                try:
                    licht_dir = (float(parts[0]), float(parts[1]), float(parts[2]))
                except ValueError:
                    print("Ungültige Lichtrichtung, verwende Standard.")
                    licht_dir = (1.0, -1.0, 2.0)

        # Blur-Radius
        try:
            blur_eingabe = input("Blur-Radius für weiche Schatten (Enter=0): ").strip()
        except EOFError:
            print("\nTschüss!")
            break
        if blur_eingabe == '':
            blur_radius = 0
        else:
            try:
                blur_radius = int(blur_eingabe)
                if blur_radius < 0:
                    blur_radius = 0
            except ValueError:
                print("Ungültiger Radius, verwende 0.")
                blur_radius = 0

        # Berechnungen
        normals = karte.normalen()
        diffuse = diffuse_schatten(normals, licht_dir)
        hard_shadow = harte_schatten_raymarch(karte, licht_dir)
        if blur_radius > 0:
            soft_shadow = box_blur(hard_shadow, blur_radius)
            shadow = soft_shadow
        else:
            shadow = hard_shadow

        # Kombiniere diffus und Schatten
        combined = [[diffuse[y][x] * shadow[y][x] for x in range(karte.b)] for y in range(karte.h)]

        # ASCII Ausgabe
        print("\nSchatten (ASCII):")
        print(ascii_export(shadow, "##@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@"))
        print("\nKombiniert (ASCII):")
        print(ascii_export(combined, "@%#*+=-:. "))

        # PPM speichern
        dateiname = "shadow.ppm"
        save_ppm(dateiname, combined, (255, 200, 150))
        print(f"\nGespeichert als {dateiname}")
        print("---")

if __name__ == "__main__":
    main()