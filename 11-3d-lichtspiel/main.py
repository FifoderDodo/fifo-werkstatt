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
                dist_achse = math.hypot(bx - cx, by - cy)
                ratio = proj / dist_light
                penumbra = br * ratio + params.light_radius * (1.0 - ratio) * 0.4
                if dist_achse < penumbra:
                    kern = max(0.0, 1.0 - dist_achse / max(0.001, penumbra))
                    f = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * (1.0 - kern * kern)
                    if f < min_f:
                        min_f = f
    return min_f

def raymarch_pixel(px, py, w, h, light_pos, baeume, params, cam_pos, view_dir, right_vec, up_vec):
    """Optimiertes Raymarching mit adaptiver Schrittweite für bessere Tiefenschärfe."""
    # Ray direction durch Pixel
    fx = (px + 0.5) / w * 2.0 - 1.0
    fy = (py + 0.5) / h * 2.0 - 1.0
    aspect = w / h
    ray_x = view_dir[0] + right_vec[0] * fx * aspect + up_vec[0] * fy
    ray_y = view_dir[1] + right_vec[1] * fx * aspect + up_vec[1] * fy
    ray_z = view_dir[2] + right_vec[2] * fx * aspect + up_vec[2] * fy
    ray_len = math.sqrt(ray_x*ray_x + ray_y*ray_y + ray_z*ray_z)
    ray_x, ray_y, ray_z = ray_x/ray_len, ray_y/ray_len, ray_z/ray_len
    
    # Jitter für Temporal AA
    jitter = 0.0
    if params.jitter_enabled:
        jitter = (random.random() - 0.5) * params.jitter_strength
    
    # Raymarching Parameter
    max_dist = 30.0
    base_step = max_dist / params.march_steps
    
    # Adaptive Step Size: Größere Schritte in niedriger Dichte, kleinere in hoher
    transmittance = 1.0
    in_scatter = 0.0
    depth_accum = 0.0
    
    step_count = 0
    dist = 0.0
    
    while dist < max_dist and step_count < params.march_steps * 2 and transmittance > params.early_exit_threshold:
        # Aktuelle Position
        sx = cam_pos[0] + ray_x * dist
        sy = cam_pos[1] + ray_y * dist
        sz = cam_pos[2] + ray_z * dist
        
        # Dichte an Position
        density = mist_dichte((sx, sy, sz), params)
        
        # Schattenfaktor
        shadow = schattenfaktor_3d((sx, sy, sz), light_pos, baeume, params)
        
        # Phase function (Henyey-Greenstein)
        cos_theta = -(ray_x * (light_pos[0]-sx) + ray_y * (light_pos[1]-sy) + ray_z * (light_pos[2]-sz)) / \
                    math.sqrt((light_pos[0]-sx)**2 + (light_pos[1]-sy)**2 + (light_pos[2]-sz)**2 + 1e-5)
        phase = henyey_greenstein(cos_theta, params.phase_g)
        
        # Scattering Beitrag
        scatter = density * params.scattering_coeff * shadow * phase
        in_scatter += transmittance * scatter * base_step
        
        # Absorption
        transmittance *= math.exp(-density * params.absorption_coeff * base_step)
        
        # Adaptive Schrittweite berechnen
        if params.adaptive_steps:
            # Hohe Dichte -> kleinere Schritte, niedrige Dichte -> größere Schritte
            density_factor = 1.0 / (1.0 + density * 5.0)
            adaptive_factor = params.min_step_factor + (params.max_step_factor - params.min_step_factor) * density_factor
            current_step = base_step * adaptive_factor
        else:
            current_step = base_step
        
        # Early exit bei sehr niedriger Transmittanz
        if transmittance < params.early_exit_threshold:
            break
            
        dist += current_step
        step_count += 1
        depth_accum += density * current_step
    
    # Tiefenbasiertes Shading (Depth of Field Approximation)
    depth_factor = 1.0 - math.exp(-depth_accum * params.depth_shading_wrap)
    
    # Volumetric Gain anwenden
    in_scatter *= params.volumetric_gain
    
    # Color Temperature
    cr, cg, cb = kelvin_to_rgb_factor(params.color_temp)
    in_scatter_r = in_scatter * cr
    in_scatter_g = in_scatter * cg
    in_scatter_b = in_scatter * cb
    
    # Ambient + Specular Highlights auf Baum-Oberflächen (vereinfacht)
    specular = 0.0
    for bx, by, br, bh in baeume:
        # Grobe Näherung: wenn Ray nah an Baumstamm vorbeigeht
        dx = bx - cam_pos[0]
        dy = by - cam_pos[1]
        proj = dx * ray_x + dy * ray_y
        if 0 < proj < dist:
            closest_x = cam_pos[0] + ray_x * proj
            closest_y = cam_pos[1] + ray_y * proj
            d_axis = math.hypot(bx - closest_x, by - closest_y)
            if d_axis < br * 1.2:
                # Specular Reflexion
                view_dot_light = ray_x * (light_pos[0]-bx) + ray_y * (light_pos[1]-by) + ray_z * (light_pos[2]-bh/2)
                view_dot_light /= math.sqrt((light_pos[0]-bx)**2 + (light_pos[1]-by)**2 + (light_pos[2]-bh/2)**2 + 1e-5)
                if view_dot_light > 0.9:
                    specular += params.specular_intensity * (view_dot_light ** params.specular_power) * (1.0 - d_axis/(br*1.2))
    
    specular = min(1.0, specular)
    
    return (in_scatter_r + specular * cr,
            in_scatter_g + specular * cg,
            in_scatter_b + specular * cb,
            depth_factor)

