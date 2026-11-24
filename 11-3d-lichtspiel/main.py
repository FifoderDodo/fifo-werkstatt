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
                # Abstand vom Strahl zum Baumstamm
                rx = px + ux * proj - bx
                ry = py + uy * proj - by
                dist_radial = math.sqrt(rx * rx + ry * ry)
                if dist_radial < br:
                    # Hart schatten im Kern
                    core = br * 0.6
                    if dist_radial < core:
                        return params.umbra_dunkelheit
                    # Penumbra-Uebergang
                    t = (dist_radial - core) / (br - core)
                    t = max(0.0, min(1.0, t))
                    f = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * t
                    min_f = min(min_f, f)
    return min_f

def baum_silhouette(px, py, pz, light_pos, baeume, params):
    """Prüft ob ein Punkt im Schatten eines Baumes liegt (für Boden/Objekte)."""
    return schattenfaktor_3d((px, py, pz), light_pos, baeume, params) < 0.5

def render_frame(w, h, params, baeume, light_pos, cam_pos, cam_yaw, cam_pitch, t):
    """Rendert einen Frame mit Volumetric Lighting via Ray Marching."""
    # Vorberechnungen
    cos_yaw, sin_yaw = math.cos(cam_yaw), math.sin(cam_yaw)
    cos_pitch, sin_pitch = math.cos(cam_pitch), math.sin(cam_pitch)
    
    # Lichtfarbe
    lr, lg, lb = kelvin_to_rgb_factor(params.color_temp)
    
    # Jitter für Temporal Stability
    jitter_x = random.random() * params.jitter_strength if params.jitter_enabled else 0.0
    jitter_y = random.random() * params.jitter_strength if params.jitter_enabled else 0.0
    
    # Framebuffer für Luminanz
    luminance = [[0.0 for _ in range(w)] for __ in range(h)]
    
    max_dist = 25.0
    step_base = max_dist / params.march_steps
    
    for y in range(h):
        for x in range(w):
            # NDC Koordinaten
            ndc_x = (x + 0.5 + jitter_x) / w * 2.0 - 1.0
            ndc_y = (y + 0.5 + jitter_y) / h * 2.0 - 1.0
            
            # Aspect ratio correction
            aspect = w / h
            ndc_x *= aspect
            
            # Ray direction in world space
            # Forward vector
            fx = cos_pitch * cos_yaw
            fy = cos_pitch * sin_yaw
            fz = sin_pitch
            
            # Right vector
            rx = -sin_yaw
            ry = cos_yaw
            rz = 0.0
            
            # Up vector
            ux = -sin_pitch * cos_yaw
            uy = -sin_pitch * sin_yaw
            uz = cos_pitch
            
            # Ray direction
            fov = 1.0
            rdx = fx + ndc_x * fov * rx + ndc_y * fov * ux
            rdy = fy + ndc_x * fov * ry + ndc_y * fov * uy
            rdz = fz + ndc_x * fov * rz + ndc_y * fov * uz
            
            rlen = math.sqrt(rdx*rdx + rdy*rdy + rdz*rdz)
            rdx, rdy, rdz = rdx/rlen, rdy/rlen, rdz/rlen
            
            # Ray marching
            accum = 0.0
            transmittance = 1.0
            px, py, pz = cam_pos
            
            for step in range(params.march_steps):
                # Adaptive step size basierend auf Dichte
                if params.adaptive_steps:
                    d = mist_dichte((px, py, pz), params)
                    step_factor = params.min_step_factor + (params.max_step_factor - params.min_step_factor) * (1.0 - min(1.0, d * 5.0))
                    step_size = step_base * step_factor
                else:
                    step_size = step_base
                
                # Nächste Position
                px += rdx * step_size
                py += rdy * step_size
                pz += rdz * step_size
                
                # Dichte an Position
                density = mist_dichte((px, py, pz), params)
                if density < 1e-4:
                    continue
                
                # Lichtrichtung von Sample zu Licht
                ldx = light_pos[0] - px
                ldy = light_pos[1] - py
                ldz = light_pos[2] - pz
                ldist = math.sqrt(ldx*ldx + ldy*ldy + ldz*ldz)
                if ldist < 0.01:
                    continue
                ldx, ldy, ldz = ldx/ldist, ldy/ldist, ldz/ldist
                
                # Phase function (Henyey-Greenstein)
                cos_theta = rdx * ldx + rdy * ldy + rdz * ldz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                
                # Schattenfaktor
                shadow = schattenfaktor_3d((px, py, pz), light_pos, baeume, params)
                
                # Falloff
                falloff = 1.0 / (1.0 + (ldist * params.falloff_start) ** params.falloff_exponent)
                
                # Scattering contribution
                scatter = density * params.scattering_coeff * phase * falloff * shadow
                
                # Absorption
                absorption = density * params.absorption_coeff
                transmittance *= math.exp(-absorption * step_size)
                
                accum += scatter * transmittance * step_size
                
                # Early exit
                if transmittance < params.early_exit_threshold:
                    break
            
            # Ambient + Volumetric
            final_lum = (params.ambient + accum * params.volumetric_gain)
            
            # Specular highlight auf Nebel (fakes glitzernde Partikel)
            if params.specular_intensity > 0:
                # View direction zu Licht
                vdx = light_pos[0] - cam_pos[0]
                vdy = light_pos[1] - cam_pos[1]
                vdz = light_pos[2] - cam_pos[2]
                vlen = math.sqrt(vdx*vdx + vdy*vdy + vdz*vdz)
                if vlen > 0:
                    vdx, vdy, vdz = vdx/vlen, vdy/vlen, vdz/vlen
                    # Reflect view around normal (approximiert durch gradient)
                    grad = dichte_gradient((px, py, pz), params)
                    # Einfache Spekular-Approximation
                    spec = max(0.0, rdx*vdx + rdy*vdy + rdz*vdz) ** params.specular_power
                    final_lum += spec * params.specular_intensity * 0.1
            
            luminance[y][x] = final_lum
    
    # Bloom / Blur
    if params.blur_radius > 0:
        weights = gauß_gewichte(params.blur_radius)
        luminance = box_blur_1d(luminance, weights, True)
        luminance = box_blur_1d(luminance, weights, False)
    
    # Gamma & Vibrancy
    for y in range(h):
        for x in range(w):
            v = luminance[y][x]
            v = min(1.0, v * params.vibrancy) ** params.gamma
            luminance[y][x] = v
    
    return luminance

