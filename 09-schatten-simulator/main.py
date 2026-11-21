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
    lx, ly, lz = licht_dir
    # Licht kommt von oben, also negativ in y-Richtung für 2D-Koordinaten
    # Wir marschieren entgegen der Lichtrichtung (also zum Licht hin)
    step_x = -lx * 0.5  # x-Skalierung wie bei Normalen
    step_y = -ly
    step_z = -lz
    
    schatten = [[1.0 for _ in range(b)] for _ in range(h)]
    
    for y in range(h):
        for x in range(b):
            if tk.daten[y][x] <= 0.0:
                schatten[y][x] = 1.0
                continue
            
            # Startpunkt leicht versetzt (Bias gegen Self-Shadow-Acne)
            start_z = tk.daten[y][x] + 0.01
            cur_x = x + step_x * 0.5
            cur_y = y + step_y * 0.5
            cur_z = start_z + step_z * 0.5
            
            blocked = False
            for i in range(schritte):
                if cur_z <= 0.0:
                    break
                if cur_x < 0 or cur_x >= b - 1 or cur_y < 0 or cur_y >= h - 1:
                    break
                
                h_feld = tk.get_bilinear(cur_y, cur_x)
                if cur_z <= h_feld + 0.001:  # Epsilon für numerische Stabilität
                    blocked = True
                    break
                
                cur_x += step_x
                cur_y += step_y
                cur_z += step_z
            
            schatten[y][x] = 0.3 if blocked else 1.0  # Weicher Schatten, nicht ganz schwarz
    
    return schatten

def blinn_phong(normal: Vec3, licht_dir: Vec3, view_dir: Vec3, schatten_faktor: float,
                kd: Color = (200, 180, 160), ks: Color = (255, 255, 255),
                ka: Color = (30, 25, 20), shininess: float = 32.0) -> Color:
    """Blinn-Phong Shading mit Schatten."""
    n_dot_l = max(0.0, vec3_dot(normal, licht_dir))
    
    # Halfway-Vektor für Blinn-Phong
    hx = licht_dir[0] + view_dir[0]
    hy = licht_dir[1] + view_dir[1]
    hz = licht_dir[2] + view_dir[2]
    h_len = math.sqrt(hx*hx + hy*hy + hz*hz)
    if h_len > 1e-9:
        half = (hx/h_len, hy/h_len, hz/h_len)
        n_dot_h = max(0.0, vec3_dot(normal, half))
        spec = n_dot_h ** shininess
    else:
        spec = 0.0
    
    r = int(ka[0] + schatten_faktor * (kd[0] * n_dot_l + ks[0] * spec))
    g = int(ka[1] + schatten_faktor * (kd[1] * n_dot_l + ks[1] * spec))
    b = int(ka[2] + schatten_faktor * (kd[2] * n_dot_l + ks[2] * spec))
    
    return (min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b)))

def render(tk: Tiefenkarte, licht_dir: Vec3, view_dir: Vec3) -> List[List[Color]]:
    """Vollständiger Render-Pass: Normalen, Schatten, Shading."""
    normals = tk.normalen()
    schatten = diffuse_schatten(tk, normals, licht_dir)
    
    bild: List[List[Color]] = []
    for y in range(tk.h):
        reihe: List[Color] = []
        for x in range(tk.b):
            if tk.daten[y][x] <= 0.0:
                reihe.append((0, 0, 0))  # Hintergrund schwarz
            else:
                col = blinn_phong(normals[y][x], licht_dir, view_dir, schatten[y][x])
                reihe.append(col)
        bild.append(reihe)
    return bild

def schreibe_ppm(bild: List[List[Color]], out=sys.stdout.buffer) -> None:
    """Schreibt PPM Binary (P6) auf stdout."""
    h = len(bild)
    b = len(bild[0]) if h > 0 else 0
    out.write(f"P6 {b} {h} 255\n".encode('ascii'))
    for reihe in bild:
        for r, g, b_ in reihe:
            out.write(bytes([r, g, b_]))

def lies_int(prompt: str, default: int, min_wert: int = 1, max_wert: int = 200) -> int:
    """Liest Integer mit Default und EOF-Schutz."""
    try:
        s = input(prompt).strip()
        if not s:
            return default
        val = int(s)
        return max(min_wert, min(max_wert, val))
    except (EOFError, ValueError):
        return default

def lies_form(prompt: str, default: str, optionen: List[str]) -> str:
    """Liest Form-Auswahl mit Default und EOF-Schutz."""
    try:
        s = input(prompt).strip().lower()
        if not s:
            return default
        if s in optionen:
            return s
        print(f"Unbekannte Form '{s}', nehme '{default}'.", file=sys.stderr)
        return default
    except EOFError:
        return default

def main() -> None:
    print("Schatten-Simulator – Träumt weiter, kleiner Dodo.", file=sys.stderr)
    
    h = lies_int("Höhe [20]: ", 20, 5, 100)
    b = lies_int("Breite [40]: ", 40, 5, 200)
    
    formen = {
        'kugel': erzeuge_kugel,
        'kegel': erzeuge_kegel,
        'pyramide': erzeuge_stufenpyramide,
        'wellblech': erzeuge_wellblech,
        'huegel': erzeuge_zufaellige_huegel,
    }
    form_namen = list(formen.keys())
    form = lies_form(f"Form {form_namen} [kugel]: ", "kugel", form_namen)
    
    tk = formen[form](h, b)
    
    # Licht von oben-links-hinten
    licht = vec3_norm((-0.5, -0.3, -1.0))
    # Kamera schaut von vorne (Viewer in +Z)
    view = (0.0, 0.0, 1.0)
    
    bild = render(tk, licht, view)
    schreibe_ppm(bild)
    
    # Kurze Statistik auf stderr
    mn, mx, span = tk.statistik()
    print(f"Fertig: {h}x{b}, Form={form}, Höhe {mn:.3f}..{mx:.3f} (Spannweite {span:.3f})", file=sys.stderr)

if __name__ == "__main__":
    main()