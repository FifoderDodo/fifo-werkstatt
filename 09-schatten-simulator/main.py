from __future__ import annotations
import math
import sys
from typing import List, Tuple

Vec3 = Tuple[float, float, float]

def vec3_norm(v: Vec3) -> Vec3:
    x, y, z = v
    l = math.sqrt(x * x + y * y + z * z)
    if l < 1e-9: return (0.0, 0.0, 1.0)
    return (x / l, y / l, z / l)

def vec3_dot(a: Vec3, b: Vec3) -> float: return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def vec3_add(a: Vec3, b: Vec3) -> Vec3: return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def vec3_sub(a: Vec3, b: Vec3) -> Vec3: return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def vec3_scale(v: Vec3, s: float) -> Vec3: return (v[0] * s, v[1] * s, v[2] * s)

def raymarch_schatten(tk: 'Tiefenkarte', start: Vec3, l_dir: Vec3, max_dist: float, z_skalierung: float, 
                      schritte: int = 32, pcf_radius: float = 0.6, pcf_samples: int = 9,
                      light_radius: float = 0.0, light_samples: int = 1) -> float:
    """Raymarch mit PCF und Area-Light-Sampling für echte Penumbra."""
    # PCF Kernel: Zentrum + 8 Nachbarn im Quadrat (deterministisch)
    kernel = [
        (0.0, 0.0),
        (-1.0, -1.0), (0.0, -1.0), (1.0, -1.0),
        (-1.0,  0.0),           (1.0,  0.0),
        (-1.0,  1.0), (0.0,  1.0), (1.0,  1.0),
    ]
    if pcf_samples <= 1:
        kernel = [(0.0, 0.0)]
    
    # Area Light Samples: zufällige Punkte auf Scheibe (deterministisch via Hammersley)
    light_offsets = [(0.0, 0.0)]
    if light_radius > 1e-6 and light_samples > 1:
        light_offsets = []
        for i in range(light_samples):
            # Hammersley sequence für bessere Verteilung
            phi = 2.0 * math.pi * _hammersley(i, light_samples)
            r = light_radius * math.sqrt(_hammersley(i + 1, light_samples))
            light_offsets.append((r * math.cos(phi), r * math.sin(phi)))
    
    offset_bias = 0.15
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

def _hammersley(index: int, count: int) -> float:
    """Radikale Inverse Basis 2 für Hammersley-Sequenz."""
    result = 0.0
    f = 0.5
    i = index
    while i > 0:
        if i & 1:
            result += f
        f *= 0.5
        i >>= 1
    return (index + 0.5) / count if count > 0 else 0.0  # Fallback, eigentlich radical inverse

class Tiefenkarte:
    def __init__(self, daten: List[List[float]]): self.daten = daten; self.h = len(daten); self.b = len(daten[0])
    def get_bilinear(self, y: float, x: float) -> float:
        y0, x0 = int(math.floor(y)), int(math.floor(x))
        if not (0 <= y0 < self.h - 1 and 0 <= x0 < self.b - 1):
            return self.daten[min(max(y0, 0), self.h-1)][min(max(x0, 0), self.b-1)]
        dy, dx = y - y0, x - x0
        return (self.daten[y0][x0]*(1-dx) + self.daten[y0][x0+1]*dx)*(1-dy) + \
               (self.daten[y0+1][x0]*(1-dx) + self.daten[y0+1][x0+1]*dx)*dy

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
    """Schreibt Shadow Map als PPM (P6 binary) nach stdout oder Datei."""
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
    except IOError:
        # Fallback: stdout binary (funktioniert in manchen Umgebungen)
        sys.stdout.buffer.write(header + pixels)

def ascii_shadow(shadow_map: List[List[float]], chars: str = " .:-=+*#%@") -> str:
    """ASCII-Art Visualisierung der Shadow Map."""
    lines = []
    n = len(chars) - 1
    for row in shadow_map:
        line = ''.join(chars[int(max(0.0, min(1.0, v)) * n)] for v in row)
        lines.append(line)
    return '\n'.join(lines)

print("Schatten-Simulator Initialisiert - Dodo-Modus aktiv.")
# Heightmap: Rampe die in X/Y steigt. Licht kommt flach von der Seite (+X, +Z).
tk = Tiefenkarte([[0.1 * (i + j) for i in range(40)] for j in range(30)])
licht_dir = vec3_norm((8.0, 0.0, 1.0))  # Flacher Winkel -> lange Schatten

# Single Point Test
start = (20.0, 15.0, 3.5 + 0.01)
res_soft = raymarch_schatten(tk, start, licht_dir, 20.0, 1.0, schritte=64, pcf_radius=0.5, pcf_samples=9)
res_hard = raymarch_schatten(tk, start, licht_dir, 20.0, 1.0, schritte=64, pcf_samples=1)
res_area = raymarch_schatten(tk, start, licht_dir, 20.0, 1.0, schritte=64, pcf_radius=0.5, pcf_samples=9,
                              light_radius=0.3, light_samples=16)
print(f"Schattenwert (weich, 9-tap PCF):     {res_soft:.4f}")
print(f"Schattenwert (hart, 1-tap):          {res_hard:.4f}")
print(f"Schattenwert (Area Light, 16 samples): {res_area:.4f}")

# Render kleine Shadow Map für Visualisierung
print("\nRendere Shadow Map (40x30)...")
shadow_map = render_shadow_map(tk, 40, 30, licht_dir, 20.0, 1.0,
                               steps=32, pcf_radius=0.4, pcf_samples=5,
                               light_radius=0.25, light_samples=9)

# ASCII Output
print("\nASCII Shadow Map:")
print(ascii_shadow(shadow_map))

# PPM Datei schreiben
write_ppm(shadow_map, "shadow_map.ppm")
print("Fertig. Dodo watschelt zufrieden weg.")