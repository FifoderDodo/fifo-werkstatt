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
                h_sample = karte.get_bilinear(cy, cx)
                if cz <= h_sample:
                    blocked = True
                    break
            if blocked:
                shadow[y][x] = 0.0
    return shadow

def weiche_schatten(schatten: List[List[float]], radius: int = 1) -> List[List[float]]:
    """Box‑Blur für weiche Schatten."""
    h = len(schatten)
    b = len(schatten[0]) if h > 0 else 0
    if radius <= 0:
        return schatten
    # horizontal pass
    tmp = [[0.0] * b for _ in range(h)]
    for y in range(h):
        row = schatten[y]
        for x in range(b):
            s = 0.0
            cnt = 0
            for dx in range(-radius, radius + 1):
                nx = x + dx
                if 0 <= nx < b:
                    s += row[nx]
                    cnt += 1
            tmp[y][x] = s / cnt
    # vertical pass
    result = [[0.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            s = 0.0
            cnt = 0
            for dy in range(-radius, radius + 1):
                ny = y + dy
                if 0 <= ny < h:
                    s += tmp[ny][x]
                    cnt += 1
            result[y][x] = s / cnt
    return result

def ascii_export(schatten: List[List[float]], invert: bool = False) -> str:
    """Wandelt Schattenkarte in ASCII‑Art um."""
    chars = " .:-=+*#%@"
    if invert:
        chars = chars[::-1]
    lines = []
    for row in schatten:
        line = ''.join(chars[min(int(v * (len(chars) - 1)), len(chars) - 1)] for v in row)
        lines.append(line)
    return '\n'.join(lines)

def speichere_ppm(dateiname: str, daten: List[List[float]], skalierung: float = 1.0) -> None:
    """Speichert Grauwertbild als ASCII‑PPM (P3)."""
    h = len(daten)
    b = len(daten[0]) if h > 0 else 0
    with open(dateiname, 'w') as f:
        f.write(f"P3\n{b} {h}\n255\n")
        for row in daten:
            for v in row:
                val = int(max(0.0, min(1.0, v * skalierung)) * 255)
                f.write(f"{val} {val} {val} ")
            f.write("\n")

# ---------- Batch‑ und Interaktiv‑Modus ----------

def batch_modus() -> None:
    configs = [
        {"form": "kugel", "licht": (1, -1, 1), "ausgabe": "kugel_shadow.ppm"},
        {"form": "kegel", "licht": (-1, 0.5, 1), "ausgabe": "kegel_shadow.ppm"},
        {"form": "pyramide", "licht": (0, -1, 1), "ausgabe": "pyramide_shadow.ppm"},
        {"form": "wellblech", "licht": (1, 1, 1), "ausgabe": "wellblech_shadow.ppm"},
    ]
    for cfg in configs:
        form = cfg["form"]
        if form == "kugel":
            karte = erzeuge_kugel()
        elif form == "kegel":
            karte = erzeuge_kegel()
        elif form == "pyramide":
            karte = erzeuge_stufenpyramide()
        elif form == "wellblech":
            karte = erzeuge_wellblech()
        else:
            karte = erzeuge_kugel()
        normals = karte.normalen()
        licht = cfg["licht"]
        diff = diffuse_schatten(normals, licht)
        hart = harte_schatten_raymarch(karte, licht)
        combined = [[diff[y][x] * hart[y][x] for x in range(karte.b)] for y in range(karte.h)]
        weich = weiche_schatten(combined, radius=1)
        speichere_ppm(cfg["ausgabe"], weich)
        print(f"Gespeichert: {cfg['ausgabe']}")

def interaktiv() -> None:
    print("Schatten‑Simulator – Interaktiver Modus")
    print("Verfügbare Formen: kugel, kegel, pyramide, wellblech")
    try:
        form = input("Form wählen: ").strip().lower()
    except EOFError:
        print("\nKeine Eingabe – Tschüss!")
        return
    if form not in ("kugel", "kegel", "pyramide", "wellblech"):
        print("Unbekannte Form, nehme Kugel.")
        form = "kugel"
    if form == "kugel":
        karte = erzeuge_kugel()
    elif form == "kegel":
        karte = erzeuge_kegel()
    elif form == "pyramide":
        karte = erzeuge_stufenpyramide()
    else:
        karte = erzeuge_wellblech()
    print("Lichtrichtung als drei Zahlen (x y z), z.B. 1 -1 1")
    try:
        lx, ly, lz = map(float, input("Licht: ").split())
    except EOFError:
        print("\nAbbruch.")
        return
    except ValueError:
        print("Ungültig, nutze Standard (1, -1, 1).")
        lx, ly, lz = 1.0, -1.0, 1.0
    licht = (lx, ly, lz)
    normals = karte.normalen()
    diff = diffuse_schatten(normals, licht)
    hart = harte_schatten_raymarch(karte, licht)
    combined = [[diff[y][x] * hart[y][x] for x in range(karte.b)] for y in range(karte.h)]
    try:
        radius = int(input("Weichzeichner‑Radius (0 für aus): ") or "1")
    except EOFError:
        radius = 1
    except ValueError:
        radius = 1
    weich = weiche_schatten(combined, radius=radius)
    print("\nASCII‑Vorschau:")
    print(ascii_export(weich))
    try:
        name = input("Dateiname für PPM (Enter für keine): ").strip()
    except EOFError:
        name = ""
    if name:
        speichere_ppm(name, weich)
        print(f"Gespeichert als {name}")
    else:
        print("Keine Datei gespeichert.")

def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        batch_modus()
    else:
        interaktiv()

if __name__ == "__main__":
    main()