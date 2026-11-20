# main.py – Schatten-Simulator, Teil 4
# Fifo, der Dodo, optimiert das Raymarching: weniger Overhead, schnellere Bilinear-Interpolation, sauberere Schleife.

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
        
        # Clamping
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
    Echter Schattenwurf durch Raymarching auf dem Höhenfeld (optimiert).
    - Lokale Variablen für heiße Schleife
    - Inline-Bilinear ohne Clamping (Bounds-Check vorher)
    - Vorgezogener Reziproke für Division
    """
    lx, ly, lz = licht_dir
    daten = karte.daten
    h = karte.h
    b = karte.b
    
    # Licht kommt von oben (lz > 0). Wir marschieren ENTGEGEN der Lichtrichtung (zum Licht hin).
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
    # Lokale Referenzen für Speed
    daten_local = daten
    h_minus_1 = h - 1
    b_minus_1 = b - 1
    
    for y in range(h):
        reihe = []
        row_data = daten_local[y] # Zugriff auf Zeile für Start-Höhe
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
                # Wir prüfen gegen 0 und b-1/h-1, da wir bilinear y0,y1/x0,x1 brauchen
                if not (0 <= cur_x < b_minus_1 and 0 <= cur_y < h_minus_1):
                    break
                
                # --- Inline Bilinear Interpolation (Ohne Clamping, da In-Bounds) ---
                y0 = int(cur_y)
                x0 = int(cur_x)
                y1 = y0 + 1
                x1 = x0 + 1
                
                dy = cur_y - y0
                dx = cur_x - x0
                
                # Direktzugriff auf Listen (schneller als Methode)
                h00 = daten_local[y0][x0]
                h01 = daten_local[y0][x1]
                h10 = daten_local[y1][x0]
                h11 = daten_local[y1][x1]
                
                h0 = h00 * (1 - dx) + h01 * dx
                h1 = h10 * (1 - dx) + h11 * dx
                feld_h = h0 * (1 - dy) + h1 * dy
                # ----------------------------------------------------------------
                
                if feld_h > cur_h:
                    im_schatten = True
                    break
            
            reihe.append(0.0 if im_schatten else 1.0)
        schattenkarte.append(reihe)
    return schattenkarte


def kombiniere(lambert: List[List[float]],
               occlusion: List[List[float]],
               ambient: float = 0.15) -> List[List[float]]:
    """Kombiniert diffus (Lambert) und harten Schatten (Occlusion) mit Ambient-Anteil."""
    h = len(lambert)
    b = len(lambert[0]) if h > 0 else 0
    ergebnis = []
    for y in range(h):
        reihe = []
        for x in range(b):
            # Ambient + (Diffuse * Shadow)
            val = ambient + (1.0 - ambient) * lambert[y][x] * occlusion[y][x]
            reihe.append(max(0.0, min(1.0, val)))
        ergebnis.append(reihe)
    return ergebnis


def drucke_heatmap(daten: List[List[float]], titel: str) -> None:
    """Gibt 2D-Array als ASCII-Heatmap aus (0.0 bis 1.0)."""
    print(f"\n{titel}:")
    chars = " .:-=+*#%@"
    n = len(chars) - 1
    for reihe in daten:
        zeile = "  "
        for v in reihe:
            idx = int(max(0.0, min(1.0, v)) * n)
            zeile += chars[idx] + " "
        print(zeile)


def main() -> None:
    """Einstiegspunkt: Tiefenkarte laden, Normalen, Lambert, Echter Schatten, Kombinieren, Interaktion."""
    print("🦤 Fifo meldet Dienst: Schatten-Simulator Teil 4 – Raymarching optimiert")

    # Beispieldaten: Ein kleiner Hügel mit Kante
    hoehen_daten = [
        [0.10, 0.20, 0.30, 0.20],
        [0.20, 0.50, 0.60, 0.30],
        [0.30, 0.70, 0.90, 0.40],
        [0.20, 0.40, 0.50, 0.30],
    ]

    karte = Tiefenkarte(hoehen_daten)
    print("Aktuelle Tiefenkarte (Höhenwerte 0.00–1.00):")
    print(karte)
    mn, mx, sp = karte.statistik()
    print(f"Tiefenbereich: min={mn:.2f}, max={mx:.2f}, spanne={sp:.2f}")

    # Lichtvektor: Normiert, zeigt ZUR Lichtquelle (von Oberfläche weg). Z > 0 = von oben.
    # Beispiel: Leicht schräg von vorn-links-oben
    licht_roh = (-0.5, -0.3, 1.0)
    l_len = math.sqrt(licht_roh[0]**2 + licht_roh[1]**2 + licht_roh[2]**2)
    licht_dir = (licht_roh[0]/l_len, licht_roh[1]/l_len, licht_roh[2]/l_len)
    print(f"Lichtrichtung (normiert): ({licht_dir[0]:.3f}, {licht_dir[1]:.3f}, {licht_dir[2]:.3f})")

    # 1. Normalen
    normals = karte.normalen()
    
    # 2. Lambert (Diffuse)
    lambert = diffuse_schatten(normals, licht_dir)
    drucke_heatmap(lambert, "Lambert (Diffuse)")

    # 3. Harte Schatten (Raymarching optimiert)
    occlusion = harte_schatten_raymarch(karte, licht_dir, schritte=32, bias=0.005)
    drucke_heatmap(occlusion, "Occlusion (Harter Schatten)")

    # 4. Kombination
    final = kombiniere(lambert, occlusion, ambient=0.15)
    drucke_heatmap(final, "Final (Kombiniert + Ambient)")

    # Interaktive Schleife: Höhe ändern -> Neu berechnen
    print("\n🦤 Tipp neue Höhenwerte ein (y x wert), 'q' zum Beenden.")
    print("   Beispiel: 2 2 0.5  (setzt Zentrum auf 0.5)")
    
    while True:
        try:
            eingabe = input("🦤 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n🦤 Fifo watschelt davon. Tschüss!")
            break
        
        if not eingabe or eingabe.lower() == 'q':
            print("🦤 Fifo watschelt davon. Tschüss!")
            break
        
        teile = eingabe.split()
        if len(teile) != 3:
            print("🦤 Drei Werte erwartet: y x wert")
            continue
        
        try:
            y = int(teile[0])
            x = int(teile[1])
            wert = float(teile[2])
        except ValueError:
            print("🦤 Zahlen bitte: y x wert")
            continue
        
        if karte.setze(y, x, wert):
            print(f"🦤 Höhe [{y}][{x}] = {wert:.2f} gesetzt. Rechne neu...")
            # Nur betroffene Normalen aktualisieren? Einfach: Alles neu (klein).
            normals = karte.normalen()
            lambert = diffuse_schatten(normals, licht_dir)
            occlusion = harte_schatten_raymarch(karte, licht_dir, schritte=32, bias=0.005)
            final = kombiniere(lambert, occlusion, ambient=0.15)
            
            drucke_heatmap(lambert, "Lambert (Diffuse)")
            drucke_heatmap(occlusion, "Occlusion (Harter Schatten)")
            drucke_heatmap(final, "Final (Kombiniert + Ambient)")
            mn, mx, sp = karte.statistik()
            print(f"Tiefenbereich: min={mn:.2f}, max={mx:.2f}, spanne={sp:.2f}")
        else:
            print(f"🦤 Ungültig: y 0-{karte.h-1}, x 0-{karte.b-1}, wert 0.0-1.0")

if __name__ == "__main__":
    main()