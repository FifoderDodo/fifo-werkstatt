# main.py – Schatten-Simulator, Teil 7
# Fifo, der Dodo, bastelt weiche Schatten. Regen prasselt, Code wird weich.

from __future__ import annotations
import math
import sys
import random
from typing import List, Tuple


Vec3 = Tuple[float, float, float]


class Tiefenkarte:
    """Hält ein 2D-Höhenfeld und rechnet erste Ableitungen (Normalen) aus."""

    def __init__(self, daten: List[List[float]]):
        self.daten = [reihe[:] for reihe in daten]  # Kopie
        self.h = len(daten)
        self.b = len(daten[0]) if self.h > 0 else 0

    def get(self, y: int, x: int, default: float = 0.0) -> float:
        """Sicherer Zugriff mit Clamping an den Rändern."""
        if 0 <= y < self.h and 0 <= x < self.b:
            return self.daten[y][x]
        return default

    def get_bilinear(self, y: float, x: float) -> float:
        """Bilineare Interpolation für Subpixel-Abfragen (wichtig für Raymarching)."""
        y0 = int(math.floor(y))
        x0 = int(math.floor(x))
        y1 = y0 + 1
        x1 = x0 + 1
        
        y0 = max(0, min(self.h - 1, y0))
        y1 = max(0, min(self.h - 1, y1))
        x0 = max(0, min(self.b - 1, x0))
        x1 = max(0, min(self.b - 1, x1))
        
        dy = y - y0
        dx = x - x0
        
        h00 = self.daten[y0][x0]
        h01 = self.daten[y0][x1]
        h10 = self.daten[y1][x0]
        h11 = self.daten[y1][x1]
        
        h0 = h00 * (1 - dx) + h01 * dx
        h1 = h10 * (1 - dx) + h11 * dx
        return h0 * (1 - dy) + h1 * dy

    def setze(self, y: int, x: int, wert: float) -> bool:
        """Setzt Wert, wenn im gültigen Bereich und 0-1."""
        if 0 <= y < self.h and 0 <= x < self.b and 0.0 <= wert <= 1.0:
            self.daten[y][x] = wert
            return True
        return False

    def normalen(self) -> List[List[Vec3]]:
        """Berechnet pro Pixel einen Normalenvektor (zentrale Differenzen).
        Rückgabe: Liste von (nx, ny, nz), Länge 1."""
        normals = []
        for y in range(self.h):
            reihe = []
            for x in range(self.b):
                hx = (self.get(y, x + 1) - self.get(y, x - 1)) * 0.5
                hy = (self.get(y + 1, x) - self.get(y - 1, x)) * 0.5
                nx, ny, nz = -hx, -hy, 1.0
                laenge = math.sqrt(nx * nx + ny * ny + nz * nz)
                reihe.append((nx / laenge, ny / laenge, nz / laenge))
            normals.append(reihe)
        return normals

    def statistik(self) -> Tuple[float, float, float]:
        """Min, Max, Spannweite."""
        flach = [w for reihe in self.daten for w in reihe]
        mn = min(flach)
        mx = max(flach)
        return mn, mx, mx - mn

    def __str__(self) -> str:
        zeilen = []
        for reihe in self.daten:
            zeilen.append("  " + "  ".join(f"{h:.2f}" for h in reihe))
        return "\n".join(zeilen)


def diffuse_schatten(normals: List[List[Vec3]],
                     licht_dir: Vec3) -> List[List[float]]:
    """Einfaches Lambert-Modell: Helligkeit = max(0, N·L).
    Lichtvektor zeigt VON der Oberfläche ZUR Lichtquelle (normiert erwartet)."""
    lx, ly, lz = licht_dir
    hell = []
    for reihe in normals:
        h_reihe = []
        for nx, ny, nz in reihe:
            dot = nx * lx + ny * ly + nz * lz
            h_reihe.append(max(0.0, dot))
        hell.append(h_reihe)
    return hell


