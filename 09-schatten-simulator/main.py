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
                
                # Diffuse Komponente (Lambert)
                ndotl = max(0.0, vec3_dot(n, l_dir))
                
                # Schatten per Raymarching
                schatten = raymarch_schatten(tk, p, l_dir, dist, z_tiefe)
                
                # Spekular (Blinn-Phong)
                halb = vec3_norm(vec3_add(l_dir, sicht_vektor))
                ndoth = max(0.0, vec3_dot(n, halb))
                spekular = (ndoth ** glanz_haerte) * glanz_staerke
                
                gesamt_helligkeit += energie * schatten * (ndotl + spekular)
            
            reihe.append(min(1.0, max(0.0, gesamt_helligkeit)))
        ausgabe.append(reihe)
    return ausgabe

# ---------- ASCII-Rendering ----------
ASCII_RAMP = ' .\`^,:;Il!i><~+_-?][}{1)(|\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8@B@$'

def helligkeit_zu_ascii(wert: float, gamma: float = 1.0) -> str:
    if wert <= 0.0:
        return ASCII_RAMP[0]
    if wert >= 1.0:
        return ASCII_RAMP[-1]
    korrigiert = wert ** (1.0 / gamma)
    idx = int(korrigiert * (len(ASCII_RAMP) - 1))
    return ASCII_RAMP[idx]

def rendere_ascii(helligkeiten: List[List[float]], gamma: float = 1.0) -> str:
    zeilen = []
    for reihe in helligkeiten:
        zeilen.append(''.join(helligkeit_zu_ascii(w, gamma) for w in reihe))
    return '\n'.join(zeilen)

# ---------- Prozedurale Tiefenerzeugung ----------
def erzeuge_tiefenkarte(breite: int, hoehe: int, seed: Optional[int] = None) -> Tiefenkarte:
    if seed is not None:
        random.seed(seed)
    daten = [[0.0 for _ in range(breite)] for _ in range(hoehe)]
    # Mehrere Hügel addieren
    anzahl_huegel = random.randint(3, 6)
    for _ in range(anzahl_huegel):
        cx = random.uniform(0, breite)
        cy = random.uniform(0, hoehe)
        radius = random.uniform(min(breite, hoehe) * 0.15, min(breite, hoehe) * 0.35)
        hoehe_h = random.uniform(0.4, 1.0)
        for y in range(hoehe):
            dy = y - cy
            for x in range(breite):
                dx = x - cx
                dist = math.sqrt(dx*dx + dy*dy)
                if dist < radius:
                    # Weiche Kante per cosinus
                    faktor = 0.5 * (1.0 + math.cos(math.pi * dist / radius))
                    daten[y][x] += hoehe_h * faktor
    # Normalisieren auf 0..1
    flach = [w for reihe in daten for w in reihe]
    mx = max(flach) if flach else 1.0
    if mx > 0:
        for y in range(hoehe):
            for x in range(breite):
                daten[y][x] /= mx
    # Etwas Rauschen für Details
    for y in range(hoehe):
        for x in range(breite):
            daten[y][x] = min(1.0, daten[y][x] + random.uniform(-0.02, 0.02))
    return Tiefenkarte(daten)

# ---------- Hauptprogramm ----------
def main() -> None:
    print("☀️  Schatten-Simulator – Teil 46")
    print("==============================++")
    
    # Standardparameter
    breite, hoehe = 80, 40
    z_tiefe = 6.0
    gamma = 1.2
    ambient = 0.15
    glanz_staerke = 0.4
    glanz_haerte = 16.0
    seed = random.randint(0, 10000)
    
    # Lichtsetup: eine gerichtete Sonne + ein paar Punktlichter
    def erstelle_lichter() -> List[Lichtquelle]:
        return [
            Lichtquelle('gerichtet', vec3_norm((0.5, -0.3, -1.0)), intensitaet=1.2),
            Lichtquelle('punkt', (breite*0.2, hoehe*0.2, z_tiefe*2.0), intensitaet=0.8, abfall=0.001),
            Lichtquelle('punkt', (breite*0.8, hoehe*0.8, z_tiefe*1.5), intensitaet=0.6, abfall=0.0015),
        ]
    
    eingabe_zaehler = 0
    max_eingaben = 20
    
    while eingabe_zaehler < max_eingaben:
        try:
            tk = erzeuge_tiefenkarte(breite, hoehe, seed)
            lichter = erstelle_lichter()
            helligkeiten = berechne_tiefen_schattierung(
                tk, lichter,
                z_tiefe=z_tiefe,
                ambient=ambient,
                glanz_staerke=glanz_staerke,
                glanz_haerte=glanz_haerte
            )
            bild = rendere_ascii(helligkeiten, gamma)
            print(bild)
            print(f"\nSeed: {seed} | Tiefe: {z_tiefe:.1f} | Gamma: {gamma:.2f} | Ambient: {ambient:.2f}")
            print("Befehle: [n]euer Seed, [t]iefe, [g]amma, [a]mbient, [s]pektrum, [q]uit")
            cmd = input("> ").strip().lower()
            eingabe_zaehler += 1
            
            if cmd == 'q':
                break
            elif cmd == 'n':
                seed = random.randint(0, 10000)
            elif cmd == 't':
                val = input("  Neue Z-Tiefe (1-20): ").strip()
                try:
                    z_tiefe = max(1.0, min(20.0, float(val)))
                except ValueError:
                    pass
            elif cmd == 'g':
                val = input("  Neues Gamma (0.5-3.0): ").strip()
                try:
                    gamma = max(0.5, min(3.0, float(val)))
                except ValueError:
                    pass
            elif cmd == 'a':
                val = input("  Neuer Ambient (0.0-0.5): ").strip()
                try:
                    ambient = max(0.0, min(0.5, float(val)))
                except ValueError:
                    pass
            elif cmd == 's':
                val = input("  Glanzstärke (0.0-1.0): ").strip()
                try:
                    glanz_staerke = max(0.0, min(1.0, float(val)))
                except ValueError:
                    pass
                val = input("  Glan'härte (1-64): ").strip()
                try:
                    glanz_haerte = max(1.0, min(64.0, float(val)))
                except ValueError:
                    pass
            else:
                print("Unbekanntes Kommando.")
        except EOFError:
            break
        except KeyboardInterrupt:
            break
    print("\n👋  Schatten-Simulator beendet. Bis zum nächsten Render!")

if __name__ == "__main__":
    main()