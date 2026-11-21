# 3D-Lichtspiel – Teil 11: Specular Highlights mit Blinn-Phong im Raymarching
# Fifo der Dodo poliert die Herbstluft – jetzt glitzern Staub und Tau im Lichtkegel.

import math
import sys
import random
import unicodedata
import time


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
        # NEU: Blinn-Phong Specular
        self.specular_intensity = 0.8
        self.specular_power = 32.0
        self.specular_noise_scale = 0.5
    
    def klonen(self):
        klon = ShaderParams()
        klon.__dict__.update(self.__dict__)
        return klon


def _norm(s: str) -> str:
    return unicodedata.normalize('NFC', s).strip().lower()


def gauß_gewichte(kernel_radius: int) -> list:
    size = kernel_radius * 2 + 1
    gewicht = 1.0 / size
    return [gewicht] * size


def box_blur_1d(puffer: list, gewichte: list, horizontal: bool = True) -> list:
    h = len(puffer)
    w = len(puffer[0])
    k_rad = len(gewichte) // 2
    ergebnis = [[0.0 for _ in range(w)] for __ in range(h)]
    
    if horizontal:
        for y in range(h):
            row_src = puffer[y]
            row_dst = ergebnis[y]
            for x in range(w):
                acc = 0.0
                for i, gew in enumerate(gewichte):
                    xi = x - k_rad + i
                    if 0 <= xi < w:
                        acc += row_src[xi] * gew
                row_dst[x] = acc
    else:
        for x in range(w):
            for y in range(h):
                acc = 0.0
                for i, gew in enumerate(gewichte):
                    yi = y - k_rad + i
                    if 0 <= yi < h:
                        acc += puffer[yi][x] * gew
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
    elif w > 0.65:
        return '#'
    elif w > 0.45:
        return '*'
    elif w > 0.25:
        return '+'
    elif w > 0.1:
        return '.'
    else:
        return ' '


def schattenfaktor_für_punkt(px: float, py: float, qx: float, qy: float, radius: float, 
                              bäume: list, params: ShaderParams) -> float:
    dx = px - qx
    dy = py - qy
    dist_q_p = math.hypot(dx, dy)
    
    if dist_q_p > radius or dist_q_p < 0.01:
        return 1.0
    
    ux = dx / dist_q_p
    uy = dy / dist_q_p
    
    min_shadow = 1.0
    
    for bx, by, bradius in bäume:
        vx = bx - qx
        vy = by - qy
        dist_q_b = math.hypot(vx, vy)
        
        if dist_q_b < 0.01:
            continue
        
        proj = vx * ux + vy * uy
        if proj <= 0.01 or proj >= dist_q_p:
            continue
        
        abstand_zu_strahl = abs(vx * uy - vy * ux)
        
        if abstand_zu_strahl >= bradius:
            continue
        
        schatten_radius_hier = bradius * (dist_q_p / dist_q_b)
        if schatten_radius_hier <= 0.0:
            continue
            
        rand_faktor = abstand_zu_strahl / schatten_radius_hier
        
        penumbra = params.penumbra_breite
        umbra = params.umbra_dunkelheit
        
        if rand_faktor < 1.0 - penumbra:
            faktor = umbra
        elif rand_faktor > 1.0 + penumbra:
            faktor = 1.0
        else:
            t = (rand_faktor - (1.0 - penumbra)) / (2.0 * penumbra)
            faktor = umbra + (1.0 - umbra) * t
        
        if faktor < min_shadow:
            min_shadow = faktor
            
    return min_shadow


def noise_2d(x: float, y: float, seed: int) -> float:
    """Einfaches deterministisches 2D-Rauschen (Integer-Hash)."""
    n = int(x * 123.45) ^ int(y * 678.91) ^ seed
    n = (n ^ (n >> 13)) * 0x5bd1e995
    n = (n ^ (n >> 15)) * 0x5bd1e995
    n = n ^ (n >> 15)
    return (n & 0x7fffffff) / 0x7fffffff * 2.0 - 1.0  # -1 bis 1