def generiere_baeume(anzahl, radius_bereich, hoehe_bereich, seed=123):
    """Generiert zufällige Bäume im Park."""
    random.seed(seed)
    baeume = []
    for _ in range(anzahl):
        x = random.uniform(-15, 15)
        y = random.uniform(-15, 15)
        r = random.uniform(*radius_bereich)
        h = random.uniform(*hoehe_bereich)
        baeume.append((x, y, r, h))
    return baeume

def main():
    print("🍂 3D-Lichtspiel – Herbstlicher Park bei Nacht")
    print("==============================================")
    print()
    
    # Parameter
    params = ShaderParams()
    
    # Szene
    baeume = generiere_baeume(12, (0.3, 0.6), (3.0, 5.0), 42)
    
    # Kamera
    cam_pos = [0.0, -8.0, 1.6]
    cam_yaw = 0.0
    cam_pitch = 0.15
    
    # Lichtquelle (bewegt sich)
    light_angle = 0.0
    light_height = 4.0
    light_radius = 6.0
    
    # Framebuffer Größe
    w, h = 80, 40
    
    print(f"Canvas: {w}x{h} | Bäume: {len(baeume)} | Steps: {params.march_steps}")
    print("Steuerung: [Enter]=weiter, [q]=quit, [p]=Parameter, [c]=Kamera, [l]=Licht")
    print()
    
    frame = 0
    try:
        while True:
            # Licht animieren
            light_angle += 0.02
            light_pos = (
                math.cos(light_angle) * light_radius,
                math.sin(light_angle) * light_radius,
                light_height + math.sin(light_angle * 0.7) * 0.5
            )
            
            # Render
            start = time.time()
            lum = render_frame(w, h, params, baeume, light_pos, cam_pos, cam_yaw, cam_pitch, frame)
            render_time = time.time() - start
            
            # ASCII Output
            print(f"\rFrame {frame:04d} | Light: ({light_pos[0]:.1f}, {light_pos[1]:.1f}, {light_pos[2]:.1f}) | {render_time*1000:.1f}ms", end='')
            for y in range(h):
                line = ''.join(intensitaet_zu_ascii(lum[y][x], params.gamma) for x in range(w))
                print(f"\n{line}", end='')
            print()
            
            frame += 1
            
            # Input
            try:
                cmd = input("\n> ").strip().lower()
            except EOFError:
                print("\n👋 Tschüss!")
                break
            
            if cmd in ('q', 'quit', 'exit'):
                print("👋 Gute Nacht!")
                break
            elif cmd == 'p':
                print(f"\nParameter: mist_density={params.mist_density}, volumetric_gain={params.volumetric_gain}, ")
                print(f"  scattering={params.scattering_coeff}, absorption={params.absorption_coeff}")
                print(f"  phase_g={params.phase_g}, march_steps={params.march_steps}")
                print(f"  blur_radius={params.blur_radius}, gamma={params.gamma}")
                try:
                    key = input("Parameter ändern (name=wert oder Enter): ").strip()
                    if '=' in key:
                        name, val = key.split('=', 1)
                        name = name.strip()
                        val = float(val.strip())
                        if hasattr(params, name):
                            setattr(params, name, val)
                            print(f"  {name} = {val}")
                        else:
                            print(f"  Unbekannt: {name}")
                except (ValueError, EOFError):
                    pass
            elif cmd == 'c':
                print(f"\nKamera: pos={cam_pos}, yaw={cam_yaw:.2f}, pitch={cam_pitch:.2f}")
                try:
                    inp = input("Neue yaw pitch (z.B. 0.5 0.2): ").strip()
                    if inp:
                        parts = inp.split()
                        if len(parts) >= 2:
                            cam_yaw = float(parts[0])
                            cam_pitch = max(-1.4, min(1.4, float(parts[1])))
                except (ValueError, EOFError):
                    pass
            elif cmd == 'l':
                print(f"\nLicht: radius={light_radius}, height={light_height}, angle={light_angle:.2f}")
                try:
                    inp = input("Neue radius height (z.B. 8 5): ").strip()
                    if inp:
                        parts = inp.split()
                        if len(parts) >= 2:
                            light_radius = float(parts[0])
                            light_height = float(parts[1])
                except (ValueError, EOFError):
                    pass
            elif cmd == 'r':
                # Reset
                params = ShaderParams()
                cam_pos = [0.0, -8.0, 1.6]
                cam_yaw = 0.0
                cam_pitch = 0.15
                light_angle = 0.0
                light_radius = 6.0
                light_height = 4.0
                print("🔄 Reset!")
            elif cmd == 'h' or cmd == 'help':
                print("\nBefehle:")
                print("  Enter - nächster Frame")
                print("  p     - Parameter anzeigen/ändern")
                print("  c     - Kamera anpassen")
                print("  l     - Licht anpassen")
                print("  r     - Reset")
                print("  h     - Hilfe")
                print("  q     - Beenden")
            # Sonst: nächster Frame
            
    except KeyboardInterrupt:
        print("\n👋 Unterbrochen. Schlaf gut!")

if __name__ == "__main__":
    main()