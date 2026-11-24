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
        self.bloom_threshold = 0.6
        self.bloom_intensity = 0.45
        self.bloom_radius = 2
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
                # Abstand des Strahls zum Baummittelpunkt in XY
                perp_sq = dx*dx + dy*dy - proj*proj
                if perp_sq < 0:
                    perp_sq = 0
                d_perp = math.sqrt(perp_sq)
                if d_perp < br:
                    # innerhalb des Stamms -> voller Schatten mit Penumbra
                    # Penumbra-Breite als Anteil des Radius
                    penumbra = params.penumbra_breite * br
                    if d_perp < br - penumbra:
                        f = params.umbra_dunkelheit
                    else:
                        t = (d_perp - (br - penumbra)) / penumbra
                        f = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * t
                    min_f = min(min_f, f)
                elif d_perp < br + params.penumbra_breite * br:
                    # Penumbra-Bereich
                    t = (d_perp - br) / (params.penumbra_breite * br)
                    f = 1.0 - (1.0 - params.umbra_dunkelheit) * (1.0 - t)
                    min_f = min(min_f, f)
    return min_f

def render_frame(params, baeume, light_pos, cam_pos, cam_dir, cam_up, fov, width, height):
    """Rendert ein Frame mit Ray-Marching und gibt 2D-Liste von Intensitäten zurück."""
    # Vorberechnungen
    aspect = width / height
    half_fov = math.tan(fov * 0.5)
    right = (cam_dir[1]*cam_up[2] - cam_dir[2]*cam_up[1],
             cam_dir[2]*cam_up[0] - cam_dir[0]*cam_up[2],
             cam_dir[0]*cam_up[1] - cam_dir[1]*cam_up[0])
    rlen = math.sqrt(right[0]**2 + right[1]**2 + right[2]**2)
    if rlen > 0:
        right = (right[0]/rlen, right[1]/rlen, right[2]/rlen)
    up = (cam_dir[1]*right[2] - cam_dir[2]*right[1],
          cam_dir[2]*right[0] - cam_dir[0]*right[2],
          cam_dir[0]*right[1] - cam_dir[1]*right[0])
    
    # Lichtfarbe
    light_color = kelvin_to_rgb_factor(params.color_temp)
    extinction = params.scattering_coeff + params.absorption_coeff
    
    bild = [[0.0 for _ in range(width)] for __ in range(height)]
    
    for y in range(height):
        for x in range(width):
            # Pixel-Koordinaten [-1,1]
            px_ndc = (x + 0.5) / width * 2.0 - 1.0
            py_ndc = (y + 0.5) / height * 2.0 - 1.0
            # Strahlrichtung
            dir_x = cam_dir[0] + right[0] * px_ndc * half_fov * aspect + up[0] * py_ndc * half_fov
            dir_y = cam_dir[1] + right[1] * px_ndc * half_fov * aspect + up[1] * py_ndc * half_fov
            dir_z = cam_dir[2] + right[2] * px_ndc * half_fov * aspect + up[2] * py_ndc * half_fov
            dlen = math.sqrt(dir_x*dir_x + dir_y*dir_y + dir_z*dir_z)
            if dlen == 0:
                continue
            rdx, rdy, rdz = dir_x/dlen, dir_y/dlen, dir_z/dlen
            
            # Jitter für temporales AA / Rauschen
            jitter = 0.0
            if params.jitter_enabled:
                jitter = (random.random() - 0.5) * params.jitter_strength
            
            # Ray Marching
            max_dist = 30.0
            steps = params.march_steps
            if params.adaptive_steps:
                steps = int(steps * params.max_step_factor)
            step_size = max_dist / steps
            
            radiance = 0.0
            transmittance = 1.0
            
            for s in range(steps):
                t = (s + 0.5 + jitter) * step_size
                px_w = cam_pos[0] + rdx * t
                py_w = cam_pos[1] + rdy * t
                pz_w = cam_pos[2] + rdz * t
                
                # Dichte an dieser Stelle
                density = mist_dichte((px_w, py_w, pz_w), params)
                if density < 1e-4:
                    continue
                
                # Lichtrichtung
                lx, ly, lz = light_pos
                vx, vy, vz = lx - px_w, ly - py_w, lz - pz_w
                dist_light = math.sqrt(vx*vx + vy*vy + vz*vz)
                if dist_light < 0.01:
                    continue
                ldx, ldy, ldz = vx/dist_light, vy/dist_light, vz/dist_light
                
                # Schattenfaktor
                shadow = schattenfaktor_3d((px_w, py_w, pz_w), light_pos, baeume, params)
                
                # Phasenfunktion
                cos_theta = rdx*ldx + rdy*ldy + rdz*ldz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                
                # Lichtabfall (inverse square mit Falloff-Start)
                falloff = 1.0 / max(params.falloff_start, dist_light) ** params.falloff_exponent
                
                # Streulicht-Beitrag
                scatter = density * params.scattering_coeff * phase * shadow * falloff
                
                # Absorption entlang des Sichtstrahls (vereinfacht)
                # Wir akkumulieren Transparenz basierend auf Dichte * Absorption * Schrittweite
                transmittance *= math.exp(-density * params.absorption_coeff * step_size)
                
                radiance += scatter * transmittance * step_size
                
                # Early exit
                if transmittance < params.early_exit_threshold:
                    break
            
            # Ambient hinzufügen
            radiance += params.ambient
            
            # Volumetric Gain
            radiance *= params.volumetric_gain
            
            # Farbtemperatur anwenden (einfache Multiplikation mit Luminanz)
            # Wir nutzen nur Luminanz für ASCII, aber für Farb-Konsistenz:
            lum = 0.2126*light_color[0] + 0.7152*light_color[1] + 0.0722*light_color[2]
            radiance *= lum
            
            # Vibrancy / Sättigung (hier nur Helligkeit)
            radiance = min(1.0, radiance * params.vibrancy)
            
            bild[y][x] = radiance
    
    # Bloom: separabler Gaussian Blur auf hellen Bereichen
    if params.bloom_radius > 0 and params.bloom_intensity > 0:
        # Threshold
        bloom_src = [[max(0.0, v - params.bloom_threshold) for v in row] for row in bild]
        gewichte = gauß_gewichte(params.bloom_radius)
        blur_h = box_blur_1d(bloom_src, gewichte, True)
        blur_v = box_blur_1d(blur_h, gewichte, False)
        for y in range(height):
            for x in range(width):
                bild[y][x] += blur_v[y][x] * params.bloom_intensity
    
    return bild

