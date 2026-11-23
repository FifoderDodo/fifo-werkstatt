import math, sys, random, unicodedata, time, select

class ShaderParams:
    """Container für alle einstellbaren Shader‑Parameter mit Defaults."""
    def __init__(self):
        self.penumbra_breite = 0.15
        self.umbra_dunkelheit = 0.05
        self.falloff_exponent = 2.0
        self.falloff_start = 0.5
        self.blur_radius = 3
        self.ambient = 0.05
        self.volumetric_gain = 2.5
        self.gamma = 0.55
        self.scattering_coeff = 0.45
        self.absorption_coeff = 0.08
        self.mist_density = 0.22
        self.mist_height_falloff = 0.8
        self.color_temp = 3000.0
        self.jitter_strength = 0.12
        self.phase_g = 0.6
        self.noise_seed = 42
        self.march_steps = 16  # reduziert für Performance
        self.jitter_enabled = True
        self.specular_intensity = 0.6
        self.specular_power = 24.0
        self.specular_noise_scale = 0.5
        self.light_radius = 0.8
    def klonen(self):
        k = ShaderParams()
        k.__dict__.update(self.__dict__)
        return k

def _norm(s: str) -> str:
    return unicodedata.normalize('NFC', s).strip().lower()

def gauß_gewichte(kernel_radius: int) -> list:
    size = kernel_radius * 2 + 1
    sigma = kernel_radius / 2.0
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
                    xi = x - k_rad + i
                    if 0 <= xi < w:
                        acc += src[xi] * g
                dst[x] = acc
    else:
        for x in range(w):
            for y in range(h):
                acc = 0.0
                for i, g in enumerate(gewichte):
                    yi = y - k_rad + i
                    if 0 <= yi < h:
                        acc += puffer[yi][x] * g
                ergebnis[y][x] = acc
    return ergebnis

def henyey_greenstein(cos_theta: float, g: float) -> float:
    g2 = g * g
    denom = (1.0 + g2 - 2.0 * g * cos_theta) ** 1.5
    return (1.0 - g2) / (4.0 * math.pi * denom) if denom > 1e-6 else 1.0

def kelvin_to_rgb_factor(temp_k: float) -> tuple:
    t = temp_k / 100.0
    if t <= 66:
        r = 1.0
        g = 0.39008158 * math.log(t) - 0.63184144
    else:
        r = 1.29293619 * (t - 60.0) ** -0.13320476
        g = 1.12989086 * (t - 60.0) ** -0.07551485
    if t >= 66:
        b = 1.0
    elif t <= 19:
        b = 0.0
    else:
        b = 0.54320679 * math.log(t - 10.0) - 1.19625409
    g = max(0.01, g)
    return (r / g, 1.0, b / g)

def intensitaet_zu_ascii(wert: float, gamma: float = 0.6) -> str:
    if wert <= 0.0:
        return ' '
    w = min(1.0, max(0.0, wert)) ** gamma
    if w > 0.85:
        return '@'
    if w > 0.65:
        return '#'
    if w > 0.45:
        return '*'
    if w > 0.25:
        return '+'
    if w > 0.1:
        return '.'
    return ' '

def schattenfaktor_für_punkt(px, py, qx, qy, light_radius, bäume, params):
    dx, dy = px - qx, py - qy
    dist_lp = math.hypot(dx, dy)
    if dist_lp < 0.01:
        return 1.0
    ux, uy = dx / dist_lp, dy / dist_lp
    min_faktor = 1.0
    for bx, by, br in bäume:
        vx, vy = bx - qx, by - qy
        dist_lt = math.hypot(vx, vy)
        if dist_lt < 0.01:
            continue
        proj = vx * ux + vy * uy
        if proj <= 0.01 or proj >= dist_lp:
            continue
        abstand = abs(vx * uy - vy * ux)
        factor = dist_lp / dist_lt
        penumbra_radius = br * factor + light_radius * (factor - 1.0)
        umbra_radius = max(0.0, br * factor - light_radius * (factor - 1.0))
        if abstand >= penumbra_radius:
            continue
        if abstand <= umbra_radius:
            faktor = params.umbra_dunkelheit
        else:
            t = (abstand - umbra_radius) / (penumbra_radius - umbra_radius) if penumbra_radius > umbra_radius else 0.0
            t = max(0.0, min(1.0, t))
            faktor = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * t
        if faktor < min_faktor:
            min_faktor = faktor
    return min_faktor

