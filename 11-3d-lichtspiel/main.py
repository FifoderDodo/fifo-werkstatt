import math, sys, random, unicodedata, time, os

class ShaderParams:
    """Container für alle einstellbaren Shader-Parameter mit Defaults."""
    def __init__(self):
        self.penumbra_breite = 0.15
        self.umbra_dunkelheit = 0.05
        self.falloff_exponent = 2.0
        self.falloff_start = 0.5
        self.blur_radius = 1
        self.ambient = 0.08
        self.volumetric_gain = 1.0
        self.gamma = 0.6
        self.scattering_coeff = 0.3
        self.absorption_coeff = 0.08
        self.mist_density = 0.15
        self.mist_height_falloff = 0.8
        self.color_temp = 3200.0
        self.jitter_strength = 0.10
        self.phase_g = 0.55
        self.noise_seed = 42
        self.march_steps = 16
        self.jitter_enabled = True
        self.specular_intensity = 0.7
        self.specular_power = 18.0
        self.light_radius = 0.7
        self.vibrancy = 1.25
        self.depth_shading_wrap = 0.35
        self.bloom_threshold = 0.6
        self.bloom_intensity = 0.3
        self.bloom_radius = 1
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

def noise_2d(x, y, seed):
    ix, iy = int(math.floor(x)), int(math.floor(y))
    fx, fy = x - ix, y - iy
    def h(ix, iy):
        n = (ix * 73856093) ^ (iy * 19349663) ^ seed
        n = (n ^ (n >> 13)) * 0x5bd1e995
        n = (n ^ (n >> 15)) * 0x5bd1e995
        return ((n ^ (n >> 15)) & 0x7fffffff) / 2147483647.0
    u = fx * fx * (3.0 - 2.0 * fx)
    v = fy * fy * (3.0 - 2.0 * fy)
    a = h(ix, iy)
    b = h(ix + 1, iy)
    c = h(ix, iy + 1)
    d = h(ix + 1, iy + 1)
    x1 = a + (b - a) * u
    x2 = c + (d - c) * u
    return x1 + (x2 - x1) * v

def mist_dichte(pos, params):
    x, y, z = pos
    if z < 0.0:
        return 0.0
    basis = params.mist_density * math.exp(-z * params.mist_height_falloff)
    turbulenz = noise_2d(x * 0.45, y * 0.45, params.noise_seed)
    return max(0.0, basis * (0.65 + 0.7 * turbulenz))

def schattenfaktor_3d(pos, light_pos, baeume, params):
    px, py, pz = pos
    lx, ly, lz = light_pos
    vx, vy, vz = lx - px, ly - py, lz - pz
    dist_light_sq = vx * vx + vy * vy + vz * vz
    if dist_light_sq < 0.0025:
        return 1.0
    dist_light = math.sqrt(dist_light_sq)
    ux, uy, uz = vx / dist_light, vy / dist_light, vz / dist_light
    min_f = 1.0
    for bx, by, br, bh in baeume:
        dx, dy = bx - px, by - py
        proj = dx * ux + dy * uy
        if 0.2 < proj < dist_light:
            cz = pz + uz * proj
            if 0.0 <= cz <= bh:
                dist_center_sq = dx * dx + dy * dy - proj * proj
                if dist_center_sq < br * br:
                    dist_center = math.sqrt(dist_center_sq)
                    rand_faktor = 1.0 - (dist_center / br)
                    penumbra = params.penumbra_breite * (proj / dist_light)
                    shadow = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * max(0.0, (rand_faktor - penumbra) / max(0.001, 1.0 - penumbra))
                    min_f = min(min_f, shadow)
    return min_f

