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
                    t = dist_achse / penumbra
                    falloff = t ** params.falloff_exponent
                    f = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * falloff
                    min_f = min(min_f, f)
    return min_f

def raymarch(origin, direction, light_pos, baeume, params):
    ox, oy, oz = origin
    dx, dy, dz = direction
    step_dist = 0.3
    max_dist = 30.0
    accumulated = 0.0
    transmittance = 1.0
    lx, ly, lz = light_pos
    light_dir = (lx - ox, ly - oy, lz - oz)
    light_dist = math.sqrt(light_dir[0]**2 + light_dir[1]**2 + light_dir[2]**2)
    if light_dist > 0:
        light_dir = (light_dir[0]/light_dist, light_dir[1]/light_dist, light_dir[2]/light_dist)
    
    for step in range(params.march_steps):
        t = step * step_dist
        px = ox + dx * t
        py = oy + dy * t
        pz = oz + dz * t
        
        if pz < -0.5 or t > max_dist:
            break
            
        density = mist_dichte((px, py, pz), params)
        if density <= 0.001:
            continue
            
        # Schatten berechnen
        shadow = schattenfaktor_3d((px, py, pz), light_pos, baeume, params)
        
        # Phase function
        cos_theta = dx * light_dir[0] + dy * light_dir[1] + dz * light_dir[2]
        phase = henyey_greenstein(cos_theta, params.phase_g)
        
        # Scattering
        scatter = density * params.scattering_coeff * phase * shadow
        
        # Absorption
        absorb = density * params.absorption_coeff
        transmittance *= math.exp(-absorb * step_dist)
        
        accumulated += scatter * transmittance * step_dist
        
        if transmittance < 0.01:
            break
    
    return accumulated

def render_frame(params, baeume, light_pos, cam_pos, cam_yaw, cam_pitch, width=80, height=40):
    # Kamera-Basisvektoren
    yaw = cam_yaw
    pitch = cam_pitch
    forward = (math.cos(pitch) * math.sin(yaw),
               math.cos(pitch) * math.cos(yaw),
               math.sin(pitch))
    right = (math.cos(yaw), -math.sin(yaw), 0.0)
    up = (0.0, 0.0, 1.0)
    
    fov = 1.0
    aspect = width / height
    
    # Framebuffer
    frame = [[0.0 for _ in range(width)] for __ in range(height)]
    depth_buf = [[float('inf') for _ in range(width)] for __ in range(height)]
    
    for y in range(height):
        for x in range(width):
            # NDC-Koordinaten
            ndc_x = (x + 0.5) / width * 2.0 - 1.0
            ndc_y = 1.0 - (y + 0.5) / height * 2.0
            
            # Ray-Direktion
            ray_x = forward[0] + right[0] * ndc_x * fov * aspect + up[0] * ndc_y * fov
            ray_y = forward[1] + right[1] * ndc_x * fov * aspect + up[1] * ndc_y * fov
            ray_z = forward[2] + right[2] * ndc_x * fov * aspect + up[2] * ndc_y * fov
            
            ray_len = math.sqrt(ray_x**2 + ray_y**2 + ray_z**2)
            ray_x, ray_y, ray_z = ray_x/ray_len, ray_y/ray_len, ray_z/ray_len
            
            # Volumetric Light
            vol_light = raymarch(cam_pos, (ray_x, ray_y, ray_z), light_pos, baeume, params)
            
            # Boden-Schatten (einfacher Hit-Test)
            ground_hit = 0.0
            if ray_z < -0.01:
                t_ground = -cam_pos[2] / ray_z
                if t_ground > 0:
                    gx = cam_pos[0] + ray_x * t_ground
                    gy = cam_pos[1] + ray_y * t_ground
                    shadow = schattenfaktor_3d((gx, gy, 0.0), light_pos, baeume, params)
                    ground_hit = shadow * 0.3
            
            # Kombinieren
            total = params.ambient + vol_light * params.volumetric_gain + ground_hit
            frame[y][x] = min(1.0, total * params.vibrancy)
            depth_buf[y][x] = t_ground if ray_z < -0.01 else 100.0
    
    # Blur für weichere Lichtkegel
    if params.blur_radius > 0:
        weights = gauß_gewichte(params.blur_radius)
        frame = box_blur_1d(frame, weights, True)
        frame = box_blur_1d(frame, weights, False)
    
    # ASCII-Konvertierung
    lines = []
    for y in range(height):
        line = ''.join(intensitaet_zu_ascii(frame[y][x], params.gamma) for x in range(width))
        lines.append(line)
    
    return '\n'.join(lines)

def parameter_menü(params):
    print("\n=== Shader-Parameter ===")
    attrs = [a for a in dir(params) if not a.startswith('_') and not callable(getattr(params, a))]
    for i, a in enumerate(attrs):
        print(f"  {i+1:2d}. {a} = {getattr(params, a)}")
    print("  0. Zurück")
    try:
        choice = input("Wähle Parameter (Nummer) oder Enter zum Überspringen: ").strip()
        if not choice:
            return
        idx = int(choice) - 1
        if 0 <= idx < len(attrs):
            attr = attrs[idx]
            val = input(f"Neuer Wert für {attr} (aktuell: {getattr(params, attr)}): ").strip()
            if val:
                setattr(params, attr, float(val))
                print(f"→ {attr} = {getattr(params, attr)}")
    except (ValueError, EOFError):
        pass

