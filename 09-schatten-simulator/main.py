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
    
    x = (index + 0.5) / count  # Gleichmäßige Stratifizierung
    y = radical_inverse_base2(index)  # Niedrig-Diskrepanz in y
    
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
            # Vermeidet Clustering im Zentrum
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
            h = tk.get_bilinear(float(y), float(x)) * z_scale
            start = (float(x), float(y), h + 0.01)  # Leicht über Oberfläche
            val = raymarch_schatten(tk, start, light_dir, max_dist, z_scale,
                                    steps, pcf_radius, pcf_samples,
                                    light_radius, light_samples)
            row.append(val)
        shadow_map.append(row)
    return shadow_map


def write_ppm(shadow_map: List[List[float]], filename: str = "shadow.ppm"):
    """Schreibt Shadow Map als PPM (P6 binary) in Datei."""
    h = len(shadow_map)
    w = len(shadow_map[0]) if h > 0 else 0
    header = f"P6\n{w} {h}\n255\n".encode('ascii')
    pixels = bytearray()
    for row in shadow_map:
        for val in row:
            v = int(max(0.0, min(1.0, val)) * 255)
            pixels.extend([v, v, v])  # Graustufen
    try:
        with open(filename, 'wb') as f:
            f.write(header + pixels)
        print(f"PPM geschrieben: {filename} ({w}x{h})", file=sys.stderr)
    except IOError as e:
        print(f"Fehler beim Schreiben: {e}", file=sys.stderr)
        # Fallback: stdout binary
        sys.stdout.buffer.write(header + pixels)


def ascii_shadow(shadow_map: List[List[float]], chars: str = " .:-=+*#%@") -> str:
    """ASCII-Art Visualisierung der Shadow Map."""
    lines = []
    n = len(chars) - 1
    for row in shadow_map:
        line = ''.join(chars[int(max(0.0, min(1.0, v)) * n)] for v in row)
        lines.append(line)
    return '\n'.join(lines)


def demo_heightmap(width: int, height: int) -> List[List[float]]:
    """Erzeugt eine Demo-Höhenkarte: zwei Hügel + Rauschen."""
    data = []
    for y in range(height):
        row = []
        for x in range(width):
            fx = x / (width - 1)
            fy = y / (height - 1)
            # Zwei Gauß-Hügel
            h1 = math.exp(-((fx - 0.3)**2 + (fy - 0.4)**2) * 50) * 0.8
            h2 = math.exp(-((fx - 0.7)**2 + (fy - 0.6)**2) * 30) * 0.5
            # Ein bisschen wellenförmiges Rauschen
            noise = math.sin(fx * 20) * math.cos(fy * 15) * 0.03
            row.append(h1 + h2 + noise)
        data.append(row)
    return data


def main() -> int:
    print("Schatten-Simulator Initialisiert - Dodo-Modus aktiv.", file=sys.stderr)
    
    # Demo-Szene
    WIDTH, HEIGHT = 60, 40
    heightmap_data = demo_heightmap(WIDTH, HEIGHT)
    tk = Tiefenkarte(heightmap_data)
    
    # Licht von oben-links
    light_dir = vec3_norm((-0.6, -0.4, -1.0))
    max_dist = 30.0
    z_scale = 5.0
    
    print(f"\nRendere Shadow Map ({WIDTH}x{HEIGHT}) mit PCF + Area Light...")
    
    # 1. Hart (Referenz)
    shadow_hard = render_shadow_map(tk, WIDTH, HEIGHT, light_dir, max_dist, z_scale,
                                     steps=32, pcf_samples=1, light_samples=1)
    
    # 2. Weich mit PCF
    shadow_pcf = render_shadow_map(tk, WIDTH, HEIGHT, light_dir, max_dist, z_scale,
                                    steps=32, pcf_radius=0.6, pcf_samples=9,
                                    light_samples=1)
    
    # 3. Area Light mit Hammersley (16 Samples)
    shadow_area = render_shadow_map(tk, WIDTH, HEIGHT, light_dir, max_dist, z_scale,
                                     steps=32, pcf_radius=0.6, pcf_samples=9,
                                     light_radius=0.15, light_samples=16)
    
    # ASCII Output
    print("\n--- Hart (1 Tap) ---")
    print(ascii_shadow(shadow_hard))
    
    print("\n--- Weich (9-tap PCF) ---")
    print(ascii_shadow(shadow_pcf))
    
    print("\n--- Area Light (Hammersley 16x) ---")
    print(ascii_shadow(shadow_area))
    
    # PPM speichern
    write_ppm(shadow_area, "shadow_demo.ppm")
    
    # Statistik
    def avg_shadow(sm):
        return sum(sum(row) for row in sm) / (len(sm) * len(sm[0]))
    
    print(f"\nDurchschnittlicher Schattenwert:")
    print(f"  Hart:      {avg_shadow(shadow_hard):.4f}")
    print(f"  PCF:       {avg_shadow(shadow_pcf):.4f}")
    print(f"  Area:      {avg_shadow(shadow_area):.4f}")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nAbbruch durch Nutzer.", file=sys.stderr)
        sys.exit(130)
    except EOFError:
        print("\nKeine Eingabe - Dodo schläft weiter.", file=sys.stderr)
        sys.exit(0)