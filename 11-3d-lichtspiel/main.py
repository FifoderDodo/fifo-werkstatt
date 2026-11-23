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
        self.march_steps = 12  # reduziert für bessere Performance
        self.jitter_enabled = True
        self.specular_intensity = 0.6
        self.specular_power = 24.0
        self.specular_noise_scale = 0.5
        self.light_radius = 0.8
        self.vibrancy = 1.2
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

def mist_dichte(pos, params):
    """Mist-Dichte mit Höhenabfall und 3D-Noise."""
    x, y, z = pos
    basis = params.mist_density * math.exp(-z * params.mist_height_falloff)
    n = noise_3d(x * 0.5, y * 0.5, z * 0.3, params.noise_seed + 1)
    return basis * (1.0 + n * 0.4)

def dichte_gradient(pos, params, eps=0.08):
    """Optimierter Dichte-Gradient für Normalen: zentrale Differenzen mit größerem eps für Stabilität."""
    x, y, z = pos
    # Größeres eps = weniger Rauschen, stabilere Normalen
    dx = mist_dichte((x + eps, y, z), params) - mist_dichte((x - eps, y, z), params)
    dy = mist_dichte((x, y + eps, z), params) - mist_dichte((x, y - eps, z), params)
    dz = mist_dichte((x, y, z + eps), params) - mist_dichte((x, y, z - eps), params)
    return (dx * 0.5 / eps, dy * 0.5 / eps, dz * 0.5 / eps)

def erstelle_szene(params, breite=80, höhe=40):
    """Generiert Bäume und Lichtposition für den Park."""
    random.seed(params.noise_seed)
    bäume = []
    for _ in range(12):
        bx = random.uniform(0.1, 0.9)
        by = random.uniform(0.1, 0.9)
        br = random.uniform(0.04, 0.08)
        bäume.append((bx, by, br))
    # Lichtposition: leicht versetzt oben mittig
    lx, ly, lz = 0.5, 0.5, 1.2
    return bäume, (lx, ly, lz)

def raymarch_volumetric(px, py, bäume, light_pos, params, breite, höhe):
    """Volumetric Raymarching mit optimiertem Normalen-Gradienten."""
    lx, ly, lz = light_pos
    # View direction: von Kamera (0.5, 0.5, -1) zum Pixel
    vx = (px / breite - 0.5) * 1.6
    vy = (py / höhe - 0.5) * 1.6
    vz = 1.0
    vlen = math.hypot(vx, math.hypot(vy, vz))
    vx, vy, vz = vx / vlen, vy / vlen, vz / vlen
    
    # Light direction zum Pixel
    px_w = px / breite
    py_w = py / höhe
    ldx = px_w - lx
    ldy = py_w - ly
    ldz = 0.0 - lz
    ldist = math.hypot(ldx, math.hypot(ldy, ldz))
    ldx, ldy, ldz = ldx / ldist, ldy / ldist, ldz / ldist
    
    # Shadow factor für diesen Pixel
    shadow = schattenfaktor_für_punkt(px_w, py_w, lx, ly, params.light_radius, bäume, params)
    
    # Raymarching
    steps = params.march_steps
    max_dist = 3.0
    step_size = max_dist / steps
    
    # Jitter für Temporal Stability
    jitter = 0.0
    if params.jitter_enabled:
        jitter = noise_2d(px * 0.1, py * 0.1, params.noise_seed) * params.jitter_strength * step_size
    
    accum_r = accum_g = accum_b = 0.0
    transmittance = 1.0
    
    # Farbtemperatur
    cr, cg, cb = kelvin_to_rgb_factor(params.color_temp)
    
    for i in range(steps):
        t = (i + 0.5) * step_size + jitter
        sx = 0.5 + vx * t
        sy = 0.5 + vy * t
        sz = -1.0 + vz * t
        
        if sz > 1.0:  # Über Boden hinaus
            break
            
        density = mist_dichte((sx, sy, sz), params)
        if density < 1e-4:
            continue
        
        # Optimierter Normalen-Gradient (größeres eps, weniger Samples)
        nx, ny, nz = dichte_gradient((sx, sy, sz), params, eps=0.12)
        nlen = math.hypot(nx, math.hypot(ny, nz))
        if nlen > 1e-6:
            nx, ny, nz = nx / nlen, ny / nlen, nz / nlen
        else:
            nx, ny, nz = 0.0, 0.0, 1.0
        
        # Phase function
        cos_theta = -(vx * ldx + vy * ldy + vz * ldz)
        phase = henyey_greenstein(cos_theta, params.phase_g)
        
        # Scattering
        scatter = density * params.scattering_coeff * phase * shadow
        absorption = density * params.absorption_coeff
        extinction = scatter + absorption
        
        if extinction * step_size > 0.01:
            transmittance *= math.exp(-extinction * step_size)
        
        if transmittance < 0.001:
            break
            
        light_contrib = scatter * transmittance * params.volumetric_gain
        accum_r += light_contrib * cr
        accum_g += light_contrib * cg
        accum_b += light_contrib * cb
    
    # Ambient + Specular Highlights auf Nebel
    spec = 0.0
    if nlen > 1e-6:
        # Specular反射方向
        rx = 2.0 * (vx * nx + vy * ny + vz * nz) * nx - vx
        ry = 2.0 * (vx * nx + vy * ny + vz * nz) * ny - vy
        rz = 2.0 * (vx * nx + vy * ny + vz * nz) * nz - vz
        spec_cos = max(0.0, rx * ldx + ry * ldy + rz * ldz)
        spec = params.specular_intensity * (spec_cos ** params.specular_power) * shadow
        # Noise auf Specular für organisches Aussehen
        spec_noise = noise_3d(sx * params.specular_noise_scale, sy * params.specular_noise_scale, sz * params.specular_noise_scale, params.noise_seed + 2)
        spec *= 1.0 + spec_noise * 0.3
    
    accum_r += params.ambient * cr + spec * cr
    accum_g += params.ambient * cg + spec * cg
    accum_b += params.ambient * cb + spec * cb
    
    # Vibrancy (Sättigung)
    if params.vibrancy != 1.0:
        avg = (accum_r + accum_g + accum_b) / 3.0
        accum_r = avg + (accum_r - avg) * params.vibrancy
        accum_g = avg + (accum_g - avg) * params.vibrancy
        accum_b = avg + (accum_b - avg) * params.vibrancy
    
    return accum_r, accum_g, accum_b

