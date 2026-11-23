import math, sys, random, unicodedata, time, select

class ShaderParams:
    """Container für alle einstellbaren Shader‑Parameter mit Defaults."""
    def __init__(self):
        self.penumbra_breite = 0.15
        self.umbra_dunkelheit = 0.05
        self.falloff_exponent = 2.0
        self.falloff_start = 0.5
        self.blur_radius = 3
        self.ambient = 0.05
        self.volumetric_gain = 2.5
        self.gamma = 0.55
        self.scattering_coeff = 0.45
        self.absorption_coeff = 0.08
        self.mist_density = 0.22
        self.mist_height_falloff = 0.8
        self.color_temp = 3000.0
        self.jitter_strength = 0.12
        self.phase_g = 0.6
        self.noise_seed = 42
        self.march_steps = 12  # reduziert für bessere Performance
        self.jitter_enabled = True
        self.specular_intensity = 0.6
        self.specular_power = 24.0
        self.specular_noise_scale = 0.5
        self.light_radius = 0.8
        self.vibrancy = 1.2  # Neu: Farb-Vibranz (1.0 = neutral)
    def klonen(self):
        k = ShaderParams()
        k.__dict__.update(self.__dict__)
        return k

def _norm(s: str) -> str:
    return unicodedata.normalize('NFC', s).strip().lower()

def gauß_gewichte(kernel_radius: int) -> list:
    size = kernel_radius * 2 + 1
    sigma = kernel_radius / 2.0
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

def schattenfaktor_für_punkt(px, py, qx, qy, light_radius, bäume, params):
    dx, dy = px - qx, py - qy
    dist_lp = math.hypot(dx, dy)
    if dist_lp < 0.01:
        return 1.0
    ux, uy = dx / dist_lp, dy / dist_lp
    min_faktor = 1.0
    for bx, by, br in bäume:
        vx, vy = bx - qx, by - qy
        dist_lt = math.hypot(vx, vy)
        if dist_lt < 0.01:
            continue
        proj = vx * ux + vy * uy
        if proj <= 0.01 or proj >= dist_lp:
            continue
        abstand = abs(vx * uy - vy * ux)
        factor = dist_lp / dist_lt
        penumbra_radius = br * factor + light_radius * (factor - 1.0)
        umbra_radius = max(0.0, br * factor - light_radius * (factor - 1.0))
        if abstand >= penumbra_radius:
            continue
        if abstand <= umbra_radius:
            faktor = params.umbra_dunkelheit
        else:
            t = (abstand - umbra_radius) / (penumbra_radius - umbra_radius) if penumbra_radius > umbra_radius else 0.0
            t = max(0.0, min(1.0, t))
            faktor = params.umbra_dunkelheit + (1.0 - params.umbra_dunkelheit) * t
        if faktor < min_faktor:
            min_faktor = faktor
    return min_faktor

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
    u = fx * fx * (3.0 - 2.0 * fx)
    v = fy * fy * (3.0 - 2.0 * fy)
    w = fz * fz * (3.0 - 2.0 * fz)
    a = hash3d(ix, iy, iz)
    b = hash3d(ix + 1, iy, iz)
    c = hash3d(ix, iy + 1, iz)
    d = hash3d(ix + 1, iy + 1, iz)
    e = hash3d(ix, iy, iz + 1)
    f = hash3d(ix + 1, iy, iz + 1)
    g = hash3d(ix, iy + 1, iz + 1)
    h = hash3d(ix + 1, iy + 1, iz + 1)
    x1 = a + (b - a) * u
    x2 = c + (d - c) * u
    y1 = x1 + (x2 - x1) * v
    x3 = e + (f - e) * u
    x4 = g + (h - g) * u
    y2 = x3 + (x4 - x3) * v
    return y1 + (y2 - y1) * w

def erstelle_szene(params, breite=80, höhe=40):
    """Generiert Bäume und Lichtposition für den Park."""
    random.seed(params.noise_seed)
    bäume = []
    for _ in range(12):
        bx = random.uniform(5, breite - 5)
        by = random.uniform(5, höhe - 5)
        br = random.uniform(1.5, 3.0)
        bäume.append((bx, by, br))
    # Lichtquelle leicht versetzt oben mittig
    lx = breite * 0.5 + random.uniform(-2, 2)
    ly = höhe * 0.2 + random.uniform(-1, 1)
    return bäume, (lx, ly)