def bloom_pass(frame_r, frame_g, frame_b, params):
    """Bloom: Threshold -> Gaussian Blur -> Additive Blend."""
    h, w = len(frame_r), len(frame_r[0])
    # 1. Threshold: nur helle Pixel extrahieren
    bloom_src_r = [[0.0]*w for _ in range(h)]
    bloom_src_g = [[0.0]*w for _ in range(h)]
    bloom_src_b = [[0.0]*w for _ in range(h)]
    
    for y in range(h):
        for x in range(w):
            lum = 0.2126*frame_r[y][x] + 0.7152*frame_g[y][x] + 0.0722*frame_b[y][x]
            if lum > params.bloom_threshold:
                excess = lum - params.bloom_threshold
                factor = excess / max(1e-5, lum)
                bloom_src_r[y][x] = frame_r[y][x] * factor
                bloom_src_g[y][x] = frame_g[y][x] * factor
                bloom_src_b[y][x] = frame_b[y][x] * factor
    
    # 2. Gaussian Blur (separable)
    gewichte = gauß_gewichte(params.bloom_radius)
    blur_r = box_blur_1d(bloom_src_r, gewichte, True)
    blur_r = box_blur_1d(blur_r, gewichte, False)
    blur_g = box_blur_1d(bloom_src_g, gewichte, True)
    blur_g = box_blur_1d(blur_g, gewichte, False)
    blur_b = box_blur_1d(bloom_src_b, gewichte, True)
    blur_b = box_blur_1d(blur_b, gewichte, False)
    
    # 3. Additive Blending
    out_r = [[0.0]*w for _ in range(h)]
    out_g = [[0.0]*w for _ in range(h)]
    out_b = [[0.0]*w for _ in range(h)]
    
    for y in range(h):
        for x in range(w):
            out_r[y][x] = min(1.0, frame_r[y][x] + blur_r[y][x] * params.bloom_intensity)
            out_g[y][x] = min(1.0, frame_g[y][x] + blur_g[y][x] * params.bloom_intensity)
            out_b[y][x] = min(1.0, frame_b[y][x] + blur_b[y][x] * params.bloom_intensity)
    
    return out_r, out_g, out_b

