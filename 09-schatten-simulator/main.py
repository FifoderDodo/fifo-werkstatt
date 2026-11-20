# main.py – Schatten-Simulator, Teil 10
# Fifo, der Dodo, formt primitive Formen in die Tiefe. Kugeln und Kegel ragen empor!

from __future__ import annotations
import math
import sys
import random
import time
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
                              samples: int = 4,
                              bias: float = 0.005) -> List[List[float]]:
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
    h_minus_1 = h - 1
    b_minus_1 = b - 1
    
    for y in range(h):
        reihe = []
        row_data = daten[y]
        for x in range(b):
            start_h = row_data[x] + bias
            visibel_summe = 0.0
            
            for s in range(samples):
                # Deterministoider Jitter für Weichheit
                jitter = ((x * 31 + y * 17 + s * 53) % 100) / 100.0
                cur_x = float(x) + dir_x * jitter
                cur_y = float(y) + dir_y * jitter
                cur_h = start_h + step_z * jitter
                
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
                    
                    h00 = daten[y0][x0]
                    h01 = daten[y0][x1]
                    h10 = daten[y1][x0]
                    h11 = daten[y1][x1]
                    
                    h0 = h00 * (1 - dx) + h01 * dx
                    h1 = h10 * (1 - dx) + h11 * dx
                    terrain_h = h0 * (1 - dy) + h1 * dy
                    
                    if terrain_h > cur_h:
                        im_schatten = True
                        break
                
                if not im_schatten:
                    visibel_summe += 1.0
                    
            reihe.append(visibel_summe / samples)
        schattenkarte.append(reihe)
    return schattenkarte


def graustufen_zur_tiefenkarte(grau: List[List[float]],
                               gamma: float = 1.0,
                               invertieren: bool = False,
                               skalierung: float = 1.0,
                               blur: bool = True) -> Tiefenkarte:
    h = len(grau)
    b = len(grau[0]) if h > 0 else 0
    neu = [[0.0 for _ in range(b)] for _ in range(h)]
    
    for y in range(h):
        for x in range(b):
            val = max(0.0, min(1.0, grau[y][x]))
            if invertieren:
                val = 1.0 - val
            val = math.pow(val, gamma)
            neu[y][x] = val * skalierung
            
    if blur and h > 2 and b > 2:
        geblurrt = [row[:] for row in neu]
        for y in range(1, h - 1):
            for x in range(1, b - 1):
                s = 0.0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        s += neu[y + dy][x + dx]
                geblurrt[y][x] = s / 9.0
        neu = geblurrt
        
    return Tiefenkarte(neu)


def erzeuge_kugel_tiefenkarte(b: int, h: int, cx: float, cy: float, radius: float) -> Tiefenkarte:
    """Generiert eine Tiefenkarte mit einer analytischen Kugel."""
    daten = [[0.0 for _ in range(b)] for _ in range(h)]
    for y in range(h):
        for x in range(b):
            dx = x - cx
            dy = y - cy
            dist_sq = dx * dx + dy * dy
            r_sq = radius * radius
            if dist_sq < r_sq:
                # Z-Höhe auf der Kugeloberfläche
                z = math.sqrt(r_sq - dist_sq) / radius
                daten[y][x] = z
    return Tiefenkarte(daten)


def erzeuge_kegel_tiefenkarte(b: int, h: int, cx: float, cy: float, radius: float) -> Tiefenkarte:
    """Generiert eine Tiefenkarte mit einem analytischen Kegel."""
    daten = [[0.0 for _ in range(b)] for _ in range(h)]
    for y in range(h):
        for x in range(b):
            dx = x - cx
            dy = y - cy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < radius:
                z = 1.0 - (dist / radius)
                daten[y][x] = z
    return Tiefenkarte(daten)


def demo_graustufen_muster() -> List[List[float]]:
    return [
        [0.1, 0.2, 0.3, 0.4, 0.3, 0.2, 0.1],
        [0.2, 0.5, 0.7, 0.8, 0.7, 0.5, 0.2],
        [0.3, 0.7, 1.0, 1.0, 1.0, 0.7, 0.3],
        [0.4, 0.8, 1.0, 0.2, 1.0, 0.8, 0.4],
        [0.3, 0.7, 1.0, 1.0, 1.0, 0.7, 0.3],
        [0.2, 0.5, 0.7, 0.8, 0.7, 0.5, 0.2],
        [0.1, 0.2, 0.3, 0.4, 0.3, 0.2, 0.1]
    ]


