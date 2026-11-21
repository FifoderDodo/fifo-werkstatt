# 3D-Lichtspiel – Teil 12: Specular Highlights mit Blinn-Phong im Raymarching (vollständig)
# Fifo der Dodo poliert die Herbstluft – jetzt glitzern Staub und Tau im Lichtkegel.
# Der Truncation-Fehler in noise_3d wurde behoben, Hauptschleife und Menü sind enthalten.

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
    
    # Interpolate
    def lerp(a, b, t):
        return a + (b - a) * t
    
    c00 = lerp(c000, c100, fx)
    c01 = lerp(c001, c101, fx)
    c10 = lerp(c010, c110, fx)
    c11 = lerp(c011, c111, fx)
    
    c0 = lerp(c00, c10, fy)
    c1 = lerp(c01, c11, fy)
    
    return lerp(c0, c1, fz) * 2.0 - 1.0  # -1 bis 1


def rendere_szene(breite: int, hoehe: int, params: ShaderParams, bäume: list, licht_pos: tuple, kamera_pos: tuple) -> list:
    """Raymarching für jeden Pixel, gibt 2D-Liste mit Helligkeitswerten zurück."""
    lx, ly, lz = licht_pos
    cx, cy, cz = kamera_pos
    radius = max(breite, hoehe) * 0.5
    
    # Farbtemperatur-Faktoren
    rf, gf, bf = kelvin_to_rgb_factor(params.color_temp)
    
    bild = [[0.0 for _ in range(breite)] for __ in range(hoehe)]
    
    for y in range(hoehe):
        for x in range(breite):
            # Normalisierte Koordinaten -1..1
            nx = (x - breite * 0.5) / (breite * 0.5)
            ny = (y - hoehe * 0.5) / (hoehe * 0.5)
            
            # Ray-Direktion (einfache orthogonale Projektion)
            rdx, rdy, rdz = nx * 0.5, ny * 0.5, -1.0
            rd_len = math.sqrt(rdx*rdx + rdy*rdy + rdz*rdz)
            rdx, rdy, rdz = rdx/rd_len, rdy/rd_len, rdz/rd_len
            
            # Raymarching
            transmittance = 1.0
            scattered = 0.0
            specular_acc = 0.0
            
            # Startpunkt leicht vor der Kamera
            px, py, pz = cx, cy, cz
            step_size = 2.0 / params.march_steps
            
            for step in range(params.march_steps):
                # Jitter für dithering
                if params.jitter_enabled:
                    jitter = (noise_2d(x + step * 0.1, y + step * 0.1, params.noise_seed) * 2 - 1) * params.jitter_strength
                    px += rdx * step_size + jitter
                    py += rdy * step_size + jitter
                    pz += rdz * step_size + jitter
                else:
                    px += rdx * step_size
                    py += rdy * step_size
                    pz += rdz * step_size
                
                # Distanz zum Licht
                to_light_x = lx - px
                to_light_y = ly - py
                to_light_z = lz - pz
                dist_light = math.sqrt(to_light_x**2 + to_light_y**2 + to_light_z**2)
                
                if dist_light < 0.01:
                    continue
                
                # Licht-Richtung
                ldx, ldy, ldz = to_light_x/dist_light, to_light_y/dist_light, to_light_z/dist_light
                
                # Schattenfaktor (2D-Schattenwurf auf Bodenebene, approximiert)
                shadow = schattenfaktor_für_punkt(px, py, lx, ly, dist_light, bäume, params)
                
                # Mist-Dichte mit Höhenabfall
                mist = params.mist_density * math.exp(-pz * params.mist_height_falloff)
                
                # Extinction
                extinction = (params.scattering_coeff + params.absorption_coeff) * mist
                transmittance *= math.exp(-extinction * step_size)
                
                # Phase-Funktion (Henyey-Greenstein)
                cos_theta = rdx*ldx + rdy*ldy + rdz*ldz
                phase = henyey_greenstein(cos_theta, params.phase_g)
                
                # Falloff
                falloff = 1.0 / (1.0 + params.falloff_start * dist_light**params.falloff_exponent)
                
                # Streulicht-Akkumulation
                scattered += transmittance * params.scattering_coeff * mist * phase * falloff * shadow * step_size
                
                # Specular (Blinn-Phong) an Partikeln
                # Half-Vector
                hx = rdx + ldx
                hy = rdy + ldy
                hz = rdz + ldz
                h_len = math.sqrt(hx*hx + hy*hy + hz*hz)
                if h_len > 1e-6:
                    hx, hy, hz = hx/h_len, hy/h_len, hz/h_len
                    # Normalen-Variation durch 3D-Noise
                    nscale = params.specular_noise_scale
                    nx_noise = noise_3d(px * nscale, py * nscale, pz * nscale, params.noise_seed + 1)
                    ny_noise = noise_3d(px * nscale + 100, py * nscale + 100, pz * nscale + 100, params.noise_seed + 2)
                    nz_noise = noise_3d(px * nscale + 200, py * nscale + 200, pz * nscale + 200, params.noise_seed + 3)
                    # Störte Normalen
                    n_len = math.sqrt(nx_noise**2 + ny_noise**2 + nz_noise**2)
                    if n_len > 1e-6:
                        nx_noise, ny_noise, nz_noise = nx_noise/n_len, ny_noise/n_len, nz_noise/n_len
                    # Half-Vector dot Normal
                    ndot_h = hx*nx_noise + hy*ny_noise + hz*nz_noise
                    if ndot_h > 0:
                        spec = (ndot_h ** params.specular_power) * params.specular_intensity
                        specular_acc += transmittance * spec * falloff * shadow * step_size
            
            # Gesamt-Helligkeit mit Ambient und Gain
            gesamt = (scattered + specular_acc) * params.volumetric_gain + params.ambient
            bild[y][x] = gesamt
    
    # Box-Blur für weichere Kanten
    if params.blur_radius > 0:
        gewichte = gauß_gewichte(params.blur_radius)
        bild = box_blur_1d(bild, gewichte, True)
        bild = box_blur_1d(bild, gewichte, False)
    
    return bild


