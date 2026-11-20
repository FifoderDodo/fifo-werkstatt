# main.py – Schatten-Simulator, Teil 13
# Fifo, der Dodo, träumt weiter: Blinn-Phong, AO, weiche Schatten – alles fein verwoben.
# Neue Form 'Wellblech' hinzugefügt, Menü erweitert, kleiner Bugfix bei weichen Schatten (Sample-Count).

from __future__ import annotations
import math
import sys
import random
from typing import List, Tuple, Optional

Vec3 = Tuple[float, float, float]


def vec3_norm(v: Vec3) -> Vec3:
    x, y, z = v
    l = math.sqrt(x * x + y * y + z * z)
    if l < 1e-9:
        return (0.0, 0.0, 1.0)
    return (x / l, y / l, z / l)


def vec3_dot(a: Vec3, b: Vec3) -> float:
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


def vec3_add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0]+b[0], a[1]+b[1], a[2]+b[2])


def vec3_scale(v: Vec3, s: float) -> Vec3:
    return (v[0]*s, v[1]*s, v[2]*s)


class Tiefenkarte:
    """Hält ein 2D-Höhenfeld und berechnet Oberflächenableitungen (Normalen)."""

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
        normals = []
        for y in range(self.h):
            reihe = []
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


def erzeuge_kugel(h: int = 20, b: int = 40, r_rel: float = 0.42) -> Tiefenkarte:
    karte = [[0.0 for _ in range(b)] for _ in range(h)]
    cy, cx = (h - 1) / 2.0, (b - 1) / 2.0
    radius = min(h, b) * r_rel
    for y in range(h):
        for x in range(b):
            dy = (y - cy)
            dx = (x - cx) * 0.5  # Aspektkorrektur für Terminal-Zeichen
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
            dy = (y - cy)
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
    """Erzeugt ein wellenförmiges Höhenfeld (wie Wellblech)."""
    karte = [[0.0 for _ in range(b)] for _ in range(h)]
    for y in range(h):
        for x in range(b):
            # Wellen in x-Richtung, leicht moduliert in y
            val = 0.5 + 0.5 * math.sin(2.0 * math.pi * wellen * x / b + 0.5 * math.sin(2.0 * math.pi * y / h))
            karte[y][x] = val
    return Tiefenkarte(karte)


def diffuse_schatten(normals: List[List[Vec3]], licht_dir: Vec3) -> List[List[float]]:
    lx, ly, lz = vec3_norm(licht_dir)
    hell = []
    for reihe in normals:
        h_reihe = []
        for nx, ny, nz in reihe:
            dot = nx * lx + ny * ly + nz * lz
            h_reihe.append(max(0.0, dot))
        hell.append(h_reihe)
    return hell


def harte_schatten_raymarch(karte: Tiefenkarte, licht_dir: Vec3,
                             schritte: int = 32, bias: float = 0.005) -> List[List[float]]:
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

    schatten = []
    for y in range(h):
        reihe = []
        for x in range(b):
            cur_h = karte.get(y, x) + bias
            cx, cy = float(x), float(y)
            im_schatten = False
            for _ in range(schritte):
                cx += dir_x
                cy += dir_y
                cur_h += step_z
                if not (0 <= cx < b - 1 and 0 <= cy < h - 1):
                    break
                if karte.get_bilinear(cy, cx) > cur_h:
                    im_schatten = True
                    break
            reihe.append(0.0 if im_schatten else 1.0)
        schatten.append(reihe)
    return schatten


