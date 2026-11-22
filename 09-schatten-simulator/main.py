from __future__ import annotations
import math
import sys
from typing import List, Tuple

# ─── Typ-Aliase ──────────────────────────────────────────────────────
Vec3 = Tuple[float, float, float]

# ─── Konstanten ──────────────────────────────────────────────────────
# Kleiner Epsilon-Wert für Null-Checks
EPSILON = 1e-9
# Standard-Offset gegen Self-Shadowing-Artefakte (Peter Panning vermeiden)
OFFSET_BIAS = 0.15
# PCF-Kernel für weiche Schatten (3x3 Umfeld)
PCF_KERNEL_3X3: List[Tuple[float, float]] = [
    (0.0, 0.0),
    (-1.0, -1.0), (0.0, -1.0), (1.0, -1.0),
    (-1.0,  0.0),           (1.0,  0.0),
    (-1.0,  1.0), (0.0,  1.0), (1.0,  1.0),
]

# ─── Vektormathematik – minimal, aber ausreichend ────────────────────

def vec3_norm(v: Vec3) -> Vec3:
    """Normalisiert einen 3D-Vektor. Fällt bei Nullvektor auf (0,0,1) zurück."""
    x, y, z = v
    l = math.sqrt(x * x + y * y + z * z)
    if l < EPSILON:
        return (0.0, 0.0, 1.0)
    return (x / l, y / l, z / l)


