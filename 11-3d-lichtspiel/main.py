import math, sys, random, unicodedata, time, select

class ShaderParams:
    """Container für alle einstellbaren Shader‑Parameter mit Defaults."""
    def __init__(self):
        self.penumbra_breite = 0.15
        self.umbra_dunkelheit = 0.05
        self.falloff_exponent = 2.0
        self.falloff_start = 0.5
        self.blur_radius = 3
        self.ambient = 0.05
        self.volumetric_gain = 2.5
        self.gamma = 0.55
        self.scattering_coeff = 0.45
        self.absorption_coeff = 0.08
        self.mist_density = 0.22
        self.mist_height_falloff = 0.8
        self.color_temp = 3000.0
        self.jitter_strength = 0.12
        self.phase_g = 0.6
        self.noise_seed = 42
        self.march_steps = 24
        self.jitter_enabled = True
        self.specular_intensity = 0.6
        self.specular_power = 24.0
        self.specular_noise_scale = 0.5
        self.light_radius = 0.8
    def klonen(self):
        k = ShaderParams()
        k.__dict__.update(self.__dict__)
        return k

def _norm(s: str) -> str:
    return unicodedata.normalize('NFC', s).strip().lower()

def gauß_gewichte(kernel_radius: int) -> list:
    size = kernel_radius * 2 + 1
    sigma = kernel_radius / 2.0
    gewichte = []
    sum_g = 0.0
    for i in range(size):
        x = i - kernel_radius
        g = math.exp(-(x * x) / (2.0 * sigma * sigma))
        gewichte.append(g)
        sum_g += g
    return [g / sum_g for g in gewichte]

def box_blur_1d(puffer: list, gewichte: list, horizontal: bool = True) -> list:
    h, w = len(puffer), len(puffer[0])
    k_rad = len(gewichte) // 2
    ergebnis = [[0.0 for _ in range(w)] for __ in range(h)]
    if horizontal:
        for y in range(h):
            src = puffer[y]
            dst = ergebnis[y]
            for x in range(w):
                acc = 0.0
                for i, g in enumerate(gewichte):
                    xi = x - k_rad + i
                    if 0 <= xi < w:
                        acc += src[xi] * g
                dst[x] = acc
    else:
        for x in range(w):
            for y in range(h):
                acc = 0.0
                for i, g in enumerate(gewichte):
                    yi = y - k_rad + i
                    if 0 <= yi < h:
                        acc += puffer[yi][x] * g
                ergebnis[y][x] = acc
    return ergebnis

def henyey_greenstein(cos_theta: float, g: float) -> float:
    g2 = g * g
    denom = (1.0 + g2 - 2.0 * g * cos_theta) ** 1.5
    return (1.0 - g2) / (4.0 * math.pi * denom) if denom > 1e-6 else 1.0

def kelvin_to_rgb_factor(temp_k: float) -> tuple:
    t = temp_k / 100.0
    if t <= 66:
        r = 1.0
        g = 0.39008158 * math.log(t) - 0.63184144
    else:
        r = 1.29293619 * (t - 60.0) ** -0.13320476
        g = 1.12989086 * (t - 60.0) ** -0.07551485
    if t >= 66:
        b = 1.0
    elif t <= 19:
        b = 0.0
    else:
        b = 0.54320679 * math.log(t - 10.0) - 1.19625409
    g = max(0.01, g)
    return (r / g, 1.0, b / g)

def intensitaet_zu_ascii(wert: float, gamma: float = 0.6) -> str:
    if wert <= 0.0:
        return ' '
    w = min(1.0, max(0.0, wert)) ** gamma
    if w > 0.85:
        return '@'
    if w > 0.65:
        return '#'
    if w > 0.45:
        return '*'
    if w > 0.25:
        return '+'
    if w > 0.1:
        return '.'
    return ' '

def schattenfaktor_für_punkt(px, py, qx, qy, light_radius, bäume, params):
    dx, dy = px - qx, py - qy
    dist_lp = math.hypot(dx, dy)
    if dist_lp < 0.01:
        return 1.0
    ux, uy = dx / dist_lp, dy / dist_lp
    min_faktor = 1.0
    for bx, by, br in bäume:
        vx, vy = bx - qx, by - qy
        dist_lt = math.hypot(vx, vy)
        if dist_lt < 0.01:
            continue
        proj = vx * ux + vy * uy
        if proj <= 0.01 or proj >= dist_lp:
            continue
        abstand = abs(vx * uy - vy * ux)
        factor = dist_lp / dist_lt
        penumbra_radius = br * factor + light_radius * (factor - 1.0)
        umbra_radius = max(0.0, br * factor - light_radius * (factor - 1.0))
        if abstand >= penumbra_radius:
            continue
        if abstand <= umbra_radius:
            faktor = params.umbra_dunkelheit
        else:
            t = (abstand - umbra_radius) / (penumbra_radius - umbra_radius) if penumbra_radius > umbra_radius else 0.0
            t = max(0.0, min(1.0, t))
            faktor = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * t
        if faktor < min_faktor:
            min_faktor = faktor
    return min_faktor

def noise_2d(x, y, seed):
    n = int(x * 123.45) ^ int(y * 678.91) ^ seed
    n = (n ^ (n >> 13)) * 0x5bd1e995
    n = (n ^ (n >> 15)) * 0x5bd1e995
    n = n ^ (n >> 15)
    return (n & 0x7fffffff) / 0x7fffffff * 2.0 - 1.0