def noise_2d(x, y, seed):
    n = int(x * 123.45) ^ int(y * 678.91) ^ seed
    n = (n ^ (n >> 13)) * 0x5bd1e995
    n = (n ^ (n >> 15)) * 0x5bd1e995
    n = n ^ (n >> 15)
    return (n & 0x7fffffff) / 0x7fffffff * 2.0 - 1.0

def noise_3d(x, y, z, seed):
    ix, iy, iz = int(math.floor(x)), int(math.floor(y)), int(math.floor(z))
    fx, fy, fz = x - ix, y - iy, z - iz
    def hash3d(ix, iy, iz):
        n = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ seed
        n = (n ^ (n >> 13)) * 0x5bd1e995
        n = (n ^ (n >> 15)) * 0x5bd1e995
        n = n ^ (n >> 15)
        return (n & 0x7fffffff) / 0x7fffffff
    u = fx * fx * (3.0 - 2.0 * fx)
    v = fy * fy * (3.0 - 2.0 * fy)
    w = fz * fz * (3.0 - 2.0 * fz)
    a = hash3d(ix, iy, iz)
    b = hash3d(ix + 1, iy, iz)
    c = hash3d(ix, iy + 1, iz)
    d = hash3d(ix + 1, iy + 1, iz)
    e = hash3d(ix, iy, iz + 1)
    f = hash3d(ix + 1, iy, iz + 1)
    g = hash3d(ix, iy + 1, iz + 1)
    h = hash3d(ix + 1, iy + 1, iz + 1)
    x1 = a + (b - a) * u
    x2 = c + (d - c) * u
    y1 = x1 + (x2 - x1) * v
    x3 = e + (f - e) * u
    x4 = g + (h - g) * u
    y2 = x3 + (x4 - x3) * v
    return y1 + (y2 - y1) * w

