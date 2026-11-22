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
    
    # Vorberechnete Farbfaktoren für Lichttemperatur
    rf, gf, bf = kelvin_to_rgb_factor(params.color_temp)
    
    for iy in range(height):
        for ix in range(width):
            # Pixel → Weltkoordinaten auf der Viewplane (z=0)
            wx = (ix - width * 0.5) / width * world_w
            wy = (iy - height * 0.5) / height * world_h
            # Ray Direction (normalisiert)
            rdx, rdy, rdz = wx - cam_x, wy - cam_y, -cam_z
            rlen = math.hypot(rdx, math.hypot(rdy, rdz))
            rdx, rdy, rdz = rdx / rlen, rdy / rlen, rdz / rlen
            
            # Ray Marching
            vol = 0.0
            t = 0.0
            for step in range(params.march_steps):
                # Position entlang des Rays
                px = cam_x + rdx * t
                py = cam_y + rdy * t
                pz = cam_z + rdz * t
                if pz <= 0.0:
                    break
                
                # Lichtvektor von Sample zu Lichtquelle
                ldx, ldy, ldz = lx - px, ly - py, lz - pz
                ld = math.hypot(ldx, math.hypot(ldy, ldz))
                if ld < 1e-4:
                    t += step_size
                    continue
                ldx, ldy, ldz = ldx / ld, ldy / ld, ldz / ld
                
                # Phase Function (Henyey‑Greenstein)
                cos_theta = rdx * ldx + rdy * ldy + rdz * ldz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                
                # Falloff (quadratisch ab falloff_start)
                falloff = 1.0
                if ld > params.falloff_start:
                    falloff = (params.falloff_start / ld) ** params.falloff_exponent
                
                # Mist Dichte (exponentiell mit Höhe)
                mist = params.mist_density * math.exp(-pz * params.mist_height_falloff)
                
                # Jitter für weichere Kanten
                jitter = 0.0
                if params.jitter_enabled:
                    jitter = noise_3d(px * 0.5, py * 0.5, pz * 0.5 + frame * 0.07, params.noise_seed) * params.jitter_strength
                
                # Akkumulation
                vol += (phase * falloff * mist * params.scattering_coeff * (1.0 + jitter)) * step_size
                
                # Absorption (einfaches Beer‑Lambert)
                vol *= math.exp(-params.absorption_coeff * step_size)
                
                t += step_size
            
            # Ground Intersection (z=0)
            if rdz < 0:
                t_ground = -cam_z / rdz
                gx = cam_x + rdx * t_ground
                gy = cam_y + rdy * t_ground
                # Schattenfaktor von Bäumen
                shadow = schattenfaktor_für_punkt(gx, gy, lx, ly, max_dist, bäume, params)
                # Ground Contribution (diffus + spekulär)
                ground = params.ambient + shadow * (0.6 + 0.4 * max(0.0, -rdz))
                # Spekularer Glanz auf nassem Laub
                if params.specular_intensity > 0:
                    hx, hy, hz = (rdx + ldx) * 0.5, (rdy + ldy) * 0.5, (rdz + ldz) * 0.5
                    hlen = math.hypot(hx, math.hypot(hy, hz))
                    if hlen > 0:
                        hx, hy, hz = hx / hlen, hy / hlen, hz / hlen
                        spec = max(0.0, hz) ** params.specular_power
                        spec_noise = noise_2d(gx * params.specular_noise_scale, gy * params.specular_noise_scale, params.noise_seed + 1) * 0.5 + 0.5
                        ground += params.specular_intensity * spec * spec_noise * shadow
            else:
                ground = params.ambient
            
            # Volumetric Gain & Gamma
            total = (vol * params.volumetric_gain + ground) ** params.gamma
            # Farbtemperatur anwenden (nur für Helligkeit relevant, ASCII ist monochrom)
            # Wir nutzen den Grün‑Kanal als Luminanz‑Proxy
            total *= gf
            img[iy][ix] = min(1.0, max(0.0, total))
    
    # Optional: Box Blur auf dem fertigen Bild für weichere Kanten
    if params.blur_radius > 0:
        gew = gauß_gewichte(params.blur_radius)
        img = box_blur_1d(img, gew, True)
        img = box_blur_1d(img, gew, False)
    
    # ASCII Konvertierung
    ascii_lines = []
    for row in img:
        line = ''.join(intensitaet_zu_ascii(v, params.gamma) for v in row)
        ascii_lines.append(line)
    return ascii_lines


