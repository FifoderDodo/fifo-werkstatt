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
                # Abstand vom Strahl zum Zylinderzentrum in XY
                rx = px + ux * proj - bx
                ry = py + uy * proj - by
                dist_ray = math.sqrt(rx * rx + ry * ry)
                if dist_ray < br:
                    # harter Kernschatten
                    return params.umbra_dunkelheit
                elif dist_ray < br + params.penumbra_breite:
                    # weicher Penumbra-Übergang
                    t = (dist_ray - br) / params.penumbra_breite
                    f = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * t
                    if f < min_f:
                        min_f = f
    return min_f

def render_frame(params, light_pos, baeume, width=80, height=40, fov=1.2):
    """Ray-Marching für jeden Pixel, gibt 2D-Luminanz-Array zurück."""
    aspect = width / height
    frame = [[0.0 for _ in range(width)] for __ in range(height)]
    color_r, color_g, color_b = kelvin_to_rgb_factor(params.color_temp)
    vibrancy = params.vibrancy
    for y in range(height):
        for x in range(width):
            # Normalisierte Gerätekoordinaten
            ndc_x = (x + 0.5) / width * 2.0 - 1.0
            ndc_y = 1.0 - (y + 0.5) / height * 2.0
            # Ray-Direction
            dir_x = ndc_x * aspect * fov
            dir_y = ndc_y * fov
            dir_z = -1.0
            len_dir = math.sqrt(dir_x*dir_x + dir_y*dir_y + dir_z*dir_z)
            dir_x /= len_dir
            dir_y /= len_dir
            dir_z /= len_dir
            # Ray-Origin (Kamera bei 0,0,2)
            ox, oy, oz = 0.0, 0.0, 2.0
            # Jitter für Temporal AA
            jitter = 0.0
            if params.jitter_enabled:
                jitter = (random.random() - 0.5) * params.jitter_strength
            # Adaptive Schrittweite
            step_count = params.march_steps
            if params.adaptive_steps:
                # Einfache Heuristik: mehr Schritte bei Nebel
                step_count = int(params.march_steps * (1.0 + params.mist_density))
            step_size = 1.0 / step_count
            transmittance = 1.0
            radiance = 0.0
            for step in range(step_count):
                t = (step + 0.5 + jitter) * step_size
                px = ox + dir_x * t
                py = oy + dir_y * t
                pz = oz + dir_z * t
                if pz < 0.0:
                    break
                # Dichte an Position
                density = mist_dichte((px, py, pz), params)
                if density < 1e-4:
                    continue
                # Schattenfaktor
                shadow = schattenfaktor_3d((px, py, pz), light_pos, baeume, params)
                # Phase-Funktion (Henyey-Greenstein)
                cos_theta = -(dir_x * 0.0 + dir_y * 0.0 + dir_z * 1.0)  # Licht kommt von oben
                phase = henyey_greenstein(cos_theta, params.phase_g)
                # Scattering
                scatter = density * params.scattering_coeff * phase * shadow
                # Absorption
                absorb = density * params.absorption_coeff
                # Volumetric Gain
                radiance += transmittance * scatter * params.volumetric_gain
                transmittance *= math.exp(-absorb)
                if transmittance < params.early_exit_threshold:
                    break
            # Ambient & Tonemapping
            radiance = (radiance + params.ambient) * vibrancy
            # Gamma-Korrektur
            radiance = radiance ** params.gamma
            frame[y][x] = radiance
    return frame

def apply_bloom(frame, params):
    """Einfache Bloom-Postprocessing: Threshold -> Blur -> Add."""
    h, w = len(frame), len(frame[0])
    # Threshold
    bloom_src = [[max(0.0, frame[y][x] - params.bloom_threshold) for x in range(w)] for y in range(h)]
    # Blur
    weights = gauß_gewichte(params.bloom_radius)
    blur_h = box_blur_1d(bloom_src, weights, horizontal=True)
    blur_v = box_blur_1d(blur_h, weights, horizontal=False)
    # Add
    result = [[0.0 for _ in range(w)] for __ in range(h)]
    for y in range(h):
        for x in range(w):
            result[y][x] = min(1.0, frame[y][x] + blur_v[y][x] * params.bloom_intensity)
    return result