def main():
    print("╔══════════════════════════════════════════╗")
    print("║     3D-Lichtspiel – Herbstlicher Park    ║")
    print("║   Volumetric Light & Shadow Simulator    ║")
    print("╚══════════════════════════════════════════╝")
    
    params = ShaderParams()
    
    # Bäume: (x, y, radius, höhe)
    random.seed(12345)
    baeume = []
    for _ in range(12):
        bx = random.uniform(-10, 10)
        by = random.uniform(-10, 10)
        br = random.uniform(0.4, 0.9)
        bh = random.uniform(3.0, 6.0)
        baeume.append((bx, by, br, bh))
    
    # Lichtposition (über den Bäumen)
    light_pos = (0.0, 0.0, 8.0)
    
    # Kamera
    cam_pos = (0.0, -12.0, 1.8)
    cam_yaw = 0.0
    cam_pitch = -0.2
    
    width, height = 80, 35
    
    print(f"\nBäume: {len(baeume)} | Licht: {light_pos} | Kamera: {cam_pos}")
    print("Steuerung: WASD=Bewegen, QE=Drehen, RF=Hoch/Runter, P=Parameter, Enter=Neu rendern, X=Beenden")
    
    frame_count = 0
    last_render = ""
    
    while True:
        try:
            # Auto-Render beim Start
            if frame_count == 0:
                print("\n--- Rendering... ---")
                start = time.time()
                last_render = render_frame(params, baeume, light_pos, cam_pos, cam_yaw, cam_pitch, width, height)
                elapsed = time.time() - start
                print(last_render)
                print(f"\n[Frame {frame_count}] Renderzeit: {elapsed:.2f}s | Yaw: {cam_yaw:.2f} Pitch: {cam_pitch:.2f}")
                frame_count += 1
            
            cmd = input("\n> ").strip().lower()
            if not cmd:
                # Neu rendern
                print("\n--- Rendering... ---")
                start = time.time()
                last_render = render_frame(params, baeume, light_pos, cam_pos, cam_yaw, cam_pitch, width, height)
                elapsed = time.time() - start
                print(last_render)
                print(f"\n[Frame {frame_count}] Renderzeit: {elapsed:.2f}s")
                frame_count += 1
                continue
            
            if cmd == 'x' or cmd == 'q':
                print("Tschüss! Der Dodo watschelt davon. 🦤")
                break
            elif cmd == 'p':
                parameter_menü(params)
                continue
            elif cmd == 'w':
                cam_pos = (cam_pos[0] + math.sin(cam_yaw) * 0.5,
                           cam_pos[1] + math.cos(cam_yaw) * 0.5,
                           cam_pos[2])
            elif cmd == 's':
                cam_pos = (cam_pos[0] - math.sin(cam_yaw) * 0.5,
                           cam_pos[1] - math.cos(cam_yaw) * 0.5,
                           cam_pos[2])
            elif cmd == 'a':
                cam_pos = (cam_pos[0] + math.cos(cam_yaw) * 0.5,
                           cam_pos[1] - math.sin(cam_yaw) * 0.5,
                           cam_pos[2])
            elif cmd == 'd':
                cam_pos = (cam_pos[0] - math.cos(cam_yaw) * 0.5,
                           cam_pos[1] + math.sin(cam_yaw) * 0.5,
                           cam_pos[2])
            elif cmd == 'q':
                cam_yaw -= 0.15
            elif cmd == 'e':
                cam_yaw += 0.15
            elif cmd == 'r':
                cam_pitch = min(1.4, cam_pitch + 0.1)
            elif cmd == 'f':
                cam_pitch = max(-1.4, cam_pitch - 0.1)
            elif cmd == 'h':
                print("Hilfe: W/A/S/D=Vorwärts/Links/Rückwärts/Rechts, Q/E=Yaw, R/F=Pitch, P=Parameter, Enter=Render, X=Exit")
                continue
            else:
                print(f"Unbekannt: '{cmd}' (h für Hilfe)")
                continue
            
            # Nach Bewegung neu rendern
            print("\n--- Rendering... ---")
            start = time.time()
            last_render = render_frame(params, baeume, light_pos, cam_pos, cam_yaw, cam_pitch, width, height)
            elapsed = time.time() - start
            print(last_render)
            print(f"\n[Frame {frame_count}] Renderzeit: {elapsed:.2f}s | Pos: ({cam_pos[0]:.1f}, {cam_pos[1]:.1f}, {cam_pos[2]:.1f})")
            frame_count += 1
            
        except EOFError:
            print("\nEingabe beendet. Der Dodo nickt müde. 🦤")
            break
        except KeyboardInterrupt:
            print("\nAbbruch. Tschüss! 🦤")
            break
        except Exception as e:
            print(f"Fehler: {e}")
            continue

if __name__ == "__main__":
    main()