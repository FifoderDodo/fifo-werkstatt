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
                # Abstand zur Baumkrone (einfacher Zylinder)
                rad = math.hypot(cx - bx, cy - by)
                if rad < br:
                    # Voller Schatten
                    return 0.0
    return min_f

def raymarch_light(pos, dir_vec, light_pos, baeume, params):
    """Raymarch entlang dir_vec von pos zur Lichtquelle.
    Gibt transmittanz (0..1) zurück, adaptiv gesteuert."""
    step = params.light_radius / params.march_steps
    trans = 1.0
    cur = list(pos)
    for i in range(params.march_steps):
        # Abstand zur Lichtquelle
        to_light = [light_pos[j] - cur[j] for j in range(3)]
        dist = math.sqrt(sum(d * d for d in to_light))
        if dist < step:
            break
        # Dichte am aktuellen Punkt
        dens = mist_dichte(tuple(cur), params)
        # Adaptive Schrittweite
        if params.adaptive_steps:
            step = max(step * params.min_step_factor, min(step * params.max_step_factor, step * (1.0 - dens)))
        # Abschwächung durch Nebel
        trans *= math.exp(-dens * params.absorption_coeff * step)
        if trans < params.early_exit_threshold:
            return 0.0
        # Schritt vorwärts
        for j in range(3):
            cur[j] += dir_vec[j] * step
    # Schatten durch Bäume
    shad = schattenfaktor_3d(pos, light_pos, baeume, params)
    return trans * shad

def render_frame(width, height, params, light_pos, baeume):
    buffer = [[0.0 for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(width):
            # Bildkoordinaten in Weltkoordinaten (einfaches Orthogonal-Setup)
            world_x = (x - width / 2) * 0.05
            world_y = (y - height / 2) * 0.05
            world_z = 1.5  # Kamerahöhe
            pos = (world_x, world_y, world_z)
            # Richtung zum Licht
            lx, ly, lz = light_pos
            dir_vec = [(lx - world_x), (ly - world_y), (lz - world_z)]
            norm = math.sqrt(sum(d * d for d in dir_vec))
            dir_vec = [d / norm for d in dir_vec]
            # Grundhelligkeit durch direkte Beleuchtung + Volumen
            trans = raymarch_light(pos, dir_vec, light_pos, baeume, params)
            intensity = params.ambient + params.volumetric_gain * trans
            buffer[y][x] = intensity
    # Bloom-Pass (einfaches 2‑D‑Gaussian‑Blur)
    if params.bloom_intensity > 0:
        kernel = gauß_gewichte(params.bloom_radius)
        horiz = box_blur_1d(buffer, kernel, True)
        blurred = box_blur_1d(horiz, kernel, False)
        for y in range(height):
            for x in range(width):
                if buffer[y][x] > params.bloom_threshold:
                    buffer[y][x] += blurred[y][x] * params.bloom_intensity
    # ASCII‑Ausgabe
    lines = []
    for row in buffer:
        line = ''.join(intensitaet_zu_ascii(v, params.gamma) for v in row)
        lines.append(line)
    return '\n'.join(lines)

def beispiel_baeume():
    # Einige zufällige Bäume (x, y, radius, höhe)
    random.seed(1)
    return [(random.uniform(-3, 3), random.uniform(-3, 3), random.uniform(0.2, 0.5), random.uniform(1.5, 2.5)) for _ in range(8)]

def main():
    width, height = 80, 30
    params = ShaderParams()
    light_pos = (0.0, 0.0, 5.0)
    baeume = beispiel_baeume()
    print("Drücke Enter für nächsten Frame, EOF zum Beenden...")
    frame = 0
    while True:
        try:
            if frame == 0:
                # erster Frame sofort
                pass
            else:
                input()
        except EOFError:
            print("Auf Wiedersehen!")
            break
        # leichte Animation: Licht leicht rotieren
        angle = frame * 0.05
        light_pos = (5.0 * math.cos(angle), 5.0 * math.sin(angle), 5.0)
        output = render_frame(width, height, params, light_pos, baeume)
        sys.stdout.write('\x1b[H\x1b[2J')  # clear screen
        sys.stdout.write(output + '\n')
        sys.stdout.flush()
        frame += 1
        if frame >= 20:
            print("Maximale Frame‑Anzahl erreicht.")
            break

if __name__ == "__main__":
    main()