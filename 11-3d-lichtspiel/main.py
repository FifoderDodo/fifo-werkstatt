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
        # Neu: Bloom / Leuchteffekt
        self.bloom_threshold = 0.6
        self.bloom_intensity = 0.45
        self.bloom_radius = 3
        # Neu: Raymarching-Optimierung
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
                dist_xy = math.hypot(cx - bx, cy - by)
                if dist_xy < br:
                    # Penumbra basierend auf Distanz zum Stammesrand
                    r_ratio = dist_xy / br
                    f = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * (r_ratio ** 2)
                    if f < min_f:
                        min_f = f
    return min_f

def raymarch_pixel(px, py, pz, vx, vy, vz, light_pos, baeume, params):
    """Raymarching für einen Pixel, gibt (r,g,b) zurück."""
    # Startpunkt etwas vor der Kamera
    ox, oy, oz = px, py, pz
    dx, dy, dz = vx, vy, vz
    # Lichtrichtung für Phase Function
    lx, ly, lz = light_pos
    # Länge des View-Rays (bis zum Boden oder max)
    max_dist = 30.0
    step = max_dist / params.march_steps
    if params.adaptive_steps:
        step *= params.min_step_factor
    
    transmittance = 1.0
    in_scatter = (0.0, 0.0, 0.0)
    dist_traveled = 0.0
    
    # Farbtemperatur des Lichts
    light_color = kelvin_to_rgb_factor(params.color_temp)
    
    for i in range(params.march_steps):
        if params.adaptive_steps and transmittance < params.early_exit_threshold:
            break
        # Position entlang des Rays
        sx = ox + dx * dist_traveled
        sy = oy + dy * dist_traveled
        sz = oz + dz * dist_traveled
        
        # Dichte an dieser Stelle
        density = mist_dichte((sx, sy, sz), params)
        if density > 0.0:
            # Schattenfaktor
            shadow = schattenfaktor_3d((sx, sy, sz), light_pos, baeume, params)
            # Lichtrichtung von Sample zu Licht
            lvx = lx - sx
            lvy = ly - sy
            lvz = lz - sz
            ld = math.sqrt(lvx*lvx + lvy*lvy + lvz*lvz)
            if ld > 1e-5:
                lvx, lvy, lvz = lvx/ld, lvy/ld, lvz/ld
                # Phase Function (Henyey-Greenstein)
                cos_theta = dx*lvx + dy*lvy + dz*lvz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                # Falloff
                falloff = 1.0 / (ld*ld + 0.01)
                if ld > params.falloff_start:
                    falloff *= (params.falloff_start / ld) ** params.falloff_exponent
                # Streuung
                scatter = density * params.scattering_coeff * phase * falloff * shadow
                # Absorption
                absorb = density * params.absorption_coeff
                transmittance *= math.exp(-absorb * step)
                # In-Scattering addieren
                in_scatter = (
                    in_scatter[0] + light_color[0] * scatter * transmittance * step,
                    in_scatter[1] + light_color[1] * scatter * transmittance * step,
                    in_scatter[2] + light_color[2] * scatter * transmittance * step
                )
        dist_traveled += step
        if params.adaptive_steps:
            # Schrittweite anpassen basierend auf Dichte
            step = max(step * params.max_step_factor, max_dist * params.min_step_factor)
    
    # Volumetric Gain
    in_scatter = (in_scatter[0] * params.volumetric_gain,
                  in_scatter[1] * params.volumetric_gain,
                  in_scatter[2] * params.volumetric_gain)
    # Ambient
    in_scatter = (in_scatter[0] + params.ambient * light_color[0],
                  in_scatter[1] + params.ambient * light_color[1],
                  in_scatter[2] + params.ambient * light_color[2])
    return in_scatter

def render_frame(width, height, params, baeume, light_pos, cam_pos, cam_dir, fov=60.0):
    """Rendert einen Frame in einen Float-RGB-Puffer."""
    aspect = width / height
    fov_rad = math.radians(fov)
    # Kamera-Basisvektoren
    forward = cam_dir
    right = (forward[2], 0.0, -forward[0])  # vereinfacht, annahme: forward.y == 0
    rlen = math.sqrt(right[0]*right[0] + right[2]*right[2])
    if rlen < 1e-5:
        right = (1.0, 0.0, 0.0)
    else:
        right = (right[0]/rlen, 0.0, right[2]/rlen)
    up = (0.0, 1.0, 0.0)
    
    buffer = [[(0.0,0.0,0.0) for _ in range(width)] for __ in range(height)]
    
    for y in range(height):
        for x in range(width):
            # NDC Koordinaten
            ndc_x = (x + 0.5) / width * 2.0 - 1.0
            ndc_y = 1.0 - (y + 0.5) / height * 2.0
            # Ray Direction
            ray_x = right[0] * ndc_x * aspect * math.tan(fov_rad/2) + forward[0] * ndc_y * math.tan(fov_rad/2) + forward[0]
            ray_y = ndc_y * math.tan(fov_rad/2) + forward[1]
            ray_z = right[2] * ndc_x * aspect * math.tan(fov_rad/2) + forward[2] * ndc_y * math.tan(fov_rad/2) + forward[2]
            rlen = math.sqrt(ray_x*ray_x + ray_y*ray_y + ray_z*ray_z)
            ray_x, ray_y, ray_z = ray_x/rlen, ray_y/rlen, ray_z/rlen
            
            # Jitter für Temporal AA
            if params.jitter_enabled:
                jitter = params.jitter_strength * (random.random() - 0.5)
                ray_x += jitter
                ray_y += jitter
                ray_z += jitter
                rlen = math.sqrt(ray_x*ray_x + ray_y*ray_y + ray_z*ray_z)
                ray_x, ray_y, ray_z = ray_x/rlen, ray_y/rlen, ray_z/rlen
            
            color = raymarch_pixel(cam_pos[0], cam_pos[1], cam_pos[2],
                                   ray_x, ray_y, ray_z,
                                   light_pos, baeume, params)
            buffer[y][x] = color
    return buffer

