# main.py – Schatten-Simulator, Teil 6
# Fifo, der Dodo, optimiert den Raymarcher ein letztes Mal heute. Dann ist Feierabend.

from __future__ import annotations
import math
import sys
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
    Echter Schattenwurf durch Raymarching auf dem Höhenfeld (Finaler Optimierungsstand für heute).
    - Vollständig inline Bilinear-Interpolation ohne Funktionsaufrufe
    - Vorgezogene Reziproke & Konstanten
    - Early-Out bei Licht von genau oben
    - Kein Clamping im heißen Pfad (Bounds-Check davor)
    """
    lx, ly, lz = licht_dir
    daten = karte.daten
    h = karte.h
    b = karte.b
    
    # Licht kommt von oben (lz > 0). Wir marschieren ENTGEGEN der Lichtrichtung (zum Licht hin).
    # Maximale Distanz ist Diagonale der Map.
    max_dist = math.sqrt(h * h + b * b)
    step_xy = max_dist / schritte
    
    l_xy_len = math.sqrt(lx * lx + ly * ly)
    if l_xy_len < 1e-6: # Licht genau von oben -> keine harten Schatten durch Horizont
        return [[1.0 for _ in range(b)] for _ in range(h)]
    
    inv_l_xy = 1.0 / l_xy_len
    # Richtung zum Licht (XY-Anteil normiert), negativ weil wir vom Pixel ZUM Licht marschieren
    dir_x = -lx * inv_l_xy * step_xy
    dir_y = -ly * inv_l_xy * step_xy
    
    # Z-Anstieg pro Schritt: Steigung = lz / l_xy_len
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
                
                # Abbruch wenn außerhalb der Karte (Licht erreicht)
                if not (0 <= cur_x < b_minus_1 and 0 <= cur_y < h_minus_1):
                    break
                
                # --- Inline Bilinear Interpolation (Ohne Clamping, da In-Bounds garantiert) ---
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


def kombiniere_schatten(diffus: List[List[float]], hart: List[List[float]]) -> List[List[float]]:
    """Multiplikation: Hart schneidet Diffus aus (oder mischt).
    Hier: Hart dominiert (0 gewinnt), sonst Diffus."""
    h = len(diffus)
    b = len(diffus[0])
    erg = []
    for y in range(h):
        reihe = []
        for x in range(b):
            # Hart ist 0 oder 1. Diffus 0-1.
            reihe.append(diffus[y][x] * hart[y][x])
        erg.append(reihe)
    return erg


def main() -> None:
    print("🦤 Fifo meldet Dienst: Schatten-Simulator Teil 6 – Letzter Schliff")
    print("Draußen tropft's. Drinnen flackert der Monitor. Raymarcher wird glattgezogen.")
    
    # Beispieldaten: Ein kleiner Hügelkrater
    daten = [
        [0.1, 0.2, 0.3, 0.2, 0.1],
        [0.2, 0.5, 0.6, 0.4, 0.2],
        [0.3, 0.7, 0.9, 0.5, 0.3],
        [0.2, 0.4, 0.5, 0.3, 0.2],
        [0.1, 0.2, 0.3, 0.2, 0.1],
    ]
    
    karte = Tiefenkarte(daten)
    print("\nAktuelle Tiefenkarte (Höhenwerte 0.00–1.00):")
    print(karte)
    
    # Licht von schräg oben-links
    licht = (0.5, -0.3, 1.0)
    laenge = math.sqrt(licht[0]**2 + licht[1]**2 + licht[2]**2)
    licht_norm = (licht[0]/laenge, licht[1]/laenge, licht[2]/laenge)
    
    print(f"\nLichtrichtung (normiert): {licht_norm[0]:.2f}, {licht_norm[1]:.2f}, {licht_norm[2]:.2f}")
    
    # 1. Diffus (Normalen)
    normals = karte.normalen()
    diffus = diffuse_schatten(normals, licht_norm)
    
    # 2. Hart (Raymarching) - Jetzt optimiert
    print("\nRaymarching läuft (optimiert)...")
    hart = harte_schatten_raymarch(karte, licht_norm, schritte=64, bias=0.005)
    
    # 3. Kombiniert
    final = kombiniere_schatten(diffus, hart)
    
    print("\nErgebnis: Kombinierte Schattenkarte (0.00 = dunkel, 1.00 = hell):")
    for reihe in final:
        print("  " + "  ".join(f"{v:.2f}" for v in reihe))
    
    # Eine kleine Interaktion vor dem Schlaf
    print("\nDer Code steht. Die Schatten fallen. Fifo gähnt.")
    try:
        antwort = input("Alles gut für heute? (j/n) ").strip().lower()
        if antwort.startswith('j'):
            print("🦤 Gute Nacht, Pixel. Der Dodo schläft.")
        else:
            print("🦤 Okay, noch eine Runde... aber morgen. Gute Nacht.")
    except EOFError:
        print("\n🦤 Keine Antwort. Der Dodo schläft trotzdem.")


if __name__ == "__main__":
    main()