def weiche_schatten_raymarch(karte: Tiefenkarte, licht_dir: Vec3,
                              schritte: int = 24, samples: int = 4,
                              bias: float = 0.005) -> List[List[float]]:
    h, b = karte.h, karte.b
    akkumulator = [[0.0] * b for _ in range(h)]
    rng = random.Random(42)
    lx, ly, lz = vec3_norm(licht_dir)
    
    for _ in range(samples):
        # Jitter: leicht zufällige Änderung der Lichtrichtung
        jitter = 0.15
        jx = lx + rng.uniform(-jitter, jitter)
        jy = ly + rng.uniform(-jitter, jitter)
        jz = lz + rng.uniform(-jitter, jitter)
        jitter_dir = vec3_norm((jx, jy, jz))
        
        schatten = harte_schatten_raymarch(karte, jitter_dir, schritte, bias)
        for y in range(h):
            for x in range(b):
                akkumulator[y][x] += schatten[y][x]
    
    # Durchschnitt bilden
    inv_samples = 1.0 / samples
    for y in range(h):
        for x in range(b):
            akkumulator[y][x] *= inv_samples
    return akkumulator


def ambient_occlusion(normals: List[List[Vec3]], karte: Tiefenkarte,
                       radius: float = 2.0, samples: int = 8) -> List[List[float]]:
    """Screen-Space Ambient Occlusion (sehr vereinfacht)."""
    h, b = karte.h, karte.b
    ao = [[1.0] * b for _ in range(h)]
    rng = random.Random(123)
    for y in range(h):
        for x in range(b):
            n = normals[y][x]
            occ = 0
            for _ in range(samples):
                # Zufällige Richtung in der Hemisphäre
                theta = rng.uniform(0, math.pi/2)
                phi = rng.uniform(0, 2*math.pi)
                dx = math.sin(theta) * math.cos(phi)
                dy = math.sin(theta) * math.sin(phi)
                dz = math.cos(theta)
                # In Weltkoordinaten (vereinfacht: Tangentenraum ~ Normalen)
                # Wir projizieren einfach entlang der Normalen und prüfen Höhenfeld
                step = radius / 4.0
                cx, cy = float(x), float(y)
                ch = karte.get(y, x)
                hit = False
                for _ in range(4):
                    cx += dx * step
                    cy += dy * step
                    ch += dz * step * 0.1
                    if not (0 <= cx < b-1 and 0 <= cy < h-1):
                        break
                    if karte.get_bilinear(cy, cx) > ch:
                        hit = True
                        break
                if hit:
                    occ += 1
            ao[y][x] = 1.0 - (occ / samples) * 0.5  # Abschwächen für subtilen Effekt
    return ao


def blinn_phong(normals: List[List[Vec3]], licht_dir: Vec3,
                 view_dir: Vec3 = (0.0, 0.0, 1.0),
                 spec_exp: float = 32.0) -> List[List[float]]:
    """Blinn-Phong Specular Highlights."""
    l = vec3_norm(licht_dir)
    v = vec3_norm(view_dir)
    # Half vector
    h = vec3_norm(vec3_add(l, v))
    spec = []
    for reihe in normals:
        s_reihe = []
        for n in reihe:
            nh = max(0.0, vec3_dot(n, h))
            s_reihe.append(nh ** spec_exp)
        spec.append(s_reihe)
    return spec


