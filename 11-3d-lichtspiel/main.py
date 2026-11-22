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
    
    for y in range(height):
        for x in range(width):
            # Pixel → Weltkoordinate auf Ground‑Plane (z=0)
            wx = (x / (width - 1) - 0.5) * world_w
            wy = (y / (height - 1) - 0.5) * world_h
            wz = 0.0
            # View‑Richtung (normiert)
            vx, vy, vz = wx - cam_x, wy - cam_y, wz - cam_z
            vlen = math.hypot(vx, vy, vz)
            if vlen == 0:
                continue
            vx, vy, vz = vx / vlen, vy / vlen, vz / vlen
            
            acc = 0.0
            # Ray‑March von Kamera bis Ground‑Plane (und etwas darüber für Mist)
            for step in range(params.march_steps):
                t = step * step_size
                px = cam_x + vx * t
                py = cam_y + vy * t
                pz = cam_z + vz * t
                if pz < -0.5:  # unter Ground -> abbrechen
                    break
                # Vector zum Licht
                ldx, ldy, ldz = lx - px, ly - py, lz - pz
                ld = math.hypot(ldx, ldy, ldz)
                if ld < 0.01:
                    continue
                ldx, ldy, ldz = ldx / ld, ldy / ld, ldz / ld
                # Phase‑Funktion (View vs Light)
                cos_theta = vx * ldx + vy * ldy + vz * ldz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                # Abschwächung (Inverse Square + Absorption)
                attenuation = (1.0 / (ld * ld + 0.01)) * math.exp(-params.absorption_coeff * ld)
                # Schatten (2D‑Projection auf Ground, Bäume als Zylinder)
                shadow = schattenfaktor_für_punkt(px, py, lx, ly, max_dist, bäume, params)
                # Mist‑Dichte mit Height‑Falloff
                mist = params.mist_density * math.exp(-max(0.0, pz) * params.mist_height_falloff)
                # Jitter
                jitter = 1.0
                if params.jitter_enabled:
                    jitter += noise_3d(px * 0.5, py * 0.5, pz * 0.5, params.noise_seed + frame) * params.jitter_strength
                # Accumulate
                acc += phase * attenuation * shadow * mist * jitter * params.scattering_coeff * step_size
            
            # Ambient + Volumetric Gain
            acc = (acc + params.ambient) * params.volumetric_gain
            img[y][x] = acc
    
    # Blur (separable box)
    weights = gauß_gewichte(params.blur_radius)
    img = box_blur_1d(img, weights, True)
    img = box_blur_1d(img, weights, False)
    
    # Color‑Temperature & Gamma → ASCII
    rf, gf, bf = kelvin_to_rgb_factor(params.color_temp)
    ascii_lines = []
    for y in range(height):
        line = ''
        for x in range(width):
            val = img[y][x]
            # Einfache Farb‑Modulation (hier nur Helligkeit, aber Faktoren könnten für echte Farb‑ASCII genutzt werden)
            val = min(1.0, max(0.0, val)) ** params.gamma
            line += intensitaet_zu_ascii(val, params.gamma)
        ascii_lines.append(line)
    return ascii_lines


def main():
    params = ShaderParams()
    # Beispiel‑Bäume: (x, y, radius)
    bäume = [
        (-3.0, -2.0, 0.8),
        (2.5, 1.0, 0.6),
        (-1.5, 3.0, 0.7),
        (4.0, -3.5, 0.9),
        (0.0, 0.0, 0.5),
    ]
    licht = [0.0, 0.0, 5.0]  # Start‑Position
    frame = 0
    print("3D-Lichtspiel – Drücke Strg+C oder EOF zum Beenden.")
    print("Eingabe: x y z (Leerzeichen-getrennt) oder ENTER für nächsten Frame.")
    
    while True:
        # Render
        lines = render(params, bäume, licht, width=80, height=24, frame=frame)
        print('\n'.join(lines))
        print(f"Frame {frame} | Licht: {licht[0]:.2f} {licht[1]:.2f} {licht[2]:.2f}")
        
        # Input non-blocking? Wir nutzen select für Timeout, aber input() blockiert.
        # Einfache Variante: input() mit Try/Except.
        try:
            s = input("Lichtposition (x y z) oder ENTER: ").strip()
        except EOFError:
            print("\nTschüss!")
            break
        if not s:
            frame += 1
            continue
        parts = s.split()
        if len(parts) != 3:
            print("Bitte exakt drei Werte eingeben.")
            continue
        try:
            licht[0] = float(parts[0])
            licht[1] = float(parts[1])
            licht[2] = float(parts[2])
        except ValueError:
            print("Ungültige Zahlen.")
            continue
        frame += 1

if __name__ == "__main__":
    main()