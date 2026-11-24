import math, sys, random, unicodedata, time, os

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
        self.march_steps = 8
        self.jitter_enabled = True
        self.specular_intensity = 0.7
        self.specular_power = 18.0
        self.light_radius = 0.7
        self.vibrancy = 1.25
        self.depth_shading_wrap = 0.35
        self.bloom_threshold = 0.6
        self.bloom_intensity = 0.45
        self.bloom_radius = 3
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
                dist_xy_sq = dx * dx + dy * dy - proj * proj
                if dist_xy_sq < br * br:
                    # Penumbra‑Übergang
                    d = math.sqrt(br * br - dist_xy_sq)
                    t = (proj - d) / dist_light
                    f = max(0.0, min(1.0, t))
                    min_f = min(min_f, f * (1.0 - params.penumbra_breite) + params.penumbra_breite)
    return min_f

def raymarch(start, dir_vec, max_dist, params, light_pos, baeume):
    step = params.march_steps
    step_size = max_dist / step
    acc = 0.0
    pos = list(start)
    for i in range(step):
        pos[0] += dir_vec[0] * step_size
        pos[1] += dir_vec[1] * step_size
        pos[2] += dir_vec[2] * step_size
        dens = mist_dichte(tuple(pos), params)
        if dens > 0.0:
            shade = schattenfaktor_3d(tuple(pos), light_pos, baeume, params)
            acc += dens * shade * params.volumetric_gain * step_size
    return acc

def render_frame(width, height, params, light_pos, baeume, time_sec):
    aspect = width / height
    fov = math.radians(60)
    tan_fov = math.tan(fov / 2)
    frame = []
    for y in range(height):
        row = []
        for x in range(width):
            ndc_x = (x + 0.5) / width * 2 - 1
            ndc_y = 1 - (y + 0.5) / height * 2
            ray_dir = [ndc_x * aspect * tan_fov, ndc_y * tan_fov, -1]
            length = math.sqrt(sum(c * c for c in ray_dir))
            ray_dir = [c / length for c in ray_dir]
            col = raymarch((0, 1.5, 5 + math.sin(time_sec) * 0.5), ray_dir, 20.0, params, light_pos, baeume)
            row.append(intensitaet_zu_ascii(col, params.gamma))
        frame.append(''.join(row))
    return frame

def apply_bloom(frame, params):
    # Konvertiere ASCII zu Helligkeit, blur, zurück
    height = len(frame)
    width = len(frame[0]) if height else 0
    # Mapping ASCII->float
    ramp = " .:'-=+*#%@"
    rev = {c: i / (len(ramp) - 1) for i, c in enumerate(ramp)}
    buffer = [[rev.get(ch, 0.0) for ch in line] for line in frame]
    # Blur horizontal & vertikal
    w = gauß_gewichte(params.bloom_radius)
    buffer = box_blur_1d(buffer, w, True)
    buffer = box_blur_1d(buffer, w, False)
    # Add bloom
    result = []
    for y in range(height):
        line = []
        for x in range(width):
            base = rev.get(frame[y][x], 0.0)
            add = buffer[y][x] * params.bloom_intensity
            val = min(1.0, base + add)
            line.append(intensitaet_zu_ascii(val, params.gamma))
        result.append(''.join(line))
    return result

def clear_screen():
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

def main():
    width, height = 80, 30
    params = ShaderParams()
    # Beispiel‑Bäume: (x, y, radius, height)
    baeume = [(-2, -1, 0.5, 2.0), (1.5, 0.5, 0.4, 1.8), (0, -2, 0.6, 2.2)]
    light_pos = (0.0, 3.0, 2.0)
    start_time = time.time()
    frame_count = 0
    try:
        while True:
            t = time.time() - start_time
            raw = render_frame(width, height, params, light_pos, baeume, t)
            frame = apply_bloom(raw, params)
            clear_screen()
            print('\n'.join(frame))
            frame_count += 1
            # einfache Eingabe für Beenden nach 20 Frames oder bei EOF
            if frame_count >= 20:
                break
            time.sleep(0.1)
    except EOFError:
        pass
    print('Simulation beendet. Danke für das Zuschauen!')

if __name__ == '__main__':
    main()