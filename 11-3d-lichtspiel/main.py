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
        self.march_steps = 32          # erhöht auf 32
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
    
    # Kamerarichtungsvektoren
    forward = (cos_yaw * cos_pitch, sin_yaw * cos_pitch, sin_pitch)
    right = (-sin_yaw, cos_yaw, 0.0)
    up = (-cos_yaw * sin_pitch, -sin_yaw * sin_pitch, cos_pitch)
    
    fov = math.pi / 3.0  # 60 Grad
    aspect = breite / hoehe
    max_dist = 50.0
    base_step = max_dist / params.march_steps
    
    for y in range(hoehe):
        for x in range(breite):
            # NDC-Koordinaten
            ndc_x = (x + 0.5) / breite * 2.0 - 1.0
            ndc_y = 1.0 - (y + 0.5) / hoehe * 2.0
            # Ray Direction
            dir_x = forward[0] + right[0] * ndc_x * aspect * math.tan(fov * 0.5) + up[0] * ndc_y * math.tan(fov * 0.5)
            dir_y = forward[1] + right[1] * ndc_x * aspect * math.tan(fov * 0.5) + up[1] * ndc_y * math.tan(fov * 0.5)
            dir_z = forward[2] + right[2] * ndc_x * aspect * math.tan(fov * 0.5) + up[2] * ndc_y * math.tan(fov * 0.5)
            dir_len = math.sqrt(dir_x*dir_x + dir_y*dir_y + dir_z*dir_z)
            dir_x, dir_y, dir_z = dir_x/dir_len, dir_y/dir_len, dir_z/dir_len
            
            # Jitter für temporale Stabilität
            if params.jitter_enabled:
                jitter = (random.random() - 0.5) * params.jitter_strength * base_step
            else:
                jitter = 0.0
            
            # Raymarching
            transmittance = 1.0
            acc_r, acc_g, acc_b = 0.0, 0.0, 0.0
            dist = 0.0
            step = base_step
            
            while dist < max_dist and transmittance > params.early_exit_threshold:
                pos = (cam_pos[0] + (dist + jitter) * dir_x,
                       cam_pos[1] + (dist + jitter) * dir_y,
                       cam_pos[2] + (dist + jitter) * dir_z)
                
                density = mist_dichte(pos, params)
                if density > 0.0:
                    shadow = schattenfaktor_3d(pos, light_pos, baeume, params)
                    # Lichtrichtung
                    ldx = light_pos[0] - pos[0]
                    ldy = light_pos[1] - pos[1]
                    ldz = light_pos[2] - pos[2]
                    ldist = math.sqrt(ldx*ldx + ldy*ldy + ldz*ldz)
                    if ldist > 1e-5:
                        ldx, ldy, ldz = ldx/ldist, ldy/ldist, ldz/ldist
                        cos_theta = dir_x * ldx + dir_y * ldy + dir_z * ldz
                        phase = henyey_greenstein(cos_theta, params.phase_g)
                        scatter = density * shadow * phase * params.scattering_coeff * step
                        attenuation = math.exp(-density * params.absorption_coeff * step)
                        acc_r += transmittance * scatter * lr
                        acc_g += transmittance * scatter * lg
                        acc_b += transmittance * scatter * lb
                        transmittance *= attenuation
                
                # Adaptive Schrittweite
                if params.adaptive_steps:
                    # Schrittweite basierend auf Dichte anpassen: dichter -> kleiner Schritt
                    step = base_step * max(params.min_step_factor, min(params.max_step_factor, 1.0 / (1.0 + density * 5.0)))
                else:
                    step = base_step
                dist += step
            
            # Umgebungslicht und Verstärkung
            acc_r = (acc_r + params.ambient * lr) * params.volumetric_gain
            acc_g = (acc_g + params.ambient * lg) * params.volumetric_gain
            acc_b = (acc_b + params.ambient * lb) * params.volumetric_gain
            
            # Vibrancy / Sättigung
            lum = 0.2126 * acc_r + 0.7152 * acc_g + 0.0722 * acc_b
            acc_r = lum + (acc_r - lum) * params.vibrancy
            acc_g = lum + (acc_g - lum) * params.vibrancy
            acc_b = lum + (acc_b - lum) * params.vibrancy
            
            fb_r[y][x] = acc_r
            fb_g[y][x] = acc_g
            fb_b[y][x] = acc_b
    
    # Bloom (optional)
    if params.bloom_intensity > 0.0 and params.bloom_radius > 0:
        # Luminanz extrahieren
        lum_buf = [[0.0 for _ in range(breite)] for __ in range(hoehe)]
        for y in range(hoehe):
            for x in range(breite):
                lum_buf[y][x] = 0.2126 * fb_r[y][x] + 0.7152 * fb_g[y][x] + 0.0722 * fb_b[y][x]
        # Threshold
        for y in range(hoehe):
            for x in range(breite):
                if lum_buf[y][x] < params.bloom_threshold:
                    lum_buf[y][x] = 0.0
        # Blur
        weights = gauß_gewichte(params.bloom_radius)
        lum_buf = box_blur_1d(lum_buf, weights, True)
        lum_buf = box_blur_1d(lum_buf, weights, False)
        # Add back
        for y in range(hoehe):
            for x in range(breite):
                fb_r[y][x] += lum_buf[y][x] * params.bloom_intensity * lr
                fb_g[y][x] += lum_buf[y][x] * params.bloom_intensity * lg
                fb_b[y][x] += lum_buf[y][x] * params.bloom_intensity * lb
    
    return fb_r, fb_g, fb_b

