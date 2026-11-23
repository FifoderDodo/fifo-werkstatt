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
                    # Neue Light-Decay-Formel für weichere Penumbra und realistischere Tiefe
                    t = dist_achse / penumbra
                    shadow = 1.0 - (1.0 - t) ** 2.5  # Exponent 2.5 für weicheren Übergang
                    if shadow < min_f:
                        min_f = shadow
    return min_f

def raymarch(origin, direction, light_pos, baeume, params, width, height):
    """Volumetric ray marching mit Schatten und Streuung."""
    ox, oy, oz = origin
    dx, dy, dz = direction
    step_len = 0.3
    transmittance = 1.0
    radiance = 0.0
    for step in range(params.march_steps):
        px = ox + dx * step_len * step
        py = oy + dy * step_len * step
        pz = oz + dz * step_len * step
        if pz < 0.0:
            continue
        density = mist_dichte((px, py, pz), params)
        if density <= 0.0:
            continue
        # Schatten
        shadow = schattenfaktor_3d((px, py, pz), light_pos, baeume, params)
        # Phase function
        lx, ly, lz = light_pos
        vx, vy, vz = lx - px, ly - py, lz - pz
        dist_light = math.sqrt(vx*vx + vy*vy + vz*vz)
        if dist_light > 1e-3:
            ldx, ldy, ldz = vx/dist_light, vy/dist_light, vz/dist_light
            cos_theta = dx*ldx + dy*ldy + dz*ldz
            phase = henyey_greenstein(cos_theta, params.phase_g)
        else:
            phase = 1.0
        # Streuung
        scatter = density * params.scattering_coeff * phase * shadow
        # Absorption
        absorb = density * params.absorption_coeff
        transmittance *= math.exp(-absorb * step_len)
        radiance += scatter * transmittance * step_len
        if transmittance < 0.01:
            break
    return radiance * params.volumetric_gain

def render_frame(params, cam_x, cam_y, cam_z, cam_yaw, cam_pitch, light_pos, baeume, width=80, height=40):
    """Rendert einen Frame als ASCII-Bild."""
    # Kamera-Richtungen
    cos_yaw = math.cos(cam_yaw)
    sin_yaw = math.sin(cam_yaw)
    cos_pitch = math.cos(cam_pitch)
    sin_pitch = math.sin(cam_pitch)
    # Farbtemperatur
    cr, cg, cb = kelvin_to_rgb_factor(params.color_temp)
    # Jitter
    jitter = params.jitter_strength if params.jitter_enabled else 0.0
    # Framebuffer für Helligkeit
    fb = [[0.0 for _ in range(width)] for __ in range(height)]
    for y in range(height):
        for x in range(width):
            # NDC -> View Ray
            nx = (x + 0.5) / width * 2.0 - 1.0
            ny = (y + 0.5) / height * 2.0 - 1.0
            # Perspektive
            fx = nx * 1.2
            fy = ny * 1.2
            fz = 1.0
            # Kamerarotation anwenden
            # Yaw
            rx = fx * cos_yaw - fz * sin_yaw
            rz = fx * sin_yaw + fz * cos_yaw
            # Pitch
            ry = fy * cos_pitch - rz * sin_pitch
            rz = fy * sin_pitch + rz * cos_pitch
            # Normalisieren
            length = math.sqrt(rx*rx + ry*ry + rz*rz)
            if length == 0:
                continue
            rx, ry, rz = rx/length, ry/length, rz/length
            # Jitter
            if jitter > 0:
                rx += (random.random()-0.5)*jitter
                ry += (random.random()-0.5)*jitter
                rz += (random.random()-0.5)*jitter
            # Raymarch
            val = raymarch((cam_x, cam_y, cam_z), (rx, ry, rz), light_pos, baeume, params, width, height)
            # Ambient + Specular Highlights (vereinfacht)
            val += params.ambient
            fb[y][x] = val
    # Blur
    if params.blur_radius > 0:
        w = gauß_gewichte(params.blur_radius)
        fb = box_blur_1d(fb, w, True)
        fb = box_blur_1d(fb, w, False)
    # Gamma & Vibrancy
    for y in range(height):
        for x in range(width):
            v = fb[y][x]
            v = min(1.0, v * params.vibrancy)
            fb[y][x] = v ** params.gamma
    # ASCII Output
    lines = []
    for y in range(height):
        line = ''.join(intensitaet_zu_ascii(fb[y][x], params.gamma) for x in range(width))
        lines.append(line)
    return '\n'.join(lines)

