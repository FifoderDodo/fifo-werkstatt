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
    
    schrittweite = max(0.5, min(2.0, max_dist / schritte))
    d = offset
    while d < max_dist:
        curr_x += l_dir[0] * schrittweite
        curr_y += l_dir[1] * schrittweite
        curr_z += l_dir[2] * schrittweite
        d += schrittweite
        
        if not (0 <= curr_x < tk.b and 0 <= curr_y < tk.h):
            break
            
        karten_h_roh = tk.get_bilinear(curr_y, curr_x)
        karten_h_welt = karten_h_roh * z_skalierung
        if curr_z < karten_h_welt:
            return 0.1  # Im Kernschatten
    return 1.0  # Volles Licht

def berechne_tiefen_schattierung(
    tk: Tiefenkarte,
    lichter: List[Lichtquelle],
    z_tiefe: float = 6.0,
    ambient: float = 0.15,
    glanz_staerke: float = 0.4,
    glanz_haerte: float = 16.0
) -> List[List[float]]:
    """Berechnet vollständige 3D-Lichtvektoren, Glanzpunkte und Raymarch-Schatten."""
    normalen_feld = tk.normalen(z_faktor=z_tiefe * 0.4)
    ausgabe: List[List[float]] = []
    sicht_vektor: Vec3 = (0.0, 0.0, 1.0)  # Beobachter schaut frontal auf die Szene

    for y in range(tk.h):
        reihe: List[float] = []
        for x in range(tk.b):
            z_val = tk.get(y, x) * z_tiefe
            p: Vec3 = (float(x), float(y), z_val)
            n = normalen_feld[y][x]
            
            # Ambient mit leichter Höhenmodulation
            gesamt_helligkeit = ambient * (0.8 + 0.2 * tk.get(y, x))
            
            for licht in lichter:
                l_dir, dist = licht.vektor_und_distanz(p)
                energie = licht.energie_an(dist)
                
                # Diffuse Komponente (Lambert)
                n_dot_l = max(0.0, vec3_dot(n, l_dir))
                if n_dot_l > 0:
                    # Raymarch-Schatten
                    schatten = raymarch_schatten(tk, p, l_dir, dist, z_tiefe)
                    gesamt_helligkeit += n_dot_l * energie * schatten
                    
                    # Spekulare Komponente (Blinn-Phong)
                    h = vec3_norm(vec3_add(l_dir, sicht_vektor))
                    n_dot_h = max(0.0, vec3_dot(n, h))
                    if n_dot_h > 0:
                        glanz = (n_dot_h ** glanz_haerte) * glanz_staerke * energie * schatten
                        gesamt_helligkeit += glanz
            
            reihe.append(min(1.0, max(0.0, gesamt_helligkeit)))
        ausgabe.append(reihe)
    return ausgabe

# ---------- ASCII Rendering ----------

ASCII_RAMPE = " .'`^\"\,;:Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8@$B"

def rendere_ascii(helligkeiten: List[List[float]], rampe: str = ASCII_RAMPE) -> str:
    """Wandelt Helligkeitswerte (0..1) in ASCII-Zeichen um."""
    zeilen = []
    max_idx = len(rampe) - 1
    for reihe in helligkeiten:
        zeile = ''.join(rampe[int(w * max_idx)] for w in reihe)
        zeilen.append(zeile)
    return '\n'.join(zeilen)

# ---------- Prozedurale Tiefenkarte ----------

def erzeuge_tiefenkarte(breite: int, hoehe: int, seed: int, z_tiefe: float = 1.0) -> Tiefenkarte:
    """Erzeugt eine prozedurale Tiefenkarte mit Value Noise (5 Oktaven)."""
    noise = ValueNoise(seed)
    daten = []
    for y in range(hoehe):
        reihe = []
        for x in range(breite):
            # Noise im Bereich 0..1
            w = noise.fractal(x, y, okta=5, persistenz=0.5, laengenskalierung=0.05)
            w = (w + 1.0) * 0.5  # -1..1 -> 0..1
            # Leichte Kantenabschwächung (Vignette) damit Ränder nicht hart aufschneiden
            rx = x / max(1, breite - 1)
            ry = y / max(1, hoehe - 1)
            rand_faktor = (1.0 - (rx - 0.5) ** 2 * 0.5) * (1.0 - (ry - 0.5) ** 2 * 0.5)
            w *= rand_faktor
            reihe.append(w)
        daten.append(reihe)
    return Tiefenkarte(daten)

# ---------- Licht-Setups ----------

