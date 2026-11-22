import math, sys, random, unicodedata, time, select

class ShaderParams:
    """Container für alle einstellbaren Shader-Parameter mit Defaults."""
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
        self.march_steps = 32
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

def render(params: ShaderParams, bäume, licht_pos, width=80, height=24, frame=0):
    """Ray‑March vom Kamerapunkt (0,0,10) auf die Ground‑Plane z=0.
    Gibt Liste von ASCII‑Zeilen zurück."""
    # Float-Puffer für Helligkeit
    img = [[0.0 for _ in range(width)] for _ in range(height)]
    lx, ly, lz = licht_pos
    # Kamera fix über dem Park
    cam_x, cam_y, cam_z = 0.0, 0.0, 10.0
    # View‑Plane: x,y in [-5,5] (World‑Units)
    world_w, world_h = 10.0, 10.0 * height / width
    max_dist = 15.0
    step_size = max_dist / max(1, params.march_steps)
    
    # Vorberechnung: Schattenkarte für Ground-Plane (einmal pro Frame)
    # Wir nutzen die 2D-Schattenfunktion direkt während des Marching.
    
    # Jitter-Seed für dieses Frame
    jitter_seed = params.noise_seed + frame * 17
    
    # Lichtfarbe aus Farbtemperatur
    r_factor, g_factor, b_factor = kelvin_to_rgb_factor(params.color_temp)
    # Normiere so dass Grün = 1.0, dann wenden wir später an
    
    # Ground-Albedo
    ground_albedo = 0.3
    
    for iy in range(height):
        for ix in range(width):
            # Weltkoordinaten des Pixels auf der Ground-Plane
            wx = -world_w/2 + (ix + 0.5) * world_w / width
            wy = -world_h/2 + (iy + 0.5) * world_h / height
            
            # Ray-Direction von Kamera zum Ground-Punkt
            rx, ry, rz = wx - cam_x, wy - cam_y, 0.0 - cam_z
            ray_len = math.sqrt(rx*rx + ry*ry + rz*rz)
            rdx, rdy, rdz = rx/ray_len, ry/ray_len, rz/ray_len
            
            # View-Direction (von Sample zur Kamera) ist -ray_dir
            vdx, vdy, vdz = -rdx, -rdy, -rdz
            
            acc = 0.0  # akkumulierte Streuung
            # Marching entlang des Rays
            for step in range(params.march_steps):
                t = (step + 0.5) / params.march_steps  # Mitte des Steps
                # Jitter auf t anwenden
                if params.jitter_enabled:
                    jitter = noise_2d(ix * 0.1, iy * 0.1, jitter_seed + step) * params.jitter_strength / params.march_steps
                    t += jitter
                if t >= 1.0:
                    break
                # Sample-Position
                sx = cam_x + rdx * ray_len * t
                sy = cam_y + rdy * ray_len * t
                sz = cam_z + rdz * ray_len * t
                
                # Mist-Dichte mit Height-Falloff
                density = params.mist_density * math.exp(-sz * params.mist_height_falloff)
                if density <= 0.0:
                    continue
                
                # Lichtvektor vom Sample zur Lichtquelle
                ldx = lx - sx
                ldy = ly - sy
                ldz = lz - sz
                light_dist = math.sqrt(ldx*ldx + ldy*ldy + ldz*ldz)
                if light_dist < 0.001:
                    continue
                ldx /= light_dist
                ldy /= light_dist
                ldz /= light_dist
                
                # Schattenfaktor (2D, da Bäume vertikale Zylinder sind)
                light_dist_2d = math.hypot(sx - lx, sy - ly)
                shadow = schattenfaktor_für_punkt(sx, sy, lx, ly, light_dist_2d, bäume, params)
                if shadow <= 0.0:
                    continue
                
                # Phase-Funktion (Henyey-Greenstein)
                cos_theta = vdx*ldx + vdy*ldy + vdz*ldz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                
                # Absorption entlang des Lichtpfads (vereinfacht exponentiell)
                absorption = math.exp(-params.absorption_coeff * light_dist)
                
                # Streu-Beitrag dieses Steps
                # Lichtintensität fällt mit 1/r^2 ab
                light_intensity = 1.0 / (light_dist * light_dist + 1e-6)
                scatter = density * params.scattering_coeff * phase * light_intensity * shadow * absorption
                # Step-Größe in Welt-Einheiten
                step_world = ray_len / params.march_steps
                acc += scatter * step_world
            
            # Ground-Hit (t=1.0): diffusere Bodenreflexion
            # Bodenpunkt ist (wx, wy, 0)
            gdx = lx - wx
            gdy = ly - wy
            gdz = lz - 0.0
            glight_dist = math.sqrt(gdx*gdx + gdy*gdy + gdz*gdz)
            if glight_dist > 0.001:
                gdx /= glight_dist
                gdy /= glight_dist
                gdz /= glight_dist
                glight_dist_2d = math.hypot(wx - lx, wy - ly)
                gshadow = schattenfaktor_für_punkt(wx, wy, lx, ly, glight_dist_2d, bäume, params)
                gabsorption = math.exp(-params.absorption_coeff * glight_dist)
                glight_intensity = 1.0 / (glight_dist * glight_dist + 1e-6)
                ground = ground_albedo * glight_intensity * gshadow * gabsorption
                acc += ground
            
            # Ambient hinzufügen
            acc += params.ambient
            
            # Volumetric Gain
            acc *= params.volumetric_gain
            
            img[iy][ix] = acc
    
    # Box Blur (horizontal + vertical)
    if params.blur_radius > 0:
        gewichte = gauß_gewichte(params.blur_radius)
        img = box_blur_1d(img, gewichte, horizontal=True)
        img = box_blur_1d(img, gewichte, horizontal=False)
    
    # Gamma-Korrektur und Farbtemperatur anwenden, dann ASCII-Mapping
    ascii_lines = []
    for y in range(height):
        line_chars = []
        for x in range(width):
            val = img[y][x]
            # Gamma
            val = max(0.0, min(1.0, val)) ** params.gamma
            # Einfache Farbtemperatur: wir skalieren die Helligkeit nach Farbkanälen,
            # aber ASCII ist monochrom. Wir nutzen die Luminanz (grün dominiert).
            # Um die Farbe zu simulieren, könnten wir verschiedene Zeichen für RGB nutzen,
            # aber wir bleiben bei monochrom und nutzen den Grün-Faktor als Basis.
            # Hier einfach val * g_factor (normiert).
            val = val * g_factor
            ch = intensitaet_zu_ascii(val, gamma=1.0)  # gamma schon angewendet
            line_chars.append(ch)
        ascii_lines.append(''.join(line_chars))
    return ascii_lines

