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
        # Weltkoordinaten -> Tiefenkarten-Indizes
        map_x = curr_x
        map_y = curr_y
        
        if 0 <= map_x < tk.b - 1 and 0 <= map_y < tk.h - 1:
            hoehe = tk.get_bilinear(map_y, map_x) * z_skalierung
            if curr_z <= hoehe + 0.05 * z_skalierung:
                return 0.0  # im Schatten
        
        curr_x += l_dir[0] * schrittweite
        curr_y += l_dir[1] * schrittweite
        curr_z += l_dir[2] * schrittweite
    
    return 1.0  # beleuchtet


def phong_schatten(tk: Tiefenkarte, normalen: List[List[Vec3]], y: int, x: int,
                   lichter: List[Lichtquelle], v_aug: Vec3, z_skalierung: float,
                   k_a: float = 0.15, k_d: float = 0.7, k_s: float = 0.3, glanz: float = 32.0) -> float:
    """Berechnet Phong-Beleuchtung mit Weichschatten für einen Pixel."""
    n = normalen[y][x]
    p_welt = (float(x), float(y), tk.daten[y][x] * z_skalierung)
    
    gesamt = k_a  # Ambient-Anteil
    
    for licht in lichter:
        l_dir, dist = licht.vektor_und_distanz(p_welt)
        energie = licht.energie_an(dist)
        
        # Schattenfaktor (0.0 = voller Schatten, 1.0 = voll beleuchtet)
        schatten = raymarch_schatten(tk, p_welt, l_dir, dist if licht.typ == 'punkt' else 50.0, z_skalierung)
        
        if schatten > 0.01:
            # Diffus
            ndotl = max(0.0, vec3_dot(n, l_dir))
            diffus = k_d * ndotl
            
            # Spekular (Blinn-Phong)
            h = vec3_norm(vec3_add(l_dir, v_aug))
            ndoth = max(0.0, vec3_dot(n, h))
            spekular = k_s * (ndoth ** glanz)
            
            gesamt += (diffus + spekular) * energie * schatten
    
    return min(1.0, max(0.0, gesamt))

# ---------- ANSI-Rendering ----------

ASCII_RAMP = " .'`^\\\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8@%$"

def helligkeit_zu_ascii(wert: float) -> str:
    idx = int(wert * (len(ASCII_RAMP) - 1))
    return ASCII_RAMP[max(0, min(len(ASCII_RAMP) - 1, idx))]

def farbe_256(r: float, g: float, b: float) -> int:
    """Konvertiert RGB (0-1) zu nächstem 256-Farbraum-Index (16-231)."""
    ri = int(r * 5)
    gi = int(g * 5)
    bi = int(b * 5)
    return 16 + 36 * ri + 6 * gi + bi

