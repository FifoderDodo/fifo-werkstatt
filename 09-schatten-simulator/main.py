# main.py – Schatten‑Simulator, Teil 22
# Fifo, der Dodo, träumt den letzten Schliff: Speichern, Batch‑Modus, kleine Aufräumarbeiten.
# Diesmal: Ray‑Marching fertig, Weichzeichner, ASCII‑Export, EOF‑Sicherheit, Batch‑Modus.

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
    step_z = lz * inv_xy * step_xy * 0.1  # 0.1 ≈ z‑Skalierung der Tiefenkarte

    shadow: List[List[float]] = []
    for y in range(h):
        reihe: List[float] = []
        for x in range(b):
            # Startpunkt leicht über der Oberfläche
            cur_x = x + 0.5
            cur_y = y + 0.5
            cur_z = karte.daten[y][x] + bias
            blocked = False
            for _ in range(schritte):
                cur_x += dir_x
                cur_y += dir_y
                cur_z += step_z
                if cur_x < 0 or cur_x >= b or cur_y < 0 or cur_y >= h:
                    break
                # bilinear sample Höhe
                h_val = karte.get_bilinear(cur_y, cur_x)
                if cur_z <= h_val + bias:
                    blocked = True
                    break
            reihe.append(0.0 if blocked else 1.0)
        shadow.append(reihe)
    return shadow

def box_blur(src: List[List[float]], radius: int) -> List[List[float]]:
    """Einfacher Box‑Blur (separable) für Weichzeichner."""
    if radius <= 0:
        return src
    h = len(src)
    b = len(src[0]) if h > 0 else 0
    # horizontal
    tmp = [[0.0] * b for _ in range(h)]
    for y in range(h):
        row = src[y]
        for x in range(b):
            s = 0.0
            cnt = 0
            for dx in range(-radius, radius + 1):
                xi = x + dx
                if 0 <= xi < b:
                    s += row[xi]
                    cnt += 1
            tmp[y][x] = s / cnt if cnt else 0.0
    # vertical
    dst = [[0.0] * b for _ in range(h)]
    for x in range(b):
        for y in range(h):
            s = 0.0
            cnt = 0
            for dy in range(-radius, radius + 1):
                yi = y + dy
                if 0 <= yi < h:
                    s += tmp[yi][x]
                    cnt += 1
            dst[y][x] = s / cnt if cnt else 0.0
    return dst

def weiche_schatten(karte: Tiefenkarte, licht_dir: Vec3,
                    schritte: int = 32, blur_radius: int = 2) -> List[List[float]]:
    """Kombiniert Ray‑Marching mit Box‑Blur für weiche Schatten."""
    hard = harte_schatten_raymarch(karte, licht_dir, schritte)
    return box_blur(hard, blur_radius)

# ---------- ASCII‑Rendering ----------

def ascii_art(werte: List[List[float]], palette: str = " .:-=+*#%@") -> str:
    """Wandelt 2D‑Float‑Array (0..1) in ASCII‑Zeilen um."""
    lines = []
    n = len(palette) - 1
    for reihe in werte:
        line = ''.join(palette[min(n, max(0, int(v * n)))] for v in reihe)
        lines.append(line)
    return '\n'.join(lines)

# ---------- Speichern ----------

def speichern(text: str, dateiname: str) -> bool:
    """Speichert Text in Datei (nur im aktuellen Ordner)."""
    try:
        with open(dateiname, 'w', encoding='utf-8') as f:
            f.write(text)
        return True
    except Exception as e:
        print(f"Fehler beim Speichern: {e}")
        return False

# ---------- Eingabe‑Hilfen mit EOF‑Schutz ----------

def safe_input(prompt: str, default: str = "") -> str:
    """input() mit EOF‑Abruf und Default."""
    try:
        return input(prompt)
    except EOFError:
        print("\nEOF – Ende.")
        sys.exit(0)


def parse_vec3(s: str, default: Vec3) -> Vec3:
    parts = s.strip().split()
    if len(parts) != 3:
        return default
    try:
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    except ValueError:
        return default


def parse_int(s: str, default: int, lo: int, hi: int) -> int:
    try:
        v = int(s.strip())
        if lo <= v <= hi:
            return v
    except ValueError:
        pass
    return default

# ---------- Hauptprogramm ----------

