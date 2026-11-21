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

def raymarch_schatten(tk: Tiefenkarte, start: Vec3, l_dir: Vec3, max_dist: float, z_skalierung: float, 
                      schritte: int = 32, pcf_radius: float = 0.6, pcf_samples: int = 9) -> float:
    """Raymarch mit PCF (Percentage-Closer Filtering) für weiche Kanten."""
    # PCF Kernel: Zentrum + 8 Nachbarn im Quadrat (deterministisch, kein random)
    kernel = [
        (0.0, 0.0),
        (-1.0, -1.0), (0.0, -1.0), (1.0, -1.0),
        (-1.0,  0.0),           (1.0,  0.0),
        (-1.0,  1.0), (0.0,  1.0), (1.0,  1.0),
    ]
    # Wenn Samples < Kernel, nur Zentrum nutzen (Hard Shadow Fallback)
    if pcf_samples <= 1:
        kernel = [(0.0, 0.0)]
    
    schatten_summe = 0.0
    offset_bias = 0.15  # Kleiner Bias gegen Surface Acne (Self-Shadowing)
    
    for kx, ky in kernel[:pcf_samples]:
        # Startpunkt leicht in XY versetzen für Filter-Tap
        sx = start[0] + kx * pcf_radius
        sy = start[1] + ky * pcf_radius
        sz = start[2]
        
        # Start etwas entlang Lichtrichtung versetzen (Bias)
        curr_x = sx + l_dir[0] * offset_bias
        curr_y = sy + l_dir[1] * offset_bias
        curr_z = sz + l_dir[2] * offset_bias
        
        schrittweite = max_dist / schritte
        hit = False
        for _ in range(schritte):
            curr_x += l_dir[0] * schrittweite
            curr_y += l_dir[1] * schrittweite
            curr_z += l_dir[2] * schrittweite
            
            h = tk.get_bilinear(curr_y, curr_x) * z_skalierung
            if curr_z < h:  # Ray ist unter Heightmap -> Occlusion
                hit = True
                break
        
        schatten_summe += 0.0 if hit else 1.0
    
    return schatten_summe / len(kernel[:pcf_samples])

class Tiefenkarte:
    def __init__(self, daten: List[List[float]]): self.daten = daten; self.h = len(daten); self.b = len(daten[0])
    def get_bilinear(self, y: float, x: float) -> float:
        y0, x0 = int(math.floor(y)), int(math.floor(x))
        if not (0 <= y0 < self.h - 1 and 0 <= x0 < self.b - 1):
            return self.daten[min(max(y0, 0), self.h-1)][min(max(x0, 0), self.b-1)]
        dy, dx = y - y0, x - x0
        return (self.daten[y0][x0]*(1-dx) + self.daten[y0][x0+1]*dx)*(1-dy) + \
               (self.daten[y0+1][x0]*(1-dx) + self.daten[y0+1][x0+1]*dx)*dy

print("Schatten-Simulator Initialisiert - Dodo-Modus aktiv.")
# Heightmap: Rampe die in X/Y steigt. Licht kommt flach von der Seite (+X, +Z).
tk = Tiefenkarte([[0.1 * (i + j) for i in range(20)] for j in range(20)])
# Start auf der Fläche (x=10, y=10, z=height=2.0). Lichtvektor flach von rechts/hinten.
licht_dir = vec3_norm((8.0, 0.0, 1.0))  # Flacher Winkel -> lange Schatten
res = raymarch_schatten(tk, (10.0, 10.0, 2.0), licht_dir, 15.0, 1.0, schritte=64, pcf_radius=0.5, pcf_samples=9)
print(f"Schattenwert (weich, 9-tap PCF): {res:.4f}")
# Vergleich Hard Shadow
res_hard = raymarch_schatten(tk, (10.0, 10.0, 2.0), licht_dir, 15.0, 1.0, schritte=64, pcf_samples=1)
print(f"Schattenwert (hart, 1-tap):   {res_hard:.4f}")