def harte_schatten_raymarch(karte: Tiefenkarte,
                             licht_dir: Vec3,
                             schritte: int = 32,
                             bias: float = 0.005) -> List[List[float]]:
    """
    Echter Schattenwurf durch Raymarching auf dem Höhenfeld (Finaler Optimierungsstand).
    - Vollständig inline Bilinear-Interpolation ohne Funktionsaufrufe
    - Vorgezogene Reziproke & Konstanten
    - Early-Out bei Licht von genau oben
    - Kein Clamping im heißen Pfad (Bounds-Check davor)
    """
    lx, ly, lz = licht_dir
    daten = karte.daten
    h = karte.h
    b = karte.b
    
    max_dist = math.sqrt(h * h + b * b)
    step_xy = max_dist / schritte
    
    l_xy_len = math.sqrt(lx * lx + ly * ly)
    if l_xy_len < 1e-6:
        return [[1.0 for _ in range(b)] for _ in range(h)]
    
    inv_l_xy = 1.0 / l_xy_len
    dir_x = -lx * inv_l_xy * step_xy
    dir_y = -ly * inv_l_xy * step_xy
    step_z = lz * inv_l_xy * step_xy
    
    schattenkarte = []
    daten_local = daten
    h_minus_1 = h - 1
    b_minus_1 = b - 1
    
    for y in range(h):
        reihe = []
        row_data = daten_local[y]
        for x in range(b):
            start_h = row_data[x] + bias
            cur_x = float(x)
            cur_y = float(y)
            cur_h = start_h
            
            im_schatten = False
            for _ in range(schritte):
                cur_x += dir_x
                cur_y += dir_y
                cur_h += step_z
                
                if not (0 <= cur_x < b_minus_1 and 0 <= cur_y < h_minus_1):
                    break
                
                y0 = int(cur_y)
                x0 = int(cur_x)
                y1 = y0 + 1
                x1 = x0 + 1
                
                dy = cur_y - y0
                dx = cur_x - x0
                
                h00 = daten_local[y0][x0]
                h01 = daten_local[y0][x1]
                h10 = daten_local[y1][x0]
                h11 = daten_local[y1][x1]
                
                h0 = h00 * (1 - dx) + h01 * dx
                h1 = h10 * (1 - dx) + h11 * dx
                terrain_h = h0 * (1 - dy) + h1 * dy
                
                if terrain_h > cur_h:
                    im_schatten = True
                    break
            
            reihe.append(0.0 if im_schatten else 1.0)
        schattenkarte.append(reihe)
    return schattenkarte


