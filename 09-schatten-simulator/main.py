# main.py – Schatten-Simulator, Teil 12
# Fifo, der Dodo, träumt weiter: Blinn-Phong, AO, weiche Schatten – alles fein verwoben.

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
                              schritte: int = 24, samples: int = 3,
                              bias: float = 0.005) -> List[List[float]]:
    h, b = karte.h, karte.b
    akkumulator = [[0.0] * b for _ in range(h)]
    rng = random.Random(42)
    lx, ly, lz = licht_dir
    for _ in range(samples):
        jx = lx + rng.uniform(-0.15, 0.15)
        jy = ly + rng.uniform(-0.15, 0.15)
        jz = max(0.05, lz + rng.uniform(-0.05, 0.05))
        sub = harte_schatten_raymarch(karte, (jx, jy, jz), schritte=schritte, bias=bias)
        for y in range(h):
            for x in range(b):
                akkumulator[y][x] += sub[y][x]
    for y in range(h):
        for x in range(b):
            akkumulator[y][x] /= samples
    return akkumulator


def ambient_occlusion(karte: Tiefenkarte, normals: List[List[Vec3]],
                       samples: int = 8, steps: int = 10, radius: float = 1.5) -> List[List[float]]:
    """Einfaches SSAO für Höhenfelder: zufällige Hemisphäre-Samples um die Normale."""
    h, b = karte.h, karte.b
    ao = [[1.0] * b for _ in range(h)]
    rng = random.Random(123)
    for y in range(h):
        for x in range(b):
            n = normals[y][x]
            # Basisvektoren für Tangentenraum
            if abs(n[2]) < 0.999:
                up = (0.0, 0.0, 1.0)
            else:
                up = (0.0, 1.0, 0.0)
            tx = vec3_norm((n[1]*up[2] - n[2]*up[1],
                            n[2]*up[0] - n[0]*up[2],
                            n[0]*up[1] - n[1]*up[0]))
            ty = vec3_norm((n[1]*tx[2] - n[2]*tx[1],
                            n[2]*tx[0] - n[0]*tx[2],
                            n[0]*tx[1] - n[1]*tx[0]))
            occ = 0.0
            for _ in range(samples):
                # Zufallsrichtung in Hemisphäre (cosinus-gewichtet)
                u1, u2 = rng.random(), rng.random()
                r = math.sqrt(u1)
                theta = 2.0 * math.pi * u2
                x_loc = r * math.cos(theta)
                y_loc = r * math.sin(theta)
                z_loc = math.sqrt(max(0.0, 1.0 - u1))
                # In Weltraum rotieren
                wx = tx[0]*x_loc + ty[0]*y_loc + n[0]*z_loc
                wy = tx[1]*x_loc + ty[1]*y_loc + n[1]*z_loc
                wz = tx[2]*x_loc + ty[2]*y_loc + n[2]*z_loc
                # Raymarch
                cx, cy, ch = float(x), float(y), karte.get(y, x) + 0.01
                hit = False
                for _ in range(steps):
                    cx += wx * radius / steps
                    cy += wy * radius / steps
                    ch += wz * radius / steps * 0.1
                    if not (0 <= cx < b - 1 and 0 <= cy < h - 1):
                        break
                    if karte.get_bilinear(cy, cx) > ch:
                        hit = True
                        break
                if hit:
                    occ += 1.0
            ao[y][x] = 1.0 - occ / samples
    return ao


def blinn_phong(normal: Vec3, light_dir: Vec3, view_dir: Vec3 = (0.0, 0.0, 1.0),
                 shininess: float = 32.0) -> float:
    """Blinn-Phong Spekulareterm."""
    n = vec3_norm(normal)
    l = vec3_norm(light_dir)
    v = vec3_norm(view_dir)
    h_vec = vec3_norm(vec3_add(l, v))
    ndotl = max(0.0, vec3_dot(n, l))
    ndoth = max(0.0, vec3_dot(n, h_vec))
    spec = ndotl * (ndoth ** shininess)  # nur wenn frontfacing
    return spec


