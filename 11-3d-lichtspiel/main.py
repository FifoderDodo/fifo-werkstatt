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
        self.march_steps = 12  # reduziert für bessere Performance
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
    """Generiert Bäume und Lichtposition für den Park."""
    random.seed(params.noise_seed)
    bäume = []
    for _ in range(12):
        bx = random.uniform(5, breite - 5)
        by = random.uniform(5, höhe - 5)
        br = random.uniform(1.5, 3.0)
        bäume.append((bx, by, br))
    # Lichtquelle leicht versetzt oben mittig
    lx = breite * 0.5 + random.uniform(-3, 3)
    ly = höhe * 0.2 + random.uniform(-2, 2)
    return bäume, (lx, ly)

def raymarch_volumetric(px, py, lx, ly, bäume, params, breite, höhe):
    """Raymarching für volumetrisches Licht mit Henyey-Greenstein Phasenfunktion."""
    # Blickrichtung: von Pixel zur Kamera (vereinfacht: senkrecht zum Bildschirm)
    # Lichtrichtung: von Pixel zur Lichtquelle
    dx = lx - px
    dy = ly - py
    dist_to_light = math.hypot(dx, dy)
    if dist_to_light < 0.01:
        return 1.0
    
    ldx, ldy = dx / dist_to_light, dy / dist_to_light
    
    # Raymarching entlang des Blickstrahls (hier vereinfacht: entlang Lichtkegel)
    # Wir marschen von der Kamera zum Pixel und accumulieren Streulicht
    steps = params.march_steps
    step_size = dist_to_light / steps
    
    transmittance = 1.0
    in_scatter = 0.0
    
    # Jitter für temporales AA / Rauschen reduzieren
    jitter = 0.0
    if params.jitter_enabled:
        jitter = (noise_2d(px * 0.1, py * 0.1, params.noise_seed + int(time.time() * 1000) % 1000) * 0.5 + 0.5) * params.jitter_strength
    
    for i in range(steps):
        t = (i + jitter) * step_size
        sx = px + ldx * t
        sy = py + ldy * t
        
        # Höhe für Nebel-Falloff (y-Koordinate invertiert, 0 unten)
        height_factor = 1.0 - (sy / höhe) * params.mist_height_falloff
        height_factor = max(0.1, height_factor)
        
        # Mist-Dichte mit 3D-Noise für Volumenstruktur
        nz = noise_3d(sx * 0.05, sy * 0.05, t * 0.1, params.noise_seed) * 0.5 + 0.5
        local_density = params.mist_density * height_factor * (0.7 + 0.6 * nz)
        
        # Absorption
        sigma_a = params.absorption_coeff * local_density
        transmittance *= math.exp(-sigma_a * step_size)
        
        # Streuung (In-Scattering)
        sigma_s = params.scattering_coeff * local_density
        
        # Schattenfaktor an dieser Position
        shadow = schattenfaktor_für_punkt(sx, sy, lx, ly, params.light_radius, bäume, params)
        
        # Phasenfunktion: Winkel zwischen Blick- und Lichtrichtung
        # Vereinfacht: Blickrichtung ist (0,0,-1), Lichtrichtung ist (ldx, ldy, 0)
        # Für 2D-Projektion nutzen wir den Winkel im Bildschirmraum
        cos_theta = ldy  # Annahme: Blick von oben (negatives y)
        phase = henyey_greenstein(cos_theta, params.phase_g)
        
        # Falloff mit Distanz zur Lichtquelle
        dist_factor = 1.0 / (1.0 + (t * params.falloff_start) ** params.falloff_exponent)
        
        in_scatter += transmittance * sigma_s * phase * shadow * dist_factor * step_size
        
        if transmittance < 0.01:
            break
    
    # Direkte Beleuchtung (Punktlichtquelle mit Schatten)
    direct_shadow = schattenfaktor_für_punkt(px, py, lx, ly, params.light_radius, bäume, params)
    direct = direct_shadow * (1.0 / (1.0 + dist_to_light * 0.1) ** 2)
    
    # Spekulare Highlights auf "Nebelpartikeln"
    specular = 0.0
    if params.specular_intensity > 0:
        # Einfache Approximation: Glanz dort, wo Dichte und Winkel passen
        nz = noise_3d(px * params.specular_noise_scale, py * params.specular_noise_scale, 0, params.noise_seed + 1)
        if nz > 0.7:
            specular = params.specular_intensity * (nz - 0.7) / 0.3 * direct_shadow
    
    total = (in_scatter * params.volumetric_gain + direct + specular) * transmittance + params.ambient
    return min(1.0, total)

