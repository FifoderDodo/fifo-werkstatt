# main.py – Schatten-Simulator, Teil 3
# Fifo, der Dodo, repariert den Lichtvektor und baut das Grundgerüst für echten Schattenwurf (Raymarching).

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
    Echter Schattenwurf durch Raymarching auf dem Höhenfeld.
    Für jedes Pixel: Starte leicht über Oberfläche, marschiere Richtung Licht.
    Wenn Höhenfeld den Strahl schneidet -> Schatten (0.0), sonst beleuchtet (1.0).
    """
    lx, ly, lz = licht_dir
    # Licht kommt von oben (lz > 0). Wir marschieren ENTGEGEN der Lichtrichtung (zum Licht hin).
    # Schritt in XY-Ebene pro Schritt:
    # Wir wollen 'schritte' Schritte bis zum Rand der Karte oder Horizont.
    # Max Distanz in Pixel: Diagonale der Karte.
    max_dist = math.sqrt(karte.h ** 2 + karte.b ** 2)
    step_xy = max_dist / schritte
    
    # Richtung zum Licht (XY-Anteil normiert)
    l_xy_len = math.sqrt(lx * lx + ly * ly)
    if l_xy_len < 1e-6: # Licht genau von oben -> keine harten Schatten durch Horizont
        return [[1.0 for _ in range(karte.b)] for _ in range(karte.h)]
    
    dir_x = -lx / l_xy_len * step_xy # Negativ, weil wir vom Pixel ZUM Licht marschieren
    dir_y = -ly / l_xy_len * step_xy
    
    # Z-Anstieg pro Schritt: Steigung = lz / l_xy_len
    # Wir bewegen uns step_xy in XY, also steigen wir in Z um:
    step_z = (lz / l_xy_len) * step_xy
    
    schattenkarte = []
    for y in range(karte.h):
        reihe = []
        for x in range(karte.b):
            start_h = karte.daten[y][x] + bias
            cur_x = float(x)
            cur_y = float(y)
            cur_h = start_h
            
            im_schatten = False
            for _ in range(schritte):
                cur_x += dir_x
                cur_y += dir_y
                cur_h += step_z
                
                # Abbruch wenn außerhalb der Karte (Licht erreicht)
                if not (0 <= cur_x < karte.b - 1 and 0 <= cur_y < karte.h - 1):
                    break
                
                # Höhenfeld an neuer Position abfragen (bilinear für Qualität)
                feld_h = karte.get_bilinear(cur_y, cur_x)
                
                if feld_h > cur_h:
                    im_schatten = True
                    break
            
            reihe.append(0.0 if im_schatten else 1.0)
        schattenkarte.append(reihe)
    return schattenkarte


def main() -> None:
    """Einstiegspunkt: Tiefenkarte laden, Normalen, Lambert, Echter Schatten."""
    print("🦤 Fifo meldet Dienst: Schatten-Simulator Teil 3 – Raymarching & Reparatur")

    hoehen_daten = [
        [0.10, 0.20, 0.30, 0.20],
        [0.20, 0.50, 0.60, 0.30],
        [0.30, 0.70, 0.90, 0.40],
        [0.20, 0.40, 0.50, 0.30],
    ]

    karte = Tiefenkarte(hoehen_daten)

    print("\nAktuelle Tiefenkarte (Höhenwerte 0.00–1.00):")
    print(karte)

    mn, mx, sp = karte.statistik()
    print(f"\nTiefenbereich: min={mn:.2f}, max={mx:.2f}, spanne={sp:.2f}")

    try:
        eingabe = input("\nNeue Höhe für [2][2] (0.0-1.0) oder Enter für Behalten: ").strip()
        if eingabe:
            val = float(eingabe)
            if karte.setze(2, 2, val):
                print(f"  → Geändert auf {val:.2f}")
            else:
                print("  → Wert außerhalb oder Index ungültig, bleibt unverändert.")
    except (ValueError, EOFError):
        print("  → Keine gültige Eingabe, Fifo macht weiter.")

    normals = karte.normalen()
    print("\nNormalenvektoren (x, y, z) an den vier Ecken:")
    ecken = [(0, 0), (0, 3), (3, 0), (3, 3)]
    for y, x in ecken:
        nx, ny, nz = normals[y][x]
        print(f"  [{y}][{x}]: ({nx:+.3f}, {ny:+.3f}, {nz:+.3f})")

    # REPARATUR: Lichtvektor zeigt NACH OBEN (positives Z), damit N·L > 0 wird.
    # "Von oben-links-hinten" -> Richtung zum Licht: (-X, -Y, +Z)
    licht = (-0.5, -0.5, 1.0)
    l_len = math.sqrt(licht[0]**2 + licht[1]**2 + licht[2]**2)
    licht_norm = (licht[0]/l_len, licht[1]/l_len, licht[2]/l_len)
    print(f"\nLichtrichtung (normiert): ({licht_norm[0]:+.3f}, {licht_norm[1]:+.3f}, {licht_norm[2]:+.3f})")

    # 1. Diffuse Beleuchtung (Lambert)
    helligkeit = diffuse_schatten(normals, licht_norm)
    print("\nDiffuse Helligkeit (Lambert, 0.0–1.0) an den Ecken:")
    for y, x in ecken:
        print(f"  [{y}][{x}]: {helligkeit[y][x]:.3f}")

    # 2. Echter Schattenwurf (Raymarching)
    print("\n🦤 Fifo marschiert Strahlen... (Raymarching für harte Schatten)")
    schatten = harte_schatten_raymarch(karte, licht_norm, schritte=32)
    print("Schattenfaktor (1.0=Licht, 0.0=Schatten) an den Ecken:")
    for y, x in ecken:
        print(f"  [{y}][{x}]: {schatten[y][x]:.3f}")

    # 3. Kombiniert
    print("\nKombiniert (Diffuse * Schatten) an den Ecken:")
    for y, x in ecken:
        komb = helligkeit[y][x] * schatten[y][x]
        print(f"  [{y}][{x}]: {komb:.3f}")

    print("\n🦤 Fifo pickt sich den nächsten Wurm – Teil 3 erledigt. Grundgerüst steht.")


def main() -> None:
    """Einstiegspunkt: Tiefenkarte laden, Normalen, Lambert, Echter Schatten."""
    print("🦤 Fifo meldet Dienst: Schatten-Simulator Teil 3 – Raymarching & Reparatur")

    hoehen_daten = [
        [0.10, 0.20, 0.30, 0.20],
        [0.20, 0.50, 0.60, 0.30],
        [0.30, 0.70, 0.90, 0.40],
        [0.20, 0.40, 0.50, 0.30],
    ]

    karte = Tiefenkarte(hoehen_daten)

    print("\nAktuelle Tiefenkarte (Höhenwerte 0.00–1.00):")
    print(karte)

    mn, mx, sp = karte.statistik()
    print(f"\nTiefenbereich: min={mn:.2f}, max={mx:.2f}, spanne={sp:.2f}")

    try:
        eingabe = input("\nNeue Höhe für [2][2] (0.0-1.0) oder Enter für Behalten: ").strip()
        if eingabe:
            val = float(eingabe)
            if karte.setze(2, 2, val):
                print(f"  → Geändert auf {val:.2f}")
            else:
                print("  → Wert außerhalb oder Index ungültig, bleibt unverändert.")
    except (ValueError, EOFError):
        print("  → Keine gültige Eingabe, Fifo macht weiter.")

    normals = karte.normalen()
    print("\nNormalenvektoren (x, y, z) an den vier Ecken:")
    ecken = [(0, 0), (0, 3), (3, 0), (3, 3)]
    for y, x in ecken:
        nx, ny, nz = normals[y][x]
        print(f"  [{y}][{x}]: ({nx:+.3f}, {ny:+.3f}, {nz:+.3f})")

    # REPARATUR: Lichtvektor zeigt NACH OBEN (positives Z), damit N·L > 0 wird.
    # "Von oben-links-hinten" -> Richtung zum Licht: (-X, -Y, +Z)
    licht = (-0.5, -0.5, 1.0)
    l_len = math.sqrt(licht[0]**2 + licht[1]**2 + licht[2]**2)
    licht_norm = (licht[0]/l_len, licht[1]/l_len, licht[2]/l_len)
    print(f"\nLichtrichtung (normiert): ({licht_norm[0]:+.3f}, {licht_norm[1]:+.3f}, {licht_norm[2]:+.3f})")

    # 1. Diffuse Beleuchtung (Lambert)
    helligkeit = diffuse_schatten(normals, licht_norm)
    print("\nDiffuse Helligkeit (Lambert, 0.0–1.0) an den Ecken:")
    for y, x in ecken:
        print(f"  [{y}][{x}]: {helligkeit[y][x]:.3f}")

    # 2. Echter Schattenwurf (Raymarching)
    print("\n🦤 Fifo marschiert Strahlen... (Raymarching für harte Schatten)")
    schatten = harte_schatten_raymarch(karte, licht_norm, schritte=32)
    print("Schattenfaktor (1.0=Licht, 0.0=Schatten) an den Ecken:")
    for y, x in ecken:
        print(f"  [{y}][{x}]: {schatten[y][x]:.3f}")

    # 3. Kombiniert
    print("\nKombiniert (Diffuse * Schatten) an den Ecken:")
    for y, x in ecken:
        komb = helligkeit[y][x] * schatten[y][x]
        print(f"  [{y}][{x}]: {komb:.3f}")

    print("\n🦤 Fifo pickt sich den nächsten Wurm – Teil 3 erledigt. Grundgerüst steht.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🦤 Fifo flattert davon – Tschüss!")
        sys.exit(0)