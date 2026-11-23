import math, sys, random, unicodedata, time

class ShaderParams:
    """Container für alle einstellbaren Shader-Parameter mit Defaults."""
    def __init__(self):
        self.penumbra_breite = 0.15
        self.umbra_dunkelheit = 0.05
        self.falloff_exponent = 2.0
        self.falloff_start = 0.5
        self.blur_radius = 2
        self.ambient = 0.08
        self.volumetric_gain = 2.4
        self.gamma = 0.6
        self.scattering_coeff = 0.45
        self.absorption_coeff = 0.08
        self.mist_density = 0.22
        self.mist_height_falloff = 0.8
        self.color_temp = 3200.0
        self.jitter_strength = 0.10
        self.phase_g = 0.55
        self.noise_seed = 42
        self.march_steps = 10
        self.jitter_enabled = True
        self.specular_intensity = 0.7
        self.specular_power = 18.0
        self.light_radius = 0.7
        self.vibrancy = 1.25
        self.depth_shading_wrap = 0.35
        # Neu: Bloom / Leuchteffekt
        self.bloom_threshold = 0.6
        self.bloom_intensity = 0.45
        self.bloom_radius = 3
        # Neu: Raymarching-Optimierung
        self.adaptive_steps = True
        self.min_step_factor = 0.3
        self.max_step_factor = 2.0
        self.early_exit_threshold = 0.005

    def klonen(self):
        k = ShaderParams()
        k.__dict__.update(self.__dict__)
        return k

def _norm(s: str) -> str:
    return unicodedata.normalize('NFC', s).strip().lower()

def gauß_gewichte(kernel_radius: int) -> list:
    if kernel_radius <= 0:
        return [1.0]
    size = kernel_radius * 2 + 1
    sigma = max(0.5, kernel_radius / 2.0)
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
                    xi = max(0, min(w - 1, x - k_rad + i))
                    acc += src[xi] * g
                dst[x] = acc
    else:
        for x in range(w):
            for y in range(h):
                acc = 0.0
                for i, g in enumerate(gewichte):
                    yi = max(0, min(h - 1, y - k_rad + i))
                    acc += puffer[yi][x] * g
                ergebnis[y][x] = acc
    return ergebnis

def henyey_greenstein(cos_theta: float, g: float) -> float:
    cos_t = max(-1.0, min(1.0, cos_theta))
    g2 = g * g
    denom = (1.0 + g2 - 2.0 * g * cos_t) ** 1.5
    return (1.0 - g2) / (4.0 * math.pi * denom) if denom > 1e-5 else 1.0

def kelvin_to_rgb_factor(temp_k: float) -> tuple:
    t = temp_k / 100.0
    if t <= 66:
        r = 1.0
        g = 0.39008158 * math.log(max(1.0, t)) - 0.63184144
    else:
        r = 1.29293619 * (max(1.0, t - 60.0)) ** -0.13320476
        g = 1.12989086 * (max(1.0, t - 60.0)) ** -0.07551485
    if t >= 66:
        b = 1.0
    elif t <= 19:
        b = 0.0
    else:
        b = 0.54320679 * math.log(max(1.0, t - 10.0)) - 1.19625409
    return (max(0.05, r), max(0.05, g), max(0.05, b))

def intensitaet_zu_ascii(wert: float, gamma: float = 0.6) -> str:
    if wert <= 0.0:
        return ' '
    w = min(1.0, max(0.0, wert)) ** gamma
    rampe = " .:-=+*#%@"
    idx = int(w * (len(rampe) - 1))
    return rampe[max(0, min(len(rampe) - 1, idx))]

