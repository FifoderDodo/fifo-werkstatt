import math, sys, random, unicodedata, time, select

class ShaderParams:
    """Container für alle einstellbaren Shader-Parameter mit Defaults."""
    def __init__(self):
        self.penumbra_breite = 0.15
        self.umbra_dunkelheit = 0.05
        self.falloff_exponent = 2.0
        self.falloff_start = 0.5
        self.blur_radius = 3
        self.ambient = 0.02
        self.volumetric_gain = 1.2
        self.gamma = 0.6
        self.scattering_coeff = 0.35
        self.absorption_coeff = 0.12
        self.mist_density = 0.18
        self.mist_height_falloff = 0.8
        self.color_temp = 3200.0
        self.jitter_strength = 0.15
        self.phase_g = 0.6
        self.noise_seed = 42
        self.march_steps = 32
        self.jitter_enabled = True
        self.specular_intensity = 0.8
        self.specular_power = 32.0
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

def render(params: ShaderParams, bäume, licht_pos, width=80, height=24, frame=0):
    img = [[0.0 for _ in range(width)] for _ in range(height)]
    lx, ly, lz = licht_pos
    max_dist = 10.0
    step_size = max_dist / params.march_steps
    tree_height = 5.0
    
    for y in range(height):
        for x in range(width):
            nx = (x / (width - 1)) * 2 - 1
            ny = (y / (height - 1)) * 2 - 1
            ray_origin = (0.0, 0.0, -2.0)
            ray_dir = (nx, ny, 2.0)
            ray_len = math.sqrt(ray_dir[0]**2 + ray_dir[1]**2 + ray_dir[2]**2)
            ray_dir = (ray_dir[0]/ray_len, ray_dir[1]/ray_len, ray_dir[2]/ray_len)
            
            # Optional jitter for temporal AA
            if params.jitter_enabled:
                jx = noise_2d(x + frame * 0.1, y + frame * 0.1, params.noise_seed) * params.jitter_strength
                jy = noise_2d(x + frame * 0.1 + 100, y + frame * 0.1 + 100, params.noise_seed) * params.jitter_strength
                ray_dir = (ray_dir[0] + jx, ray_dir[1] + jy, ray_dir[2])
                rl = math.sqrt(ray_dir[0]**2 + ray_dir[1]**2 + ray_dir[2]**2)
                ray_dir = (ray_dir[0]/rl, ray_dir[1]/rl, ray_dir[2]/rl)
            
            accumulated = 0.0
            transmittance = 1.0
            for step in range(params.march_steps):
                t = step * step_size
                sx = ray_origin[0] + ray_dir[0] * t
                sy = ray_origin[1] + ray_dir[1] * t
                sz = ray_origin[2] + ray_dir[2] * t
                
                mist = params.mist_density * math.exp(-sz * params.mist_height_falloff)
                
                ldx = lx - sx
                ldy = ly - sy
                ldz = lz - sz
                light_dist = math.sqrt(ldx*ldx + ldy*ldy + ldz*ldz)
                if light_dist < 0.01:
                    light_dir = (0, 0, 1)
                else:
                    light_dir = (ldx/light_dist, ldy/light_dist, ldz/light_dist)
                
                cos_theta = ray_dir[0]*light_dir[0] + ray_dir[1]*light_dir[1] + ray_dir[2]*light_dir[2]
                phase = henyey_greenstein(cos_theta, params.phase_g)
                
                shadow = schattenfaktor_für_punkt(sx, sy, lx, ly, max_dist, bäume, params)
                
                attenuation = math.exp(-(params.absorption_coeff + params.scattering_coeff) * light_dist * mist)
                
                contrib = params.volumetric_gain * mist * phase * attenuation * shadow
                accumulated += contrib * transmittance
                transmittance *= math.exp(-mist * step_size)
                if transmittance < 0.001:
                    break
            
            accumulated += params.ambient
            img[y][x] = accumulated
    
    weights = gauß_gewichte(params.blur_radius)
    img = box_blur_1d(img, weights, horizontal=True)
    img = box_blur_1d(img, weights, horizontal=False)
    
    ascii_img = []
    for y in range(height):
        line = ''.join(intensitaet_zu_ascii(img[y][x], params.gamma) for x in range(width))
        ascii_img.append(line)
    return ascii_img

def main():
    params = ShaderParams()
    bäume = [
        (-3.0, -2.0, 0.5),
        (2.0, 1.5, 0.4),
        (-1.0, 3.0, 0.6),
        (4.0, -3.0, 0.5),
        (-4.0, 2.0, 0.3),
    ]
    licht_pos = [0.0, 0.0, 5.0]
    frame = 0
    width, height = 80, 24
    
    print("3D-Lichtspiel – Drücke 'q' zum Beenden, '+'/'-' für Mist-Dichte, 'p' für Pause.")
    print("Andere Tasten: 'a'/'z' für Umgebungslicht, 'b'/'n' für Blur-Radius.")
    time.sleep(1)
    
    paused = False
    try:
        while True:
            if not paused:
                # Animiere Lichtposition in einem Kreis
                angle = frame * 0.03
                licht_pos[0] = math.sin(angle) * 4.0
                licht_pos[1] = math.cos(angle) * 4.0
                licht_pos[2] = 5.0 + math.sin(angle * 0.5) * 1.0
                
                ascii_frame = render(params, bäume, licht_pos, width, height, frame)
                # Lösche Bildschirm mit ANSI-Escape (funktioniert in den meisten Terminals)
                sys.stdout.write('\x1b[2J\x1b[H')
                for line in ascii_frame:
                    sys.stdout.write(line + '\n')
                sys.stdout.flush()
                frame += 1
            
            # Non-blocking input
            rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
            if rlist:
                try:
                    line = sys.stdin.readline()
                    if not line:
                        break
                    cmd = line.strip().lower()
                    if cmd == 'q':
                        break
                    elif cmd == 'p':
                        paused = not paused
                        print("Pausiert" if paused else "Fortgesetzt")
                    elif cmd == '+':
                        params.mist_density = min(1.0, params.mist_density + 0.02)
                        print(f"Mist-Dichte: {params.mist_density:.2f}")
                    elif cmd == '-':
                        params.mist_density = max(0.0, params.mist_density - 0.02)
                        print(f"Mist-Dichte: {params.mist_density:.2f}")
                    elif cmd == 'a':
                        params.ambient = min(0.5, params.ambient + 0.01)
                        print(f"Ambient: {params.ambient:.3f}")
                    elif cmd == 'z':
                        params.ambient = max(0.0, params.ambient - 0.01)
                        print(f"Ambient: {params.ambient:.3f}")
                    elif cmd == 'b':
                        params.blur_radius = min(10, params.blur_radius + 1)
                        print(f"Blur-Radius: {params.blur_radius}")
                    elif cmd == 'n':
                        params.blur_radius = max(0, params.blur_radius - 1)
                        print(f"Blur-Radius: {params.blur_radius}")
                    elif cmd == 'h':
                        print("Hilfe: q=quit, p=pause, +/-=mist, a/z=ambient, b/n=blur")
                except EOFError:
                    break
            time.sleep(0.03)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write('\x1b[2J\x1b[H')
        print("Auf Wiedersehen!")

if __name__ == "__main__":
    main()