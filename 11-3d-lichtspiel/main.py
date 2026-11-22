import math, sys, random, unicodedata, time, select

class ShaderParams:
    """Container für alle einstellbaren Shader‑Parameter mit Defaults."""
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
        self.march_steps = 16          # reduziert für Performance
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

def render(params: ShaderParams, bäume, licht_pos, width=40, height=12, frame=0):
    """Ray‑March vom Kamerapunkt (0,0,10) auf die Ground‑Plane z=0.
    Gibt Liste von ASCII‑Zeilen zurück."""
    img = [[0.0 for _ in range(width)] for _ in range(height)]
    lx, ly, lz = licht_pos
    cam_x, cam_y, cam_z = 0.0, 0.0, 10.0
    world_w, world_h = 10.0, 10.0 * height / width
    max_dist = 15.0
    step_size = max_dist / max(1, params.march_steps)

    # 1. Schattenkarte (nur Ground‑Plane) – für jedes Pixel prüfen, ob Licht durch Bäume blockiert
    shadow_map = [[1.0 for _ in range(width)] for __ in range(height)]
    for py_idx in range(height):
        for px_idx in range(width):
            # Weltkoordinaten des Pixels auf Ground‑Plane (z=0)
            wx = (px_idx / (width - 1) - 0.5) * world_w
            wy = (py_idx / (height - 1) - 0.5) * world_h
            # Abstand zum Licht in XY
            dx = wx - lx
            dy = wy - ly
            dist_light = math.hypot(dx, dy)
            if dist_light < 0.01:
                shadow_map[py_idx][px_idx] = 1.0
                continue
            # Schattenfaktor durch Bäume
            shadow = 1.0
            for bx, by, br in bäume:
                vx = bx - lx
                vy = by - ly
                dqb = math.hypot(vx, vy)
                if dqb < 0.01:
                    continue
                proj = vx * dx / dist_light + vy * dy / dist_light
                if proj <= 0.01 or proj >= dist_light:
                    continue
                abstand = abs(vx * dy - vy * dx) / dist_light
                if abstand >= br:
                    continue
                shadow_radius = br * (dist_light / dqb)
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
                if faktor < shadow:
                    shadow = faktor
            shadow_map[py_idx][px_idx] = shadow

    # Optionaler Blur auf Schattenkarte für weichere Kanten
    if params.blur_radius > 0:
        gewichte = gauß_gewichte(params.blur_radius)
        shadow_map = box_blur_1d(shadow_map, gewichte, True)
        shadow_map = box_blur_1d(shadow_map, gewichte, False)

    # 2. Volumetric Ray‑March für jedes Pixel
    for py_idx in range(height):
        for px_idx in range(width):
            # Ray‑Direction vom Kamera‑Punkt durch Pixel auf Near‑Plane (z=1)
            u = (px_idx / (width - 1) - 0.5) * world_w
            v = (py_idx / (height - 1) - 0.5) * world_h
            # Ray vom Kamera‑Punkt (0,0,10) durch (u, v, 0) auf Ground‑Plane
            # Parametrisierung: cam + t * dir, wobei dir = (u, v, -cam_z)
            dir_x, dir_y, dir_z = u, v, -cam_z
            length = math.sqrt(dir_x*dir_x + dir_y*dir_y + dir_z*dir_z)
            dir_x /= length
            dir_y /= length
            dir_z /= length

            acc = 0.0
            transmittance = 1.0
            # Jitter für temporales Rauschen
            jitter = 0.0
            if params.jitter_enabled:
                jitter = noise_2d(px_idx * 0.1, py_idx * 0.1, params.noise_seed + frame) * params.jitter_strength

            for step in range(params.march_steps):
                t = (step + 0.5 + jitter) * step_size
                if t > max_dist:
                    break
                # Position entlang des Rays
                rx = cam_x + dir_x * t
                ry = cam_y + dir_y * t
                rz = cam_z + dir_z * t
                if rz <= 0.0:
                    # Ground erreicht
                    break
                # Mist‑Dichte mit Height‑Falloff
                density = params.mist_density * math.exp(-rz * params.mist_height_falloff)
                # Noise für turbulente Mist‑Struktur
                noise_val = noise_3d(rx * params.specular_noise_scale, ry * params.specular_noise_scale, rz * params.specular_noise_scale, params.noise_seed + frame)
                density *= (1.0 + noise_val * 0.3)
                # Licht‑Richtung vom Sample‑Punkt zum Licht
                ldx = lx - rx
                ldy = ly - ry
                ldz = lz - rz
                ldist = math.sqrt(ldx*ldx + ldy*ldy + ldz*ldz)
                if ldist < 0.01:
                    continue
                ldx /= ldist
                ldy /= ldist
                ldz /= ldist
                # Phase‑Function (Henyey‑Greenstein)
                cos_theta = dir_x * ldx + dir_y * ldy + dir_z * ldz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                # Schatten entlang der Licht‑Richtung (einfacher Shadow‑Test auf Ground‑Plane)
                # Projektieren Sie den Sample‑Punkt auf Ground‑Plane entlang Licht‑Richtung
                if ldz < -1e-4:
                    t_light = -rz / ldz
                    sx = rx + ldx * t_light
                    sy = ry + ldy * t_light
                    # Schattenfaktor aus Shadow‑Map (bilinear interpoliert)
                    # Map world coords to shadow_map indices
                    sm_x = (sx / world_w + 0.5) * (width - 1)
                    sm_y = (sy / world_h + 0.5) * (height - 1)
                    ix0 = int(math.floor(sm_x))
                    iy0 = int(math.floor(sm_y))
                    fx = sm_x - ix0
                    fy = sm_y - iy0
                    shadow = 1.0
                    if 0 <= ix0 < width - 1 and 0 <= iy0 < height - 1:
                        s00 = shadow_map[iy0][ix0]
                        s10 = shadow_map[iy0][ix0 + 1]
                        s01 = shadow_map[iy0 + 1][ix0]
                        s11 = shadow_map[iy0 + 1][ix0 + 1]
                        shadow = (s00 * (1-fx) + s10 * fx) * (1-fy) + (s01 * (1-fx) + s11 * fx) * fy
                    else:
                        shadow = 1.0
                else:
                    shadow = 1.0
                # Falloff mit Exponent
                falloff = 1.0 / (1.0 + (ldist * params.falloff_start) ** params.falloff_exponent)
                # Scattering‑Beitrag
                scatter = density * params.scattering_coeff * phase * falloff * shadow
                # Absorption
                transmittance *= math.exp(-density * params.absorption_coeff * step_size)
                acc += scatter * transmittance
                if transmittance < 0.01:
                    break
            # Add ambient
            acc += params.ambient
            # Volumetric gain
            acc *= params.volumetric_gain
            img[py_idx][px_idx] = acc

    # 3. Convert to ASCII
    lines = []
    for row in img:
        line = ''.join(intensitaet_zu_ascii(v, params.gamma) for v in row)
        lines.append(line)
    return lines

