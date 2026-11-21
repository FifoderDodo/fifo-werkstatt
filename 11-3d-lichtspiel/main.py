import math, sys, random, unicodedata, time

class ShaderParams:
    """Container für alle einstellbaren Shader-Parameter mit Defaults."""
    def __init__(self):
        self.penumbra_breite = 0.15
        self.umbra_dunkelheit = 0.05
        self.falloff_exponent = 2.0
        self.falloff_start = 0.5
        self.blur_radius = 3
        self.ambient = 0.02
        self.volumetric_gain = 1.2
        self.gamma = 0.6
        self.scattering_coeff = 0.35
        self.absorption_coeff = 0.12
        self.mist_density = 0.18
        self.mist_height_falloff = 0.8
        self.color_temp = 3200.0
        self.jitter_strength = 0.15
        self.phase_g = 0.6
        self.noise_seed = 42
        self.march_steps = 32
        self.jitter_enabled = True
        self.specular_intensity = 0.8
        self.specular_power = 32.0
        self.specular_noise_scale = 0.5
    def klonen(self):
        k = ShaderParams()
        k.__dict__.update(self.__dict__)
        return k

def _norm(s: str) -> str:
    return unicodedata.normalize('NFC', s).strip().lower()

def gauß_gewichte(kernel_radius: int) -> list:
    size = kernel_radius * 2 + 1
    gewicht = 1.0 / size
    return [gewicht] * size

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

def schattenfaktor_für_punkt(px, py, qx, qy, radius, bäume, params):
    dx, dy = px - qx, py - qy
    dist = math.hypot(dx, dy)
    if dist > radius or dist < 0.01:
        return 1.0
    ux, uy = dx / dist, dy / dist
    min_shadow = 1.0
    for bx, by, br in bäume:
        vx, vy = bx - qx, by - qy
        dqb = math.hypot(vx, vy)
        if dqb < 0.01:
            continue
        proj = vx * ux + vy * uy
        if proj <= 0.01 or proj >= dist:
            continue
        abstand = abs(vx * uy - vy * ux)
        if abstand >= br:
            continue
        shadow_radius = br * (dist / dqb)
        if shadow_radius <= 0:
            continue
        rand_faktor = abstand / shadow_radius
        pen, umb = params.penumbra_breite, params.umbra_dunkelheit
        if rand_faktor < 1.0 - pen:
            faktor = umb
        elif rand_faktor > 1.0 + pen:
            faktor = 1.0
        else:
            t = (rand_faktor - (1.0 - pen)) / (2.0 * pen)
            faktor = umb + (1.0 - umb) * t
        if faktor < min_shadow:
            min_shadow = faktor
    return min_shadow

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
    c000 = hash3d(ix, iy, iz)
    c100 = hash3d(ix + 1, iy, iz)
    c010 = hash3d(ix, iy + 1, iz)
    c110 = hash3d(ix + 1, iy + 1, iz)
    c001 = hash3d(ix, iy, iz + 1)
    c101 = hash3d(ix + 1, iy, iz + 1)
    c011 = hash3d(ix, iy + 1, iz + 1)
    c111 = hash3d(ix + 1, iy + 1, iz + 1)
    # trilineare interpolation
    def lerp(a, b, t):
        return a + t * (b - a)
    c00 = lerp(c000, c100, fx)
    c01 = lerp(c001, c101, fx)
    c10 = lerp(c010, c110, fx)
    c11 = lerp(c011, c111, fx)
    c0 = lerp(c00, c10, fy)
    c1 = lerp(c01, c11, fy)
    return lerp(c0, c1, fz)

