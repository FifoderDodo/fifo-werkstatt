from __future__ import annotations
import math
import sys
import random
from typing import List, Tuple, Optional, Dict

Vec3 = Tuple[float, float, float]

# ---------- Vektor-Mathematik ----------

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

def vec3_sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def vec3_scale(v: Vec3, s: float) -> Vec3:
    return (v[0] * s, v[1] * s, v[2] * s)

def vec3_reflect(v: Vec3, n: Vec3) -> Vec3:
    dot = vec3_dot(v, n)
    return vec3_sub(v, vec3_scale(n, 2.0 * dot))

# ---------- Wert-Rauschen (Value Noise) ----------

def _fade(t: float) -> float:
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

def _lerp(a: float, b: float, t: float) -> float:
    return a + t * (b - a)

class ValueNoise:
    """Einfaches 2D Value Noise mit Permutationstabelle."""
    def __init__(self, seed: int = 0):
        random.seed(seed)
        self.perm = list(range(256))
        random.shuffle(self.perm)
        self.perm += self.perm  # für schnellen Indexzugriff
    
    def _hash(self, x: int, y: int) -> float:
        h = self.perm[(x + self.perm[y & 255]) & 255]
        return (h / 255.0) * 2.0 - 1.0  # -1 bis 1
    
    def sample(self, x: float, y: float) -> float:
        x0 = int(math.floor(x))
        y0 = int(math.floor(y))
        x1 = x0 + 1
        y1 = y0 + 1
        tx = _fade(x - x0)
        ty = _fade(y - y0)
        h00 = self._hash(x0, y0)
        h10 = self._hash(x1, y0)
        h01 = self._hash(x0, y1)
        h11 = self._hash(x1, y1)
        return _lerp(_lerp(h00, h10, tx), _lerp(h01, h11, tx), ty)
    
    def fractal(self, x: float, y: float, okta: int = 5, persistenz: float = 0.5, laengenskalierung: float = 0.05) -> float:
        wert = 0.0
        amp = 1.0
        freq = laengenskalierung
        max_wert = 0.0
        for _ in range(okta):
            wert += self.sample(x * freq, y * freq) * amp
            max_wert += amp
            amp *= persistenz
            freq *= 2.0
        return wert / max_wert if max_wert > 0 else 0.0

# ---------- Tiefenkarte ----------

class Tiefenkarte:
    """Speichert Höhendaten und errechnet Normalenvektoren zur Tiefenerzwingung."""

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
        return (h00 * (1.0 - dx) + h01 * dx) * (1.0 - dy) + (h10 * (1.0 - dx) + h11 * dx) * dy

    def normalen(self, z_faktor: float = 2.5) -> List[List[Vec3]]:
        """Berechnet Normalen per Sobel-Filter (3x3) für mathematisch glattere Kanten."""
        normals: List[List[Vec3]] = []
        for y in range(self.h):
            reihe: List[Vec3] = []
            for x in range(self.b):
                gx = (
                    -self.get(y-1, x-1) + self.get(y-1, x+1)
                    -2.0 * self.get(y, x-1)   + 2.0 * self.get(y, x+1)
                    -self.get(y+1, x-1) + self.get(y+1, x+1)
                ) * 0.125 * z_faktor
                gy = (
                    -self.get(y-1, x-1) - 2.0 * self.get(y-1, x) - self.get(y-1, x+1)
                    +self.get(y+1, x-1) + 2.0 * self.get(y+1, x) + self.get(y+1, x+1)
                ) * 0.125 * z_faktor
                reihe.append(vec3_norm((-gx, -gy, 1.0)))
            normals.append(reihe)
        return normals

    def statistik(self) -> Tuple[float, float, float]:
        flach = [w for reihe in self.daten for w in reihe]
        if not flach:
            return 0.0, 0.0, 0.0
        mn, mx = min(flach), max(flach)
        return mn, mx, mx - mn

# ---------- Lichtquellen-System ----------

class Lichtquelle:
    """Punktförmiges oder gerichtetes Licht mit Vektorberechnung."""

    def __init__(self, typ: str, pos_oder_dir: Vec3, intensitaet: float = 1.0, abfall: float = 0.002):
        self.typ = typ  # 'gerichtet' oder 'punkt'
        self.vec = pos_oder_dir
        self.intensitaet = intensitaet
        self.abfall = abfall

    def vektor_und_distanz(self, p: Vec3) -> Tuple[Vec3, float]:
        if self.typ == 'gerichtet':
            return vec3_norm(self.vec), 1e6
        else:
            diff = vec3_sub(self.vec, p)
            dist = math.sqrt(vec3_dot(diff, diff))
            l_dir = vec3_norm(diff) if dist > 1e-6 else (0.0, 0.0, 1.0)
            return l_dir, dist

    def energie_an(self, dist: float) -> float:
        if self.typ == 'gerichtet':
            return self.intensitaet
        return self.intensitaet / (1.0 + self.abfall * dist * dist)

