from __future__ import annotations
import math
import sys
import random
from typing import List, Tuple, Optional, Dict

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

def raymarch_schatten(tk: Tiefenkarte, start: Vec3, l_dir: Vec3, max_dist: float, z_skalierung: float, schritte: int = 24) -> float:
    offset = 0.5
    curr_x, curr_y, curr_z = start[0] + l_dir[0] * offset, start[1] + l_dir[1] * offset, start[2] + l_dir[2] * offset
    schrittweite = max_dist / schritte
    for _ in range(schritte):
        curr_x += l_dir[0] * schrittweite
        curr_y += l_dir[1] * schrittweite
        curr_z += l_dir[2] * schrittweite
        h = tk.get_bilinear(curr_y, curr_x) * z_skalierung
        if curr_z < h:
            return 0.0
    return 1.0

class Tiefenkarte:
    def __init__(self, daten: List[List[float]]): self.daten = daten; self.h = len(daten); self.b = len(daten[0])
    def get_bilinear(self, y: float, x: float) -> float:
        y0, x0 = int(math.floor(y)), int(math.floor(x))
        if not (0 <= y0 < self.h - 1 and 0 <= x0 < self.b - 1): return self.daten[min(max(y0, 0), self.h-1)][min(max(x0, 0), self.b-1)]
        dy, dx = y - y0, x - x0
        return (self.daten[y0][x0]*(1-dx) + self.daten[y0][x0+1]*dx)*(1-dy) + (self.daten[y0+1][x0]*(1-dx) + self.daten[y0+1][x0+1]*dx)*dy

print("Schatten-Simulator Initialisiert - Dodo-Modus aktiv.")
tk = Tiefenkarte([[0.1 * (i+j) for i in range(10)] for j in range(10)])
res = raymarch_schatten(tk, (5.0, 5.0, 1.0), (0.0, 0.0, -1.0), 2.0, 1.0)
print(f"Schattenwert: {res}")