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

def vec3_lerp(a: Vec3, b: Vec3, t: float) -> Vec3:
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t)

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
    lx, ly, lz = licht_dir
    if lz >= 0:
        return shadow
    for y in range(h):
        for x in range(b):
            n = normals[y][x]
            ndotl = vec3_dot(n, licht_dir)
            if ndotl <= 0:
                shadow[y][x] = 0.0
                continue
            px = x + 0.5
            py = y + 0.5
            pz = tk.daten[y][x]
            step_x = -lx / schritte
            step_y = -ly / schritte
            step_z = -lz / schritte
            blocked = False
            for i in range(1, schritte):
                px += step_x
                py += step_y
                pz += step_z
                if pz <= 0:
                    break
                ix = int(px)
                iy = int(py)
                if 0 <= ix < b and 0 <= iy < h:
                    h_terrain = tk.get_bilinear(iy, ix)
                    if pz < h_terrain - 1e-4:
                        blocked = True
                        break
            shadow[y][x] = 0.0 if blocked else 1.0
    return shadow


def blinn_phong(normal: Vec3, licht_dir: Vec3, view_dir: Vec3,
                kd: float = 0.8, ks: float = 0.3, shininess: float = 32.0) -> float:
    """Blinn-Phong BRDF, gibt Helligkeitsfaktor 0..1 zurück."""
    ndotl = max(0.0, vec3_dot(normal, licht_dir))
    if ndotl == 0.0:
        return 0.0
    half_vec = vec3_norm(vec3_add(licht_dir, view_dir))
    ndoth = max(0.0, vec3_dot(normal, half_vec))
    spec = ks * (ndoth ** shininess)
    diffuse = kd * ndotl
    return min(1.0, diffuse + spec)


def ambient_occlusion(tk: Tiefenkarte, normals: List[List[Vec3]], samples: int = 8, radius: float = 2.0) -> List[List[float]]:
    """Screen-Space Ambient Occlusion (vereinfacht)."""
    h, b = tk.h, tk.b
    ao = [[1.0 for _ in range(b)] for _ in range(h)]
    for y in range(h):
        for x in range(b):
            n = normals[y][x]
            occ = 0
            for i in range(samples):
                angle = 2.0 * math.pi * i / samples
                dx = math.cos(angle) * radius
                dy = math.sin(angle) * radius
                sx = x + dx
                sy = y + dy
                if 0 <= sx < b and 0 <= sy < h:
                    h_sample = tk.get_bilinear(sy, sx)
                    h_center = tk.daten[y][x]
                    if h_sample > h_center:
                        occ += 1
            ao[y][x] = 1.0 - (occ / samples) * 0.5
    return ao

# ---------- Render-Pipeline ----------

def render(tk: Tiefenkarte,
           licht_dir: Vec3 = (0.5, -0.3, -0.8),
           view_dir: Vec3 = (0.0, 0.0, 1.0),
           skala: float = 1.0,
           gamma: float = 2.2) -> List[List[Color]]:
    """Rendert die Tiefenkarte zu einem Farbbild (Höhe x Breite)."""
    h, b = tk.h, tk.b
    out_h = max(1, int(h * skala))
    out_b = max(1, int(b * skala))
    
    normals = tk.normalen()
    shadow = diffuse_schatten(tk, normals, licht_dir)
    ao = ambient_occlusion(tk, normals)
    
    bild: List[List[Color]] = []
    for y in range(out_h):
        reihe: List[Color] = []
        sy = y / skala
        for x in range(out_b):
            sx = x / skala
            iy = int(sy)
            ix = int(sx)
            if 0 <= iy < h and 0 <= ix < b:
                n = normals[iy][ix]
                h_val = tk.daten[iy][ix]
                sh = shadow[iy][ix]
                ao_val = ao[iy][ix]
                
                if h_val <= 0:
                    reihe.append((10, 10, 20))
                    continue
                
                lighting = blinn_phong(n, licht_dir, view_dir)
                lighting *= sh
                lighting *= ao_val
                
                base_color = (200, 180, 140)
                r = base_color[0] * lighting
                g = base_color[1] * lighting
                b_col = base_color[2] * lighting
                
                height_tint = h_val * 0.3
                r += 50 * height_tint
                g += 40 * height_tint
                b_col += 30 * height_tint
                
                def gammac(c: float) -> int:
                    c = max(0.0, min(1.0, c / 255.0))
                    return int(pow(c, 1.0 / gamma) * 255 + 0.5)
                
                reihe.append((gammac(r), gammac(g), gammac(b_col)))
            else:
                reihe.append((0, 0, 0))
        bild.append(reihe)
    return bild


