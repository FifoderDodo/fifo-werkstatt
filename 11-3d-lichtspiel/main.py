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
    
    # Farbtemperatur-Faktoren
    rf, gf, bf = kelvin_to_rgb_factor(params.color_temp)
    
    # Vorberechnung: Licht-Richtung für Phase-Function
    light_dir = (lx - cam_x, ly - cam_y, lz - cam_z)
    light_dist = math.hypot(*light_dir)
    if light_dist > 0:
        light_dir = (light_dir[0]/light_dist, light_dir[1]/light_dist, light_dir[2]/light_dist)
    else:
        light_dir = (0,0,1)
    
    for iy in range(height):
        for ix in range(width):
            # Pixel -> Weltkoordinaten auf Ground-Plane (z=0)
            wx = (ix + 0.5) / width * world_w - world_w * 0.5
            wy = (iy + 0.5) / height * world_h - world_h * 0.5
            wz = 0.0
            
            # Ray-Direction von Kamera zum Pixel auf Ground
            rx, ry, rz = wx - cam_x, wy - cam_y, wz - cam_z
            rlen = math.hypot(rx, ry, rz)
            if rlen < 1e-6:
                continue
            rx, ry, rz = rx / rlen, ry / rlen, rz / rlen
            
            # Ray-Marching
            accum = 0.0
            transmittance = 1.0
            px, py, pz = cam_x, cam_y, cam_z
            for step in range(params.march_steps):
                # Jitter für weichere Kanten
                if params.jitter_enabled:
                    jx = noise_2d(px * 0.5 + frame * 0.01, py * 0.5, params.noise_seed) * params.jitter_strength * step_size
                    jy = noise_2d(px * 0.5 + frame * 0.01 + 100, py * 0.5, params.noise_seed) * params.jitter_strength * step_size
                    jz = noise_2d(px * 0.5 + frame * 0.01 + 200, py * 0.5, params.noise_seed) * params.jitter_strength * step_size
                    px += jx; py += jy; pz += jz
                
                # Distanz zum Licht
                ldx, ldy, ldz = lx - px, ly - py, lz - pz
                ld = math.hypot(ldx, ldy, ldz)
                if ld < 0.01:
                    break
                ldx, ldy, ldz = ldx/ld, ldy/ld, ldz/ld
                
                # Phase-Function (Henyey-Greenstein)
                cos_theta = rx * ldx + ry * ldy + rz * ldz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                
                # Falloff
                falloff = 1.0 / max(0.01, ld ** params.falloff_exponent)
                if ld > params.falloff_start:
                    falloff *= (params.falloff_start / ld) ** params.falloff_exponent
                
                # Mist-Dichte mit Height-Falloff
                mist = params.mist_density * math.exp(-pz * params.mist_height_falloff)
                
                # Schatten-Lookup: Projektionspunkt auf Ground-Plane
                # Wir schneiden den Lichtstrahl mit z=0
                if ldz < -1e-4:
                    t_ground = -pz / ldz
                    if t_ground > 0:
                        sx = px + ldx * t_ground
                        sy = py + ldy * t_ground
                        shadow = schattenfaktor_für_punkt(sx, sy, lx, ly, ld, bäume, params)
                    else:
                        shadow = 1.0
                else:
                    shadow = 1.0
                
                # Volumetrischer Beitrag
                scatter = params.scattering_coeff * phase * falloff * mist * shadow
                absorption = params.absorption_coeff * mist
                accum += transmittance * scatter * step_size
                transmittance *= math.exp(-absorption * step_size)
                if transmittance < 0.01:
                    break
                
                # Nächster Schritt
                px += rx * step_size
                py += ry * step_size
                pz += rz * step_size
                if pz <= 0:
                    break
            
            # Ground-Intersection (einfaches Lambert + Specular)
            if pz <= 0:
                # Schnittpunkt schon bei pz<=0
                gx, gy = px, py
            else:
                # Extrapoliere zum Ground
                t = -cam_z / rz
                if t > 0:
                    gx = cam_x + rx * t
                    gy = cam_y + ry * t
                else:
                    gx, gy = wx, wy
            
            # Schatten am Ground-Punkt
            ld_ground = math.hypot(gx - lx, gy - ly)
            shadow_ground = schattenfaktor_für_punkt(gx, gy, lx, ly, ld_ground, bäume, params) if ld_ground > 0.01 else 1.0
            
            # Lambert-Term
            n_dot_l = max(0.0, ldz)  # Ground-Normal ist (0,0,1)
            lambert = n_dot_l * falloff * shadow_ground
            
            # Specular (Blinn-Phong approximation)
            hx, hy, hz = (rx + ldx) * 0.5, (ry + ldy) * 0.5, (rz + ldz) * 0.5
            hlen = math.hypot(hx, hy, hz)
            spec = 0.0
            if hlen > 0:
                hx, hy, hz = hx/hlen, hy/hlen, hz/hlen
                n_dot_h = max(0.0, hz)
                spec = (n_dot_h ** params.specular_power) * params.specular_intensity * shadow_ground
                # Specular-Noise für raue Oberfläche
                spec_noise = noise_2d(gx * params.specular_noise_scale, gy * params.specular_noise_scale, params.noise_seed + 1)
                spec *= 0.5 + 0.5 * spec_noise
            
            # Gesamthelligkeit
            total = (accum * params.volumetric_gain + lambert + spec) * (1.0 - params.ambient) + params.ambient
            
            # Farbtemperatur anwenden (nur für Helligkeit relevant, ASCII ist monochrom)
            # Wir mischen die Kanäle zu einem Luminanzwert
            lum = total * (0.2126 * rf + 0.7152 * gf + 0.0722 * bf)
            img[iy][ix] = lum
    
    # Optional: Box-Blur für weichere Volumenkegel
    if params.blur_radius > 0:
        gew = gauß_gewichte(params.blur_radius)
        img = box_blur_1d(img, gew, True)
        img = box_blur_1d(img, gew, False)
    
    # Gamma-Korrektur und ASCII-Umwandlung
    ascii_lines = []
    for row in img:
        line = ''.join(intensitaet_zu_ascii(v, params.gamma) for v in row)
        ascii_lines.append(line)
    return ascii_lines

