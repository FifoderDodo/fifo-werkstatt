from __future__ import annotations
import math
import sys
from typing import List, Tuple

Vec3 = Tuple[float, float, float]


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


def _radical_inverse_base2(index: int) -> float:
    """Radikale Inverse Basis 2 (Van der Corput-Sequenz)."""
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
    """Hammersley-Punkt in 2D für gegebene Index und Gesamtzahl."""
    if count <= 0:
        return (0.0, 0.0)
    x = (index + 0.5) / count
    y = _radical_inverse_base2(index)
    return (x, y)


def raymarch_schatten(tk: 'Tiefenkarte', start: Vec3, l_dir: Vec3, max_dist: float, z_skalierung: float, 
                      schritte: int = 32, pcf_radius: float = 0.6, pcf_samples: int = 9,
                      light_radius: float = 0.0, light_samples: int = 1) -> float:
    """Raymarch mit PCF und Area-Light-Sampling für echte Penumbra."""
    kernel = [
        (0.0, 0.0),
        (-1.0, -1.0), (0.0, -1.0), (1.0, -1.0),
        (-1.0,  0.0),           (1.0,  0.0),
        (-1.0,  1.0), (0.0,  1.0), (1.0,  1.0),
    ]
    if pcf_samples <= 1:
        kernel = [(0.0, 0.0)]
    
    light_offsets = [(0.0, 0.0)]
    if light_radius > 1e-6 and light_samples > 1:
        light_offsets = []
        for i in range(light_samples):
            u, v = hammersley_2d(i, light_samples)
            phi = 2.0 * math.pi * u
            r = light_radius * math.sqrt(v)
            light_offsets.append((r * math.cos(phi), r * math.sin(phi)))
    
    offset_bias = 0.15
    schatten_summe = 0.0
    total_taps = len(kernel[:pcf_samples]) * len(light_offsets)
    
    for kx, ky in kernel[:pcf_samples]:
        sx = start[0] + kx * pcf_radius
        sy = start[1] + ky * pcf_radius
        sz = start[2]
        
        for lx, ly in light_offsets:
            if lx != 0.0 or ly != 0.0:
                l_dir_var = vec3_norm((l_dir[0] + lx, l_dir[1] + ly, l_dir[2]))
            else:
                l_dir_var = l_dir
            
            curr_x = sx + l_dir_var[0] * offset_bias
            curr_y = sy + l_dir_var[1] * offset_bias
            curr_z = sz + l_dir_var[2] * offset_bias
            
            schrittweite = max_dist / schritte
            hit = False
            for _ in range(schritte):
                curr_x += l_dir_var[0] * schrittweite
                curr_y += l_dir_var[1] * schrittweite
                curr_z += l_dir_var[2] * schrittweite
                
                h = tk.get_bilinear(curr_y, curr_x) * z_skalierung
                if curr_z < h:
                    hit = True
                    break
            
            schatten_summe += 0.0 if hit else 1.0
    
    return schatten_summe / total_taps if total_taps > 0 else 1.0


class Tiefenkarte:
    """Höhenfeld mit bilinearer Interpolation."""
    def __init__(self, daten: List[List[float]]):
        self.daten = daten
        self.h = len(daten)
        self.b = len(daten[0]) if daten else 0
    
    def get_bilinear(self, y: float, x: float) -> float:
        """Bilineare Interpolation mit Clamping an Rändern."""
        if self.h == 0 or self.b == 0:
            return 0.0
        y0 = int(math.floor(y))
        x0 = int(math.floor(x))
        
        # Clamping
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
        
        dy = y - y0
        dx = x - x0
        
        # Bilineare Interpolation
        v00 = self.daten[y0][x0]
        v10 = self.daten[y0][x1]
        v01 = self.daten[y1][x0]
        v11 = self.daten[y1][x1]
        
        return (v00 * (1 - dx) * (1 - dy) +
                v10 * dx * (1 - dy) +
                v01 * (1 - dx) * dy +
                v11 * dx * dy)


def erstelle_test_karte() -> Tiefenkarte:
    """Erzeugt eine kleine Test-Tiefenkarte (Hügel + Tal)."""
    daten = []
    for y in range(16):
        reihe = []
        for x in range(16):
            # Zwei Gauß-Hügel und ein Tal
            dx1 = x - 4.0
            dy1 = y - 4.0
            h1 = 1.0 * math.exp(-(dx1*dx1 + dy1*dy1) / 8.0)
            
            dx2 = x - 11.0
            dy2 = y - 11.0
            h2 = 0.7 * math.exp(-(dx2*dx2 + dy2*dy2) / 12.0)
            
            # Tal in der Mitte
            dx3 = x - 7.5
            dy3 = y - 7.5
            tal = -0.3 * math.exp(-(dx3*dx3 + dy3*dy3) / 10.0)
            
            reihe.append(h1 + h2 + tal)
        daten.append(reihe)
    return Tiefenkarte(daten)