def noise_3d(x, y, z, seed):
    ix, iy, iz = int(math.floor(x)), int(math.floor(y)), int(math.floor(z))
    fx, fy, fz = x - ix, y - iy, z - iz
    def hash3d(ix, iy, iz):
        n = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ seed
        n = (n ^ (n >> 13)) * 0x5bd1e995
        n = (n ^ (n >> 15)) * 0x5bd1e995
        n = n ^ (n >> 15)
        return (n & 0x7fffffff) / 0x7fffffff
    u = fx * fx * (3.0 - 2.0 * fx)
    v = fy * fy * (3.0 - 2.0 * fy)
    w = fz * fz * (3.0 - 2.0 * fz)
    a = hash3d(ix, iy, iz)
    b = hash3d(ix + 1, iy, iz)
    c = hash3d(ix, iy + 1, iz)
    d = hash3d(ix + 1, iy + 1, iz)
    e = hash3d(ix, iy, iz + 1)
    f = hash3d(ix + 1, iy, iz + 1)
    g = hash3d(ix, iy + 1, iz + 1)
    h = hash3d(ix + 1, iy + 1, iz + 1)
    x1 = a + (b - a) * u
    x2 = c + (d - c) * u
    y1 = x1 + (x2 - x1) * v
    x3 = e + (f - e) * u
    x4 = g + (h - g) * u
    y2 = x3 + (x4 - x3) * v
    return y1 + (y2 - y1) * w

def erstelle_szene(params, breite=80, höhe=40):
    """Generiert Bäume und Lichtposition für den Park."""
    random.seed(params.noise_seed)
    bäume = []
    for _ in range(25):
        bx = random.uniform(2, breite - 3)
        by = random.uniform(2, höhe - 3)
        br = random.uniform(0.8, 1.8)
        bäume.append((bx, by, br))
    lx, ly = breite * 0.5, höhe * 0.3
    return bäume, (lx, ly)

def render_zbuffer(breite, höhe, bäume, licht_pos, params, frame):
    """Z-Buffer Renderer: Erstellt Tiefenpuffer und Licht-Sichtbarkeit."""
    lx, ly = licht_pos
    zbuffer = [[float('inf') for _ in range(breite)] for __ in range(höhe)]
    shadow_map = [[1.0 for _ in range(breite)] for __ in range(höhe)]
    
    for y in range(höhe):
        for x in range(breite):
            px = x + 0.5
            py = y + 0.5
            dist = math.hypot(px - lx, py - ly)
            zbuffer[y][x] = dist
            shadow_map[y][x] = schattenfaktor_für_punkt(px, py, lx, ly, params.light_radius, bäume, params)
    
    return zbuffer, shadow_map

def render_volumetric(breite, höhe, zbuffer, shadow_map, licht_pos, params, frame):
    """Berechnet volumetrisches Licht (God Rays) ohne Raymarching."""
    lx, ly = licht_pos
    bild = [[0.0 for _ in range(breite)] for __ in range(höhe)]
    
    for y in range(höhe):
        for x in range(breite):
            px = x + 0.5
            py = y + 0.5
            dx = px - lx
            dy = py - ly
            dist = math.hypot(dx, dy)
            if dist < 0.5:
                continue
            
            falloff = 1.0 / (1.0 + (dist * params.falloff_start) ** params.falloff_exponent)
            shadow = shadow_map[y][x]
            
            mist = params.mist_density * math.exp(-py * params.mist_height_falloff / höhe)
            noise_val = noise_3d(px * 0.1, py * 0.1, frame * 0.05, params.noise_seed)
            mist *= 1.0 + noise_val * params.jitter_strength
            
            cos_theta = -dy / dist if dist > 0 else 0
            phase = henyey_greenstein(cos_theta, params.phase_g)
            
            volumetric = falloff * shadow * mist * phase * params.volumetric_gain
            bild[y][x] = min(1.0, volumetric + params.ambient)
    
    if params.blur_radius > 0:
        gewichte = gauß_gewichte(params.blur_radius)
        bild = box_blur_1d(bild, gewichte, True)
        bild = box_blur_1d(bild, gewichte, False)
    
    return bild

def rendere_szene(bild, params):
    """Wendet Gamma-Korrektur an und konvertiert zu ASCII."""
    zeilen = []
    for row in bild:
        zeile = ''.join(intensitaet_zu_ascii(v, params.gamma) for v in row)
        zeilen.append(zeile)
    return '\n'.join(zeilen)

def main():
    params = ShaderParams()
    breite, höhe = 80, 40
    bäume, licht_pos = erstelle_szene(params, breite, höhe)
    
    print("3D-Lichtspiel – Herbstlicher Park (Z-Buffer Version)")
    print("Drücke Enter für nächsten Frame, 'q' zum Beenden.")
    print("Strg+C oder EOF beendet ebenfalls.\n")
    
    frame = 0
    try:
        while frame < 30:
            zbuffer, shadow_map = render_zbuffer(breite, höhe, bäume, licht_pos, params, frame)
            bild = render_volumetric(breite, höhe, zbuffer, shadow_map, licht_pos, params, frame)
            ascii_art = rendere_szene(bild, params)
            
            print(f'\033[2J\033[HFrame {frame}')
            print(ascii_art)
            print(f'Licht: ({licht_pos[0]:.1f}, {licht_pos[1]:.1f})  Bäume: {len(bäume)}')
            
            frame += 1
            time.sleep(0.15)
            
            if select.select([sys.stdin], [], [], 0)[0]:
                eingabe = sys.stdin.readline()
                if not eingabe or _norm(eingabe) in ('q', 'quit', 'exit'):
                    break
    except (EOFError, KeyboardInterrupt):
        pass
    
    print("\nDanke fürs Zuschauen! Der Dodo watschelt davon. 🦤")

if __name__ == '__main__':
    main()