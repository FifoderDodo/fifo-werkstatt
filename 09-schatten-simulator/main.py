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
    # v: einfallender Vektor (von Licht zur Oberfläche), n: Normalenvektor
    # R = v - 2*(v·n)*n
    dot = vec3_dot(v, n)
    return vec3_sub(v, vec3_scale(n, 2.0 * dot))

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
                # Sobel X (horizontal)
                gx = (
                    -self.get(y-1, x-1) + self.get(y-1, x+1)
                    -2.0 * self.get(y, x-1)   + 2.0 * self.get(y, x+1)
                    -self.get(y+1, x-1) + self.get(y+1, x+1)
                ) * 0.125 * z_faktor
                # Sobel Y (vertikal)
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
            gesamt_helligkeit = ambient * (0.3 + 0.7 * tk.get(y, x))
            
            for licht in lichter:
                l_dir, dist = licht.vektor_und_distanz(p)
                energie = licht.energie_an(dist)
                
                # Diffuse (Lambert)
                ndotl = max(0.0, vec3_dot(n, l_dir))
                diffus = ndotl * energie
                
                # Spekular (Blinn-Phong Approximation via Reflection)
                # Reflektiere Lichtvektor an Normalen, dann dot mit Sichtvektor
                r = vec3_reflect(vec3_scale(l_dir, -1.0), n)  # Licht kommt von Lichtquelle, also -l_dir
                rdv = max(0.0, vec3_dot(r, sicht_vektor))
                spekular = (rdv ** glanz_haerte) * glanz_staerke * energie
                
                # Schatten per Raymarching
                max_dist = dist if licht.typ == 'punkt' else 1e4
                schatten = raymarch_schatten(tk, p, l_dir, max_dist, z_tiefe)
                
                gesamt_helligkeit += (diffus + spekular) * schatten
            
            # Clampen auf [0, 1] aber Highlights dürfen leicht darüber
            if gesamt_helligkeit > 1.0:
                gesamt_helligkeit = 1.0 + (gesamt_helligkeit - 1.0) * 0.5
            reihe.append(max(0.0, gesamt_helligkeit))
        ausgabe.append(reihe)
    return ausgabe

# ---------- ASCII Rendering ----------

def helligkeit_zu_ascii(wert: float) -> str:
    """Mappt Helligkeit 0..1+ auf ASCII-Rampen."""
    rampen = " .'`^\"\,;:Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
    idx = int(min(max(wert, 0.0), 1.0) * (len(rampen) - 1))
    return rampen[idx]

def rendere_ascii(schattierung: List[List[float]]) -> str:
    zeilen = []
    for reihe in schattierung:
        zeilen.append(''.join(helligkeit_zu_ascii(w) for w in reihe))
    return '\n'.join(zeilen)

# ---------- Prozedurale Tiefenkarte ----------

def generiere_tiefenkarte(breite: int, hoehe: int, seed: int = 42) -> Tiefenkarte:
    """Erzeugt eine prozedurale Tiefenkarte mit mehreren Oktaven (Value Noise)."""
    random.seed(seed)
    # Basis-Rauschen
    basis = [[random.random() for _ in range(breite)] for __ in range(hoehe)]
    
    def glatte_interpolation(a: float, b: float, t: float) -> float:
        ft = t * t * (3.0 - 2.0 * t)
        return a + (b - a) * ft
    
    def sample_octave(oct_daten: List[List[float]], x: float, y: float) -> float:
        h = len(oct_daten)
        b = len(oct_daten[0]) if h > 0 else 0
        if h == 0 or b == 0:
            return 0.0
        x0 = int(math.floor(x)) % b
        y0 = int(math.floor(y)) % h
        x1 = (x0 + 1) % b
        y1 = (y0 + 1) % h
        tx = x - math.floor(x)
        ty = y - math.floor(y)
        v0 = glatte_interpolation(oct_daten[y0][x0], oct_daten[y0][x1], tx)
        v1 = glatte_interpolation(oct_daten[y1][x0], oct_daten[y1][x1], tx)
        return glatte_interpolation(v0, v1, ty)
    
    # Mehrere Oktaven zusammenfassen
    ergebnis = [[0.0 for _ in range(breite)] for __ in range(hoehe)]
    amplitude = 1.0
    frequenz = 1.0
    max_wert = 0.0
    for _ in range(5):  # 5 Oktaven
        for y in range(hoehe):
            for x in range(breite):
                ergebnis[y][x] += sample_octave(basis, x * frequenz / breite, y * frequenz / hoehe) * amplitude
        max_wert += amplitude
        amplitude *= 0.5
        frequenz *= 2.0
    
    # Normalisieren auf 0..1
    for y in range(hoehe):
        for x in range(breite):
            ergebnis[y][x] /= max_wert
    
    # Leichtes Plateau in der Mitte für interessantere Formen
    for y in range(hoehe):
        for x in range(breite):
            dx = (x - breite/2) / (breite/2)
            dy = (y - hoehe/2) / (hoehe/2)
            dist = math.sqrt(dx*dx + dy*dy)
            ergebnis[y][x] = ergebnis[y][x] * (1.0 - 0.3 * dist)
    
    return Tiefenkarte(ergebnis)

