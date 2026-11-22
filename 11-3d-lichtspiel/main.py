import math, sys, random, unicodedata, time, select

class ShaderParams:
    """Container für alle einstellbaren Shader‑Parameter mit Defaults."""
    def __init__(self):
        self.penumbra_breite = 0.15
        self.umbra_dunkelheit = 0.05
        self.falloff_exponent = 2.0
        self.falloff_start = 0.5
        self.blur_radius = 3
        self.ambient = 0.05          # etwas mehr Umgebungslicht
        self.volumetric_gain = 2.5   # stärkerer Volumeneffekt
        self.gamma = 0.55            # etwas offener
        self.scattering_coeff = 0.45 # mehr Streuung
        self.absorption_coeff = 0.08 # weniger Absorption
        self.mist_density = 0.22
        self.mist_height_falloff = 0.8
        self.color_temp = 3000.0     # wärmeres Licht
        self.jitter_strength = 0.12
        self.phase_g = 0.6
        self.noise_seed = 42
        self.march_steps = 24        # mehr Schritte für sauberere Kegel
        self.jitter_enabled = True
        self.specular_intensity = 0.6
        self.specular_power = 24.0
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
    def lerp(a, b, t):
        return a + t * (b - a)
    c00 = lerp(c000, c100, fx)
    c01 = lerp(c001, c101, fx)
    c10 = lerp(c010, c110, fx)
    c11 = lerp(c011, c111, fx)
    c0 = lerp(c00, c10, fy)
    c1 = lerp(c01, c11, fy)
    return lerp(c0, c1, fz)

def render(params: ShaderParams, bäume, licht_pos, width=60, height=18, frame=0):
    """Ray‑March vom Kamerapunkt (0,0,10) auf die Ground‑Plane z=0.
    Gibt Liste von ASCII‑Zeilen zurück."""
    img = [[0.0 for _ in range(width)] for _ in range(height)]
    lx, ly, lz = licht_pos
    cam_x, cam_y, cam_z = 0.0, 0.0, 10.0
    world_w, world_h = 12.0, 12.0 * height / width
    max_dist = 18.0
    step_size = max_dist / max(1, params.march_steps)
    # Farbtemperatur
    cr, cg, cb = kelvin_to_rgb_factor(params.color_temp)
    # Jitter für dieses Frame
    jitter = 0.0
    if params.jitter_enabled:
        jitter = noise_2d(frame * 0.1, 0.0, params.noise_seed) * params.jitter_strength
    for iy in range(height):
        for ix in range(width):
            # NDC -> World
            ux = (ix + 0.5) / width * world_w - world_w * 0.5
            uy = (iy + 0.5) / height * world_h - world_h * 0.5
            # Ray direction
            rx, ry, rz = ux - cam_x, uy - cam_y, -cam_z
            rlen = math.hypot(rx, ry, rz)
            rx, ry, rz = rx / rlen, ry / rlen, rz / rlen
            # Ray marching
            accum = 0.0
            transmittance = 1.0
            for step in range(params.march_steps):
                t = (step + 0.5 + jitter) * step_size
                px, py, pz = cam_x + rx * t, cam_y + ry * t, cam_z + rz * t
                if pz <= 0.0:
                    # Ground hit
                    break
                # Vector to light
                vlx, vly, vlz = lx - px, ly - py, lz - pz
                dist_light = math.hypot(vlx, vly, vlz)
                if dist_light < 0.01:
                    continue
                vlx, vly, vlz = vlx / dist_light, vly / dist_light, vlz / dist_light
                # Phase function
                cos_theta = rx * vlx + ry * vly + rz * vlz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                # Falloff
                falloff = 1.0 / max(0.001, (dist_light * params.falloff_start) ** params.falloff_exponent)
                # Shadow
                shadow = schattenfaktor_für_punkt(px, py, lx, ly, dist_light, bäume, params)
                # Mist density with height falloff
                mist = params.mist_density * math.exp(-pz * params.mist_height_falloff)
                # Noise for volumetric variation
                noise = noise_3d(px * 0.5, py * 0.5, pz * 0.5, params.noise_seed + frame) * 0.5 + 0.5
                mist *= noise
                # Scattering contribution
                scatter = params.scattering_coeff * phase * falloff * shadow * mist
                # Absorption
    
                absorption = math.exp(-params.absorption_coeff * mist * step_size)
                transmittance *= absorption
                accum += scatter * transmittance
                if transmittance < 0.01:
                    break
            # Ground contribution (simple lambert + specular)
            if pz <= 0.0:
                # Ground normal (0,0,1)
                # Diffuse
                ground_diffuse = max(0.0, vlz) * falloff * shadow
                # Specular (Blinn-Phong)
                hx, hy, hz = rx + vlx, ry + vly, rz + vlz
                hlen = math.hypot(hx, hy, hz)
                if hlen > 0.0:
                    hx, hy, hz = hx / hlen, hy / hlen, hz / hlen
                    spec = max(0.0, hz) ** params.specular_power
                    # Noise on specular
                    spec_noise = noise_2d(px * params.specular_noise_scale, py * params.specular_noise_scale, params.noise_seed + 100) * 0.5 + 0.5
                    spec *= spec_noise
                    ground_specular = spec * params.specular_intensity * falloff * shadow
                else:
                    ground_specular = 0.0
                ground = (ground_diffuse + ground_specular) * transmittance
                accum += ground
            # Ambient
            accum += params.ambient
            # Volumetric gain
            accum *= params.volumetric_gain
            # Tone mapping (simple Reinhard)
            accum = accum / (1.0 + accum)
            # Color temperature
            accum_r = accum * cr
            accum_g = accum * cg
            accum_b = accum * cb
            # Luminance for ASCII
            lum = 0.2126 * accum_r + 0.7152 * accum_g + 0.0722 * accum_b
            img[iy][ix] = lum
    # Optional blur
    if params.blur_radius > 0:
        weights = gauß_gewichte(params.blur_radius)
        img = box_blur_1d(img, weights, True)
        img = box_blur_1d(img, weights, False)
    # Convert to ASCII
    ascii_lines = []
    for row in img:
        line = ''.join(intensitaet_zu_ascii(v, params.gamma) for v in row)
        ascii_lines.append(line)
    return ascii_lines

