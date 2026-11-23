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
                    t = dist_achse / penumbra
                    # Potenzfunktion für weichere Penumbra (smoothstep-artig)
                    shadow = t * t * (3.0 - 2.0 * t)
                    min_f = min(min_f, params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * shadow)
    return min_f

def raymarch(origin, direction, light_pos, baeume, params, dt=0.3, max_dist=30.0):
    """Integriert volumetrisches Licht entlang des Strahls."""
    ox, oy, oz = origin
    dx, dy, dz = direction
    t = 0.0
    acc_light = 0.0
    transmittance = 1.0
    light_color = kelvin_to_rgb_factor(params.color_temp)
    
    # Jitter Start für Temporal Stability / Dithering
    jitter_off = 0.0
    if params.jitter_enabled:
        jitter_off = (random.random() - 0.5) * params.jitter_strength * dt
    t += jitter_off

    for _ in range(params.march_steps):
        if t > max_dist:
            break
        px, py, pz = ox + dx * t, oy + dy * t, oz + dz * t
        
        # Mist Dichte
        density = mist_dichte((px, py, pz), params)
        if density > 1e-4:
            # Schattenfaktor
            shadow = schattenfaktor_3d((px, py, pz), light_pos, baeume, params)
            
            # Phase Function (Henyey-Greenstein)
            lx, ly, lz = light_pos
            vx, vy, vz = lx - px, ly - py, lz - pz
            dist_l = math.sqrt(vx*vx + vy*vy + vz*vz)
            if dist_l > 0.01:
                ldx, ldy, ldz = vx/dist_l, vy/dist_l, vz/dist_l
                cos_theta = dx*ldx + dy*ldy + dz*ldz
                phase = henyey_greenstein(cos_theta, params.phase_g)
            else:
                phase = 1.0
            
            # Scattering
            scatter = density * params.scattering_coeff * phase * shadow
            # Absorption
            absorb = density * params.absorption_coeff
            
            # Volumetric Light Accumulation (Front-to-Back)
            # Light arrives at point, scatters towards eye.
            # Intensity falls off with distance to light.
            falloff = 1.0 / max(0.01, dist_l * dist_l)
            radiance = scatter * falloff * params.volumetric_gain
            
            acc_light += radiance * transmittance * dt
            transmittance *= math.exp(-absorb * dt)
            
            if transmittance < 0.01:
                break
        t += dt
    
    return acc_light, transmittance, light_color

def render_frame(params, baeume, light_pos, cam_pos, cam_yaw, cam_pitch, width, height):
    """Rendert einen Frame in einen Float-Buffer (HDR)."""
    buffer = [[0.0 for _ in range(width)] for __ in range(height)]
    
    # Kamera Basisvektoren
    cy = math.cos(cam_yaw)
    sy = math.sin(cam_yaw)
    cp = math.cos(cam_pitch)
    sp = math.sin(cam_pitch)
    
    # Forward
    fx, fy, fz = cy * cp, sy * cp, sp
    # Right
    rx, ry, rz = -sy, cy, 0.0
    # Up
    ux, uy, uz = -cy * sp, -sy * sp, cp
    
    fov = 1.0 # ~90 grad äquivalent
    aspect = width / height
    
    for y in range(height):
        for x in range(width):
            # NDC [-1, 1]
            nx = (x + 0.5) / width * 2.0 - 1.0
            ny = 1.0 - (y + 0.5) / height * 2.0
            
            # Ray Direction
            dx = fx + rx * nx * fov * aspect + ux * ny * fov
            dy = fy + ry * nx * fov * aspect + uy * ny * fov
            dz = fz + rz * nx * fov * aspect + uz * ny * fov
            len_d = math.sqrt(dx*dx + dy*dy + dz*dz)
            dx, dy, dz = dx/len_d, dy/len_d, dz/len_d
            
            # Raymarch
            light_val, trans, lc = raymarch(cam_pos, (dx, dy, dz), light_pos, baeume, params)
            
            # Sky / Background (einfaches Gradient)
            sky_intensity = max(0.0, dz * 0.5 + 0.5) * 0.1 * trans # Dunst am Horizont
            
            # Specular Highlight auf "Boden" / Nebel (Fake)
            # Einfacher Glanz in Blickrichtung zum Licht
            lx, ly, lz = light_pos
            vx, vy, vz = lx - cam_pos[0], ly - cam_pos[1], lz - cam_pos[2]
            dist_l = math.sqrt(vx*vx + vy*vy + vz*vz)
            if dist_l > 0:
                ldx, ldy, ldz = vx/dist_l, vy/dist_l, vz/dist_l
                cos_spec = dx*ldx + dy*ldy + dz*ldz
                if cos_spec > 0.95:
                    sky_intensity += (cos_spec - 0.95) * 20.0 * params.specular_intensity
            
            total = (light_val + sky_intensity + params.ambient) * trans
            buffer[y][x] = total
            
    return buffer

def bloom_pass(hdr_buffer, params):
    """Extrahiert helle Bereiche, blurt sie und addiert sie additiv zurück."""
    h, w = len(hdr_buffer), len(hdr_buffer[0])
    # 1. Threshold & Extract
    bloom_src = [[0.0 for _ in range(w)] for __ in range(h)]
    for y in range(h):
        for x in range(w):
            val = hdr_buffer[y][x]
            if val > params.bloom_threshold:
                bloom_src[y][x] = (val - params.bloom_threshold) * params.bloom_intensity
    
    # 2. Blur (Separable Gaussian)
    weights = gauß_gewichte(params.bloom_radius)
    blur_h = box_blur_1d(bloom_src, weights, horizontal=True)
    blur_v = box_blur_1d(blur_h, weights, horizontal=False)
    
    # 3. Add back (Additive Blending)
    result = [[0.0 for _ in range(w)] for __ in range(h)]
    for y in range(h):
        for x in range(w):
            result[y][x] = hdr_buffer[y][x] + blur_v[y][x]
    return result

