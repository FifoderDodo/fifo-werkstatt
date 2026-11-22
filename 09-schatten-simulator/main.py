from __future__ import annotations
import math
import sys
import time
from typing import List, Tuple

# ─── Typ-Aliase ──────────────────────────────────────────────────────
Vec3 = Tuple[float, float, float]

# ─── Konstanten ──────────────────────────────────────────────────────
EPSILON = 1e-9
OFFSET_BIAS = 0.15
PCF_KERNEL_3X3: List[Tuple[float, float]] = [
    (0.0, 0.0),
    (-1.0, -1.0), (0.0, -1.0), (1.0, -1.0),
    (-1.0,  0.0),           (1.0,  0.0),
    (-1.0,  1.0), (0.0,  1.0), (1.0,  1.0),
]

# ─── Vektormathematik ────────────────────────────────────────────────

def vec3_norm(v: Vec3) -> Vec3:
    x, y, z = v
    l = math.sqrt(x * x + y * y + z * z)
    if l < EPSILON:
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


def vec3_cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1]*b[2] - a[2]*b[1],
            a[2]*b[0] - a[0]*b[2],
            a[0]*b[1] - a[1]*b[0])

# ─── Quasi-Zufallsfolgen ─────────────────────────────────────────────

def _radical_inverse_base2(index: int) -> float:
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
    if count <= 0:
        return (0.0, 0.0)
    x = (index + 0.5) / count
    y = _radical_inverse_base2(index)
    return (x, y)

# ─── Tiefenkarte ─────────────────────────────────────────────────────

class Tiefenkarte:
    def __init__(self, daten: List[List[float]]):
        self.daten = daten
        self.h = len(daten)
        self.b = len(daten[0]) if daten else 0
    
    def get_bilinear(self, y: float, x: float) -> float:
        if self.h == 0 or self.b == 0:
            return 0.0
        y0 = int(math.floor(y))
        x0 = int(math.floor(x))
        if y0 < 0: y0 = 0
        elif y0 >= self.h - 1: y0 = self.h - 2
        if x0 < 0: x0 = 0
        elif x0 >= self.b - 1: x0 = self.b - 2
        y1, x1 = y0 + 1, x0 + 1
        dy, dx = y - y0, x - x0
        v00 = self.daten[y0][x0]
        v10 = self.daten[y0][x1]
        v01 = self.daten[y1][x0]
        v11 = self.daten[y1][x1]
        return (v00 * (1 - dx) * (1 - dy) +
                v10 * dx * (1 - dy) +
                v01 * (1 - dx) * dy +
                v11 * dx * dy)

    def get_normal(self, y: float, x: float) -> Vec3:
        """Approximierte Normalen per Central Differences."""
        eps = 0.5
        hx = self.get_bilinear(y, x + eps) - self.get_bilinear(y, x - eps)
        hy = self.get_bilinear(y + eps, x) - self.get_bilinear(y - eps, x)
        return vec3_norm((-hx, -hy, 2.0 * eps))

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
    """Raymarching-Schatten mit PCF, Area Light & Contact-Hardening."""
    kernel = PCF_KERNEL_3X3
    if pcf_samples <= 1:
        kernel = [(0.0, 0.0)]
    else:
        kernel = kernel[:pcf_samples]
    
    light_offsets = [(0.0, 0.0)]
    if light_radius > 1e-6 and light_samples > 1:
        light_offsets = []
        for i in range(light_samples):
            u, v = hammersley_2d(i, light_samples)
            phi = 2.0 * math.pi * u
            r = light_radius * math.sqrt(v)
            light_offsets.append((r * math.cos(phi), r * math.sin(phi)))
    
    # Orthonormalbasis für Light-Offsets (tangent space)
    lx, ly, lz = l_dir
    if abs(lz) < 0.9:
        up = (0.0, 0.0, 1.0)
    else:
        up = (0.0, 1.0, 0.0)
    tx = vec3_norm(vec3_cross(up, l_dir))
    ty = vec3_norm(vec3_cross(l_dir, tx))
    
    schatten_summe = 0.0
    total_taps = len(kernel) * len(light_offsets)
    
    for lx_off, ly_off in light_offsets:
        # Variierte Lichtrichtung für Area Light
        if lx_off != 0.0 or ly_off != 0.0:
            var_dir = vec3_add(l_dir, vec3_add(vec3_scale(tx, lx_off), vec3_scale(ty, ly_off)))
            var_dir = vec3_norm(var_dir)
        else:
            var_dir = l_dir
        
        for kx, ky in kernel:
            # Startpunkt mit PCF-Offset in Texel-Koordinaten
            sx = start[0] + kx * pcf_radius
            sy = start[1] + ky * pcf_radius
            sz = start[2]
            
            # Raymarching
            hit = False
            step_dist = max_dist / schritte
            for step in range(schritte):
                t = (step + 0.5) * step_dist
                px = sx + var_dir[0] * t
                py = sy + var_dir[1] * t
                pz = sz + var_dir[2] * t
                
                # Höhenfeld abfragen
                h = tk.get_bilinear(py, px) * z_skalierung
                
                # Slope-scaled Bias gegen Peter Panning
                ndotl = max(0.0, vec3_dot(tk.get_normal(py, px), var_dir))
                bias = OFFSET_BIAS * (1.0 + 0.5 * (1.0 - ndotl))
                
                if pz - bias <= h:
                    hit = True
                    break
            
            schatten_summe += 0.0 if hit else 1.0
    
    return schatten_summe / total_taps if total_taps > 0 else 1.0