# ---------- Hauptprogramm ----------

def main() -> None:
    print("Schatten-Simulator – Teil 47/50")
    print("Drücke Enter für Standardwerte oder gib Zahlen ein.")
    print("Strg+C / EOF zum Beenden.")
    
    # Standardparameter
    breite, hoehe = 80, 40
    z_tiefe = 6.0
    ambient = 0.15
    glanz_staerke = 0.4
    glanz_haerte = 16.0
    seed = 42
    licht_typ = 'gemischt'  # 'gerichtet', 'punkt', 'gemischt'
    
    eingaben = 0
    max_eingaben = 20
    
    while eingaben < max_eingaben:
        try:
            print(f"\n--- Frame {eingaben+1} ---")
            print(f"Aktuell: breite={breite} hoehe={hoehe} z_tiefe={z_tiefe} ambient={ambient} glanz={glanz_staerke}/{glanz_haerte} seed={seed} licht={licht_typ}")
            
            # Eingaben abfragen (einfach nacheinander)
            inp = input("Breite (Enter=unverändert): ").strip()
            if inp:
                breite = max(10, min(200, int(inp)))
            inp = input("Höhe (Enter=unverändert): ").strip()
            if inp:
                hoehe = max(10, min(100, int(inp)))
            inp = input("Z-Tiefe (Enter=unverändert): ").strip()
            if inp:
                z_tiefe = max(0.5, min(20.0, float(inp)))
            inp = input("Ambient (Enter=unverändert): ").strip()
            if inp:
                ambient = max(0.0, min(1.0, float(inp)))
            inp = input("Glanz-Stärke (Enter=unverändert): ").strip()
            if inp:
                glanz_staerke = max(0.0, min(2.0, float(inp)))
            inp = input("Glanz-Härte (Enter=unverändert): ").strip()
            if inp:
                glanz_haerte = max(1.0, min(128.0, float(inp)))
            inp = input("Seed (Enter=unverändert): ").strip()
            if inp:
                seed = int(inp)
            inp = input("Licht-Typ [gerichtet/punkt/gemischt] (Enter=unverändert): ").strip().lower()
            if inp in ('gerichtet', 'punkt', 'gemischt'):
                licht_typ = inp
            
            # Tiefenkarte erzeugen
            tk = generiere_tiefenkarte(breite, hoehe, seed)
            
            # Lichtquellen definieren
            lichter: List[Lichtquelle] = []
            if licht_typ in ('gerichtet', 'gemischt'):
                lichter.append(Lichtquelle('gerichtet', vec3_norm((-0.5, -0.3, -1.0)), intensitaet=1.0))
            if licht_typ in ('punkt', 'gemischt'):
                lichter.append(Lichtquelle('punkt', (breite*0.5, hoehe*0.3, z_tiefe*2.5), intensitaet=1.5, abfall=0.0015))
            
            # Schattierung berechnen
            schattierung = berechne_tiefen_schattierung(
                tk, lichter,
                z_tiefe=z_tiefe,
                ambient=ambient,
                glanz_staerke=glanz_staerke,
                glanz_haerte=glanz_haerte
            )
            
            # ASCII rendern und ausgeben
            ascii_art = rendere_ascii(schattierung)
            print(ascii_art)
            
            eingaben += 1
            
        except EOFError:
            print("\nEOF – Tschüss!")
            break
        except KeyboardInterrupt:
            print("\nAbbruch – Tschüss!")
            break
        except ValueError:
            print("Ungültige Zahl, wird ignoriert.")
            continue
        except Exception as e:
            print(f"Fehler: {e}")
            continue
    
    print("Maximale Anzahl an Iterationen erreicht oder beendet. Danke fürs Testen!")

if __name__ == "__main__":
    main()