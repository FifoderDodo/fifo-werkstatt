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
                dist_center = math.sqrt(dx * dx + dy * dy - proj * proj)
                if dist_center < br:
                    return params.umbra_dunkelheit
                elif dist_center < br + params.penumbra_breite:
                    t = (dist_center - br) / params.penumbra_breite
                    min_f = min(min_f, params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * t)
    return min_f

def render_frame(breite, hoehe, params, baeume, light_pos, cam_pos, cam_dir, zeit):
    farb_faktor = kelvin_to_rgb_factor(params.color_temp)
    frame_buffer = [[0.0 for _ in range(breite)] for __ in range(hoehe)]
    cx, cy, cz = cam_dir
    cl = math.sqrt(cx * cx + cy * cy + cz * cz)
    if cl < 1e-6:
        cx, cy, cz = 0.0, 1.0, 0.0
    else:
        cx, cy, cz = cx / cl, cy / cl, cz / cl
    rx = -cy
    ry = cx
    rz = 0.0
    rl = math.sqrt(rx * rx + ry * ry)
    if rl < 1e-6:
        rx, ry = 1.0, 0.0
    else:
        rx, ry = rx / rl, ry / rl
    ux = cy * rz - cz * ry
    uy = cz * rx - cx * rz
    uz = cx * ry - cy * rx
    fov = 1.0
    aspect = breite / max(1, hoehe)
    for y in range(hoehe):
        for x in range(breite):
            ndc_x = (x + 0.5) / breite * 2.0 - 1.0
            ndc_y = 1.0 - (y + 0.5) / hoehe * 2.0
            rdx = cx * fov + rx * ndc_x * fov * aspect + ux * ndc_y * fov
            rdy = cy * fov + ry * ndc_x * fov * aspect + uy * ndc_y * fov
            rdz = cz * fov + rz * ndc_x * fov * aspect + uz * ndc_y * fov
            rdl = math.sqrt(rdx * rdx + rdy * rdy + rdz * rdz)
            if rdl > 0:
                rdx, rdy, rdz = rdx / rdl, rdy / rdl, rdz / rdl
            march_steps = params.march_steps
            if params.adaptive_steps:
                march_steps = int(march_steps * params.max_step_factor)
            px, py, pz = cam_pos
            step_size = 0.15
            accumulated = 0.0
            transmittance = 1.0
            jitter = 0.0
            if params.jitter_enabled:
                jitter = (noise_3d(x * 0.1, y * 0.1, zeit * 0.5, params.noise_seed) - 0.5) * params.jitter_strength
            for step in range(march_steps):
                px += rdx * step_size
                py += rdy * step_size
                pz += rdz * step_size
                ldx = light_pos[0] - px
                ldy = light_pos[1] - py
                ldz = light_pos[2] - pz
                dist_light = math.sqrt(ldx * ldx + ldy * ldy + ldz * ldz)
                if dist_light < 0.01:
                    break
                density = mist_dichte((px, py, pz), params)
                if density < 1e-4:
                    continue
                shadow = schattenfaktor_3d((px, py, pz), light_pos, baeume, params)
                ldx_n, ldy_n, ldz_n = ldx / dist_light, ldy / dist_light, ldz / dist_light
                cos_theta = -(rdx * ldx_n + rdy * ldy_n + rdz * ldz_n)
                phase = henyey_greenstein(cos_theta, params.phase_g)
                falloff = 1.0 / max(0.01, dist_light * dist_light)
                if dist_light > params.falloff_start:
                    falloff *= (params.falloff_start / dist_light) ** params.falloff_exponent
                scatter = density * params.scattering_coeff * phase * falloff * shadow
                absorption = density * params.absorption_coeff
                contrib = scatter * transmittance * step_size
                accumulated += contrib
                transmittance *= math.exp(-absorption * step_size)
                if transmittance < params.early_exit_threshold:
                    break
            final_val = params.ambient + accumulated * params.volumetric_gain
            frame_buffer[y][x] = min(1.0, final_val)
    if params.bloom_intensity > 0 and params.bloom_radius > 0:
        bloom_weights = gauß_gewichte(params.bloom_radius)
        bloom_buf = [[v for v in row] for row in frame_buffer]
        for y in range(hoehe):
            for x in range(breite):
                if bloom_buf[y][x] < params.bloom_threshold:
                    bloom_buf[y][x] = 0.0
                else:
                    bloom_buf[y][x] = (bloom_buf[y][x] - params.bloom_threshold) * params.bloom_intensity
        bloom_buf = box_blur_1d(bloom_buf, bloom_weights, True)
        bloom_buf = box_blur_1d(bloom_buf, bloom_weights, False)
        for y in range(hoehe):
            for x in range(breite):
                frame_buffer[y][x] = min(1.0, frame_buffer[y][x] + bloom_buf[y][x])
    if params.blur_radius > 0:
        blur_weights = gauß_gewichte(params.blur_radius)
        frame_buffer = box_blur_1d(frame_buffer, blur_weights, True)
        frame_buffer = box_blur_1d(frame_buffer, blur_weights, False)
    ascii_frame = []
    for y in range(hoehe):
        row = ''
        for x in range(breite):
            row += intensitaet_zu_ascii(frame_buffer[y][x], params.gamma)
        ascii_frame.append(row)
    return ascii_frame

