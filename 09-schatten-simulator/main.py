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
    """Radikale Inverse Basis 2 (Van der Corput-Sequenz).
    
    Kehrt die Bits von index um und interpretiert sie als Binärbruch.
    z.B. index=1 (0b1) -> 0.1_2 = 0.5
         index=2 (0b10) -> 0.01_2 = 0.25
         index=3 (0b11) -> 0.11_2 = 0.75
    """
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
    """Hammersley-Punkt in 2D für gegebene Index und Gesamtzahl.
    
    Die Hammersley-Sequenz ist eine niedrig-diskrepante Folge, die sich hervorragend
    für Quasi-Monte-Carlo-Integration eignet. Sie kombiniert:
    - x: Gleichmäßige Stratifizierung (index + 0.5) / count
    - y: Van der Corput-Sequenz (radikale Inverse Basis 2)
    
    Eigenschaften:
    - Deterministisch, keine Zufallszahlen nötig
    - Sehr gute Verteilung, vermeidet Clustering
    - Ideal für Area-Light-Sampling auf Scheiben
    - Konvergenz O((log N)^d / N) statt O(1/sqrt(N)) bei zufälligem Sampling
    
    Args:
        index: Index des Samples (0 <= index < count)
        count: Gesamtzahl der Samples
    
    Returns:
        (x, y) Tupel im Einheitsquadrat [0,1)²
    """
    if count <= 0:
        return (0.0, 0.0)
    x = (index + 0.5) / count
    y = _radical_inverse_base2(index)
    return (x, y)


def raymarch_schatten(tk: 'Tiefenkarte', start: Vec3, l_dir: Vec3, max_dist: float, z_skalierung: float, 
                      schritte: int = 32, pcf_radius: float = 0.6, pcf_samples: int = 9,
                      light_radius: float = 0.0, light_samples: int = 1) -> float:
    """Raymarch mit PCF und Area-Light-Sampling für echte Penumbra.
    
    Kombiniert Percentage-Closer Filtering (PCF) für weiche Kanten
    mit Area-Light-Sampling via Hammersley-Sequenz für physikalische Penumbra.
    
    Args:
        tk: Tiefenkarte (Höhenfeld)
        start: Startpunkt des Rays (x, y, z)
        l_dir: Normierte Lichtrichtung
        max_dist: Maximale Marschdistanz
        z_skalierung: Skalierung der Höhenwerte
        schritte: Anzahl Raymarch-Schritte
        pcf_radius: PCF-Kernel-Radius in Pixeln
        pcf_samples: Anzahl PCF-Samples (1=kein PCF, 9=3x3 Kernel)
        light_radius: Radius des Area Lights (0=Punktlicht)
        light_samples: Anzahl Area-Light-Samples
    
    Returns:
        Schattierungsfaktor 0.0 (voll Schatten) bis 1.0 (voll beleuchtet)
    """
    # PCF Kernel: Zentrum + 8 Nachbarn im 3x3-Gitter (deterministisch)
    kernel = [
        (0.0, 0.0),
        (-1.0, -1.0), (0.0, -1.0), (1.0, -1.0),
        (-1.0,  0.0),           (1.0,  0.0),
        (-1.0,  1.0), (0.0,  1.0), (1.0,  1.0),
    ]
    if pcf_samples <= 1:
        kernel = [(0.0, 0.0)]
    
    # Area Light Samples: Hammersley-Sequenz auf Scheibe (deterministisch, gut verteilt)
    light_offsets = [(0.0, 0.0)]
    if light_radius > 1e-6 and light_samples > 1:
        light_offsets = []
        for i in range(light_samples):
            u, v = hammersley_2d(i, light_samples)
            # Konzentrische Abbildung Quadrat -> Scheibe (Shirley-Chiu)
            # Vermeidet Clustering im Zentrum im Gegensatz zu polar mapping
            phi = 2.0 * math.pi * u
            r = light_radius * math.sqrt(v)
            light_offsets.append((r * math.cos(phi), r * math.sin(phi)))
    
    offset_bias = 0.15  # Self-Shadowing Bias
    schatten_summe = 0.0
    total_taps = len(kernel[:pcf_samples]) * len(light_offsets)
    
    for kx, ky in kernel[:pcf_samples]:
        sx = start[0] + kx * pcf_radius
        sy = start[1] + ky * pcf_radius
        sz = start[2]
        
        for lx, ly in light_offsets:
            # Lichtrichtung leicht variieren für Area Light
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
        
        dy = y - y0
        dx = x - x0
        
        # Bilinear: (1-dy)*[(1-dx)*v00 + dx*v01] + dy*[(1-dx)*v10 + dx*v11]
        v00 = self.daten[y0][x0]
        v01 = self.daten[y0][x0 + 1]
        v10 = self.daten[y0 + 1][x0]
        v11 = self.daten[y0 + 1][x0 + 1]
        
        return (v00 * (1 - dx) + v01 * dx) * (1 - dy) + \
               (v10 * (1 - dx) + v11 * dx) * dy


