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
                    if faktor < min_f:
                        min_f = faktor
    return min_f

def raymarch(origin, direction, light_pos, baeume, params):
    """Einfaches Volumen-Raymarching mit Schatten und Phasenfunktion."""
    steps = params.march_steps
    step_len = 0.5
    transmittance = 1.0
    radiance = 0.0
    pos = list(origin)
    dir_norm = math.sqrt(direction[0]**2 + direction[1]**2 + direction[2]**2)
    dx, dy, dz = direction[0]/dir_norm, direction[1]/dir_norm, direction[2]/dir_norm
    
    for i in range(steps):
        # Jitter für weichere Kanten
        if params.jitter_enabled:
            jitter = (random.random() - 0.5) * params.jitter_strength * step_len
        else:
            jitter = 0.0
        
        pos[0] += dx * step_len
        pos[1] += dy * step_len
        pos[2] += dz * step_len
        
        density = mist_dichte(pos, params)
        if density <= 0.0:
            continue
        
        # Schattenfaktor an dieser Position
        shadow = schattenfaktor_3d(pos, light_pos, baeume, params)
        
        # Lichtvektor von Probe zur Lichtquelle
        lx, ly, lz = light_pos
        vx, vy, vz = lx - pos[0], ly - pos[1], lz - pos[2]
        dist_light = math.sqrt(vx*vx + vy*vy + vz*vz)
        if dist_light < 1e-4:
            continue
        lx, ly, lz = vx/dist_light, vy/dist_light, vz/dist_light
        
        # Phasenfunktion (Henyey-Greenstein)
        cos_theta = dx*lx + dy*ly + dz*lz
        phase = henyey_greenstein(cos_theta, params.phase_g)
        
        # Falloff
        falloff = 1.0 / max(1e-4, dist_light**params.falloff_exponent)
        if dist_light < params.falloff_start:
            falloff *= (dist_light / params.falloff_start)
        
        # Absorption und Scattering
        extinction = (params.scattering_coeff + params.absorption_coeff) * density * step_len
        transmittance *= math.exp(-extinction)
        
        scatter = params.scattering_coeff * density * phase * falloff * shadow * step_len
        radiance += transmittance * scatter * params.volumetric_gain
        
        if transmittance < 0.01:
            break
    
    # Ambient und Depth-Shading-Wrap
    radiance += params.ambient * (1.0 - transmittance)
    wrap = params.depth_shading_wrap
    radiance = radiance * (1.0 + wrap) / (radiance + wrap)
    
    # Farbtemperatur anwenden
    r_mult, g_mult, b_mult = kelvin_to_rgb_factor(params.color_temp)
    radiance_r = radiance * r_mult
    radiance_g = radiance * g_mult
    radiance_b = radiance * b_mult
    
    # Vibrancy
    avg = (radiance_r + radiance_g + radiance_b) / 3.0
    radiance_r = avg + (radiance_r - avg) * params.vibrancy
    radiance_g = avg + (radiance_g - avg) * params.vibrancy
    radiance_b = avg + (radiance_b - avg) * params.vibrancy
    
    return (radiance_r, radiance_g, radiance_b)

def render_frame(params, width=80, height=40):
    """Rendert einen Frame in ASCII."""
    # Szene definieren
    light_pos = (0.0, 0.0, 5.0)
    baeume = [
        (-3.0, -2.0, 0.8, 4.0),
        (2.5, 1.5, 0.6, 3.5),
        (-1.0, 3.0, 0.7, 3.0),
        (4.0, -3.0, 0.9, 4.5),
    ]
    
    # Kamera: Blickrichtung -Z, Bildschirm in XY-Ebene
    frame = []
    aspect = width / height
    fov = 1.2
    
    for y in range(height):
        row = []
        sy = (y / height - 0.5) * fov
        for x in range(width):
            sx = (x / width - 0.5) * fov * aspect
            # Ray direction
            dir_vec = (sx, sy, -1.0)
            origin = (0.0, 0.0, 6.0)
            r, g, b = raymarch(origin, dir_vec, light_pos, baeume, params)
            # Luminanz für ASCII
            lum = 0.2126*r + 0.7152*g + 0.0722*b
            row.append(intensitaet_zu_ascii(lum, params.gamma))
        frame.append(''.join(row))
    return frame

def main():
    params = ShaderParams()
    print("3D-Lichtspiel – Interaktiver Simulator (Teil 60)")
    print("Befehle: [enter]=neu rendern, q=quit, p=Parameter ändern")
    
    while True:
        try:
            frame = render_frame(params)
            print('\n'.join(frame))
            print("---")
            cmd = input("> ").strip().lower()
            if cmd == 'q':
                break
            elif cmd == 'p':
                print("Verfügbare Parameter:")
                for k, v in params.__dict__.items():
                    print(f"  {k} = {v}")
                name = input("Parameter name: ").strip()
                if name in params.__dict__:
                    val = float(input(f"Neuer Wert für {name}: "))
                    params.__dict__[name] = val
                    print(f"{name} = {val}")
                else:
                    print("Unbekannter Parameter.")
            # sonst einfach neu rendern
        except EOFError:
            print("\nEOF – Tschüss!")
            break
        except KeyboardInterrupt:
            print("\nAbbruch – Tschüss!")
            break
        except Exception as e:
            print(f"Fehler: {e}")
            break

if __name__ == "__main__":
    main()