def render_frame(params, frame_idx=0):
    w, h = 80, 40
    aspect = w / h
    
    # Kamera Setup
    cam_pos = (0.0, 0.0, 1.8)
    look_at = (0.0, 8.0, 1.2)
    view_dir = (look_at[0]-cam_pos[0], look_at[1]-cam_pos[1], look_at[2]-cam_pos[2])
    vlen = math.sqrt(view_dir[0]**2 + view_dir[1]**2 + view_dir[2]**2)
    view_dir = (view_dir[0]/vlen, view_dir[1]/vlen, view_dir[2]/vlen)
    
    # Right & Up Vektoren
    right_vec = (-view_dir[1], view_dir[0], 0.0)
    rlen = math.sqrt(right_vec[0]**2 + right_vec[1]**2)
    right_vec = (right_vec[0]/rlen, right_vec[1]/rlen, 0.0)
    up_vec = (0.0, 0.0, 1.0)  # Einfach nach oben
    
    # Lichtposition (bewegt sich langsam)
    light_angle = frame_idx * 0.02
    light_pos = (math.sin(light_angle) * 6.0, 10.0 + math.cos(light_angle) * 2.0, 5.0)
    
    # Bäume: (x, y, radius, height)
    baeume = [
        (-4.0, 3.0, 0.6, 4.0),
        (3.0, 4.5, 0.5, 3.5),
        (-7.0, 8.0, 0.8, 5.0),
        (6.0, 9.0, 0.7, 4.5),
        (-2.0, 12.0, 0.5, 3.0),
        (5.0, 14.0, 0.6, 4.0),
        (-5.0, 16.0, 0.7, 5.0),
        (2.0, 18.0, 0.5, 3.5),
    ]
    
    # Framebuffer
    frame_r = [[0.0]*w for _ in range(h)]
    frame_g = [[0.0]*w for _ in range(h)]
    frame_b = [[0.0]*w for _ in range(h)]
    depth_buf = [[0.0]*w for _ in range(h)]
    
    # Rendering
    for y in range(h):
        for x in range(w):
            r, g, b, depth = raymarch_pixel(x, y, w, h, light_pos, baeume, params,
                                             cam_pos, view_dir, right_vec, up_vec)
            frame_r[y][x] = r
            frame_g[y][x] = g
            frame_b[y][x] = b
            depth_buf[y][x] = depth
    
    # Bloom Pass
    frame_r, frame_g, frame_b = bloom_pass(frame_r, frame_g, frame_b, params)
    
    # Gamma Correction & Vibrancy
    for y in range(h):
        for x in range(w):
            # Vibrancy: Sättigung erhöhen
            lum = 0.2126*frame_r[y][x] + 0.7152*frame_g[y][x] + 0.0722*frame_b[y][x]
            frame_r[y][x] = lum + (frame_r[y][x] - lum) * params.vibrancy
            frame_g[y][x] = lum + (frame_g[y][x] - lum) * params.vibrancy
            frame_b[y][x] = lum + (frame_b[y][x] - lum) * params.vibrancy
            
            # Gamma
            frame_r[y][x] = frame_r[y][x] ** params.gamma
            frame_g[y][x] = frame_g[y][x] ** params.gamma
            frame_b[y][x] = frame_b[y][x] ** params.gamma
    
    # ASCII Output
    ascii_lines = []
    for y in range(h):
        line = ""
        for x in range(w):
            lum = 0.2126*frame_r[y][x] + 0.7152*frame_g[y][x] + 0.0722*frame_b[y][x]
            line += intensitaet_zu_ascii(lum, params.gamma)
        ascii_lines.append(line)
    
    return ascii_lines