def main():
    print("3D-Lichtspiel: Herbstlicher Park – Volumetric Light & Shadow")
    print("Steuerung: WASD=Bewegen, QE=Hoch/Runter, Pfeile=Drehen, L=Licht bewegen, P=Parameter, Enter=Neuer Frame, X=Ende")
    params = ShaderParams()
    # Szene: Bäume (x, y, radius, höhe)
    baeume = [
        (-3.0, -2.0, 0.6, 4.0),
        (4.0, 3.0, 0.5, 3.5),
        (-5.0, 5.0, 0.7, 5.0),
        (2.0, -4.0, 0.4, 3.0),
        (0.0, 6.0, 0.8, 4.5),
        (-7.0, -1.0, 0.5, 3.8),
    ]
    light_pos = [0.0, 0.0, 8.0]
    cam_x, cam_y, cam_z = 0.0, -10.0, 2.0
    cam_yaw, cam_pitch = 0.0, -0.2
    width, height = 80, 40
    try:
        while True:
            frame = render_frame(params, cam_x, cam_y, cam_z, cam_yaw, cam_pitch, light_pos, baeume, width, height)
            print('\033[2J\033[H', end='')  # Clear screen
            print(frame)
            print(f"Cam: ({cam_x:.1f},{cam_y:.1f},{cam_z:.1f}) Yaw:{cam_yaw:.2f} Pitch:{cam_pitch:.2f} Light:({light_pos[0]:.1f},{light_pos[1]:.1f},{light_pos[2]:.1f})")
            print("Cmd: ", end='', flush=True)
            try:
                cmd = input().strip().lower()
            except EOFError:
                break
            if not cmd:
                continue
            if cmd == 'x':
                break
            elif cmd == 'w':
                cam_x += math.cos(cam_yaw) * 0.5
                cam_y += math.sin(cam_yaw) * 0.5
            elif cmd == 's':
                cam_x -= math.cos(cam_yaw) * 0.5
                cam_y -= math.sin(cam_yaw) * 0.5
            elif cmd == 'a':
                cam_x += math.cos(cam_yaw + math.pi/2) * 0.5
                cam_y += math.sin(cam_yaw + math.pi/2) * 0.5
            elif cmd == 'd':
                cam_x += math.cos(cam_yaw - math.pi/2) * 0.5
                cam_y += math.sin(cam_yaw - math.pi/2) * 0.5
            elif cmd == 'q':
                cam_z += 0.5
            elif cmd == 'e':
                cam_z -= 0.5
            elif cmd == 'left':
                cam_yaw -= 0.1
            elif cmd == 'right':
                cam_yaw += 0.1
            elif cmd == 'up':
                cam_pitch += 0.1
            elif cmd == 'down':
                cam_pitch -= 0.1
            elif cmd == 'l':
                print("Licht X Y Z (leer für skip): ", end='', flush=True)
                try:
                    coords = input().split()
                    if len(coords) == 3:
                        light_pos[0] = float(coords[0])
                        light_pos[1] = float(coords[1])
                        light_pos[2] = float(coords[2])
                except:
                    pass
            elif cmd == 'p':
                print("Parameter (name=wert, leer zum Ende):")
                while True:
                    try:
                        line = input().strip()
                    except EOFError:
                        break
                    if not line:
                        break
                    if '=' in line:
                        name, val = line.split('=', 1)
                        name = name.strip()
                        try:
                            val = float(val.strip())
                            if hasattr(params, name):
                                setattr(params, name, val)
                                print(f"  {name} = {val}")
                            else:
                                print(f"  Unbekannt: {name}")
                        except:
                            print(f"  Ungültiger Wert: {val}")
            else:
                print(f"Unbekannt: {cmd}")
    except KeyboardInterrupt:
        pass
    print("\nBis zum nächsten Lichtspiel!")

if __name__ == "__main__":
    main()