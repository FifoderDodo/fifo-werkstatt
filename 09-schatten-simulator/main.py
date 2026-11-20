# main.py – Schatten-Simulator, Teil 9
# Fifo, der Dodo, malt Tiefen in Graustufen. Wer Höhen liest, sieht Schatten kommen.

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
                              samples: int = 4,
                              bias: float = 0.005) -> List[List[float]]:
    """
    Weiche Schatten via deterministischem Jitter (Hash) und Early-Out.
    Durchschnitt über mehrere versetzte Strahlen pro Pixel.
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
    base_dir_x = -lx * inv_l_xy * step_xy
    base_dir_y = -ly * inv_l_xy * step_xy
    step_z = lz * inv_l_xy * step_xy
    
    # Einfache Hash-Funktion für deterministisches Rauschen
    def hash2(x: int, y: int, s: int) -> Tuple[float, float]:
        n = (x * 127 + y * 311 + s * 17) & 0xFFFF
        n = (n ^ (n >> 8)) * 0x6D2B79F5
        n = (n ^ (n >> 8)) & 0xFFFFFFFF
        u = (n & 0xFFFF) / 65535.0
        v = ((n >> 16) & 0xFFFF) / 65535.0
        return (u - 0.5) * 0.5, (v - 0.5) * 0.5  # Jitter in [-0.25, 0.25] Pixel
    
    schattenkarte = []
    daten_local = daten
    h_minus_1 = h - 1
    b_minus_1 = b - 1
    
    for y in range(h):
        reihe = []
        for x in range(b):
            start_h = daten_local[y][x] + bias
            visibility_sum = 0.0
            
            for s in range(samples):
                jx, jy = hash2(x, y, s)
                cur_x = float(x) + jx
                cur_y = float(y) + jy
                cur_h = start_h
                
                im_schatten = False
                for _ in range(schritte):
                    cur_x += base_dir_x
                    cur_y += base_dir_y
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
                
                visibility_sum += 0.0 if im_schatten else 1.0
            
            reihe.append(visibility_sum / samples)
        schattenkarte.append(reihe)
    return schattenkarte


def kombiniere_schatten(diffus: List[List[float]],
                         hart: List[List[float]],
                         weich: List[List[float]],
                         gewicht_diffus: float = 0.3,
                         gewicht_hart: float = 0.3,
                         gewicht_weich: float = 0.4) -> List[List[float]]:
    """Mischt die drei Schattenarten gewichtet. Summe der Gewichte sollte 1.0 sein."""
    h = len(diffus)
    b = len(diffus[0]) if h > 0 else 0
    ergebnis = []
    for y in range(h):
        reihe = []
        for x in range(b):
            val = (diffus[y][x] * gewicht_diffus +
                   hart[y][x] * gewicht_hart +
                   weich[y][x] * gewicht_weich)
            reihe.append(max(0.0, min(1.0, val)))
        ergebnis.append(reihe)
    return ergebnis


def ascii_art(karte: List[List[float]], breite: int = 80) -> str:
    """Wandelt 0-1 Werte in ASCII-Zeichen um."""
    charset = " .'`^\":;~!+<>()[]{}|/?@#$%&*"
    h = len(karte)
    b = len(karte[0]) if h > 0 else 0
    if b == 0:
        return ""
    skalierung = b / breite
    zeilen = []
    for y in range(h):
        zeile = []
        for x_i in range(breite):
            src_x = int(x_i * skalierung)
            if src_x >= b:
                src_x = b - 1
            val = karte[y][src_x]
            idx = int(val * (len(charset) - 1))
            zeile.append(charset[idx])
        zeilen.append(" ".join(zeile))
    return "\n".join(zeilen)


def graustufen_zur_tiefenkarte(graustufen: List[List[float]],
                                gamma: float = 1.0,
                                invertieren: bool = False,
                                skaliere: float = 1.0,
                                glätten: int = 0) -> Tiefenkarte:
    """
    Wandelt ein 2D-Graustufenarray (0.0-1.0) in eine Tiefenkarte um.
    - gamma: >1 hebt Höhen hervor, <1 komprimiert.
    - invertieren: Schwarz wird Hoch, Weiß wird Tief.
    - skaliere: Multiplikator für endgültige Höhe (Clamping auf 1.0).
    - glätten: Anzahl Box-Filter Durchläufe (0 = aus).
    """
    h = len(graustufen)
    b = len(graustufen[0]) if h > 0 else 0
    if h == 0 or b == 0:
        return Tiefenkarte([[0.0]])
    
    daten = [[0.0 for _ in range(b)] for _ in range(h)]
    
    # 1. Gamma & Inversion & Skalierung
    for y in range(h):
        for x in range(b):
            val = graustufen[y][x]
            if invertieren:
                val = 1.0 - val
            if gamma != 1.0:
                val = val ** gamma
            val *= skaliere
            daten[y][x] = max(0.0, min(1.0, val))
    
    # 2. Optional: Box-Blur Glättung (separabel für Geschwindigkeit, hier naiv)
    for _ in range(glätten):
        neu = [[0.0 for _ in range(b)] for _ in range(h)]
        for y in range(h):
            for x in range(b):
                acc = 0.0
                cnt = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < b:
                            acc += daten[ny][nx]
                            cnt += 1
                neu[y][x] = acc / cnt if cnt else 0.0
        daten = neu
    
    return Tiefenkarte(daten)


def demo_graustufen_muster(breite: int = 20, hoehe: int = 15) -> List[List[float]]:
    """Erzeugt ein synthetisches Graustufenbild: Kreise, Gradienten, Rauschen."""
    daten = [[0.0 for _ in range(breite)] for _ in range(hoehe)]
    cx, cy = breite / 2.0, hoehe / 2.0
    max_r = math.sqrt(cx*cx + cy*cy)
    
    for y in range(hoehe):
        for x in range(breite):
            # Basis: Radialer Gradient
            dx = x - cx
            dy = y - cy
            dist = math.sqrt(dx*dx + dy*dy) / max_r
            val = 1.0 - dist  # Hell in der Mitte
            
            # Überlagerung: Zwei "Berge" (Sinuskreise)
            val += 0.3 * math.sin(dist * 12.0) * (1.0 - dist)
            
            # Rauschen (deterministisch)
            noise = ((x * 17 + y * 23) % 100) / 100.0 * 0.1
            val += noise
            
            daten[y][x] = max(0.0, min(1.0, val))
    return daten


def main() -> None:
    print("☔ Fifo's Schatten-Simulator – Teil 9: Graustufen-Tiefe")
    print("=" * 55)
    
    # 1. Demodaten: Synthetisches Graustufenbild
    print("🎨 Erzeuge Graustufen-Muster (20x15)...")
    grau_raw = demo_graustufen_muster(20, 15)
    
    # 2. Umwandlung zur Tiefenkarte (NEU in Teil 9)
    print("🧮 Wandele Graustufen in Tiefenkarte um (Gamma=1.5, Glätten=1)...")
    karte = graustufen_zur_tiefenkarte(grau_raw, gamma=1.5, glätten=1, skaliere=1.0)
    
    mn, mx, span = karte.statistik()
    print(f"Karte: {karte.b}x{karte.h}  Höhen: Min={mn:.2f} Max={mx:.2f} Spanne={span:.2f}")
    
    # Lichtrichtung
    licht = (0.4, -0.4, 0.82)
    l_len = math.sqrt(licht[0]**2 + licht[1]**2 + licht[2]**2)
    licht_norm = (licht[0]/l_len, licht[1]/l_len, licht[2]/l_len)
    print(f"Licht: ({licht_norm[0]:.2f}, {licht_norm[1]:.2f}, {licht_norm[2]:.2f})")
    
    # Menü
    while True:
        print("\n🔧 Modus wählen:")
        print("  1 – Diffus (Lambert only)")
        print("  2 – Harte Schatten (Raymarch)")
        print("  3 – Weiche Schatten (Raymarch + Jitter)")
        print("  4 – Kombiniert (Diffus + Hart + Weich)")
        print("  5 – Tiefe/Normalen anzeigen (ASCII)")
        print("  6 – Performance-Test (10 Runs)")
        print("  7 – Graustufen-Rohdaten anzeigen")
        print("  0 – Beenden")
        
        try:
            wahl = input("🦤 Fifo fragt: Deine Wahl? ").strip()
        except EOFError:
            print("\n👋 Tschüss! Der Dodo schläft.")
            break
        
        if wahl == "0":
            print("👋 Tschüss! Der Dodo schläft.")
            break
        
        start = time.perf_counter()
        
        if wahl == "1":
            normals = karte.normalen()
            diff = diffuse_schatten(normals, licht_norm)
            print("\n☀️ Diffuses Licht (Lambert):")
            print(ascii_art(diff))
        
        elif wahl == "2":
            hart = harte_schatten_raymarch(karte, licht_norm, schritte=32)
            print("\n🌑 Harte Schatten (Raymarch):")
            print(ascii_art(hart))
        
        elif wahl == "3":
            weich = weiche_schatten_raymarch(karte, licht_norm, schritte=32, samples=4)
            print("\n☁️ Weiche Schatten (4 Samples Jitter):")
            print(ascii_art(weich))
        
        elif wahl == "4":
            normals = karte.normalen()
            diff = diffuse_schatten(normals, licht_norm)
            hart = harte_schatten_raymarch(karte, licht_norm, schritte=32)
            weich = weiche_schatten_raymarch(karte, licht_norm, schritte=32, samples=4)
            combo = kombiniere_schatten(diff, hart, weich)
            print("\n🎨 Kombiniert (30% Diffus, 30% Hart, 40% Weich):")
            print(ascii_art(combo))
        
        elif wahl == "5":
            print("\n📏 Höhenfeld (Roh):")
            print(karte)
            normals = karte.normalen()
            print("\n📐 Normalen-Z (Aufwärts-Komponente):")
            nz_map = [[nz for (_, _, nz) in reihe] for reihe in normals]
            print(ascii_art(nz_map))
        
        elif wahl == "6":
            runs = 10
            print(f"\n⏱️ Performance-Test ({runs} Runs, 32 Schritte, 4 Samples)...")
            t_hart = 0.0
            t_weich = 0.0
            for i in range(runs):
                t0 = time.perf_counter()
                harte_schatten_raymarch(karte, licht_norm, schritte=32)
                t_hart += time.perf_counter() - t0
                t0 = time.perf_counter()
                weiche_schatten_raymarch(karte, licht_norm, schritte=32, samples=4)
                t_weich += time.perf_counter() - t0
            print(f"  Hart:  {t_hart/runs*1000:.2f} ms/Run")
            print(f"  Weich: {t_weich/runs*1000:.2f} ms/Run")
        
        elif wahl == "7":
            print("\n🖼️ Graustufen-Rohdaten (0.00 - 1.00):")
            for reihe in grau_raw:
                print("  " + "  ".join(f"{v:.2f}" for v in reihe))
        
        else:
            print("❓ Unbekannt. Bitte 0-7 eingeben.")
            continue
        
        dauer = time.perf_counter() - start
        print(f"⏱️ Dauer: {dauer*1000:.1f} ms")

if __name__ == "__main__":
    main()