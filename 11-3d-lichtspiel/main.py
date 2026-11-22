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
    img = [[0.0 for _ in range(width)] for _ in range(height)]
    lx, ly, lz = licht_pos
    cam_x, cam_y, cam_z = 0.0, 0.0, 10.0
    world_w, world_h = 12.0, 12.0 * height / width
    max_dist = 18.0
    step_size = max_dist / max(1, params.march_steps)
    light_r, light_g, light_b = kelvin_to_rgb_factor(params.color_temp)
    
    # Temporal jitter for noise
    jitter = 0.0
    if params.jitter_enabled:
        jitter = (noise_2d(frame * 0.1, 0.0, params.noise_seed) * 0.5 + 0.5) * params.jitter_strength
    
    for y in range(height):
        for x in range(width):
            # Pixel to world coordinates
            px = (x + 0.5 + jitter) / width * world_w - world_w * 0.5
            py = (y + 0.5) / height * world_h - world_h * 0.5
            
            # Ray from camera to pixel on near plane (z=0)
            rx, ry, rz = px - cam_x, py - cam_y, -cam_z
            rlen = math.sqrt(rx*rx + ry*ry + rz*rz)
            rx, ry, rz = rx/rlen, ry/rlen, rz/rlen
            
            # Light direction from pixel to light
            ldx, ldy, ldz = lx - px, ly - py, lz - 0.0  # light at ground level? assume z=0
            ldlen = math.sqrt(ldx*ldx + ldy*ldy + ldz*ldz)
            if ldlen < 0.001:
                continue
            ldx, ldy, ldz = ldx/ldlen, ldy/ldlen, ldz/ldlen
            
            # Cosine of angle between view ray and light direction
            cos_theta = rx*ldx + ry*ldy + rz*ldz
            phase = henyey_greenstein(cos_theta, params.phase_g)
            
            # Ray marching
            acc = 0.0
            transmittance = 1.0
            for step in range(params.march_steps):
                t = step * step_size
                # Current point in world
                wx = cam_x + rx * t
                wy = cam_y + ry * t
                wz = cam_z + rz * t
                if wz <= 0.0:
                    # Hit ground
                    break
                
                # Distance to light
                dlx = lx - wx
                dly = ly - wy
                dlz = lz - wz
                dlight = math.sqrt(dlx*dlx + dly*dly + dlz*dlz)
                if dlight < 0.001:
                    continue
                
                # Shadow factor from trees
                shadow = schattenfaktor_für_punkt(wx, wy, lx, ly, dlight, bäume, params)
                
                # Mist density with height falloff
                mist = params.mist_density * math.exp(-wz * params.mist_height_falloff)
                
                # Noise for volumetric variation
                n = noise_3d(wx * 0.5, wy * 0.5, wz * 0.5, params.noise_seed + frame)
                mist *= 1.0 + n * 0.3
                
                # Falloff
                falloff = 1.0 / (1.0 + (dlight * params.falloff_start) ** params.falloff_exponent)
                
                # Scattering and absorption
                scatter = params.scattering_coeff * mist * falloff * phase * shadow
                absorb = params.absorption_coeff * mist
                
                # Accumulate
                acc += transmittance * scatter * step_size
                transmittance *= math.exp(-absorb * step_size)
                if transmittance < 0.01:
                    break
            
            # Specular highlight on ground (if ray hits ground)
            # Simple ground intersection at z=0
            if rz < 0:
                t_ground = -cam_z / rz
                if t_ground > 0:
                    gx = cam_x + rx * t_ground
                    gy = cam_y + ry * t_ground
                    # Distance to light
                    glx = lx - gx
                    gly = ly - gy
                    glz = lz - 0.0
                    glen = math.sqrt(glx*glx + gly*gly + glz*glz)
                    if glen > 0.001:
                        glx, gly, glz = glx/glen, gly/glen, glz/glen
                        # View direction from ground to camera
                        vx, vy, vz = -rx, -ry, -rz
                        # Half vector
                        hx, hy, hz = (vx+glx)*0.5, (vy+gly)*0.5, (vz+glz)*0.5
                        hlen = math.sqrt(hx*hx + hy*hy + hz*hz)
                        if hlen > 0.001:
                            hx, hy, hz = hx/hlen, hy/hlen, hz/hlen
                            spec = max(0.0, hx*vx + hy*vy + hz*vz) ** params.specular_power
                            # Add noise to specular
                            spec_noise = noise_2d(gx * params.specular_noise_scale, gy * params.specular_noise_scale, params.noise_seed + 100)
                            spec *= 1.0 + spec_noise * 0.2
                            acc += params.specular_intensity * spec * light_r  # use red channel as intensity
            
            # Apply volumetric gain and ambient
            acc = acc * params.volumetric_gain + params.ambient
            
            # Color temperature weighting (simplified to luminance)
            luminance = acc * (light_r * 0.2126 + light_g * 0.7152 + light_b * 0.0722)
            img[y][x] = luminance
    
    # Optional blur
    if params.blur_radius > 0:
        weights = gauß_gewichte(params.blur_radius)
        img = box_blur_1d(img, weights, True)
        img = box_blur_1d(img, weights, False)
    
    return img

