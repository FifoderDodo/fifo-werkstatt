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
    for iy in range(height):
        for ix in range(width):
            # Normalized device coordinates
            nx = (ix + 0.5) / width
            ny = (iy + 0.5) / height
            # World coordinates on near plane
            wx = (nx - 0.5) * world_w
            wy = (ny - 0.5) * world_h
            # Ray direction from camera
            rdx, rdy, rdz = wx - cam_x, wy - cam_y, -cam_z
            rlen = math.hypot(rdx, rdy, rdz)
            rdx, rdy, rdz = rdx / rlen, rdy / rlen, rdz / rlen
            
            acc = 0.0
            transmittance = 1.0
            for step in range(params.march_steps):
                t = step * step_size
                px = cam_x + rdx * t
                py = cam_y + rdy * t
                pz = cam_z + rdz * t
                if pz <= 0.0:
                    # Ground intersection
                    ground_dist = t
                    # Specular reflection on wet ground
                    if params.specular_intensity > 0:
                        # Light direction at ground point
                        ldx, ldy, ldz = lx - px, ly - py, lz - pz
                        llen = math.hypot(ldx, ldy, ldz)
                        ldx, ldy, ldz = ldx / llen, ldy / llen, ldz / llen
                        # View direction (towards camera)
                        vdx, vdy, vdz = -rdx, -rdy, -rdz
                        # Half vector
                        hx, hy, hz = ldx + vdx, ldy + vdy, ldz + vdz
                        hlen = math.hypot(hx, hy, hz)
                        if hlen > 0:
                            hx, hy, hz = hx / hlen, hy / hlen, hz / hlen
                            # Normal is (0,0,1)
                            ndoth = hz
                            if ndoth > 0:
                                spec = (ndoth ** params.specular_power) * params.specular_intensity
                                # Add noise to break up specular
                                n = noise_2d(px * params.specular_noise_scale, py * params.specular_noise_scale, params.noise_seed + frame)
                                spec *= 0.5 + 0.5 * n
                                acc += spec * transmittance
                    break
                
                # Light direction from sample point
                ldx, ldy, ldz = lx - px, ly - py, lz - pz
                llen = math.hypot(ldx, ldy, ldz)
                if llen < 0.01:
                    continue
                ldx, ldy, ldz = ldx / llen, ldy / llen, ldz / llen
                
                # Phase function
                cos_theta = rdx * ldx + rdy * ldy + rdz * ldz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                
                # Falloff
                falloff = 1.0 / max(1e-3, llen ** params.falloff_exponent)
                if llen > params.falloff_start:
                    falloff *= (params.falloff_start / llen) ** params.falloff_exponent
                
                # Shadow
                shadow = schattenfaktor_für_punkt(px, py, lx, ly, llen, bäume, params)
                
                # Mist density with height falloff
                mist = params.mist_density * math.exp(-pz * params.mist_height_falloff)
                # Add 3D noise for volumetric variation
                if params.jitter_enabled:
                    mist += noise_3d(px * 0.5, py * 0.5, pz * 0.5, params.noise_seed + frame) * params.jitter_strength
                mist = max(0.0, mist)
                
                # Absorption
                absorption = math.exp(-params.absorption_coeff * t)
                
                # Scattering contribution
                scatter = phase * falloff * shadow * mist * params.scattering_coeff * absorption * params.volumetric_gain
                acc += scatter * transmittance * step_size
                transmittance *= math.exp(-mist * params.absorption_coeff * step_size)
                if transmittance < 0.01:
                    break
            
            # Add ambient
            acc += params.ambient
            img[iy][ix] = acc
    return img

def main():
    params = ShaderParams()
    # Generate some trees
    random.seed(12345)
    bäume = []
    for _ in range(12):
        bx = random.uniform(-5.5, 5.5)
        by = random.uniform(-5.5, 5.5)
        br = random.uniform(0.3, 0.7)
        bäume.append((bx, by, br))
    
    licht_pos = [0.0, 0.0, 5.0]
    width, height = 60, 18
    frame = 0
    
    print("3D-Lichtspiel – Herbstpark. Tasten: q=quit, n=next frame, p=Parameter ändern")
    
    while True:
        # Animate light position
        licht_pos[0] = math.sin(frame * 0.07) * 3.0
        licht_pos[1] = math.cos(frame * 0.05) * 2.5
        licht_pos[2] = 4.0 + math.sin(frame * 0.03) * 1.0
        
        img = render(params, bäume, licht_pos, width, height, frame)
        # Blur
        gewichte = gauß_gewichte(params.blur_radius)
        img = box_blur_1d(img, gewichte, True)
        img = box_blur_1d(img, gewichte, False)
        
        # Output
        for row in img:
            line = ''.join(intensitaet_zu_ascii(v, params.gamma) for v in row)
            print(line)
        print(f"Frame {frame} - 'q' quit, 'n' next, 'p' Parameter ändern (z.B. blur_radius=2)")
        
        # Non-blocking input
        try:
            rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
            if rlist:
                cmd = sys.stdin.readline().strip()
                if not cmd:
                    break
                cmd = _norm(cmd)
                if cmd == 'q':
                    break
                elif cmd == 'n':
                    frame += 1
                    continue
                elif cmd == 'p':
                    print("Parameter: penumbra_breite, umbra_dunkelheit, falloff_exponent, falloff_start, blur_radius, ambient, volumetric_gain, gamma, scattering_coeff, absorption_coeff, mist_density, mist_height_falloff, color_temp, jitter_strength, phase_g, noise_seed, march_steps, jitter_enabled, specular_intensity, specular_power, specular_noise_scale")
                    print("Format: name=wert")
                    continue
                elif '=' in cmd:
                    name, val = cmd.split('=', 1)
                    name = name.strip()
                    val = val.strip()
                    try:
                        if hasattr(params, name):
                            current = getattr(params, name)
                            if isinstance(current, bool):
                                setattr(params, name, val.lower() in ('true', '1', 'yes', 'on'))
                            elif isinstance(current, int):
                                setattr(params, name, int(float(val)))
                            else:
                                setattr(params, name, float(val))
                            print(f"{name} = {getattr(params, name)}")
                        else:
                            print(f"Unbekannter Parameter: {name}")
                    except ValueError:
                        print(f"Ungültiger Wert für {name}: {val}")
                    continue
                else:
                    print(f"Unbekannter Befehl: {cmd}")
            frame += 1
        except (EOFError, KeyboardInterrupt):
            break
    print("Tschüss!")

if __name__ == "__main__":
    main()