def bloom_pass(buffer, params):
    """Einfacher Bloom: Threshold -> Blur -> Add."""
    h, w = len(buffer), len(buffer[0])
    # Luminanz extrahieren
    lum = [[0.0]*w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            r,g,b = buffer[y][x]
            lum[y][x] = 0.2126*r + 0.7152*g + 0.0722*b
    # Threshold
    for y in range(h):
        for x in range(w):
            if lum[y][x] < params.bloom_threshold:
                lum[y][x] = 0.0
            else:
                lum[y][x] = (lum[y][x] - params.bloom_threshold) * params.bloom_intensity
    # Blur
    weights = gauß_gewichte(params.bloom_radius)
    lum = box_blur_1d(lum, weights, True)
    lum = box_blur_1d(lum, weights, False)
    # Add back
    for y in range(h):
        for x in range(w):
            r,g,b = buffer[y][x]
            l = lum[y][x]
            buffer[y][x] = (r + l, g + l, b + l)
    return buffer

def tonemap(buffer, params):
    """Reinhard Tonemapping + Gamma + Vibrancy."""
    h, w = len(buffer), len(buffer[0])
    for y in range(h):
        for x in range(w):
            r,g,b = buffer[y][x]
            # Vibrancy: Sättigung erhöhen
            avg = (r+g+b)/3.0
            r = avg + (r - avg) * params.vibrancy
            g = avg + (g - avg) * params.vibrancy
            b = avg + (b - avg) * params.vibrancy
            # Reinhard
            r = r / (1.0 + r)
            g = g / (1.0 + g)
            b = b / (1.0 + b)
            # Gamma
            r = r ** params.gamma
            g = g ** params.gamma
            b = b ** params.gamma
            buffer[y][x] = (r,g,b)
    return buffer

def buffer_to_ascii(buffer, params):
    """Konvertiert RGB-Buffer in ASCII-Zeilen."""
    lines = []
    for row in buffer:
        line = ''
        for r,g,b in row:
            # Luminanz
            lum = 0.2126*r + 0.7152*g + 0.0722*b
            line += intensitaet_zu_ascii(lum, params.gamma)
        lines.append(line)
    return lines

def main():
    random.seed(12345)
    params = ShaderParams()
    
    # Szene: Bäume (x, y, radius, height)
    baeume = [
        (-3.0, -2.0, 0.5, 4.0),
        (4.0, 3.0, 0.7, 5.0),
        (-5.0, 5.0, 0.6, 3.5),
        (2.0, -4.0, 0.4, 3.0),
        (0.0, 6.0, 0.8, 6.0),
        (-7.0, -1.0, 0.5, 4.5),
    ]
    light_pos = (0.0, 0.0, 8.0)
    cam_pos = (0.0, -10.0, 2.0)
    cam_dir = (0.0, 1.0, -0.2)  # leicht nach unten
    clen = math.sqrt(cam_dir[0]**2 + cam_dir[1]**2 + cam_dir[2]**2)
    cam_dir = (cam_dir[0]/clen, cam_dir[1]/clen, cam_dir[2]/clen)
    
    width, height = 80, 40
    
    print("3D-Lichtspiel – Volumetrisches Licht im herbstlichen Park")
    print("Drücke Enter für nächsten Frame, 'q' zum Beenden.")
    print("Parameter: [p] Penumbra, [u] Umbra, [g] Gain, [m] Mist, [b] Bloom")
    
    frame = 0
    try:
        while True:
            # Leichtes Wackeln der Lichtquelle
            light_pos = (math.sin(frame*0.07)*1.5, math.cos(frame*0.05)*1.5, 8.0)
            
            buffer = render_frame(width, height, params, baeume, light_pos, cam_pos, cam_dir)
            buffer = bloom_pass(buffer, params)
            buffer = tonemap(buffer, params)
            ascii_lines = buffer_to_ascii(buffer, params)
            
            # Clear screen (ANSI)
            print("\033[H\033[J", end='')
            for line in ascii_lines:
                print(line)
            print(f"Frame: {frame}  Licht: ({light_pos[0]:.1f},{light_pos[1]:.1f},{light_pos[2]:.1f})")
            print("Befehle: [Enter] weiter, [q] quit, [p/u/g/m/b] Parameter ändern")
            
            inp = input().strip().lower()
            if inp == 'q':
                break
            elif inp == 'p':
                try:
                    val = float(input("Penumbra-Breite (0.05-0.5): "))
                    params.penumbra_breite = max(0.05, min(0.5, val))
                except:
                    pass
            elif inp == 'u':
                try:
                    val = float(input("Umbra-Dunkelheit (0.0-0.5): "))
                    params.umbra_dunkelheit = max(0.0, min(0.5, val))
                except:
                    pass
            elif inp == 'g':
                try:
                    val = float(input("Volumetric Gain (0.5-5.0): "))
                    params.volumetric_gain = max(0.5, min(5.0, val))
                except:
                    pass
            elif inp == 'm':
                try:
                    val = float(input("Mist-Dichte (0.05-0.5): "))
                    params.mist_density = max(0.05, min(0.5, val))
                except:
                    pass
            elif inp == 'b':
                try:
                    val = float(input("Bloom-Intensity (0.0-1.0): "))
                    params.bloom_intensity = max(0.0, min(1.0, val))
                except:
                    pass
            frame += 1
    except EOFError:
        pass
    print("\nDodo schläft weiter... Gute Nacht!")

if __name__ == "__main__":
    main()