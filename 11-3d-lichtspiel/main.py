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
        self.bloom_threshold = 0.6
        self.bloom_intensity = 0.45
        self.bloom_radius = 2
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
    rampe = " .:'-=+*#%@"
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
    """Berechnet den Schattenfaktor (0..1) für einen Punkt.
    Penumbra wird mit einer linearen Interpolation über die Breite
    des Lichtkegels modelliert."""
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
            cz = pz + uz * proj
            if 0.0 <= cz <= bh:
                crown_r = br * (1.3 if cz > bh * 0.35 else 0.45)
                d_sq = (dx - proj * ux) ** 2 + (dy - proj * uy) ** 2
                dist_axis = math.sqrt(max(0.0, d_sq))
                penumbra = max(0.05, params.penumbra_breite * (proj / max(0.1, dist_light)))
                if dist_axis < crown_r:
                    min_f = min(min_f, params.umbra_dunkelheit)
                elif dist_axis < crown_r + penumbra:
                    t = (dist_axis - crown_r) / penumbra
                    f = params.umbra_dunkelheit + t * (1.0 - params.umbra_dunkelheit)
                    min_f = min(min_f, f)
    return min_f

def anwenden_bloom(puffer, params):
    h, w = len(puffer), len(puffer[0])
    hell_puffer = [[0.0 for _ in range(w)] for __ in range(h)]
    thresh = params.bloom_threshold
    for y in range(h):
        for x in range(w):
            val = puffer[y][x]
            if val > thresh:
                hell_puffer[y][x] = val - thresh
    gewichte = gauß_gewichte(params.bloom_radius)
    blur_h = box_blur_1d(hell_puffer, gewichte, horizontal=True)
    blur_hv = box_blur_1d(blur_h, gewichte, horizontal=False)
    ergebnis = [[0.0 for _ in range(w)] for __ in range(h)]
    for y in range(h):
        for x in range(w):
            ergebnis[y][x] = puffer[y][x] + blur_hv[y][x] * params.bloom_intensity
    return ergebnis

def raymarch_szene(breite: int, hoehe: int, sonnen_azimut: float, sonnen_hoehe: float, params: ShaderParams):
    lx = 6.0 * math.cos(sonnen_azimut) * math.cos(sonnen_hoehe)
    ly = 6.0 * math.sin(sonnen_azimut) * math.cos(sonnen_hoehe)
    lz = 1.0 + 5.0 * math.sin(sonnen_hoehe)
    light_pos = (lx, ly, lz)
    light_color = kelvin_to_rgb_factor(params.color_temp)
    light_helligkeit = (light_color[0] + light_color[1] + light_color[2]) / 3.0

    baeume = [
        (-1.8, 3.2, 0.65, 3.2),
        (1.5, 4.0, 0.85, 3.8),
        (0.2, 5.5, 0.70, 3.5),
        (-2.5, 6.0, 0.90, 4.0),
        (2.8, 5.0, 0.75, 3.4)
    ]

    cam_pos = (0.0, -4.5, 1.8)
    cam_dir = (0.0, 1.0, -0.05)
    cam_right = (1.0, 0.0, 0.0)
    cam_up = (0.0, 0.05, 1.0)

    puffer = [[0.0 for _ in range(breite)] for __ in range(hoehe)]
    t_max = 10.0
    steps = max(4, params.march_steps)

    for py in range(hoehe):
        fy = (hoehe / 2.0 - py) / (hoehe / 2.0) * 0.6
        for px in range(breite):
            fx = (px - breite / 2.0) / (breite / 2.0) * 0.9
            rx = cam_dir[0] + fx * cam_right[0] + fy * cam_up[0]
            ry = cam_dir[1] + fx * cam_right[1] + fy * cam_up[1]
            rz = cam_dir[2] + fx * cam_right[2] + fy * cam_up[2]
            rlen = math.sqrt(rx * rx + ry * ry + rz * rz)
            rdx, rdy, rdz = rx / rlen, ry / rlen, rz / rlen

            t_ground = t_max
            if rdz < -1e-4:
                tg = -cam_pos[2] / rdz
                if tg > 0.0:
                    t_ground = min(t_max, tg)

            march_dist = min(t_max, t_ground)
            dt = march_dist / steps
            accum_light = 0.0
            transmittance = 1.0

            cos_theta = (rdx * (light_pos[0] - cam_pos[0]) +
                         rdy * (light_pos[1] - cam_pos[1]) +
                         rdz * (light_pos[2] - cam_pos[2]))
            cos_theta /= max(0.1, math.sqrt(sum((a - b)**2 for a, b in zip(light_pos, cam_pos))))
            phase = henyey_greenstein(cos_theta, params.phase_g)

            for s in range(steps):
                t = (s + 0.5) * dt
                pos = (cam_pos[0] + rdx * t, cam_pos[1] + rdy * t, cam_pos[2] + rdz * t)
                dichte = mist_dichte(pos, params)
                if dichte > 1e-4:
                    schatten = schattenfaktor_3d(pos, light_pos, baeume, params)
                    to_l = (light_pos[0] - pos[0], light_pos[1] - pos[1], light_pos[2] - pos[2])
                    dist_sq = to_l[0]**2 + to_l[1]**2 + to_l[2]**2
                    attenuation = 1.0 / (1.0 + 0.08 * dist_sq)
                    step_light = dichte * schatten * attenuation * phase * light_helligkeit * params.volumetric_gain
                    accum_light += step_light * transmittance * dt
                    extinction = (params.scattering_coeff + params.absorption_coeff) * dichte
                    transmittance *= math.exp(-extinction * dt)
                    if transmittance < params.early_exit_threshold:
                        break

            boden_wert = 0.0
            if t_ground < t_max:
                gx = cam_pos[0] + rdx * t_ground
                gy = cam_pos[1] + rdy * t_ground
                boden_schatten = schattenfaktor_3d((gx, gy, 0.01), light_pos, baeume, params)
                herbst_laub = 0.5 + 0.5 * noise_3d(gx * 1.5, gy * 1.5, 0.0, 99)
                boden_wert = (params.ambient + 0.65 * boden_schatten * herbst_laub) * transmittance

            hintergrund = params.ambient * (0.8 + 0.3 * math.sin(py / max(1, hoehe)))
            gesamtwert = accum_light + boden_wert + hintergrund * transmittance
            puffer[py][px] = gesamtwert

    final_puffer = anwenden_bloom(puffer, params)
    return final_puffer

