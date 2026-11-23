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
                dist_achse = math.hypot(bx - cx, by - cy)
                ratio = proj / dist_light
                penumbra = br * ratio + params.light_radius * (1.0 - ratio) * 0.4
                if dist_achse < penumbra:
                    # Neue Light-Decay-Formel für weichere Penumbra und realistischere Tiefe
                    t = dist_achse / max(1e-4, penumbra)
                    faktor = params.umbra_dunkelheit + (t ** params.falloff_exponent) * (1.0 - params.umbra_dunkelheit)
                    if faktor < min_f:
                        min_f = faktor
    return min_f

def raymarch(origin, direction, light_pos, baeume, params, jitter=0.0):
    """Volumetric ray marching mit Schatten und Streuung."""
    steps = params.march_steps
    max_dist = 12.0
    step_size = max_dist / steps
    r, g, b = 0.0, 0.0, 0.0
    transmittance = 1.0
    light_color = kelvin_to_rgb_factor(params.color_temp)
    
    for i in range(steps):
        t = (i + 0.5) * step_size + jitter
        px = origin[0] + direction[0] * t
        py = origin[1] + direction[1] * t
        pz = origin[2] + direction[2] * t
        
        density = mist_dichte((px, py, pz), params)
        if density <= 0.0:
            continue
        
        # Schattenfaktor an dieser Position
        shadow = schattenfaktor_3d((px, py, pz), light_pos, baeume, params)
        
        # Lichtvektor von Probe zur Lichtquelle
        lx, ly, lz = light_pos
        lvx, lvy, lvz = lx - px, ly - py, lz - pz
        light_dist = math.sqrt(lvx*lvx + lvy*lvy + lvz*lvz)
        if light_dist < 0.01:
            continue
        lvx, lvy, lvz = lvx/light_dist, lvy/light_dist, lvz/light_dist
        
        # Phase function (Henyey-Greenstein)
        cos_theta = direction[0]*lvx + direction[1]*lvy + direction[2]*lvz
        phase = henyey_greenstein(cos_theta, params.phase_g)
        
        # Light decay mit falloff_start und exponent
        decay = 1.0 / (1.0 + (light_dist * params.falloff_start) ** params.falloff_exponent)
        
        # Streuung
        scatter = density * params.scattering_coeff * phase * decay * shadow
        absorption = density * params.absorption_coeff
        
        # Akkumulation
        r += transmittance * scatter * light_color[0]
        g += transmittance * scatter * light_color[1]
        b += transmittance * scatter * light_color[2]
        transmittance *= math.exp(-absorption * step_size)
        if transmittance < 0.001:
            break
    
    # Umgebungslicht
    r += params.ambient * light_color[0]
    g += params.ambient * light_color[1]
    b += params.ambient * light_color[2]
    
    # Volumetric gain
    r *= params.volumetric_gain
    g *= params.volumetric_gain
    b *= params.volumetric_gain
    
    # Vibrancy (Sättigung)
    avg = (r + g + b) / 3.0
    r = avg + (r - avg) * params.vibrancy
    g = avg + (g - avg) * params.vibrancy
    b = avg + (b - avg) * params.vibrancy
    
    return (r, g, b)