def render_ansi(tk: Tiefenkarte, normalen: List[List[Vec3]], lichter: List[Lichtquelle],
                z_skalierung: float, v_aug: Vec3, breite: int = 80) -> List[str]:
    """Rendert die Tiefenkarte als ANSI-farbiges ASCII-Bild."""
    h, b = tk.h, tk.b
    if b == 0 or h == 0:
        return []
    
    skala = breite / b
    out_h = max(1, int(h * skala * 0.5))  # 0.5 für Zeichen-Seitenverhältnis
    
    zeilen: List[str] = []
    for yy in range(out_h):
        src_y = yy / skala / 0.5
        zeile_chars: List[str] = []
        for xx in range(breite):
            src_x = xx / skala
            
            # Bilineare Interpolation für Normalen und Höhe
            y0 = int(math.floor(src_y))
            x0 = int(math.floor(src_x))
            y1 = min(h - 1, y0 + 1)
            x1 = min(b - 1, x0 + 1)
            dy = src_y - y0
            dx = src_x - x0
            
            if 0 <= y0 < h and 0 <= x0 < b:
                # Normalen interpolieren
                n00 = normalen[y0][x0]
                n01 = normalen[y0][x1]
                n10 = normalen[y1][x0]
                n11 = normalen[y1][x1]
                
                nx = (n00[0] * (1-dx) + n01[0] * dx) * (1-dy) + (n10[0] * (1-dx) + n11[0] * dx) * dy
                ny = (n00[1] * (1-dx) + n01[1] * dx) * (1-dy) + (n10[1] * (1-dx) + n11[1] * dx) * dy
                nz = (n00[2] * (1-dx) + n01[2] * dx) * (1-dy) + (n10[2] * (1-dx) + n11[2] * dx) * dy
                n_interp = vec3_norm((nx, ny, nz))
                
                # Höhe interpolieren für Welt-Position
                h00 = tk.daten[y0][x0]
                h01 = tk.daten[y0][x1]
                h10 = tk.daten[y1][x0]
                h11 = tk.daten[y1][x1]
                h_interp = (h00 * (1-dx) + h01 * dx) * (1-dy) + (h10 * (1-dx) + h11 * dx) * dy
                
                p_welt = (src_x, src_y, h_interp * z_skalierung)
                
                # Beleuchtung berechnen
                helligkeit = 0.15  # Ambient
                for licht in lichter:
                    l_dir, dist = licht.vektor_und_distanz(p_welt)
                    energie = licht.energie_an(dist)
                    schatten = raymarch_schatten(tk, p_welt, l_dir,
                                                dist if licht.typ == 'punkt' else 50.0, z_skalierung)
                    if schatten > 0.01:
                        ndotl = max(0.0, vec3_dot(n_interp, l_dir))
                        h_vec = vec3_norm(vec3_add(l_dir, v_aug))
                        ndoth = max(0.0, vec3_dot(n_interp, h_vec))
                        helligkeit += (0.7 * ndotl + 0.3 * (ndoth ** 32.0)) * energie * schatten
                
                helligkeit = min(1.0, max(0.0, helligkeit))
                
                # Farbe basierend auf Höhe und Beleuchtung
                hoehe_norm = (h_interp - tk.statistik()[0]) / max(0.001, tk.statistik()[2])
                r = 0.2 + 0.6 * hoehe_norm * helligkeit
                g = 0.3 + 0.5 * (1.0 - hoehe_norm) * helligkeit
                b_col = 0.5 + 0.3 * helligkeit
                
                farb_idx = farbe_256(r, g, b_col)
                ascii_char = helligkeit_zu_ascii(helligkeit)
                zeile_chars.append(f"\033[38;5;{farb_idx}m{ascii_char}")
            else:
                zeile_chars.append(" ")
        zeilen.append(" ".join(zeile_chars) + "\033[0m")
    return zeilen

# ---------- Beispieldaten & Hauptprogramm ----------

def generiere_landkarte(breite: int = 60, hoehe: int = 40, seed: int = 42) -> Tiefenkarte:
    """Erzeugt eine prozedurale Höhenkarte mit Value Noise."""
    noise = ValueNoise(seed)
    daten: List[List[float]] = []
    for y in range(hoehe):
        reihe: List[float] = []
        for x in range(breite):
            # Mehrere Noise-Layer für interessante Landschaft
            basis = noise.fractal(x, y, okta=4, persistenz=0.5, laengenskalierung=0.08)
            detail = noise.fractal(x, y, okta=3, persistenz=0.4, laengenskalierung=0.15) * 0.3
            fluss = noise.fractal(x * 0.5, y * 0.5, okta=2, persistenz=0.6, laengenskalierung=0.03) * 0.2
            # Leichte Kuppenformung
            mitten_x, mitten_y = breite * 0.5, hoehe * 0.5
            dist_mitte = math.sqrt((x - mitten_x)**2 + (y - mitten_y)**2) / max(breite, hoehe)
            kuppen = (1.0 - dist_mitte) * 0.4
            
            hoehe = basis + detail + fluss + kuppen
            reihe.append(max(0.0, min(1.0, hoehe)))
        daten.append(reihe)
    return Tiefenkarte(daten)

