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
                # Distance from ray to tree center in XY plane
                rx = px + ux * proj
                ry = py + uy * proj
                dist_tree = math.sqrt((bx - rx)**2 + (by - ry)**2)
                if dist_tree < br:
                    return params.umbra_dunkelheit
                if dist_tree < br + params.penumbra_breite:
                    t = (dist_tree - br) / params.penumbra_breite
                    f = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * t
                    if f < min_f:
                        min_f = f
    return min_f

def render_frame(params, baeume, light_pos, cam_pos, cam_dir, cam_up, fov, width, height):
    """Ray-marching renderer für volumetrisches Licht."""
    # Precompute camera basis
    forward = cam_dir
    f_len = math.sqrt(forward[0]**2 + forward[1]**2 + forward[2]**2)
    forward = (forward[0]/f_len, forward[1]/f_len, forward[2]/f_len)
    right = (cam_up[1]*forward[2] - cam_up[2]*forward[1],
             cam_up[2]*forward[0] - cam_up[0]*forward[2],
             cam_up[0]*forward[1] - cam_up[1]*forward[0])
    r_len = math.sqrt(right[0]**2 + right[1]**2 + right[2]**2)
    right = (right[0]/r_len, right[1]/r_len, right[2]/r_len)
    up = (forward[1]*right[2] - forward[2]*right[1],
          forward[2]*right[0] - forward[0]*right[2],
          forward[0]*right[1] - forward[1]*right[0])
    
    aspect = width / height
    tan_half_fov = math.tan(fov * 0.5)
    
    frame = [[0.0 for _ in range(width)] for __ in range(height)]
    
    for y in range(height):
        for x in range(width):
            # Normalized device coordinates
            ndc_x = (x + 0.5) / width * 2.0 - 1.0
            ndc_y = 1.0 - (y + 0.5) / height * 2.0
            
            # Ray direction
            dir_x = forward[0] + right[0] * ndc_x * aspect * tan_half_fov + up[0] * ndc_y * tan_half_fov
            dir_y = forward[1] + right[1] * ndc_x * aspect * tan_half_fov + up[1] * ndc_y * tan_half_fov
            dir_z = forward[2] + right[2] * ndc_x * aspect * tan_half_fov + up[2] * ndc_y * tan_half_fov
            dir_len = math.sqrt(dir_x**2 + dir_y**2 + dir_z**2)
            dir_x, dir_y, dir_z = dir_x/dir_len, dir_y/dir_len, dir_z/dir_len
            
            # Ray marching
            step_count = params.march_steps
            if params.adaptive_steps:
                # Vary steps based on distance to light? Keep simple.
                pass
            
            # Jitter
            jitter = 0.0
            if params.jitter_enabled:
                jitter = (random.random() - 0.5) * params.jitter_strength
            
            accum = 0.0
            transmittance = 1.0
            
            # March from camera to some far plane
            max_dist = 30.0
            step_size = max_dist / step_count
            
            for i in range(step_count):
                t = (i + 0.5 + jitter) * step_size
                px = cam_pos[0] + dir_x * t
                py = cam_pos[1] + dir_y * t
                pz = cam_pos[2] + dir_z * t
                
                # Density at point
                density = mist_dichte((px, py, pz), params)
                if density <= 0.0:
                    continue
                
                # Light direction
                lx, ly, lz = light_pos
                vx, vy, vz = lx - px, ly - py, lz - pz
                dist_light = math.sqrt(vx*vx + vy*vy + vz*vz)
                if dist_light < 0.01:
                    continue
                light_dir = (vx/dist_light, vy/dist_light, vz/dist_light)
                
                # Shadow factor
                shadow = schattenfaktor_3d((px, py, pz), light_pos, baeume, params)
                
                # Phase function
                cos_theta = dir_x*light_dir[0] + dir_y*light_dir[1] + dir_z*light_dir[2]
                phase = henyey_greenstein(cos_theta, params.phase_g)
                
                # Falloff
                falloff = 1.0 / max(0.01, dist_light**params.falloff_exponent)
                
                # Scattering contribution
                scatter = density * params.scattering_coeff * phase * falloff * shadow
                
                # Absorption
                absorb = density * params.absorption_coeff
                transmittance *= math.exp(-absorb * step_size)
                
                accum += scatter * transmittance * step_size
                
                if transmittance < params.early_exit_threshold:
                    break
            
            # Add ambient
            accum += params.ambient
            
            # Volumetric gain
            accum *= params.volumetric_gain
            
            # Vibrancy (simple color boost)
            accum *= params.vibrancy
            
            frame[y][x] = accum
    
    return frame

