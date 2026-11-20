# main.py – Schatten-Simulator, Teil 14
# Fifo, der Dodo, träumt weiter: Datei vervollständigt, EOF-Sicherheit, Render-Pipeline glattgezogen.
# Blinn-Phong, AO, weiche Schatten – alles fein verwoben. Neue Form 'Wellblech' drin.

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


def vec3_sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])


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
                              schritte: int = 32, samples: int = 4, bias: float = 0.005) -> List[List[float]]:
    """Weiche Schatten via Jittered Raymarching."""
    h, b = karte.h, karte.b
    ergebnis = [[0.0] * b for _ in range(h)]
    for s in range(samples):
        # Jitter Lichtrichtung leicht
        jitter = 0.01
        lx = licht_dir[0] + random.uniform(-jitter, jitter)
        ly = licht_dir[1] + random.uniform(-jitter, jitter)
        lz = licht_dir[2]
        l_norm = vec3_norm((lx, ly, lz))
        harte = harte_schatten_raymarch(karte, l_norm, schritte, bias)
        for y in range(h):
            for x in range(b):
                ergebnis[y][x] += harte[y][x]
    for y in range(h):
        for x in range(b):
            ergebnis[y][x] /= samples
    return ergebnis


def ambient_occlusion(karte: Tiefenkarte, normals: List[List[Vec3]],
                       samples: int = 8, radius: float = 5.0) -> List[List[float]]:
    """Screen-Space Ambient Occlusion (vereinfacht)."""
    h, b = karte.h, karte.b
    ao = [[1.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            n = normals[y][x]
            if n[2] < 0.1: continue
            okklusion = 0
            for _ in range(samples):
                # Zufallsrichtung im Hemisphere
                ang = random.random() * 2 * math.pi
                dist = random.random() * radius
                sx = x + math.cos(ang) * dist
                sy = y + math.sin(ang) * dist
                if 0 <= sx < b - 1 and 0 <= sy < h - 1:
                    h_sample = karte.get_bilinear(sy, sx)
                    h_center = karte.get(y, x)
                    if h_sample > h_center + 0.02:
                        okklusion += 1
            ao[y][x] = 1.0 - (okklusion / samples) * 0.5
    return ao


def blinn_phong(normals: List[List[Vec3]], licht_dir: Vec3, view_dir: Vec3,
                 shadow: List[List[float]], ao: List[List[float]],
                 spec_exp: float = 32.0) -> List[List[float]]:
    """Blinn-Phong Shading mit Schatten und AO."""
    l = vec3_norm(licht_dir)
    v = vec3_norm(view_dir)
    # Half Vector
    h_vec = vec3_norm(vec3_add(l, v))
    h, b = len(normals), len(normals[0])
    bild = [[0.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            n = normals[y][x]
            ndotl = max(0.0, vec3_dot(n, l))
            ndoth = max(0.0, vec3_dot(n, h_vec))
            spec = (ndoth ** spec_exp) * shadow[y][x]
            diffuse = ndotl * shadow[y][x] * ao[y][x]
            ambient = 0.15 * ao[y][x]
            bild[y][x] = min(1.0, ambient + diffuse + spec)
    return bild


def render_ascii(bild: List[List[float]]) -> str:
    """Wandelt 0..1 Floatwerte in ASCII-Kunst um."""
    ramp = " .'`^\":;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8@$B"
    zeilen = []
    for reihe in bild:
        zeile = ""
        for val in reihe:
            idx = int(val * (len(ramp) - 1))
            zeile += ramp[idx]
        zeilen.append(zeile)
    return "\n".join(zeilen)


def menue() -> None:
    print("\n🦤 Schatten-Simulator – Menü:")
    print(" 1 – Harte Schatten (Raymarch)")
    print(" 2 – Weiche Schatten (Jittered Raymarch)")
    print(" 3 – Nur Ambient Occlusion")
    print(" 4 – Diffuse (Lambert) + Schatten")
    print(" 5 – Vollbild (Blinn-Phong + Schatten + AO)")
    print(" 6 – Tiefenform wählen (Kugel, Kegel, Pyramide, Wellblech)")
    print(" 7 – Lichtrichtung anpassen")
    print(" 8 – Höhen-Rohdaten anzeigen")
    print(" 0 – Beenden")


def parse_vec3(s: str) -> Optional[Vec3]:
    try:
        teile = [float(x.strip()) for x in s.split(",")]
        if len(teile) == 3:
            return tuple(teile)
    except ValueError:
        pass
    return None


def main() -> None:
    random.seed(42)
    karten_fabrik = {
        "1": ("Kugel", erzeuge_kugel),
        "2": ("Kegel", erzeuge_kegel),
        "3": ("Pyramide", erzeuge_stufenpyramide),
        "4": ("Wellblech", erzeuge_wellblech),
    }
    aktuelle_form = "1"
    karte = karten_fabrik[aktuelle_form][1]()
    licht_dir = (-0.5, -0.5, -1.0)
    view_dir = (0.0, 0.0, -1.0)

    while True:
        menue()
        try:
            wahl = input("🦤 Fifo fragt: Deine Wahl? 🦤 ").strip()
        except EOFError:
            print("\n🦤 Eingabeende. Der Dodo schläft weiter. Gute Nacht! 🦤")
            break

        if wahl == "0":
            print("🦤 Der Dodo nickt ein. Bis zum nächsten Traum! 🦤")
            break
        elif wahl == "1":
            normals = karte.normalen()
            shadow = harte_schatten_raymarch(karte, licht_dir)
            diffuse = diffuse_schatten(normals, licht_dir)
            combined = [[diffuse[y][x] * shadow[y][x] for x in range(karte.b)] for y in range(karte.h)]
            print(render_ascii(combined))
        elif wahl == "2":
            normals = karte.normalen()
            shadow = weiche_schatten_raymarch(karte, licht_dir)
            diffuse = diffuse_schatten(normals, licht_dir)
            combined = [[diffuse[y][x] * shadow[y][x] for x in range(karte.b)] for y in range(karte.h)]
            print(render_ascii(combined))
        elif wahl == "3":
            normals = karte.normalen()
            ao = ambient_occlusion(karte, normals)
            print(render_ascii(ao))
        elif wahl == "4":
            normals = karte.normalen()
            shadow = harte_schatten_raymarch(karte, licht_dir)
            diffuse = diffuse_schatten(normals, licht_dir)
            combined = [[diffuse[y][x] * shadow[y][x] for x in range(karte.b)] for y in range(karte.h)]
            print(render_ascii(combined))
        elif wahl == "5":
            normals = karte.normalen()
            shadow = weiche_schatten_raymarch(karte, licht_dir)
            ao = ambient_occlusion(karte, normals)
            shaded = blinn_phong(normals, licht_dir, view_dir, shadow, ao)
            print(render_ascii(shaded))
        elif wahl == "6":
            print("Formen: 1=Kugel, 2=Kegel, 3=Pyramide, 4=Wellblech")
            try:
                f = input("Neue Form (1-4): ").strip()
                if f in karten_fabrik:
                    aktuelle_form = f
                    karte = karten_fabrik[f][1]()
                    print(f"🦤 Form '{karten_fabrik[f][0]}' geladen.")
                else:
                    print("🦤 Unbekannte Form.")
            except EOFError:
                break
        elif wahl == "7":
            print("Lichtrichtung als x,y,z (z.B. -0.5,-0.5,-1.0)")
            try:
                s = input("Neue Lichtrichtung: ").strip()
                v = parse_vec3(s)
                if v:
                    licht_dir = v
                    print(f"🦤 Licht gesetzt auf {v}.")
                else:
                    print("🦤 Ungültiges Format.")
            except EOFError:
                break
        elif wahl == "8":
            mn, mx, rng = karte.statistik()
            print(f"Höhe: min={mn:.3f}, max={mx:.3f}, range={rng:.3f}")
            # Mini-Heatmap
            ramp = " .:;+*#@"
            for y in range(karte.h):
                zeile = ""
                for x in range(karte.b):
                    v = karte.get(y, x)
                    idx = int(v * (len(ramp) - 1))
                    zeile += ramp[idx]
                print(zeile)
        else:
            print("🦤 Unbekannte Option.")

if __name__ == "__main__":
    main()