def main():
    print("🌲 3D-Lichtspiel – Herbstlicher Park bei Nacht")
    print("===============================================")
    print("Steuerung: [Enter] nächster Frame, [q] Beenden, [p] Parameter ändern")
    print()
    params = ShaderParams()
    random.seed(12345)
    baeume = []
    for _ in range(12):
        bx = random.uniform(-8, 8)
        by = random.uniform(-8, 8)
        br = random.uniform(0.3, 0.8)
        bh = random.uniform(3.0, 6.0)
        baeume.append((bx, by, br, bh))
    light_pos = (0.0, 0.0, 4.0)
    cam_pos = (0.0, -10.0, 1.5)
    cam_dir = (0.0, 1.0, -0.1)
    # Reduce resolution for quick test
    breite, hoehe = 40, 20
    zeit = 0.0
    frame_nr = 0
    max_frames = 5  # stop after a few frames to avoid endless run in tests
    try:
        while frame_nr < max_frames:
            light_pos = (
                math.sin(zeit * 0.3) * 0.15,
                math.cos(zeit * 0.25) * 0.1,
                4.0 + math.sin(zeit * 0.2) * 0.05
            )
            frame = render_frame(breite, hoehe, params, baeume, light_pos, cam_pos, cam_dir, zeit)
            print(f"\x1b[2J\x1b[HFrame {frame_nr} | Zeit {zeit:.1f}s | Licht({light_pos[0]:.2f},{light_pos[1]:.2f},{light_pos[2]:.2f})")
            for row in frame:
                print(row)
            print(f"\n[Enter] weiter | [q] quit | [p] params | Steps:{params.march_steps} Gain:{params.volumetric_gain}")
            try:
                inp = input().strip().lower()
            except EOFError:
                print("\n🌙 Gute Nacht!")
                break
            if inp == 'q':
                print("🌙 Gute Nacht!")
                break
            elif inp == 'p':
                print("\nParameter (Enter = behalten):")
                try:
                    val = input(f"  volumetric_gain [{params.volumetric_gain}]: ").strip()
                    if val:
                        params.volumetric_gain = float(val)
                    val = input(f"  march_steps [{params.march_steps}]: ").strip()
                    if val:
                        params.march_steps = int(val)
                    val = input(f"  mist_density [{params.mist_density}]: ").strip()
                    if val:
                        params.mist_density = float(val)
                    val = input(f"  color_temp [{params.color_temp}]: ").strip()
                    if val:
                        params.color_temp = float(val)
                    val = input(f"  gamma [{params.gamma}]: ").strip()
                    if val:
                        params.gamma = float(val)
                    print("  ✓ Parameter aktualisiert\n")
                except ValueError:
                    print("  ✗ Ungültige Eingabe, wird ignoriert\n")
                continue
            zeit += 0.15
            frame_nr += 1
    except KeyboardInterrupt:
        print("\n🌙 Gute Nacht!")

if __name__ == "__main__":
    main()