def main():
    # Szene: Bäume als (x, y, radius)
    random.seed(12345)
    bäume = []
    for _ in range(12):
        bx = random.uniform(-5.5, 5.5)
        by = random.uniform(-5.5, 5.5)
        br = random.uniform(0.3, 0.7)
        bäume.append((bx, by, br))
    params = ShaderParams()
    frame = 0
    licht_winkel = 0.0
    licht_radius = 4.0
    licht_höhe = 3.5
    last_time = time.time()
    print("\x1b[2J\x1b[H", end='')  # clear screen
    try:
        while True:
            # Animation: Licht kreist
            licht_winkel += 0.02
            lx = math.cos(licht_winkel) * licht_radius
            ly = math.sin(licht_winkel) * licht_radius
            lz = licht_höhe + 0.5 * math.sin(licht_winkel * 0.7)
            licht_pos = (lx, ly, lz)
            # Render
            lines = render(params, bäume, licht_pos, frame=frame)
            # UI line
            ui = f"Frame {frame} Licht=({lx:.1f},{ly:.1f},{lz:.1f}) Steps={params.march_steps} Gain={params.volumetric_gain} [q]uit [+/-]Gain [.</>]Steps [a/z]Ambient [c/v]ColorTemp [b/n]Mist [m/,]Scatter [j/k]Jitter [p/l]Spec"
            # Output
            sys.stdout.write("\x1b[H")
            for line in lines:
                sys.stdout.write(line + "\n")
            sys.stdout.write(ui + "\n")
            sys.stdout.flush()
            # Non-blocking input
            rlist, _, _ = select.select([sys.stdin], [], [], 0.03)
            if rlist:
                key = sys.stdin.read(1)
                if not key:
                    break
                key = _norm(key)
                if key == 'q':
                    break
                elif key == '+':
                    params.volumetric_gain = min(5.0, params.volumetric_gain + 0.1)
                elif key == '-':
                    params.volumetric_gain = max(0.1, params.volumetric_gain - 0.1)
                elif key == '.':
                    params.march_steps = min(64, params.march_steps + 2)
                elif key == '>':
                    params.march_steps = max(4, params.march_steps - 2)
                elif key == 'a':
                    params.ambient = min(0.5, params.ambient + 0.01)
                elif key == 'z':
                    params.ambient = max(0.0, params.ambient - 0.01)
                elif key == 'c':
                    params.color_temp = min(10000.0, params.color_temp + 200.0)
                elif key == 'v':
                    params.color_temp = max(1000.0, params.color_temp - 200.0)
                elif key == 'b':
                    params.mist_density = min(1.0, params.mist_density + 0.02)
                elif key == 'n':
                    params.mist_density = max(0.0, params.mist_density - 0.02)
                elif key == 'm':
                    params.scattering_coeff = min(2.0, params.scattering_coeff + 0.05)
                elif key == ',':
                    params.scattering_coeff = max(0.0, params.scattering_coeff - 0.05)
                elif key == 'j':
                    params.jitter_strength = min(0.5, params.jitter_strength + 0.02)
                elif key == 'k':
                    params.jitter_strength = max(0.0, params.jitter_strength - 0.02)
                elif key == 'p':
                    params.specular_intensity = min(2.0, params.specular_intensity + 0.05)
                elif key == 'l':
                    params.specular_intensity = max(0.0, params.specular_intensity - 0.05)
            frame += 1
            # Frame rate cap
            elapsed = time.time() - last_time
            if elapsed < 0.03:
                time.sleep(0.03 - elapsed)
            last_time = time.time()
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        print("\x1b[2J\x1b[H", end='')
        print("Dodo wacht auf. Gute Nacht!")

if __name__ == "__main__":
    main()