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
    """Ray-Marching-Schatten: für jeden Pixel entlang der Lichtrichtung marschieren und Prüfen, ob die Höhenkarte getroffen wird."""
    lx, ly, lz = licht_dir
    # Licht kommt *von* dieser Richtung. Wir marschieren entgegen der Lichtrichtung (also -lx, -ly, -lz)
    # Startpunkt ist auf der Oberfläche (x, y, h).
    # Wir prüfen, ob der Strahl vor Erreichen des "Lichts" die Höhe an einer anderen Stelle schneidet.
    schatten = [[1.0 for _ in range(tk.b)] for _ in range(tk.h)]
    if lz >= -1e-6: # Licht von der Seite oder unten -> kein Schatten durch Höhenkarte (vereinfacht)
        return schatten

    # Schrittweite in Weltkoordinaten (x,y sind Pixel, z ist Höhe 0..1)
    # Wir normalisieren die Schrittlänge in XY etwas, damit wir nicht zu weit springen.
    # Max Distanz diagonal über die Karte.
    max_dist = math.hypot(tk.b, tk.h)
    step_len = max_dist / schritte
    
    for y in range(tk.h):
        for x in range(tk.b):
            h_start = tk.daten[y][x]
            if h_start <= 1e-6:
                continue # Kein Objekt hier
            
            # Startposition
            cx, cy, cz = float(x), float(y), h_start
            # Richtung entgegen Lichtvektor (Licht zeigt *auf* Objekt, Schattenstrahl zeigt *weg* von Lichtquelle)
            dx, dy, dz = -lx, -ly, -lz
            
            hit = False
            for i in range(1, schritte + 1):
                t = i * step_len
                sx = cx + dx * t
                sy = cy + dy * t
                sz = cz + dz * t
                
                # Wenn wir über die Kartenhöhe hinaus sind (z > 1), brechen wir ab (kein Schatten)
                if sz > 1.0:
                    break
                
                # Prüfen ob innerhalb der Kartengrenzen
                if 0 <= sx < tk.b - 1e-4 and 0 <= sy < tk.h - 1e-4:
                    h_map = tk.get_bilinear(sy, sx)
                    # Wenn die Kartenhöhe an der Strahlposition höher ist als der Strahl selbst -> Schatten
                    # Kleines Bias gegen Self-Shadowing Akne
                    if h_map > sz + 1e-4:
                        hit = True
                        break
                else:
                    # Strahl verlässt Karte -> kein Schatten durch Gelände
                    break
            
            if hit:
                schatten[y][x] = 0.3 # Umgebungslicht im Schatten
            else:
                schatten[y][x] = 1.0
    return schatten

def blinn_phong(normal: Vec3, licht_dir: Vec3, view_dir: Vec3, schatten_faktor: float, 
                farbe: Color = (200, 180, 140), 
                ka: float = 0.2, kd: float = 0.7, ks: float = 0.3, shininess: float = 32.0) -> Color:
    """Blinn-Phong Beleuchtungsmodell."""
    # Normalisieren für Sicherheit
    n = vec3_norm(normal)
    l = vec3_norm(licht_dir)
    v = vec3_norm(view_dir)
    
    # Halbvektor
    h = vec3_norm(vec3_add(l, v))
    
    # Diffuse (N dot L)
    ndl = max(0.0, vec3_dot(n, l))
    # Spekular (N dot H)^shininess
    ndh = max(0.0, vec3_dot(n, h))
    spec = ndh ** shininess
    
    # Lichtfarbe (weiß)
    light_col = (1.0, 1.0, 1.0)
    
    r = ka * farbe[0] + schatten_faktor * (kd * ndl * farbe[0] + ks * spec * 255 * light_col[0])
    g = ka * farbe[1] + schatten_faktor * (kd * ndl * farbe[1] + ks * spec * 255 * light_col[1])
    b = ka * farbe[2] + schatten_faktor * (kd * ndl * farbe[2] + ks * spec * 255 * light_col[2])
    
    def clamp(c: float) -> int:
        return max(0, min(255, int(c)))
    
    return (clamp(r), clamp(g), clamp(b))