def noise_3d(x: float, y: float, z: float, seed: int) -> float:
    """3D-Rauschen für Specular-Variation (einfaches Hash-basiertes Value Noise)."""
    ix, iy, iz = int(x), int(y), int(z)
    fx, fy, fz = x - ix, y - iy, z - iz
    
    def hash3d(ix, iy, iz):
        n = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ seed
        n = (n ^ (n >> 13)) * 0x5bd1e995
        n = (n ^ (n >> 15)) * 0x5bd1e995
        n = n ^ (n >> 15)
        return (n & 0x7fffffff) / 0x7fffffff
    
    # Trilinear interpolation
    c000 = hash3d(ix, iy, iz)
    c100 = hash3d(ix + 1, iy, iz)
    c010 = hash3d(ix, iy + 1, iz)
    c110 = hash3d(ix + 1, iy + 1, iz)
    c001 = hash3d(ix, iy, iz + 1)
    c101 = hash3d(ix + 1, iy, iz + 1)
    c011 = hash3d(ix, iy + 1, iz + 1)
    c111 = hash3d(ix + 1, iy + 1, iz + 1)
    
    def lerp(a, b, t):
        return a + (b - a) * t
    
    u = fx * fx * (3.0 - 2.0 * fx)
    v = fy * fy * (3.0 - 2.0 * fy)
    w = fz * fz * (3.0 - 2.0 * fz)
    
    x0 = lerp(c000, c100, u)
    x1 = lerp(c010, c110, u)
    x2 = lerp(c001, c101, u)
    x3 = lerp(c011, c111, u)
    
    y0 = lerp(x0, x1, v)
    y1 = lerp(x2, x3, v)
    
    return lerp(y0, y1, w) * 2.0 - 1.0


def berechne_volumetrisch(breite: int, hoehe: int, quelle: tuple, radius: float, 
                          bäume: list, params: ShaderParams) -> list:
    """Raymarching für volumetrische Lichtkegel mit Schatten, Streuung, Falloff & Specular."""
    qx, qy = quelle
    rgb_factors = kelvin_to_rgb_factor(params.color_temp)
    
    # Shadow-Cache: Berechne Schattenfaktor pro Pixel einmal (2D)
    print("  Berechne Shadow-Map...")
    shadow_map = [[1.0 for _ in range(breite)] for __ in range(hoehe)]
    for y in range(hoehe):
        for x in range(breite):
            wx = (x - breite * 0.5) * 0.1
            wy = (y - hoehe * 0.5) * 0.1
            shadow_map[y][x] = schattenfaktor_für_punkt(wx, wy, qx, qy, radius, bäume, params)
    
    # Raymarching pro Pixel
    print("  Raymarching mit Blinn-Phong Specular...")
    ergebnis = [[0.0 for _ in range(breite)] for __ in range(hoehe)]
    
    # Kamera-Parameter: orthografisch, Blickrichtung -Z
    cam_z = -20.0
    max_dist = 40.0
    
    for y in range(hoehe):
        for x in range(breite):
            # Weltkoordinaten des Pixels (XY-Ebene)
            wx = (x - breite * 0.5) * 0.1
            wy = (y - hoehe * 0.5) * 0.1
            
            shadow = shadow_map[y][x]
            if shadow <= params.umbra_dunkelheit * 1.5:
                # Tiefer Schatten – wenig Volumetrik nötig
                ergebnis[y][x] = params.ambient * shadow
                continue
            
            # Raymarching entlang Z
            transmittance = 1.0
            accumulated = 0.0
            specular_accum = 0.0
            
            step_size = max_dist / params.march_steps
            
            # Jitter-Offset für dieses Pixel
            jitter = 0.0
            if params.jitter_enabled:
                jitter = noise_2d(x * 0.1, y * 0.1, params.noise_seed) * params.jitter_strength * step_size
            
            for step in range(params.march_steps):
                t = (step + 0.5) * step_size + jitter
                z = cam_z + t
                
                # Distanz zur Lichtquelle (3D)
                dx = wx - qx
                dy = wy - qy
                dz = z - 0.0  # Lichtquelle auf z=0
                dist_to_light = math.sqrt(dx*dx + dy*dy + dz*dz)
                
                if dist_to_light > radius:
                    continue
                
                # Falloff mit Start-Offset
                falloff_dist = max(dist_to_light - params.falloff_start, 0.001)
                falloff = 1.0 / (falloff_dist ** params.falloff_exponent)
                
                # Mist-Dichte mit Höhen-Abfall (z-Achse = Höhe)
                height_factor = math.exp(-abs(z) * params.mist_height_falloff)
                density = params.mist_density * height_factor
                
                # Transparenz (Absorption)
                transmittance *= math.exp(-params.absorption_coeff * density * step_size)
                if transmittance < 0.01:
                    break
                
                # Phase-Funktion (Henyey-Greenstein)
                # View dir: (0, 0, 1) - Kamera schaut entlang +Z
                # Light dir: von Sample zur Lichtquelle
                lx, ly, lz = -dx, -dy, -dz
                light_len = math.sqrt(lx*lx + ly*ly + lz*lz)
                if light_len > 0:
                    lx, ly, lz = lx/light_len, ly/light_len, lz/light_len
                cos_theta = lz  # View dir ist (0,0,1)
                phase = henyey_greenstein(cos_theta, params.phase_g)
                
                # Volumetrischer Streuungs-Beitrag
                scatter = density * phase * falloff * shadow * transmittance
                accumulated += scatter
                
                # NEU: Blinn-Phong Specular Highlights
                # Half-Vector zwischen View (0,0,1) und Light Dir
                hx = lx * 0.5
                hy = ly * 0.5
                hz = (lz + 1.0) * 0.5
                h_len = math.sqrt(hx*hx + hy*hy + hz*hz)
                if h_len > 0:
                    hx, hy, hz = hx/h_len, hy/h_len, hz/h_len
                    # N dot H (Normal ist View-Dir für isotrope Partikel, aber wir nutzen Noise für Variation)
                    # Verwende 3D-Noise als "Normalen-Störung" für Glitzer-Partikel
                    noise_val = noise_3d(wx * params.specular_noise_scale, 
                                         wy * params.specular_noise_scale, 
                                         z * params.specular_noise_scale, 
                                         params.noise_seed + 12345)
                    # Spekulare Normale: leicht gestört von View-Dir
                    nx = noise_val * 0.3
                    ny = noise_val * 0.3
                    nz = math.sqrt(max(0.0, 1.0 - nx*nx - ny*ny))
                    nh = nx*hx + ny*hy + nz*hz
                    if nh > 0:
                        spec = (nh ** params.specular_power) * params.specular_intensity
                        spec *= falloff * shadow * transmittance * density
                        specular_accum += spec
            
            # Kombiniere Volumetrik + Specular + Ambient
            total = (accumulated + specular_accum) * params.volumetric_gain + params.ambient * shadow
            ergebnis[y][x] = min(1.0, total)
    
    return ergebnis


