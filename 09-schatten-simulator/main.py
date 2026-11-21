from __future__ import annotations
import math
import sys
import random
from typing import List, Tuple, Optional

Vec3 = Tuple[float, float, float]
Color = Tuple[int, int, int]

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

def erzeuge_zufaellige_huegel(h: int = 20, b: int = 40, anzahl: int = 5, seed: int = 42) -> Tiefenkarte:
    """Einfache Perlin-ish Hügel: Summe von ein paar Gauß-Glocken."""
    random.seed(seed)
    karte = [[0.0 for _ in range(b)] for _ in range(h)]
    centers = []
    for _ in range(anzahl):
        cy = random.uniform(0.2, 0.8) * (h - 1)
        cx = random.uniform(0.2, 0.8) * (b - 1)
        rad = random.uniform(0.15, 0.35) * min(h, b)
        hoehe = random.uniform(0.5, 1.0)
        centers.append((cy, cx, rad, hoehe))
    for y in range(h):
        for x in range(b):
            val = 0.0
            for cy, cx, rad, hoehe in centers:
                dy = y - cy
                dx = (x - cx) * 0.5
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < rad:
                    val += hoehe * (1.0 - dist / rad)
            karte[y][x] = min(1.0, val)
    return Tiefenkarte(karte)

# ---------- Beleuchtungs- und Schatten-Funktionen ----------

def diffuse_schatten(tk: Tiefenkarte, normals: List[List[Vec3]], licht_dir: Vec3, schritte: int = 64) -> List[List[float]]:
    """Ray-Marching-Schatten: für jeden Pixel entlang der Lichtrichtung marschieren und Prüfen, ob die Höhenkarte getroffen wird."""
    lx, ly, lz = vec3_norm(licht_dir)
    # Licht von oben -> lz negativ? Wir definieren Lichtrichtung als Vektor ZUR Lichtquelle.
    # Wenn Licht von oben kommt, ist lz > 0. Wir marschieren ENTLANG der Lichtrichtung (also vom Pixel zur Lichtquelle).
    # Der Höhenwert ist in [0,1]. Wir skalieren z auf 0..1.
    result: List[List[float]] = []
    for y in range(tk.h):
        rreihe: List[float] = []
        for x in range(tk.b):
            h = tk.daten[y][x]
            if h <= 0.0:
                rreihe.append(1.0)
                continue
            # Startpunkt leicht über der Oberfläche
            px = x + 0.5
            py = y + 0.5
            pz = h * 1.0  # Skalierung: Höhe 1.0 entspricht 1.0 in Weltkoordinaten
            # Schrittgröße in Weltkoordinaten
            step = 1.0 / schritte
            in_shadow = False
            for i in range(1, schritte + 1):
                px += lx * step
                py += ly * step
                pz += lz * step
                if pz < 0.0:
                    break
                # Bilineare Interpolation der Höhenkarte
                hy = tk.get_bilinear(py - 0.5, px - 0.5)
                if hy * 1.0 >= pz - 1e-4:
                    in_shadow = True
                    break
                if px < 0.5 or px >= tk.b - 0.5 or py < 0.5 or py >= tk.h - 0.5:
                    break
            rreihe.append(0.0 if in_shadow else 1.0)
        result.append(rreihe)
    return result

def blinn_phong(normals: List[List[Vec3]], licht_dir: Vec3, view_dir: Vec3, shadow: List[List[float]],
                kd: float = 0.8, ks: float = 0.3, shininess: float = 32.0, ambient: float = 0.2) -> List[List[Color]]:
    """Berechnet Farbe pro Pixel mit Blinn-Phong."""
    l = vec3_norm(licht_dir)
    v = vec3_norm(view_dir)
    h_vec = vec3_norm(vec3_add(l, v))
    img: List[List[Color]] = []
    for y, reihe in enumerate(normals):
        rreihe: List[Color] = []
        for x, n in enumerate(reihe):
            ndotl = max(0.0, vec3_dot(n, l))
            ndoth = max(0.0, vec3_dot(n, h_vec))
            spec = (ndoth ** shininess) * ks
            diff = ndotl * kd
            shade = shadow[y][x]
            intensity = ambient + shade * (diff + spec)
            intensity = max(0.0, min(1.0, intensity))
            # Einfache Materialfarbe: weiß
            col = (int(intensity * 255), int(intensity * 255), int(intensity * 255))
            rreihe.append(col)
        img.append(rreihe)
    return img

# ---------- Hauptprogramm ----------

def main() -> None:
    print("Schatten-Simulator – Teil 34: Ray-Marching-Schatten repariert, Blinn-Phong, PPM-Ausgabe")
    print("Verfügbare Formen: 1=Kugel, 2=Kegel, 3=Stufenpyramide, 4=Wellblech, 5=Zufällige Hügel")
    try:
        eingabe = input("Form wählen [1-5] (Enter=1): ").strip()
    except EOFError:
        print("Keine Eingabe, Standard wird verwendet.")
        eingabe = "1"
    form = int(eingabe) if eingabe.isdigit() and 1 <= int(eingabe) <= 5 else 1
    
    try:
        eingabe = input("Breite (Zeichen) [40]: ").strip()
    except EOFError:
        eingabe = "40"
    b = int(eingabe) if eingabe.isdigit() and int(eingabe) > 0 else 40
    
    try:
        eingabe = input("Höhe (Zeilen) [20]: ").strip()
    except EOFError:
        eingabe = "20"
    h = int(eingabe) if eingabe.isdigit() and int(eingabe) > 0 else 20
    
    try:
        eingabe = input("Lichtrichtung x y z (z.B. 0.5 -0.5 1) [0.5 -0.5 1]: ").strip()
    except EOFError:
        eingabe = "0.5 -0.5 1"
    parts = eingabe.split()
    if len(parts) == 3:
        try:
            licht = (float(parts[0]), float(parts[1]), float(parts[2]))
        except ValueError:
            licht = (0.5, -0.5, 1.0)
    else:
        licht = (0.5, -0.5, 1.0)
    
    # Form erzeugen
    if form == 1:
        tk = erzeuge_kugel(h, b)
    elif form == 2:
        tk = erzeuge_kegel(h, b)
    elif form == 3:
        tk = erzeuge_stufenpyramide(h, b)
    elif form == 4:
        tk = erzeuge_wellblech(h, b)
    else:
        tk = erzeuge_zufaellige_huegel(h, b)
    
    print(f"Erzeugt: {tk.h}x{tk.b}, Statistik: {tk.statistik()}")
    
    # Normalen
    normals = tk.normalen(z_skalierung=2.0)
    
    # Schatten mit Ray-Marching
    print("Berechne Schatten (Ray-Marching, 64 Schritte)...")
    shadow = diffuse_schatten(tk, normals, licht, schritte=64)
    
    # Beleuchtung
    view = (0.0, 0.0, 1.0)  # feste View-Direction
    print("Berechne Beleuchtung (Blinn-Phong)...")
    img = blinn_phong(normals, licht, view, shadow)
    
    # PPM P6 auf stdout schreiben
    out = sys.stdout.buffer
    out.write(f"P6\n{tk.b} {tk.h}\n255\n".encode('ascii'))
    for reihe in img:
        for r, g, b in reihe:
            out.write(bytes([r, g, b]))
    out.flush()
    print("\nFertig. PPM auf stdout.", file=sys.stderr)

if __name__ == "__main__":
    main()