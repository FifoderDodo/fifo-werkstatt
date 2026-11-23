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
                dist_xy = math.hypot(cx - bx, cy - by)
                if dist_xy < br:
                    # Penumbra: weicher Schattenübergang
                    t = (dist_xy / br) / params.penumbra_breite
                    t = max(0.0, min(1.0, t))
                    shadow = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * t
                    min_f = min(min_f, shadow)
    return min_f

def raymarch_pixel(sx, sy, params, light_pos, baeume, cam_pos, cam_dir, cam_up, cam_right, fov, aspect):
    """Berechnet die Farbe eines Pixels durch Raymarching."""
    # Strahlrichtung im Weltraum
    px = (sx + 0.5) * 2.0 - 1.0  # -1 bis 1
    py = (sy + 0.5) * 2.0 - 1.0
    ray_dir = (
        cam_dir[0] +
        cam_right[0] * px * math.tan(fov * 0.5) * aspect +
        cam_up[0] * py * math.tan(fov * 0.5)
    ), (
        cam_dir[1] +
        cam_right[1] * px * math.tan(fov * 0.5) * aspect +
        cam_up[1] * py * math.tan(fov * 0.5)
    ), (
        cam_dir[2] +
        cam_right[2] * px * math.tan(fov * 0.5) * aspect +
        cam_up[2] * py * math.tan(fov * 0.5)
    )
    # Normalisieren
    rlen = math.sqrt(ray_dir[0]**2 + ray_dir[1]**2 + ray_dir[2]**2)
    ray_dir = (ray_dir[0]/rlen, ray_dir[1]/rlen, ray_dir[2]/rlen)
    
    # Raymarching Parameter
    max_dist = 30.0
    step_size = max_dist / params.march_steps
    if params.adaptive_steps:
        step_size *= params.min_step_factor
    
    # Lichtvektor
    lx, ly, lz = light_pos
    light_vec = (lx - cam_pos[0], ly - cam_pos[1], lz - cam_pos[2])
    light_dist = math.sqrt(light_vec[0]**2 + light_vec[1]**2 + light_vec[2]**2)
    light_dir = (light_vec[0]/light_dist, light_vec[1]/light_dist, light_vec[2]/light_dist)
    
    # Farbe akkumulieren
    color = [0.0, 0.0, 0.0]
    transmittance = 1.0
    
    # Jitter für temporales Rauschen
    jitter = 0.0
    if params.jitter_enabled:
        jitter = (random.random() - 0.5) * params.jitter_strength * step_size
    
    for step in range(params.march_steps):
        t = (step + 0.5) * step_size + jitter
        if t > max_dist:
            break
        # Aktuelle Position
        pos = (cam_pos[0] + ray_dir[0] * t,
               cam_pos[1] + ray_dir[1] * t,
               cam_pos[2] + ray_dir[2] * t)
        
        # Dichte an dieser Position
        density = mist_dichte(pos, params)
        if density < params.early_exit_threshold:
            continue
        
        # Schattenfaktor
        shadow = schattenfaktor_3d(pos, light_pos, baeume, params)
        
        # Phase function (Henyey-Greenstein)
        cos_theta = ray_dir[0]*light_dir[0] + ray_dir[1]*light_dir[1] + ray_dir[2]*light_dir[2]
        phase = henyey_greenstein(cos_theta, params.phase_g)
        
        # Streuung
        scatter = density * params.scattering_coeff * phase * shadow
        
        # Absorption
        absorption = density * params.absorption_coeff
        transmittance *= math.exp(-absorption * step_size)
        
        # Lichtfarbe (Farbtemperatur)
        light_color = kelvin_to_rgb_factor(params.color_temp)
        
        # Akkumulation
        for c in range(3):
            color[c] += scatter * light_color[c] * transmittance * step_size * params.volumetric_gain
        
        # Adaptive step size: wenn Dichte hoch, kleinere Schritte
        if params.adaptive_steps and density > 0.1:
            step_size = max(step_size * params.min_step_factor, max_dist / params.march_steps * params.min_step_factor)
        else:
            step_size = min(step_size * params.max_step_factor, max_dist / params.march_steps * params.max_step_factor)
    
    # Ambient light
    for c in range(3):
        color[c] += params.ambient
    
    return color