def main():
    # Standard-Parameter
    params = ShaderParams()
    # Ein paar Bäume im Park (x, y, radius)
    bäume = [
        (-3.0, -2.0, 0.4),
        (2.5, 1.5, 0.3),
        (-1.0, 3.0, 0.5),
        (4.0, -3.0, 0.35),
        (0.0, -4.0, 0.45),
        (-4.0, 2.0, 0.3),
    ]
    # Default-Lichtposition
    licht_pos = (0.0, 0.0, 5.0)
    frame = 0
    width, height = 80, 24
    
    print("3D-Lichtspiel – interaktiver volumetrischer Park (Strg+C oder EOF zum Beenden)")
    print("Gib Lichtposition als 'x y z' ein (z.B. '0 0 5'), Enter für Default.")
    
    while True:
        try:
            line = input("Lichtposition> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTschüss!")
            break
        if not line:
            # Default behalten
            pass
        else:
            parts = line.split()
            if len(parts) != 3:
                print("Bitte drei Zahlen eingeben.")
                continue
            try:
                lx, ly, lz = map(float, parts)
                licht_pos = (lx, ly, lz)
            except ValueError:
                print("Bitte drei Zahlen eingeben.")
                continue
        
        # Rendern
        ascii_frame = render(params, bäume, licht_pos, width, height, frame)
        # Bildschirm löschen (ANSI escape)
        print("\033[2J\033[H", end='')
        for row in ascii_frame:
            print(row)
        print(f"Frame {frame} | Licht: {licht_pos[0]:.1f} {licht_pos[1]:.1f} {licht_pos[2]:.1f}")
        frame += 1

if __name__ == "__main__":
    main()