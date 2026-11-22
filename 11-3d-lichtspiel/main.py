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
    img = [[0.0 for _ in range(width)] for _ in range(height)]
    lx, ly, lz = licht_pos
    cam_x, cam_y, cam_z = 0.0, 0.0, 10.0
    world_w, world_h = 12.0, 12.0 * height / width
    max_dist = 18.0
    step_size = max_dist / max(1, params.march_steps)
    light_r, light_g, light_b = kelvin_to_rgb_factor(params.color_temp)
    
    # Temporal jitter for noise
    jitter_x = noise_2d(frame * 0.1, 0.0, params.noise_seed) * params.jitter_strength if params.jitter_enabled else 0.0
    jitter_y = noise_2d(0.0, frame * 0.1, params.noise_seed + 1) * params.jitter_strength if params.jitter_enabled else 0.0
    
    for iy in range(height):
        # Viewport coordinates: from -world_w/2 to world_w/2, same for height
        sy = (iy / (height - 1) - 0.5) * world_h
        for ix in range(width):
            sx = (ix / (width - 1) - 0.5) * world_w
            # Ray direction from camera to pixel on near plane (z=0)
            rx = sx - cam_x
            ry = sy - cam_y
            rz = 0.0 - cam_z  # near plane at z=0
            ray_len = math.sqrt(rx*rx + ry*ry + rz*rz)
            rx, ry, rz = rx/ray_len, ry/ray_len, rz/ray_len
            
            acc_r = acc_g = acc_b = 0.0
            transmittance = 1.0
            
            for step in range(params.march_steps):
                t = (step + 0.5) * step_size
                px = cam_x + rx * t
                py = cam_y + ry * t
                pz = cam_z + rz * t
                
                # Mist density decreases with height
                mist = params.mist_density * math.exp(-pz * params.mist_height_falloff)
                if mist <= 0.0:
                    continue
                
                # Vector from sample point to light
                ldx = lx - px
                ldy = ly - py
                ldz = lz - pz
                light_dist = math.sqrt(ldx*ldx + ldy*ldy + ldz*ldz)
                if light_dist < 0.01:
                    continue
                ldx, ldy, ldz = ldx/light_dist, ldy/light_dist, ldz/light_dist
                
                # Phase function (Henyey-Greenstein)
                cos_theta = rx*ldx + ry*ldy + rz*ldz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                
                # Falloff
                falloff = 1.0 / max(params.falloff_start, light_dist) ** params.falloff_exponent
                
                # Shadow factor: project sample point onto ground (z=0) and use 2D shadow function
                # This approximates volumetric shadows by assuming light blocking is vertical.
                shadow = schattenfaktor_für_punkt(px, py, lx, ly, light_dist, bäume, params)
                
                # Absorption
                absorption = math.exp(-params.absorption_coeff * light_dist)
                
                # Scattering contribution
                scatter = params.scattering_coeff * mist * phase * falloff * shadow * absorption
                
                # Add jitter to scattering for noise
                if params.jitter_enabled:
                    jitter = noise_3d(px*0.5, py*0.5, pz*0.5 + frame*0.1, params.noise_seed + 2) * params.jitter_strength
                    scatter *= (1.0 + jitter)
                
                # Accumulate with transmittance
                acc_r += transmittance * scatter * light_r
                acc_g += transmittance * scatter * light_g
                acc_b += transmittance * scatter * light_b
                
                # Update transmittance (extinction)
                transmittance *= math.exp(-params.absorption_coeff * mist * step_size)
                if transmittance < 0.001:
                    break
            
            # Ground intersection specular highlight (simple approximation)
            # Find intersection of ray with ground plane z=0
            if rz < 0:
                t_ground = -cam_z / rz
                if t_ground > 0:
                    gx = cam_x + rx * t_ground
                    gy = cam_y + ry * t_ground
                    # Distance from light to ground point
                    gd = math.hypot(gx - lx, gy - ly)
                    if gd < 1e-3:
                        gd = 1e-3
                    # Specular based on angle between view and reflection
                    # Simplified: use noise for variation
                    spec_noise = noise_2d(gx * params.specular_noise_scale, gy * params.specular_noise_scale, params.noise_seed + 3)
                    spec = params.specular_intensity * (max(0.0, spec_noise) ** params.specular_power) * (1.0 / (gd * gd))
                    acc_r += spec * light_r
                    acc_g += spec * light_g
                    acc_b += spec * light_b
            
            # Combine channels with volumetric gain
            luminance = (acc_r + acc_g + acc_b) / 3.0 * params.volumetric_gain
            # Add ambient
            luminance += params.ambient
            img[iy][ix] = luminance
    
    # Box blur for volumetric glow
    weights = gauß_gewichte(params.blur_radius)
    img = box_blur_1d(img, weights, horizontal=True)
    img = box_blur_1d(img, weights, horizontal=False)
    
    # Convert to ASCII
    ascii_frame = []
    for y in range(height):
        line = ''.join(intensitaet_zu_ascii(img[y][x], params.gamma) for x in range(width))
        ascii_frame.append(line)
    return ascii_frame

