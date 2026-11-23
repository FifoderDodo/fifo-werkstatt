import math, sys, random, unicodedata, time, select

class ShaderParams:
    """Container für alle einstellbaren Shader‑Parameter mit Defaults."""
    def __init__(self):
        self.penumbra_breite = 0.15
        self.umbra_dunkelheit = 0.05
        self.falloff_exponent = 2.0
        self.falloff_start = 0.5
        self.blur_radius = 3
        self.ambient = 0.05
        self.volumetric_gain = 2.5
        self.gamma = 0.55
        self.scattering_coeff = 0.45
        self.absorption_coeff = 0.08
        self.mist_density = 0.22
        self.mist_height_falloff = 0.8
        self.color_temp = 3000.0
        self.jitter_strength = 0.12
        self.phase_g = 0.6
        self.noise_seed = 42
        self.march_steps = 12  # reduziert für bessere Performance
        self.jitter_enabled = True
        self.specular_intensity = 0.6
        self.specular_power = 24.0
        self.specular_noise_scale = 0.5
        self.light_radius = 0.8
        self.vibrancy = 1.2
    def klonen(self):
        k = ShaderParams()
        k.__dict__.update(self.__dict__)
        return k

def _norm(s: str) -> str:
    return unicodedata.normalize('NFC', s).strip().lower()

def gauß_gewichte(kernel_radius: int) -> list:
    size = kernel_radius * 2 + 1
    sigma = kernel_radius / 2.0
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

def schattenfaktor_für_punkt(px, py, qx, qy, light_radius, bäume, params):
    dx, dy = px - qx, py - qy
    dist_lp = math.hypot(dx, dy)
    if dist_lp < 0.01:
        return 1.0
    ux, uy = dx / dist_lp, dy / dist_lp
    min_faktor = 1.0
    for bx, by, br in bäume:
        vx, vy = bx - qx, by - qy
        dist_lt = math.hypot(vx, vy)
        if dist_lt < 0.01:
            continue
        proj = vx * ux + vy * uy
        if proj <= 0.01 or proj >= dist_lp:
            continue
        abstand = abs(vx * uy - vy * ux)
        factor = dist_lp / dist_lt
        penumbra_radius = br * factor + light_radius * (factor - 1.0)
        umbra_radius = max(0.0, br * factor - light_radius * (factor - 1.0))
        if abstand >= penumbra_radius:
            continue
        if abstand <= umbra_radius:
            faktor = params.umbra_dunkelheit
        else:
            t = (abstand - umbra_radius) / (penumbra_radius - umbra_radius) if penumbra_radius > umbra_radius else 0.0
            t = max(0.0, min(1.0, t))
            faktor = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * t
        if faktor < min_faktor:
            min_faktor = faktor
    return min_faktor

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
    u = fx * fx * (3.0 - 2.0 * fx)
    v = fy * fy * (3.0 - 2.0 * fy)
    w = fz * fz * (3.0 - 2.0 * fz)
    a = hash3d(ix, iy, iz)
    b = hash3d(ix + 1, iy, iz)
    c = hash3d(ix, iy + 1, iz)
    d = hash3d(ix + 1, iy + 1, iz)
    e = hash3d(ix, iy, iz + 1)
    f = hash3d(ix + 1, iy, iz + 1)
    g = hash3d(ix, iy + 1, iz + 1)
    h = hash3d(ix + 1, iy + 1, iz + 1)
    x1 = a + (b - a) * u
    x2 = c + (d - c) * u
    y1 = x1 + (x2 - x1) * v
    x3 = e + (f - e) * u
    x4 = g + (h - g) * u
    y2 = x3 + (x4 - x3) * v
    return y1 + (y2 - y1) * w

def mist_dichte(pos, params):
    """Mist-Dichte mit Höhenabfall und 3D-Noise."""
    x, y, z = pos
    basis = params.mist_density * math.exp(-z * params.mist_height_falloff)
    n = noise_3d(x * 0.5, y * 0.5, z * 0.3, params.noise_seed)
    return basis * (1.0 + 0.4 * n)

def dichte_gradient(pos, params, eps=0.12):
    """Numerischer Gradient der Mist-Dichte für Normalen-Berechnung."""
    x, y, z = pos
    dx = mist_dichte((x + eps, y, z), params) - mist_dichte((x - eps, y, z), params)
    dy = mist_dichte((x, y + eps, z), params) - mist_dichte((x, y - eps, z), params)
    dz = mist_dichte((x, y, z + eps), params) - mist_dichte((x, y, z - eps), params)
    length = math.sqrt(dx*dx + dy*dy + dz*dz)
    if length < 1e-6:
        return (0.0, 0.0, 1.0)
    return (dx/length, dy/length, dz/length)