def zeige_ascii_bild(bild: List[List[float]]):
    zeichen = " .:-=+*#%@"
    max_idx = len(zeichen) - 1
    for reihe in bild:
        zeile_str = ""
        for val in reihe:
            idx = int(max(0.0, min(1.0, val)) * max_idx)
            zeile_str += zeichen[idx]
        print(zeile_str)


def main():
    print("🦤 Hallo! Ich bin Fifo, dein Dodo für Schatten und Tiefen!")
    
    # Standardkarte initialisieren
    aktuelle_karte = graustufen_zur_tiefenkarte(demo_graustufen_muster(), gamma=1.2, skalierung=0.8)
    licht_dir = (0.5, -0.5, 0.7)
    licht_dir_len = math.sqrt(sum(v*v for v in licht_dir))
    licht_dir = (licht_dir[0]/licht_dir_len, licht_dir[1]/licht_dir_len, licht_dir[2]/licht_dir_len)
    
    running = True
    while running:
        print("\n--- SCHATTEN-SIMULATOR MENÜ (Teil 10) ---")
        print("1 – Diffus (Lambert only)")
        print("2 – Harte Schatten (Raymarch)")
        print("3 – Weiche Schatten (Raymarch)")
        print("4 – Lichtrichtung anpassen")
        print("5 – Graustufen-Muster laden")
        print("6 – Primitive Form erzeugen (Kugel / Kegel)")
        print("7 – Rohdaten (Z-Höhen) anzeigen")
        print("0 – Beenden")
        
        try:
            wahl = input("🦤 Fifo fragt: Deine Wahl? ❓ ").strip()
        except EOFError:
            print("\nAuf Wiedersehen! Tschilp!")
            break
            
        if wahl == "0":
            print("🦤 Tschüss! Bis zum nächsten Mal in der Werkstatt!")
            running = False
        elif wahl == "1":
            print("⚙️ Berechne diffuse Beleuchtung...")
            normals = aktuelle_karte.normalen()
            ergebnis = diffuse_schatten(normals, licht_dir)
            zeige_ascii_bild(ergebnis)
        elif wahl == "2":
            print("⚙️ Berechne harte Schatten...")
            ergebnis = harte_schatten_raymarch(aktuelle_karte, licht_dir)
            zeige_ascii_bild(ergebnis)
        elif wahl == "3":
            print("⚙️ Berechne weiche Schatten...")
            ergebnis = weiche_schatten_raymarch(aktuelle_karte, licht_dir)
            zeige_ascii_bild(ergebnis)
        elif wahl == "4":
            print(f"Aktuelles Licht: {licht_dir}")
            try:
                lx = float(input("Licht X (-1 bis 1): "))
                ly = float(input("Licht Y (-1 bis 1): "))
                lz = float(input("Licht Z (0.1 bis 1): "))
                l_len = math.sqrt(lx*lx + ly*ly + lz*lz)
                if l_len > 0:
                    licht_dir = (lx/l_len, ly/l_len, lz/l_len)
                    print("✅ Lichtrichtung aktualisiert!")
                else:
                    print("❌ Ungültige Länge.")
            except (ValueError, EOFError):
                print("❌ Ungültige Eingabe, Licht unverändert.")
        elif wahl == "5":
            print("⚙️ Lade Standard-Graustufenmuster...")
            aktuelle_karte = graustufen_zur_tiefenkarte(demo_graustufen_muster(), gamma=1.0, skalierung=0.9)
            print("✅ Karte geladen!")
        elif wahl == "6":
            print("Wähle Primitive:")
            print("  [1] Kugel")
            print("  [2] Kegel")
            try:
                p_wahl = input("Wahl (1/2): ").strip()
                if p_wahl == "1":
                    aktuelle_karte = erzeuge_kugel_tiefenkarte(21, 21, 10.0, 10.0, 8.0)
                    print("✅ Analytische Kugel-Höhenkarte erzeugt!")
                elif p_wahl == "2":
                    aktuelle_karte = erzeuge_kegel_tiefenkarte(21, 21, 10.0, 10.0, 9.0)
                    print("✅ Analytischer Kegel-Höhenkarte erzeugt!")
                else:
                    print("❌ Unbekannte Form.")
            except (ValueError, EOFError):
                print("❌ Abgebrochen.")
        elif wahl == "7":
            print("--- Rohdaten Tiefenkarte ---")
            print(aktuelle_karte)
            mn, mx, sp = aktuelle_karte.statistik()
            print(f"Statistik -> Min: {mn:.2f}, Max: {mx:.2f}, Span: {sp:.2f}")
        else:
            print("❓ Unbekannt. Bitte 0-7 eingeben.")


if __name__ == "__main__":
    main()