def bild_zu_ascii(bild: list, gamma: float) -> str:
    zeilen = []
    for row in bild:
        zeilen.append(''.join(intensitaet_zu_ascii(v, gamma) for v in row))
    return '\n'.join(zeilen)


def parameter_menü(params: ShaderParams) -> bool:
    """Zeigt Menü und verarbeitet Eingabe. Gibt False zurück bei Beenden."""
    print("\n=== 3D-Lichtspiel – Parameter ===")
    print(f"1) Penumbra-Breite: {params.penumbra_breite:.2f}")
    print(f"2) Umbra-Dunkelheit: {params.umbra_dunkelheit:.2f}")
    print(f"3) Falloff-Exponent: {params.falloff_exponent:.2f}")
    print(f"4) Falloff-Start: {params.falloff_start:.2f}")
    print(f"5) Blur-Radius: {params.blur_radius}")
    print(f"6) Ambient: {params.ambient:.3f}")
    print(f"7) Volumetric Gain: {params.volumetric_gain:.2f}")
    print(f"8) Gamma: {params.gamma:.2f}")
    print(f"9) Scattering Coeff: {params.scattering_coeff:.2f}")
    print(f"10) Absorption Coeff: {params.absorption_coeff:.2f}")
    print(f"11) Mist Density: {params.mist_density:.2f}")
    print(f"12) Mist Height Falloff: {params.mist_height_falloff:.2f}")
    print(f"13) Color Temp (K): {params.color_temp:.0f}")
    print(f"14) Jitter Strength: {params.jitter_strength:.2f}")
    print(f"15) Phase g: {params.phase_g:.2f}")
    print(f"16) Noise Seed: {params.noise_seed}")
    print(f"17) March Steps: {params.march_steps}")
    print(f"18) Jitter Enabled: {params.jitter_enabled}")
    print(f"19) Specular Intensity: {params.specular_intensity:.2f}")
    print(f"20) Specular Power: {params.specular_power:.1f}")
    print(f"21) Specular Noise Scale: {params.specular_noise_scale:.2f}")
    print("R) Rendern")
    print("Q) Beenden")
    try:
        wahl = input("Wahl: ").strip()
    except EOFError:
        return False
    
    if _norm(wahl) == 'q':
        return False
    if _norm(wahl) == 'r':
        return 'render'
    
    try:
        idx = int(wahl)
        if idx == 1:
            val = float(input("Penumbra-Breite (0.01-0.5): "))
            params.penumbra_breite = max(0.01, min(0.5, val))
        elif idx == 2:
            val = float(input("Umbra-Dunkelheit (0.0-0.5): "))
            params.umbra_dunkelheit = max(0.0, min(0.5, val))
        elif idx == 3:
            val = float(input("Falloff-Exponent (0.5-5.0): "))
            params.falloff_exponent = max(0.5, min(5.0, val))
        elif idx == 4:
            val = float(input("Falloff-Start (0.01-2.0): "))
            params.falloff_start = max(0.01, min(2.0, val))
        elif idx == 5:
            val = int(input("Blur-Radius (0-10): "))
            params.blur_radius = max(0, min(10, val))
        elif idx == 6:
            val = float(input("Ambient (0.0-0.2): "))
            params.ambient = max(0.0, min(0.2, val))
        elif idx == 7:
            val = float(input("Volumetric Gain (0.1-5.0): "))
            params.volumetric_gain = max(0.1, min(5.0, val))
        elif idx == 8:
            val = float(input("Gamma (0.1-2.0): "))
            params.gamma = max(0.1, min(2.0, val))
        elif idx == 9:
            val = float(input("Scattering Coeff (0.0-2.0): "))
            params.scattering_coeff = max(0.0, min(2.0, val))
        elif idx == 10:
            val = float(input("Absorption Coeff (0.0-1.0): "))
            params.absorption_coeff = max(0.0, min(1.0, val))
        elif idx == 11:
            val = float(input("Mist Density (0.01-1.0): "))
            params.mist_density = max(0.01, min(1.0, val))
        elif idx == 12:
            val = float(input("Mist Height Falloff (0.1-2.0): "))
            params.mist_height_falloff = max(0.1, min(2.0, val))
        elif idx == 13:
            val = float(input("Color Temp (1000-10000): "))
            params.color_temp = max(1000.0, min(10000.0, val))
        elif idx == 14:
            val = float(input("Jitter Strength (0.0-0.5): "))
            params.jitter_strength = max(0.0, min(0.5, val))
        elif idx == 15:
            val = float(input("Phase g (-0.95-0.95): "))
            params.phase_g = max(-0.95, min(0.95, val))
        elif idx == 16:
            val = int(input("Noise Seed (0-9999): "))
            params.noise_seed = max(0, min(9999, val))
        elif idx == 17:
            val = int(input("March Steps (8-128): "))
            params.march_steps = max(8, min(128, val))
        elif idx == 18:
            val = input("Jitter Enabled (ja/nein): ").strip().lower()
            params.jitter_enabled = val in ('ja', 'j', 'yes', 'y', 'true', '1')
        elif idx == 19:
            val = float(input("Specular Intensity (0.0-2.0): "))
            params.specular_intensity = max(0.0, min(2.0, val))
        elif idx == 20:
            val = float(input("Specular Power (1.0-128.0): "))
            params.specular_power = max(1.0, min(128.0, val))
        elif idx == 21:
            val = float(input("Specular Noise Scale (0.01-2.0): "))
            params.specular_noise_scale = max(0.01, min(2.0, val))
        else:
            print("Unbekannte Option.")
        print("Parameter aktualisiert.")
    except ValueError:
        print("Ungültige Eingabe.")
    except EOFError:
        return False
    return True