def main():
    params = ShaderParams()
    # Beispiel‑Bäume: (x, y, radius)
    random.seed(123)
    bäume = []
    for _ in range(12):
        bx = random.uniform(-5.5, 5.5)
        by = random.uniform(-5.5, 5.5)
        br = random.uniform(0.4, 0.9)
        bäume.append((bx, by, br))
    
    # Lichtposition startet links oben
    licht = [ -4.0, 3.0, 4.0 ]
    frame = 0
    width, height = 60, 18
    
    print("3D‑Lichtspiel – Tasten: q=quit, +/- Gain, </> Steps, a/z Ambient,")
    print("  c/v ColorTemp, b/n Mist, m/, Scatter, j/k Jitter, p/l Specular")
    
    try:
        while True:
            # Animation: Licht kreist langsam
            angle = frame * 0.02
            licht[0] = math.sin(angle) * 4.5
            licht[1] = math.cos(angle) * 3.5
            licht[2] = 3.5 + 0.5 * math.sin(frame * 0.01)
            
            lines = render(params, bäume, licht, width, height, frame)
            # Cursor nach oben bewegen (ANSI)
            sys.stdout.write('\x1b[H')  # Home
            for ln in lines:
                sys.stdout.write(ln + '\n')
            sys.stdout.write(f'Frame {frame} Licht=({licht[0]:.1f},{licht[1]:.1f},{licht[2]:.1f}) Steps={params.march_steps} Gain={params.volumetric_gain:.1f}')
            sys.stdout.write(' [q]uit [+/-]Gain [.</>]Steps [a/z]Ambient [c/v]ColorTemp [b/n]Mist [m/,]Scatter [j/k]Jitter [p/l]Spec\n')
            sys.stdout.flush()
            
            # Non‑blocking Input
            rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
            if rlist:
                key = sys.stdin.read(1)
                if not key:
                    break
                key = _norm(key)
                if key == 'q':
                    break
                elif key == '+':
                    params.volumetric_gain = min(5.0, params.volumetric_gain + 0.1)
                elif key == '-':
                    params.volumetric_gain = max(0.5, params.volumetric_gain - 0.1)
                elif key == '.':
                    params.march_steps = min(64, params.march_steps + 2)
                elif key == '>':
                    params.march_steps = max(8, params.march_steps - 2)
                elif key == 'a':
                    params.ambient = min(0.3, params.ambient + 0.01)
                elif key == 'z':
                    params.ambient = max(0.0, params.ambient - 0.01)
                elif key == 'c':
                    params.color_temp = min(6500.0, params.color_temp + 100.0)
                elif key == 'v':
                    params.color_temp = max(1500.0, params.color_temp - 100.0)
                elif key == 'b':
                    params.mist_density = min(0.5, params.mist_density + 0.01)
                elif key == 'n':
                    params.mist_density = max(0.05, params.mist_density - 0.01)
                elif key == 'm':
                    params.scattering_coeff = min(1.0, params.scattering_coeff + 0.02)
                elif key == ',':
                    params.scattering_coeff = max(0.1, params.scattering_coeff - 0.02)
                elif key == 'j':
                    params.jitter_strength = min(0.3, params.jitter_strength + 0.01)
                elif key == 'k':
                    params.jitter_strength = max(0.0, params.jitter_strength - 0.01)
                elif key == 'p':
                    params.specular_intensity = min(1.0, params.specular_intensity + 0.05)
                elif key == 'l':
                    params.specular_intensity = max(0.0, params.specular_intensity - 0.05)
            
            frame += 1
            time.sleep(0.03)
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        sys.stdout.write('\nTschüss! Der Dodo schläft weiter.\n')
        sys.stdout.flush()

if __name__ == '__main__':
    main()