def main():
    params = ShaderParams()
    # Beispiel-Bäume: (x, y, radius)
    bäume = [
        (-3.0, -2.0, 0.8),
        (2.0, 1.5, 0.6),
        (-1.0, 3.0, 0.7),
        (4.0, -3.0, 0.5),
        (-4.0, 2.0, 0.9),
    ]
    
    width, height = 60, 18
    frame = 0
    max_frames = 30
    
    # Licht animiert auf einer Kreisbahn
    light_radius = 4.0
    light_height = 4.2
    
    print("3D-Lichtspiel – Drücke 'q' zum Beenden, 'p' für Parameter, Enter für nächsten Frame")
    
    while frame < max_frames:
        # Lichtposition berechnen
        angle = frame * 0.2
        lx = math.sin(angle) * light_radius
        ly = math.cos(angle) * light_radius
        lz = light_height
        
        img = render(params, bäume, (lx, ly, lz), width, height, frame)
        
        # Ausgabe
        sys.stdout.write(f"\rFrame {frame:3d} - Licht: ({lx:5.1f}, {ly:5.1f}, {lz:4.1f}) Params: gain={params.volumetric_gain:.2f}\n")
        for row in img:
            line = ''.join(intensitaet_zu_ascii(v, params.gamma) for v in row)
            sys.stdout.write(line + '\n')
        sys.stdout.flush()
        
        # Non-blocking input
        ready, _, _ = select.select([sys.stdin], [], [], 0.05)
        if ready:
            try:
                inp = sys.stdin.readline().strip().lower()
                if inp == 'q':
                    break
                elif inp == 'p':
                    print(f"\nParameter: gain={params.volumetric_gain}, gamma={params.gamma}, scatter={params.scattering_coeff}, absorption={params.absorption_coeff}, mist={params.mist_density}, temp={params.color_temp}")
                    print("Neue Werte (leer lassen für Beibehaltung):")
                    try:
                        val = input("volumetric_gain: ").strip()
                        if val: params.volumetric_gain = float(val)
                        val = input("gamma: ").strip()
                        if val: params.gamma = float(val)
                        val = input("scattering_coeff: ").strip()
                        if val: params.scattering_coeff = float(val)
                        val = input("absorption_coeff: ").strip()
                        if val: params.absorption_coeff = float(val)
                        val = input("mist_density: ").strip()
                        if val: params.mist_density = float(val)
                        val = input("color_temp: ").strip()
                        if val: params.color_temp = float(val)
                    except (ValueError, EOFError):
                        pass
                    print("Parameter aktualisiert.\n")
                elif inp == '':
                    pass  # just advance frame
            except EOFError:
                break
        
        frame += 1
        time.sleep(0.05)
    
    print("\nEnde der Simulation. Gute Nacht!")

if __name__ == "__main__":
    main()