def render_frame(params, breite=80, höhe=40):
    """Rendert einen Frame als ASCII mit Farbcodes."""
    bäume, light_pos = erstelle_szene(params, breite, höhe)
    raw = [[(0.0, 0.0, 0.0) for _ in range(breite)] for __ in range(höhe)]
    
    for y in range(höhe):
        for x in range(breite):
            raw[y][x] = raymarch_volumetric(x, y, bäume, light_pos, params, breite, höhe)
    
    # Blur für weichere Lichtkegel
    if params.blur_radius > 0:
        gewichte = gauß_gewichte(params.blur_radius)
        # Split channels
        r_buf = [[raw[y][x][0] for x in range(breite)] for y in range(höhe)]
        g_buf = [[raw[y][x][1] for x in range(breite)] for y in range(höhe)]
        b_buf = [[raw[y][x][2] for x in range(breite)] for y in range(höhe)]
        r_buf = box_blur_1d(box_blur_1d(r_buf, gewichte, True), gewichte, False)
        g_buf = box_blur_1d(box_blur_1d(g_buf, gewichte, True), gewichte, False)
        b_buf = box_blur_1d(box_blur_1d(b_buf, gewichte, True), gewichte, False)
        for y in range(höhe):
            for x in range(breite):
                raw[y][x] = (r_buf[y][x], g_buf[y][x], b_buf[y][x])
    
    # Gamma & ASCII
    ascii_frame = []
    for y in range(höhe):
        line = ''
        for x in range(breite):
            r, g, b = raw[y][x]
            # Luminance
            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
            ch = intensitaet_zu_ascii(lum, params.gamma)
            # ANSI Truecolor
            ri = int(min(255, max(0, r * 255)))
            gi = int(min(255, max(0, g * 255)))
            bi = int(min(255, max(0, b * 255)))
            line += f'\033[38;2;{ri};{gi};{bi}m{ch}\033[0m'
        ascii_frame.append(line)
    return '\n'.join(ascii_frame)

def parameter_menü(params):
    """Interaktives Menü für Shader-Parameter."""
    print('\n=== 3D-Lichtspiel Parameter ===')
    attrs = [a for a in dir(params) if not a.startswith('_') and not callable(getattr(params, a))]
    for i, a in enumerate(attrs):
        print(f'  {i+1:2d}. {a} = {getattr(params, a)}')
    print('  0. Weiter zum Rendering')
    print('  q. Beenden')
    try:
        choice = input('Wähle Parameter (Nummer) oder Enter für Defaults: ').strip()
    except EOFError:
        return False
    if not choice:
        return True
    if choice.lower() == 'q':
        return False
    try:
        idx = int(choice) - 1
        if idx == -1:
            return True
        if 0 <= idx < len(attrs):
            attr = attrs[idx]
            current = getattr(params, attr)
            try:
                new_val = input(f'  Neuer Wert für {attr} [{current}]: ').strip()
                if new_val:
                    if isinstance(current, int):
                        setattr(params, attr, int(new_val))
                    elif isinstance(current, float):
                        setattr(params, attr, float(new_val))
                    elif isinstance(current, bool):
                        setattr(params, attr, new_val.lower() in ('true', '1', 'yes', 'ja'))
                    else:
                        setattr(params, attr, new_val)
            except EOFError:
                return False
    except ValueError:
        pass
    return True

def main():
    print('🍂 3D-Lichtspiel – Herbstlicher Park mit volumetrischem Licht')
    print('    Part 56: Optimierter Dichte-Gradient für Normalen (eps=0.12)\n')
    params = ShaderParams()
    
    while parameter_menü(params):
        pass
    
    try:
        breite = int(input('Breite [80]: ') or '80')
        höhe = int(input('Höhe [40]: ') or '40')
        frames = int(input('Anzahl Frames (1=single) [1]: ') or '1')
    except EOFError:
        breite, höhe, frames = 80, 40, 1
    
    print('\nRendering...')
    start = time.time()
    for f in range(frames):
        if frames > 1:
            # Leichte Animation: Lichtposition und Seed variieren
            params.noise_seed += 1
            params.color_temp = 3000 + 500 * math.sin(f * 0.3)
        frame = render_frame(params, breite, höhe)
        print('\033[H\033[J')  # Clear screen
        print(frame)
        print(f'\nFrame {f+1}/{frames} | Zeit: {time.time()-start:.2f}s')
        if frames > 1:
            time.sleep(0.08)
    print('\nFertig. Tschüss! 🦤')

if __name__ == '__main__':
    main()