def render_shadow_map(tk: Tiefenkarte, width: int, height: int, light_dir: Vec3,
                       max_dist: float, z_scale: float, steps: int = 32,
                       pcf_radius: float = 0.5, pcf_samples: int = 9,
                       light_radius: float = 0.0, light_samples: int = 1) -> List[List[float]]:
    """Rendert eine komplette Shadow Map für die Heightmap."""
    shadow_map = []
    for y in range(height):
        row = []
        for x in range(width):
            # Startpunkt auf der Oberfläche
            start = (float(x), float(y), tk.get_bilinear(y, x) * z_scale)
            shadow = raymarch_schatten(tk, start, light_dir, max_dist, z_scale,
                                       steps, pcf_radius, pcf_samples,
                                       light_radius, light_samples)
            row.append(shadow)
        shadow_map.append(row)
    return shadow_map


def ascii_shadow(shadow_map: List[List[float]], invert: bool = False) -> str:
    """Wandelt Shadow Map in ASCII-Art um."""
    ramp = "@%#*+=-:. " if not invert else " .:-=+*#%@"
    lines = []
    for row in shadow_map:
        line = ""
        for v in row:
            idx = int(v * (len(ramp) - 1))
            if idx < 0:
                idx = 0
            elif idx >= len(ramp):
                idx = len(ramp) - 1
            line += ramp[idx]
        lines.append(line)
    return "\n".join(lines)


def write_ppm(shadow_map: List[List[float]], filename: str) -> None:
    """Schreibt Shadow Map als PPM (P6 binary) Datei."""
    h = len(shadow_map)
    w = len(shadow_map[0]) if h > 0 else 0
    with open(filename, 'wb') as f:
        f.write(f'P6\n{w} {h}\n255\n'.encode())
        for row in shadow_map:
            for v in row:
                val = int(v * 255)
                if val < 0:
                    val = 0
                elif val > 255:
                    val = 255
                f.write(bytes([val, val, val]))


def generate_demo_heightmap(w: int, h: int) -> List[List[float]]:
    """Erzeugt eine Demo-Höhenkarte mit Hügeln, Tälern und einer Kante."""
    data = []
    for y in range(h):
        row = []
        for x in range(w):
            fx = x / (w - 1) * 4.0 - 2.0
            fy = y / (h - 1) * 4.0 - 2.0
            # Zwei Gaussche Hügel
            hill1 = 1.5 * math.exp(-(fx + 0.5)**2 - (fy - 0.3)**2)
            hill2 = 1.0 * math.exp(-(fx - 0.8)**2 - (fy + 0.5)**2)
            # Ein Tal
            valley = -0.7 * math.exp(-(fx)**2 - (fy)**2 / 0.5)
            # Scharfe Kante
            edge = 0.8 if fx > 0.0 else 0.0
            # Rauschen
            noise = 0.1 * math.sin(fx * 10.0) * math.cos(fy * 8.0)
            val = hill1 + hill2 + valley + edge + noise
            row.append(max(0.0, val))
        data.append(row)
    return data


def main() -> None:
    print("=== Schatten-Simulator: Area-Light & Hammersley Demo ===\n")
    
    # Parameter
    WIDTH, HEIGHT = 80, 40
    LIGHT_DIR = vec3_norm((0.5, -0.3, -1.0))  # Von oben-links-hinten
    MAX_DIST = 10.0
    Z_SCALE = 2.0
    STEPS = 64
    
    # Demo-Höhenkarte erzeugen
    print("Generiere Höhenkarte...")
    heightmap_data = generate_demo_heightmap(WIDTH, HEIGHT)
    tk = Tiefenkarte(heightmap_data)
    
    # Drei Schatten-Modi
    modes = [
        ("Hard Shadows (Punktlicht)", 0.0, 1, 0.0, 1),
        ("PCF Soft Shadows", 0.0, 1, 0.6, 9),
        ("Area Light + PCF (physikalisch)", 0.15, 16, 0.6, 9),
    ]
    
    for name, l_rad, l_samp, pcf_r, pcf_s in modes:
        print(f"\n--- {name} ---")
        print(f"   light_radius={l_rad}, light_samples={l_samp}, pcf_radius={pcf_r}, pcf_samples={pcf_s}")
        
        shadow_map = render_shadow_map(tk, WIDTH, HEIGHT, LIGHT_DIR,
                                       MAX_DIST, Z_SCALE, STEPS,
                                       pcf_r, pcf_s, l_rad, l_samp)
        
        # ASCII Output
        print(ascii_shadow(shadow_map))
        
        # PPM speichern
        fname = f"shadow_{name.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('+', 'plus')}.ppm"
        write_ppm(shadow_map, fname)
        print(f"   -> {fname} gespeichert")
    
    # Hammersley-Visualisierung
    print("\n--- Hammersley-Sequenz (erste 16 Punkte) ---")
    for i in range(16):
        x, y = hammersley_2d(i, 16)
        print(f"  [{i:2d}] ({x:.4f}, {y:.4f})")
    
    print("\nFertig! Dodo watschelt zufrieden davon. 🦤")

if __name__ == "__main__":
    try:
        main()
    except EOFError:
        print("\nKeine Eingabe, Dodo schläft weiter. 🦤")
    except KeyboardInterrupt:
        print("\nAbgebrochen. Dodo watschelt weg. 🦤")