def vec3_dot(a: Vec3, b: Vec3) -> float:
    """Skalarprodukt zweier 3D-Vektoren."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vec3_add(a: Vec3, b: Vec3) -> Vec3:
    """Addiert zwei 3D-Vektoren komponentenweise."""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vec3_sub(a: Vec3, b: Vec3) -> Vec3:
    """Subtrahiert b von a komponentenweise."""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vec3_scale(v: Vec3, s: float) -> Vec3:
    """Skaliert einen 3D-Vektor mit einem Skalar."""
    return (v[0] * s, v[1] * s, v[2] * s)

# ─── Quasi-Zufallsfolgen für Area-Light-Sampling ────────────────────

def _radical_inverse_base2(index: int) -> float:
    """Radikale Inverse Basis 2 (Van-der-Corput-Sequenz). Gibt gleichverteilte Werte in [0,1)."""
    result = 0.0
    factor = 0.5
    i = index
    while i > 0:
        if i & 1:
            result += factor
        factor *= 0.5
        i >>= 1
    return result


def hammersley_2d(index: int, count: int) -> Tuple[float, float]:
    """Hammersley-Punkt in 2D für gegebenen Index und Gesamtzahl. Sehr gleichmäßig verteilt."""
    if count <= 0:
        return (0.0, 0.0)
    x = (index + 0.5) / count          # jitterter regulärer Grid in x
    y = _radical_inverse_base2(index)  # Van-der-Corput in y
    return (x, y)

# ─── Tiefenkarte (Höhenfeld) ────────────────────────────────────────

class Tiefenkarte:
    """Höhenfeld mit bilinearer Interpolation und Clamping an den Rändern."""
    
    def __init__(self, daten: List[List[float]]):
        self.daten = daten
        self.h = len(daten)                    # Zeilen (y)
        self.b = len(daten[0]) if daten else 0 # Spalten (x)
    
    def get_bilinear(self, y: float, x: float) -> float:
        """Bilineare Interpolation mit Clamping an Rändern.
        
        Koordinaten (y, x) entsprechen Zeile/Spalte. Werte außerhalb
        werden auf den gültigen Bereich geklemmt (kein Wrapping).
        """
        if self.h == 0 or self.b == 0:
            return 0.0
        
        # Ganzzahlige Koordinaten der vier Eckpunkte
        y0 = int(math.floor(y))
        x0 = int(math.floor(x))
        
        # Clamping auf gültigen Interpolationsbereich [0, h-2] × [0, b-2]
        if y0 < 0:
            y0 = 0
        elif y0 >= self.h - 1:
            y0 = self.h - 2
        if x0 < 0:
            x0 = 0
        elif x0 >= self.b - 1:
            x0 = self.b - 2
        
        y1 = y0 + 1
        x1 = x0 + 1
        
        # Bruchanteile für Interpolation
        dy = y - y0
        dx = x - x0
        
        # Vier Eckwerte holen
        v00 = self.daten[y0][x0]
        v10 = self.daten[y0][x1]
        v01 = self.daten[y1][x0]
        v11 = self.daten[y1][x1]
        
        # Bilineare Interpolation: erst x, dann y (oder umgekehrt)
        return (v00 * (1 - dx) * (1 - dy) +
                v10 * dx * (1 - dy) +
                v01 * (1 - dx) * dy +
                v11 * dx * dy)

# ─── Shadow-Raymarching mit PCF & Area Light ────────────────────────

def raymarch_schatten(tk: Tiefenkarte,
                      start: Vec3,
                      l_dir: Vec3,
                      max_dist: float,
                      z_skalierung: float,
                      schritte: int = 32,
                      pcf_radius: float = 0.6,
                      pcf_samples: int = 9,
                      light_radius: float = 0.0,
                      light_samples: int = 1) -> float:
    """Raymarching-Schatten mit PCF (Percentage Closer Filtering) und Area-Light-Sampling.
    
    Parameter:
        tk:             Tiefenkarte (Höhenfeld)
        start:          Startpunkt des Rays (x, y, z) – meist knapp über Oberfläche
        l_dir:          Normierte Lichtrichtung (zeigt VOM Licht ZUR Oberfläche)
        max_dist:       Maximale Marschdistanz
        z_skalierung:   Skalierung der Höhenwerte (Weltmaßstab)
        schritte:       Anzahl Raymarch-Schritte (mehr = genauer, langsamer)
        pcf_radius:     Radius des PCF-Kernels in Texel (weichere Kanten)
        pcf_samples:    Anzahl PCF-Taps (1 = hart, 9 = 3x3 Kernel)
        light_radius:   Radius des Area Lights (0 = Punktlichtquelle)
        light_samples:  Anzahl Samples auf Area Light (für Penumbra)
    
    Rückgabe:
        Schattenfaktor in [0, 1]: 0 = voller Schatten, 1 = voll beleuchtet
    """
    # PCF-Kernel wählen
    kernel = PCF_KERNEL_3X3
    if pcf_samples <= 1:
        kernel = [(0.0, 0.0)]
    
    # Area-Light Offsets generieren (Hammersley auf Disk)
    light_offsets = [(0.0, 0.0)]
    if light_radius > 1e-6 and light_samples > 1:
        light_offsets = []
        for i in range(light_samples):
            u, v = hammersley_2d(i, light_samples)
            phi = 2.0 * math.pi * u
            r = light_radius * math.sqrt(v)  # sqrt für gleichmäßige Verteilung auf Disk
            light_offsets.append((r * math.cos(phi), r * math.sin(phi)))
    
    schatten_summe = 0.0
    total_taps = len(kernel[:pcf_samples]) * len(light_offsets)
    
    # PCF: über Nachbarpixel um Startpunkt herum
    for kx, ky in kernel[:pcf_samples]:
        sx = start[0] + kx * pcf_radius
        sy = start[1] + ky * pcf_radius
        sz = start[2]
        
        # Area Light: über Lichtquellenfläche integrieren
        for lx, ly in light_offsets:
            # Lichtrichtung leicht variieren für Area-Light-Sample
            if lx != 0.0 or ly != 0.0:
                l_dir_var = vec3_norm((l_dir[0] + lx, l_dir[1] + ly, l_dir[2]))
            else:
                l_dir_var = l_dir
            
            # Startpunkt mit Bias vorverschieben (vermeidet Self-Shadowing)
            curr_x = sx + l_dir_var[0] * OFFSET_BIAS
            curr_y = sy + l_dir_var[1] * OFFSET_BIAS
            curr_z = sz + l_dir_var[2] * OFFSET_BIAS
            
            schrittweite = max_dist / schritte
            hit = False
            
            # Raymarching-Schleife
            for _ in range(schritte):
                curr_x += l_dir_var[0] * schrittweite
                curr_y += l_dir_var[1] * schrittweite
                curr_z += l_dir_var[2] * schrittweite
                
                # Höhe an aktueller (y, x) Position abfragen
                # Achtung: Tiefenkarte erwartet (y, x) = (row, col)
                h = tk.get_bilinear(curr_y, curr_x) * z_skalierung
                
                # Wenn Ray unter Höhenfeld taucht → Occlusion
                if curr_z < h:
                    hit = True
                    break
            
            # 1.0 = beleuchtet, 0.0 = im Schatten
            schatten_summe += 0.0 if hit else 1.0
    
    return schatten_summe / total_taps if total_taps > 0 else 1.0

# ─── Testdaten-Generierung ──────────────────────────────────────────

def erstelle_test_karte() -> Tiefenkarte:
    """Erzeugt eine 16×16 Test-Tiefenkarte mit zwei Hügeln und einem Tal."""
    daten = []
    for y in range(16):
        reihe = []
        for x in range(16):
            # Hügel 1: bei (4, 4), Höhe 1.0, Breite ~sqrt(8)
            dx1 = x - 4.0
            dy1 = y - 4.0
            h1 = 1.0 * math.exp(-(dx1*dx1 + dy1*dy1) / 8.0)
            
            # Hügel 2: bei (11, 11), Höhe 0.7, etwas breiter
            dx2 = x - 11.0
            dy2 = y - 11.0
            h2 = 0.7 * math.exp(-(dx2*dx2 + dy2*dy2) / 12.0)
            
            # Tal in der Mitte: bei (7.5, 7.5), Tiefe -0.3
            dx3 = x - 7.5
            dy3 = y - 7.5
            tal = -0.3 * math.exp(-(dx3*dx3 + dy3*dy3) / 10.0)
            
            reihe.append(h1 + h2 + tal)
        daten.append(reihe)
    return Tiefenkarte(daten)

# ─── Demo & Interaktion ─────────────────────────────────────────────

def demo_raymarch(tk: Tiefenkarte):
    """Führt vorberechnete Raymarch-Tests an 5 Positionen aus."""
    print("\n=== Raymarch-Demo ===")
    print("Lichtrichtung: von oben-links (normiert)")
    print("Positionen werden auf der Höhe der Karte getestet.\n")
    
    l_dir = vec3_norm((-0.5, -0.5, -1.0))  # Licht von oben-links
    max_dist = 10.0
    z_skalierung = 2.0
    
    test_punkte = [
        (2.0, 2.0, "Nahe Hügel 1 (Schattenseite)"),
        (7.5, 7.5, "Im Tal (starker Schatten)"),
        (11.0, 11.0, "Nahe Hügel 2 (Schattenseite)"),
        (8.0, 8.0, "Kante Tal/Hügel (Penumbra)"),
        (0.0, 0.0, "Ecke (kein Schatten)"),
    ]
    
    for x, y, name in test_punkte:
        h = tk.get_bilinear(y, x) * z_skalierung
        start = (x, y, h + 0.01)  # Knapp über Oberfläche
        
        # Hart / Weich / Area Light vergleichen
        hart = raymarch_schatten(tk, start, l_dir, max_dist, z_skalierung,
                                 schritte=32, pcf_samples=1, light_samples=1)
        weich = raymarch_schatten(tk, start, l_dir, max_dist, z_skalierung,
                                  schritte=32, pcf_radius=0.6, pcf_samples=9,
                                  light_samples=1)
        area = raymarch_schatten(tk, start, l_dir, max_dist, z_skalierung,
                                 schritte=32, pcf_radius=0.6, pcf_samples=9,
                                 light_radius=0.3, light_samples=16)
        
        print(f"  {name:30s}  x={x:4.1f} y={y:4.1f}  h={h:5.2f}")
        print(f"    Hart:   {hart:.3f}  |  Weich (PCF): {weich:.3f}  |  Area Light: {area:.3f}")
    print()


def test_einzelpunkt(tk: Tiefenkarte):
    """Interaktiver Test: Benutzer gibt x, y ein, Programm zeigt Schattenwerte."""
    print("\n=== Einzelpunkt-Test ===")
    print("Gib Koordinaten x y ein (0-15), oder 'q' zum Abbrechen.")
    
    l_dir = vec3_norm((-0.5, -0.5, -1.0))
    max_dist = 10.0
    z_skalierung = 2.0
    
    while True:
        try:
            eingabe = input("Koordinaten (x y) > ").strip()
            if eingabe.lower() in ('q', 'quit', 'exit', ''):
                break
            
            teile = eingabe.split()
            if len(teile) != 2:
                print("  Bitte zwei Zahlen eingeben (z.B. '7.5 7.5').")
                continue
            
            x = float(teile[0])
            y = float(teile[1])
            
            if not (0 <= x < 16 and 0 <= y < 16):
                print("  Koordinaten außerhalb der Karte (0-15).")
                continue
            
            h = tk.get_bilinear(y, x) * z_skalierung
            start = (x, y, h + 0.01)
            
            hart = raymarch_schatten(tk, start, l_dir, max_dist, z_skalierung,
                                     schritte=32, pcf_samples=1, light_samples=1)
            weich = raymarch_schatten(tk, start, l_dir, max_dist, z_skalierung,
                                      schritte=32, pcf_radius=0.6, pcf_samples=9,
                                      light_samples=1)
            area = raymarch_schatten(tk, start, l_dir, max_dist, z_skalierung,
                                     schritte=32, pcf_radius=0.6, pcf_samples=9,
                                     light_radius=0.3, light_samples=16)
            
            print(f"  Position: x={x:.2f} y={y:.2f}  Höhe: {h:.3f}")
            print(f"  Hart:     {hart:.4f}  (0=Schatten, 1=Licht)")
            print(f"  Weich:    {weich:.4f}  (PCF 3x3, r=0.6)")
            print(f"  Area:     {area:.4f}  (Radius 0.3, 16 Samples)\n")
        
        except EOFError:
            break
        except ValueError:
            print("  Ungültige Eingabe. Bitte Zahlen eingeben.")
        except KeyboardInterrupt:
            break
    print()

# ─── Hauptprogramm ──────────────────────────────────────────────────

def main() -> int:
    """Einstiegspunkt: Karte erzeugen, Menü anzeigen, Schleife fahren."""
    print("╔══════════════════════════════════════╗")
    print("║ Schatten-Simulator – Teil 62        ║")
    print("║ Raymarching mit PCF & Area Light    ║")
    print("║ Code-Struktur aufgeräumt, Docs added║")
    print("╚══════════════════════════════════════╝")
    
    tk = erstelle_test_karte()
    print(f"\nTiefenkarte erzeugt: {tk.b}x{tk.h} Pixel")
    
    while True:
        print("--- Menü ---")
        print("1) Raymarch-Demo an 5 Positionen")
        print("2) Einzelnen Punkt testen (Eingabe x y)")
        print("3) Beenden")
        
        try:
            wahl = input("Wahl [1-3] > ").strip()
        except EOFError:
            print("\nEOF – tschüss!")
            break
        except KeyboardInterrupt:
            print("\nAbbruch – tschüss!")
            break
        
        if wahl == '1':
            demo_raymarch(tk)
        elif wahl == '2':
            test_einzelpunkt(tk)
        elif wahl == '3':
            print("Tschüss!")
            break
        else:
            print("Unbekannte Option. Bitte 1, 2 oder 3 wählen.\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())