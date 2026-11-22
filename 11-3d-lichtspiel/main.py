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
            # Pixel to world direction
            px = (ix + 0.5) / width * world_w - world_w * 0.5
            py = (iy + 0.5) / height * world_h - world_h * 0.5
            # Ray from camera through pixel
            rx, ry, rz = px - cam_x, py - cam_y, -cam_z
            rlen = math.hypot(rx, ry, rz)
            rx, ry, rz = rx / rlen, ry / rlen, rz / rlen
            
            acc = 0.0
            transmittance = 1.0
            
            for step in range(params.march_steps):
                t = (step + 0.5) * step_size
                sx, sy, sz = cam_x + rx * t, cam_y + ry * t, cam_z + rz * t
                
                # Distance to light
                ldx, ldy, ldz = lx - sx, ly - sy, lz - sz
                ldist = math.hypot(ldx, ldy, ldz)
                if ldist < 0.01:
                    continue
                ldx, ldy, ldz = ldx / ldist, ldy / ldist, ldz / ldist
                
                # Shadow factor at this sample point (projected onto ground)
                shadow = schattenfaktor_für_punkt(sx, sy, lx, ly, ldist, bäume, params)
                
                # Phase function (Henyey-Greenstein)
                cos_theta = rx * ldx + ry * ldy + rz * ldz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                
                # Falloff
                falloff = 1.0 / max(1e-3, (ldist * params.falloff_start) ** params.falloff_exponent)
                
                # Mist density with height falloff
                mist = params.mist_density * math.exp(-sy * params.mist_height_falloff)
                
                # Jitter for volumetric noise
                jitter = 0.0
                if params.jitter_enabled:
                    jitter = noise_3d(sx * params.specular_noise_scale,
                                      sy * params.specular_noise_scale,
                                      sz * params.specular_noise_scale,
                                      params.noise_seed + frame) * params.jitter_strength
                
                # Absorption
                absorption = math.exp(-params.absorption_coeff * t)
                
                # Volumetric contribution
                contrib = (params.scattering_coeff * phase * falloff * shadow * mist
                           * (1.0 + jitter) * absorption * transmittance)
                acc += contrib * params.volumetric_gain
                transmittance *= (1.0 - mist * params.absorption_coeff * step_size)
                if transmittance < 0.01:
                    break
            
            # Ground intersection (simple plane at y=0)
            if ry < -1e-3:
                t_ground = -cam_y / ry
                if 0 < t_ground < max_dist:
                    gx, gz = cam_x + rx * t_ground, cam_z + rz * t_ground
                    # Check if in shadow on ground
                    ground_shadow = schattenfaktor_für_punkt(gx, 0.0, lx, ly,
                                                            math.hypot(lx - gx, ly - 0.0),
                                                            bäume, params)
                    # Specular highlight on wet ground
                    hx, hy, hz = (rx + ldx) * 0.5, (ry + ldy) * 0.5, (rz + ldz) * 0.5
                    hlen = math.hypot(hx, hy, hz)
                    if hlen > 1e-3:
                        hx, hy, hz = hx / hlen, hy / hlen, hz / hlen
                        spec = max(0.0, hz) ** params.specular_power
                        spec *= params.specular_intensity * ground_shadow
                        acc += spec
            
            img[iy][ix] = acc + params.ambient
    
    # Blur for volumetric glow
    weights = gauß_gewichte(params.blur_radius)
    img = box_blur_1d(img, weights, True)
    img = box_blur_1d(img, weights, False)
    
    # Convert to ASCII
    ascii_frame = []
    for row in img:
        line = ''.join(intensitaet_zu_ascii(v, params.gamma) for v in row)
        ascii_frame.append(line)
    return ascii_frame

def main():
    params = ShaderParams()
    # Bäume: (x, y, radius)
    bäume = [
        (-3.0, -2.0, 0.8),
        (2.5, 1.5, 0.6),
        (-1.0, 3.0, 0.7),
        (4.0, -3.0, 0.5),
        (-4.5, 0.5, 0.9),
    ]
    frame = 0
    max_frames = 30
    light_angle = 0.0
    
    print("3D-Lichtspiel – volumetric light & shadows. Tasten: q=quit, n=next, p=params")
    
    while frame < max_frames:
        # Animate light in a circle
        light_angle += 0.08
        lx = math.sin(light_angle) * 5.0
        ly = math.cos(light_angle) * 5.0
        lz = 4.0 + 0.5 * math.sin(light_angle * 0.7)
        
        ascii_art = render(params, bäume, (lx, ly, lz), frame=frame)
        
        # Clear screen (ANSI)
        sys.stdout.write('\x1b[2J\x1b[H')
        for line in ascii_art:
            sys.stdout.write(line + '\n')
        sys.stdout.write(f"Frame {frame} - 'q' quit, 'n' next, 'p' Parameter ändern\n")
        sys.stdout.flush()
        
        # Non-blocking input
        ready, _, _ = select.select([sys.stdin], [], [], 0.1)
        if ready:
            key = sys.stdin.readline().strip().lower()
            if key == 'q':
                break
            elif key == 'n':
                frame += 1
                continue
            elif key == 'p':
                print("\nAktuelle Parameter:")
                for k, v in params.__dict__.items():
                    print(f"  {k}: {v}")
                print("Welchen Parameter ändern? (Name oder Enter zum Überspringen)")
                name = sys.stdin.readline().strip()
                if name in params.__dict__:
                    print(f"Neuer Wert für {name} (aktuell {getattr(params, name)}):")
                    val_str = sys.stdin.readline().strip()
                    try:
                        val = float(val_str)
                        setattr(params, name, val)
                        print(f"{name} = {val}")
                    except ValueError:
                        print("Ungültige Zahl.")
                time.sleep(0.5)
                continue
        frame += 1
        time.sleep(0.05)
    
    print("\nBis zum nächsten Traum.")

if __name__ == "__main__":
    try:
        main()
    except EOFError:
        print("\nEingabe beendet. Gute Nacht.")
    except KeyboardInterrupt:
        print("\nUnterbrochen. Schlaf gut.")