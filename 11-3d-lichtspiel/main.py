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
                    return params.umbra_dunkelheit
                penumbra_r = br + params.penumbra_breite * dist_light
                if dist_xy_sq < penumbra_r * penumbra_r:
                    dist_xy = math.sqrt(dist_xy_sq)
                    t = (dist_xy - br) / (params.penumbra_breite * dist_light)
                    t = max(0.0, min(1.0, t))
                    smooth = t * t * (3.0 - 2.0 * t)
                    f = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * smooth
                    min_f = min(min_f, f)
    return min_f

def raymarch_pixel(px, py, cam_pos, cam_dir, light_pos, baeume, params, width, height):
    """Volumetric Raymarching für einen Pixel."""
    # Near / Far planes
    near, far = 0.5, 30.0
    steps = params.march_steps
    if params.adaptive_steps:
        # Einfache adaptive Logik: mehr Schritte bei Nebel
        steps = int(steps * params.max_step_factor)
    
    step_size = (far - near) / steps
    
    # Startposition
    ox, oy, oz = cam_pos
    dx, dy, dz = cam_dir
    
    # Jitter für Temporal Stability / Dithering
    jitter = 0.0
    if params.jitter_enabled:
        jitter = (random.random() - 0.5) * params.jitter_strength * step_size
    
    # Lichtrichtung vorberechnen
    lx, ly, lz = light_pos
    
    transmittance = 1.0
    radiance = 0.0
    
    for i in range(steps):
        t = near + (i + 0.5) * step_size + jitter
        sx, sy, sz = ox + dx * t, oy + dy * t, oz + dz * t
        
        # Dichte an Sample-Position
        density = mist_dichte((sx, sy, sz), params)
        if density < 1e-4:
            continue
            
        # Extinction
        sigma_t = params.scattering_coeff + params.absorption_coeff
        delta_optical = density * sigma_t * step_size
        transmittance *= math.exp(-delta_optical)
        
        if transmittance < params.early_exit_threshold:
            break
            
        # In-Scattering
        # Lichtvektor vom Sample zur Light
        lvx, lvy, lvz = lx - sx, ly - sy, lz - sz
        dist_light = math.sqrt(lvx*lvx + lvy*lvy + lvz*lvz)
        if dist_light < 0.01:
            continue
        lvx, lvy, lvz = lvx/dist_light, lvy/dist_light, lvz/dist_light
        
        # Phase Function (Henyey-Greenstein)
        cos_theta = dx * lvx + dy * lvy + dz * lvz
        phase = henyey_greenstein(cos_theta, params.phase_g)
        
        # Shadow
        shadow = schattenfaktor_3d((sx, sy, sz), light_pos, baeume, params)
        
        # Light Intensity (Inverse Square + Falloff)
        falloff = 1.0 / (1.0 + (dist_light * params.falloff_start) ** params.falloff_exponent)
        
        scatter = density * params.scattering_coeff * phase * shadow * falloff * step_size
        radiance += scatter * transmittance * params.volumetric_gain
        
    # Ambient / Base Fog Color
    radiance += params.ambient * (1.0 - transmittance) * 0.5
    
    return radiance

def render_frame(cam_pos, cam_yaw, cam_pitch, light_pos, baeume, params, width, height):
    """Rendert einen Frame in einen Float-Buffer."""
    buffer = [[0.0 for _ in range(width)] for __ in range(height)]
    fov = math.pi / 3.0 # 60 Grad
    aspect = width / height
    
    # Kameravektoren
    cy = math.cos(cam_yaw)
    sy = math.sin(cam_yaw)
    cp = math.cos(cam_pitch)
    sp = math.sin(cam_pitch)
    
    forward = (cy * cp, sy * cp, sp)
    right = (-sy, cy, 0.0)
    up = (-cy * sp, -sy * sp, cp)
    
    for y in range(height):
        for x in range(width):
            # NDC -1..1
            nx = (x + 0.5) / width * 2.0 - 1.0
            ny = 1.0 - (y + 0.5) / height * 2.0 # Y nach oben
            
            # Ray Direction
            rx = forward[0] + right[0] * nx * math.tan(fov/2) * aspect + up[0] * ny * math.tan(fov/2)
            ry = forward[1] + right[1] * nx * math.tan(fov/2) * aspect + up[1] * ny * math.tan(fov/2)
            rz = forward[2] + right[2] * nx * math.tan(fov/2) * aspect + up[2] * ny * math.tan(fov/2)
            rlen = math.sqrt(rx*rx + ry*ry + rz*rz)
            rx, ry, rz = rx/rlen, ry/rlen, rz/rlen
            
            val = raymarch_pixel(x, y, cam_pos, (rx, ry, rz), light_pos, baeume, params, width, height)
            buffer[y][x] = val
    return buffer

def bloom_pass(buffer, params):
    """Extrahiert helle Bereiche, blurred sie und addiert sie wieder hinzu."""
    h, w = len(buffer), len(buffer[0])
    # 1. Threshold
    bloom_src = [[0.0 for _ in range(w)] for __ in range(h)]
    for y in range(h):
        for x in range(w):
            val = buffer[y][x]
            if val > params.bloom_threshold:
                bloom_src[y][x] = (val - params.bloom_threshold) * params.bloom_intensity
    
    # 2. Blur (Separable Gaussian)
    weights = gauß_gewichte(params.bloom_radius)
    blur_h = box_blur_1d(bloom_src, weights, True)
    blur_v = box_blur_1d(blur_h, weights, False)
    
    # 3. Add back
    result = [[0.0 for _ in range(w)] for __ in range(h)]
    for y in range(h):
        for x in range(w):
            result[y][x] = buffer[y][x] + blur_v[y][x]
    return result

