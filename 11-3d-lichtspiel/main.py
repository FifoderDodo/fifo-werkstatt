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
                # distance from ray to tree center at projection
                rx = dx - proj * ux
                ry = dy - proj * uy
                d = math.sqrt(rx * rx + ry * ry)
                if d < br:
                    f = params.umbra_dunkelheit
                elif d < br + params.penumbra_breite:
                    t = (d - br) / params.penumbra_breite
                    f = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * t
                else:
                    f = 1.0
                if f < min_f:
                    min_f = f
    return min_f

def render_frame(params, baeume, light_pos, cam_pos, cam_dir, cam_up, fov, width, height):
    """Ray-marching volumetric light renderer. Returns 2D list of float intensities."""
    # Precompute camera basis
    forward = cam_dir
    f_len = math.sqrt(forward[0]**2 + forward[1]**2 + forward[2]**2)
    forward = (forward[0]/f_len, forward[1]/f_len, forward[2]/f_len)
    right = (cam_up[1]*forward[2] - cam_up[2]*forward[1],
             cam_up[2]*forward[0] - cam_up[0]*forward[2],
             cam_up[0]*forward[1] - cam_up[1]*forward[0])
    r_len = math.sqrt(right[0]**2 + right[1]**2 + right[2]**2)
    right = (right[0]/r_len, right[1]/r_len, right[2]/r_len)
    up = (forward[1]*right[2] - forward[2]*right[1],
          forward[2]*right[0] - forward[0]*right[2],
          forward[0]*right[1] - forward[1]*right[0])
    
    aspect = width / height
    fov_rad = math.radians(fov)
    half_h = math.tan(fov_rad * 0.5)
    half_w = half_h * aspect
    
    # Light color factor
    light_color = kelvin_to_rgb_factor(params.color_temp)
    
    frame = [[0.0 for _ in range(width)] for __ in range(height)]
    
    for y in range(height):
        for x in range(width):
            # Normalized device coordinates [-1,1]
            nx = (x + 0.5) / width * 2.0 - 1.0
            ny = 1.0 - (y + 0.5) / height * 2.0  # y up
            
            # Ray direction
            rx = forward[0] + right[0] * nx * half_w + up[0] * ny * half_h
            ry = forward[1] + right[1] * nx * half_w + up[1] * ny * half_h
            rz = forward[2] + right[2] * nx * half_w + up[2] * ny * half_h
            r_len = math.sqrt(rx*rx + ry*ry + rz*rz)
            rx, ry, rz = rx/r_len, ry/r_len, rz/r_len
            
            # Ray marching
            max_dist = 30.0
            steps = params.march_steps
            if params.adaptive_steps:
                # simple adaptive: more steps near camera
                steps = int(params.march_steps * (1.0 + 0.5 * random.random()))
            step_size = max_dist / steps
            
            transmittance = 1.0
            radiance = 0.0
            
            for i in range(steps):
                t = (i + 0.5) * step_size
                px = cam_pos[0] + rx * t
                py = cam_pos[1] + ry * t
                pz = cam_pos[2] + rz * t
                
                # Mist density at point
                density = mist_dichte((px, py, pz), params)
                if density <= 0.0:
                    continue
                
                # Shadow factor towards light
                shadow = schattenfaktor_3d((px, py, pz), light_pos, baeume, params)
                
                # Phase function: angle between view ray and light direction
                lx = light_pos[0] - px
                ly = light_pos[1] - py
                lz = light_pos[2] - pz
                l_dist = math.sqrt(lx*lx + ly*ly + lz*lz)
                if l_dist < 1e-3:
                    continue
                lx, ly, lz = lx/l_dist, ly/l_dist, lz/l_dist
                cos_theta = rx*lx + ry*ly + rz*lz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                
                # Light intensity falloff
                falloff = 1.0 / (1.0 + l_dist * l_dist * 0.01)
                
                # Scattering contribution
                scatter = params.scattering_coeff * density * shadow * phase * falloff
                # Absorption along ray segment
                absorption = params.absorption_coeff * density * step_size
                transmittance *= math.exp(-absorption)
                radiance += scatter * transmittance * step_size
                
                # Early exit if transmittance too low
                if transmittance < params.early_exit_threshold:
                    break
            
            # Apply volumetric gain and ambient
            radiance = radiance * params.volumetric_gain + params.ambient
            # Simple tone mapping
            radiance = radiance / (1.0 + radiance)
            # Vibrancy (color saturation approximation)
            radiance = radiance * params.vibrancy
            
            frame[y][x] = radiance
    
    return frame

def main():
    params = ShaderParams()
    
    # Example trees: (x, y, radius, height)
    baeume = [
        (-3.0, 2.0, 0.4, 4.0),
        (2.5, -1.0, 0.3, 3.5),
        (-1.0, -3.0, 0.5, 5.0),
        (4.0, 3.0, 0.35, 4.2),
        (0.0, 5.0, 0.45, 3.8),
    ]
    
    # Default light position
    light_pos = (0.0, 0.0, 8.0)
    
    # Camera setup
    cam_pos = (0.0, -12.0, 2.5)
    cam_dir = (0.0, 1.0, -0.2)  # looking slightly down
    cam_up = (0.0, 0.0, 1.0)
    fov = 70.0
    width, height = 80, 40
    
    # Allow a few interactive inputs (max 20)
    inputs_used = 0
    try:
        if inputs_used < 20:
            ans = input("Light height [8.0]? ").strip()
            inputs_used += 1
            if ans:
                try:
                    light_pos = (light_pos[0], light_pos[1], float(ans))
                except ValueError:
                    pass
        if inputs_used < 20:
            ans = input("Mist density [0.22]? ").strip()
            inputs_used += 1
            if ans:
                try:
                    params.mist_density = float(ans)
                except ValueError:
                    pass
        if inputs_used < 20:
            ans = input("March steps [10]? ").strip()
            inputs_used += 1
            if ans:
                try:
                    params.march_steps = int(ans)
                except ValueError:
                    pass
        if inputs_used < 20:
            ans = input("Color temperature [3200]? ").strip()
            inputs_used += 1
            if ans:
                try:
                    params.color_temp = float(ans)
                except ValueError:
                    pass
    except EOFError:
        pass
    
    print("Rendering...", file=sys.stderr)
    frame = render_frame(params, baeume, light_pos, cam_pos, cam_dir, cam_up, fov, width, height)
    
    # Optional bloom (simple threshold and blur)
    if params.bloom_intensity > 0.0:
        # Threshold
        bloom_src = [[max(0.0, v - params.bloom_threshold) for v in row] for row in frame]
        # Blur horizontally and vertically
        weights = gauß_gewichte(params.bloom_radius)
        bloom_blur = box_blur_1d(bloom_src, weights, True)
        bloom_blur = box_blur_1d(bloom_blur, weights, False)
        # Add back
        for y in range(height):
            for x in range(width):
                frame[y][x] += bloom_blur[y][x] * params.bloom_intensity
    
    # Gamma correction and ASCII conversion
    for y in range(height):
        line = ''.join(intensitaet_zu_ascii(frame[y][x], params.gamma) for x in range(width))
        print(line)
    
    print("Done.", file=sys.stderr)

if __name__ == "__main__":
    main()