def render_frame(params, breite=80, höhe=40):
    """Rendert einen kompletten Frame."""
    bäume, (lx, ly) = erstelle_szene(params, breite, höhe)
    rohdaten = [[0.0 for _ in range(breite)] for __ in range(höhe)]
    
    for y in range(höhe):
        for x in range(breite):
            # Pixel-Koordinaten in Weltkoordinaten
            wx = x + 0.5
            wy = y + 0.5
            val = raymarch_volumetric(wx, wy, lx, ly, bäume, params, breite, höhe)
            rohdaten[y][x] = val
    
    # Gauss-Blur für weiche Lichtkegel
    gewichte = gauß_gewichte(params.blur_radius)
    blur_h = box_blur_1d(rohdaten, gewichte, horizontal=True)
    blur_v = box_blur_1d(blur_h, gewichte, horizontal=False)
    
    # Farbtemperatur anwenden (hier nur Intensität, ASCII ist monochrom)
    r_factor, g_factor, b_factor = kelvin_to_rgb_factor(params.color_temp)
    luminance_factor = 0.2126 * r_factor + 0.7152 * g_factor + 0.0722 * b_factor
    
    ascii_zeilen = []
    for y in range(höhe):
        zeile = ''
        for x in range(breite):
            val = blur_v[y][x] * luminance_factor
            zeile += intensitaet_zu_ascii(val, params.gamma)
        ascii_zeilen.append(zeile)
    
    return ascii_zeilen, bäume, (lx, ly)

def parameter_menü(params):
    """Interaktives Menü zur Parameter-Anpassung."""
    print("\n=== 3D-Lichtspiel: Parameter ===")
    print("1) penumbra_breite     ", params.penumbra_breite)
    print("2) umbra_dunkelheit    ", params.umbra_dunkelheit)
    print("3) falloff_exponent    ", params.falloff_exponent)
    print("4) falloff_start       ", params.falloff_start)
    print("5) blur_radius         ", params.blur_radius)
    print("6) ambient             ", params.ambient)
    print("7) volumetric_gain     ", params.volumetric_gain)
    print("8) gamma               ", params.gamma)
    print("9) scattering_coeff    ", params.scattering_coeff)
    print("10) absorption_coeff   ", params.absorption_coeff)
    print("11) mist_density       ", params.mist_density)
    print("12) mist_height_falloff", params.mist_height_falloff)
    print("13) color_temp (K)     ", params.color_temp)
    print("14) jitter_strength    ", params.jitter_strength)
    print("15) phase_g            ", params.phase_g)
    print("16) march_steps        ", params.march_steps)
    print("17) jitter_enabled     ", params.jitter_enabled)
    print("18) specular_intensity ", params.specular_intensity)
    print("19) specular_power     ", params.specular_power)
    print("20) light_radius       ", params.light_radius)
    print("Enter = weiter, 'q' = beenden")
    
    try:
        eingabe = input("Parameter-Nr oder Enter: ").strip()
    except EOFError:
        return False
    
    if not eingabe or _norm(eingabe) in ('q', 'quit', 'exit'):
        return False
    
    try:
        nr = int(eingabe)
        if 1 <= nr <= 20:
            try:
                neu = float(input("Neuer Wert: ").strip())
            except EOFError:
                return False
            
            attrs = [
                'penumbra_breite', 'umbra_dunkelheit', 'falloff_exponent',
                'falloff_start', 'blur_radius', 'ambient', 'volumetric_gain',
                'gamma', 'scattering_coeff', 'absorption_coeff', 'mist_density',
                'mist_height_falloff', 'color_temp', 'jitter_strength', 'phase_g',
                'march_steps', 'jitter_enabled', 'specular_intensity',
                'specular_power', 'light_radius'
            ]
            attr = attrs[nr - 1]
            if attr in ('blur_radius', 'march_steps', 'jitter_enabled'):
                if attr == 'jitter_enabled':
                    neu = bool(int(neu))
                else:
                    neu = int(neu)
            setattr(params, attr, neu)
            print(f"{attr} = {neu}")
        else:
            print("Ungültige Nummer.")
    except ValueError:
        print("Bitte Zahl eingeben.")
    return True

def main():
    params = ShaderParams()
    breite, höhe = 80, 40
    
    print("3D-Lichtspiel - Volumetrisches Licht im herbstlichen Park")
    print("Drücke Enter für neues Frame, 'p' für Parameter, 'q' zum Beenden.")
    
    while True:
        try:
            start = time.time()
            frame, bäume, (lx, ly) = render_frame(params, breite, höhe)
            elapsed = time.time() - start
            
            # Frame ausgeben
            print("\x1b[2J\x1b[H", end='')  # Clear screen
            for zeile in frame:
                print(zeile)
            print(f"\nRenderzeit: {elapsed*1000:.1f}ms | Steps: {params.march_steps} | Light: ({lx:.1f},{ly:.1f}) | Trees: {len(bäume)}")
            print("[Enter] Neu  [p] Parameter  [q] Quit")
            
            eingabe = input().strip().lower()
            if eingabe == 'q':
                break
            elif eingabe == 'p':
                if not parameter_menü(params):
                    break
            # Enter = nächster Frame (mit neuem Jitter)
        except EOFError:
            break
        except KeyboardInterrupt:
            break
    
    print("\nTschüss! Der Dodo watschelt davon. 🦤")

if __name__ == '__main__':
    main()