def main() -> None:
    print("=== Schatten‑Simulator (Teil 22) ===")
    print("Formen: 1=Kugel, 2=Kegel, 3=Stufenpyramide, 4=Wellblech")
    
    # Eingabezähler für Limit 20
    eingaben = 0
    MAX_EINGABEN = 20
    
    def get_input(prompt: str, default: str) -> str:
        nonlocal eingaben
        if eingaben >= MAX_EINGABEN:
            print("Eingabe‑Limit erreicht, nutze Defaults.")
            return default
        eingaben += 1
        return safe_input(prompt, default)
    
    # Form wählen
    formwahl = get_input("Form wählen [1‑4]: ", "1")
    if formwahl not in ("1", "2", "3", "4"):
        print("Ungültig, nehme Kugel.")
        formwahl = "1"
    
    if formwahl == "1":
        karte = erzeuge_kugel()
        formenname = "kugel"
    elif formwahl == "2":
        karte = erzeuge_kegel()
        formenname = "kegel"
    elif formwahl == "3":
        karte = erzeuge_stufenpyramide()
        formenname = "pyramide"
    else:
        karte = erzeuge_wellblech()
        formenname = "wellblech"
    
    # Lichtrichtung
    licht_str = get_input('Lichtrichtung als drei Zahlen (x y z), z.B. "1 1 -2": ', "1 1 -2")
    licht = parse_vec3(licht_str, (1.0, 1.0, -2.0))
    if licht_str.strip() == "":
        print("Ungültig, nehme Standard (1, 1, -2).")
    
    # Schatten‑Samples
    samples_str = get_input("Schatten‑Samples (Ray‑March Steps) [8‑64]: ", "32")
    samples = parse_int(samples_str, 32, 8, 64)
    if samples_str.strip() == "":
        print("Ungültig, nehme 32.")
    
    # Weichzeichner‑Radius
    blur_str = get_input("Weichzeichner‑Radius (Box‑Blur) [0‑4]: ", "2")
    blur = parse_int(blur_str, 2, 0, 4)
    if blur_str.strip() == "":
        print("Ungültig, nehme 2.")
    
    # Berechnungen
    print("\nBerechne Normalen …")
    normals = karte.normalen()
    
    print("Berechne diffuse Beleuchtung …")
    diffuse = diffuse_schatten(normals, licht)
    
    print("Berechne harte Schatten (Ray‑Marching) …")
    hard = harte_schatten_raymarch(karte, licht, samples)
    
    print("Wende Weichzeichner an …")
    soft = box_blur(hard, blur)
    
    # Kombinieren: diffuse * shadow
    combined = []
    for y in range(karte.h):
        row = []
        for x in range(karte.b):
            row.append(diffuse[y][x] * soft[y][x])
        combined.append(row)
    
    # ASCII Ausgabe
    print("\n=== Ergebnis (diffus * weicher Schatten) ===")
    ascii_out = ascii_art(combined)
    print(ascii_out)
    
    # Speichern?
    save = get_input("In Datei speichern? (j/n) [n]: ", "n").lower()
    if save == "j" or save == "ja":
        fname = get_input("Dateiname (z.B. schatten.txt): ", f"schatten_{formenname}.txt")
        if speichern(ascii_out, fname):
            print(f"Gespeichert unter {fname}")
        else:
            print("Speichern fehlgeschlagen.")
    
    # Batch‑Modus?
    batch = get_input("Batch‑Modus für alle Formen? (j/n) [n]: ", "n").lower()
    if batch == "j" or batch == "ja":
        print("\n=== Batch‑Modus ===")
        formen = [
            ("kugel", erzeuge_kugel),
            ("kegel", erzeuge_kegel),
            ("pyramide", erzeuge_stufenpyramide),
            ("wellblech", erzeuge_wellblech),
        ]
        for name, func in formen:
            print(f"\n--- {name} ---")
            k = func()
            n = k.normalen()
            d = diffuse_schatten(n, licht)
            h = harte_schatten_raymarch(k, licht, samples)
            s = box_blur(h, blur)
            c = [[d[y][x] * s[y][x] for x in range(k.b)] for y in range(k.h)]
            a = ascii_art(c)
            print(a)
            fn = f"batch_{name}.txt"
            if speichern(a, fn):
                print(f"Gespeichert: {fn}")
    
    print("\nFertig. Gute Nacht!")

if __name__ == "__main__":
    main()