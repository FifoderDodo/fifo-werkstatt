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
        self.light_radius = 0.8  # Radius der Lichtquelle für echte Penumbra
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
    """
    Berechnet Schattenfaktor für Punkt (px, py) von Lichtquelle (qx, qy) mit Radius light_radius.
    Berücksichtigt echte Umbra/Penumbra-Geometrie durch Flächenlichtquelle.
    """
    dx, dy = px - qx, py - qy
    dist_lp = math.hypot(dx, dy)  # Abstand Licht -> Punkt
    if dist_lp < 0.01:
        return 1.0
    
    ux, uy = dx / dist_lp, dy / dist_lp
    min_faktor = 1.0
    
    for bx, by, br in bäume:
        vx, vy = bx - qx, by - qy
        dist_lt = math.hypot(vx, vy)  # Abstand Licht -> Baum
        if dist_lt < 0.01:
            continue
        
        proj = vx * ux + vy * uy  # Projektion Baum auf Licht->Punkt
        if proj <= 0.01 or proj >= dist_lp:
            continue  # Baum nicht zwischen Licht und Punkt
        
        abstand = abs(vx * uy - vy * ux)  # Seitlicher Abstand zum Strahl
        
        # Geometrie: Ähnliche Dreiecke für Flächenlichtquelle
        # Penumbra-Außenradius am Punkt:
        # R_penumbra = br * (dist_lp / dist_lt) + light_radius * (dist_lp - dist_lt) / dist_lt
        # Umbra-Innenradius (nur wenn light_radius < br):
        # R_umbra = max(0, br * (dist_lp / dist_lt) - light_radius * (dist_lp - dist_lt) / dist_lt)
        
        factor = dist_lp / dist_lt
        penumbra_radius = br * factor + light_radius * (factor - 1.0)
        umbra_radius = max(0.0, br * factor - light_radius * (factor - 1.0))
        
        if abstand >= penumbra_radius:
            continue  # Kein Schatten
        
        if abstand <= umbra_radius:
            faktor = params.umbra_dunkelheit
        else:
            # Weicher Übergang in der Penumbra-Zone
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

def render(params: ShaderParams, bäume, licht_pos, width=60, height=18, frame=0):
    img = [[0.0 for _ in range(width)] for _ in range(height)]
    lx, ly, lz = licht_pos
    cam_x, cam_y, cam_z = 0.0, 0.0, 10.0
    world_w, world_h = 12.0, 12.0 * height / width
    max_dist = 18.0
    step_size = max_dist / max(1, params.march_steps)
    light_r, light_g, light_b = kelvin_to_rgb_factor(params.color_temp)
    
    # Jitter für Temporal Stability / Dithering
    jitter_x = noise_2d(frame * 0.1, 0.0, params.noise_seed) * params.jitter_strength if params.jitter_enabled else 0.0
    jitter_y = noise_2d(0.0, frame * 0.1, params.noise_seed) * params.jitter_strength if params.jitter_enabled else 0.0

    for y in range(height):
        sy = (y / height - 0.5) * world_h + jitter_y
        for x in range(width):
            sx = (x / width - 0.5) * world_w + jitter_x
            
            # Ray Direction
            rdx, rdy, rdz = sx - cam_x, sy - cam_y, -cam_z
            rd_len = math.hypot(rdx, rdy, rdz)
            rdx, rdy, rdz = rdx / rd_len, rdy / rd_len, rdz / rd_len
            
            acc_r = acc_g = acc_b = 0.0
            transmittance = 1.0
            
            for step in range(params.march_steps):
                t = step * step_size
                px = cam_x + rdx * t
                py = cam_y + rdy * t
                pz = cam_z + rdz * t
                
                if pz <= 0.0:  # Boden getroffen
                    # Bodenbeitrag (Ambient + Schatten)
                    shadow = schattenfaktor_für_punkt(px, py, lx, ly, params.light_radius, bäume, params)
                    ground_col = params.ambient * shadow
                    acc_r += ground_col * light_r * transmittance
                    acc_g += ground_col * light_g * transmittance
                    acc_b += ground_col * light_b * transmittance
                    break
                
                # Volumetric Scattering
                # Lichtvektor vom Sample zur Lichtquelle
                ldx, ldy, ldz = lx - px, ly - py, lz - pz
                dist_light = math.hypot(ldx, ldy, ldz)
                if dist_light < 0.01:
                    continue
                ldx, ldy, ldz = ldx / dist_light, ldy / dist_light, ldz / dist_light
                
                # Phase Function
                cos_theta = rdx * ldx + rdy * ldy + rdz * ldz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                
                # Shadow Factor für diesen Sample-Punkt
                shadow = schattenfaktor_für_punkt(px, py, lx, ly, params.light_radius, bäume, params)
                
                # Falloff & Absorption
                falloff = 1.0 / max(0.01, dist_light ** params.falloff_exponent)
                mist = params.mist_density * math.exp(-pz * params.mist_height_falloff)
                density = (params.scattering_coeff + mist) * shadow
                absorption = params.absorption_coeff + mist * 0.5
                
                scatter = density * phase * falloff * transmittance
                
                acc_r += scatter * light_r * params.volumetric_gain
                acc_g += scatter * light_g * params.volumetric_gain
                acc_b += scatter * light_b * params.volumetric_gain
                
                transmittance *= math.exp(-absorption * step_size)
                if transmittance < 0.001:
                    break
            
            # Gamma & Tone Mapping
            def tonemap(c):
                c = max(0.0, c)
                return (c ** params.gamma) / (1.0 + c ** params.gamma)
            
            fr, fg, fb = tonemap(acc_r), tonemap(acc_g), tonemap(acc_b)
            luminance = 0.2126 * fr + 0.7152 * fg + 0.0722 * fb
            img[y][x] = luminance
    
    # Blur für weichere Kanten
    if params.blur_radius > 0:
        wts = gauß_gewichte(params.blur_radius)
        img = box_blur_1d(img, wts, True)
        img = box_blur_1d(img, wts, False)
    
    return img