# ─── Rendering-Pipeline ──────────────────────────────────────────────

def render_schattenbild(tk: Tiefenkarte,
                        l_dir: Vec3,
                        z_skalierung: float,
                        breite: int = 80,
                        hoehe: int = 40,
                        **params) -> List[str]:
    """Rendert ein ASCII-Schattenbild der Tiefenkarte."""
    l_dir_n = vec3_norm(l_dir)
    max_dist = max(tk.b, tk.h) * 1.5
    
    # Beleuchtungsrichtung für Shading (Lambert)
    light_vec = vec3_scale(l_dir_n, -1.0)  # Licht kommt ENTGEGEN der Schattenrichtung
    
    zeilen = []
    for iy in range(hoehe):
        y = (iy + 0.5) * tk.h / hoehe
        zeile = []
        for ix in range(breite):
            x = (ix + 0.5) * tk.b / breite
            h = tk.get_bilinear(y, x) * z_skalierung
            
            # Startpunkt knapp über Oberfläche
            start = (x, y, h + 0.01)
            
            # Schattenfaktor
            schatten = raymarch_schatten(tk, start, l_dir_n, max_dist, z_skalierung, **params)
            
            # Normalen für Diffuse Lighting
            n = tk.get_normal(y, x)
            diffuse = max(0.0, vec3_dot(n, light_vec))
            
            # Kombinieren: Schatten * Diffuse
            helligkeit = schatten * (0.3 + 0.7 * diffuse)
            
            # ASCII-Rampe
            if helligkeit > 0.85: ch = '█'
            elif helligkeit > 0.70: ch = '▓'
            elif helligkeit > 0.55: ch = '▒'
            elif helligkeit > 0.40: ch = '░'
            elif helligkeit > 0.25: ch = '·'
            else: ch = ' '
            zeile.append(ch)
        zeilen.append(''.join(zeile))
    return zeilen

# ─── Demo-Daten ──────────────────────────────────────────────────────