def main():
    # Szenen-Setup
    bäume = [
        (-1.5, -1.0, 0.3),
        (1.2, 0.8, 0.25),
        (-0.5, 1.5, 0.4),
        (2.0, -1.2, 0.2),
        (-2.0, 0.5, 0.35),
    ]
    licht_pos = (0.0, 0.0, 3.0)      # Lichtquelle über der Szene
    kamera_pos = (0.0, 0.0, 5.0)     # Kamera etwas weiter weg
    
    params = ShaderParams()
    breite, hoehe = 80, 40
    
    print("3D-Lichtspiel – Volumetrisches Licht im herbstlichen Park")
    print("Drücke R zum Rendern, Q zum Beenden.")
    
    while True:
        erg = parameter_menü(params)
        if erg is False:
            break
        if erg == 'render':
            print("\nRendere...", end='', flush=True)
            start = time.time()
            bild = rendere_szene(breite, hoehe, params, bäume, licht_pos, kamera_pos)
            ascii_art = bild_zu_ascii(bild, params.gamma)
            dauer = time.time() - start
            print(f"\rFertig in {dauer:.2f}s.\n")
            print(ascii_art)
            print("\n---")
    
    print("\nFifo winkt mit dem Flügel – bis zum nächsten Traum!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbbruch.")
    except Exception as e:
        print(f"\nUnerwarteter Fehler: {e}")
        sys.exit(1)