def main():
    params = ShaderParams()
    
    # Szene definieren
    baeume = [
        (-3.0, -2.0, 0.4, 4.0),
        (2.5, -1.5, 0.3, 3.5),
        (-1.0, 3.0, 0.5, 5.0),
        (4.0, 2.0, 0.35, 4.2),
        (-4.0, 1.0, 0.45, 3.8),
        (0.0, -4.0, 0.4, 4.5),
    ]
    light_pos = (0.0, -5.0, 6.0)
    cam_pos = (0.0, -12.0, 2.5)
    cam_target = (0.0, 0.0, 1.5)
    cam_dir = (cam_target[0]-cam_pos[0], cam_target[1]-cam_pos[1], cam_target[2]-cam_pos[2])
    clen = math.sqrt(cam_dir[0]**2 + cam_dir[1]**2 + cam_dir[2]**2)
    cam_dir = (cam_dir[0]/clen, cam_dir[1]/clen, cam_dir[2]/clen)
    cam_up = (0.0, 0.0, 1.0)
    fov = 1.0  # ~57 Grad
    width, height = 80, 40
    
    print("3D-Lichtspiel – Herbstlicher Park (Drücke Enter für neues Frame, 'q' zum Beenden)")
    
    frame = 0
    while True:
        try:
            cmd = input("> ").strip().lower()
            if cmd == 'q' or cmd == 'quit':
                break
            if cmd == 'r' or cmd == 'reset':
                params = ShaderParams()
                print("Parameter zurückgesetzt.")
                continue
            if cmd.startswith('seed'):
                parts = cmd.split()
                if len(parts) == 2:
                    try:
                        params.noise_seed = int(parts[1])
                        print(f"Seed gesetzt auf {params.noise_seed}")
                    except ValueError:
                        print("Ungültiger Seed.")
                continue
            if cmd == 'params':
                for k, v in params.__dict__.items():
                    print(f"  {k} = {v}")
                continue
        except EOFError:
            print("\nTschüss!")
            break
        except KeyboardInterrupt:
            print("\nTschüss!")
            break
        
        # Frame rendern
        start = time.time()
        bild = render_frame(params, baeume, light_pos, cam_pos, cam_dir, cam_up, fov, width, height)
        elapsed = time.time() - start
        
        # ASCII ausgeben
        for row in bild:
            line = ''.join(intensitaet_zu_ascii(v, params.gamma) for v in row)
            print(line)
        print(f"Frame {frame} | {elapsed*1000:.1f} ms | Seed {params.noise_seed}")
        frame += 1

if __name__ == "__main__":
    main()