def erstelle_licht_setup(modus: str, breite: int, hoehe: int) -> List[Lichtquelle]:
    """Gibt vorgefertigte Lichtkonfigurationen zurück."""
    cx, cy = breite * 0.5, hoehe * 0.5
    if modus == 'einzeln':
        return [Lichtquelle('gerichtet', vec3_norm((-0.3, -0.5, 1.0)), 1.2)]
    elif modus == 'doppelt':
        return [
            Lichtquelle('gerichtet', vec3_norm((-0.4, -0.3, 1.0)), 0.8),
            Lichtquelle('punkt', (cx + 10, cy - 5, 30.0), 1.0, 0.0015)
        ]
    elif modus == 'drei':
        return [
            Lichtquelle('gerichtet', vec3_norm((-0.2, -0.4, 1.0)), 0.6),
            Lichtquelle('punkt', (cx - 15, cy + 10, 25.0), 0.7, 0.002),
            Lichtquelle('punkt', (cx + 20, cy - 8, 35.0), 0.5, 0.0015)
        ]
    else:  # gemischt
        return [
            Lichtquelle('gerichtet', vec3_norm((-0.3, -0.2, 1.0)), 0.7),
            Lichtquelle('punkt', (cx, cy, 40.0), 0.9, 0.001)
        ]

# ---------- Hauptprogramm ----------

def lies_eingabe(prompt: str, standard: str) -> str:
    """Liest Eingabe mit Standardwert, fängt EOF/KeyboardInterrupt ab."""
    try:
        val = input(prompt).strip()
        return val if val else standard
    except (EOFError, KeyboardInterrupt):
        print('\nTschüss!')
        sys.exit(0)

def parse_float(val: str, standard: float) -> float:
    try:
        return float(val)
    except ValueError:
        print(f'  Ungültige Zahl, wird ignoriert.')
        return standard

def parse_int(val: str, standard: int) -> int:
    try:
        return int(val)
    except ValueError:
        print(f'  Ungültige Zahl, wird ignoriert.')
        return standard

def main() -> None:
    print('=== Schatten-Simulator ===')
    print('Prozedurale 3D-Tiefe + Raymarch-Schatten + ASCII-Output')
    print('(nur Python-Standardbibliothek, keine externen Abhängigkeiten)\n')
    
    # Startwerte
    breite = 80
    hoehe = 40
    z_tiefe = 6.0
    ambient = 0.15
    glanz_staerke = 0.4
    glanz_haerte = 16.0
    seed = 42
    licht_modus = 'gemischt'
    
    eingabe_count = 0
    max_eingaben = 20
    
    while eingabe_count < max_eingaben:
        # Tiefenkarte erzeugen
        tk = erzeuge_tiefenkarte(breite, hoehe, seed, z_tiefe)
        mn, mx, span = tk.statistik()
        
        # Lichter
        lichter = erstelle_licht_setup(licht_modus, breite, hoehe)
        
        # Shading berechnen
        helligkeiten = berechne_tiefen_schattierung(
            tk, lichter, z_tiefe, ambient, glanz_staerke, glanz_haerte
        )
        
        # ASCII rendern
        ascii_kunst = rendere_ascii(helligkeiten)
        print(f'\n--- Frame {eingabe_count + 1} ---')
        print(f'Aktuell: breite={breite} hoehe={hoehe} z_tiefe={z_tiefe} ambient={ambient} glanz={glanz_staerke}/{glanz_haerte} seed={seed} licht={licht_modus}')
        print(f'Tiefenstatistik: min={mn:.3f} max={mx:.3f} span={span:.3f}')
        print(ascii_kunst)
        
        if eingabe_count >= max_eingaben - 1:
            print('\nMaximale Anzahl Eingaben erreicht.')
            break
        
        print('\n--- Parameter anpassen (Enter = unverändert) ---')
        val = lies_eingabe(f'Breite (Enter={breite}): ', str(breite))
        breite = parse_int(val, breite)
        val = lies_eingabe(f'Höhe (Enter={hoehe}): ', str(hoehe))
        hoehe = parse_int(val, hoehe)
        val = lies_eingabe(f'Z-Tiefe (Enter={z_tiefe}): ', str(z_tiefe))
        z_tiefe = parse_float(val, z_tiefe)
        val = lies_eingabe(f'Ambient (Enter={ambient}): ', str(ambient))
        ambient = parse_float(val, ambient)
        val = lies_eingabe(f'Glanz-Stärke (Enter={glanz_staerke}): ', str(glanz_staerke))
        glanz_staerke = parse_float(val, glanz_staerke)
        val = lies_eingabe(f'Glanz-Härte (Enter={glanz_haerte}): ', str(glanz_haerte))
        glanz_haerte = parse_float(val, glanz_haerte)
        val = lies_eingabe(f'Seed (Enter={seed}): ', str(seed))
        seed = parse_int(val, seed)
        val = lies_eingabe(f'Licht-Modus [einzeln/doppelt/drei/gemischt] (Enter={licht_modus}): ', licht_modus)
        if val in ('einzeln', 'doppelt', 'drei', 'gemischt'):
            licht_modus = val
        else:
            print(f'  Unbekannter Modus, behalte {licht_modus}.')
        
        eingabe_count += 1
    
    print('\nFertig. Danke fürs Testen!')

if __name__ == '__main__':
    main()