def raymarch(origin, direction, params, bäume, light_pos, far=30.0):
    """Volumetric Raymarching mit Schatten, Scattering und Specular."""
    steps = params.march_steps
    step_size = far / steps
    r, g, b = 0.0, 0.0, 0.0
    transmittance = 1.0
    light_dir = (light_pos[0] - origin[0], light_pos[1] - origin[1], light_pos[2] - origin[2])
    light_dist = math.sqrt(light_dir[0]**2 + light_dir[1]**2 + light_dir[2]**2)
    light_dir = (light_dir[0]/light_dist, light_dir[1]/light_dist, light_dir[2]/light_dist)
    view_dir = (-direction[0], -direction[1], -direction[2])
    for i in range(steps):
        t = (i + 0.5) * step_size
        if params.jitter_enabled:
            t += (random.random() - 0.5) * params.jitter_strength * step_size
        pos = (origin[0] + direction[0]*t,
               origin[1] + direction[1]*t,
               origin[2] + direction[2]*t)
        density = mist_dichte(pos, params)
        if density < 1e-4:
            continue
        # Schatten
        shadow = schattenfaktor_für_punkt(pos[0], pos[1], light_pos[0], light_pos[1],
                                          params.light_radius, bäume, params)
        # Phase function
        cos_theta = (direction[0]*light_dir[0] + direction[1]*light_dir[1] + direction[2]*light_dir[2])
        phase = henyey_greenstein(cos_theta, params.phase_g)
        # Normal für Specular
        normal = dichte_gradient(pos, params)
        half_vec = ((light_dir[0]+view_dir[0])*0.5, (light_dir[1]+view_dir[1])*0.5, (light_dir[2]+view_dir[2])*0.5)
        half_len = math.sqrt(half_vec[0]**2 + half_vec[1]**2 + half_vec[2]**2)
        if half_len > 0:
            half_vec = (half_vec[0]/half_len, half_vec[1]/half_len, half_vec[2]/half_len)
        spec = max(0.0, normal[0]*half_vec[0] + normal[1]*half_vec[1] + normal[2]*half_vec[2])
        spec = spec ** params.specular_power
        spec *= params.specular_intensity
        # Noise auf Specular
        spec_noise = noise_3d(pos[0]*params.specular_noise_scale, pos[1]*params.specular_noise_scale, pos[2]*params.specular_noise_scale, params.noise_seed+1)
        spec *= (1.0 + 0.3 * spec_noise)
        # Lichtbeitrag
        light_intensity = shadow * phase * (1.0 / (1.0 + t * params.falloff_start)) ** params.falloff_exponent
        scatter = density * params.scattering_coeff * light_intensity
        absorb = density * params.absorption_coeff
        transmittance *= math.exp(-absorb * step_size)
        color_factor = kelvin_to_rgb_factor(params.color_temp)
        r += transmittance * scatter * color_factor[0] * params.volumetric_gain
        g += transmittance * scatter * color_factor[1] * params.volumetric_gain
        b += transmittance * scatter * color_factor[2] * params.volumetric_gain
        # Specular additiv
        r += transmittance * spec * color_factor[0]
        g += transmittance * spec * color_factor[1]
        b += transmittance * spec * color_factor[2]
        if transmittance < 0.01:
            break
    # Ambient
    r += params.ambient * color_factor[0]
    g += params.ambient * color_factor[1]
    b += params.ambient * color_factor[2]
    return (r, g, b)

def render_frame(params, bäume, light_pos, cam_pos, cam_target, fov, width, height):
    """Rendert ein Frame als 2D-Array von (r,g,b)."""
    # Kamera-Basis
    forward = (cam_target[0]-cam_pos[0], cam_target[1]-cam_pos[1], cam_target[2]-cam_pos[2])
    flen = math.sqrt(forward[0]**2 + forward[1]**2 + forward[2]**2)
    forward = (forward[0]/flen, forward[1]/flen, forward[2]/flen)
    right = (forward[2], 0.0, -forward[0])  # vereinfacht, up = (0,1,0)
    rlen = math.sqrt(right[0]**2 + right[2]**2)
    right = (right[0]/rlen, 0.0, right[2]/rlen)
    up = (0.0, 1.0, 0.0)
    aspect = width / height
    tan_half_fov = math.tan(fov * 0.5 * math.pi / 180.0)
    frame = [[(0.0,0.0,0.0) for _ in range(width)] for __ in range(height)]
    for y in range(height):
        for x in range(width):
            ndc_x = (x + 0.5) / width * 2.0 - 1.0
            ndc_y = 1.0 - (y + 0.5) / height * 2.0
            ray_x = forward[0] + right[0] * ndc_x * aspect * tan_half_fov + up[0] * ndc_y * tan_half_fov
            ray_y = forward[1] + right[1] * ndc_x * aspect * tan_half_fov + up[1] * ndc_y * tan_half_fov
            ray_z = forward[2] + right[2] * ndc_x * aspect * tan_half_fov + up[2] * ndc_y * tan_half_fov
            rlen = math.sqrt(ray_x**2 + ray_y**2 + ray_z**2)
            ray_dir = (ray_x/rlen, ray_y/rlen, ray_z/rlen)
            frame[y][x] = raymarch(cam_pos, ray_dir, params, bäume, light_pos)
    return frame

