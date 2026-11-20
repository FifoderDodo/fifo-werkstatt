# main.py – Schatten-Simulator, Teil 11
# Fifo, der Dodo, kombiniert im Traum Blinn-Phong-Glanz und Umgebungsverdeckung (AO)!

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
    return [[val / samples for val in reihe] for reihe in akkumulator]


def ambient_occlusion(karte: Tiefenkarte, samples: int = 8, radius: float = 3.5) -> List[List[float]]:
    """Schätzt Horizont-Verdeckung an Furchen und Kanten ein."""
    h, b = karte.h, karte.b
    ao_map = []
    angles = [i * (2.0 * math.pi / samples) for i in range(samples)]
    for y in range(h):
        reihe = []
        for x in range(b):
            center_h = karte.get(y, x)
            verdeckung = 0.0
            for ang in angles:
                sx = x + math.cos(ang) * radius * 1.5
                sy = y + math.sin(ang) * radius
                nh = karte.get_bilinear(sy, sx)
                diff = nh - center_h
                if diff > 0.0:
                    verdeckung += min(1.0, diff * 3.0)
            ao = max(0.0, 1.0 - (verdeckung / samples))
            reihe.append(ao)
        ao_map.append(reihe)
    return ao_map


def blinn_phong_render(karte: Tiefenkarte, licht_dir: Vec3,
                       schatten_map: List[List[float]],
                       ao_map: Optional[List[List[float]]] = None,
                       specular_exp: float = 18.0) -> List[List[float]]:
    h, b = karte.h, karte.b
    normals = karte.normalen()
    lx, ly, lz = vec3_norm(licht_dir)
    view_dir = (0.0, 0.0, 1.0)
    hx, hy, hz = vec3_norm((lx + view_dir[0], ly + view_dir[1], lz + view_dir[2]))

    bild = []
    k_ambient = 0.15
    k_diffuse = 0.65
    k_specular = 0.35

    for y in range(h):
        reihe = []
        for x in range(b):
            nx, ny, nz = normals[y][x]
            s = schatten_map[y][x]
            ao = ao_map[y][x] if ao_map else 1.0

            # Diffus
            n_dot_l = max(0.0, nx * lx + ny * ly + nz * lz)
            diffuse = k_diffuse * n_dot_l * s

            # Ambient mit Horizont-AO
            ambient = k_ambient * ao

            # Glanz (Specular Blinn-Phong)
            n_dot_h = max(0.0, nx * hx + ny * hy + nz * hz)
            spec = (n_dot_h ** specular_exp) * k_specular * s if n_dot_l > 0 else 0.0

            total = min(1.0, max(0.0, ambient + diffuse + spec))
            reihe.append(total)
        bild.append(reihe)
    return bild


def render_ascii(matrix: List[List[float]]) -> str:
    palette = " .:-=+*#%@"
    zeilen = []
    for reihe in matrix:
        zeile = "".join(palette[min(len(palette) - 1, int(val * len(palette)))] for val in reihe)
        zeilen.append(zeile)
    return "\n".join(zeilen)


def main():
    print("🦤 Fifo murmelt im Traum: Schatten-Simulator Teil 11 bereit!")
    karte = erzeuge_kugel(20, 42)
    licht = vec3_norm((1.0, -1.0, 0.9))

    while True:
        print("\n--- SCHATTEN-SIMULATOR MENÜ (Teil 11) ---")
        print("1 – Diffus (Lambert only)")
        print("2 – Harte Schatten (Raymarch)")
        print("3 – Weiche Schatten (Raymarch Jitter)")
        print("4 – Umgebungsverdeckung (Ambient Occlusion)")
        print("5 – Vollbild (Blinn-Phong + Schatten + AO)")
        print("6 – Tiefenform wählen (Kugel, Kegel, Pyramide)")
        print("7 – Lichtrichtung anpassen")
        print("8 – Höhen-Rohdaten anzeigen")
        print("0 – Beenden")

        try:
            wahl = input("🦤 Fifo fragt: Deine Wahl? ").strip()
        except EOFError:
            print("\n🦤 Fifo schläft leise ein... Tschi-püüü!")
            break

        if wahl == "0":
            print("🦤 Fifo packt seine Schatten zusammen. Bis bald!")
            break
        elif wahl == "1":
            n = karte.normalen()
            diff = diffuse_schatten(n, licht)
            print("\n[ Diffuse Schattierung ]")
            print(render_ascii(diff))
        elif wahl == "2":
            print("\n[ Harte Schatten (Raymarch) ]")
            schatten = harte_schatten_raymarch(karte, licht)
            print(render_ascii(schatten))
        elif wahl == "3":
            print("\n[ Weiche Schatten (Raymarch Jitter) ]")
            schatten = weiche_schatten_raymarch(karte, licht)
            print(render_ascii(schatten))
        elif wahl == "4":
            print("\n[ Umgebungsverdeckung (Ambient Occlusion) ]")
            ao = ambient_occlusion(karte)
            print(render_ascii(ao))
        elif wahl == "5":
            print("\n[ Blinn-Phong Komposition (Volles Bild) ]")
            schatten = weiche_schatten_raymarch(karte, licht, schritte=20, samples=2)
            ao = ambient_occlusion(karte, samples=6)
            final = blinn_phong_render(karte, licht, schatten, ao)
            print(render_ascii(final))
        elif wahl == "6":
            print("\nFormen: 1=Kugel, 2=Kegel, 3=Stufenpyramide")
            try:
                f_wahl = input("Welche Form? ").strip()
            except EOFError:
                break
            if f_wahl == "1":
                karte = erzeuge_kugel(20, 42)
                print("🦤 Kugel erzeugt!")
            elif f_wahl == "2":
                karte = erzeuge_kegel(20, 42)
                print("🦤 Kegel aufgerichtet!")
            elif f_wahl == "3":
                karte = erzeuge_stufenpyramide(20, 42)
                print("🦤 Stufenpyramide errichtet!")
            else:
                print("❓ Unbekannte Form.")
        elif wahl == "7":
            print(f"Aktuelles Licht: {licht}")
            try:
                lx_str = input("Licht X [-2..2]: ").strip()
                ly_str = input("Licht Y [-2..2]: ").strip()
                lz_str = input("Licht Z Höhe [0.1..2]: ").strip()
                licht = vec3_norm((float(lx_str), float(ly_str), float(lz_str)))
                print(f"🦤 Neue Lichtrichtung: {licht}")
            except (ValueError, EOFError):
                print("❓ Ungültige Eingabe, behalte bisherige Richtung.")
        elif wahl == "8":
            mn, mx, sp = karte.statistik()
            print(f"\nStatistik: Min={mn:.2f}, Max={mx:.2f}, Spanne={sp:.2f}")
            print(render_ascii(karte.daten))
        else:
            print("❓ Unbekannt. Bitte 0-8 eingeben.")


if __name__ == "__main__":
    main()