def rendern(tk: Tiefenkarte, licht_dir: Vec3) -> List[List[Color]]:
    """Haupt-Render-Funktion: Normalen, Schatten, Blinn-Phong."""
    print(f"  Berechne Normalen...", file=sys.stderr)
    normals = tk.normalen(z_skalierung=2.0)
    print(f"  Berechne Schatten (Ray Marching)...", file=sys.stderr)
    schatten = diffuse_schatten(tk, normals, licht_dir, schritte=64)
    
    # View Direction: Kamera schaut von vorn (0, 0, -1) auf die XY-Ebene
    # Da unser Koordinatensystem: x rechts, y runter, z hoch -> Kamera bei z=+inf schaut in -z Richtung
    view_dir = (0.0, 0.0, -1.0)
    
    bild: List[List[Color]] = []
    for y in range(tk.h):
        reihe: List[Color] = []
        for x in range(tk.b):
            h = tk.daten[y][x]
            if h < 1e-4:
                reihe.append((0, 0, 0)) # Hintergrund schwarz
            else:
                col = blinn_phong(normals[y][x], licht_dir, view_dir, schatten[y][x])
                reihe.append(col)
        bild.append(reihe)
    return bild

def schreibe_ppm(bild: List[List[Color]], out_stream: sys.stdout) -> None:
    """Schreibt PPM (P6 binary) auf stdout.buffer."""
    if not bild or not bild[0]:
        return
    h = len(bild)
    b = len(bild[0])
    header = f"P6\n{b} {h}\n255\n".encode('ascii')
    out_stream.buffer.write(header)
    for reihe in bild:
        for r, g, b in reihe:
            out_stream.buffer.write(bytes((r, g, b)))

# ---------- Hauptprogramm ----------

def eingabe(prompt: str, default: str = "") -> Optional[str]:
    """Sichere Eingabe mit EOF-Behandlung."""
    try:
        val = input(prompt)
        return val.strip()
    except EOFError:
        return None

def main() -> None:
    print("Schatten-Simulator – Teil 35: Ray-Marching-Schatten, Blinn-Phong, PPM-Ausgabe", file=sys.stderr)
    print("Verfügbare Formen: 1=Kugel, 2=Kegel, 3=Stufenpyramide, 4=Wellblech, 5=Zufällige Hügel", file=sys.stderr)
    
    formen = {
        '1': erzeuge_kugel,
        '2': erzeuge_kegel,
        '3': erzeuge_stufenpyramide,
        '4': erzeuge_wellblech,
        '5': erzeuge_zufaellige_huegel,
    }
    
    wahl = eingabe("Form wählen [1-5] (Enter=1): ", "1")
    if wahl is None: return
    if wahl not in formen: wahl = '1'
    
    b_str = eingabe("Breite (Zeichen) [40]: ", "40")
    if b_str is None: return
    h_str = eingabe("Höhe (Zeilen) [20]: ", "20")
    if h_str is None: return
    
    try:
        b = max(10, min(200, int(b_str)))
        h = max(10, min(100, int(h_str)))
    except ValueError:
        b, h = 40, 20
    
    licht_str = eingabe("Lichtrichtung x y z (z.B. 0.5 -0.5 1) [0.5 -0.5 1]: ", "0.5 -0.5 1")
    if licht_str is None: return
    try:
        lx, ly, lz = map(float, licht_str.split())
        licht_dir = vec3_norm((lx, ly, lz))
    except ValueError:
        licht_dir = vec3_norm((0.5, -0.5, 1.0))
    
    print(f"Erzeuge Form {wahl} ({b}x{h})...", file=sys.stderr)
    tk = formen[wahl](h, b)
    
    print(f"Rendere Bild...", file=sys.stderr)
    bild = rendern(tk, licht_dir)
    
    print(f"Schreibe PPM auf stdout...", file=sys.stderr)
    schreibe_ppm(bild, sys.stdout)
    print(f"Fertig.", file=sys.stderr)

if __name__ == "__main__":
    main()