def compose_vollbild(karte: Tiefenkarte, normals: List[List[Vec3]],
                      licht_dir: Vec3) -> List[List[float]]:
    """Kombiniert diffus, Schatten, AO und Spekular zu einem Bild."""
    h, b = karte.h, karte.b
    diffuse = diffuse_schatten(normals, licht_dir)
    schatten = weiche_schatten_raymarch(karte, licht_dir, schritte=16, samples=4)
    ao = ambient_occlusion(karte, normals, samples=6, steps=8)
    bild = [[0.0]*b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            n = normals[y][x]
            d = diffuse[y][x]
            s = schatten[y][x]
            a = ao[y][x]
            spec = blinn_phong(n, licht_dir)
            # Ambient 0.2, Diffus 0.6 * Schatten * AO, Spekular 0.4 * Schatten
            val = 0.2 + 0.6 * d * s * a + 0.4 * spec * s
            bild[y][x] = min(1.0, max(0.0, val))
    return bild


def als_ascii(bild: List[List[float]], ramp: str = " .:-=+*#%@") -> str:
    """Wandelt 2D-Float-Array (0-1) in ASCII-Zeilen um."""
    zeilen = []
    n = len(ramp) - 1
    for reihe in bild:
        zeile = ''.join(ramp[min(n, max(0, int(v * n)))] for v in reihe)
        zeilen.append(zeile)
    return '\n'.join(zeilen)


def drucke_roh(karte: Tiefenkarte):
    """Zeigt Höhenwerte als Zahlen-Gitter."""
    for reihe in karte.daten:
        print(' '.join(f'{v:.2f}' for v in reihe))


def menue() -> None:
    print("\n--- SCHATTEN-SIMULATOR MENÜ (Teil 12) ---")
    print("1 – Diffuse Schatten (Lambert)")
    print("2 – Harte Schatten (Raymarch)")
    print("3 – Weiche Schatten (Raymarch + Jitter)")
    print("4 – Ambient Occlusion (SSAO)")
    print("5 – Vollbild (Blinn-Phong + Schatten + AO)")
    print("6 – Tiefenform wählen (Kugel, Kegel, Pyramide)")
    print("7 – Lichtrichtung anpassen")
    print("8 – Höhen-Rohdaten anzeigen")
    print("0 – Beenden")
    print("🦤 Fifo fragt: Deine Wahl?", end=' ')


def parse_vec3(s: str) -> Optional[Vec3]:
    try:
        parts = [float(p) for p in s.replace(',', ' ').split()]
        if len(parts) == 3:
            return tuple(parts)
    except ValueError:
        pass
    return None


def main() -> None:
    random.seed(42)
    karte = erzeuge_kugel()
    licht_dir = vec3_norm((0.5, 0.3, 1.0))
    forms = {
        '1': ('Kugel', erzeuge_kugel),
        '2': ('Kegel', erzeuge_kegel),
        '3': ('Pyramide', erzeuge_stufenpyramide),
    }
    current_form = '1'

    while True:
        try:
            menue()
            wahl = input().strip()
        except EOFError:
            print("\n🦤 Fifo wacht auf. Gute Nacht!")
            break

        if wahl == '0':
            print("🦤 Fifo wacht auf. Gute Nacht!")
            break
        elif wahl == '1':
            normals = karte.normalen()
            diff = diffuse_schatten(normals, licht_dir)
            print(als_ascii(diff))
        elif wahl == '2':
            schatten = harte_schatten_raymarch(karte, licht_dir)
            print(als_ascii(schatten, ramp=" .:#"))
        elif wahl == '3':
            schatten = weiche_schatten_raymarch(karte, licht_dir)
            print(als_ascii(schatten, ramp=" .:#"))
        elif wahl == '4':
            normals = karte.normalen()
            ao = ambient_occlusion(karte, normals)
            print(als_ascii(ao, ramp=" .:-=+*#%@"))
        elif wahl == '5':
            normals = karte.normalen()
            bild = compose_vollbild(karte, normals, licht_dir)
            print(als_ascii(bild))
        elif wahl == '6':
            print("Formen: 1=Kugel, 2=Kegel, 3=Pyramide")
            f = input("Wähle Form (1-3): ").strip()
            if f in forms:
                current_form = f
                name, func = forms[f]
                karte = func()
                print(f"🦤 {name} erstellt.")
            else:
                print("❓ Unbekannte Form.")
        elif wahl == '7':
            print(f"Aktuelles Licht: {licht_dir[0]:.2f} {licht_dir[1]:.2f} {licht_dir[2]:.2f}")
            s = input("Neue Richtung (x y z): ").strip()
            v = parse_vec3(s)
            if v:
                licht_dir = vec3_norm(v)
                print(f"🦤 Licht gesetzt auf {licht_dir[0]:.2f} {licht_dir[1]:.2f} {licht_dir[2]:.2f}")
            else:
                print("❓ Ungültiges Format. Drei Zahlen erwartet.")
        elif wahl == '8':
            drucke_roh(karte)
        else:
            print("❓ Unbekannt. Bitte 0-8 eingeben.")

if __name__ == "__main__":
    main()