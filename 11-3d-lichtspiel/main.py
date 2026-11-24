import math, sys, random, unicodedata, time, os

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
                dist_xy_sq = dx * dx + dy * dy - proj * proj
                if dist_xy_sq < br * br:
                    # inside trunk radius
                    return params.umbra_dunkelheit
                # penumbra
                dist_xy = math.sqrt(dist_xy_sq)
                penumbra = (dist_xy - br) / (params.penumbra_breite * br)
                if penumbra < 1.0:
                    min_f = min(min_f, penumbra)
    return min_f

def render_frame(params, width=60, height=30):
    """Erzeugt einen einfachen ASCII-Frame mit volumetrischem Licht."""
    # Kamera und Lichtposition
    cam = (0.0, 0.0, 1.8)
    light = (9.6, 2.8, 8.1)
    # Ein paar Bäume: (x, y, radius, height)
    baeume = [
        (-3.0, -2.0, 0.5, 4.0),
        (5.0, 1.0, 0.4, 3.5),
        (2.0, -4.0, 0.6, 5.0),
        (-6.0, 3.0, 0.3, 3.0),
    ]
    # Blickrichtung: leicht nach unten
    yaw = math.radians(-6)
    pitch = math.radians(6)
    dir_x = math.cos(pitch) * math.sin(yaw)
    dir_y = math.cos(pitch) * math.cos(yaw)
    dir_z = math.sin(pitch)
    # Rechtvektor für horizontales Scannen
    right = (-dir_y, dir_x, 0.0)
    up = (0.0, 0.0, 1.0)
    fov = math.radians(60)
    aspect = width / height
    frame = []
    for iy in range(height):
        line_chars = []
        for ix in range(width):
            # Normalisierte Gerätekoordinaten
            nx = (ix + 0.5) / width * 2.0 - 1.0
            ny = (iy + 0.5) / height * 2.0 - 1.0
            # Strahlrichtung
            rx = dir_x + right[0] * nx * math.tan(fov/2) * aspect + up[0] * ny * math.tan(fov/2)
            ry = dir_y + right[1] * nx * math.tan(fov/2) * aspect + up[1] * ny * math.tan(fov/2)
            rz = dir_z + right[2] * nx * math.tan(fov/2) * aspect + up[2] * ny * math.tan(fov/2)
            rlen = math.sqrt(rx*rx + ry*ry + rz*rz)
            rx, ry, rz = rx/rlen, ry/rlen, rz/rlen
            # Einfaches Raymarching für Volumetrisches Licht
            steps = params.march_steps
            max_dist = 30.0
            step_size = max_dist / steps
            accum = 0.0
            for s in range(steps):
                t = (s + 0.5) * step_size
                px = cam[0] + rx * t
                py = cam[1] + ry * t
                pz = cam[2] + rz * t
                if pz < 0.0:
                    continue
                # Nebeldichte
                d = mist_dichte((px, py, pz), params)
                if d <= 0.0:
                    continue
                # Schattenfaktor
                shadow = schattenfaktor_3d((px, py, pz), light, baeume, params)
                # Streuung (vereinfacht Henyey-Greenstein)
                lx, ly, lz = light[0]-px, light[1]-py, light[2]-pz
                ldist = math.sqrt(lx*lx + ly*ly + lz*lz)
                if ldist > 0.0:
                    lx, ly, lz = lx/ldist, ly/ldist, lz/ldist
                    cos_theta = rx*lx + ry*ly + rz*lz
                    phase = henyey_greenstein(cos_theta, params.phase_g)
                else:
                    phase = 1.0
                # Falloff
                falloff = 1.0 / (1.0 + (ldist * params.falloff_start) ** params.falloff_exponent)
                accum += d * shadow * phase * falloff * params.volumetric_gain * step_size
                if accum > 1.0:
                    accum = 1.0
            # Ambient hinzufügen
            accum = min(1.0, accum + params.ambient)
            line_chars.append(intensitaet_zu_ascii(accum, params.gamma))
        frame.append(''.join(line_chars))
    return frame

def main():
    params = ShaderParams()
    print("3D-Lichtspiel – Herbstlicher Park (ASCII)")
    print("Drücke Enter für einen Frame, 'q' zum Beenden.")
    frame_count = 0
    try:
        while frame_count < 3:  # maximal 3 Frames, damit der Test schnell durchläuft
            inp = input("> ").strip().lower()
            if inp == 'q':
                break
            # Frame rendern
            start = time.time()
            frame = render_frame(params)
            elapsed = time.time() - start
            for line in frame:
                print(line)
            print(f"Renderzeit: {elapsed:.3f}s  Frame: {frame_count+1}")
            frame_count += 1
    except EOFError:
        pass
    print("Tschüss, Dodo träumt weiter.")

if __name__ == "__main__":
    main()