def main():
    params = ShaderParams()
    # Beispiel‑Bäume: (x, y, radius)
    bäume = [
        (-3.0, -2.0, 0.8),
        (2.5, 1.5, 0.6),
        (-1.0, 3.0, 0.7),
        (4.0, -3.0, 0.9),
        (0.0, -4.0, 0.5),
    ]
    frame = 0
    try:
        while True:
            # Licht bewegt sich auf einem Kreis
            angle = frame * 0.05
            lx = 5.0 * math.cos(angle)
            ly = 5.0 * math.sin(angle)
            lz = 4.0 + 0.5 * math.sin(frame * 0.03)
            lines = render(params, bäume, (lx, ly, lz), width=60, height=20, frame=frame)
            print(f'-- Frame {frame} --')
            for line in lines:
                print(line)
            sys.stdout.flush()
            frame += 1
            # Eingabe prüfen (nicht blockierend)
            ready, _, _ = select.select([sys.stdin], [], [], 0.05)
            if ready:
                inp = sys.stdin.readline()
                if not inp:
                    break
                inp = _norm(inp)
                if inp in ('q', 'quit', 'exit'):
                    break
                # Einfache Parameter‑Änderungen per Tastatur
                if inp == 'w':
                    params.mist_density = min(1.0, params.mist_density + 0.02)
                elif inp == 's':
                    params.mist_density = max(0.0, params.mist_density - 0.02)
                elif inp == 'a':
                    params.volumetric_gain = max(0.1, params.volumetric_gain - 0.1)
                elif inp == 'd':
                    params.volumetric_gain = min(5.0, params.volumetric_gain + 0.1)
                elif inp == 'r':
                    params = ShaderParams()  # Reset
                print(f'Parameter: mist={params.mist_density:.2f}, gain={params.volumetric_gain:.2f}')
            time.sleep(0.03)
    except (KeyboardInterrupt, EOFError):
        pass
    print('\nDodo wacht auf. Bis zum nächsten Traum!')

if __name__ == '__main__':
    main()