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
    """Ray‑March vom Kamerapunkt (0,0,10) auf die Ground‑Plane z=0.
    Gibt Liste von ASCII‑Zeilen zurück."""
    img = [[0.0 for _ in range(width)] for _ in range(height)]
    lx, ly, lz = licht_pos
    cam_x, cam_y, cam_z = 0.0, 0.0, 10.0
    world_w, world_h = 10.0, 10.0 * height / width
    max_dist = 15.0
    step_size = max_dist / max(1, params.march_steps)
    
    # Schattenkarte für Ground-Plane (einmal pro Frame)
    shadow_map = [[1.0 for _ in range(width)] for _ in range(height)]
    for iy in range(height):
        wy = (iy / (height - 1) - 0.5) * world_h
        for ix in range(width):
            wx = (ix / (width - 1) - 0.5) * world_w
            # Lichtrichtung zum Bodenpunkt
            s = schattenfaktor_für_punkt(wx, wy, lx, ly, 100.0, bäume, params)
            shadow_map[iy][ix] = s
    
    # Ray-Marching für jeden Pixel
    for iy in range(height):
        wy = (iy / (height - 1) - 0.5) * world_h
        for ix in range(width):
            wx = (ix / (width - 1) - 0.5) * world_w
            # Ray direction from camera to ground point
            dx, dy, dz = wx - cam_x, wy - cam_y, -cam_z
            ray_len = math.hypot(dx, dy, dz)
            if ray_len == 0:
                continue
            rdx, rdy, rdz = dx / ray_len, dy / ray_len, dz / ray_len
            
            # Light direction at ground intersection (for phase function)
            ldx, ldy, ldz = wx - lx, wy - ly, -lz
            ldist = math.hypot(ldx, ldy, ldz)
            if ldist > 0:
                ldx, ldy, ldz = ldx / ldist, ldy / ldist, ldz / ldist
            
            acc = 0.0
            transmittance = 1.0
            t = 0.0
            for step in range(params.march_steps):
                if t >= ray_len:
                    break
                # Jitter for dithering
                if params.jitter_enabled:
                    jitter = noise_3d(ix + t * 0.1, iy + t * 0.1, frame * 0.01, params.noise_seed) * params.jitter_strength
                    t += jitter * step_size
                
                px = cam_x + rdx * t
                py = cam_y + rdy * t
                pz = cam_z + rdz * t
                
                # Mist density with height falloff
                mist = params.mist_density * math.exp(-pz * params.mist_height_falloff)
                
                # Phase function (Henyey-Greenstein)
                cos_theta = rdx * ldx + rdy * ldy + rdz * ldz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                
                # Shadow at this point (approximate using ground shadow map)
                # Project to ground plane
                if pz > 0:
                    ground_x = cam_x + rdx * (cam_z / -rdz) if rdz != 0 else wx
                    ground_y = cam_y + rdy * (cam_z / -rdz) if rdz != 0 else wy
                    gx = int((ground_x / world_w + 0.5) * (width - 1))
                    gy = int((ground_y / world_h + 0.5) * (height - 1))
                    if 0 <= gx < width and 0 <= gy < height:
                        shadow = shadow_map[gy][gx]
                    else:
                        shadow = 1.0
                else:
                    shadow = 1.0
                
                # Scattering contribution
                scatter = params.scattering_coeff * mist * phase * shadow * params.volumetric_gain
                acc += transmittance * scatter * step_size
                transmittance *= math.exp(-params.absorption_coeff * mist * step_size)
                if transmittance < 1e-4:
                    break
                t += step_size
            
            # Ground contribution (specular reflection of light)
            ground_shadow = shadow_map[iy][ix]
            # Simple Lambertian ground with specular highlight
            nx, ny, nz = 0.0, 0.0, 1.0
            view_dx, view_dy, view_dz = -rdx, -rdy, -rdz
            # Diffuse
            diffuse = max(0.0, nx * ldx + ny * ldy + nz * ldz) * ground_shadow
            # Specular (Blinn-Phong)
            hx, hy, hz = (ldx + view_dx) * 0.5, (ldy + view_dy) * 0.5, (ldz + view_dz) * 0.5
            hlen = math.hypot(hx, hy, hz)
            specular = 0.0
            if hlen > 0:
                hx, hy, hz = hx / hlen, hy / hlen, hz / hlen
                spec_angle = max(0.0, nx * hx + ny * hy + nz * hz)
                specular = params.specular_intensity * (spec_angle ** params.specular_power) * ground_shadow
            ground_contrib = (diffuse + specular) * 0.5
            
            total = acc + ground_contrib + params.ambient
            
            # Color temperature factor (luminance)
            rfac, gfac, bfac = kelvin_to_rgb_factor(params.color_temp)
            luminance = 0.2126 * rfac + 0.7152 * gfac + 0.0722 * bfac
            total *= luminance
            
            img[iy][ix] = total
    
    # Box blur
    if params.blur_radius > 0:
        gewichte = gauß_gewichte(params.blur_radius)
        img = box_blur_1d(img, gewichte, horizontal=True)
        img = box_blur_1d(img, gewichte, horizontal=False)
    
    # Convert to ASCII
    ascii_lines = []
    for row in img:
        line = ''.join(intensitaet_zu_ascii(v, params.gamma) for v in row)
        ascii_lines.append(line)
    return ascii_lines

