# main.py – Schatten-Simulator, Teil 2
# Fifo, der Dodo, wackelt mit dem Schwänzchen und baut das Grundgerüst für echte Tiefenberechnung.

from __future__ import annotations
import math
import sys
from typing import List


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

    def setze(self, y: int, x: int, wert: float) -> bool:
        """Setzt Wert, wenn im gültigen Bereich und 0-1."""
        if 0 <= y < self.h and 0 <= x < self.b and 0.0 <= wert <= 1.0:
            self.daten[y][x] = wert
            return True
        return False

    def normalen(self) -> List[List[tuple[float, float, float]]]:
        """Berechnet pro Pixel einen Normalenvektor (zentrale Differenzen).
        Rückgabe: Liste von (nx, ny, nz), Länge 1."""
        normals = []
        for y in range(self.h):
            reihe = []
            for x in range(self.b):
                # Ableitungen nach x und y (Sobel-ähnlich, hier einfach zentral)
                hx = (self.get(y, x + 1) - self.get(y, x - 1)) * 0.5
                hy = (self.get(y + 1, x) - self.get(y - 1, x)) * 0.5
                # Normalvektor zeigt "nach oben" aus der Oberfläche
                nx, ny, nz = -hx, -hy, 1.0
                laenge = math.sqrt(nx * nx + ny * ny + nz * nz)
                reihe.append((nx / laenge, ny / laenge, nz / laenge))
            normals.append(reihe)
        return normals

    def statistik(self) -> tuple[float, float, float]:
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


def diffuse_schatten(normals: List[List[tuple[float, float, float]]],
                     licht_dir: tuple[float, float, float]) -> List[List[float]]:
    """Einfaches Lambert-Modell: Helligkeit = max(0, N·L).
    Lichtvektor wird normiert erwartet."""
    lx, ly, lz = licht_dir
    hell = []
    for reihe in normals:
        h_reihe = []
        for nx, ny, nz in reihe:
            dot = nx * lx + ny * ly + nz * lz
            h_reihe.append(max(0.0, dot))
        hell.append(h_reihe)
    return hell


def main() -> None:
    """Einstiegspunkt: Tiefenkarte laden, Normalen rechnen, ersten Schatten werfen."""
    print("🦤 Fifo meldet Dienst: Schatten-Simulator Teil 2 – Normalen & Licht")

    # Beispieldaten: 4×4-Grid
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

    # Interaktion: ein Wert ändern
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

    # Normalen berechnen
    normals = karte.normalen()
    print("\nNormalenvektoren (x, y, z) an den vier Ecken:")
    ecken = [(0, 0), (0, 3), (3, 0), (3, 3)]
    for y, x in ecken:
        nx, ny, nz = normals[y][x]
        print(f"  [{y}][{x}]: ({nx:+.3f}, {ny:+.3f}, {nz:+.3f})")

    # Lichtquelle definieren (von oben-links-hinten)
    licht = (0.5, 0.5, -1.0)  # zeigt Richtung negative Z (in Bild rein)
    l_len = math.sqrt(licht[0]**2 + licht[1]**2 + licht[2]**2)
    licht_norm = (licht[0]/l_len, licht[1]/l_len, licht[2]/l_len)

    # Diffuse Beleuchtung berechnen
    helligkeit = diffuse_schatten(normals, licht_norm)
    print("\nDiffuse Helligkeit (0.0–1.0) an den vier Ecken:")
    for y, x in ecken:
        print(f"  [{y}][{x}]: {helligkeit[y][x]:.3f}")

    print("\n🦤 Fifo pickt sich den nächsten Wurm – Teil 2 erledigt.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🦤 Fifo flattert davon – Tschüss!")
        sys.exit(0)