def tonemap_and_gamma(frame, gamma, vibrancy):
    """Wendet Vibrancy und Gamma-Korrektur an."""
    h, w = len(frame), len(frame[0])
    out = [[(0,0,0) for _ in range(w)] for __ in range(h)]
    for y in range(h):
        for x in range(w):
            r, g, b = frame[y][x]
            # Vibrancy: Sättigung erhöhen
            max_c = max(r, g, b)
            if max_c > 0:
                r = r + (r - max_c) * (vibrancy - 1.0)
                g = g + (g - max_c) * (vibrancy - 1.0)
                b = b + (b - max_c) * (vibrancy - 1.0)
            r = min(1.0, max(0.0, r ** gamma))
            g = min(1.0, max(0.0, g ** gamma))
            b = min(1.0, max(0.0, b ** gamma))
            out[y][x] = (int(r*255), int(g*255), int(b*255))
    return out

def apply_blur(frame, radius):
    """Trenntbaren Box-Blur auf RGB anwenden."""
    if radius <= 0:
        return frame
    h, w = len(frame), len(frame[0])
    r_ch = [[frame[y][x][0] for x in range(w)] for y in range(h)]
    g_ch = [[frame[y][x][1] for x in range(w)] for y in range(h)]
    b_ch = [[frame[y][x][2] for x in range(w)] for y in range(h)]
    weights = gauß_gewichte(radius)
    r_ch = box_blur_1d(box_blur_1d(r_ch, weights, True), weights, False)
    g_ch = box_blur_1d(box_blur_1d(g_ch, weights, True), weights, False)
    b_ch = box_blur_1d(box_blur_1d(b_ch, weights, True), weights, False)
    out = [[(0,0,0) for _ in range(w)] for __ in range(h)]
    for y in range(h):
        for x in range(w):
            out[y][x] = (int(r_ch[y][x]), int(g_ch[y][x]), int(b_ch[y][x]))
    return out

def frame_to_ansi(frame):
    """Konvertiert RGB-Frame in ANSI-Escape-Strings pro Zeile."""
    lines = []
    for row in frame:
        line = ''
        for r, g, b in row:
            line += f'\x1b[38;2;{r};{g};{b}m█'
        line += '\x1b[0m'
        lines.append(line)
    return '\n'.join(lines)

def print_menu(params):
    print('\n--- 3D-Lichtspiel Parameter ---')
    attrs = [a for a in dir(params) if not a.startswith('_') and not callable(getattr(params, a))]
    for i, a in enumerate(attrs):
        print(f'  {i+1:2d}. {a} = {getattr(params, a)}')
    print('  0. Rendern')
    print('  q. Beenden')

def parse_input(params, choice):
    attrs = [a for a in dir(params) if not a.startswith('_') and not callable(getattr(params, a))]
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(attrs):
            attr = attrs[idx]
            val = input(f'Neuer Wert für {attr} (aktuell {getattr(params, attr)}): ')
            if val.strip():
                try:
                    setattr(params, attr, type(getattr(params, attr))(val))
                except ValueError:
                    print('Ungültiger Wert.')
            return True
    except ValueError:
        pass
    return False

def main():
    random.seed(42)
    params = ShaderParams()
    # Beispiel-Szene
    bäume = [(-3.0, -1.0, 0.8), (2.5, 0.5, 0.6), (-1.0, 2.0, 0.7), (4.0, -2.0, 0.5)]
    light_pos = (0.0, 0.0, 5.0)
    cam_pos = (0.0, -8.0, 2.0)
    cam_target = (0.0, 0.0, 1.0)
    fov = 70.0
    width, height = 80, 40
    print('3D-Lichtspiel – Herbstlicher Park')
    print('Drücke Enter für Standard-Render oder wähle Parameter.')
    while True:
        try:
            print_menu(params)
            choice = input('> ').strip().lower()
            if choice == 'q':
                print('Tschüss!')
                break
            if choice == '0' or choice == '':
                print('Rendere...')
                start = time.time()
                frame = render_frame(params, bäume, light_pos, cam_pos, cam_target, fov, width, height)
                frame = tonemap_and_gamma(frame, params.gamma, params.vibrancy)
                frame = apply_blur(frame, params.blur_radius)
                ansi = frame_to_ansi(frame)
                print(ansi)
                print(f'Renderzeit: {time.time()-start:.2f}s')
            else:
                parse_input(params, choice)
        except EOFError:
            print('\nEOF – Programm wird beendet.')
            break
        except KeyboardInterrupt:
            print('\nAbbruch.')
            break

if __name__ == '__main__':
    main()