def frame_to_ascii(fb_r, fb_g, fb_b, gamma):
    hoehe = len(fb_r)
    breite = len(fb_r[0])
    lines = []
    for y in range(hoehe):
        line = []
        for x in range(breite):
            lum = 0.2126 * fb_r[y][x] + 0.7152 * fb_g[y][x] + 0.0722 * fb_b[y][x]
            line.append(intensitaet_zu_ascii(lum, gamma))
        lines.append(''.join(line))
    return '\n'.join(lines)

def main():
    params = ShaderParams()
    breite, hoehe = 80, 40
    
    # Beispiel-Szene: Bäume (x, y, radius, höhe)
    baeume = [
        (-5.0, -3.0, 0.8, 4.0),
        (3.0, 2.0, 0.6, 3.5),
        (-2.0, 4.0, 0.7, 3.0),
        (6.0, -1.0, 0.9, 4.5),
        (0.0, -5.0, 0.5, 2.5),
    ]
    light_pos = (0.0, 0.0, 10.0)
    cam_pos = (0.0, -8.0, 1.5)
    cam_yaw = 0.0
    cam_pitch = 0.2
    t = 0.0
    
    print("3D-Lichtspiel – interaktiver volumetrischer Simulator")
    print("Steuerung: [Enter] Weiter  [q] Beenden  [+/-] Mist-Dichte  [1/2] Steps  [b] Bloom")
    print("Drücke Enter für den ersten Frame...")
    
    try:
        while True:
            user_in = input().strip().lower()
            if user_in == 'q':
                break
            elif user_in == '+':
                params.mist_density = min(1.0, params.mist_density + 0.02)
                print(f"Mist-Dichte: {params.mist_density:.2f}")
                continue
            elif user_in == '-':
                params.mist_density = max(0.0, params.mist_density - 0.02)
                print(f"Mist-Dichte: {params.mist_density:.2f}")
                continue
            elif user_in == '1':
                params.march_steps = max(4, params.march_steps - 4)
                print(f"March Steps: {params.march_steps}")
                continue
            elif user_in == '2':
                params.march_steps = min(64, params.march_steps + 4)
                print(f"March Steps: {params.march_steps}")
                continue
            elif user_in == 'b':
                params.bloom_intensity = 0.3 if params.bloom_intensity == 0.0 else 0.0
                print(f"Bloom: {'an' if params.bloom_intensity > 0 else 'aus'}")
                continue
            # Enter oder andere Eingabe -> nächsten Frame rendern
            
            fb_r, fb_g, fb_b = render_frame(breite, hoehe, params, baeume, light_pos, cam_pos, cam_yaw, cam_pitch, t)
            ascii_frame = frame_to_ascii(fb_r, fb_g, fb_b, params.gamma)
            print(ascii_frame)
            print("[Enter] Weiter  [q] Beenden  [+/-] Mist-Dichte  [1/2] Steps  [b] Bloom")
            
            # Leichte Animation
            t += 0.1
            light_pos = (math.sin(t) * 5.0, math.cos(t) * 3.0, 10.0 + math.sin(t * 0.5) * 2.0)
            cam_yaw += 0.01
    except EOFError:
        pass
    print("Auf Wiedersehen!")

if __name__ == "__main__":
    main()