def render(params: ShaderParams, bäume, licht_pos, width=80, height=24):
    img = [[0.0 for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(width):
            # Normalisierte Bildschirmkoordinaten [-1,1]
            nx = (x / (width - 1)) * 2 - 1
            ny = (y / (height - 1)) * 2 - 1
            # Simple ray direction (orthogonal)
            ray_dir = (0, 0, -1)
            # Position im Raum (z=0)
            pos = (nx, ny, 0)
            # Grundbeleuchtung
            intensity = params.ambient
            # Volumetrische Streuung (einfach)
            dist = math.hypot(nx - licht_pos[0], ny - licht_pos[1])
            falloff = 1.0 / (params.falloff_start + dist ** params.falloff_exponent)
            intensity += params.volumetric_gain * falloff
            # Schatten durch Bäume
            shadow = schattenfaktor_für_punkt(nx, ny, licht_pos[0], licht_pos[1], 0.5, bäume, params)
            intensity *= shadow
            # Blinn-Phong Specular mit Rauschen
            if params.specular_intensity > 0:
                # Halbvektor zwischen Licht und Auge (einfaches orthogonales Auge)
                h = ((licht_pos[0] - nx) * 0.5, (licht_pos[1] - ny) * 0.5, 0)
                hlen = math.hypot(h[0], h[1]) + 1e-6
                ndoth = max(0.0, (h[0] / hlen))
                spec = (ndoth ** params.specular_power) * params.specular_intensity
                # noise modulation
                n = noise_3d(nx * params.specular_noise_scale,
                             ny * params.specular_noise_scale,
                             0.0,
                             params.noise_seed)
                spec *= (0.5 + 0.5 * n)
                intensity += spec
            img[y][x] = intensity
    # Apply optional blur
    if params.blur_radius > 0:
        w = gauß_gewichte(params.blur_radius)
        img = box_blur_1d(img, w, True)
        img = box_blur_1d(img, w, False)
    # ASCII output
    lines = []
    for row in img:
        line = ''.join(intensitaet_zu_ascii(v, params.gamma) for v in row)
        lines.append(line)
    return '\n'.join(lines)

def menu(params: ShaderParams):
    options = [
        ('Penumbra Breite', 'penumbra_breite'),
        ('Umbra Dunkelheit', 'umbra_dunkelheit'),
        ('Falloff Exponent', 'falloff_exponent'),
        ('Falloff Start', 'falloff_start'),
        ('Blur Radius', 'blur_radius'),
        ('Ambient', 'ambient'),
        ('Volumetric Gain', 'volumetric_gain'),
        ('Gamma', 'gamma'),
        ('Scattering Coeff', 'scattering_coeff'),
        ('Absorption Coeff', 'absorption_coeff'),
        ('Mist Density', 'mist_density'),
        ('Mist Height Falloff', 'mist_height_falloff'),
        ('Color Temp (K)', 'color_temp'),
        ('Jitter Strength', 'jitter_strength'),
        ('Phase g', 'phase_g'),
        ('Noise Seed', 'noise_seed'),
        ('March Steps', 'march_steps'),
        ('Jitter Enabled', 'jitter_enabled'),
        ('Specular Intensity', 'specular_intensity'),
        ('Specular Power', 'specular_power'),
        ('Specular Noise Scale', 'specular_noise_scale'),
    ]
    while True:
        print('\n--- Parameter Menu ---')
        for i, (name, attr) in enumerate(options, 1):
            val = getattr(params, attr)
            print(f"{i}) {name}: {val}")
        print('R) Rendern')
        print('Q) Beenden')
        try:
            choice = input('Wahl: ').strip().lower()
        except EOFError:
            print('\nEOF erreicht, Programm beendet.')
            sys.exit(0)
        if choice == 'q':
            sys.exit(0)
        if choice == 'r':
            # Beispielbäume und Lichtposition
            bäume = [(-0.4, 0.2, 0.08), (0.3, -0.1, 0.07), (0.0, 0.5, 0.09)]
            licht = (0.0, 0.8)
            print(render(params, bäume, licht))
            continue
        if not choice.isdigit():
            continue
        idx = int(choice) - 1
        if 0 <= idx < len(options):
            _, attr = options[idx]
            cur = getattr(params, attr)
            new = input(f'Neuer Wert für {attr} (aktuell {cur}): ')
            if isinstance(cur, bool):
                setattr(params, attr, new.lower() in ('true', '1', 'yes', 'y'))
            elif isinstance(cur, int):
                try:
                    setattr(params, attr, int(new))
                except ValueError:
                    pass
            else:
                try:
                    setattr(params, attr, float(new))
                except ValueError:
                    pass

if __name__ == '__main__':
    params = ShaderParams()
    menu(params)