def noise_3d(x, y, z, seed):
    ix, iy, iz = int(math.floor(x)), int(math.floor(y)), int(math.floor(z))
    fx, fy, fz = x - ix, y - iy, z - iz
    def h(ix, iy, iz):
        n = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ seed
        n = (n ^ (n >> 13)) * 0x5bd1e995
        n = (n ^ (n >> 15)) * 0x5bd1e995
        return ((n ^ (n >> 15)) & 0x7fffffff) / 2147483647.0
    u = fx * fx * (3.0 - 2.0 * fx)
    v = fy * fy * (3.0 - 2.0 * fy)
    w = fz * fz * (3.0 - 2.0 * fz)
    a = h(ix, iy, iz)
    b = h(ix + 1, iy, iz)
    c = h(ix, iy + 1, iz)
    d = h(ix + 1, iy + 1, iz)
    e = h(ix, iy, iz + 1)
    f = h(ix + 1, iy, iz + 1)
    g_val = h(ix, iy + 1, iz + 1)
    h_val = h(ix + 1, iy + 1, iz + 1)
    x1 = a + (b - a) * u
    x2 = c + (d - c) * u
    y1 = x1 + (x2 - x1) * v
    x3 = e + (f - e) * u
    x4 = g_val + (h_val - g_val) * u
    y2 = x3 + (x4 - x3) * v
    return y1 + (y2 - y1) * w

def mist_dichte(pos, params):
    x, y, z = pos
    if z < 0.0:
        return 0.0
    basis = params.mist_density * math.exp(-z * params.mist_height_falloff)
    turbulenz = noise_3d(x * 0.45, y * 0.45, z * 0.25, params.noise_seed)
    return max(0.0, basis * (0.65 + 0.7 * turbulenz))

def dichte_gradient(pos, params, eps=0.1):
    px, py, pz = pos
    dx = mist_dichte((px + eps, py, pz), params) - mist_dichte((px - eps, py, pz), params)
    dy = mist_dichte((px, py + eps, pz), params) - mist_dichte((px, py - eps, pz), params)
    dz = mist_dichte((px, py, pz + eps), params) - mist_dichte((px, py, pz - eps), params)
    l = math.sqrt(dx * dx + dy * dy + dz * dz)
    if l < 1e-5:
        return (0.0, 0.0, 1.0)
    return (-dx / l, -dy / l, -dz / l)

def schattenfaktor_3d(pos, light_pos, baeume, params):
    px, py, pz = pos
    lx, ly, lz = light_pos
    vx, vy, vz = lx - px, ly - py, lz - pz
    dist_light = math.sqrt(vx * vx + vy * vy + vz * vz)
    if dist_light < 0.05:
        return 1.0
    ux, uy, uz = vx / dist_light, vy / dist_light, vz / dist_light
    min_f = 1.0
    for bx, by, br, bh in baeume:
        dx, dy = bx - px, by - py
        proj = dx * ux + dy * uy
        if 0.2 < proj < dist_light:
            cx = px + ux * proj
            cy = py + uy * proj
            cz = pz + uz * proj
            if 0.0 <= cz <= bh:
                dist_xy = math.sqrt((cx - bx) ** 2 + (cy - by) ** 2)
                if dist_xy < br:
                    # harter Schatten mit Penumbra
                    rand = br - dist_xy
                    penumbra = params.penumbra_breite * br
                    if rand < penumbra:
                        f = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * (rand / penumbra)
                    else:
                        f = params.umbra_dunkelheit
                    min_f = min(min_f, f)
    return min_f