def render_frame(params, light_pos, baeume, cam_pos, cam_dir, cam_up, cam_right, fov, aspect, width, height):
    """Rendert ein ganzes Frame in einen Float-Puffer (RGB)."""
    frame = [[[0.0, 0.0, 0.0] for _ in range(width)] for __ in range(height)]
    for y in range(height):
        for x in range(width):
            col = raymarch_pixel(x, y, params, light_pos, baeume, cam_pos, cam_dir, cam_up, cam_right, fov, aspect)
            frame[y][x] = col
    return frame

def bloom_pass(frame, params):
    """Wendet einen einfachen Bloom-Effekt an: extrahiere helle Bereiche, blurre, addiere zurück."""
    h, w = len(frame), len(frame[0])
    # Extrahiere Helligkeit (Luminanz)
    bright = [[0.0 for _ in range(w)] for __ in range(h)]
    for y in range(h):
        for x in range(w):
            r, g, b = frame[y][x]
            lum = 0.2126*r + 0.7152*g + 0.0722*b
            if lum > params.bloom_threshold:
                bright[y][x] = (lum - params.bloom_threshold) * params.bloom_intensity
    # Blur
    weights = gauß_gewichte(params.bloom_radius)
    blur_h = box_blur_1d(bright, weights, horizontal=True)
    blur_v = box_blur_1d(blur_h, weights, horizontal=False)
    # Add back
    result = [[[0.0, 0.0, 0.0] for _ in range(w)] for __ in range(h)]
    for y in range(h):
        for x in range(w):
            add = blur_v[y][x]
            r, g, b = frame[y][x]
            result[y][x] = [r + add, g + add, b + add]
    return result

def tonemap_and_ascii(frame, params):
    """Wendet Tonemapping (Gamma, Vibrancy) an und wandelt in ASCII um."""
    h, w = len(frame), len(frame[0])
    ascii_lines = []
    for y in range(h):
        line = []
        for x in range(w):
            r, g, b = frame[y][x]
            # Vibrancy: erhöhe Sättigung
            max_c = max(r, g, b)
            if max_c > 0:
                r = r * params.vibrancy + (1 - params.vibrancy) * max_c
                g = g * params.vibrancy + (1 - params.vibrancy) * max_c
                b = b * params.vibrancy + (1 - params.vibrancy) * max_c
            # Clamp
            r = min(1.0, max(0.0, r))
            g = min(1.0, max(0.0, g))
            b = min(1.0, max(0.0, b))
            # Luminanz für ASCII
            lum = 0.2126*r + 0.7152*g + 0.0722*b
            # Gamma
            lum = lum ** params.gamma
            line.append(intensitaet_zu_ascii(lum, gamma=1.0))
        ascii_lines.append(''.join(line))
    return '\n'.join(ascii_lines)

