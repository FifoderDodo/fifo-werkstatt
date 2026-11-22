import math, sys, random, unicodedata, time, select

class ShaderParams:
    """Container für alle einstellbaren Shader-Parameter mit Defaults."""
    def __init__(self):
        self.penumbra_breite = 0.15
        self.umbra_dunkelheit = 0.05
        self.falloff_exponent = 2.0
        self.falloff_start = 0.5
        self.blur_radius = 3
        self.ambient = 0.02
        self.volumetric_gain = 1.2
        self.gamma = 0.6
        self.scattering_coeff = 0.35
        self.absorption_coeff = 0.12
        self.mist_density = 0.18
        self.mist_height_falloff = 0.8
        self.color_temp = 3200.0
        self.jitter_strength = 0.15
        self.phase_g = 0.6
        self.noise_seed = 42
        self.march_steps = 32
        self.jitter_enabled = True
        self.specular_intensity = 0.8
        self.specular_power = 32.0
        self.specular_noise_scale = 0.5
    def klonen(self):
        k = ShaderParams()
        k.__dict__.update(self.__dict__)
        return k

def _norm(s: str) -> str:
    return unicodedata.normalize('NFC', s).strip().lower()

def gauß_gewichte(kernel_radius: int) -> list:
    size = kernel_radius * 2 + 1
    gewicht = 1.0 / size
    return [gewicht] * size

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

def schattenfaktor_für_punkt(px, py, qx, qy, radius, bäume, params):
    dx, dy = px - qx, py - qy
    dist = math.hypot(dx, dy)
    if dist > radius or dist < 0.01:
        return 1.0
    ux, uy = dx / dist, dy / dist
    min_shadow = 1.0
    for bx, by, br in bäume:
        vx, vy = bx - qx, by - qy
        dqb = math.hypot(vx, vy)
        if dqb < 0.01:
            continue
        proj = vx * ux + vy * uy
        if proj <= 0.01 or proj >= dist:
            continue
        abstand = abs(vx * uy - vy * ux)
        if abstand >= br:
            continue
        shadow_radius = br * (dist / dqb)
        if shadow_radius <= 0:
            continue
        rand_faktor = abstand / shadow_radius
        pen, umb = params.penumbra_breite, params.umbra_dunkelheit
        if rand_faktor < 1.0 - pen:
            faktor = umb
        elif rand_faktor > 1.0 + pen:
            faktor = 1.0
        else:
            t = (rand_faktor - (1.0 - pen)) / (2.0 * pen)
            faktor = umb + (1.0 - umb) * t
        if faktor < min_shadow:
            min_shadow = faktor
    return min_shadow

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
    c000 = hash3d(ix, iy, iz)
    c100 = hash3d(ix + 1, iy, iz)
    c010 = hash3d(ix, iy + 1, iz)
    c110 = hash3d(ix + 1, iy + 1, iz)
    c001 = hash3d(ix, iy, iz + 1)
    c101 = hash3d(ix + 1, iy, iz + 1)
    c011 = hash3d(ix, iy + 1, iz + 1)
    c111 = hash3d(ix + 1, iy + 1, iz + 1)
    def lerp(a, b, t):
        return a + t * (b - a)
    c00 = lerp(c000, c100, fx)
    c01 = lerp(c001, c101, fx)
    c10 = lerp(c010, c110, fx)
    c11 = lerp(c011, c111, fx)
    c0 = lerp(c00, c10, fy)
    c1 = lerp(c01, c11, fy)
    return lerp(c0, c1, fz)

