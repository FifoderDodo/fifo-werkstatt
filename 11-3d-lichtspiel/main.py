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
                dist_center = math.sqrt((dx - proj * ux) ** 2 + (dy - proj * uy) ** 2)
                if dist_center < br:
                    # Penumbra: weicher Übergang am Baumrand
                    penumbra = params.penumbra_breite * proj
                    if dist_center < br - penumbra:
                        return params.umbra_dunkelheit
                    elif dist_center < br + penumbra:
                        t = (dist_center - (br - penumbra)) / (2 * penumbra)
                        min_f = min(min_f, params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * t)
    return min_f

def render_frame(params, light_pos, baeume, width=80, height=40):
    """Rendert einen Frame als ASCII-Karte."""
    # Kamera: schaut von oben leicht schräg auf die Szene
    cam_x, cam_y, cam_z = 0.0, -8.0, 4.0
    fov = 1.2
    
    # Lichtfarbe
    lr, lg, lb = kelvin_to_rgb_factor(params.color_temp)
    
    frame = []
    for y in range(height):
        zeile = []
        for x in range(width):
            # Normalisierte Koordinaten -1..1
            nx = (x - width * 0.5) / (width * 0.5) * fov
            ny = (y - height * 0.5) / (height * 0.5) * fov * (height / width)
            
            # Ray direction
            rx, ry, rz = nx, ny, -1.0
            rlen = math.sqrt(rx*rx + ry*ry + rz*rz)
            rx, ry, rz = rx/rlen, ry/rlen, rz/rlen
            
            # Raymarching für volumetrisches Licht
            steps = params.march_steps
            max_dist = 15.0
            step_size = max_dist / steps
            
            acc_r = acc_g = acc_b = 0.0
            transmittance = 1.0
            
            for s in range(steps):
                t = (s + 0.5) * step_size
                px = cam_x + rx * t
                py = cam_y + ry * t
                pz = cam_z + rz * t
                
                if pz < 0:
                    continue
                
                # Distanz zum Licht
                ldx = light_pos[0] - px
                ldy = light_pos[1] - py
                ldz = light_pos[2] - pz
                ldist = math.sqrt(ldx*ldx + ldy*ldy + ldz*ldz)
                
                if ldist < 0.1:
                    continue
                
                # Schattenfaktor
                shadow = schattenfaktor_3d((px, py, pz), light_pos, baeume, params)
                
                # Nebeldichte
                density = mist_dichte((px, py, pz), params)
                if density < 1e-4:
                    continue
                
                # Phase function (Henyey-Greenstein)
                cos_theta = (rx * ldx + ry * ldy + rz * ldz) / ldist
                phase = henyey_greenstein(cos_theta, params.phase_g)
                
                # Falloff
                falloff = 1.0 / (1.0 + (ldist - params.falloff_start) ** params.falloff_exponent)
                
                # Scattering
                scatter = density * params.scattering_coeff * phase * falloff * shadow
                absorption = density * params.absorption_coeff
                
                # Volumetric gain
                scatter *= params.volumetric_gain
                
                # Accumulate mit Transmittanz
                acc_r += transmittance * scatter * lr
                acc_g += transmittance * scatter * lg
                acc_b += transmittance * scatter * lb
                
                transmittance *= math.exp(-absorption * step_size)
                if transmittance < params.early_exit_threshold:
                    break
            
            # Ambient
            acc_r += params.ambient * lr
            acc_g += params.ambient * lg
            acc_b += params.ambient * lb
            
            # Vibrancy & Gamma
            def apply(v):
                v = min(1.0, v * params.vibrancy)
                return v ** params.gamma
            
            acc_r = apply(acc_r)
            acc_g = apply(acc_g)
            acc_b = apply(acc_b)
            
            # Luminanz für ASCII
            lum = 0.2126 * acc_r + 0.7152 * acc_g + 0.0722 * acc_b
            zeile.append(intensitaet_zu_ascii(lum, params.gamma))
        frame.append(''.join(zeile))
    return frame

def main():
    params = ShaderParams()
    light_pos = [0.3, 0.0, 3.5]
    
    # Bäume: (x, y, radius, höhe)
    baeume = [
        (-3.0, -2.0, 0.8, 4.0),
        (2.5, -1.5, 0.6, 3.5),
        (-1.0, 1.0, 0.7, 3.8),
        (4.0, 2.0, 0.5, 3.0),
        (-4.0, 3.0, 0.9, 4.5),
        (0.0, -4.0, 0.6, 3.2),
    ]
    
    print("3D-Lichtspiel - Herbstlicher Park")
    print("==================================")
    print(f"Licht: {tuple(light_pos)} | Nebel: {params.mist_density} | Temp: {params.color_temp}K | Steps: {params.march_steps}")
    print("Befehle: w/a/s/d=Licht bewegen, q/e=Höhe, +/-=Nebel, r=Reset, x=Ende")
    print()
    
    while True:
        try:
            # Frame rendern
            frame = render_frame(params, light_pos, baeume, 80, 30)
            print('\n'.join(frame))
            print(f"\nLicht: ({light_pos[0]:.1f}, {light_pos[1]:.1f}, {light_pos[2]:.1f})  Nebel: {params.mist_density:.2f}")
            print("Befehl (h=Hilfe, x=Ende): ", end='', flush=True)
            
            cmd = input().strip().lower()
            if not cmd:
                continue
            if cmd == 'x':
                print("Tschüss!")
                break
            elif cmd == 'h':
                print("w/a/s/d: Licht XY  |  q/e: Licht Z  |  +/-: Nebeldichte  |  r: Reset  |  x: Ende")
            elif cmd == 'w':
                light_pos[1] += 0.3
            elif cmd == 's':
                light_pos[1] -= 0.3
            elif cmd == 'a':
                light_pos[0] -= 0.3
            elif cmd == 'd':
                light_pos[0] += 0.3
            elif cmd == 'q':
                light_pos[2] = max(0.5, light_pos[2] - 0.3)
            elif cmd == 'e':
                light_pos[2] += 0.3
            elif cmd == '+':
                params.mist_density = min(1.0, params.mist_density + 0.05)
            elif cmd == '-':
                params.mist_density = max(0.0, params.mist_density - 0.05)
            elif cmd == 'r':
                params = ShaderParams()
                light_pos = [0.3, 0.0, 3.5]
            else:
                print(f"Unbekannt: {cmd}")
        except EOFError:
            print("\nEOF - Tschüss!")
            break
        except KeyboardInterrupt:
            print("\nAbbruch - Tschüss!")
            break

if __name__ == "__main__":
    main()