def main():
    print("3D-Lichtspiel - Volumetrisches Licht im herbstlichen Park")
    print("Steuerung: WASD - Licht bewegen, Q/E - Höhe, +/- Parameter, R - Reset, X - Beenden")
    
    params = ShaderParams()
    
    # Szene: Bäume (x, y, radius, height)
    baeume = [
        (-5.0, -3.0, 1.2, 4.0),
        (4.0, 2.0, 1.0, 3.5),
        (-2.0, 5.0, 0.8, 3.0),
        (6.0, -4.0, 1.5, 5.0),
        (0.0, 0.0, 0.5, 2.0),
        (-7.0, 1.0, 1.0, 4.0),
        (3.0, -6.0, 1.2, 3.5),
    ]
    
    # Kamera
    cam_pos = (0.0, -10.0, 2.0)
    cam_dir = (0.0, 1.0, -0.2)  # leicht nach unten
    clen = math.sqrt(cam_dir[0]**2 + cam_dir[1]**2 + cam_dir[2]**2)
    cam_dir = (cam_dir[0]/clen, cam_dir[1]/clen, cam_dir[2]/clen)
    cam_up = (0.0, 0.0, 1.0)
    # Right = cross(dir, up)
    cam_right = (cam_dir[1]*cam_up[2] - cam_dir[2]*cam_up[1],
                 cam_dir[2]*cam_up[0] - cam_dir[0]*cam_up[2],
                 cam_dir[0]*cam_up[1] - cam_dir[1]*cam_up[0])
    rlen = math.sqrt(cam_right[0]**2 + cam_right[1]**2 + cam_right[2]**2)
    cam_right = (cam_right[0]/rlen, cam_right[1]/rlen, cam_right[2]/rlen)
    # Recompute up to be orthogonal
    cam_up = (cam_right[1]*cam_dir[2] - cam_right[2]*cam_dir[1],
              cam_right[2]*cam_dir[0] - cam_right[0]*cam_dir[2],
              cam_right[0]*cam_dir[1] - cam_right[1]*cam_dir[0])
    
    fov = math.radians(60.0)
    aspect = 2.0  # Breite/Höhe in Zeichen (ca. 80x40 -> 2.0)
    width, height = 80, 40
    
    # Lichtposition
    light_pos = [0.0, 0.0, 5.0]
    
    try:
        while True:
            # Frame rendern
            frame = render_frame(params, light_pos, baeume, cam_pos, cam_dir, cam_up, cam_right, fov, aspect, width, height)
            # Bloom
            frame = bloom_pass(frame, params)
            # Tonemap & ASCII
            ascii_art = tonemap_and_ascii(frame, params)
            # Ausgabe
            sys.stdout.write('\033[H\033[J')  # Clear screen (ANSI)
            sys.stdout.write(ascii_art + '\n')
            sys.stdout.write(f"Light: ({light_pos[0]:.1f}, {light_pos[1]:.1f}, {light_pos[2]:.1f})  Steps: {params.march_steps}  Gain: {params.volumetric_gain:.2f}\n")
            sys.stdout.write("Befehl (WASD/QE/+/-/R/X): ")
            sys.stdout.flush()
            
            try:
                cmd = input().strip().lower()
            except EOFError:
                print("\nAuf Wiedersehen!")
                break
            
            if not cmd:
                continue
            if cmd == 'x':
                print("Auf Wiedersehen!")
                break
            elif cmd == 'r':
                params = ShaderParams()
                light_pos = [0.0, 0.0, 5.0]
            elif cmd == 'w':
                light_pos[1] += 0.5
            elif cmd == 's':
                light_pos[1] -= 0.5
            elif cmd == 'a':
                light_pos[0] -= 0.5
            elif cmd == 'd':
                light_pos[0] += 0.5
            elif cmd == 'q':
                light_pos[2] += 0.5
            elif cmd == 'e':
                light_pos[2] = max(0.5, light_pos[2] - 0.5)
            elif cmd == '+':
                params.volumetric_gain = min(5.0, params.volumetric_gain + 0.1)
            elif cmd == '-':
                params.volumetric_gain = max(0.1, params.volumetric_gain - 0.1)
            elif cmd == 'b':
                params.bloom_intensity = min(2.0, params.bloom_intensity + 0.05)
            elif cmd == 'n':
                params.bloom_intensity = max(0.0, params.bloom_intensity - 0.05)
            elif cmd == 'm':
                params.mist_density = min(1.0, params.mist_density + 0.02)
            elif cmd == 'k':
                params.mist_density = max(0.0, params.mist_density - 0.02)
            else:
                print(f"Unbekannter Befehl: {cmd}")
    except KeyboardInterrupt:
        print("\nAuf Wiedersehen!")

if __name__ == "__main__":
    main()