def main():
    params = ShaderParams()
    random.seed(42)
    # Beispiel-Bäume: (x, y, radius)
    bäume = [(random.uniform(-5, 5), random.uniform(-5, 5), random.uniform(0.3, 0.8)) for _ in range(15)]
    licht_pos = (0.0, 0.0, 5.0)
    frame = 0
    width, height = 80, 24
    
    print("3D-Lichtspiel – Drücke 'q' zum Beenden, Enter für nächsten Frame.")
    while True:
        try:
            lines = render(params, bäume, licht_pos, width, height, frame)
            # Clear screen (ANSI)
            print('\033[H\033[J', end='')
            for line in lines:
                print(line)
            print(f"Frame {frame}  Licht: ({licht_pos[0]:.1f}, {licht_pos[1]:.1f}, {licht_pos[2]:.1f})")
            print("Befehle: q=quit, p=params, +=blur, -=blur, n=neue Bäume, Enter=weiter")
            
            # Non-blocking input check for 0.1s
            rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
            if rlist:
                cmd = sys.stdin.readline().strip().lower()
                if cmd == 'q':
                    break
                elif cmd == 'p':
                    print(f"penumbra={params.penumbra_breite}, umbra={params.umbra_dunkelheit}, blur={params.blur_radius}, mist={params.mist_density}")
                    print(f"scattering={params.scattering_coeff}, absorption={params.absorption_coeff}, gain={params.volumetric_gain}")
                    print(f"gamma={params.gamma}, color_temp={params.color_temp}, jitter={params.jitter_strength}")
                    continue
                elif cmd == '+':
                    params.blur_radius = min(10, params.blur_radius + 1)
                elif cmd == '-':
                    params.blur_radius = max(0, params.blur_radius - 1)
                elif cmd == 'n':
                    bäume = [(random.uniform(-5, 5), random.uniform(-5, 5), random.uniform(0.3, 0.8)) for _ in range(15)]
                # else ignore
            
            # Animate light
            frame += 1
            angle = frame * 0.03
            licht_pos = (math.sin(angle) * 4.0, math.cos(angle) * 4.0, 5.0 + math.sin(angle * 0.5) * 1.0)
            
        except EOFError:
            print("\nEOF – Tschüss!")
            break
        except KeyboardInterrupt:
            print("\nAbbruch – Tschüss!")
            break
        except Exception as e:
            print(f"Fehler: {e}")
            break

if __name__ == '__main__':
    main()