def eingabe_mit_default(prompt: str, default: str, typ: type = str) -> any:
    """Robuste Eingabe mit Default-Wert und Typ-Konvertierung."""
    try:
        val = input(f"{prompt} [{default}]: ").strip()
        if not val:
            return typ(default)
        return typ(val)
    except (ValueError, EOFError):
        return typ(default)

def main() -> None:
    print("\n=== Schatten-Simulator v52 ===")
    print("Prozedurale 3D-Tiefenberechnung mit Weichschatten & ANSI-Rendering")
    print("Teil 52/55: Feinabstimmung Tiefenberechnung & Helligkeitstest\n")
    
    # Parameter abfragen
    breite = eingabe_mit_default("Kartenbreite", "60", int)
    hoehe = eingabe_mit_default("Kartenhöhe", "40", int)
    seed = eingabe_mit_default("Noise-Seed", "42", int)
    z_skalierung = eingabe_mit_default("Z-Skalierung (Tiefe)", "2.5", float)
    render_breite = eingabe_mit_default("Render-Breite (Zeichen)", "80", int)
    
    print("\nGeneriere Höhenkarte...")
    tk = generiere_landkarte(breite, hoehe, seed)
    mn, mx, span = tk.statistik()
    print(f"Höhenbereich: {mn:.3f} - {mx:.3f} (Spanne: {span:.3f})")
    
    print("Berechne Normalen...")
    normalen = tk.normalen(z_skalierung)
    
    # Licht-Setup
    print("\nLichtquellen konfigurieren:")
    print("1: Gerichtetes Licht (Sonne)")
    print("2: Punktlicht (Lampe)")
    print("3: Beide kombiniert")
    licht_wahl = eingabe_mit_default("Wahl", "3", int)
    
    lichter: List[Lichtquelle] = []
    if licht_wahl in (1, 3):
        # Sonnenlicht von oben-links-hinten
        lichter.append(Lichtquelle('gerichtet', vec3_norm((-0.5, -0.3, -1.0)), intensitaet=1.2))
    if licht_wahl in (2, 3):
        # Punktlicht in der Mitte, etwas erhöht
        lichter.append(Lichtquelle('punkt', (breite * 0.5, hoehe * 0.5, 15.0), intensitaet=3.0, abfall=0.008))
    
    # View-Vektor (Kamera schaut von oben nach unten, leicht geneigt)
    v_aug = vec3_norm((0.1, 0.2, -1.0))
    
    print("\nRendere ASCII-Bild mit Schatten...")
    bild = render_ansi(tk, normalen, lichter, z_skalierung, v_aug, render_breite)
    
    print("\n" + "=" * render_breite)
    for zeile in bild:
        print(zeile)
    print("=" * render_breite)
    
    # Helligkeitsstatistik
    print("\n--- Helligkeitstest ---")
    test_punkte = [(hoehe//2, breite//2), (hoehe//4, breite//4), (3*hoehe//4, 3*breite//4)]
    for ty, tx in test_punkte:
        if 0 <= ty < hoehe and 0 <= tx < breite:
            n = normalen[ty][tx]
            p = (float(tx), float(ty), tk.daten[ty][tx] * z_skalierung)
            hell = phong_schatten(tk, normalen, ty, tx, lichter, v_aug, z_skalierung)
            print(f"  Pixel ({tx},{ty}) Höhe={tk.daten[ty][tx]:.3f} Normalen=({n[0]:.2f},{n[1]:.2f},{n[2]:.2f}) -> Helligkeit={hell:.3f}")
    
    print("\nFertig! Drücke Enter zum Beenden...")
    try:
        input()
    except EOFError:
        pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
    except Exception as e:
        print(f"\nFehler: {e}")
        import traceback
        traceback.print_exc()