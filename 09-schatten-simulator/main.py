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
        if self.h == 0 or self.b == 0:
            return 0.0
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
    """Ray-Marching-Schatten: für jeden Pixel entlang der Lichtrichtung marschieren."""
    h, b = tk.h, tk.b
    schatten = [[1.0 for _ in range(b)] for _ in range(h)]
    # Lichtrichtung normalisieren
    lx, ly, lz = vec3_norm(licht_dir)
    # Schrittweite in Weltkoordinaten: wir gehen von der Oberfläche weg
    max_dist = math.sqrt(h * h + b * b) * 1.5
    step = max_dist / schritte
    bias = 0.01  # Self-Shadow-Bias
    for y in range(h):
        for x in range(b):
            # Startpunkt auf der Oberfläche
            pz = tk.daten[y][x]
            py = float(y)
            px = float(x)
            # Ein wenig entlang der Normalen versetzen, um Self-Shadowing zu vermeiden
            nx, ny, nz = normals[y][x]
            py += ny * bias
            px += nx * bias
            pz += nz * bias
            # Ray marching
            blocked = 0.0
            for i in range(schritte):
                py -= ly * step
                px -= lx * step
                pz -= lz * step
                if pz < 0.0:
                    break
                # Höhe der Tiefenkarte an dieser Stelle (bilinear)
                h_map = tk.get_bilinear(py, px)
                if pz <= h_map:
                    blocked = 1.0
                    break
            schatten[y][x] = 1.0 - blocked
    return schatten

def blinn_phong(normal: Vec3, licht_dir: Vec3, view_dir: Vec3, schatten: float,
                 ambient: float = 0.1, diffuse: float = 0.7, specular: float = 0.5, shininess: float = 32.0) -> Color:
    """Blinn-Phong-Beleuchtung mit Schatten."""
    n = vec3_norm(normal)
    l = vec3_norm(licht_dir)
    v = vec3_norm(view_dir)
    # Half vector
    h = vec3_norm(vec3_add(l, v))
    ndotl = max(0.0, vec3_dot(n, l))
    ndoth = max(0.0, vec3_dot(n, h))
    diff = diffuse * ndotl
    spec = specular * (ndoth ** shininess)
    intensity = ambient + schatten * (diff + spec)
    intensity = max(0.0, min(1.0, intensity))
    # Einfache Farbgebung: grau mit leichter Färbung nach Höhe (hier nur Intensität)
    c = int(255 * intensity)
    return (c, c, c)

def rendern(tk: Tiefenkarte, normals: List[List[Vec3]], schatten: List[List[float]],
            licht_dir: Vec3, view_dir: Vec3) -> List[List[Color]]:
    """Erzeugt das finale Bild als Liste von Zeilen mit RGB-Tupeln."""
    h, b = tk.h, tk.b
    bild: List[List[Color]] = []
    for y in range(h):
        reihe: List[Color] = []
        for x in range(b):
            col = blinn_phong(normals[y][x], licht_dir, view_dir, schatten[y][x])
            reihe.append(col)
        bild.append(reihe)
    return bild

def schreibe_ppm(bild: List[List[Color]], out_stream) -> None:
    """Schreibt PPM Binary (P6) auf den gegebenen Stream."""
    h = len(bild)
    b = len(bild[0]) if h > 0 else 0
    out_stream.write(f"P6\n{b} {h}\n255\n".encode('ascii'))
    for reihe in bild:
        for r, g, b_ in reihe:
            out_stream.write(bytes([r, g, b_]))

def wahl_form() -> str:
    print("Verfügbare Formen: kugel, kegel, pyramide, wellblech, huegel")
    try:
        w = input("Form [kugel]: ").strip().lower()
    except EOFError:
        w = ""
    if w in ("kugel", "kegel", "pyramide", "wellblech", "huegel"):
        return w
    return "kugel"

def main() -> None:
    print("Schatten-Simulator – Träumt weiter, kleiner Dodo.")
    def get_int(prompt: str, default: int) -> int:
        try:
            s = input(prompt).strip()
        except EOFError:
            return default
        if not s:
            return default
        try:
            return int(s)
        except ValueError:
            return default
    h = get_int("Höhe [20]: ", 20)
    b = get_int("Breite [40]: ", 40)
    form = wahl_form()
    if form == "kugel":
        tk = erzeuge_kugel(h, b)
    elif form == "kegel":
        tk = erzeuge_kegel(h, b)
    elif form == "pyramide":
        tk = erzeuge_stufenpyramide(h, b)
    elif form == "wellblech":
        tk = erzeuge_wellblech(h, b)
    else:
        tk = erzeuge_zufaellige_huegel(h, b)
    print("Berechne Normalen...")
    normals = tk.normalen(z_skalierung=2.0)
    print("Berechne Schatten...")
    # Licht von oben-links-hinten
    licht_dir = vec3_norm((-0.5, -0.5, -1.0))
    schatten = diffuse_schatten(tk, normals, licht_dir, schritte=64)
    print("Rendere Bild...")
    view_dir = (0.0, 0.0, 1.0)  # Betrachter schaut von vorn
    bild = rendern(tk, normals, schatten, licht_dir, view_dir)
    print("Fertig. Träum was Schönes.")
    schreibe_ppm(bild, sys.stdout.buffer)

if __name__ == "__main__":
    main()