def apply_bloom(frame, params):
    """Einfacher Bloom-Effekt: threshold, blur, add."""
    h, w = len(frame), len(frame[0])
    # Extract bright parts
    bright = [[max(0.0, frame[y][x] - params.bloom_threshold) for x in range(w)] for y in range(h)]
    # Blur
    gewichte = gauß_gewichte(params.bloom_radius)
    blur1 = box_blur_1d(bright, gewichte, True)
    blur2 = box_blur_1d(blur1, gewichte, False)
    # Add back
    for y in range(h):
        for x in range(w):
            frame[y][x] += blur2[y][x] * params.bloom_intensity
    return frame

def frame_to_ascii(frame, params):
    """Konvertiert Frame in ASCII-Art."""
    lines = []
    for row in frame:
        line = ''.join(intensitaet_zu_ascii(v, params.gamma) for v in row)
        lines.append(line)
    return '\n'.join(lines)

def main():
    print("3D-Lichtspiel – Herbstlicher Park (Drücke 'q' zum Beenden)")
    
    # Standardparameter
    params = ShaderParams()
    
    # Szene: Bäume als (x, y, radius, height)
    random.seed(12345)
    baeume = []
    for _ in range(15):
        bx = random.uniform(-10, 10)
        by = random.uniform(-10, 10)
        br = random.uniform(0.3, 0.8)
        bh = random.uniform(2.0, 5.0)
        baeume.append((bx, by, br, bh))
    
    # Lichtposition
    light_pos = (0.0, 0.0, 8.0)
    
    # Kamera
    cam_pos = (0.0, -15.0, 3.0)
    cam_dir = (0.0, 1.0, -0.2)
    cam_up = (0.0, 0.0, 1.0)
    fov = math.radians(60)
    width, height = 80, 40
    
    frame_count = 0
    
    while True:
        try:
            # Render
            start = time.time()
            frame = render_frame(params, baeume, light_pos, cam_pos, cam_dir, cam_up, fov, width, height)
            frame = apply_bloom(frame, params)
            ascii_art = frame_to_ascii(frame, params)
            elapsed = time.time() - start
            
            # Clear screen (ANSI)
            print('\033[2J\033[H', end='')
            print(ascii_art)
            print(f"\nFrame {frame_count} | {elapsed*1000:.1f}ms | Seed: {params.noise_seed} | Steps: {params.march_steps}")
            print("Befehle: q=quit, r=rerender, seed=<int>, params (zeigt Parameter), set <name> <wert>")
            
            cmd = input("> ").strip()
            if not cmd:
                continue
            cmd_norm = _norm(cmd)
            if cmd_norm == 'q':
                break
            elif cmd_norm == 'r':
                frame_count += 1
                continue
            elif cmd_norm.startswith('seed='):
                try:
                    val = int(cmd_norm.split('=')[1])
                    params.noise_seed = val
                    print(f"Noise seed gesetzt auf {val}")
                except:
                    print("Ungültiger Seed")
            elif cmd_norm == 'params':
                for k, v in sorted(params.__dict__.items()):
                    print(f"  {k}: {v}")
            elif cmd_norm.startswith('set '):
                parts = cmd_norm.split()
                if len(parts) == 3:
                    name, val_str = parts[1], parts[2]
                    if hasattr(params, name):
                        try:
                            # Try to convert to same type as current value
                            current = getattr(params, name)
                            if isinstance(current, int):
                                val = int(val_str)
                            elif isinstance(current, float):
                                val = float(val_str)
                            elif isinstance(current, bool):
                                val = val_str.lower() in ('true', '1', 'yes', 'on')
                            else:
                                val = val_str
                            setattr(params, name, val)
                            print(f"{name} = {val}")
                        except Exception as e:
                            print(f"Fehler beim Setzen: {e}")
                    else:
                        print(f"Unbekannter Parameter: {name}")
                else:
                    print("Usage: set <name> <wert>")
            else:
                print("Unbekannter Befehl")
            frame_count += 1
        except EOFError:
            print("\nEOF – Tschüss!")
            break
        except KeyboardInterrupt:
            print("\nAbbruch – Tschüss!")
            break
        except Exception as e:
            print(f"Fehler: {e}")
            import traceback
            traceback.print_exc()
            break
    print("Programm beendet.")

if __name__ == "__main__":
    main()