def wende_blur_an(puffer: list, radius: int) -> list:
    if radius <= 0:
        return puffer
    gewichte = gauß_gewichte(radius)
    tmp = box_blur_1d(puffer, gewichte, horizontal=True)
    res = box_blur_1d(tmp, gewichte, horizontal=False)
    return res


def rendere_ascii(puffer: list, gamma: float) -> str:
    zeilen = []
    for row in puffer:
        zeile = ''.join(intensitaet_zu_ascii(v, gamma) for v in row)
        zeilen.append(zeile)
    return '\n'.join(zeilen)


def erstelle_demo_szene():
    """Erzeugt Beispieldaten: Lichtquelle, Bäume, Parameter."""
    quelle = (0.0, 0.0)
    radius = 15.0
    bäume = [
        (-5.0, -3.0, 1.2),
        (6.0, -2.0, 0.9),
        (-7.0, 4.0, 1.5),
        (4.0, 5.0, 1.0),
        (0.0, -8.0, 1.3),
        (-3.0, 7.0, 0.8),
        (8.0, 1.0, 1.1),
    ]
    params = ShaderParams()
    return quelle, radius, bäume, params


def menü_anzeigen(params: ShaderParams):
    print("\n=== 3D-Lichtspiel – Parameter ===")
    print(f"1) Penumbra-Breite:      {params.penumbra_breite:.2f}")
    print(f"2) Umbra-Dunkelheit:     {params.umbra_dunkelheit:.2f}")
    print(f"3) Falloff-Exponent:     {params.falloff_exponent:.2f}")
    print(f"4) Falloff-Start:        {params.falloff_start:.2f}")
    print(f"5) Blur-Radius:          {params.blur_radius}")
    print(f"6) Ambient:              {params.ambient:.3f}")
    print(f"7) Volumetric Gain:      {params.volumetric_gain:.2f}")
    print(f"8) Gamma:                {params.gamma:.2f}")
    print(f"9) Scattering Coeff:     {params.scattering_coeff:.2f}")
    print(f"10) Absorption Coeff:    {params.absorption_coeff:.2f}")
    print(f"11) Mist Density:        {params.mist_density:.2f}")
    print(f"12) Mist Height Falloff: {params.mist_height_falloff:.2f}")
    print(f"13) Color Temp (K):      {params.color_temp:.0f}")
    print(f"14) Jitter Strength:     {params.jitter_strength:.2f}")
    print(f"15) Phase g:             {params.phase_g:.2f}")
    print(f"16) March Steps:         {params.march_steps}")
    print(f"17) Specular Intensity:  {params.specular_intensity:.2f}")
    print(f"18) Specular Power:      {params.specular_power:.1f}")
    print(f"19) Specular Noise Scale:{params.specular_noise_scale:.2f}")
    print(f"20) JitterEnabled:       {params.jitter_enabled}")
    print("R) Rendern")
    print("Q) Beenden")