# ---------- 3D Raymarching & Shading ----------

def raymarch_schatten(tk: Tiefenkarte, start: Vec3, l_dir: Vec3, max_dist: float, z_skalierung: float, schritte: int = 24) -> float:
    """Prüft entlang des Lichtvektors in Weltkoordinaten, ob die Tiefenkarte die Sichtlinie schneidet."""
    offset = 0.4 * z_skalierung
    curr_x = start[0] + l_dir[0] * offset
    curr_y = start[1] + l_dir[1] * offset
    curr_z = start[2] + l_dir[2] * offset
    
    schrittweite = max(0.5, max_dist / schritte)
    for _ in range(schritte):
        # Weltkoordinaten in Heightmap-Indizes (y, x) umrechnen
        h_here = tk.get_bilinear(curr_y, curr_x) * z_skalierung
        if curr_z < h_here:
            return 0.0  # im Schatten
        curr_x += l_dir[0] * schrittweite
        curr_y += l_dir[1] * schrittweite
        curr_z += l_dir[2] * schrittweite
    return 1.0  # kein Schatten

def phong_shading(
    normal: Vec3,
    view_dir: Vec3,
    lights: List[Lichtquelle],
    pos: Vec3,
    tk: Tiefenkarte,
    z_skalierung: float,
    ambient: float = 0.15,
    diffus: float = 0.8,
    spekular: float = 0.3,
    glanz: float = 32.0
) -> Tuple[float, float, float]:
    """Berechnet Phong-Beleuchtung mit Weichschatten (mehrere Samples pro Licht)."""
    r, g, b = ambient, ambient, ambient
    for light in lights:
        l_dir, dist = light.vektor_und_distanz(pos)
        energie = light.energie_an(dist)
        # Weichschatten: 3 Samples mit kleinem Jitter
        schatten = 0.0
        for j in range(3):
            jitter = (random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15))
            jittered_start = vec3_add(pos, jitter)
            schatten += raymarch_schatten(tk, jittered_start, l_dir, dist, z_skalierung, schritte=16)
        schatten /= 3.0
        if schatten < 0.02:
            continue
        # Diffuse
        ndl = max(0.0, vec3_dot(normal, l_dir))
        # Spekular (Blinn-Phong)
        half_vec = vec3_norm(vec3_add(l_dir, view_dir))
        ndh = max(0.0, vec3_dot(normal, half_vec))
        spec = (ndh ** glanz) * spekular
        diff = ndl * diffus
        r += (diff + spec) * energie * schatten
        g += (diff + spec) * energie * schatten
        b += (diff + spec) * energie * schatten
    return (min(1.0, r), min(1.0, g), min(1.0, b))

# ---------- ANSI-Renderer ----------

def rgb_to_ansi256(r: float, g: float, b: float) -> int:
    """Konvertiert 0-1 RGB in ANSI-256-Farbindex (6x6x6-Würfel + Graustufen)."""
    r_i = int(r * 5 + 0.5)
    g_i = int(g * 5 + 0.5)
    b_i = int(b * 5 + 0.5)
    if r_i == g_i == b_i:
        # Graustufe 232-255
        gray = int(r * 23 + 0.5)
        return 232 + max(0, min(23, gray))
    return 16 + 36 * r_i + 6 * g_i + b_i

def ansi_fg(code: int) -> str:
    return f"\x1b[38;5;{code}m"

def ansi_reset() -> str:
    return "\x1b[0m"