def schreiben_ppm(bild: List[List[Color]], out=sys.stdout.buffer) -> None:
    """Schreibt P6-PPM (binär) auf stdout."""
    h = len(bild)
    b = len(bild[0]) if h > 0 else 0
    out.write(f"P6\n{b} {h}\n255\n".encode('ascii'))
    for reihe in bild:
        for r, g, b_col in reihe:
            out.write(bytes([r & 255, g & 255, b_col & 255]))


def schreiben_ascii(bild: List[List[Color]]) -> None:
    """Fallback: kleines ASCII-Preview auf stderr."""
    chars = " .:-=+*#%@"
    for reihe in bild:
        line = ""
        for r, g, b_col in reihe:
            lum = (r + g + b_col) / 3.0 / 255.0
            idx = int(lum * (len(chars) - 1))
            line += chars[idx]
        print(line, file=sys.stderr)

# ---------- Eingabe & Hauptprogramm ----------

def frage(prompt: str, default: str = "") -> str:
    try:
        val = input(f"{prompt} ")
        return val.strip() if val.strip() else default
    except EOFError:
        print("\nKeine Eingabe – Tschüss!", file=sys.stderr)
        sys.exit(0)


def wahl(prompt: str, optionen: List[str], default: str) -> str:
    val = frage(f"{prompt} [{', '.join(optionen)}] [{default}]", default)
    if val in optionen:
        return val
    print(f"Unbekannte Wahl '{val}', nehme '{default}'.", file=sys.stderr)
    return default


def zahl(prompt: str, default: int, min_wert: int = 1, max_wert: int = 200) -> int:
    val = frage(f"{prompt} [{default}]", str(default))
    try:
        n = int(val)
        return max(min_wert, min(max_wert, n))
    except ValueError:
        return default


def main() -> None:
    print("Schatten-Simulator – Träumt weiter, kleiner Dodo.", file=sys.stderr)
    
    h = zahl("Höhe", 20, 5, 100)
    b = zahl("Breite", 40, 5, 200)
    
    formen = ['kugel', 'kegel', 'pyramide', 'wellblech', 'huegel']
    form = wahl("Form", formen, 'kugel')
    
    skala_str = frage("Ausgabe-Skalierung (1.0 = 1:1, 0.5 = halb so gross) [1.0]", "1.0")
    try:
        skala = float(skala_str)
    except ValueError:
        skala = 1.0
    skala = max(0.1, min(4.0, skala))
    
    if form == 'kugel':
        tk = erzeuge_kugel(h, b)
    elif form == 'kegel':
        tk = erzeuge_kegel(h, b)
    elif form == 'pyramide':
        tk = erzeuge_stufenpyramide(h, b)
    elif form == 'wellblech':
        tk = erzeuge_wellblech(h, b)
    else:
        tk = erzeuge_zufaellige_huegel(h, b)
    
    mn, mx, span = tk.statistik()
    print(f"Fertig: {tk.h}x{tk.b}, Form={form}, Höhe {mn:.3f}..{mx:.3f} (Spannweite {span:.3f})", file=sys.stderr)
    
    bild = render(tk, skala=skala)
    
    # ASCII-Preview auf stderr
    schreiben_ascii(bild)
    
    # PPM auf stdout
    schreiben_ppm(bild)

if __name__ == "__main__":
    main()