def erstelle_szene(params, breite=80, höhe=40):
    """Generiert Bäume, Lichtposition und z-Buffer für den Park."""
    random.seed(params.noise_seed)
    bäume = []
    for _ in range(12):
        bx = random.uniform(10, breite - 10)
        by = random.uniform(5, höhe - 5)
        br = random.uniform(0.5, 2.0)
        bäume.append((bx, by, br))
    # Lichtposition etwas links oben
    light_x = random.uniform(15, breite - 15)
    light_y = random.uniform(5, höhe // 2)
    # Einfacher z-Buffer: flacher Boden, Bäume als hohe Säulen
    z_buffer = [[0.0 for _ in range(breite)] for __ in range(höhe)]
    for y in range(höhe):
        for x in range(breite):
            z_buffer[y][x] = 0.0  # Bodenhöhe
    return bäume, (light_x, light_y), z_buffer

def render_frame(params, breite, höhe, bäume, light_pos, z_buffer):
    """Rendert ein Frame mit volumetrischem Licht und Schatten."""
    lx, ly = light_pos
    # Farbfaktoren für Lichttemperatur
    rf, gf, bf = kelvin_to_rgb_factor(params.color_temp)
    # Vorberechnung: Gauß-Gewichte für Blur
    gewichte = gauß_gewichte(params.blur_radius)
    # Rohes Licht-Buffer (nur Intensität)
    raw = [[0.0 for _ in range(breite)] for __ in range(höhe)]
    # Für jeden Pixel: Raymarching vom Boden zum Licht (vereinfacht)
    for y in range(höhe):
        for x in range(breite):
            # Weltkoordinaten des Pixels (Boden)
            px, py = float(x), float(y)
            # Schattenfaktor vom Licht zu diesem Punkt
            shadow = schattenfaktor_für_punkt(px, py, lx, ly, params.light_radius, bäume, params)
            # Distanz zum Licht
            dx, dy = lx - px, ly - py
            dist = math.hypot(dx, dy)
            if dist < 0.01:
                dist = 0.01
            # Falloff
            falloff = 1.0 / (1.0 + (dist * params.falloff_start) ** params.falloff_exponent)
            # Volumetrisches Streulicht (einfaches Raymarching entlang der Blickrichtung?)
            # Wir approximieren: Streulicht proportional zu Schatten * Falloff * Mist-Dichte
            mist = params.mist_density * math.exp(-py * params.mist_height_falloff / höhe)
            volumetric = shadow * falloff * mist * params.volumetric_gain
            # Spekularer Glanz auf dem Boden (Noise-basiert)
            spec = 0.0
            if params.specular_intensity > 0:
                n = noise_2d(px * params.specular_noise_scale, py * params.specular_noise_scale, params.noise_seed)
                spec = max(0.0, n) ** params.specular_power * params.specular_intensity
            # Gesamtintensität
            intensity = params.ambient + volumetric + spec
            raw[y][x] = intensity
    # Blur horizontal + vertikal für weiche Lichtkegel
    blurred = box_blur_1d(raw, gewichte, True)
    blurred = box_blur_1d(blurred, gewichte, False)
    # Gamma-Korrektur und ASCII-Umwandlung
    frame = []
    for y in range(höhe):
        line = []
        for x in range(breite):
            val = blurred[y][x]
            # Farbkanäle getrennt? Wir nutzen nur Intensität für ASCII.
            ch = intensitaet_zu_ascii(val, params.gamma)
            line.append(ch)
        frame.append(''.join(line))
    return frame

def main():
    params = ShaderParams()
    breite, höhe = 80, 40
    bäume, light_pos, z_buffer = erstelle_szene(params, breite, höhe)
    frame_count = 0
    start_time = time.time()
    print("3D-Lichtspiel – Drücke Enter für nächsten Frame, 'q' zum Beenden.")
    try:
        while True:
            # Eingabe prüfen (non-blocking)
            ready, _, _ = select.select([sys.stdin], [], [], 0.0)
            if ready:
                line = sys.stdin.readline()
                if not line:
                    break
                cmd = _norm(line)
                if cmd in ('q', 'quit', 'exit'):
                    break
                # Einfache Parameteränderungen
                if cmd.startswith('r'):  # Radius
                    try:
                        val = float(cmd.split()[1])
                        params.light_radius = max(0.1, min(5.0, val))
                    except:
                        pass
                elif cmd.startswith('m'):  # March steps
                    try:
                        val = int(cmd.split()[1])
                        params.march_steps = max(4, min(64, val))
                    except:
                        pass
                elif cmd.startswith('s'):  # Seed
                    try:
                        val = int(cmd.split()[1])
                        params.noise_seed = val
                        bäume, light_pos, z_buffer = erstelle_szene(params, breite, höhe)
                    except:
                        pass
            # Frame rendern
            frame_start = time.time()
            frame = render_frame(params, breite, höhe, bäume, light_pos, z_buffer)
            frame_time = (time.time() - frame_start) * 1000
            # Ausgabe
            sys.stdout.write('\033[H\033[J')  # Clear screen
            for line in frame:
                print(line)
            print(f"Frame: {frame_count}  Zeit: {frame_time:.1f}ms  Licht: ({light_pos[0]:.1f},{light_pos[1]:.1f})")
            sys.stdout.flush()
            frame_count += 1
            # Begrenzen auf 30 Frames für Test
            if frame_count >= 30:
                break
    except EOFError:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        print("\nBis bald im herbstlichen Park!")

if __name__ == "__main__":
    main()