def render_ansi(tk: Tiefenkarte, normals: List[List[Vec3]], lights: List[Lichtquelle], z_skalierung: float, breite: int = 80, hoehe: int = 40) -> List[str]:
    """Rendert die Tiefenkarte als ANSI-Farbbild mit bilinearer Interpolation."""
    view_dir = (0.0, 0.0, -1.0)  # Kamera schaut von oben (-Z)
    max_dist = max(tk.b, tk.h) * z_skalierung * 1.5
    out_lines: List[str] = []
    for zeile in range(hoehe):
        line_parts: List[str] = []
        for spalte in range(breite):
            # Zielkoordinaten in Heightmap-Raum
            u = (spalte + 0.5) / breite * (tk.b - 1)
            v = (zeile + 0.5) / hoehe * (tk.h - 1)
            h = tk.get_bilinear(v, u) * z_skalierung
            # Normal bilinear interpolieren
            n = (0.0, 0.0, 1.0)
            if 0 <= v < tk.h - 1 and 0 <= u < tk.b - 1:
                y0, x0 = int(v), int(u)
                dy, dx = v - y0, u - x0
                n00 = normals[y0][x0]
                n10 = normals[y0][x0+1]
                n01 = normals[y0+1][x0]
                n11 = normals[y0+1][x0+1]
                nx = (n00[0]*(1-dx)+n10[0]*dx)*(1-dy) + (n01[0]*(1-dx)+n11[0]*dx)*dy
                ny = (n00[1]*(1-dx)+n10[1]*dx)*(1-dy) + (n01[1]*(1-dx)+n11[1]*dx)*dy
                nz = (n00[2]*(1-dx)+n10[2]*dx)*(1-dy) + (n01[2]*(1-dx)+n11[2]*dx)*dy
                n = vec3_norm((nx, ny, nz))
            pos = (u, v, h)
            col = phong_shading(n, view_dir, lights, pos, tk, z_skalierung)
            ansi_code = rgb_to_ansi256(*col)
            # Zeichen nach Helligkeit wählen
            lum = 0.2126*col[0] + 0.7152*col[1] + 0.0722*col[2]
            if lum > 0.7:
                ch = "#"
            elif lum > 0.5:
                ch = "o"
            elif lum > 0.3:
                ch = "*"
            elif lum > 0.15:
                ch = "."
            else:
                ch = " "
            line_parts.append(f"{ansi_fg(ansi_code)}{ch}{ansi_reset()}")
        out_lines.append("".join(line_parts))
    return out_lines

# ---------- Hauptprogramm ----------

def main() -> None:
    random.seed(42)  # reproduzierbar
    print("Schatten-Simulator – Part 53/55")
    print("================================")
    try:
        # Parameter per Input oder Defaults
        b = int(input("Breite der Heightmap (Default 120): ") or "120")
        h = int(input("Höhe der Heightmap (Default 60): ") or "60")
        skal = float(input("Z-Skalierung (Default 8.0): ") or "8.0")
        seed = int(input("Noise-Seed (Default 12345): ") or "12345")
        okta = int(input("Oktaven (Default 6): ") or "6")
        pers = float(input("Persistenz (Default 0.5): ") or "0.5")
        lac = float(input("Lakunarität (Default 2.0): ") or "2.0")
    except (EOFError, ValueError):
        print("\nEingabe abgebrochen oder ungültig – nutze Defaults.")
        b, h, skal, seed, okta, pers, lac = 120, 60, 8.0, 12345, 6, 0.5, 2.0
    
    # Prozedurale Landschaft generieren
    noise = ValueNoise(seed)
    daten: List[List[float]] = []
    for y in range(h):
        reihe: List[float] = []
        for x in range(b):
            # Mehrere Noise-Layer für interessante Formen
            base = noise.fractal(x, y, okta, pers, 0.015)
            detail = noise.fractal(x*2, y*2, 3, 0.3, 0.08) * 0.15
            ridge = 1.0 - abs(noise.fractal(x*0.5, y*0.5, 4, 0.5, 0.03))
            reihe.append(max(0.0, min(1.0, base*0.6 + detail + ridge*0.25)))
        daten.append(reihe)
    
    tk = Tiefenkarte(daten)
    mn, mx, rng = tk.statistik()
    print(f"Heightmap: {b}x{h}, Range [{mn:.3f}, {mx:.3f}], Spanne {rng:.3f}")
    
    normals = tk.normalen(z_faktor=skal)
    
    # Lichtquellen definieren
    lights = [
        Lichtquelle('gerichtet', vec3_norm((0.6, -0.4, -1.0)), 1.2),
        Lichtquelle('punkt', (b*0.5, h*0.2, skal*1.5), 0.8, 0.001),
        Lichtquelle('punkt', (b*0.8, h*0.8, skal*1.0), 0.5, 0.002),
    ]
    
    # Rendern
    print("\nRendere ANSI-Bild (80x40)...")
    frame = render_ansi(tk, normals, lights, skal, 80, 40)
    for line in frame:
        print(line)
    
    # Helligkeits-Testpunkte
    print("\nHelligkeits-Test an 5 zufälligen Stellen:")
    for _ in range(5):
        tx = random.uniform(0, b-1)
        ty = random.uniform(0, h-1)
        th = tk.get_bilinear(ty, tx) * skal
        tn = normals[int(ty)][int(tx)] if 0 <= int(ty) < h and 0 <= int(tx) < b else (0,0,1)
        tp = (tx, ty, th)
        col = phong_shading(tn, (0,0,-1), lights, tp, tk, skal)
        lum = 0.2126*col[0] + 0.7152*col[1] + 0.0722*col[2]
        print(f"  ({tx:.1f},{ty:.1f}) h={th:.2f} col=({col[0]:.2f},{col[1]:.2f},{col[2]:.2f}) lum={lum:.2f}")
    
    print("\nFertig. Drücke Enter für Ende oder Strg+C zum Abbruch.")
    try:
        input()
    except EOFError:
        pass
    print("Tschüss!")

if __name__ == "__main__":
    main()