def parameter_eingabe(params: ShaderParams, wahl: str) -> bool:
    try:
        if wahl == '1':
            params.penumbra_breite = float(input("Penumbra-Breite (0.01-0.5): "))
        elif wahl == '2':
            params.umbra_dunkelheit = float(input("Umbra-Dunkelheit (0.0-0.5): "))
        elif wahl == '3':
            params.falloff_exponent = float(input("Falloff-Exponent (0.5-4.0): "))
        elif wahl == '4':
            params.falloff_start = float(input("Falloff-Start (0.0-5.0): "))
        elif wahl == '5':
            params.blur_radius = int(input("Blur-Radius (0-10): "))
        elif wahl == '6':
            params.ambient = float(input("Ambient (0.0-0.2): "))
        elif wahl == '7':
            params.volumetric_gain = float(input("Volumetric Gain (0.1-5.0): "))
        elif wahl == '8':
            params.gamma = float(input("Gamma (0.2-1.5): "))
        elif wahl == '9':
            params.scattering_coeff = float(input("Scattering Coeff (0.0-2.0): "))
        elif wahl == '10':
            params.absorption_coeff = float(input("Absorption Coeff (0.0-1.0): "))
        elif wahl == '11':
            params.mist_density = float(input("Mist Density (0.0-1.0): "))
        elif wahl == '12':
            params.mist_height_falloff = float(input("Mist Height Falloff (0.1-3.0): "))
        elif wahl == '13':
            params.color_temp = float(input("Color Temp Kelvin (1000-10000): "))
        elif wahl == '14':
            params.jitter_strength = float(input("Jitter Strength (0.0-0.5): "))
        elif wahl == '15':
            params.phase_g = float(input("Phase g (-0.9-0.9): "))
        elif wahl == '16':
            params.march_steps = int(input("March Steps (8-128): "))
        elif wahl == '17':
            params.specular_intensity = float(input("Specular Intensity (0.0-2.0): "))
        elif wahl == '18':
            params.specular_power = float(input("Specular Power (1-128): "))
        elif wahl == '19':
            params.specular_noise_scale = float(input("Specular Noise Scale (0.1-2.0): "))
        elif wahl == '20':
            val = input("JitterEnabled (j/n): ").strip().lower()
            params.jitter_enabled = val == 'j'
        else:
            return False
    except (ValueError, EOFError):
        print("Ungültige Eingabe.")
    return True


def main():
    print("🍂 3D-Lichtspiel – Teil 11: Blinn-Phong Specular Highlights 🍂")
    print("Fifo der Dodo lässt Herbststaub im Lichtkegel glitzern.\n")
    
    quelle, radius, bäume, params = erstelle_demo_szene()
    breite, hoehe = 80, 40
    
    while True:
        menü_anzeigen(params)
        try:
            wahl = input("\nWahl: ").strip().lower()
        except EOFError:
            print("\nTschüss! Der Dodo watschelt davon. 🦤")
            break
        
        if wahl in ('q', 'quit', 'exit'):
            print("\nTschüss! Der Dodo watschelt davon. 🦤")
            break
        elif wahl in ('r', 'render'):
            start = time.time()
            rohdaten = berechne_volumetrisch(breite, hoehe, quelle, radius, bäume, params)
            if params.blur_radius > 0:
                rohdaten = wende_blur_an(rohdaten, params.blur_radius)
            ascii_art = rendere_ascii(rohdaten, params.gamma)
            print("\n" + ascii_art)
            print(f"\nRenderzeit: {time.time() - start:.2f}s")
        elif parameter_eingabe(params, wahl):
            print("Parameter aktualisiert.")
        else:
            print("Unbekannter Befehl.")

if __name__ == "__main__":
    main()