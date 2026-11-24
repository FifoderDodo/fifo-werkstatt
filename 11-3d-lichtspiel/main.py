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
        self.bloom_threshold = 0.6
        self.bloom_intensity = 0.45
        self.bloom_radius = 2
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
    rampe = " .:'-=+*#%@"
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
    """Berechnet den Schattenfaktor (0..1) für einen Punkt.
    Penumbra wird mit einer linearen Interpolation über die Breite
    des Lichtkegels modelliert."""
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
            cz = pz + uz * proj
            if 0.0 <= cz <= bh:
                # distance from ray to tree center in xy plane
                dist_xy = math.sqrt((dx - proj*ux)**2 + (dy - proj*uy)**2)
                if dist_xy < br:
                    # inside umbra
                    min_f = min(min_f, params.umbra_dunkelheit)
                else:
                    # penumbra region
                    penumbra_width = params.penumbra_breite * (proj / dist_light) * params.light_radius * 2.0
                    if dist_xy < br + penumbra_width:
                        t = (dist_xy - br) / penumbra_width
                        shadow_val = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * t
                        min_f = min(min_f, shadow_val)
    return min_f

def render_frame(params, frame_time, width=80, height=40):
    """Rendert einen Frame als Liste von Strings (ASCII)."""
    # Kamera-Setup
    cam_pos = (0.0, -15.0, 2.0)
    look_at = (0.0, 0.0, 1.0)
    up = (0.0, 0.0, 1.0)
    fov = math.radians(60.0)
    aspect = width / height
    
    # Lichtposition (bewegt sich langsam)
    light_angle = frame_time * 0.2
    light_pos = (math.sin(light_angle) * 8.0, math.cos(light_angle) * 8.0, 6.0)
    
    # Bäume: (x, y, radius, height)
    baeume = [
        (-4.0, -2.0, 0.8, 4.0),
        (3.0, 1.0, 0.6, 3.5),
        (-2.0, 5.0, 0.7, 3.0),
        (5.0, -4.0, 0.9, 4.5),
        (0.0, 6.0, 0.5, 2.5),
        (-6.0, -3.0, 0.8, 3.8),
    ]
    
    # Farbtemperatur
    r_f, g_f, b_f = kelvin_to_rgb_factor(params.color_temp)
    
    # Ray-Marching Parameter
    max_dist = 30.0
    steps = params.march_steps
    step_size = max_dist / steps
    
    # Vorberechnete View-Richtungen für jeden Pixel
    forward = (look_at[0] - cam_pos[0], look_at[1] - cam_pos[1], look_at[2] - cam_pos[2])
    f_len = math.sqrt(forward[0]**2 + forward[1]**2 + forward[2]**2)
    forward = (forward[0]/f_len, forward[1]/f_len, forward[2]/f_len)
    right = (forward[1]*up[2] - forward[2]*up[1],
             forward[2]*up[0] - forward[0]*up[2],
             forward[0]*up[1] - forward[1]*up[0])
    r_len = math.sqrt(right[0]**2 + right[1]**2 + right[2]**2)
    right = (right[0]/r_len, right[1]/r_len, right[2]/r_len)
    up_vec = (right[1]*forward[2] - right[2]*forward[1],
              right[2]*forward[0] - right[0]*forward[2],
              right[0]*forward[1] - right[1]*forward[0])
    
    half_height = math.tan(fov * 0.5)
    half_width = half_height * aspect
    
    frame = []
    for j in range(height):
        line_chars = []
        for i in range(width):
            # Normalized device coordinates
            u = (i + 0.5) / width * 2.0 - 1.0
            v = (j + 0.5) / height * 2.0 - 1.0
            # Ray direction
            dir_x = forward[0] + right[0] * u * half_width + up_vec[0] * v * half_height
            dir_y = forward[1] + right[1] * u * half_width + up_vec[1] * v * half_height
            dir_z = forward[2] + right[2] * u * half_width + up_vec[2] * v * half_height
            d_len = math.sqrt(dir_x**2 + dir_y**2 + dir_z**2)
            dir_x, dir_y, dir_z = dir_x/d_len, dir_y/d_len, dir_z/d_len
            
            # Ray Marching
            accumulated = 0.0
            transmittance = 1.0
            for s in range(steps):
                t = (s + 0.5) * step_size
                px = cam_pos[0] + dir_x * t
                py = cam_pos[1] + dir_y * t
                pz = cam_pos[2] + dir_z * t
                
                # Mist density at this point
                density = mist_dichte((px, py, pz), params)
                if density <= 0.0:
                    continue
                
                # Shadow factor towards light
                shadow = schattenfaktor_3d((px, py, pz), light_pos, baeume, params)
                
                # Vector to light
                lx = light_pos[0] - px
                ly = light_pos[1] - py
                lz = light_pos[2] - pz
                l_dist = math.sqrt(lx**2 + ly**2 + lz**2)
                if l_dist < 0.01:
                    continue
                lx, ly, lz = lx/l_dist, ly/l_dist, lz/l_dist
                
                # Phase function (Henyey-Greenstein)
                cos_theta = dir_x * lx + dir_y * ly + dir_z * lz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                
                # Light intensity falloff
                falloff = 1.0 / (l_dist**2 + 0.1)
                
                # Scattering contribution
                scatter = density * params.scattering_coeff * phase * falloff * shadow
                
                # Absorption
                absorb = density * params.absorption_coeff
                transmittance *= math.exp(-absorb * step_size)
                
                accumulated += scatter * transmittance * step_size
                
                # Early exit if transmittance too low
                if transmittance < params.early_exit_threshold:
                    break
            
            # Add ambient
            accumulated += params.ambient
            
            # Apply volumetric gain and color temperature
            accumulated *= params.volumetric_gain
            accumulated = accumulated * (0.3 + 0.7 * r_f)  # simplify to monochrome with warm tint
            
            # Tone mapping / gamma
            char = intensitaet_zu_ascii(accumulated, params.gamma)
            line_chars.append(char)
        frame.append(''.join(line_chars))
    return frame

def main():
    params = ShaderParams()
    frame_count = 0
    max_frames = 20  # safety limit
    print("3D-Lichtspiel: Volumetrisches Licht und Schatten im herbstlichen Park")
    print("Drücke Enter für nächsten Frame, 'q' zum Beenden. Strg+C oder EOF beendet ebenfalls.")
    try:
        while frame_count < max_frames:
            frame_time = frame_count * 0.1
            frame = render_frame(params, frame_time)
            # Clear screen (ANSI escape)
            print("\033[H\033[J", end='')
            for line in frame:
                print(line)
            print(f"Frame {frame_count+1}/{max_frames}  (Zeit: {frame_time:.1f}s)")
            frame_count += 1
            
            # Wait for user input (non-blocking would be better, but simple)
            try:
                user_in = input("[Enter=weiter, q=quit] ").strip().lower()
                if user_in == 'q':
                    break
            except EOFError:
                print("\nEOF erkannt. Beende freundlich.")
                break
    except KeyboardInterrupt:
        print("\nAbbruch durch Benutzer. Tschüss!")
    print("Danke fürs Zuschauen. Der Dodo schläft weiter.")

if __name__ == "__main__":
    main()