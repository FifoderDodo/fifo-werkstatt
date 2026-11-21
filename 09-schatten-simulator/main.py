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
        # Sobel-Kernel Gewichte
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
                # Normalenvektor zeigt aus der Bildfläche nach oben-außen
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
    # Leicht anheben gegen Selbsteinkerbung (in Welt-Einheiten)
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
                diffus = max(0.0, vec3_dot(n, l_dir))
                
                if diffus > 0.001:
                    # Raymarch in Weltkoordinaten, Startpunkt auf Oberfläche (Welt-Z)
                    schatten = raymarch_schatten(tk, p, l_dir, min(dist, 40.0), z_tiefe)
                    energie = licht.energie_an(dist) * schatten
                    
                    # Diffuser Anteil (Lambert)
                    gesamt_helligkeit += diffus * energie
                    
                    # Spekularer Anteil (Blinn-Phong)
                    h_vec = vec3_norm(vec3_add(l_dir, sicht_vektor))
                    spek = max(0.0, vec3_dot(n, h_vec))
                    spek = spek ** glanz_haerte
                    gesamt_helligkeit += spek * glanz_staerke * energie
            
            reihe.append(min(1.0, gesamt_helligkeit))
        ausgabe.append(reihe)
    return ausgabe

# ---------- Szenenbau & Ausgabe ----------

def szene_bauen(breite: int = 80, hoehe: int = 40) -> Tiefenkarte:
    """Erzeugt eine prozedurale Testszene mit Hügeln, Kugel und Rillen."""
    daten = [[0.0 for _ in range(breite)] for _ in range(hoehe)]
    cx, cy = breite * 0.5, hoehe * 0.5
    for y in range(hoehe):
        for x in range(breite):
            dx = (x - cx) / breite
            dy = (y - cy) / hoehe
            # Großer Hügel
            dist = math.sqrt(dx*dx + dy*dy)
            h = 0.6 * (1.0 - min(1.0, dist * 2.5))
            # Kleine Kugel links oben
            kx, ky = (x - breite*0.25) / breite, (y - hoehe*0.25) / hoehe
            kdist = math.sqrt(kx*kx + ky*ky)
            h += 0.4 * max(0.0, 1.0 - kdist * 8.0)
            # Rillen (Sinusrillen)
            h += 0.08 * math.sin(x * 0.4) * math.cos(y * 0.3)
            # Rauschen
            h += 0.02 * (random.random() - 0.5)
            daten[y][x] = max(0.0, min(1.0, h))
    return Tiefenkarte(daten)

def licht_waehlen(tk: Tiefenkarte) -> List[Lichtquelle]:
    """Plaziert ein Hauptlicht und zwei Fülllichter."""
    lichter = [
        Lichtquelle('gerichtet', vec3_norm((0.5, -0.3, 1.0)), 1.2),
        Lichtquelle('punkt', (tk.b * 0.8, tk.h * 0.2, 15.0), 0.6, 0.001),
        Lichtquelle('punkt', (tk.b * 0.1, tk.h * 0.8, 10.0), 0.4, 0.002),
    ]
    return lichter

ASCII_RAMPE = " .'`^\",;:Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$€"[:70]  # 70 Stufen
def als_ascii_ausgeben(helligkeiten: List[List[float]], gamma: float = 1.8) -> None:
    """Wandelt Helligkeitsmatrix in ASCII-Art mit Gamma-Korrektur um."""
    rampe_len = len(ASCII_RAMPE) - 1
    for reihe in helligkeiten:
        zeile = ''
        for h in reihe:
            h = max(0.0, min(1.0, h))
            h = h ** (1.0 / gamma)
            idx = int(h * rampe_len + 0.5)
            zeile += ASCII_RAMPE[idx]
        print(zeile)

def main() -> None:
    print("☠ Schatten-Simulator v45 — Tiefenglättung & Koordinatenfix ☠")
    print("Erzeuge Szenerie (80x40)...")
    tk = szene_bauen(80, 40)
    mn, mx, sp = tk.statistik()
    print(f"Tiefe: min={mn:.3f} max={mx:.3f} span={sp:.3f}")
    
    print("Platziere Lichter...")
    lichter = licht_waehlen(tk)
    
    print("Berechne 3D-Schattierung (Raymarch + Blinn-Phong)...")
    hell = berechne_tiefen_schattierung(tk, lichter, z_tiefe=6.0)
    
    print("\n--- Render-Ausgabe ---")
    als_ascii_ausgeben(hell, gamma=1.8)
    print("--- Ende ---")
    
    # Interaktiver Loop (optional, für Browser-Tests)
    while True:
        try:
            cmd = input("\n[enter=neu, q=quit, z=neue tiefe, g=neues gamma]: ").strip().lower()
            if cmd == 'q' or cmd == 'quit':
                break
            elif cmd == 'z':
                try:
                    z = float(input("Z-Tiefe (1-20): "))
                    hell = berechne_tiefen_schattierung(tk, lichter, z_tiefe=z)
                    als_ascii_ausgeben(hell, gamma=1.8)
                except (ValueError, EOFError):
                    pass
            elif cmd == 'g':
                try:
                    g = float(input("Gamma (0.5-3.0): "))
                    als_ascii_ausgeben(hell, gamma=g)
                except (ValueError, EOFError):
                    pass
            else:
                # Neuer Seed, neue Szenerie
                random.seed()
                tk = szene_bauen(80, 40)
                lichter = licht_waehlen(tk)
                hell = berechne_tiefen_schattierung(tk, lichter, z_tiefe=6.0)
                als_ascii_ausgeben(hell, gamma=1.8)
        except EOFError:
            print("\nTschüss! 👋")
            break
        except KeyboardInterrupt:
            print("\nAbgebrochen.")
            break

if __name__ == "__main__":
    main()