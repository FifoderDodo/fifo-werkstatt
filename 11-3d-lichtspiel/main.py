import math, sys, random, unicodedata, time, select

class ShaderParams:
    """Container für alle einstellbaren Shader‑Parameter mit Defaults."""
    def __init__(self):
        self.penumbra_breite = 0.15
        self.umbra_dunkelheit = 0.05
        self.falloff_exponent = 2.0
        self.falloff_start = 0.5
        self.blur_radius = 3
        self.ambient = 0.05          # etwas mehr Umgebungslicht
        self.volumetric_gain = 2.5   # stärkerer Volumeneffekt
        self.gamma = 0.55            # etwas offener
        self.scattering_coeff = 0.45 # mehr Streuung
        self.absorption_coeff = 0.08 # weniger Absorption
        self.mist_density = 0.22
        self.mist_height_falloff = 0.8
        self.color_temp = 3000.0     # wärmeres Licht
        self.jitter_strength = 0.12
        self.phase_g = 0.6
        self.noise_seed = 42
        self.march_steps = 24        # mehr Schritte für sauberere Kegel
        self.jitter_enabled = True
        self.specular_intensity = 0.6
        self.specular_power = 24.0
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

def render(params: ShaderParams, bäume, licht_pos, width=60, height=18, frame=0):
    """Ray‑March vom Kamerapunkt (0,0,10) auf die Ground‑Plane z=0.
    Gibt Liste von ASCII‑Zeilen zurück."""
    img = [[0.0 for _ in range(width)] for _ in range(height)]
    lx, ly, lz = licht_pos
    cam_x, cam_y, cam_z = 0.0, 0.0, 10.0
    world_w, world_h = 12.0, 12.0 * height / width
    max_dist = 18.0
    step_size = max_dist / max(1, params.march_steps)

    # 1. Schattenkarte (nur Ground‑Plane) – für jedes Pixel prüfen, ob Licht durch Bäume blockiert
    shadow_map = [[1.0 for _ in range(width)] for __ in range(height)]
    for iy in range(height):
        wy = (iy / (height - 1) - 0.5) * world_h
        for ix in range(width):
            wx = (ix / (width - 1) - 0.5) * world_w
            # Vektor von Licht zum Punkt auf Ground
            dx, dy, dz = wx - lx, wy - ly, -lz
            dist_light = math.sqrt(dx*dx + dy*dy + dz*dz)
            if dist_light < 0.001:
                shadow_map[iy][ix] = 1.0
                continue
            ux, uy, uz = dx/dist_light, dy/dist_light, dz/dist_light
            shadow = 1.0
            for bx, by, br in bäume:
                # Baum als Zylinder: prüfen ob Strahl den Zylinder schneidet
                vx, vy = bx - lx, by - ly
                proj = vx*ux + vy*uy
                if proj <= 0 or proj >= dist_light:
                    continue
                closest_x = lx + ux*proj
                closest_y = ly + uy*proj
                d = math.hypot(bx - closest_x, by - closest_y)
                if d < br:
                    # Penumbra
                    pen = params.penumbra_breite
                    umb = params.umbra_dunkelheit
                    rand_f = d / br
                    if rand_f < 1.0 - pen:
                        shadow = min(shadow, umb)
                    elif rand_f < 1.0 + pen:
                        t = (rand_f - (1.0 - pen)) / (2.0 * pen)
                        shadow = min(shadow, umb + (1.0 - umb) * t)
            shadow_map[iy][ix] = shadow

    # 2. Ray Marching für jeden Pixel
    for iy in range(height):
        wy = (iy / (height - 1) - 0.5) * world_h
        for ix in range(width):
            wx = (ix / (width - 1) - 0.5) * world_w
            # Ray von Kamera durch Pixel auf Ground Plane (z=0)
            rx, ry, rz = wx - cam_x, wy - cam_y, -cam_z
            ray_len = math.sqrt(rx*rx + ry*ry + rz*rz)
            if ray_len == 0:
                continue
            rdx, rdy, rdz = rx/ray_len, ry/ray_len, rz/ray_len
            # Startpunkt leicht vor der Kamera
            sx, sy, sz = cam_x + rdx*0.1, cam_y + rdy*0.1, cam_z + rdz*0.1
            transmittance = 1.0
            radiance = 0.0
            for step in range(params.march_steps):
                # Position entlang des Strahls
                px = sx + rdx * step * step_size
                py = sy + rdy * step * step_size
                pz = sz + rdz * step * step_size
                if pz <= 0.0:  # Ground erreicht
                    break
                # Distanz zum Licht
                ldx, ldy, ldz = lx - px, ly - py, lz - pz
                dist_light = math.sqrt(ldx*ldx + ldy*ldy + ldz*ldz)
                if dist_light < 0.001:
                    continue
                ldx, ldy, ldz = ldx/dist_light, ldy/dist_light, ldz/dist_light
                # Phase Function
                cos_theta = rdx*ldx + rdy*ldy + rdz*ldz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                # Falloff
                falloff = 1.0 / max(0.01, dist_light**params.falloff_exponent)
                # Mist Density mit Height Falloff
                mist = params.mist_density * math.exp(-pz * params.mist_height_falloff)
                # Jitter für Rauschunterdrückung
                jitter = 0.0
                if params.jitter_enabled:
                    jitter = noise_3d(px*params.specular_noise_scale, py*params.specular_noise_scale, frame*0.1, params.noise_seed) * params.jitter_strength
                # Shadow Lookup: projiziere Punkt auf Ground und sample shadow_map
                # Einfache Projektion entlang Lichtrichtung bis z=0
                if ldz < -1e-4:
                    t_ground = -pz / ldz
                    gx = px + ldx * t_ground
                    gy = py + ldy * t_ground
                    # In Pixelkoordinaten umrechnen
                    ix_s = int((gx / world_w + 0.5) * (width - 1))
                    iy_s = int((gy / world_h + 0.5) * (height - 1))
                    if 0 <= ix_s < width and 0 <= iy_s < height:
                        shadow = shadow_map[iy_s][ix_s]
                    else:
                        shadow = 1.0
                else:
                    shadow = 1.0
                # Volumetric Contribution
                scatter = params.scattering_coeff * phase * falloff * mist * shadow
                absorb = math.exp(-params.absorption_coeff * mist * step_size)
                radiance += transmittance * scatter * (1.0 - absorb)
                transmittance *= absorb
                if transmittance < 0.01:
                    break
            # Ground Contribution (einfaches Lambert mit Shadow)
            if pz <= 0.0:
                ground_shadow = shadow_map[iy][ix]
                radiance += transmittance * params.ambient * ground_shadow
            img[iy][ix] = radiance

    # 3. Blur für weichere Kanten
    if params.blur_radius > 0:
        w = gauß_gewichte(params.blur_radius)
        img = box_blur_1d(img, w, True)
        img = box_blur_1d(img, w, False)

    # 4. Tonemapping & Gamma
    r_factor, g_factor, b_factor = kelvin_to_rgb_factor(params.color_temp)
    ascii_lines = []
    for row in img:
        line = ''
        for val in row:
            # Einfaches Tonemapping (Reinhard-ish)
            mapped = val * params.volumetric_gain
            mapped = mapped / (1.0 + mapped)
            ch = intensitaet_zu_ascii(mapped, params.gamma)
            line += ch
        ascii_lines.append(line)
    return ascii_lines