def main():
    params = ShaderParams()
    # Example trees: (x, y, radius)
    bäume = [
        (-3.0, -2.0, 0.8),
        (2.5, 1.5, 0.6),
        (-1.0, 3.0, 0.7),
        (4.0, -3.0, 0.5),
        (-4.0, 2.0, 0.9),
    ]
    
    frame = 0
    light_angle = 0.0
    light_radius = 5.0
    light_height = 4.0
    
    print("3D-Lichtspiel – Drücke 'q' zum Beenden, Pfeiltasten für Parameter (nicht implementiert), Enter für nächsten Frame.")
    print("Strg+C oder EOF beendet das Programm.")
    
    try:
        while True:
            # Animate light position
            light_angle += 0.04
            lx = math.cos(light_angle) * light_radius
            ly = math.sin(light_angle) * light_radius
            lz = light_height + math.sin(light_angle * 0.7) * 0.5
            
            ascii_frame = render(params, bäume, (lx, ly, lz), frame=frame)
            
            # Clear screen (ANSI escape)
            sys.stdout.write('\x1b[2J\x1b[H')
            for line in ascii_frame:
                sys.stdout.write(line + '\n')
            sys.stdout.write(f'Frame {frame} - Licht: ({lx:.1f}, {ly:.1f}, {lz:.1f})\n')
            sys.stdout.flush()
            
            # Non-blocking input check
            rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
            if rlist:
                key = sys.stdin.readline()
                if not key:  # EOF
                    break
                key = key.strip().lower()
                if key == 'q':
                    break
                # Simple parameter tweaks
                elif key == 'w':
                    params.volumetric_gain = min(5.0, params.volumetric_gain + 0.1)
                elif key == 's':
                    params.volumetric_gain = max(0.1, params.volumetric_gain - 0.1)
                elif key == 'a':
                    params.mist_density = min(1.0, params.mist_density + 0.02)
                elif key == 'd':
                    params.mist_density = max(0.0, params.mist_density - 0.02)
                elif key == 'g':
                    params.gamma = min(1.5, params.gamma + 0.05)
                elif key == 'h':
                    params.gamma = max(0.1, params.gamma - 0.05)
                elif key == 'r':
                    params.color_temp = min(6500.0, params.color_temp + 200.0)
                elif key == 'b':
                    params.color_temp = max(1000.0, params.color_temp - 200.0)
                elif key == ' ':
                    params.jitter_enabled = not params.jitter_enabled
                # Print current params
                sys.stdout.write(f'Params: gain={params.volumetric_gain:.2f}, mist={params.mist_density:.2f}, gamma={params.gamma:.2f}, temp={params.color_temp:.0f}K, jitter={"on" if params.jitter_enabled else "off"}\n')
                sys.stdout.flush()
            
            frame += 1
            if frame > 500:  # safety limit
                break
            time.sleep(0.03)
    except KeyboardInterrupt:
        pass
    except EOFError:
        pass
    finally:
        sys.stdout.write('\nTschüss! Der Dodo schläft weiter.\n')
        sys.stdout.flush()

if __name__ == '__main__':
    main()