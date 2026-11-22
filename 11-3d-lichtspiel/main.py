import math, sys, random, unicodedata, time, select

class ShaderParams:
    """Container für alle einstellbaren Shader‑Parameter mit Defaults."""
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
        self.march_steps = 16          # reduziert für Performance
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

def render(params: ShaderParams, bäume, licht_pos, width=40, height=12, frame=0):
    """Ray‑March vom Kamerapunkt (0,0,10) auf die Ground‑Plane z=0.
    Gibt Liste von ASCII‑Zeilen zurück."""
    img = [[0.0 for _ in range(width)] for _ in range(height)]
    lx, ly, lz = licht_pos
    cam_x, cam_y, cam_z = 0.0, 0.0, 10.0
    world_w, world_h = 10.0, 10.0 * height / width
    max_dist = 15.0
    step_size = max_dist / max(1, params.march_steps)

    # 1. Schattenkarte (nur Ground‑Plane) – für jedes Pixel prüfen, ob Licht durch Bäume blockiert
    shadow_map = [[1.0 for _ in range(width)] for __ in range(height)]
    for py_idx in range(height):
        for px_idx in range(width):
            # Weltkoordinaten des Pixels auf Ground-Plane
            wx = (px_idx / width - 0.5) * world_w
            wy = (py_idx / height - 0.5) * world_h
            # Abstand Licht -> Pixel
            dx = wx - lx
            dy = wy - ly
            dist_light = math.hypot(dx, dy)
            if dist_light < 0.01:
                shadow_map[py_idx][px_idx] = 1.0
                continue
            shadow = 1.0
            for bx, by, br in bäume:
                vx = bx - lx
                vy = by - ly
                dqb = math.hypot(vx, vy)
                if dqb < 0.01:
                    continue
                proj = (vx * dx + vy * dy) / dist_light
                if proj <= 0.01 or proj >= dist_light:
                    continue
                abstand = abs(vx * dy - vy * dx) / dist_light
                if abstand >= br:
                    continue
                shadow_radius = br * (dist_light / dqb)
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
                if faktor < shadow:
                    shadow = faktor
            shadow_map[py_idx][px_idx] = shadow

    # Optionaler Blur auf Schattenkarte für weichere Kanten
    if params.blur_radius > 0:
        gewichte = gauß_gewichte(params.blur_radius)
        shadow_map = box_blur_1d(shadow_map, gewichte, True)
        shadow_map = box_blur_1d(shadow_map, gewichte, False)

    # 2. Ray-Marching pro Pixel
    r_temp, g_temp, b_temp = kelvin_to_rgb_factor(params.color_temp)
    
    for py_idx in range(height):
        for px_idx in range(width):
            # Ray direction
            rx = (px_idx / width - 0.5) * world_w
            ry = (py_idx / height - 0.5) * world_h
            rz = -cam_z  # zeigt nach unten auf Ground-Plane
            rlen = math.sqrt(rx*rx + ry*ry + rz*rz)
            rx, ry, rz = rx/rlen, ry/rlen, rz/rlen
            
            # Light direction from pixel to light
            ldx = lx - rx * 0  # wird pro Schritt aktualisiert
            ldy = ly - ry * 0
            ldz = lz - rz * 0
            
            accumulated = 0.0
            transmittance = 1.0
            
            # Jitter für dieses Pixel
            jitter = 0.0
            if params.jitter_enabled:
                jitter = noise_2d(px_idx * 0.1, py_idx * 0.1, params.noise_seed + frame) * params.jitter_strength
            
            for step in range(params.march_steps):
                t = (step + 0.5 + jitter) * step_size
                sx = cam_x + rx * t
                sy = cam_y + ry * t
                sz = cam_z + rz * t
                
                if sz <= 0.0:
                    # Ground hit
                    ground_x = sx
                    ground_y = sy
                    # Shadow lookup
                    sm_x = int((ground_x / world_w + 0.5) * width)
                    sm_y = int((ground_y / world_h + 0.5) * height)
                    if 0 <= sm_x < width and 0 <= sm_y < height:
                        shadow = shadow_map[sm_y][sm_x]
                    else:
                        shadow = 1.0
                    
                    # Direct lighting auf Ground
                    ldx = lx - ground_x
                    ldy = ly - ground_y
                    ldz = lz - 0.0
                    ldist = math.sqrt(ldx*ldx + ldy*ldy + ldz*ldz)
                    if ldist > 0.01:
                        ldx, ldy, ldz = ldx/ldist, ldy/ldist, ldz/ldist
                        # Phase function (cos theta between view and light)
                        cos_theta = rx * ldx + ry * ldy + rz * ldz
                        phase = henyey_greenstein(cos_theta, params.phase_g)
                        falloff = 1.0 / (1.0 + (ldist * params.falloff_start) ** params.falloff_exponent)
                        direct = params.specular_intensity * falloff * phase * shadow
                        # Specular highlight mit Noise
                        spec_noise = noise_2d(ground_x * params.specular_noise_scale, ground_y * params.specular_noise_scale, params.noise_seed + 100)
                        direct *= (1.0 + spec_noise * 0.3)
                        accumulated += direct * transmittance
                    break
                
                # Volumetric scattering
                # Mist density mit Height falloff
                mist = params.mist_density * math.exp(-sz * params.mist_height_falloff)
                # Noise für heterogenes Mist
                mist *= 1.0 + 0.3 * noise_3d(sx * 0.5, sy * 0.5, sz * 0.5, params.noise_seed + 200)
                
                # Light direction zu diesem Sample
                ldx = lx - sx
                ldy = ly - sy
                ldz = lz - sz
                ldist = math.sqrt(ldx*ldx + ldy*ldy + ldz*ldz)
                if ldist > 0.01:
                    ldx, ldy, ldz = ldx/ldist, ldy/ldist, ldz/ldist
                    cos_theta = rx * ldx + ry * ldy + rz * ldz
                    phase = henyey_greenstein(cos_theta, params.phase_g)
                    falloff = 1.0 / (1.0 + (ldist * params.falloff_start) ** params.falloff_exponent)
                    
                    # Shadow für volumetric sample (approximiert via Ground shadow map)
                    # Projiziere Sample auf Ground entlang Light direction
                    if ldz < -0.001:
                        t_ground = -sz / ldz
                        gx = sx + ldx * t_ground
                        gy = sy + ldy * t_ground
                        sm_x = int((gx / world_w + 0.5) * width)
                        sm_y = int((gy / world_h + 0.5) * height)
                        if 0 <= sm_x < width and 0 <= sm_y < height:
                            shadow = shadow_map[sm_y][sm_x]
                        else:
                            shadow = 1.0
                    else:
                        shadow = 1.0
                    
                    scatter = mist * params.scattering_coeff * phase * falloff * shadow
                    absorption = mist * params.absorption_coeff
                    
                    accumulated += scatter * transmittance
                    transmittance *= math.exp(-absorption * step_size)
                    
                    if transmittance < 0.01:
                        break
            
            # Ambient hinzufügen
            accumulated += params.ambient * transmittance
            
            # Volumetric gain und Farbtemperatur (nur Intensität für ASCII)
            accumulated *= params.volumetric_gain
            
            # Clamp und speichern
            img[py_idx][px_idx] = min(1.0, max(0.0, accumulated))

    # In ASCII umwandeln
    ascii_lines = []
    for row in img:
        line = ''.join(intensitaet_zu_ascii(v, params.gamma) for v in row)
        ascii_lines.append(line)
    return ascii_lines


