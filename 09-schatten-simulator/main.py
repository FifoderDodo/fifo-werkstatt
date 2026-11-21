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
    if lz <= 1e-6:
        return [[1.0] * b for _ in range(h)]

    max_d = math.sqrt(h * h + b * b)
    step_xy = max_d / schritte
    l_xy = math.sqrt(lx * lx + ly * ly)
    
    result: List[List[float]] = []
    for y in range(h):
        reihe: List[float] = []
        for x in range(b):
            h_hier = karte.daten[y][x]
            if h_hier <= 0.0:
                reihe.append(1.0)
                continue
            # Startpunkt leicht über Oberfläche
            cx = x + lx * bias
            cy = y + ly * bias
            cz = h_hier + lz * bias
            in_shadow = False
            for i in range(schritte):
                cx += lx * step_xy
                cy += ly * step_xy
                cz += lz * step_xy
                if cz <= 0.0:
                    break
                h_da = karte.get_bilinear(cy, cx)
                if cz < h_da:
                    in_shadow = True
                    break
            reihe.append(0.0 if in_shadow else 1.0)
        result.append(reihe)
    return result

# ---------- Farb-Mapping ----------

def hoehe_zu_farbe(h: float) -> Color:
    """Mappt Höhe 0..1 auf eine schöne Farbpalette (Ozean -> Land -> Schnee)."""
    if h < 0.3:
        # Wasser: dunkelblau -> türkis
        t = h / 0.3
        r = int(0 * (1 - t) + 0 * t)
        g = int(50 * (1 - t) + 180 * t)
        b = int(120 * (1 - t) + 255 * t)
    elif h < 0.6:
        # Strand / Gras
        t = (h - 0.3) / 0.3
        r = int(200 * (1 - t) + 50 * t)
        g = int(200 * (1 - t) + 180 * t)
        b = int(50 * (1 - t) + 50 * t)
    elif h < 0.9:
        # Fels / Berg
        t = (h - 0.6) / 0.3
        r = int(100 * (1 - t) + 150 * t)
        g = int(100 * (1 - t) + 150 * t)
        b = int(100 * (1 - t) + 150 * t)
    else:
        # Schnee
        t = (h - 0.9) / 0.1
        r = int(200 * (1 - t) + 255 * t)
        g = int(200 * (1 - t) + 255 * t)
        b = int(200 * (1 - t) + 255 * t)
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

def wende_licht_farbe(basis_farbe: Color, diffuse: float, shadow: float,
                      spekular: float = 0.0, ambient: float = 0.1) -> Color:
    """Kombiniert Basisfarbe mit Licht (diffus, schatten, spekular, ambient)."""
    r, g, b = basis_farbe
    # Ambient + Diffuse * Shadow + Specular
    faktor = ambient + diffuse * shadow + spekular
    faktor = max(0.0, min(1.0, faktor))
    return (int(r * faktor), int(g * faktor), int(b * faktor))

# ---------- Spekular-Berechnung (Blinn-Phong) ----------

def spekular_beitrag(normals: List[List[Vec3]], licht_dir: Vec3, view_dir: Vec3,
                     shininess: float = 32.0) -> List[List[float]]:
    """Berechnet Spekular-Anteil für jede Normalen."""
    l = vec3_norm(licht_dir)
    v = vec3_norm(view_dir)
    # Half-Vektor
    h = vec3_norm(vec3_add(l, v))
    result: List[List[float]] = []
    for reihe in normals:
        rreihe: List[float] = []
        for n in reihe:
            nh = max(0.0, vec3_dot(n, h))
            spec = nh ** shininess
            rreihe.append(spec)
        result.append(rreihe)
    return result

# ---------- Hauptprogramm ----------

def main() -> None:
    print("=== Schatten-Simulator (Teil 33) ===")
    print("Träume von Tiefe... Form wählen:")
    print("1: Kugel")
    print("2: Kegel")
    print("3: Stufenpyramide")
    print("4: Wellblech")
    print("5: Zufällige Hügel (Perlin-ish)")
    
    form = 1
    try:
        inp = input("> ").strip()
        if inp:
            form = int(inp)
    except (ValueError, EOFError):
        pass
    
    if form == 1:
        karte = erzeuge_kugel()
    elif form == 2:
        karte = erzeuge_kegel()
    elif form == 3:
        karte = erzeuge_stufenpyramide()
    elif form == 4:
        karte = erzeuge_wellblech()
    elif form == 5:
        karte = erzeuge_zufaellige_huegel()
    else:
        karte = erzeuge_kugel()
    
    print("Lichtrichtung (x y z), z>0 heißt von oben. Enter = (0.5, -0.3, 1.0)")
    licht = (0.5, -0.3, 1.0)
    try:
        inp = input("> ").strip()
        if inp:
            parts = inp.split()
            if len(parts) == 3:
                licht = (float(parts[0]), float(parts[1]), float(parts[2]))
    except (ValueError, EOFError):
        pass
    
    print("Berechne Normalen...")
    normals = karte.normalen(z_skalierung=2.0)
    
    print("Berechne diffuse Beleuchtung...")
    diffuse = diffuse_schatten(normals, licht)
    
    print("Berechne harte Schatten (Ray-Marching)...")
    shadow = harte_schatten_raymarch(karte, licht, schritte=64, bias=0.005)
    
    print("Berechne Spekular-Highlights (Blinn-Phong)...")
    view = (0.0, 0.0, 1.0)  # Kamera schaut von oben
    spekular = spekular_beitrag(normals, licht, view, shininess=32.0)
    
    print("Rendere Farbbild (PPM P6)...")
    h, b = karte.h, karte.b
    # PPM Header
    sys.stdout.buffer.write(f"P6\n{b} {h}\n255\n".encode())
    for y in range(h):
        row_bytes = bytearray()
        for x in range(b):
            basis = hoehe_zu_farbe(karte.daten[y][x])
            d = diffuse[y][x]
            s = shadow[y][x]
            sp = spekular[y][x]
            col = wende_licht_farbe(basis, d, s, spekular=sp, ambient=0.15)
            row_bytes.extend(col)
        sys.stdout.buffer.write(row_bytes)
    print("\nFertig! Bild auf stdout als PPM.", file=sys.stderr)

if __name__ == "__main__":
    main()