def render_frame(params, breite=80, höhe=40):
    """Raymarching für jeden Pixel, gibt 2D-Array von Farbwerten (r,g,b) zurück."""
    bäume, (lx, ly) = erstelle_szene(params, breite, höhe)
    # Farbtemperatur-Faktor
    r_factor, g_factor, b_factor = kelvin_to_rgb_factor(params.color_temp)
    # Vorberechnete Gauß-Gewichte für optionalen Blur
    gewichte = gauß_gewichte(params.blur_radius) if params.blur_radius > 0 else None
    
    farb_puffer = [[(0.0, 0.0, 0.0) for _ in range(breite)] for __ in range(höhe)]
    
    for y in range(höhe):
        for x in range(breite):
            # Pixel-Koordinaten in Weltraum (0..breite, 0..höhe)
            px = x + 0.5
            py = y + 0.5
            # Richtung vom Pixel zum Licht (2D), wir raymarchen in 3D mit fester Höhe
            # Wir vereinfachen: Raymarching entlang der Sichtlinie (Kamera von oben?)
            # Stattdessen simulieren wir volumetrisches Licht durch Integration entlang der Linie zum Licht.
            # Für ASCII-Renderer nutzen wir eine 2D-Schatten/Streuung-Näherung.
            # Hier implementieren wir einen einfachen Raymarch vom Pixel zum Licht.
            dx = lx - px
            dy = ly - py
            dist = math.hypot(dx, dy)
            if dist < 0.01:
                # Direkt an der Lichtquelle
                color = (1.0, 1.0, 1.0)
            else:
                steps = params.march_steps
                step_len = dist / steps
                ux, uy = dx / dist, dy / dist
                # Start mit Jitter
                t = 0.0
                if params.jitter_enabled:
                    t = random.uniform(0, step_len) * params.jitter_strength
                transmittance = 1.0
                in_scatter = (0.0, 0.0, 0.0)
                for i in range(steps):
                    # Position entlang des Strahls
                    sx = px + ux * t
                    sy = py + uy * t
                    sz = 0.5  # feste Höhe für Mist
                    # Dichte mit Höhenabhängigkeit und 3D-Noise
                    noise_val = noise_3d(sx * 0.1, sy * 0.1, sz * 0.1, params.noise_seed)
                    density = params.mist_density * (1.0 + noise_val * 0.5) * math.exp(-sz * params.mist_height_falloff)
                    # Schattenfaktor an dieser Position
                    shadow = schattenfaktor_für_punkt(sx, sy, lx, ly, params.light_radius, bäume, params)
                    # Phasenfunktion (Henyey-Greenstein) - Winkel zwischen Blick- und Lichtrichtung
                    # Blickrichtung ist von Kamera (oben) nach unten, Lichtrichtung zum Licht.
                    # Vereinfacht: cos_theta = 1.0 (forward scattering)
                    cos_theta = 1.0
                    phase = henyey_greenstein(cos_theta, params.phase_g)
                    # Extinktion
                    extinction = (params.scattering_coeff + params.absorption_coeff) * density
                    transmittance *= math.exp(-extinction * step_len)
                    # In-Scattering
                    scatter_contrib = params.scattering_coeff * density * phase * shadow * transmittance
                    # Lichtfarbe mit Temperatur
                    light_color = (r_factor, g_factor, b_factor)
                    in_scatter = (
                        in_scatter[0] + scatter_contrib * light_color[0],
                        in_scatter[1] + scatter_contrib * light_color[1],
                        in_scatter[2] + scatter_contrib * light_color[2]
                    )
                    t += step_len
                # Spekulare Highlights (einfaches Rauschen basiert)
                spec_noise = noise_2d(px * params.specular_noise_scale, py * params.specular_noise_scale, params.noise_seed)
                spec = max(0.0, spec_noise) ** params.specular_power * params.specular_intensity
                # Gesamtfarbe
                ambient = params.ambient
                color = (
                    (in_scatter[0] + ambient + spec) * params.volumetric_gain,
                    (in_scatter[1] + ambient + spec) * params.volumetric_gain,
                    (in_scatter[2] + ambient + spec) * params.volumetric_gain
                )
            # Gamma-Korrektur und Vibranz anwenden
            gamma = params.gamma
            vib = params.vibrancy
            # Vibranz: Erhöhe Sättigung, indem wir die Luminanz beibehalten und Farbkanäle um Luminanz skalieren
            lum = 0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]
            color = (
                lum + (color[0] - lum) * vib,
                lum + (color[1] - lum) * vib,
                lum + (color[2] - lum) * vib
            )
            # Gamma
            color = (color[0] ** gamma, color[1] ** gamma, color[2] ** gamma)
            # Clamp
            color = (min(1.0, max(0.0, color[0])), min(1.0, max(0.0, color[1])), min(1.0, max(0.0, color[2])))
            farb_puffer[y][x] = color
    
    # Optionaler Blur auf Luminanz (für weichere Kanten)
    if gewichte:
        # Extrahiere Luminanz, blur, dann wieder auf Farbkanäle anwenden (vereinfachter Blur)
        lum_puffer = [[0.2126*c[0]+0.7152*c[1]+0.0722*c[2] for c in row] for row in farb_puffer]
        lum_blur_h = box_blur_1d(lum_puffer, gewichte, True)
        lum_blur = box_blur_1d(lum_blur_h, gewichte, False)
        # Mische Original mit geblurrter Luminanz (50/50)
        for y in range(höhe):
            for x in range(breite):
                orig_lum = 0.2126*farb_puffer[y][x][0]+0.7152*farb_puffer[y][x][1]+0.0722*farb_puffer[y][x][2]
                new_lum = 0.5 * orig_lum + 0.5 * lum_blur[y][x]
                if orig_lum > 0:
                    ratio = new_lum / orig_lum
                    farb_puffer[y][x] = (
                        farb_puffer[y][x][0] * ratio,
                        farb_puffer[y][x][1] * ratio,
                        farb_puffer[y][x][2] * ratio
                    )
    return farb_puffer

