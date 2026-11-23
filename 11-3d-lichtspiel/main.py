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
        self.march_steps = 24
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
        br = random.uniform(1.5, 3.0)
        bäume.append((bx, by, br))
    light_x = breite / 2.0
    light_y = höhe / 2.0
    z_buffer = [[0.0 for _ in range(breite)] for __ in range(höhe)]
    for y in range(höhe):
        for x in range(breite):
            z_buffer[y][x] = noise_2d(x * 0.1, y * 0.1, params.noise_seed) * 0.5
    return bäume, (light_x, light_y), z_buffer

def render_frame(params, bäume, light_pos, z_buffer, breite=80, höhe=40, frame_time=0.0):
    """Berechnet einen Frame mit volumetrischem Licht und Schatten."""
    lx, ly = light_pos
    # Light-Orbit für Animation
    orbit_radius = min(breite, höhe) * 0.35
    lx = breite / 2.0 + math.sin(frame_time * 0.7) * orbit_radius
    ly = höhe / 2.0 + math.cos(frame_time * 0.5) * orbit_radius
    light_pos = (lx, ly)
    
    # Direkte Beleuchtung pro Pixel
    direct = [[0.0 for _ in range(breite)] for __ in range(höhe)]
    for y in range(höhe):
        for x in range(breite):
            dx = x - lx
            dy = y - ly
            dist = math.hypot(dx, dy)
            if dist < 0.01:
                direct[y][x] = 1.0
                continue
            shadow = schattenfaktor_für_punkt(x, y, lx, ly, params.light_radius, bäume, params)
            falloff = 1.0 / (1.0 + (dist * params.falloff_start) ** params.falloff_exponent)
            direct[y][x] = falloff * shadow
    
    # Volumetrisches Streulicht (einfaches Raymarching entlang der Blickrichtung -z)
    vol = [[0.0 for _ in range(breite)] for __ in range(höhe)]
    for y in range(höhe):
        for x in range(breite):
            # Blickstrahl von Kamera (weit weg) zum Pixel (x,y,0)
            # Wir marschieren von der Kamera zum Pixel und accumulieren Streulicht
            # Vereinfacht: wir nehmen die direkte Beleuchtung am Pixel und streuen sie in der Nähe
            pass  # Wird unten durch Blur approximiert
    
    # Streulicht durch mehrfaches Blur der direkten Beleuchtung simulieren
    gewichte = gauß_gewichte(params.blur_radius)
    scatter = direct
    for _ in range(2):
        scatter = box_blur_1d(scatter, gewichte, True)
        scatter = box_blur_1d(scatter, gewichte, False)
    
    # Nebel-Rauschen hinzufügen
    for y in range(höhe):
        for x in range(breite):
            mist = noise_3d(x * 0.05, y * 0.05, frame_time * 0.2, params.noise_seed)
            mist = (mist + 1.0) * 0.5 * params.mist_density
            height_factor = 1.0 - (y / höhe) * params.mist_height_falloff
            scatter[y][x] += mist * height_factor
    
    # Kombinieren: direct + volumetric_gain * scatter
    combined = [[0.0 for _ in range(breite)] for __ in range(höhe)]
    for y in range(höhe):
        for x in range(breite):
            combined[y][x] = direct[y][x] + params.volumetric_gain * scatter[y][x]
            combined[y][x] = min(1.0, combined[y][x] + params.ambient)
    
    # Farbtemperatur anwenden (einfache Intensitäts-Modulation)
    r_factor, g_factor, b_factor = kelvin_to_rgb_factor(params.color_temp)
    # Wir nutzen nur die Grün-Komponente als Luminanz-Näherung für ASCII
    
    # Gamma-Korrektur und ASCII-Umsetzung
    ascii_frame = []
    for y in range(höhe):
        line = []
        for x in range(breite):
            val = combined[y][x] ** params.gamma
            line.append(intensitaet_zu_ascii(val, params.gamma))
        ascii_frame.append(''.join(line))
    return ascii_frame, light_pos

def main():
    print("Dodos 3D-Lichtspiel im herbstlichen Park startet...")
    params = ShaderParams()
    breite, höhe = 80, 40
    bäume, light_pos, z_buffer = erstelle_szene(params, breite, höhe)
    frame_time = 0.0
    max_frames = 120
    frame_count = 0
    
    # Nicht-blockierende Eingabe für Interaktion
    while frame_count < max_frames:
        # Prüfen auf Tastendruck (Timeout 0)
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if ready:
            try:
                key = sys.stdin.readline()
                if not key:
                    break
                key = _norm(key)
                if key in ('q', 'quit', 'exit'):
                    break
                elif key in ('h', 'help', '?'):
                    print("Tasten: q=quit, +=blur++, -=blur--, g=gamma+, G=gamma-")
                elif key == '+':
                    params.blur_radius = min(10, params.blur_radius + 1)
                elif key == '-':
                    params.blur_radius = max(0, params.blur_radius - 1)
                elif key == 'g':
                    params.gamma = min(1.5, params.gamma + 0.05)
                elif key == 'G':
                    params.gamma = max(0.1, params.gamma - 0.05)
            except EOFError:
                break
        
        frame, light_pos = render_frame(params, bäume, light_pos, z_buffer, breite, höhe, frame_time)
        # Bildschirm löschen und Frame zeichnen
        sys.stdout.write("\033[H\033[J")  # ANSI clear screen
        for line in frame:
            sys.stdout.write(line + "\n")
        sys.stdout.write(f"Frame {frame_count+1}/{max_frames} | Blur={params.blur_radius} Gamma={params.gamma:.2f} | Drücke 'q' zum Beenden\n")
        sys.stdout.flush()
        frame_time += 0.08
        frame_count += 1
        time.sleep(0.05)
    
    print("\nDodo watschelt davon. Tschüss!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbbruch – Dodo fliegt weg (so gut er kann).")
    except Exception as e:
        print(f"Fehler: {e}")
        sys.exit(1)