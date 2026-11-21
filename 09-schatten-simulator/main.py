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
    shadow = [[1.0 for _ in range(b)] for _ in range(h)]
    # Light direction is normalized and points FROM surface TO light.
    # We march opposite to light direction (i.e., from surface towards light source).
    # But typical shadow ray goes from surface towards light, so we use -licht_dir.
    # However, our licht_dir is defined as direction FROM light TO surface? Let's assume licht_dir points from surface to light (common).
    # We'll march in direction of licht_dir (towards light).
    # Step size in world units: we assume grid spacing 1.0 in x,y and z_skalierung in z.
    # We'll use a small bias to avoid self-shadowing.
    bias = 0.01
    for y in range(h):
        for x in range(b):
            if tk.daten[y][x] <= 0.0:
                shadow[y][x] = 1.0
                continue
            # Start point slightly above surface
            start_z = tk.daten[y][x] + bias
            px, py, pz = float(x), float(y), start_z
            lx, ly, lz = licht_dir
            hit = False
            for _ in range(schritte):
                px += lx
                py += ly
                pz += lz
                if px < 0 or px >= b - 1 or py < 0 or py >= h - 1:
                    break
                h_map = tk.get_bilinear(py, px)
                if pz <= h_map:
                    hit = True
                    break
            shadow[y][x] = 0.0 if hit else 1.0
    return shadow

def blinn_phong(normal: Vec3, licht_dir: Vec3, view_dir: Vec3, shadow: float, material: dict) -> Color:
    """Blinn-Phong Shading mit Shadow-Faktor."""
    # Ambient
    ka = material.get('ka', 0.1)
    kd = material.get('kd', 0.7)
    ks = material.get('ks', 0.3)
    shininess = material.get('shininess', 32.0)
    light_color = material.get('light_color', (1.0, 1.0, 1.0))
    object_color = material.get('object_color', (0.8, 0.8, 0.8))
    
    n_dot_l = max(0.0, vec3_dot(normal, licht_dir))
    diffuse = kd * n_dot_l
    
    # Half vector
    half_vec = vec3_norm(vec3_add(licht_dir, view_dir))
    n_dot_h = max(0.0, vec3_dot(normal, half_vec))
    specular = ks * (n_dot_h ** shininess)
    
    intensity = ka + shadow * (diffuse + specular)
    intensity = min(1.0, max(0.0, intensity))
    
    r = int(object_color[0] * light_color[0] * intensity * 255)
    g = int(object_color[1] * light_color[1] * intensity * 255)
    b = int(object_color[2] * light_color[2] * intensity * 255)
    return (r, g, b)

def rendern(tk: Tiefenkarte, normals: List[List[Vec3]], licht_dir: Vec3, view_dir: Vec3, shadow_map: List[List[float]], material: dict) -> List[List[Color]]:
    """Erzeugt finales Bild als Liste von Zeilen mit Farben."""
    h, b = tk.h, tk.b
    bild: List[List[Color]] = []
    for y in range(h):
        reihe: List[Color] = []
        for x in range(b):
            if tk.daten[y][x] <= 0.0:
                reihe.append((0, 0, 0))
            else:
                col = blinn_phong(normals[y][x], licht_dir, view_dir, shadow_map[y][x], material)
                reihe.append(col)
        bild.append(reihe)
    return bild

def schreibe_ppm(bild: List[List[Color]], out_stream) -> None:
    """Schreibt PPM P6 (binary) auf den gegebenen Stream."""
    h = len(bild)
    b = len(bild[0]) if h > 0 else 0
    out_stream.write(f"P6\n{b} {h}\n255\n".encode('ascii'))
    for reihe in bild:
        for r, g, b in reihe:
            out_stream.write(bytes([r, g, b]))

# ---------- Hauptprogramm ----------

def eingabe(prompt: str, default: str) -> str:
    """Liest eine Zeile, bei EOF gibt Default zurück."""
    try:
        return input(prompt).strip()
    except EOFError:
        return default

def main() -> None:
    print("Schatten-Simulator – Träumt weiter, kleiner Dodo.", file=sys.stderr)
    # Defaults
    hoehe = 20
    breite = 40
    form = "kugel"
    z_skalierung = 2.0
    licht_dir = vec3_norm((0.5, -0.5, 1.0))
    view_dir = vec3_norm((0.0, 0.0, 1.0))
    schritte = 64
    
    # Interaktive Eingabe (max 20, aber wir fragen nur ein paar)
    try:
        s = eingabe("Höhe [20]: ", "20")
        if s: hoehe = int(s)
        s = eingabe("Breite [40]: ", "40")
        if s: breite = int(s)
        s = eingabe("Form (kugel/kegel/pyramide/wellblech/huegel) [kugel]: ", "kugel")
        if s: form = s
        s = eingabe("Z-Skalierung [2.0]: ", "2.0")
        if s: z_skalierung = float(s)
        s = eingabe("Lichtrichtung x y z [0.5 -0.5 1.0]: ", "0.5 -0.5 1.0")
        if s:
            parts = list(map(float, s.split()))
            if len(parts) == 3:
                licht_dir = vec3_norm(tuple(parts))
        s = eingabe("Schatten-Schritte [64]: ", "64")
        if s: schritte = int(s)
    except Exception:
        pass  # Bei Fehler Defaults behalten
    
    # Form erzeugen
    if form == "kugel":
        tk = erzeuge_kugel(hoehe, breite)
    elif form == "kegel":
        tk = erzeuge_kegel(hoehe, breite)
    elif form == "pyramide":
        tk = erzeuge_stufenpyramide(hoehe, breite)
    elif form == "wellblech":
        tk = erzeuge_wellblech(hoehe, breite)
    elif form == "huegel":
        tk = erzeuge_zufaellige_huegel(hoehe, breite)
    else:
        tk = erzeuge_kugel(hoehe, breite)
    
    # Normalen
    normals = tk.normalen(z_skalierung)
    # Schatten
    shadow_map = diffuse_schatten(tk, normals, licht_dir, schritte)
    # Material
    material = {
        'ka': 0.1,
        'kd': 0.7,
        'ks': 0.3,
        'shininess': 32.0,
        'light_color': (1.0, 1.0, 1.0),
        'object_color': (0.9, 0.7, 0.5)
    }
    # Rendern
    bild = rendern(tk, normals, licht_dir, view_dir, shadow_map, material)
    # Ausgabe
    schreibe_ppm(bild, sys.stdout.buffer)
    print("Fertig. Träum was Schönes.", file=sys.stderr)

if __name__ == "__main__":
    main()