def main():
    params = ShaderParams()
    # Beispiel-Bäume: (x, y, radius)
    random.seed(123)
    bäume = []
    for _ in range(12):
        bx = random.uniform(-5.5, 5.5)
        by = random.uniform(-5.5, 5.5)
        br = random.uniform(0.35, 0.65)
        bäume.append((bx, by, br))

    frame = 0
    running = True
    print("3D-Lichtspiel – Drücke 'q' zum Beenden, 'h' für Hilfe.")
    while running:
        # Licht auf Kreisbahn
        angle = frame * 0.04
        lx = 4.0 * math.cos(angle)
        ly = 4.0 * math.sin(angle)
        lz = 3.5 + 0.5 * math.sin(frame * 0.02)
        lines = render(params, bäume, (lx, ly, lz), frame=frame)
        sys.stdout.write('\x1b[H\x1b[2J')  # Clear screen
        for line in lines:
            print(line)
        print(f"Frame {frame}  Licht=({lx:.1f},{ly:.1f},{lz:.1f})  Steps={params.march_steps}  Gain={params.volumetric_gain}")
        print("[q]uit [+/-]Gain [.</>]Steps [a/z]Ambient [c/v]ColorTemp [b/n]Mist [m/,]Scatter [j/k]Jitter [p/l]Phase")
        sys.stdout.flush()
        frame += 1
        # Non-blocking input
        ready, _, _ = select.select([sys.stdin], [], [], 0.05)
        if ready:
            try:
                cmd = sys.stdin.readline().strip().lower()
            except EOFError:
                break
            if not cmd:
                continue
            if cmd == 'q':
                running = False
            elif cmd == '+':
                params.volumetric_gain = min(5.0, params.volumetric_gain + 0.2)
            elif cmd == '-':
                params.volumetric_gain = max(0.2, params.volumetric_gain - 0.2)
            elif cmd == '.':
                params.march_steps = min(64, params.march_steps + 4)
            elif cmd == '>':
                params.march_steps = max(8, params.march_steps - 4)
            elif cmd == 'a':
                params.ambient = min(0.3, params.ambient + 0.01)
            elif cmd == 'z':
                params.ambient = max(0.0, params.ambient - 0.01)
            elif cmd == 'c':
                params.color_temp = min(6500.0, params.color_temp + 200.0)
            elif cmd == 'v':
                params.color_temp = max(1500.0, params.color_temp - 200.0)
            elif cmd == 'b':
                params.mist_density = min(0.5, params.mist_density + 0.02)
            elif cmd == 'n':
                params.mist_density = max(0.0, params.mist_density - 0.02)
            elif cmd == 'm':
                params.scattering_coeff = min(1.0, params.scattering_coeff + 0.05)
            elif cmd == ',':
                params.scattering_coeff = max(0.0, params.scattering_coeff - 0.05)
            elif cmd == 'j':
                params.jitter_strength = min(0.5, params.jitter_strength + 0.02)
            elif cmd == 'k':
                params.jitter_strength = max(0.0, params.jitter_strength - 0.02)
            elif cmd == 'p':
                params.phase_g = min(0.95, params.phase_g + 0.05)
            elif cmd == 'l':
                params.phase_g = max(-0.95, params.phase_g - 0.05)
            elif cmd == 'h':
                print("Hilfe: q=Quit, +=Gain+, -=Gain-, .=Steps+, >=Steps-, a/z=Ambient, c/v=ColorTemp, b/n=Mist, m/=Scatter, j/k=Jitter, p/l=Phase")
                time.sleep(1.5)
        if frame > 300:  # Sicherheitsnetz für Tests
            running = False
    print("Gute Nacht!")

if __name__ == '__main__':
    main()