def compose(diffuse: List[List[float]], shadow: List[List[float]],
            ao: List[List[float]], spec: List[List[float]],
            ambience: float = 0.2, spec_weight: float = 0.5) -> List[List[float]]:
    """Kombiniert alle Beleuchtungskomponenten."""
    h = len(diffuse)
    b = len(diffuse[0]) if h > 0 else 0
    result = [[0.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            d = diffuse[y][x]
            s = shadow[y][x]
            a = ao[y][x]
            sp = spec[y][x]
            # Diffuse * Shadow + Ambient * AO + Specular * Shadow
            val = d * s + ambience * a + spec_weight * sp * s
            result[y][x] = max(0.0, min(1.0, val))
    return result


def render_ascii(values: List[List[float]], invert: bool = False) -> str:
    """Wandelt 0..1 Werte in ASCII-Zeichen um."""
    # Zeichen von dunkel nach hell
    chars = "@%#*+=-:. "
    if invert:
        chars = chars[::-1]
    lines = []
    for reihe in values:
        line = []
        for v in reihe:
            idx = int(v * (len(chars) - 1))
            line.append(chars[idx])
        lines.append(''.join(line))
    return '\n'.join(lines)


def menu() -> str:
    return (
        "\n🦤 Schatten-Simulator – Menü:\n"
        "  1 – Harte Schatten (Raymarch)\n"
        "  2 – Weiche Schatten (Raymarch + Jitter)\n"
        "  3 – Ambient Occlusion (SSAO)\n"
        "  4 – Blinn-Phong Specular\n"
        "  5 – Vollbild (Blinn-Phong + Schatten + AO)\n"
        "  6 – Tiefenform wählen (Kugel, Kegel, Pyramide, Wellblech)\n"
        "  7 – Lichtrichtung anpassen\n"
        "  8 – Höhen-Rohdaten anzeigen\n"
        "  0 – Beenden\n"
        "🦤 Fifo fragt: Deine Wahl? "
    )


def main() -> None:
    karte = erzeuge_kugel()
    licht = (0.5, -0.3, 1.0)  # Standardlicht
    form_name = "Kugel"
    forms = {
        '1': ('Kugel', erzeuge_kugel),
        '2': ('Kegel', erzeuge_kegel),
        '3': ('Pyramide', erzeuge_stufenpyramide),
        '4': ('Wellblech', erzeuge_wellblech),
    }
    
    while True:
        try:
            print(menu())
            wahl = input().strip()
        except EOFError:
            print("\n🦤 Fifo nickt ein. Gute Nacht!")
            break
        
        if wahl == '0':
            print("🦤 Fifo watschelt davon. Bis zum nächsten Traum!")
            break
        elif wahl == '1':
            normals = karte.normalen()
            diffuse = diffuse_schatten(normals, licht)
            shadow = harte_schatten_raymarch(karte, licht)
            composed = [[diffuse[y][x] * shadow[y][x] for x in range(karte.b)] for y in range(karte.h)]
            print(render_ascii(composed))
        elif wahl == '2':
            normals = karte.normalen()
            diffuse = diffuse_schatten(normals, licht)
            shadow = weiche_schatten_raymarch(karte, licht)
            composed = [[diffuse[y][x] * shadow[y][x] for x in range(karte.b)] for y in range(karte.h)]
            print(render_ascii(composed))
        elif wahl == '3':
            normals = karte.normalen()
            ao = ambient_occlusion(normals, karte)
            print(render_ascii(ao, invert=True))  # AO invertiert: dunkel = Okklusion
        elif wahl == '4':
            normals = karte.normalen()
            spec = blinn_phong(normals, licht)
            print(render_ascii(spec))
        elif wahl == '5':
            normals = karte.normalen()
            diffuse = diffuse_schatten(normals, licht)
            shadow = weiche_schatten_raymarch(karte, licht)
            ao = ambient_occlusion(normals, karte)
            spec = blinn_phong(normals, licht)
            composed = compose(diffuse, shadow, ao, spec)
            print(render_ascii(composed))
        elif wahl == '6':
            print("  1 – Kugel")
            print("  2 – Kegel")
            print("  3 – Pyramide")
            print("  4 – Wellblech")
            try:
                f = input("  Form wählen: ").strip()
            except EOFError:
                break
            if f in forms:
                name, func = forms[f]
                karte = func()
                form_name = name
                print(f"🦤 Form geändert zu {form_name}.")
            else:
                print("🦤 Unbekannte Form.")
        elif wahl == '7':
            try:
                print(f"  Aktuelles Licht: {licht}")
                lx = float(input("  Licht X: ").strip())
                ly = float(input("  Licht Y: ").strip())
                lz = float(input("  Licht Z: ").strip())
                licht = (lx, ly, lz)
                print(f"🦤 Licht gesetzt auf {licht}.")
            except ValueError:
                print("🦤 Ungültige Zahlen.")
            except EOFError:
                break
        elif wahl == '8':
            print(render_ascii(karte.daten, invert=True))
        else:
            print("🦤 Unbekannte Option.")

if __name__ == "__main__":
    main()