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
                dist_achse = math.hypot(bx - cx, by - cy)
                ratio = proj / dist_light
                penumbra = br * ratio + params.light_radius * (1.0 - ratio) * 0.4
                if dist_achse < penumbra:
                    faktor = params.umbra_dunkelheit + (dist_achse / max(1e-4, penumbra)) * (1.0 - params.umbra_dunkelheit)
                    min_f = min(min_f, faktor)
    return min_f

def render_szene(params, width=64, height=28):
    # Herbstbäume im Park: (x, y, stamm_radius, hoehe)
    baeume = [
        (-2.2, 3.5, 0.45, 3.2),
        (0.4, 4.8, 0.60, 3.8),
        (2.6, 3.2, 0.40, 2.9),
        (-1.0, 6.0, 0.70, 4.2)
    ]
    light_pos = (2.2, 2.0, 3.5)
    cam_pos = (0.0, -2.0, 1.2)
    puffer = [[0.0 for _ in range(width)] for _ in range(height)]
    depth_puffer = [[0.0 for _ in range(width)] for _ in range(height)]

    # Kelvin Farbtönung als Multiplikator
    rgb_factor = kelvin_to_rgb_factor(params.color_temp)
    warmth = (rgb_factor[0] * 0.5 + rgb_factor[1] * 0.35 + rgb_factor[2] * 0.15) * params.vibrancy

    t_start = 1.0
    t_end = 8.0
    step_size = (t_end - t_start) / params.march_steps

    for y in range(height):
        fy = (y / (height - 1) * 2.0 - 1.0) * 0.45
        for x in range(width):
            fx = (x / (width - 1) * 2.0 - 1.0) * 0.85
            ray_dir = (fx, 1.0, -fy)
            r_len = math.sqrt(ray_dir[0]**2 + ray_dir[1]**2 + ray_dir[2]**2)
            rd = (ray_dir[0] / r_len, ray_dir[1] / r_len, ray_dir[2] / r_len)

            akkum_licht = 0.0
            akkum_trans = 1.0
            gesamt_tiefe = 0.0

            for s in range(params.march_steps):
                offset = (random.random() * 0.5) if params.jitter_enabled else 0.5
                t = t_start + (s + offset * params.jitter_strength) * step_size
                pos = (
                    cam_pos[0] + rd[0] * t,
                    cam_pos[1] + rd[1] * t,
                    cam_pos[2] + rd[2] * t
                )
                dichte = mist_dichte(pos, params)
                if dichte > 0.001:
                    lx = light_pos[0] - pos[0]
                    ly = light_pos[1] - pos[1]
                    lz = light_pos[2] - pos[2]
                    dist_l = math.sqrt(lx * lx + ly * ly + lz * lz)
                    # Glatter Beleuchtungsvektor mit Depth-Smoothing gegen flache Bänder
                    l_dir = (lx / dist_l, ly / dist_l, lz / dist_l)
                    cos_theta = rd[0] * l_dir[0] + rd[1] * l_dir[1] + rd[2] * l_dir[2]
                    phase = henyey_greenstein(cos_theta, params.phase_g)

                    # Plastizität via geglättetem Normalen-Lichtvektor & Half-Lambert Wrap
                    normale = dichte_gradient(pos, params)
                    n_dot_l = normale[0] * l_dir[0] + normale[1] * l_dir[1] + normale[2] * l_dir[2]
                    diffuse_wrap = (n_dot_l + params.depth_shading_wrap) / (1.0 + params.depth_shading_wrap)
                    diffuse_plastik = max(0.05, diffuse_wrap)

                    # Sanftes Highlight / Glanz
                    h_vec = (l_dir[0] - rd[0], l_dir[1] - rd[1], l_dir[2] - rd[2])
                    h_len = math.hypot(math.hypot(h_vec[0], h_vec[1]), h_vec[2])
                    specular = 0.0
                    if h_len > 1e-4:
                        h_norm = (h_vec[0] / h_len, h_vec[1] / h_len, h_vec[2] / h_len)
                        n_dot_h = max(0.0, normale[0] * h_norm[0] + normale[1] * h_norm[1] + normale[2] * h_norm[2])
                        specular = (n_dot_h ** params.specular_power) * params.specular_intensity

                    schatten = schattenfaktor_3d(pos, light_pos, baeume, params)
                    dist_falloff = 1.0 / (1.0 + (dist_l / params.falloff_start) ** params.falloff_exponent)
                    
                    einfallend = (diffuse_plastik + specular) * dist_falloff * schatten * warmth
                    streuung = dichte * params.scattering_coeff * phase * einfallend
                    ausloeschung = math.exp(-dichte * (params.scattering_coeff + params.absorption_coeff) * step_size)
                    
                    akkum_licht += akkum_trans * streuung * step_size
                    akkum_trans *= ausloeschung
                    gesamt_tiefe += t * dichte * step_size
                    if akkum_trans < 0.02:
                        break
            
            endwert = akkum_licht * params.volumetric_gain + params.ambient
            puffer[y][x] = endwert
            depth_puffer[y][x] = gesamt_tiefe

    # Bildweichzeichnung gegen Pixelrauschen
    if params.blur_radius > 0:
        gewichte = gauß_gewichte(params.blur_radius)
        puffer = box_blur_1d(puffer, gewichte, horizontal=True)
        puffer = box_blur_1d(puffer, gewichte, horizontal=False)

    return puffer