def farb_puffer_zu_ascii(farb_puffer, params):
    """Wandelt Farbpuffer in ASCII-Art um (Luminanz)."""
    ascii_zeilen = []
    for row in farb_puffer:
        zeile = ''
        for r, g, b in row:
            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
            zeile += intensitaet_zu_ascii(lum, params.gamma)
        ascii_zeilen.append(zeile)
    return '\n'.join(ascii_zeilen)

def parameter_menü_zeigen(params):
    print("\n=== Parameter (aktuelle Werte) ===")
    attrs = [a for a in dir(params) if not a.startswith('_') and not callable(getattr(params, a))]
    for a in attrs:
        print(f"  {a}: {getattr(params, a)}")
    print("Befehle: set <name> <wert>, reset, render, quit")

def main():
    params = ShaderParams()
    breite, höhe = 80, 40
    print("3D-Lichtspiel - Volumetrischer Herbstpark (ASCII)")
    print("Drücke Enter für Render, 'h' für Hilfe, 'q' zum Beenden.")
    
    while True:
        try:
            # Frame rendern
            farb_puffer = render_frame(params, breite, höhe)
            ascii_art = farb_puffer_zu_ascii(farb_puffer, params)
            print(ascii_art)
            
            # Eingabe
            print("\n[Enter=Neuer Frame, h=Hilfe, p=Parameter, q=Quit]", end=' ', flush=True)
            inp = sys.stdin.readline()
            if not inp:
                break
            inp = inp.strip().lower()
            if inp == '' or inp == 'render':
                continue
            if inp in ('q', 'quit', 'exit'):
                break
            if inp in ('h', 'help'):
                print("Befehle: [Enter] neuer Frame, p Parameter anzeigen/setzen, r reset, q quit")
                continue
            if inp == 'p':
                parameter_menü_zeigen(params)
                continue
            if inp == 'r':
                params = ShaderParams()
                print("Parameter zurückgesetzt.")
                continue
            if inp.startswith('set '):
                parts = inp.split()
                if len(parts) == 3:
                    name, val_str = parts[1], parts[2]
                    if hasattr(params, name):
                        try:
                            val = float(val_str)
                            setattr(params, name, val)
                            print(f"{name} = {val}")
                        except ValueError:
                            print("Ungültiger Zahlenwert.")
                    else:
                        print(f"Unbekannter Parameter: {name}")
                else:
                    print("Format: set <name> <wert>")
                continue
            print(f"Unbekannter Befehl: {inp}")
        except KeyboardInterrupt:
            break
        except EOFError:
            break
    print("\nTschüss! Der Dodo watschelt davon.")

if __name__ == '__main__':
    main()