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
        self.bloom_threshold = 0.6
        self.bloom_intensity = 0.45
        self.bloom_radius = 2
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
    rampe = " .:'-=+*#%@"
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
    """Berechnet den Schattenfaktor (0..1) für einen Punkt.
    Penumbra wird mit einer linearen Interpolation über die Breite
    des Lichtkegels modelliert."""
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
            cz = pz + uz * proj
            if 0.0 <= cz <= bh:
                # Kernschatten: sofort 0
                return 0.0
            # Penumbra: Abstand zum Baumstamm bestimmen
            horiz_dist = math.sqrt(dx * dx + dy * dy - proj * proj)
            penumbra = max(0.0, (horiz_dist - br) / params.penumbra_breite)
            min_f = min(min_f, 1.0 - penumbra)
    return min_f

def ray_march(orig, dir, params, light_pos, baeume, max_dist=20.0):
    step = max_dist / params.march_steps
    t = 0.0
    intensity = 0.0
    while t < max_dist:
        pos = (orig[0] + dir[0] * t, orig[1] + dir[1] * t, orig[2] + dir[2] * t)
        dens = mist_dichte(pos, params)
        if dens > 0.0:
            shade = schattenfaktor_3d(pos, light_pos, baeume, params)
            scattering = dens * params.scattering_coeff * shade
            intensity += scattering * math.exp(-params.absorption_coeff * t)
        t += step
    return intensity * params.volumetric_gain + params.ambient

def render_frame(width, height, cam_pos, cam_dir, params, light_pos, baeume):
    aspect = width / height
    fov = math.radians(60)
    scale = math.tan(fov * 0.5)
    buffer = []
    for y in range(height):
        row = []
        for x in range(width):
            ndc_x = (2 * (x + 0.5) / width - 1) * aspect * scale
            ndc_y = (1 - 2 * (y + 0.5) / height) * scale
            ray_dir = (ndc_x, ndc_y, -1.0)
            # normalize
            l = math.sqrt(ray_dir[0]**2 + ray_dir[1]**2 + ray_dir[2]**2)
            ray_dir = (ray_dir[0]/l, ray_dir[1]/l, ray_dir[2]/l)
            intensity = ray_march(cam_pos, ray_dir, params, light_pos, baeume)
            row.append(intensitaet_zu_ascii(intensity, params.gamma))
        buffer.append(''.join(row))
    return buffer

def main():
    width, height = 80, 30
    cam_pos = (0.0, 0.0, 2.0)
    cam_dir = (0.0, 0.0, -1.0)
    params = ShaderParams()
    # Beispiel-Bäume: (x, y, radius, height)
    baeume = [
        (-1.5, -1.0, 0.2, 1.5),
        (1.2, 0.5, 0.25, 1.8),
        (0.0, -2.0, 0.3, 2.0)
    ]
    light_pos = (0.0, 2.0, 3.0)
    frame = 0
    try:
        while True:
            # Lichtquelle leicht rotieren für Dynamik
            angle = frame * 0.03
            light_pos = (math.sin(angle) * 2.0, math.cos(angle) * 2.0, 3.0)
            buf = render_frame(width, height, cam_pos, cam_dir, params, light_pos, baeume)
            # optional blur für weichere Kanten
            if params.blur_radius > 0:
                w = gauß_gewichte(params.blur_radius)
                buf_float = [[intensitaet_zu_ascii(0.0) for _ in range(width)] for _ in range(height)]
                # Convert ASCII back to float approximation for blur
                char_to_val = {c: i/(len(" .:'-=+*#%@")-1) for i, c in enumerate(" .:'-=+*#%@")}
                for y in range(height):
                    for x in range(width):
                        buf_float[y][x] = char_to_val.get(buf[y][x], 0.0)
                buf_float = box_blur_1d(buf_float, w, True)
                buf_float = box_blur_1d(buf_float, w, False)
                # back to ASCII
                buf = [''.join(intensitaet_zu_ascii(v, params.gamma) for v in row) for row in buf_float]
            # Ausgabe
            print('\x1b[H\x1b[2J')  # clear screen
            for line in buf:
                print(line)
            time.sleep(0.05)
            frame += 1
            # Eingabe prüfen, max 20 Schritte
            if frame % 20 == 0:
                try:
                    inp = input('Weiter? (j/n) ')
                    if _norm(inp) not in ('j', 'ja', 'y', 'yes'):
                        break
                except EOFError:
                    break
    except KeyboardInterrupt:
        pass
    print('Simulation beendet. Danke für das Anschauen!')

if __name__ == '__main__':
    main()