def zeige_bild(puffer, params):
    zeilen = []
    for row in puffer:
        z = "".join(intensitaet_zu_ascii(v, params.gamma) for v in row)
        zeilen.append(z)
    return "\n".join(zeilen)

def main():
    params = ShaderParams()
    print("--- 3D-Lichtspiel: Plastische Park-Dämmerung ---")
    print("Rendering mit tiefengeglättetem Beleuchtungsvektor läuft...")
    
    start_z = time.time()
    puffer = render_szene(params, width=62, height=22)
    dauer = time.time() - start_z
    
    print(zeige_bild(puffer, params))
    print(f"\n[Renderzeit: {dauer:.2f}s | Gamma: {params.gamma} | Farbtemperatur: {params.color_temp:.0f}K]")
    
    # Kleines interaktives Einstellmenü
    optionen = [
        ("depth_shading_wrap", "Wrap-Faktor für Plastizität", float),
        ("mist_density", "Nebeldichte", float),
        ("volumetric_gain", "Volumetrischer Gain", float),
        ("specular_intensity", "Glanzlicht-Intensität", float),
        ("blur_radius", "Weichzeichnungs-Radius", int),
        ("gamma", "Gamma-Korrektur", float),
    ]
    
    eingaben_rest = 5
    while eingaben_rest > 0:
        print("\nParameter anpassen:")
        for i, (key, bez, _) in enumerate(optionen, 1):
            print(f" {i}. {bez} ({key} = {getattr(params, key)})")
        print(" 0. Neu rendern")
        print(" q. Beenden")
        
        try:
            auswahl = input("Auswahl > ").strip().lower()
        except EOFError:
            print("\nBeende Vorführung.")
            break
            
        if auswahl in ('q', 'exit', 'ende'):
            print("Auf Wiedersehen im herbstlichen Park!")
            break
        elif auswahl in ('0', 'r', 'rendern'):
            p = render_szene(params, width=62, height=22)
            print(zeige_bild(p, params))
            eingaben_rest -= 1
        else:
            try:
                idx = int(auswahl) - 1
                if 0 <= idx < len(optionen):
                    key, bez, cast_fn = optionen[idx]
                    neu_raw = input(f"Neuer Wert für {bez} [{getattr(params, key)}]: ")
                    setattr(params, key, cast_fn(neu_raw.strip()))
                    print(f"{bez} gesetzt auf: {getattr(params, key)}")
                    eingaben_rest -= 1
                else:
                    print("Ungültige Nummer.")
            except (ValueError, IndexError):
                print("Ungültige Eingabe.")

if __name__ == '__main__':
    main()