def main():
    print("3D-Lichtspiel – volumetrisches Licht im herbstlichen Park")
    print("Steuerung: w/s/a/d = Licht bewegen, r = reset, q = quit")
    print("Drücke Enter für nächsten Frame (oder warte 0.1s)...")
    
    params = ShaderParams()
    
    # Bäume: (x, y, radius)
    bäume = [
        (-2.0, -1.5, 0.8),
        (1.5, 2.0, 0.6),
        (-3.0, 2.5, 0.9),
        (3.0, -2.0, 0.7),
        (0.0, 3.0, 0.5),
        (-1.0, -3.0, 0.6),
    ]
    
    licht_pos = [0.0, 0.0, 4.0]
    licht_radius = 3.5
    licht_winkel = 0.0
    frame = 0
    width, height = 60, 18
    
    try:
        while True:
            # Animation: Licht kreist langsam
            licht_winkel += 0.02
            licht_pos[0] = math.cos(licht_winkel) * licht_radius
            licht_pos[1] = math.sin(licht_winkel) * licht_radius
            
            lines = render(params, bäume, licht_pos, width, height, frame)
            
            # Clear screen und zeichnen
            print('\033[2J\033[H', end='')
            for line in lines:
                print(line)
            print(f"Frame: {frame}  Licht: ({licht_pos[0]:.1f}, {licht_pos[1]:.1f}, {licht_pos[2]:.1f})")
            print("[w/s/a/d/r/q] > ", end='', flush=True)
            
            # Non-blocking input mit Timeout
            ready, _, _ = select.select([sys.stdin], [], [], 0.1)
            if ready:
                try:
                    cmd = sys.stdin.readline().strip().lower()
                    if cmd == 'q':
                        break
                    elif cmd == 'r':
                        licht_pos[0] = 0.0
                        licht_pos[1] = 0.0
                        licht_winkel = 0.0
                    elif cmd == 'w':
                        licht_pos[1] += 0.5
                    elif cmd == 's':
                        licht_pos[1] -= 0.5
                    elif cmd == 'a':
                        licht_pos[0] -= 0.5
                    elif cmd == 'd':
                        licht_pos[0] += 0.5
                except EOFError:
                    break
            
            frame += 1
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    
    print("\nBis zum nächsten Traum...")

if __name__ == '__main__':
    main()