def main():
    params = ShaderParams()
    # Bäume: (x, y, radius)
    random.seed(12345)
    bäume = []
    for _ in range(12):
        bx = random.uniform(-5.5, 5.5)
        by = random.uniform(-5.5, 5.5)
        br = random.uniform(0.3, 0.7)
        bäume.append((bx, by, br))
    
    width, height = 80, 24
    frame = 0
    licht_radius = 4.0
    licht_hoehe = 3.5
    licht_winkel = 0.0
    
    print("\033[?25l", end='')  # Cursor ausblenden
    try:
        while True:
            # Licht animieren
            licht_winkel += 0.02
            lx = math.cos(licht_winkel) * licht_radius
            ly = math.sin(licht_winkel) * licht_radius
            lz = licht_hoehe + 0.5 * math.sin(licht_winkel * 0.7)
            
            lines = render(params, bäume, (lx, ly, lz), width, height, frame)
            
            # Statuszeile
            status = f"Frame {frame} Licht=({lx:.1f},{ly:.1f},{lz:.1f}) Steps={params.march_steps} Gain={params.volumetric_gain} [q]uit [+/-]Gain [.</>]Steps [a/z]Ambient [c/v]ColorTemp [b/n]Mist [m/,]Scatter [j/k]Jitter [p/l]Spec"
            
            # Ausgabe: Cursor home, dann Zeilen
            out = "\033[H" + "\n".join(lines) + "\n" + status + "\n"
            sys.stdout.write(out)
            sys.stdout.flush()
            
            # Non-blocking Input
            rlist, _, _ = select.select([sys.stdin], [], [], 0.03)
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
                    params.volumetric_gain = max(0.1, params.volumetric_gain - 0.1)
                elif key == '.':
                    params.march_steps = min(64, params.march_steps + 2)
                elif key == '>':
                    params.march_steps = max(4, params.march_steps - 2)
                elif key == 'a':
                    params.ambient = min(0.5, params.ambient + 0.01)
                elif key == 'z':
                    params.ambient = max(0.0, params.ambient - 0.01)
                elif key == 'c':
                    params.color_temp = min(6500.0, params.color_temp + 100.0)
                elif key == 'v':
                    params.color_temp = max(1000.0, params.color_temp - 100.0)
                elif key == 'b':
                    params.mist_density = min(1.0, params.mist_density + 0.02)
                elif key == 'n':
                    params.mist_density = max(0.0, params.mist_density - 0.02)
                elif key == 'm':
                    params.scattering_coeff = min(2.0, params.scattering_coeff + 0.02)
                elif key == ',':
                    params.scattering_coeff = max(0.0, params.scattering_coeff - 0.02)
                elif key == 'j':
                    params.jitter_strength = min(0.5, params.jitter_strength + 0.01)
                elif key == 'k':
                    params.jitter_strength = max(0.0, params.jitter_strength - 0.01)
                elif key == 'p':
                    params.specular_intensity = min(2.0, params.specular_intensity + 0.05)
                elif key == 'l':
                    params.specular_intensity = max(0.0, params.specular_intensity - 0.05)
            
            frame += 1
            time.sleep(0.02)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        print("\033[?25h\033[2J\033[H", end='')  # Cursor wieder zeigen, Bildschirm leeren
        print("Gute Nacht vom Dodo. 🌙")

if __name__ == "__main__":
    main()