def demo_raymarch(tk: Tiefenkarte):
    """Führt ein paar Raymarch-Tests aus und gibt Ergebnisse aus."""
    print("\n=== Raymarch-Demo ===")
    print("Lichtrichtung: von oben-links (normiert)")
    print("Positionen werden auf der Höhe der Karte getestet.\n")
    
    l_dir = vec3_norm((-0.5, -0.5, -1.0))  # Licht von oben-links
    max_dist = 10.0
    z_skalierung = 2.0
    
    test_punkte = [
        (2.0, 2.0, "Nahe Hügel 1"),
        (7.5, 7.5, "Im Tal"),
        (11.0, 11.0, "Nahe Hügel 2"),
        (8.0, 8.0, "Kante Tal/Hügel"),
        (0.0, 0.0, "Ecke"),
    ]
    
    for x, y, name in test_punkte:
        h = tk.get_bilinear(y, x) * z_skalierung
        start = (x, y, h + 0.01)  # Ganz knapp über Oberfläche
        
        # Hartes Schatten (schnell)
        schatten_hart = raymarch_schatten(tk, start, l_dir, max_dist, z_skalierung,
                                          schritte=16, pcf_samples=1, light_samples=1)
        # Weiches Schatten (PCF 3x3)
        schatten_weich = raymarch_schatten(tk, start, l_dir, max_dist, z_skalierung,
                                           schritte=16, pcf_samples=9, light_samples=1)
        # Area Light (Penumbra)
        schatten_area = raymarch_schatten(tk, start, l_dir, max_dist, z_skalierung,
                                          schritte=16, pcf_samples=9, light_radius=0.3, light_samples=4)
        
        print(f"{name:20s}  Pos=({x:4.1f},{y:4.1f})  Höhe={h:5.2f}")
        print(f"  Hart:     {schatten_hart:.3f}")
        print(f"  Weich:    {schatten_weich:.3f}")
        print(f"  AreaLight:{schatten_area:.3f}")
        print()


def main():
    print("╔══════════════════════════════════════╗")
    print("║   Schatten-Simulator  –  Teil 60   ║")
    print("║   Raymarching mit PCF & Area Light ║")
    print("╚══════════════════════════════════════╝")
    
    tk = erstelle_test_karte()
    print(f"Tiefenkarte erzeugt: {tk.b}x{tk.h} Pixel")
    
    while True:
        print("\n--- Menü ---")
        print("1) Raymarch-Demo an 5 Positionen")
        print("2) Einzelnen Punkt testen (Eingabe x y)")
        print("3) Beenden")
        try:
            wahl = input("Wahl [1-3]: ").strip()
        except EOFError:
            print("\nTschüss! 🦤")
            break
        
        if wahl == "1":
            demo_raymarch(tk)
        elif wahl == "2":
            try:
                xy = input("x y (0-15): ").strip()
                if not xy:
                    continue
                x_str, y_str = xy.split()
                x = float(x_str)
                y = float(y_str)
                if not (0 <= x < tk.b and 0 <= y < tk.h):
                    print("Außerhalb der Karte!")
                    continue
                
                l_dir = vec3_norm((-0.5, -0.5, -1.0))
                max_dist = 10.0
                z_skalierung = 2.0
                h = tk.get_bilinear(y, x) * z_skalierung
                start = (x, y, h + 0.01)
                
                print(f"\nPunkt ({x:.1f}, {y:.1f}) Höhe={h:.2f}")
                for pcf, light_r, light_s, label in [
                    (1, 0.0, 1, "Hart"),
                    (9, 0.0, 1, "PCF 3x3"),
                    (9, 0.3, 4, "Area Light r=0.3"),
                    (9, 0.6, 8, "Area Light r=0.6"),
                ]:
                    s = raymarch_schatten(tk, start, l_dir, max_dist, z_skalierung,
                                          schritte=24, pcf_samples=pcf,
                                          light_radius=light_r, light_samples=light_s)
                    print(f"  {label:20s}: {s:.3f}")
            except ValueError:
                print("Ungültige Eingabe. Zwei Zahlen erwartet.")
            except EOFError:
                print("\nTschüss! 🦤")
                break
        elif wahl == "3":
            print("\nTschüss! 🦤")
            break
        else:
            print("Unbekannte Option.")

if __name__ == "__main__":
    main()