def render_frame(breite, hoehe, params, baeume, light_pos, cam_pos, cam_yaw, cam_pitch, t):
    cos_yaw, sin_yaw = math.cos(cam_yaw), math.sin(cam_yaw)
    cos_pitch, sin_pitch = math.cos(cam_pitch), math.sin(cam_pitch)
    lr, lg, lb = kelvin_to_rgb_factor(params.color_temp)
    fb_r = [[0.0 for _ in range(breite)] for __ in range(hoehe)]
    fb_g = [[0.0 for _ in range(breite)] for __ in range(hoehe)]
    fb_b = [[0.0 for _ in range(breite)] for __ in range(hoehe)]
    max_dist = 25.0
    base_step = max_dist / params.march_steps
    jitter_x = (random.random() - 0.5) * params.jitter_strength if params.jitter_enabled else 0
    jitter_y = (random.random() - 0.5) * params.jitter_strength if params.jitter_enabled else 0
    aspect = (breite / hoehe) * 0.5
    fx = cos_pitch * cos_yaw
    fy = cos_pitch * sin_yaw
    fz = sin_pitch
    rx = -sin_yaw
    ry = cos_yaw
    rz = 0.0
    ux = -sin_pitch * cos_yaw
    uy = -sin_pitch * sin_yaw
    uz = cos_pitch
    for y in range(hoehe):
        ndc_y = 1.0 - (y + 0.5 + jitter_y) / hoehe * 2.0
        for x in range(breite):
            ndc_x = (x + 0.5 + jitter_x) / breite * 2.0 - 1.0
            ndc_x *= aspect
            rdx = fx + ndc_x * rx + ndc_y * ux
            rdy = fy + ndc_x * ry + ndc_y * uy
            rdz = fz + ndc_x * rz + ndc_y * uz
            rlen = math.sqrt(rdx*rdx + rdy*rdy + rdz*rdz)
            rdx, rdy, rdz = rdx/rlen, rdy/rlen, rdz/rlen
            px, py, pz = cam_pos
            accumulated_r, accumulated_g, accumulated_b = 0.0, 0.0, 0.0
            transmittance = 1.0
            current_dist = 0.0
            for step in range(params.march_steps):
                step_size = base_step
                if params.adaptive_steps:
                    d = mist_dichte((px, py, pz), params)
                    factor = 1.0 / (1.0 + d * 5.0)
                    factor = max(params.min_step_factor, min(params.max_step_factor, factor))
                    step_size = base_step * factor
                if transmittance < params.early_exit_threshold:
                    break
                px += rdx * step_size
                py += rdy * step_size
                pz += rdz * step_size
                current_dist += step_size
                if pz < 0.0 or current_dist > max_dist:
                    break
                density = mist_dichte((px, py, pz), params)
                if density <= 0.001:
                    continue
                extinction = (params.absorption_coeff + params.scattering_coeff) * density * step_size
                transmittance *= math.exp(-extinction)
                lx, ly, lz = light_pos
                vx, vy, vz = lx - px, ly - py, lz - pz
                dist_light = math.sqrt(vx*vx + vy*vy + vz*vz)
                if dist_light < 0.01:
                    continue
                ldx, ldy, ldz = vx/dist_light, vy/dist_light, vz/dist_light
                cos_theta = rdx*ldx + rdy*ldy + rdz*ldz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                shadow = schattenfaktor_3d((px, py, pz), light_pos, baeume, params)
                falloff = 1.0 / max(0.01, (params.falloff_start + dist_light) ** params.falloff_exponent)
                scatter_amt = params.scattering_coeff * density * step_size * phase * falloff * shadow * transmittance
                accumulated_r += scatter_amt * lr
                accumulated_g += scatter_amt * lg
                accumulated_b += scatter_amt * lb
            sky_intensity = params.ambient * (0.5 + 0.5 * rdz) * transmittance
            accumulated_r += sky_intensity * 0.2
            accumulated_g += sky_intensity * 0.3
            accumulated_b += sky_intensity * 0.5
            def process(c):
                c = c * params.volumetric_gain
                return min(1.0, c ** params.gamma)
            fb_r[y][x] = process(accumulated_r)
            fb_g[y][x] = process(accumulated_g)
            fb_b[y][x] = process(accumulated_b)
    if params.bloom_intensity > 0:
        lum = [[0.0 for _ in range(breite)] for __ in range(hoehe)]
        for y in range(hoehe):
            for x in range(breite):
                lum[y][x] = 0.2126*fb_r[y][x] + 0.7152*fb_g[y][x] + 0.0722*fb_b[y][x]
        for y in range(hoehe):
            for x in range(breite):
                v = lum[y][x] - params.bloom_threshold
                lum[y][x] = max(0.0, v) * params.bloom_intensity
        weights = gauß_gewichte(params.bloom_radius)
        lum = box_blur_1d(lum, weights, True)
        lum = box_blur_1d(lum, weights, False)
        for y in range(hoehe):
            for x in range(breite):
                fb_r[y][x] = min(1.0, fb_r[y][x] + lum[y][x] * lr)
                fb_g[y][x] = min(1.0, fb_g[y][x] + lum[y][x] * lg)
                fb_b[y][x] = min(1.0, fb_b[y][x] + lum[y][x] * lb)
    if params.blur_radius > 0:
        weights = gauß_gewichte(params.blur_radius)
        fb_r = box_blur_1d(fb_r, weights, True)
        fb_r = box_blur_1d(fb_r, weights, False)
        fb_g = box_blur_1d(fb_g, weights, True)
        fb_g = box_blur_1d(fb_g, weights, False)
        fb_b = box_blur_1d(fb_b, weights, True)
        fb_b = box_blur_1d(fb_b, weights, False)
    out_lines = []
    for y in range(hoehe):
        line_chars = []
        for x in range(breite):
            l = 0.2126*fb_r[y][x] + 0.7152*fb_g[y][x] + 0.0722*fb_b[y][x]
            ch = intensitaet_zu_ascii(l, params.gamma)
            line_chars.append(ch)
        out_lines.append(''.join(line_chars))
    return '\n'.join(out_lines)

