import math, sys, random, unicodedata, time, os

class ShaderParams:
    """Container für alle einstellbaren Shader-Parameter mit Defaults."""
    def __init__(self):
        self.penumbra_breite = 0.15
        self.umbra_dunkelheit = 0.05
        self.falloff_exponent = 2.0
        self.falloff_start = 0.5
        self.blur_radius = 1
        self.ambient = 0.08
        self.volumetric_gain = 1.0
        self.gamma = 0.6
        self.scattering_coeff = 0.3
        self.absorption_coeff = 0.08
        self.mist_density = 0.15
        self.mist_height_falloff = 0.8
        self.color_temp = 3200.0
        self.jitter_strength = 0.10
        self.phase_g = 0.55
        self.noise_seed = 42
        self.march_steps = 32
        self.jitter_enabled = True
        self.specular_intensity = 0.7
        self.specular_power = 18.0
        self.light_radius = 0.7
        self.vibrancy = 1.25
        self.depth_shading_wrap = 0.35
        self.bloom_threshold = 0.6
        self.bloom_intensity = 0.3
        self.bloom_radius = 1
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

def noise_2d(x, y, seed):
    ix, iy = int(math.floor(x)), int(math.floor(y))
    fx, fy = x - ix, y - iy
    def h(ix, iy):
        n = (ix * 73856093) ^ (iy * 19349663) ^ seed
        n = (n ^ (n >> 13)) * 0x5bd1e995
        n = (n ^ (n >> 15)) * 0x5bd1e995
        return ((n ^ (n >> 15)) & 0x7fffffff) / 2147483647.0
    u = fx * fx * (3.0 - 2.0 * fx)
    v = fy * fy * (3.0 - 2.0 * fy)
    a = h(ix, iy)
    b = h(ix + 1, iy)
    c = h(ix, iy + 1)
    d = h(ix + 1, iy + 1)
    x1 = a + (b - a) * u
    x2 = c + (d - c) * u
    return x1 + (x2 - x1) * v

def mist_dichte(pos, params):
    x, y, z = pos
    if z < 0.0:
        return 0.0
    basis = params.mist_density * math.exp(-z * params.mist_height_falloff)
    turbulenz = noise_2d(x * 0.45, y * 0.45, params.noise_seed)
    return max(0.0, basis * (0.65 + 0.7 * turbulenz))

def schattenfaktor_3d(pos, light_pos, baeume, params):
    px, py, pz = pos
    lx, ly, lz = light_pos
    vx, vy, vz = lx - px, ly - py, lz - pz
    dist_light_sq = vx * vx + vy * vy + vz * vz
    if dist_light_sq < 0.0025:
        return 1.0
    dist_light = math.sqrt(dist_light_sq)
    ux, uy, uz = vx / dist_light, vy / dist_light, vz / dist_light
    min_f = 1.0
    for bx, by, br, bh in baeume:
        dx, dy = bx - px, by - py
        proj = dx * ux + dy * uy
        if 0.2 < proj < dist_light:
            cz = pz + uz * proj
            if 0.0 <= cz <= bh:
                dist_center_sq = dx * dx + dy * dy - proj * proj
                if dist_center_sq < br * br:
                    dist_center = math.sqrt(dist_center_sq)
                    rand_faktor = 1.0 - (dist_center / br)
                    penumbra = params.penumbra_breite * (proj / dist_light)
                    shadow = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * max(0.0, (rand_faktor - penumbra) / max(0.001, 1.0 - penumbra))
                    min_f = min(min_f, shadow)
    return min_f