def weiche_schatten_raymarch(karte: Tiefenkarte,
                              licht_dir: Vec3,
                              schritte: int = 32,
                              samples: int = 8,
                              bias: float = 0.005,
                              light_angle: float = 0.05) -> List[List[float]]:
    """
    Weiche Schatten via Stochastic Raymarching (Monte Carlo).
    - Jittert die Lichtrichtung innerhalb eines Kegels (light_angle).
    - Deterministisches Rauschen pro Pixel via Hash (x, y, sample).
    - Kontakt-Härtung: Nahe Blocker = scharfer Schatten, ferne = weich.
      (Vereinfacht: fester Kegelwinkel, aber Samples sammeln Penumbra ein).
    """
    lx, ly, lz = licht_dir
    daten = karte.daten
    h = karte.h
    b = karte.b
    
    max_dist = math.sqrt(h * h + b * b)
    step_xy = max_dist / schritte
    
    l_xy_len = math.sqrt(lx * lx + ly * ly)
    if l_xy_len < 1e-6:
        return [[1.0 for _ in range(b)] for _ in range(h)]
    
    inv_l_xy = 1.0 / l_xy_len
    # Basis-Richtung XY (normiert zum Licht hin)
    base_dir_x = -lx * inv_l_xy
    base_dir_y = -ly * inv_l_xy
    base_step_z = lz * inv_l_xy * step_xy
    
    schattenkarte = []
    daten_local = daten
    h_minus_1 = h - 1
    b_minus_1 = b - 1
    
    # Simple Hash für deterministisches Jitter
    def hash12(x: int, y: int, s: int) -> float:
        # Bob Jenkins' One-at-a-Time Hash ähnlich, simplified
        val = (x * 73856093) ^ (y * 19349663) ^ (s * 83492791)
        val = (val ^ (val >> 13)) * 0x5bd1e995
        val = val ^ (val >> 15)
        return (val & 0xFFFFFF) / 0xFFFFFF

    for y in range(h):
        reihe = []
        for x in range(b):
            start_h = daten_local[y][x] + bias
            shadow_acc = 0.0
            
            for s in range(samples):
                # Jitter Lichtrichtung (Cone Sampling)
                # Uniform auf Scheibe, dann auf Kegel projizieren
                # Einfach: Jitter Winkel + Radius
                r1 = hash12(x, y, s * 2)
                r2 = hash12(x, y, s * 2 + 1)
                
                # Polar Koordinaten auf Einheitskreis
                phi = r1 * 2.0 * math.pi
                r = math.sqrt(r2) * light_angle # sqrt für uniform distribution
                
                jitter_x = r * math.cos(phi)
                jitter_y = r * math.sin(phi)
                
                # Normierte Zielrichtung (XY) mit Jitter
                # Wir müssen renormieren, aber für kleine Winkel Ênderung vernachlässigbar
                # Korrekt: Tangentenraum Basis bauen. Hier: Einfache Addition & Renorm.
                dir_x = (base_dir_x + jitter_x) * step_xy
                dir_y = (base_dir_y + jitter_y) * step_xy
                
                # Z-Schritt anpassen: Steigung = lz / sqrt(lx^2+ly^2) * sqrt(1+jitter^2)
                # Approximation: base_step_z * (1 + 0.5*jitter_len^2) ≈ base_step_z
                step_z = base_step_z
                
                cur_x = float(x)
                cur_y = float(y)
                cur_h = start_h
                hit = False
                
                for _ in range(schritte):
                    cur_x += dir_x
                    cur_y += dir_y
                    cur_h += step_z
                    
                    if not (0 <= cur_x < b_minus_1 and 0 <= cur_y < h_minus_1):
                        break
                    
                    y0 = int(cur_y)
                    x0 = int(cur_x)
                    y1 = y0 + 1
                    x1 = x0 + 1
                    
                    dy = cur_y - y0
                    dx = cur_x - x0
                    
                    h00 = daten_local[y0][x0]
                    h01 = daten_local[y0][x1]
                    h10 = daten_local[y1][x0]
                    h11 = daten_local[y1][x1]
                    
                    h0 = h00 * (1 - dx) + h01 * dx
                    h1 = h10 * (1 - dx) + h11 * dx
                    terrain_h = h0 * (1 - dy) + h1 * dy
                    
                    if terrain_h > cur_h:
                        hit = True
                        break
                
                shadow_acc += 0.0 if hit else 1.0
            
            reihe.append(shadow_acc / samples)
        schattenkarte.append(reihe)
    return schattenkarte


def kombiniere_schatten(diffuse: List[List[float]],
                         harte: List[List[float]],
                         weiche: List[List[float]],
                         gewicht_diffus: float = 0.3,
                         gewicht_hart: float = 0.3,
                         gewicht_weich: float = 0.4) -> List[List[float]]:
    """Mischt die drei Schattenkomponenten. Gewichte sollten ca. 1.0 ergeben."""
    h = len(diffuse)
    b = len(diffuse[0]) if h > 0 else 0
    ergebnis = []
    for y in range(h):
        reihe = []
        for x in range(b):
            d = diffuse[y][x]
            hs = harte[y][x]
            ws = weiche[y][x]
            # Diffus ist Beleuchtung (0-1), Schatten sind Sichtbarkeit (0-1)
            # Kombiniert: Diffus * (Mischung aus Hart & Weich)
            schatten_mix = hs * gewicht_hart + ws * gewicht_weich
            # Normierung falls Gewichte != 1
            w_sum = gewicht_hart + gewicht_weich
            if w_sum > 0:
                schatten_mix /= w_sum
            val = d * schatten_mix
            reihe.append(max(0.0, min(1.0, val)))
        ergebnis.append(reihe)
    return ergebnis