def tonemap(buffer, params):
    """Reinhard-ish Tonemapping + Gamma + Vibrancy."""
    h, w = len(buffer), len(buffer[0])
    result = [[0.0 for _ in range(w)] for __ in range(h)]
    for y in range(h):
        for x in range(w):
            val = buffer[y][x]
            # Simple Reinhard
            mapped = val / (1.0 + val)
            # Gamma
            mapped = mapped ** (1.0 / max(0.01, params.gamma))
            # Vibrancy (einfacher Kontrastboost um Mittelwert)
            mapped = 0.5 + (mapped - 0.5) * params.vibrancy
            result[y][x] = max(0.0, min(1.0, mapped))
    return result

def buffer_to_ascii(buffer, params):
    """Wandelt Float-Buffer in ASCII-Strings um."""
    lines = []
    for row in buffer:
        line = ''.join(intensitaet_zu_ascii(v, params.gamma) for v in row)
        lines.append(line)
    return '\n'.join(lines)

def clear_screen():
    print('\033[2J\033[H', end='')

def main():
    random.seed(1337)
    params = ShaderParams()
    
    # Szene: Bäume (x, y, radius, height)
    baeume = [
        (-5.0, -3.0, 0.8, 4.0),
        (6.0, 2.0, 0.6, 3.5),
        (-2.0, 7.0, 1.0, 5.0),
        (8.0, -5.0, 0.7, 3.0),
        (0.0, 10.0, 0.9, 4.5),
        (-8.0, -2.0, 0.5, 2.5),
    ]
    
    # Kamera
    cam_pos = [0.0, 0.0, 1.8]
    cam_yaw = 0.0
    cam_pitch = -0.2
    
    # Licht
    light_angle = 0.0
    light_height = 8.0
    light_dist = 12.0
    
    width, height = 80, 36
    frame = 0
    max_frames = 20 # Limit für Auto-Test / Input
    
    print("3D-Lichtspiel gestartet. Steuerung: WASD=Bewegen, QE=Hoch/Runter, IJKL=Drehen, P=Pause, +=Bloom, -=Bloom, 0=Reset, Enter=Weiter, q=Quit")
    time.sleep(1)
    
    paused = False
    
    while frame < max_frames:
        if not paused:
            # Licht Animation
            light_angle += 0.005
            light_pos = (
                math.cos(light_angle) * light_dist,
                math.sin(light_angle) * light_dist,
                light_height + math.sin(light_angle * 0.7) * 1.5
            )
            
            # Render Pipeline
            raw = render_frame(cam_pos, cam_yaw, cam_pitch, light_pos, baeume, params, width, height)
            bloomed = bloom_pass(raw, params)
            toned = tonemap(bloomed, params)
            ascii_art = buffer_to_ascii(toned, params)
            
            clear_screen()
            print(f"Frame: {frame} | Pos: {cam_pos[0]:.1f},{cam_pos[1]:.1f},{cam_pos[2]:.1f} | Yaw: {cam_yaw:.2f} | Light: {light_pos[0]:.1f},{light_pos[1]:.1f}")
            print(ascii_art)
            print("[WASD/QE/IJKL/P/+/-/0/q] > ", end='', flush=True)
            
            frame += 1
        else:
            print("[PAUSED] > ", end='', flush=True)
        
        try:
            inp = input().strip().lower()
        except EOFError:
            print("\nEOF. Gute Nacht.")
            break
        
        if not inp and not paused:
            continue
        
        cmd = inp[0]
        move_speed = 0.5
        turn_speed = 0.05
        
        if cmd == 'w':
            cam_pos[0] += math.cos(cam_yaw) * move_speed
            cam_pos[1] += math.sin(cam_yaw) * move_speed
        elif cmd == 's':
            cam_pos[0] -= math.cos(cam_yaw) * move_speed
            cam_pos[1] -= math.sin(cam_yaw) * move_speed
        elif cmd == 'a':
            cam_pos[0] += math.cos(cam_yaw + math.pi/2) * move_speed
            cam_pos[1] += math.sin(cam_yaw + math.pi/2) * move_speed
        elif cmd == 'd':
            cam_pos[0] += math.cos(cam_yaw - math.pi/2) * move_speed
            cam_pos[1] += math.sin(cam_yaw - math.pi/2) * move_speed
        elif cmd == 'q':
            cam_pos[2] += move_speed
        elif cmd == 'e':
            cam_pos[2] -= move_speed
        elif cmd == 'i':
            cam_pitch = min(math.pi/2 - 0.1, cam_pitch + turn_speed)
        elif cmd == 'k':
            cam_pitch = max(-math.pi/2 + 0.1, cam_pitch - turn_speed)
        elif cmd == 'j':
            cam_yaw -= turn_speed
        elif cmd == 'l':
            cam_yaw += turn_speed
        elif cmd == 'p':
            paused = not paused
        elif cmd == '+':
            params.bloom_intensity = min(2.0, params.bloom_intensity + 0.05)
        elif cmd == '-':
            params.bloom_intensity = max(0.0, params.bloom_intensity - 0.05)
        elif cmd == '0':
            params = ShaderParams()
        elif cmd == 'q':
            print("Tschüss!")
            break
        
        # Kleines Delay damit CPU nicht glüht im Loop ohne Input
        time.sleep(0.01)
    
    print("Simulationsende.")

if __name__ == "__main__":
    main()