def demo_hoehenfeld() -> Tiefenkarte:
    """Erzeugt ein interessantes Test-Höhenfeld."""
    h, b = 64, 64
    daten = [[0.0]*b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            fx = (x - b*0.5) / (b*0.5)
            fy = (y - h*0.5) / (h*0.5)
            r = math.sqrt(fx*fx + fy*fy)
            # Mehrere Hügel + Rauschen
            val = 0.0
            val += 1.5 * math.exp(-r*r * 4.0)
            val += 0.8 * math.exp(-((fx-0.5)**2 + (fy+0.3)**2) * 10.0)
            val += 0.6 * math.exp(-((fx+0.4)**2 + (fy-0.4)**2) * 8.0)
            val += 0.3 * math.sin(fx * 12.0) * math.cos(fy * 10.0) * math.exp(-r*r * 2.0)
            val += 0.1 * math.sin(fx * 30.0) * math.sin(fy * 28.0)
            daten[y][x] = max(0.0, min(1.0, val))
    return Tiefenkarte(daten)


def demo_wellen() -> Tiefenkarte:
    h, b = 64, 64
    daten = [[0.0]*b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            fx = x / b * 4.0 * math.pi
            fy = y / h * 4.0 * math.pi
            val = 0.5 + 0.4 * math.sin(fx) * math.cos(fy)
            val += 0.1 * math.sin(2*fx) * math.cos(2*fy)
            daten[y][x] = max(0.0, min(1.0, val))
    return Tiefenkarte(daten)


def demo_schlucht() -> Tiefenkarte:
    h, b = 64, 64
    daten = [[0.0]*b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            fx = (x - b*0.5) / (b*0.5)
            fy = (y - h*0.5) / (h*0.5)
            # Schlucht in der Mitte
            val = 1.0 - 0.8 * math.exp(-fy*fy * 20.0)
            val += 0.3 * math.exp(-((fx-0.3)**2 + fy*fy) * 15.0)
            val += 0.2 * math.sin(fx * 8.0) * math.exp(-fy*fy * 5.0)
            daten[y][x] = max(0.0, min(1.0, val))
    return Tiefenkarte(daten)

# ─── Interaktion & Menü ──────────────────────────────────────────────

def sicher_input(prompt: str, default: str = '') -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print('\nTschüss! 👋')
        sys.exit(0)


def parse_float(s: str, default: float) -> float:
    try:
        return float(s)
    except ValueError:
        return default


def parse_int(s: str, default: int) -> int:
    try:
        return int(s)
    except ValueError:
        return default


def interaktiv(tk: Tiefenkarte):
    print('\n🎮 Interaktiver Modus – Leertaste+Enter für Defaults')
    params = {
        'schritte': 32,
        'pcf_radius': 0.6,
        'pcf_samples': 9,
        'light_radius': 0.0,
        'light_samples': 1,
        'z_skalierung': 1.0,
        'l_dir_x': -0.5,
        'l_dir_y': -0.3,
        'l_dir_z': 1.0,
    }
    while True:
        print('\n--- Parameter ---')
        for k, v in params.items():
            print(f'  {k}: {v}')
        print('  scene: 1=Hügel, 2=Wellen, 3=Schlucht')
        print('  render [enter] | q zum Beenden')
        cmd = sicher_input('> ').lower()
        if cmd in ('q', 'quit', 'exit'):
            break
        if cmd in ('1', '2', '3'):
            tk = [demo_hoehenfeld, demo_wellen, demo_schlucht][int(cmd)-1]()
            print(f'Szene {cmd} geladen.')
            continue
        if cmd == '':
            # Rendern
            l_dir = (params['l_dir_x'], params['l_dir_y'], params['l_dir_z'])
            print(f'\nRendering... ({80}x{40})')
            t0 = time.time()
            bild = render_schattenbild(tk, l_dir, params['z_skalierung'],
                schritte=params['schritte'],
                pcf_radius=params['pcf_radius'],
                pcf_samples=params['pcf_samples'],
                light_radius=params['light_radius'],
                light_samples=params['light_samples'],
            )
            dt = time.time() - t0
            for zeile in bild:
                print(zeile)
            print(f'\n⏱  {dt:.3f} s')
            continue
        # Parameter setzen
        parts = cmd.split()
        if len(parts) == 2 and parts[0] in params:
            key = parts[0]
            val = parts[1]
            if key in ('schritte', 'pcf_samples', 'light_samples'):
                params[key] = parse_int(val, params[key])
            else:
                params[key] = parse_float(val, params[key])
            print(f'{key} = {params[key]}')
        else:
            print('Unbekannt. Format: key value')


def demo_laufen(tk: Tiefenkarte):
    print('\n🎬 Demo-Sequenz – verschiedene Lichtwinkel & Settings')
    scenes = [
        ('Hügel (Punktlicht, hart)', demo_hoehenfeld(), (-0.5, -0.3, 1.0), 1.0,
         {'schritte': 24, 'pcf_samples': 1, 'light_radius': 0.0}),
        ('Hügel (PCF 3x3, weich)', demo_hoehenfeld(), (-0.5, -0.3, 1.0), 1.0,
         {'schritte': 32, 'pcf_radius': 0.8, 'pcf_samples': 9, 'light_radius': 0.0}),
        ('Hügel (Area Light r=0.15)', demo_hoehenfeld(), (-0.5, -0.3, 1.0), 1.0,
         {'schritte': 32, 'pcf_radius': 0.6, 'pcf_samples': 9, 'light_radius': 0.15, 'light_samples': 9}),
        ('Wellen (schräg, Area)', demo_wellen(), (-0.8, -0.1, 0.6), 0.8,
         {'schritte': 40, 'pcf_radius': 0.5, 'pcf_samples': 9, 'light_radius': 0.1, 'light_samples': 16}),
        ('Schlucht (steil, PCF)', demo_schlucht(), (0.0, -0.7, 0.7), 1.2,
         {'schritte': 32, 'pcf_radius': 0.7, 'pcf_samples': 9, 'light_radius': 0.0}),
    ]
    for name, scene_tk, l_dir, zsk, params in scenes:
        print(f'\n╔═══ {name} ═══╗')
        t0 = time.time()
        bild = render_schattenbild(scene_tk, l_dir, zsk, **params)
        dt = time.time() - t0
        for zeile in bild:
            print(zeile)
        print(f'╚═══ {dt:.3f} s ═══╝')
        sicher_input('Enter für nächsten… ')

# ─── Hauptprogramm ───────────────────────────────────────────────────

def main():
    print('╔══════════════════════════════════════╗')
    print('║ Schatten-Simulator – Teil 64        ║')
    print('║ Final Polish & Testlauf             ║')
    print('╚══════════════════════════════════════╝')
    
    tk = demo_hoehenfeld()
    
    while True:
        print('\nMenü:')
        print('  1 – Demo-Sequenz laufen lassen')
        print('  2 – Interaktiv parameterspielen')
        print('  3 – Beenden')
        wahl = sicher_input('Wahl (1/2/3): ')
        if wahl == '1':
            demo_laufen(tk)
        elif wahl == '2':
            interaktiv(tk)
        elif wahl == '3':
            print('Auf Wiedersehen! 🦤')
            break
        else:
            print('Bitte 1, 2 oder 3 eingeben.')

if __name__ == '__main__':
    main()