def main():
    params = ShaderParams()
    random.seed(1337)
    baeume = []
    for _ in range(8):
        bx = random.uniform(-10, 10)
        by = random.uniform(-10, 10)
        br = random.uniform(0.4, 0.9)
        bh = random.uniform(3.0, 6.0)
        baeume.append((bx, by, br, bh))
    cam_pos = (0.0, -8.0, 1.7)
    cam_yaw = 0.0
    cam_pitch = 0.15
    light_height = 2.5
    light_orbit_radius = 3.0
    light_speed = 0.15
    try:
        term_size = os.get_terminal_size()
        breite = min(term_size.columns, 60)
        hoehe = min(term_size.lines - 3, 30)
    except:
        breite, hoehe = 60, 30
    print("3D-Lichtspiel: Herbstlicher Park. Drücke 'q' zum Beenden, 'h' für Hilfe.")
    time.sleep(0.5)
    t = 0.0
    frame = 0
    while True:
        light_angle = t * light_speed
        light_pos = (
            math.sin(light_angle) * light_orbit_radius,
            math.cos(light_angle) * light_orbit_radius,
            light_height
        )
        frame_start = time.time()
        frame_str = render_frame(breite, hoehe, params, baeume, light_pos, cam_pos, cam_yaw, cam_pitch, t)
        render_time = (time.time() - frame_start) * 1000
        sys.stdout.write('\x1b[2J\x1b[H')
        sys.stdout.write(frame_str)
        sys.stdout.write(f'\n\nFrame: {frame} | Zeit: {render_time:.1f}ms | Steps: {params.march_steps} | Pos: ({cam_pos[0]:.1f},{cam_pos[1]:.1f},{cam_pos[2]:.1f})')
        sys.stdout.write('\nBefehle: [w/s] Vor/Zurück [a/d] Links/Rechts [e/z] Hoch/Runter [</>] Drehen [+/-] Steps [r] Reset [h] Hilfe [q] Quit\n> ')
        sys.stdout.flush()
        try:
            cmd = input().strip().lower()
        except EOFError:
            print("\nTschüss!")
            break
        if cmd == 'q':
            print("Tschüss!")
            break
        elif cmd == 'h':
            print("Hilfe: w/s/a/d/e/z bewegen Kamera. </> drehen. +/- March Steps. r Reset. q Quit.")
            time.sleep(1.5)
            continue
        elif cmd == 'w':
            cam_pos = (cam_pos[0] + math.cos(cam_yaw)*0.5, cam_pos[1] + math.sin(cam_yaw)*0.5, cam_pos[2])
        elif cmd == 's':
            cam_pos = (cam_pos[0] - math.cos(cam_yaw)*0.5, cam_pos[1] - math.sin(cam_yaw)*0.5, cam_pos[2])
        elif cmd == 'a':
            cam_pos = (cam_pos[0] - math.sin(cam_yaw)*0.5, cam_pos[1] + math.cos(cam_yaw)*0.5, cam_pos[2])
        elif cmd == 'd':
            cam_pos = (cam_pos[0] + math.sin(cam_yaw)*0.5, cam_pos[1] - math.cos(cam_yaw)*0.5, cam_pos[2])
        elif cmd == 'e':
            cam_pos = (cam_pos[0], cam_pos[1], cam_pos[2] + 0.3)
        elif cmd == 'z':
            cam_pos = (cam_pos[0], cam_pos[1], max(0.5, cam_pos[2] - 0.3))
        elif cmd == '<':
            cam_yaw -= 0.15
        elif cmd == '>':
            cam_yaw += 0.15
        elif cmd == '+':
            params.march_steps = min(128, params.march_steps + 4)
        elif cmd == '-':
            params.march_steps = max(8, params.march_steps - 4)
        elif cmd == 'r':
            cam_pos = (0.0, -8.0, 1.7)
            cam_yaw = 0.0
            cam_pitch = 0.15
            params = ShaderParams()
        t += 0.1
        frame += 1
        if frame > 20:
            break

if __name__ == '__main__':
    main()