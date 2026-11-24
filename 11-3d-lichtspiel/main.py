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
        self.march_steps = 8
        self.jitter_enabled = True
        self.specular_intensity = 0.7
        self.specular_power = 18.0
        self.light_radius = 0.7
        self.vibrancy = 1.25
        self.depth_shading_wrap = 0.35
        self.bloom_threshold = 0.6
        self.bloom_intensity = 0.45
        self.bloom_radius = 3
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
                # horizontale Distanz vom Strahl zum Baumstamm
                dist_horiz = abs(dx * uy - dy * ux)
                if dist_horiz < br:
                    umbra_radius = br - params.penumbra_breite
                    if dist_horiz <= umbra_radius:
                        f = params.umbra_dunkelheit
                    else:
                        t = (dist_horiz - umbra_radius) / params.penumbra_breite
                        f = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * t
                    if f < min_f:
                        min_f = f
    return min_f

def compute_light_at_point(pos, light_pos, baeume, params):
    """Berechnet die Lichtintensität an einem Punkt (Skalar 0..1)."""
    px, py, pz = pos
    lx, ly, lz = light_pos
    vx, vy, vz = lx - px, ly - py, lz - pz
    dist = math.sqrt(vx * vx + vy * vy + vz * vz)
    if dist < 0.001:
        return 1.0
    # Schatten
    shadow = schattenfaktor_3d(pos, light_pos, baeume, params)
    # Falloff
    falloff = 1.0 / max(params.falloff_start, dist) ** params.falloff_exponent
    # Volumetrisches Streulicht (einfache Raymarch-Integration vom Licht zum Punkt)
    steps = params.march_steps
    scatter_acc = 0.0
    transmittance = 1.0
    for i in range(steps):
        t = (i + 0.5) / steps
        sx = lx + (px - lx) * t
        sy = ly + (py - ly) * t
        sz = lz + (pz - lz) * t
        density = mist_dichte((sx, sy, sz), params)
        # Absorption
        transmittance *= math.exp(-params.absorption_coeff * density * dist / steps)
        # Streuung in Richtung Betrachter (hier vereinfacht: Phase-Funktion mit cos_theta=1)
        phase = henyey_greenstein(1.0, params.phase_g)
        scatter_acc += density * phase * transmittance
    volumetric = scatter_acc * params.volumetric_gain * dist / steps
    # Gesamthelligkeit
    intensity = (falloff * shadow + volumetric) * transmittance + params.ambient
    return max(0.0, min(1.0, intensity))

def render_frame(light_pos, baeume, params, width, height, world_scale):
    """Rendert ein 2D-Gitter der Lichtintensität auf Bodenhöhe (z=0)."""
    grid = [[0.0 for _ in range(width)] for __ in range(height)]
    half_w = width * world_scale * 0.5
    half_h = height * world_scale * 0.5
    for y in range(height):
        wy = (y - half_h) * world_scale
        for x in range(width):
            wx = (x - half_w) * world_scale
            intensity = compute_light_at_point((wx, wy, 0.0), light_pos, baeume, params)
            grid[y][x] = intensity
    return grid

def apply_bloom(grid, params):
    """Einfacher Bloom-Effekt durch Threshold und Blur."""
    h, w = len(grid), len(grid[0])
    # Threshold
    bloom_src = [[max(0.0, v - params.bloom_threshold) for v in row] for row in grid]
    # Blur
    weights = gauß_gewichte(params.bloom_radius)
    bloom_blur = box_blur_1d(bloom_src, weights, True)
    bloom_blur = box_blur_1d(bloom_blur, weights, False)
    # Add back
    for y in range(h):
        for x in range(w):
            grid[y][x] = min(1.0, grid[y][x] + bloom_blur[y][x] * params.bloom_intensity)
    return grid

def intensity_to_ascii(grid, params):
    """Wandelt Intensitäts-Gitter in Liste von Strings um."""
    lines = []
    for row in grid:
        line = ''.join(intensitaet_zu_ascii(v, params.gamma) for v in row)
        lines.append(line)
    return lines

def main():
    params = ShaderParams()
    # Beispiel-Bäume: (x, y, radius, height)
    baeume = [
        (-2.0, 1.5, 0.4, 3.0),
        (3.0, -1.0, 0.5, 2.5),
        (-1.0, -2.5, 0.3, 2.0),
        (4.0, 2.0, 0.6, 3.5),
        (0.0, 3.0, 0.4, 2.8),
    ]
    light_pos = [0.0, 0.0, 4.0]  # startet mittig über dem Ursprung
    width, height = 80, 40
    world_scale = 0.15  # Weltkoordinaten pro Zeichen
    frame = 0
    print("3D-Lichtspiel – Drücke Enter für nächsten Frame, 'q' zum Beenden, 'm <wert>' für Mistdichte.")
    try:
        while True:
            # Licht langsam im Kreis bewegen
            angle = frame * 0.03
            light_pos[0] = 3.0 * math.cos(angle)
            light_pos[1] = 3.0 * math.sin(angle)
            light_pos[2] = 4.0 + 0.5 * math.sin(frame * 0.07)
            
            grid = render_frame(light_pos, baeume, params, width, height, world_scale)
            grid = apply_bloom(grid, params)
            lines = intensity_to_ascii(grid, params)
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"Frame {frame} | Licht: ({light_pos[0]:.2f}, {light_pos[1]:.2f}, {light_pos[2]:.2f}) | Mist: {params.mist_density:.2f}")
            for line in lines:
                print(line)
            
            # Eingabe
            try:
                inp = input("> ").strip()
            except EOFError:
                break
            if not inp:
                frame += 1
                continue
            if inp.lower() == 'q':
                break
            parts = inp.split()
            if parts[0] == 'm' and len(parts) == 2:
                try:
                    params.mist_density = max(0.0, min(2.0, float(parts[1])))
                    print(f"Mistdichte auf {params.mist_density:.2f} gesetzt.")
                except ValueError:
                    pass
            frame += 1
    except KeyboardInterrupt:
        pass
    print("\nBis zum nächsten Traum.")

if __name__ == "__main__":
    main()