def print_menu(params):
    print("\n=== 3D-Lichtspiel: Herbstlicher Park ===")
    print("Parameter (aktuelle Werte):")
    print(f"  1) March Steps: {params.march_steps}")
    print(f"  2) Volumetric Gain: {params.volumetric_gain:.2f}")
    print(f"  3) Mist Density: {params.mist_density:.2f}")
    print(f"  4) Scattering: {params.scattering_coeff:.2f}")
    print(f"  5) Absorption: {params.absorption_coeff:.2f}")
    print(f"  6) Phase g: {params.phase_g:.2f}")
    print(f"  7) Color Temp (K): {params.color_temp:.0f}")
    print(f"  8) Gamma: {params.gamma:.2f}")
    print(f"  9) Bloom Threshold: {params.bloom_threshold:.2f}")
    print(f" 10) Bloom Intensity: {params.bloom_intensity:.2f}")
    print(f" 11) Bloom Radius: {params.bloom_radius}")
    print(f" 12) Adaptive Steps: {'An' if params.adaptive_steps else 'Aus'}")
    print(f" 13) Min Step Factor: {params.min_step_factor:.2f}")
    print(f" 14) Max Step Factor: {params.max_step_factor:.2f}")
    print(f" 15) Early Exit Threshold: {params.early_exit_threshold:.4f}")
    print(f" 16) Depth Shading Wrap: {params.depth_shading_wrap:.2f}")
    print(f" 17) Vibrancy: {params.vibrancy:.2f}")
    print(f" 18) Jitter Strength: {params.jitter_strength:.3f}")
    print(f" 19) Specular Power: {params.specular_power:.1f}")
    print("  q) Beenden")
    print("  Enter) Weiter rendern mit aktuellen Einstellungen")

def parse_input(eingabe, params):
    if not eingabe:
        return True
    teile = eingabe.split()
    if teile[0] == 'q':
        return False
    try:
        idx = int(teile[0])
        if len(teile) < 2:
            print("Bitte Wert angeben.")
            return True
        val = float(teile[1])
        if idx == 1: params.march_steps = int(max(4, min(64, val)))
        elif idx == 2: params.volumetric_gain = max(0.1, min(10.0, val))
        elif idx == 3: params.mist_density = max(0.0, min(2.0, val))
        elif idx == 4: params.scattering_coeff = max(0.0, min(2.0, val))
        elif idx == 5: params.absorption_coeff = max(0.0, min(2.0, val))
        elif idx == 6: params.phase_g = max(-0.99, min(0.99, val))
        elif idx == 7: params.color_temp = max(1000.0, min(12000.0, val))
        elif idx == 8: params.gamma = max(0.1, min(3.0, val))
        elif idx == 9: params.bloom_threshold = max(0.0, min(1.0, val))
        elif idx == 10: params.bloom_intensity = max(0.0, min(2.0, val))
        elif idx == 11: params.bloom_radius = int(max(0, min(8, val)))
        elif idx == 12: params.adaptive_steps = bool(val)
        elif idx == 13: params.min_step_factor = max(0.05, min(1.0, val))
        elif idx == 14: params.max_step_factor = max(1.0, min(5.0, val))
        elif idx == 15: params.early_exit_threshold = max(0.0, min(0.1, val))
        elif idx == 16: params.depth_shading_wrap = max(0.0, min(2.0, val))
        elif idx == 17: params.vibrancy = max(0.5, min(3.0, val))
        elif idx == 18: params.jitter_strength = max(0.0, min(0.5, val))
        elif idx == 19: params.specular_power = max(1.0, min(128.0, val))
        else: print("Unbekannter Parameter.")
    except ValueError:
        print("Ungültige Eingabe.")
    return True

def main():
    random.seed(1337)
    params = ShaderParams()
    frame = 0
    
    print("3D-Lichtspiel - Volumetric Light & Shadows im herbstlichen Park")
    print("Optimiertes Raymarching mit adaptiver Schrittweite für Tiefenschärfe")
    print("Drücke Enter für nächsten Frame, 'q' zum Beenden.")
    
    while True:
        try:
            lines = render_frame(params, frame)
            for line in lines:
                print(line)
            print(f"\nFrame {frame} | Steps: {params.march_steps} | Adaptive: {'On' if params.adaptive_steps else 'Off'} | Bloom: {params.bloom_intensity:.2f}")
            
            print_menu(params)
            eingabe = input("> ").strip()
            if not parse_input(eingabe, params):
                break
            frame += 1
        except EOFError:
            break
        except KeyboardInterrupt:
            break
    
    print("\nTschüss! Der Dodo watschelt davon.")

if __name__ == "__main__":
    main()