def frame_to_ascii(frame, gamma=0.6):
    """Konvertiert Luminanz-Frame in ASCII-Zeilen."""
    lines = []
    for row in frame:
        line = ''.join(intensitaet_zu_ascii(v, gamma) for v in row)
        lines.append(line)
    return '\n'.join(lines)

def main():
    params = ShaderParams()
    # Beispiel-Szene: Bäume als (x, y, radius, height)
    baeume = [
        (-1.2, -0.8, 0.25, 1.5),
        (1.0, -0.5, 0.3, 1.8),
        (-0.5, 1.2, 0.2, 1.2),
        (1.5, 1.0, 0.28, 1.6),
        (0.0, -1.5, 0.35, 2.0),
    ]
    light_pos = [0.0, 0.0, 3.0]  # x, y, z
    print("3D-Lichtspiel – interaktiver volumetrischer Simulator")
    print("Steuerung: WASD = Licht bewegen, Q/E = Höhe, +/- = Schritte, B = Bloom an/aus, R = Reset, X = Ende")
    bloom_enabled = True
    interactive = sys.stdin.isatty()
    demo_frames = 10
    frame_count = 0
    try:
        while True:
            frame = render_frame(params, light_pos, baeume)
            if bloom_enabled:
                frame = apply_bloom(frame, params)
            ascii_art = frame_to_ascii(frame, params.gamma)
            # Clear screen (ANSI)
            sys.stdout.write('\x1b[2J\x1b[H')
            sys.stdout.write(ascii_art)
            if interactive:
                sys.stdout.write(f'\n\nLicht: ({light_pos[0]:.2f}, {light_pos[1]:.2f}, {light_pos[2]:.2f})  Bloom: {"An" if bloom_enabled else "Aus"}  Schritte: {params.march_steps}')
                sys.stdout.write('\nEingabe: ')
                sys.stdout.flush()
                try:
                    cmd = input().strip().lower()
                except EOFError:
                    break
            else:
                sys.stdout.write(f'\n\nDemo frame {frame_count+1}/{demo_frames}')
                sys.stdout.flush()
                time.sleep(0.1)
                frame_count += 1
                if frame_count >= demo_frames:
                    break
                # Auto-move light for demo
                light_pos[0] = math.sin(frame_count * 0.5) * 1.5
                light_pos[1] = math.cos(frame_count * 0.5) * 1.5
                cmd = ''
            if not cmd:
                continue
            if cmd == 'x':
                break
            elif cmd == 'w':
                light_pos[1] += 0.1
            elif cmd == 's':
                light_pos[1] -= 0.1
            elif cmd == 'a':
                light_pos[0] -= 0.1
            elif cmd == 'd':
                light_pos[0] += 0.1
            elif cmd == 'q':
                light_pos[2] += 0.1
            elif cmd == 'e':
                light_pos[2] = max(0.5, light_pos[2] - 0.1)
            elif cmd == '+':
                params.march_steps = min(64, params.march_steps + 2)
            elif cmd == '-':
                params.march_steps = max(4, params.march_steps - 2)
            elif cmd == 'b':
                bloom_enabled = not bloom_enabled
            elif cmd == 'r':
                light_pos = [0.0, 0.0, 3.0]
                params = ShaderParams()
            elif cmd == 'h':
                print("\nHilfe: WASD=XY, Q/E=Z, +/-=Schritte, B=Bloom, R=Reset, X=Ende\n")
                time.sleep(1.5)
            else:
                print(f"Unbekannt: {cmd}")
                time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    print("\nTschüss – der Dodo schläft weiter.")

if __name__ == '__main__':
    main()