def main():
    print("--- Fifos 3D-Lichtspiel im herbstlichen Park (Teil 82) ---")
    params = ShaderParams()
    sonnen_azimut = 0.9
    sonnen_hoehe = 0.45
    breite = 60
    hoehe = 20

    durchlauf = 0
    max_eingaben = 15

    while durchlauf < max_eingaben:
        durchlauf += 1
        puffer = raymarch_szene(breite, hoehe, sonnen_azimut, sonnen_hoehe, params)
        zeilen = []
        for y in range(hoehe):
            zeile = "".join(intensitaet_zu_ascii(puffer[y][x], gamma=params.gamma) for x in range(breite))
            zeilen.append(zeile)

        print("\n".join(zeilen))
        print(f"[Herbstlicht] Azimut: {math.degrees(sonnen_azimut):.1f}° | Höhe: {math.degrees(sonnen_hoehe):.1f}° | Nebeldichte: {params.mist_density:.2f} | Bloom: {params.bloom_intensity:.2f}")

        try:
            befehl = input("Fifos Traumbefehl (s=Sonne drehen, n=Nebel, b=Bloom, enter=weiter, q=Ende): ")
        except EOFError:
            print("Fifo nickt zufrieden ein. Auf Wiedersehen im Park!")
            break

        b = _norm(befehl)
        if b in ('q', 'ende', 'exit', 'nein'):
            print("Fifo schlägt die Augen auf und lauscht den fallenden Blättern. Bis zum nächsten Traum!")
            break
        elif 's' in b:
            sonnen_azimut += 0.35
            sonnen_hoehe = max(0.15, min(0.85, sonnen_hoehe + 0.08))
            print("Die goldene Herbstsonne wandert tiefer zwischen die Eichen.")
        elif 'n' in b:
            params.mist_density = 0.45 if params.mist_density < 0.3 else 0.15
            print(f"Ein Nebelschleier weht durch das Tal: Dichte nun {params.mist_density:.2f}.")
        elif 'b' in b:
            params.bloom_intensity = 0.0 if params.bloom_intensity > 0.1 else 0.55
            status = "ausgeschaltet" if params.bloom_intensity == 0.0 else "eingeschaltet"
            print(f"Lichtkrone und Bloom wurden {status}.")
        else:
            sonnen_azimut += 0.15

if __name__ == '__main__':
    main()