def raymarch_pixel(px, py, cam_pos, cam_dir, light_pos, baeume, params, t):
    """Raymarching für einen Pixel. Gibt Intensität zurück."""
    # Startpunkt etwas vor der Kamera
    ox, oy, oz = cam_pos
    dx, dy, dz = cam_dir
    # Jitter für Temporal AA
    if params.jitter_enabled:
        jitter = (random.random() - 0.5) * 2.0 * params.jitter_strength
        ox += jitter * 0.01
        oy += jitter * 0.01
    # Adaptive Step-Größe
    max_dist = 30.0
    steps = params.march_steps
    if params.adaptive_steps:
        # Grobe Schätzung: weniger Steps bei dichterem Nebel
        avg_density = mist_dichte((ox, oy, oz), params)
        steps = int(steps * (params.min_step_factor + (1.0 - avg_density) * (params.max_step_factor - params.min_step_factor)))
        steps = max(4, min(params.march_steps * 2, steps))
    step_size = max_dist / steps
    accumulated = 0.0
    transmittance = 1.0
    for i in range(steps):
        # Position entlang des Strahls
        dist = i * step_size
        x = ox + dx * dist
        y = oy + dy * dist
        z = oz + dz * dist
        if z < -0.5:  # unter Boden
            break
        density = mist_dichte((x, y, z), params)
        if density < 1e-4:
            continue
        # Schattenfaktor
        shadow = schattenfaktor_3d((x, y, z), light_pos, baeume, params)
        # Streuung (Henyey-Greenstein)
        # Lichtrichtung vom Sample zum Licht
        lx, ly, lz = light_pos
        vx, vy, vz = lx - x, ly - y, lz - z
        dist_light = math.sqrt(vx * vx + vy * vy + vz * vz)
        if dist_light < 0.01:
            continue
        lx, ly, lz = vx / dist_light, vy / dist_light, vz / dist_light
        cos_theta = dx * lx + dy * ly + dz * lz
        phase = henyey_greenstein(cos_theta, params.phase_g)
        # Falloff
        falloff = 1.0 / (1.0 + (dist_light * params.falloff_start) ** params.falloff_exponent)
        # Volumetrischer Beitrag
        contrib = density * phase * falloff * shadow * params.scattering_coeff
        # Absorption
        transmittance *= math.exp(-density * params.absorption_coeff * step_size)
        accumulated += contrib * transmittance * step_size
        # Early Exit
        if transmittance < params.early_exit_threshold:
            break
    # Ambient + Volumetric Gain
    accumulated = (accumulated * params.volumetric_gain + params.ambient) * transmittance
    # Specular Highlights (einfache Approximation)
    # Wir nutzen den Gradient der Dichte als Normalen-Annäherung
    grad = dichte_gradient((ox + dx * max_dist * 0.5, oy + dy * max_dist * 0.5, oz + dz * max_dist * 0.5), params)
    gx, gy, gz = grad
    spec = max(0.0, dx * gx + dy * gy + dz * gz) ** params.specular_power
    accumulated += spec * params.specular_intensity
    return accumulated

def render_frame(w, h, cam_pos, cam_dir, light_pos, baeume, params, t):
    """Rendert einen Frame in einen Float-Puffer."""
    buffer = [[0.0 for _ in range(w)] for __ in range(h)]
    # Einfache Perspektive: FOV ~ 90 Grad
    fov = math.pi / 2.0
    aspect = w / h
    for y in range(h):
        for x in range(w):
            # Normalisierte Koordinaten -1..1
            nx = (x + 0.5) / w * 2.0 - 1.0
            ny = (y + 0.5) / h * 2.0 - 1.0
            nx *= aspect
            # Ray Direction
            dx = nx * math.tan(fov * 0.5)
            dy = ny * math.tan(fov * 0.5)
            dz = -1.0  # Blickrichtung -Z
            length = math.sqrt(dx * dx + dy * dy + dz * dz)
            dx, dy, dz = dx / length, dy / length, dz / length
            val = raymarch_pixel(x, y, cam_pos, (dx, dy, dz), light_pos, baeume, params, t)
            buffer[y][x] = val
    return buffer

def bloom_pass(buffer, params):
    """Extrahiert helle Bereiche, blurt sie und addiert sie zurück."""
    h, w = len(buffer), len(buffer[0])
    # Threshold
    bloom_src = [[0.0 for _ in range(w)] for __ in range(h)]
    for y in range(h):
        for x in range(w):
            val = buffer[y][x]
            if val > params.bloom_threshold:
                bloom_src[y][x] = (val - params.bloom_threshold) * params.bloom_intensity
    # Gaussian Blur (separable)
    weights = gauß_gewichte(params.bloom_radius)
    bloom_blur = box_blur_1d(bloom_src, weights, horizontal=True)
    bloom_blur = box_blur_1d(bloom_blur, weights, horizontal=False)
    # Add back
    for y in range(h):
        for x in range(w):
            buffer[y][x] += bloom_blur[y][x]
    return buffer

def apply_tonemap(buffer, params):
    """Gamma, Vibrancy, Farbtemperatur (hier nur Helligkeit)."""
    h, w = len(buffer), len(buffer[0])
    r_factor, g_factor, b_factor = kelvin_to_rgb_factor(params.color_temp)
    # Da ASCII monochrom: mische zu Luminanz
    lum_factor = 0.2126 * r_factor + 0.7152 * g_factor + 0.0722 * b_factor
    for y in range(h):
        for x in range(w):
            val = buffer[y][x]
            # Vibrancy: einfache Sättigungserhöhung (hier nur Kontrast)
            val = val * params.vibrancy
            # Gamma
            val = val ** params.gamma
            # Farbtemperatur als Helligkeitsmodulation
            val *= lum_factor
            buffer[y][x] = min(1.0, max(0.0, val))
    return buffer

