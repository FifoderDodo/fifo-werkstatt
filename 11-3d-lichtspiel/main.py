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
                    # Penumbra: weicher Übergang am Rand
                    dist_xy = math.sqrt(max(0.0, dist_xy_sq))
                    rand_faktor = 1.0 - (dist_xy / br)
                    # Umbra dunkler, Penumbra heller
                    schatten = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * (1.0 - rand_faktor)
                    min_f = min(min_f, schatten)
    return min_f

def render_frame(licht_pos, baeume, params, breite=80, hoehe=40, cam_z=1.5):
    """Rendert ein einzelnes Frame als 2D-Intensitäts-Array."""
    bild = [[0.0 for _ in range(breite)] for __ in range(hoehe)]
    # Kamera schaut entlang -Y auf die XZ-Ebene (y=0)
    for iy in range(hoehe):
        for ix in range(breite):
            # Pixel-Koordinaten in Weltkoordinaten
            wx = (ix - breite * 0.5) * 0.1
            wz = cam_z - iy * 0.1
            wy = 0.0
            # Raymarching vom Licht zum Pixel
            lx, ly, lz = licht_pos
            dx, dy, dz = wx - lx, wy - ly, wz - lz
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            if dist < 1e-4:
                bild[iy][ix] = 1.0
                continue
            steps = params.march_steps
            if params.adaptive_steps:
                steps = max(4, int(steps * (0.5 + 0.5 * min(1.0, dist / 10.0))))
            step_len = dist / steps
            # Jitter für temporales Rauschen
            jitter = 0.0
            if params.jitter_enabled:
                jitter = (random.random() - 0.5) * params.jitter_strength * step_len
            acc = 0.0
            transmittance = 1.0
            for s in range(steps):
                t = (s + 0.5) / steps + jitter
                px = lx + dx * t
                py = ly + dy * t
                pz = lz + dz * t
                # Dichte an Position
                rho = mist_dichte((px, py, pz), params)
                if rho <= 0.0:
                    continue
                # Schattenfaktor
                shadow = schattenfaktor_3d((px, py, pz), licht_pos, baeume, params)
                # Phase-Funktion (Henyey-Greenstein)
                view_dx, view_dy, view_dz = -dx/dist, -dy/dist, -dz/dist
                light_dx, light_dy, light_dz = dx/dist, dy/dist, dz/dist
                cos_theta = view_dx*light_dx + view_dy*light_dy + view_dz*light_dz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                # Streuung und Absorption
                scatter = rho * params.scattering_coeff * phase * shadow
                absorb = rho * params.absorption_coeff
                transmittance *= math.exp(-absorb * step_len)
                acc += scatter * transmittance * step_len
                if transmittance < params.early_exit_threshold:
                    break
            # Falloff
            falloff = 1.0 / (1.0 + (dist * params.falloff_start) ** params.falloff_exponent)
            acc *= falloff * params.volumetric_gain
            # Ambient
            acc += params.ambient
            bild[iy][ix] = min(1.0, acc)
    return bild

def apply_bloom(bild, params):
    """Einfacher Bloom-Effekt via Box-Blur und Additiv-Mischung."""
    if params.bloom_radius <= 0 or params.bloom_intensity <= 0.0:
        return bild
    h, w = len(bild), len(bild[0])
    # Threshold
    bloom_src = [[max(0.0, bild[y][x] - params.bloom_threshold) for x in range(w)] for y in range(h)]
    gewichte = gauß_gewichte(params.bloom_radius)
    blur_h = box_blur_1d(bloom_src, gewichte, True)
    blur = box_blur_1d(blur_h, gewichte, False)
    # Additiv mischen
    for y in range(h):
        for x in range(w):
            bild[y][x] = min(1.0, bild[y][x] + blur[y][x] * params.bloom_intensity)
    return bild

def main():
    params = ShaderParams()
    # Ein paar Bäume: (x, y, radius, height)
    baeume = [
        (-3.0, -2.0, 0.6, 4.0),
        (2.5, 1.5, 0.5, 3.5),
        (-1.0, 3.0, 0.7, 5.0),
        (4.0, -3.0, 0.4, 3.0),
    ]
    breite, hoehe = 80, 40
    frame = 0
    try:
        while True:
            # Licht bewegt sich auf einem Kreis
            t = frame * 0.05
            r = 5.0
            licht_pos = (r * math.cos(t), r * math.sin(t), 3.0 + 0.5 * math.sin(t * 0.7))
            bild = render_frame(licht_pos, baeume, params, breite, hoehe)
            bild = apply_bloom(bild, params)
            # Gamma-Korrektur
            for y in range(hoehe):
                for x in range(breite):
                    bild[y][x] = bild[y][x] ** params.gamma
            # Ausgabe
            os.system('cls' if os.name == 'nt' else 'clear')
            for y in range(hoehe):
                zeile = ''.join(intensitaet_zu_ascii(bild[y][x], params.gamma) for x in range(breite))
                print(zeile)
            print(f'Frame {frame} | Licht: ({licht_pos[0]:.2f}, {licht_pos[1]:.2f}, {licht_pos[2]:.2f})')
            frame += 1
            # Kurze Pause, aber Eingabe möglich
            try:
                inp = input('')  # Leere Eingabe -> nächster Frame
                if inp.strip().lower() in ('q', 'quit', 'exit'):
                    break
            except EOFError:
                # Kein Input (z.B. im Test) -> kurz schlafen
                time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    print('\nDodo wacht auf. Gute Nacht!')

if __name__ == '__main__':
    main()