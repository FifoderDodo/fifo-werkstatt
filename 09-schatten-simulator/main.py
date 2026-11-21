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
        # Weltkoordinaten in Tiefenkarten-Indizes umrechnen
        ix = curr_x
        iy = curr_y
        if 0 <= iy < tk.h and 0 <= ix < tk.b:
            h = tk.get_bilinear(iy, ix)
            if curr_z <= h * z_skalierung:
                return 0.0  # im Schatten
        curr_x += l_dir[0] * schrittweite
        curr_y += l_dir[1] * schrittweite
        curr_z += l_dir[2] * schrittweite
    return 1.0  # beleuchtet

def phong_shading(normal: Vec3, view_dir: Vec3, lights: List[Lichtquelle], pos: Vec3, z_skalierung: float, tk: Tiefenkarte, schatten_schritte: int = 24) -> Vec3:
    """Einfaches Phong-Shading mit Schatten."""
    ambient = 0.15
    diffuse = 0.0
    specular = 0.0
    shininess = 32.0
    
    for light in lights:
        l_dir, dist = light.vektor_und_distanz(pos)
        energie = light.energie_an(dist)
        # Schatten
        schatten = raymarch_schatten(tk, pos, l_dir, dist, z_skalierung, schatten_schritte)
        if schatten < 0.5:
            continue
        # Diffuse
        ndotl = max(0.0, vec3_dot(normal, l_dir))
        diffuse += ndotl * energie
        # Specular (Blinn-Phong)
        h = vec3_norm(vec3_add(l_dir, view_dir))
        ndoth = max(0.0, vec3_dot(normal, h))
        specular += (ndoth ** shininess) * energie
    
    r = ambient + diffuse * 0.7 + specular * 0.5
    g = ambient + diffuse * 0.6 + specular * 0.5
    b = ambient + diffuse * 0.5 + specular * 0.5
    return (min(1.0, r), min(1.0, g), min(1.0, b))

def rgb_to_ansi(r: float, g: float, b: float) -> str:
    """Wandelt 0-1 RGB in ANSI 256-Farben-Escape um."""
    ri = int(r * 5)
    gi = int(g * 5)
    bi = int(b * 5)
    idx = 16 + ri * 36 + gi * 6 + bi
    return f"\033[38;5;{idx}m"

def eingabe_mit_default(prompt: str, default: str, typ: type = str) -> any:
    """Hilfsfunktion für robuste Eingabe mit Default und Typkonvertierung."""
    try:
        val = input(f"{prompt} [{default}]: ").strip()
        if val == '':
            val = default
        return typ(val)
    except (ValueError, EOFError):
        print(f" -> Ungültig, nutze Default: {default}")
        return typ(default)

def main() -> None:
    print("=== Schatten-Simulator v1.0 (Finale) ===")
    print("Raymarching-Schatten, Mehrfachlicht, weiche Schatten, ANSI-Farben")
    print("Drücke Strg+C oder Strg+D zum Beenden.\n")
    
    try:
        breite = eingabe_mit_default("Breite", "80", int)
        hoehe = eingabe_mit_default("Höhe", "40", int)
        seed = eingabe_mit_default("Seed", "42", int)
        oktaven = eingabe_mit_default("Oktaven", "5", int)
        persistenz = eingabe_mit_default("Persistenz", "0.5", float)
        noise_skalierung = eingabe_mit_default("Noise-Skalierung", "0.05", float)
        z_faktor = eingabe_mit_default("Z-Faktor (Höhenübertreibung)", "2.5", float)
    except EOFError:
        print("\nTschüss!")
        return
    
    # Tiefenkarte generieren
    noise = ValueNoise(seed)
    daten = []
    for y in range(hoehe):
        reihe = []
        for x in range(breite):
            h = noise.fractal(x, y, oktaven, persistenz, noise_skalierung)
            reihe.append((h + 1.0) * 0.5)  # 0..1
        daten.append(reihe)
    
    tk = Tiefenkarte(daten)
    normalen = tk.normalen(z_faktor)
    
    # Lichtquellen definieren
    lights = [
        Lichtquelle('gerichtet', vec3_norm((0.5, -0.3, -1.0)), 1.2),
        Lichtquelle('punkt', (breite * 0.5, hoehe * 0.3, 30.0), 0.8, 0.001),
    ]
    view_dir = vec3_norm((0.0, 0.0, -1.0))
    
    # Rendering
    print("\nRendering...")
    out_lines = []
    for y in range(hoehe):
        line = ""
        for x in range(breite):
            h = tk.daten[y][x]
            pos = (float(x), float(y), h * z_faktor)
            n = normalen[y][x]
            col = phong_shading(n, view_dir, lights, pos, z_faktor, tk)
            ansi = rgb_to_ansi(*col)
            # Zeichen nach Helligkeit wählen
            helligkeit = (col[0] + col[1] + col[2]) / 3.0
            if helligkeit > 0.7:
                ch = "@"
            elif helligkeit > 0.5:
                ch = "#"
            elif helligkeit > 0.3:
                ch = "+"
            elif helligkeit > 0.15:
                ch = "."
            else:
                ch = " "
            line += f"{ansi}{ch}"
        line += "\033[0m"  # Reset
        out_lines.append(line)
    
    print("\n" + "\n".join(out_lines))
    print("\nFertig.")

if __name__ == "__main__":
    main()