def main():
    print("🦤 Fifo's 3D-Lichtspiel — Part 43: Dynamische Schattenränder")
    print("Drücke Enter für nächsten Frame, 'q' zum Beenden, 'p' für Parameter.")
    
    params = ShaderParams()
    bäume = [
        (-3.0, -2.0, 0.6),
        (2.5, 1.5, 0.5),
        (-1.0, 3.0, 0.7),
        (4.0, -3.0, 0.4),
        (-4.0, 2.0, 0.5),
        (0.0, -4.0, 0.8),
    ]
    licht_winkel = 0.0
    frame = 0
    
    while True:
        try:
            # Licht animieren
            licht_winkel += 0.03
            lx = math.sin(licht_winkel) * 5.0
            ly = math.cos(licht_winkel) * 5.0
            lz = 4.0 + math.sin(licht_winkel * 0.7) * 1.5
            
            img = render(params, bäume, (lx, ly, lz), frame=frame)
            
            # Ausgabe
            print(f"\n--- Frame {frame} | Licht: ({lx:.1f}, {ly:.1f}, {lz:.1f}) ---")
            for row in img:
                line = ''.join(intensitaet_zu_ascii(v, params.gamma) for v in row)
                print(line)
            
            frame += 1
            
            # Input non-blocking check
            print("[Enter=Weiter, q=Quit, p=Params] ", end='', flush=True)
            rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
            if rlist:
                inp = sys.stdin.readline()
                if not inp:
                    break
                inp = _norm(inp)
                if inp == 'q':
                    break
                elif inp == 'p':
                    print(f"\nParams: gain={params.volumetric_gain}, mist={params.mist_density}, steps={params.march_steps}, light_r={params.light_radius}")
                    print("Neue Werte: gain mist steps light_r (Enter zum Überspringen)")
                    try:
                        line = sys.stdin.readline()
                        if line:
                            parts = line.split()
                            if len(parts) >= 4:
                                params.volumetric_gain = float(parts[0])
                                params.mist_density = float(parts[1])
                                params.march_steps = int(parts[2])
                                params.light_radius = float(parts[3])
                                print("Parameter aktualisiert.")
                    except:
                        print("Ungültige Eingabe.")
                # Enter oder anderes -> einfach weiter
        except EOFError:
            break
        except KeyboardInterrupt:
            break
    
    print("\n🦤 Fifo watschelt weg. Tschüss!")

if __name__ == "__main__":
    main()