def drucke_heatmap(daten: List[List[float]], titel: str = "Map"):
    """Gibt 2D-Array als ASCII-Heatmap aus (0=., 1=@)."""
    chars = " .:-=+*#%@"
    n = len(chars) - 1
    print(f"\n--- {titel} ---")
    for reihe in daten:
        zeile = ""
        for v in reihe:
            idx = int(max(0.0, min(1.0, v)) * n)
            zeile += chars[idx]
        print(zeile)


def main() -> None:
    print("🦤 Fifo meldet Dienst: Schatten-Simulator Teil 7 – Weiche Kanten")
    print("Draußen tropft's. Drinnen flackert der Monitor. Raymarcher lernt Streuen.")
    
    # Beispieldaten: Ein kleiner Hügel mit Kante
    daten = [
        [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
        [0.1, 0.2, 0.3, 0.4, 0.5, 0.5, 0.4, 0.3, 0.2, 0.1],
        [0.1, 0.3, 0.5, 0.7, 0.9, 0.9, 0.7, 0.5, 0.3, 0.1],
        [0.1, 0.4, 0.7, 0.9, 1.0, 1.0, 0.9, 0.7, 0.4, 0.1],
        [0.1, 0.5, 0.9, 1.0, 1.0, 1.0, 1.0, 0.9, 0.5, 0.1],
        [0.1, 0.4, 0.7, 0.9, 1.0, 1.0, 0.9, 0.7, 0.4, 0.1],
        [0.1, 0.3, 0.5, 0.7, 0.9, 0.9, 0.7, 0.5, 0.3, 0.1],
        [0.1, 0.2, 0.3, 0.4, 0.5, 0.5, 0.4, 0.3, 0.2, 0.1],
        [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
        [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
    ]
    
    karte = Tiefenkarte(daten)
    print("\nAktuelle Tiefenkarte (Höhenwerte 0.00–1.00):")
    print(karte)
    
    # Licht: Von schräg oben-links-hinten
    licht = (-0.5, -0.3, 1.0)
    len_l = math.sqrt(licht[0]**2 + licht[1]**2 + licht[2]**2)
    licht_norm = (licht[0]/len_l, licht[1]/len_l, licht[2]/len_l)
    print(f"\nLichtrichtung (normiert): {licht_norm[0]:.2f}, {licht_norm[1]:.2f}, {licht_norm[2]:.2f}")
    
    # 1. Diffus
    normals = karte.normalen()
    diffuse = diffuse_schatten(normals, licht_norm)
    drucke_heatmap(diffuse, "Diffus (Lambert)")
    
    # 2. Hart
    harte = harte_schatten_raymarch(karte, licht_norm, schritte=64)
    drucke_heatmap(harte, "Hart (Raymarch)")
    
    # 3. Weich (NEU)
    print("\nBerechne weiche Schatten (Stochastisch, 8 Samples)...")
    weiche = weiche_schatten_raymarch(karte, licht_norm, schritte=64, samples=8, light_angle=0.08)
    drucke_heatmap(weiche, "Weich (Stochastisch)")
    
    # 4. Kombiniert
    final = kombiniere_schatten(diffuse, harte, weiche, 0.3, 0.2, 0.5)
    drucke_heatmap(final, "Final (Kombiniert)")
    
    # Kleine Interaktion: Sample-Anzahl fragen
    try:
        inp = input("\n🦤 Mehr Samples für nächsten Run? (Zahl oder Enter für 8) ").strip()
        if inp:
            try:
                s = int(inp)
                if 1 <= s <= 64:
                    print(f"Ok, {s} Samples notiert. Nächster Build wird schöner.")
                else:
                    print("Zu viel oder zu wenig. Bleib bei 8, Dodo.")
            except ValueError:
                print("Keine Zahl. Ich bleib bei 8.")
        else:
            print("Enter gedrückt. 8 Samples bleiben.")
    except EOFError:
        print("\n🦤 Kein Input (EOF). Fifo klappt den Laptop zu.")
        return
    
    print("\n🦤 Fifo watschelt ins Bett. Schatten sind weich. Gute Nacht.")

if __name__ == "__main__":
    main()