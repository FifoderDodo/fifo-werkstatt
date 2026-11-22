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
    shadow_map = [[1.0 for _ in range(width)] for _ in range(height)]
    for iy in range(height):
        for ix in range(width):
            # Weltkoordinaten des Pixels auf der Ground‑Plane
            wx = (ix / (width - 1) - 0.5) * world_w
            wy = (iy / (height - 1) - 0.5) * world_h
            shadow_map[iy][ix] = schattenfaktor_für_punkt(wx, wy, lx, ly, radius=5.0, bäume=bäume, params=params)

    # optional Blur, um weiche Schatten zu simulieren (kleiner Box‑Blur)
    if params.blur_radius > 0:
        gew = gauß_gewichte(params.blur_radius)
        shadow_map = box_blur_1d(shadow_map, gew, horizontal=True)
        shadow_map = box_blur_1d(shadow_map, gew, horizontal=False)

    # 2. Ray‑march für jedes Pixel
    for iy in range(height):
        for ix in range(width):
            # Richtung vom Kamera‑Punkt zur Pixel‑Position auf Ground‑Plane
            wx = (ix / (width - 1) - 0.5) * world_w
            wy = (iy / (height - 1) - 0.5) * world_h
            dir_x = wx - cam_x
            dir_y = wy - cam_y
            dir_z = -cam_z  # nach unten zur Plane z=0
            length = math.sqrt(dir_x * dir_x + dir_y * dir_y + dir_z * dir_z)
            dir_x, dir_y, dir_z = dir_x / length, dir_y / length, dir_z / length

            dist = 0.0
            intensity = params.ambient
            while dist < max_dist:
                # aktuelle Position im Raum
                px = cam_x + dir_x * dist
                py = cam_y + dir_y * dist
                pz = cam_z + dir_z * dist
                # einfache Dichtefunktion: nur Ground‑Plane (z=0) hat Material
                if pz <= 0.0:
                    # Abstand zum Licht für falloff
                    lx_vec = lx - px
                    ly_vec = ly - py
                    lz_vec = lz - pz
                    l_dist = math.sqrt(lx_vec * lx_vec + ly_vec * ly_vec + lz_vec * lz_vec)
                    falloff = 1.0 / (params.falloff_start + (l_dist ** params.falloff_exponent))
                    # Schattenfaktor aus vorgerenderter Karte
                    sh = shadow_map[iy][ix]
                    # simple volumetric term
                    vol = params.volumetric_gain * math.exp(-params.absorption_coeff * l_dist)
                    intensity += falloff * sh * vol
                    break
                dist += step_size
            img[iy][ix] = intensity

    # ASCII‑Umwandlung
    lines = [''.join(intensitaet_zu_ascii(v, params.gamma) for v in row) for row in img]
    return lines

def beispiel_baeume():
    # ein paar zufällige Bäume (x, y, radius) im World‑Space
    random.seed(0)
    return [(random.uniform(-4, 4), random.uniform(-4, 4), random.uniform(0.3, 0.8)) for _ in range(8)]

def main():
    params = ShaderParams()
    bäume = beispiel_baeume()
    licht_pos = (2.0, 3.0, 8.0)
    frame = 0
    width, height = 60, 20
    print('Drücke <Enter> für nächsten Frame, EOF zum Beenden')
    while True:
        lines = render(params, bäume, licht_pos, width, height, frame)
        for l in lines:
            print(l)
        print(f'-- Frame {frame} --')
        frame += 1
        # nicht‑blockierende Eingabe, maximal 20 Frames
        if frame >= 20:
            break
        # warten auf Eingabe oder Timeout von 0.1 s
        rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
        if rlist:
            try:
                _ = sys.stdin.readline()
            except EOFError:
                print('EOF erhalten, beende.')
                break
        # leichte Animation: Licht umkreist die Szene
        angle = frame * 0.2
        licht_pos = (5.0 * math.cos(angle), 5.0 * math.sin(angle), 8.0)

if __name__ == '__main__':
    main()