def buffer_to_ascii(buffer, params):
    h, w = len(buffer), len(buffer[0])
    lines = []
    for y in range(h):
        line = ''.join(intensitaet_zu_ascii(buffer[y][x], params.gamma) for x in range(w))
        lines.append(line)
    return '\n'.join(lines)

def main():
    print("🦤 Fifo's 3D-Lichtspiel – Herbstpark Edition")
    print("Drücke Enter für nächsten Frame, 'q' zum Beenden, oder ändere Parameter (z.B. 'mist_density 0.3').")
    print("Verfügbar: " + ', '.join([k for k in ShaderParams().__dict__.keys() if not k.startswith('_')]))
    
    params = ShaderParams()
    w, h = 80, 40
    
    # Szene: Bäume als (x, y, radius, height)
    random.seed(12345)
    baeume = []
    for _ in range(12):
        bx = random.uniform(-10, 10)
        by = random.uniform(-10, 10)
        br = random.uniform(0.4, 1.0)
        bh = random.uniform(2.0, 5.0)
        baeume.append((bx, by, br, bh))
    
    cam_pos = (0.0, -8.0, 1.8)
    light_angle = 0.0
    frame = 0
    max_inputs = 20
    inputs_used = 0
    
    try:
        while inputs_used < max_inputs:
            t = time.time()
            # Kamera leicht schweben
            cam_x = cam_pos[0] + math.sin(t * 0.1) * 0.3
            cam_y = cam_pos[1] + math.cos(t * 0.07) * 0.2
            cam_z = cam_pos[2] + math.sin(t * 0.05) * 0.1
            current_cam = (cam_x, cam_y, cam_z)
            # Licht umherwandern
            light_r = 6.0
            light_angle += 0.015
            light_pos = (math.sin(light_angle) * light_r,
                         math.cos(light_angle) * light_r,
                         4.0 + math.sin(t * 0.2) * 0.5)
            # Blickrichtung: zum Licht hin (leicht versetzt)
            dx = light_pos[0] - current_cam[0]
            dy = light_pos[1] - current_cam[1]
            dz = light_pos[2] - current_cam[2]
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            cam_dir = (dx/dist, dy/dist, dz/dist)
            
            buffer = render_frame(w, h, current_cam, cam_dir, light_pos, baeume, params, t)
            buffer = bloom_pass(buffer, params)
            buffer = apply_tonemap(buffer, params)
            ascii_art = buffer_to_ascii(buffer, params)
            
            print(f'\nFrame {frame} | Licht: ({light_pos[0]:.1f},{light_pos[1]:.1f},{light_pos[2]:.1f}) | Cam: ({current_cam[0]:.1f},{current_cam[1]:.1f},{current_cam[2]:.1f})')
            print(ascii_art)
            
            try:
                inp = input('> ').strip()
            except EOFError:
                print('\n🦤 Tschüss, der Dodo schläft weiter.')
                break
            
            if not inp:
                frame += 1
                continue
            if _norm(inp) in ('q', 'quit', 'exit'):
                print('🦤 Gute Nacht!')
                break
            # Parameter setzen
            parts = inp.split()
            if len(parts) == 2:
                key, val_str = parts[0], parts[1]
                if hasattr(params, key):
                    try:
                        val = float(val_str)
                        setattr(params, key, val)
                        print(f'✅ {key} = {val}')
                    except ValueError:
                        print(f'❌ Ungültiger Wert für {key}')
                else:
                    print(f'❌ Unbekannter Parameter: {key}')
            else:
                print('❓ Befehl nicht verstanden. Format: <param> <wert> oder Enter für nächsten Frame.')
            inputs_used += 1
            frame += 1
    except KeyboardInterrupt:
        print('\n🦤 Aufgewacht!')

if __name__ == '__main__':
    main()