def tonemap_and_ascii(hdr_buffer, params):
    """Wendet Gamma/Vibrancy an und wandelt in ASCII um."""
    h, w = len(hdr_buffer), len(hdr_buffer[0])
    lines = []
    for y in range(h):
        line_chars = []
        for x in range(w):
            val = hdr_buffer[y][x]
            # Reinhard-ähnlicher Tonemapping für HDR -> LDR
            mapped = val / (val + 0.5) 
            # Vibrancy / Colorfulness Simulation (hier nur Helligkeit)
            mapped = mapped ** (1.0 / params.vibrancy) 
            # Gamma
            mapped = mapped ** params.gamma
            line_chars.append(intensitaet_zu_ascii(mapped, 1.0)) # Gamma schon oben
        lines.append("".join(line_chars))
    return lines

def generate_scene():
    """Erzeugt Bäume und Lichtposition."""
    random.seed(12345)
    baeume = []
    for _ in range(25):
        bx = random.uniform(-15, 15)
        by = random.uniform(-15, 15)
        br = random.uniform(0.4, 0.9)
        bh = random.uniform(3.0, 6.0)
        baeume.append((bx, by, br, bh))
    light_pos = (0.0, 0.0, 8.0) # Hoch oben
    cam_pos = (0.0, -10.0, 1.6) # Etwas zurück, Augenhöhe
    return baeume, light_pos, cam_pos

def main():
    print("🌲 3D-Lichtspiel: Herbstlicher Park (mit sanftem Leuchten) 🌲")
    print("Steuerung: WASD=Bewegen, QE=Drehen, RF=Hoch/Runter, P=Parameter, Enter=Weiter, X=Ende")
    
    params = ShaderParams()
    baeume, light_pos, cam_pos = generate_scene()
    cam_yaw = 0.0
    cam_pitch = -0.15 # Leicht nach unten
    
    width, height = 80, 40
    
    frame = 0
    try:
        while True:
            frame += 1
            # Leichtes Licht-Bewegen für Atmosphäre
            lt = time.time() * 0.1
            cur_light = (math.sin(lt) * 3.0, math.cos(lt * 0.7) * 2.0, 8.0 + math.sin(lt * 0.3) * 0.5)
            
            # Render Pipeline
            hdr = render_frame(params, baeume, cur_light, cam_pos, cam_yaw, cam_pitch, width, height)
            bloomed = bloom_pass(hdr, params)
            ascii_lines = tonemap_and_ascii(bloomed, params)
            
            # Output
            sys.stdout.write("\x1b[H\x1b[2J") # Clear Screen ANSI
            sys.stdout.write(f"Frame: {frame} | Pos: {cam_pos[0]:.1f},{cam_pos[1]:.1f},{cam_pos[2]:.1f} | Yaw: {cam_yaw:.2f}\n")
            sys.stdout.write("\n".join(ascii_lines))
            sys.stdout.write("\n> ")
            sys.stdout.flush()
            
            # Input
            try:
                cmd = input().strip().lower()
            except EOFError:
                print("\nTschüss! 🍂")
                break
            
            if not cmd:
                continue
            if cmd == 'x':
                print("Bis bald im Nebel!")
                break
            
            # Bewegung
            move_speed = 0.5
            rot_speed = 0.08
            fx, fy = math.cos(cam_yaw), math.sin(cam_yaw)
            rx, ry = -fy, fx
            
            if 'w' in cmd: cam_pos = (cam_pos[0] + fx*move_speed, cam_pos[1] + fy*move_speed, cam_pos[2])
            if 's' in cmd: cam_pos = (cam_pos[0] - fx*move_speed, cam_pos[1] - fy*move_speed, cam_pos[2])
            if 'a' in cmd: cam_pos = (cam_pos[0] + rx*move_speed, cam_pos[1] + ry*move_speed, cam_pos[2])
            if 'd' in cmd: cam_pos = (cam_pos[0] - rx*move_speed, cam_pos[1] - ry*move_speed, cam_pos[2])
            if 'r' in cmd: cam_pos = (cam_pos[0], cam_pos[1], cam_pos[2] + move_speed)
            if 'f' in cmd: cam_pos = (cam_pos[0], cam_pos[1], max(0.5, cam_pos[2] - move_speed))
            if 'q' in cmd: cam_yaw -= rot_speed
            if 'e' in cmd: cam_yaw += rot_speed
            
            # Parameter Tweaks
            if cmd == 'p':
                print(f"Bloom Thresh: {params.bloom_threshold:.2f} (i/k), Intensity: {params.bloom_intensity:.2f} (o/l), Radius: {params.bloom_radius} (,/.)")
                print(f"Mist Density: {params.mist_density:.2f}, Vol Gain: {params.volumetric_gain:.2f}")
            elif cmd == 'i': params.bloom_threshold = min(2.0, params.bloom_threshold + 0.05)
            elif cmd == 'k': params.bloom_threshold = max(0.0, params.bloom_threshold - 0.05)
            elif cmd == 'o': params.bloom_intensity = min(2.0, params.bloom_intensity + 0.05)
            elif cmd == 'l': params.bloom_intensity = max(0.0, params.bloom_intensity - 0.05)
            elif cmd == ',': params.bloom_radius = max(1, params.bloom_radius - 1)
            elif cmd == '.': params.bloom_radius = min(10, params.bloom_radius + 1)
            
    except KeyboardInterrupt:
        print("\nAbbruch.")

if __name__ == "__main__":
    main()