def render(params: ShaderParams, bäume, licht_pos, width=80, height=24, frame=0):
    """Ray‑March vom Kamerapunkt (0,0,10) auf die Ground‑Plane z=0.
    Gibt Liste von ASCII‑Zeilen zurück."""
    # Float-Puffer für Helligkeit
    img = [[0.0 for _ in range(width)] for _ in range(height)]
    lx, ly, lz = licht_pos
    # Kamera fix über dem Park
    cam_x, cam_y, cam_z = 0.0, 0.0, 10.0
    # View‑Plane: x,y in [-5,5] (World‑Units)
    world_w, world_h = 10.0, 10.0 * height / width
    max_dist = 15.0
    step_size = max_dist / max(1, params.march_steps)
    
    # Vorberechnung: Schattenkarte für Ground-Plane (einmal pro Frame)
    shadow_map = [[1.0 for _ in range(width)] for __ in range(height)]
    light_radius = 10.0  # Einflussradius des Lichts für Schatten
    for y in range(height):
        for x in range(width):
            wx = (x / width - 0.5) * world_w
            wy = (y / height - 0.5) * world_h
            shadow_map[y][x] = schattenfaktor_für_punkt(wx, wy, lx, ly, light_radius, bäume, params)
    
    for y in range(height):
        for x in range(width):
            # Pixel -> Weltkoordinaten auf Ground-Plane (z=0)
            wx = (x / width - 0.5) * world_w
            wy = (y / height - 0.5) * world_h
            # Strahl von Kamera durch (wx, wy, 0)
            dx = wx - cam_x
            dy = wy - cam_y
            dz = 0.0 - cam_z
            ray_len = math.hypot(dx, dy, dz)
            if ray_len == 0:
                continue
            rdx, rdy, rdz = dx / ray_len, dy / ray_len, dz / ray_len
            
            # Schattenfaktor an der Ground-Intersection (konstant entlang Strahl)
            shadow = shadow_map[y][x]
            
            accumulated = 0.0
            transmittance = 1.0
            for step in range(params.march_steps):
                t = (step + 0.5) * step_size
                if params.jitter_enabled:
                    t += (random.random() - 0.5) * step_size * params.jitter_strength
                sx = cam_x + rdx * t
                sy = cam_y + rdy * t
                sz = cam_z + rdz * t
                if sz <= 0:  # Ground erreicht
                    break
                # Mist-Dichte mit Höhenabfall
                density = params.mist_density * math.exp(-sz * params.mist_height_falloff)
                # Noise für organische Variation
                if params.jitter_enabled:
                    n = noise_3d(sx * params.specular_noise_scale,
                                 sy * params.specular_noise_scale,
                                 sz * params.specular_noise_scale,
                                 params.noise_seed + frame)
                    density *= 1.0 + 0.1 * n
                # Lichtrichtung von Sample zu Lichtquelle
                ldx = lx - sx
                ldy = ly - sy
                ldz = lz - sz
                light_dist = math.hypot(ldx, ldy, ldz)
                if light_dist > 0:
                    ldx /= light_dist
                    ldy /= light_dist
                    ldz /= light_dist
                # Phase-Funktion (Henyey-Greenstein)
                cos_theta = rdx * ldx + rdy * ldy + rdz * ldz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                # Scattering-Beitrag
                scatter = density * phase * params.scattering_coeff * shadow
                # Absorption entlang des Sichtstrahls
                transmittance *= math.exp(-density * params.absorption_coeff * step_size)
                accumulated += scatter * transmittance
            
            # Ambient und Gain
            val = (accumulated * params.volumetric_gain + params.ambient) * shadow
            img[y][x] = val
    
    # Box-Blur (horizontal + vertikal)
    if params.blur_radius > 0:
        gewichte = gauß_gewichte(params.blur_radius)
        img = box_blur_1d(img, gewichte, horizontal=True)
        img = box_blur_1d(img, gewichte, horizontal=False)
    
    # ASCII-Konvertierung
    ascii_lines = []
    for y in range(height):
        line = ''.join(intensitaet_zu_ascii(img[y][x], params.gamma) for x in range(width))
        ascii_lines.append(line)
    return ascii_lines


def main():
    params = ShaderParams()
    # Beispiel-Bäume: (x, y, radius)
    bäume = [
        (-3.0, -2.0, 0.6),
        (2.5, 1.5, 0.5),
        (-1.0, 3.0, 0.7),
        (4.0, -3.0, 0.4),
        (-4.0, 0.0, 0.5),
    ]
    frame = 0
    print("3D-Lichtspiel – interaktiver volumetrischer Park (Strg+C oder EOF zum Beenden)")
    print("Gib Lichtposition als 'x y z' ein (z.B. '0 0 5'), Enter für Default.")
    while True:
        try:
            inp = input("Lichtposition> ").strip()
        except EOFError:
            print("\nTschüss! Der Dodo schläft weiter.")
            break
        if not inp:
            licht_pos = (0.0, 0.0, 5.0)
        else:
            parts = inp.split()
            if len(parts) != 3:
                print("Bitte drei Zahlen eingeben.")
                continue
            try:
                licht_pos = tuple(float(p) for p in parts)
            except ValueError:
                print("Ungültige Zahlen.")
                continue
        lines = render(params, bäume, licht_pos, frame=frame)
        for line in lines:
            print(line)
        frame += 1
        time.sleep(0.05)  # kleine Pause für Animation

if __name__ == "__main__":
    main()