def render_frame(breite, hoehe, params, baeume, light_pos, cam_pos, cam_yaw, cam_pitch, t):
    cos_yaw, sin_yaw = math.cos(cam_yaw), math.sin(cam_yaw)
    cos_pitch, sin_pitch = math.cos(cam_pitch), math.sin(cam_pitch)
    lr, lg, lb = kelvin_to_rgb_factor(params.color_temp)
    fb_r = [[0.0 for _ in range(breite)] for __ in range(hoehe)]
    fb_g = [[0.0 for _ in range(breite)] for __ in range(hoehe)]
    fb_b = [[0.0 for _ in range(breite)] for __ in range(hoehe)]
    
    forward = (cos_yaw * cos_pitch, sin_yaw * cos_pitch, sin_pitch)
    right = (-sin_yaw, cos_yaw, 0.0)
    up = (-cos_yaw * sin_pitch, -sin_yaw * sin_pitch, cos_pitch)
    
    fov = math.pi / 3.0
    aspect = breite / hoehe
    
    jitter_x = 0.0
    jitter_y = 0.0
    if params.jitter_enabled:
        random.seed(params.noise_seed + int(t * 1000))
        jitter_x = (random.random() - 0.5) * params.jitter_strength
        jitter_y = (random.random() - 0.5) * params.jitter_strength
    
    for y in range(hoehe):
        for x in range(breite):
            ndc_x = ((x + 0.5 + jitter_x) / breite) * 2.0 - 1.0
            ndc_y = 1.0 - ((y + 0.5 + jitter_y) / hoehe) * 2.0
            
            ray_x = forward[0] + right[0] * ndc_x * aspect * math.tan(fov * 0.5) + up[0] * ndc_y * math.tan(fov * 0.5)
            ray_y = forward[1] + right[1] * ndc_x * aspect * math.tan(fov * 0.5) + up[1] * ndc_y * math.tan(fov * 0.5)
            ray_z = forward[2] + right[2] * ndc_x * aspect * math.tan(fov * 0.5) + up[2] * ndc_y * math.tan(fov * 0.5)
            ray_len = math.sqrt(ray_x*ray_x + ray_y*ray_y + ray_z*ray_z)
            ray_x /= ray_len
            ray_y /= ray_len
            ray_z /= ray_len
            
            steps = params.march_steps
            max_dist = 15.0
            step_size = max_dist / steps
            
            transmittance = 1.0
            acc_r, acc_g, acc_b = 0.0, 0.0, 0.0
            pos_x, pos_y, pos_z = cam_pos[0] + ray_x * 0.1, cam_pos[1] + ray_y * 0.1, cam_pos[2] + ray_z * 0.1
            
            for step in range(steps):
                density = mist_dichte((pos_x, pos_y, pos_z), params)
                if density > 0.0:
                    shadow = schattenfaktor_3d((pos_x, pos_y, pos_z), light_pos, baeume, params)
                    lx, ly, lz = light_pos[0] - pos_x, light_pos[1] - pos_y, light_pos[2] - pos_z
                    light_dist = math.sqrt(lx*lx + ly*ly + lz*lz)
                    phase = henyey_greenstein((ray_x * lx + ray_y * ly + ray_z * lz) / max(0.001, light_dist), params.phase_g)
                    
                    scattering = params.scattering_coeff * density * shadow * phase
                    extinction = (scattering + params.absorption_coeff * density) * step_size
                    transmittance *= math.exp(-extinction)
                    light_intensity = 1.0 / (1.0 + light_dist * light_dist * 0.05)
                    contrib = scattering * light_intensity * transmittance * step_size
                    acc_r += contrib * lr
                    acc_g += contrib * lg
                    acc_b += contrib * lb
                
                if transmittance < params.early_exit_threshold:
                    break
                pos_x += ray_x * step_size
                pos_y += ray_y * step_size
                pos_z += ray_z * step_size
            
            fb_r[y][x] = (acc_r + params.ambient * lr) * params.volumetric_gain
            fb_g[y][x] = (acc_g + params.ambient * lg) * params.volumetric_gain
            fb_b[y][x] = (acc_b + params.ambient * lb) * params.volumetric_gain
    
    return [[intensitaet_zu_ascii(0.2126*fb_r[y][x] + 0.7152*fb_g[y][x] + 0.0722*fb_b[y][x], params.gamma) for x in range(breite)] for y in range(hoehe)]

def main():
    print("🍂 3D-Lichtspiel – Herbstlicher Park-Simulator 🍂")
    params = ShaderParams()
    baeume = [(-5.0, -3.0, 1.2, 8.0), (4.0, 2.0, 1.0, 6.5), (-2.0, 5.0, 0.8, 7.0), (6.0, -4.0, 1.5, 9.0)]
    light_pos, cam_pos = (0.0, 0.0, 15.0), (0.0, -10.0, 1.8)
    breite, hoehe, frame = 80, 20, 0
    try:
        while True:
            t = frame * 0.5
            curr_light = (math.sin(t * 0.3) * 8.0, math.cos(t * 0.3) * 8.0, 15.0)
            frame_ascii = render_frame(breite, hoehe, params, baeume, curr_light, cam_pos, 0, 0, t)
            for row in frame_ascii: print("".join(row))
            eingabe = input(f"\nFrame {frame} [enter=weiter, q=quit]: ").strip().lower()
            if eingabe == 'q': break
            frame += 1
    except EOFError: pass
    print("\n🍃 Danke fürs Zuschauen. 🍃")

if __name__ == "__main__":
    main()