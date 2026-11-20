# main.py – Schatten-Simulator, Teil 8
# Fifo, der Dodo, baut einen Debug-Bypass. Manchmal muss man den Schatten ausknipsen, um das Licht zu sehen.

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
                              streuung: float = 0.15) -> List[List[float]]:
    """
    Weiche Schatten via stochastischem Raymarching (Percentage Closer Filtering Idee).
    - Jitter pro Sample via deterministischem Hash (kein random-Modul im heißen Pfad).
    - Streuungskonus öffnet sich in Lichtrichtung (Penumbra).
    - Early-Out wenn alle Samples im Schatten oder alle frei.
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
    
    # Präberechne Sample-Offsets (Halton-ähnlich via Hash für Stabilität)
    sample_offsets = []
    for i in range(samples):
        # Deterministisches "Rauschen" basierend auf Sample-Index
        h_val = ((i * 7451 + 12347) % 65536) / 65535.0 * 2.0 - 1.0  # -1 bis 1
        h_val2 = ((i * 12347 + 7451) % 65536) / 65535.0 * 2.0 - 1.0
        sample_offsets.append((h_val, h_val2))
    
    schattenkarte = []
    daten_local = daten
    h_minus_1 = h - 1
    b_minus_1 = b - 1
    
    for y in range(h):
        reihe = []
        for x in range(b):
            start_h = daten_local[y][x] + bias
            
            treffer = 0
            # Pixel-Hash für Jitter-Seed
            pixel_hash = (y * b + x) * 374761393 & 0xFFFFFFFF
            
            for s_idx, (off_x, off_y) in enumerate(sample_offsets):
                # Jitter mischen: Pixel-Hash + Sample-Index
                seed = (pixel_hash ^ (s_idx * 668265263)) & 0xFFFFFFFF
                # Einfache Integer-Hash -> Float -1..1
                jx = ((seed * 2891336453) & 0xFFFFFFFF) / 4294967295.0 * 2.0 - 1.0
                jy = ((seed ^ 0x9E3779B9) * 2891336453 & 0xFFFFFFFF) / 4294967295.0 * 2.0 - 1.0
                
                # Offset skalieren mit Streuung und Höhe (höher = breiterer Konus)
                jitter_x = (off_x + jx) * streuung * start_h
                jitter_y = (off_y + jy) * streuung * start_h
                
                cur_x = float(x) + jitter_x
                cur_y = float(y) + jitter_y
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
                
                if im_schatten:
                    treffer += 1
                
                # Early Out: Wenn schon genug Schatten für "dunkel" oder genug Licht für "hell"
                if treffer > samples // 2 and treffer == s_idx + 1: # Alles Schatten bisher
                    # Könnte abbrechen, aber wir wollen glatte Übergänge -> weiterlaufen lassen
                    pass
            
            schatten_faktor = 1.0 - (treffer / samples)
            reihe.append(schatten_faktor)
        schattenkarte.append(reihe)
    return schattenkarte


def kombiniere_schatten(diffus: List[List[float]],
                         hart: List[List[float]],
                         weich: List[List[float]],
                         w_diffus: float = 0.3,
                         w_hart: float = 0.3,
                         w_weich: float = 0.4) -> List[List[float]]:
    """Mischt die drei Schattenarten gewichtet. Summe Gewichte = 1.0 empfohlen."""
    h = len(diffus)
    b = len(diffus[0]) if h > 0 else 0
    ergebnis = []
    for y in range(h):
        reihe = []
        for x in range(b):
            d = diffus[y][x]
            h_s = hart[y][x]
            w_s = weich[y][x]
            # Diffus ist Helligkeit (0-1), Schatten sind Durchlass (0-1).
            # Wir wollen kombinierte Helligkeit.
            # Hart/Weich sind Schattenmasken (1=Licht, 0=Schatten).
            # Diffus ist bereits Beleuchtung.
            # Einfaches Modell: Diffus * (gewichtete Schattenmaske)
            schatten_mix = (w_hart * h_s + w_weich * w_s) / (w_hart + w_weich) if (w_hart + w_weich) > 0 else 1.0
            gesamt = d * schatten_mix
            # Gewicht diffus dazu? Nein, diffus ist Basisbeleuchtung.
            # Wir mischen: w_diffus * diffus + (1-w_diffus) * diffus * schatten_mix
            # => diffus * (w_diffus + (1-w_diffus)*schatten_mix)
            # Einfacher: Nutze Gewichte als Mischfaktoren für den finalen Output.
            val = w_diffus * d + w_hart * (d * h_s) + w_weich * (d * w_s)
            reihe.append(max(0.0, min(1.0, val)))
        ergebnis.append(reihe)
    return ergebnis


def ascii_art(karte: List[List[float]], invert: bool = False) -> str:
    """Wandelt 0-1 Map in ASCII um."""
    chars = " .:-=+*#%@" 
    if invert:
        chars = chars[::-1]
    zeilen = []
    for reihe in karte:
        zeile = ""
        for v in reihe:
            idx = int(max(0.0, min(1.0, v)) * (len(chars) - 1))
            zeile += chars[idx]
        zeilen.append(zeile)
    return "\n".join(zeilen)


def main() -> None:
    print("☔ Fifo's Schatten-Simulator – Teil 8: Debug-Bypass aktiv")
    print("=" * 50)
    
    # Beispieldaten: Ein kleiner Hügel + Einschnitt
    daten = [
        [0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10],
        [0.10, 0.20, 0.30, 0.40, 0.50, 0.50, 0.40, 0.30, 0.20, 0.10],
        [0.10, 0.30, 0.50, 0.70, 0.90, 0.90, 0.70, 0.50, 0.30, 0.10],
        [0.10, 0.40, 0.70, 0.90, 1.00, 1.00, 0.90, 0.70, 0.40, 0.10],
        [0.10, 0.30, 0.50, 0.70, 0.90, 0.90, 0.70, 0.50, 0.30, 0.10],
        [0.10, 0.20, 0.30, 0.40, 0.50, 0.50, 0.40, 0.30, 0.20, 0.10],
        [0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10],
    ]
    
    karte = Tiefenkarte(daten)
    print(f"Karte: {karte.b}x{karte.h}")
    mn, mx, sp = karte.statistik()
    print(f"Höhen: Min={mn:.2f} Max={mx:.2f} Spanne={sp:.2f}")
    
    # Lichtrichtung: Von links-oben-hinten (x+, y-, z+)
    # Normieren
    lx, ly, lz = 1.0, -1.0, 2.0
    ln = math.sqrt(lx*lx + ly*ly + lz*lz)
    licht = (lx/ln, ly/ln, lz/ln)
    print(f"Licht: ({licht[0]:.2f}, {licht[1]:.2f}, {licht[2]:.2f})")
    
    # Normals & Diffus
    normals = karte.normalen()
    diffus = diffuse_schatten(normals, licht)
    
    # --- BYPASS / DEBUG MENÜ ---
    print("\n🔧 Debug-Modus: Was soll berechnet werden?")
    print("  1: Alles (Diffus + Hart + Weich + Kombiniert) [Standard]")
    print("  2: Nur Diffus (schnell, keine Schatten)")
    print("  3: Nur Harte Schatten (Raymarch)")
    print("  4: Nur Weiche Schatten (Stochastisch)")
    print("  5: Nur Tiefe & Normalen (ASCII)")
    print("  6: Performance-Test (nur Harte Schatten, wenig Schritte)")
    
    modus = 1
    try:
        inp = input("Wähle Modus (1-6): ").strip()
        if inp:
            modus = int(inp)
    except (ValueError, EOFError):
        print("↩️ Keine gültige Eingabe, nehme Standard (1).")
    
    schritte = 32
    samples = 8
    
    if modus == 6:
        schritte = 16
        samples = 4
        print(f"⚡ Turbo-Modus: Schritte={schritte}, Samples={samples}")
    elif modus in (3, 4, 1):
        try:
            s_inp = input(f"Raymarch-Schritte (Default {schritte}): ").strip()
            if s_inp: schritte = max(1, int(s_inp))
            if modus in (4, 1):
                sa_inp = input(f"Weich-Samples (Default {samples}): ").strip()
                if sa_inp: samples = max(1, int(sa_inp))
        except (ValueError, EOFError):
            print("↩️ Standardwerte behalten.")
    
    hart = None
    weich = None
    kombi = None
    
    if modus in (1, 3, 6):
        print(f"\n🏃 Berechne harte Schatten ({schritte} Schritte)...")
        hart = harte_schatten_raymarch(karte, licht, schritte=schritte)
        print("Harte Schatten:")
        print(ascii_art(hart, invert=True))
    
    if modus in (1, 4):
        print(f"\n☁️ Berechne weiche Schatten ({schritte} Schritte, {samples} Samples)...")
        weich = weiche_schatten_raymarch(karte, licht, schritte=schritte, samples=samples)
        print("Weiche Schatten:")
        print(ascii_art(weich, invert=True))
    
    if modus == 5:
        print("\n🗺️ Tiefe (Höhenfeld):")
        print(ascii_art(karte.daten))
        print("\n📐 Normalen-Z (Aufwärts-Komponente):")
        nz_map = [[nz for (_, _, nz) in row] for row in normals]
        print(ascii_art(nz_map))
        print("\n☀️ Diffuse Beleuchtung (Lambert):")
        print(ascii_art(diffus))
        return
    
    if modus == 2:
        print("\n☀️ Diffuse Beleuchtung (Lambert):")
        print(ascii_art(diffus))
        return
    
    if modus in (3, 4):
        return
    
    # Modus 1 oder 6: Kombinieren
    if hart is not None and weich is not None:
        print("\n🎨 Kombiniere (Diffus 30%, Hart 30%, Weich 40%)...")
        kombi = kombiniere_schatten(diffus, hart, weich, 0.3, 0.3, 0.4)
        print("Finales Bild:")
        print(ascii_art(kombi))
    elif hart is not None:
        kombi = kombiniere_schatten(diffus, hart, hart, 0.3, 0.7, 0.0)
        print("\n🎨 Kombiniere (Diffus 30%, Hart 70%)...")
        print(ascii_art(kombi))
    elif weich is not None:
        kombi = kombiniere_schatten(diffus, weich, weich, 0.3, 0.0, 0.7)
        print("\n🎨 Kombiniere (Diffus 30%, Weich 70%)...")
        print(ascii_art(kombi))
    
    print("\n✅ Fertig. Nächstes Mal: Textur-Mapping oder SSAO?")

if __name__ == "__main__":
    main()