def render_frame(params, frame_idx):
    """Rendert einen Frame als ASCII-Art."""
    width, height = 80, 40
    aspect = width / height
    
    # Kameraposition und -richtung
    cam_pos = (0.0, 0.0, 2.5)
    cam_target = (0.0, 0.0, 0.0)
    
    # Lichtposition (bewegt sich langsam)
    light_angle = frame_idx * 0.02
    light_pos = (math.sin(light_angle) * 4.0, math.cos(light_angle) * 4.0, 3.0)
    
    # Bäume: (x, y, radius, height)
    baeume = [
        (-2.0, -1.5, 0.4, 1.8),
        (1.8, 2.2, 0.35, 2.0),
        (-3.5, 1.0, 0.5, 2.2),
        (3.0, -2.0, 0.45, 1.9),
        (0.0, 3.5, 0.4, 2.1),
        (-1.0, -3.0, 0.3, 1.7),
    ]
    
    # Framebuffer für RGB
    frame_r = [[0.0]*width for _ in range(height)]
    frame_g = [[0.0]*width for _ in range(height)]
    frame_b = [[0.0]*width for _ in range(height)]
    
    for y in range(height):
        for x in range(width):
            # Normalized device coordinates
            nx = (x + 0.5) / width * 2.0 - 1.0
            ny = (y + 0.5) / height * 2.0 - 1.0
            nx *= aspect
            
            # Ray direction
            dx, dy, dz = nx, ny, -1.0
            length = math.sqrt(dx*dx + dy*dy + dz*dz)
            dx, dy, dz = dx/length, dy/length, dz/length
            
            # Jitter für Temporal AA
            jitter = 0.0
            if params.jitter_enabled:
                jitter = (random.random() - 0.5) * params.jitter_strength / params.march_steps
            
            r, g, b = raymarch(cam_pos, (dx, dy, dz), light_pos, baeume, params, jitter)
            frame_r[y][x] = r
            frame_g[y][x] = g
            frame_b[y][x] = b
    
    # Blur
    if params.blur_radius > 0:
        weights = gauß_gewichte(params.blur_radius)
        frame_r = box_blur_1d(frame_r, weights, True)
        frame_r = box_blur_1d(frame_r, weights, False)
        frame_g = box_blur_1d(frame_g, weights, True)
        frame_g = box_blur_1d(frame_g, weights, False)
        frame_b = box_blur_1d(frame_b, weights, True)
        frame_b = box_blur_1d(frame_b, weights, False)
    
    # Tone mapping & Gamma
    ascii_frame = []
    for y in range(height):
        line = []
        for x in range(width):
            # Luminance
            lum = 0.2126*frame_r[y][x] + 0.7152*frame_g[y][x] + 0.0722*frame_b[y][x]
            # Gamma-Korrektur
            lum = lum ** params.gamma
            line.append(intensitaet_zu_ascii(lum, params.gamma))
        ascii_frame.append(''.join(line))
    
    return ascii_frame

def print_parameter_menu(params):
    print("\n=== 3D-Lichtspiel Parameter ===")
    attrs = [a for a in dir(params) if not a.startswith('_') and not callable(getattr(params, a))]
    for i, a in enumerate(attrs):
        print(f"  {i+1:2d}. {a}: {getattr(params, a)}")
    print("  0. Weiter (nächster Frame)")
    print("  q. Beenden")

def main():
    params = ShaderParams()
    frame = 0
    try:
        while True:
            # Frame rendern
            ascii_art = render_frame(params, frame)
            # Clear screen (ANSI)
            print("\033[2J\033[H", end='')
            for line in ascii_art:
                print(line)
            print(f"\nFrame: {frame}  |  Lichtwinkel: {frame*0.02:.2f} rad")
            
            print_parameter_menu(params)
            choice = input("Wahl: ").strip().lower()
            if choice == 'q':
                break
            if choice == '' or choice == '0':
                frame += 1
                continue
            try:
                idx = int(choice) - 1
                attrs = [a for a in dir(params) if not a.startswith('_') and not callable(getattr(params, a))]
                if 0 <= idx < len(attrs):
                    attr = attrs[idx]
                    current = getattr(params, attr)
                    new_val = input(f"Neuer Wert für {attr} (aktuell {current}): ").strip()
                    if new_val:
                        try:
                            # Typ beibehalten
                            if isinstance(current, int):
                                setattr(params, attr, int(new_val))
                            elif isinstance(current, float):
                                setattr(params, attr, float(new_val))
                            elif isinstance(current, bool):
                                setattr(params, attr, new_val.lower() in ('true', '1', 'yes', 'ja'))
                            else:
                                setattr(params, attr, new_val)
                        except ValueError:
                            print("Ungültiger Wert.")
                            time.sleep(0.5)
                else:
                    print("Ungültige Auswahl.")
                    time.sleep(0.5)
            except ValueError:
                print("Bitte Zahl oder 'q' eingeben.")
                time.sleep(0.5)
            frame += 1
    except (EOFError, KeyboardInterrupt):
        print("\n\nTschüss! Der Dodo winkt zum Abschied. 🦤")

if __name__ == "__main__":
    main()