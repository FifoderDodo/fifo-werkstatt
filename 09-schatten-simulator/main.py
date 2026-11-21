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
            hoehe = tk.get_bilinear(iy, ix) * z_skalierung
            if curr_z <= hoehe:
                return 0.0  # im Schatten
        curr_x += l_dir[0] * schrittweite
        curr_y += l_dir[1] * schrittweite
        curr_z += l_dir[2] * schrittweite
    return 1.0  # beleuchtet

def shade_pixel(tk: Tiefenkarte, normals: List[List[Vec3]], x: int, y: int,
                z_skalierung: float, ambient: float, glanz_staerke: float, glanz_haerte: float,
                lichtquellen: List[Lichtquelle], view_dir: Vec3) -> float:
    """Berechnet Helligkeit eines Pixels (0..1) mit diffus, spekular, Schatten."""
    n = normals[y][x]
    p = (float(x), float(y), tk.daten[y][x] * z_skalierung)
    farbe = ambient
    for lq in lichtquellen:
        l_dir, dist = lq.vektor_und_distanz(p)
        ndotl = max(0.0, vec3_dot(n, l_dir))
        if ndotl > 0:
            schatten = raymarch_schatten(tk, p, l_dir, dist, z_skalierung)
            diffuse = ndotl * schatten
            # Spekular (Blinn-Phong)
            h = vec3_norm(vec3_add(l_dir, view_dir))
            ndoth = max(0.0, vec3_dot(n, h))
            spekular = (ndoth ** glanz_haerte) * glanz_staerke * schatten
            farbe += lq.energie_an(dist) * (diffuse + spekular)
    return max(0.0, min(1.0, farbe))

# ---------- ASCII Rendering ----------
ASCII_RAMPE = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. "

def render_ascii(tk: Tiefenkarte, normals: List[List[Vec3]], z_skalierung: float, ambient: float,
                 glanz_staerke: float, glanz_haerte: float, lichtquellen: List[Lichtquelle]) -> List[str]:
    """Rendert die komplette Tiefenkarte als ASCII-Zeilen."""
    view_dir = (0.0, 0.0, -1.0)  # orthografische Ansicht von oben
    zeilen = []
    for y in range(tk.h):
        zeile_chars = []
        for x in range(tk.b):
            hell = shade_pixel(tk, normals, x, y, z_skalierung, ambient, glanz_staerke, glanz_haerte,
                               lichtquellen, view_dir)
            idx = int(hell * (len(ASCII_RAMPE) - 1))
            zeile_chars.append(ASCII_RAMPE[idx])
        zeilen.append(''.join(zeile_chars))
    return zeilen

# ---------- Hilfsfunktionen für Eingabe ----------

def read_float(prompt: str, default: float) -> float:
    try:
        s = input(prompt).strip()
        if s == '':
            return default
        return float(s)
    except (ValueError, EOFError):
        print("Ungültige Zahl, wird ignoriert.")
        return default

def read_int(prompt: str, default: int) -> int:
    try:
        s = input(prompt).strip()
        if s == '':
            return default
        return int(s)
    except (ValueError, EOFError):
        print("Ungültige Zahl, wird ignoriert.")
        return default

def read_str(prompt: str, default: str, allowed: List[str]) -> str:
    try:
        s = input(prompt).strip().lower()
        if s == '':
            return default
        if s in allowed:
            return s
        print(f"Ungültige Eingabe, erlaubt: {', '.join(allowed)}. Standard wird verwendet.")
        return default
    except EOFError:
        return default

# ---------- Hauptprogramm ----------

def main() -> None:
    print("=== Schatten-Simulator ===")
    print("Teil 49 von ~50: Shading finalisieren & README vorbereiten")
    print("Drücke Enter für Standardwerte. Strg+C oder EOF zum Beenden.\n")

    # Standardwerte
    breite = 80
    hoehe = 40
    z_skalierung = 6.0
    ambient = 0.15
    glanz_staerke = 0.4
    glanz_haerte = 16.0
    seed = 42
    licht_modus = 'einzeln'

    eingaben = 0
    max_eingaben = 20

    try:
        while eingaben < max_eingaben:
            print(f"--- Frame {eingaben+1} ---")
            z_skalierung = read_float(f"Z-Tiefe (Enter={z_skalierung}): ", z_skalierung)
            eingaben += 1
            if eingaben >= max_eingaben: break
            ambient = read_float(f"Ambient (Enter={ambient}): ", ambient)
            eingaben += 1
            if eingaben >= max_eingaben: break
            glanz_staerke = read_float(f"Glanz-Stärke (Enter={glanz_staerke}): ", glanz_staerke)
            eingaben += 1
            if eingaben >= max_eingaben: break
            glanz_haerte = read_float(f"Glanz-Härte (Enter={glanz_haerte}): ", glanz_haerte)
            eingaben += 1
            if eingaben >= max_eingaben: break
            seed = read_int(f"Seed (Enter={seed}): ", seed)
            eingaben += 1
            if eingaben >= max_eingaben: break
            licht_modus = read_str(f"Licht-Modus [einzeln/doppelt] (Enter={licht_modus}): ", licht_modus, ['einzeln', 'doppelt'])
            eingaben += 1

            # Prozedurale Tiefenkarte erzeugen
            noise = ValueNoise(seed)
            daten = [[noise.fractal(x, y) for x in range(breite)] for y in range(hoehe)]
            tk = Tiefenkarte(daten)
            normals = tk.normalen(z_skalierung)

            # Lichtquellen definieren
            lichtquellen: List[Lichtquelle] = []
            if licht_modus == 'einzeln':
                lichtquellen.append(Lichtquelle('gerichtet', (0.5, -0.5, -1.0), 1.0))
            else:
                lichtquellen.append(Lichtquelle('gerichtet', (0.5, -0.5, -1.0), 0.7))
                lichtquellen.append(Lichtquelle('punkt', (breite/2, hoehe/2, 50.0), 0.5, 0.001))

            # Rendern
            ascii_zeilen = render_ascii(tk, normals, z_skalierung, ambient, glanz_staerke, glanz_haerte, lichtquellen)
            print("\n".join(ascii_zeilen))
            print()

    except KeyboardInterrupt:
        print("\nAbbruch durch Benutzer.")
    except EOFError:
        print("\nEOF erkannt.")
    finally:
        print("Tschüss! Schatten-Simulator wird beendet.")

if __name__ == "__main__":
    main()