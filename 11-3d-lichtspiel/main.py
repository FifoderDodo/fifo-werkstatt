# 3D-Lichtspiel – Teil 10: Point Light Falloff & Attenuation
# Fifo der Dodo justiert die Fernwirkung der Lichtquelle – jetzt wird's am Rand gemütlicher.

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
        self.falloff_exponent = 2.0      # NEU: Abfall-Exponent für Point-Light (1/d^exp)
        self.falloff_start = 0.5         # NEU: Distanz ab der Falloff greift (vermeidet Singularität)
        self.blur_radius = 3
        self.ambient = 0.02
        self.volumetric_gain = 1.2
        self.gamma = 0.6
        # Volumetrische Tiefe & Herbst-Atmosphäre
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


def berechne_volumetrisch(breite: int, hoehe: int, quelle: tuple, radius: float, 
                          bäume: list, params: ShaderParams) -> list:
    """Raymarching für volumetrische Lichtkegel mit Schatten, Streuung & Falloff."""
    qx, qy = quelle
    rgb_factors = kelvin_to_rgb_factor(params.color_temp)
    
    # Shadow-Cache: Berechne Schattenfaktor pro Pixel einmal (2D)
    print("  Berechne Shadow-Map...")
    shadow_map = [[1.0 for _ in range(breite)] for __ in range(hoehe)]
    for y in range(hoehe):
        for x in range(breite):
            # Weltkoordinaten (Zentrum = 0,0)
            wx = (x - breite * 0.5) * 0.1
            wy = (y - hoehe * 0.5) * 0.1
            shadow_map[y][x] = schattenfaktor_für_punkt(wx, wy, qx, qy, radius, bäume, params)
    
    # Raymarching Accumulation Buffer (nur Intensität für ASCII)
    print("  Raymarching mit Falloff...")
    accum = [[0.0 for _ in range(breite)] for __ in range(hoehe)]
    
    # Viewport: Kamera schaut auf XY-Ebene (Top-Down), Z ist "Tiefe" in den Bildschirm
    # Wir marschieren entlang der View-Richtung (Z), aber Licht kommt von (qx, qy, 0)
    # Vereinfacht: 2D Raymarching vom Licht aus? Nein, Screen-Space Raymarching.
    # Hier: Screen-Space Raymarching entlang Z (Tiefe).
    # Light Position in World: (qx, qy, 0). Camera at (0, 0, -cam_dist).
    # Pixel (x,y) -> Ray Direction (wx, wy, 1). Normalized.
    
    cam_dist = 10.0
    max_depth = 20.0
    
    for y in range(hoehe):
        for x in range(breite):
            # Shadow Faktor für diesen Screen-Pixel (projeziert auf Ground)
            wx_ground = (x - breite * 0.5) * 0.1
            wy_ground = (y - hoehe * 0.5) * 0.1
            shadow = shadow_map[y][x]
            
            if shadow < 0.01:
                continue # Voll im Schatten, skip marching
            
            # Ray Direction
            rx = wx_ground
            ry = wy_ground
            rz = cam_dist # Kamera schaut in +Z
            rlen = math.sqrt(rx*rx + ry*ry + rz*rz)
            rx /= rlen
            ry /= rlen
            rz /= rlen
            
            # Raymarch
            transmittance = 1.0
            radiance = 0.0
            
            # Jitter Offset für Start
            jitter_off = 0.0
            if params.jitter_enabled:
                jitter_off = noise_2d(x * 0.1, y * 0.1, params.noise_seed) * params.jitter_strength
            
            for step in range(params.march_steps):
                t = (step + jitter_off) / params.march_steps * max_depth
                # Sample Position World
                sx = rx * t
                sy = ry * t
                sz = -cam_dist + rz * t # World Z
                
                # Distanz zur Lichtquelle (qx, qy, 0)
                dlx = sx - qx
                dly = sy - qy
                dlz = sz - 0.0
                dist_light = math.sqrt(dlx*dlx + dly*dly + dlz*dlz)
                
                if dist_light > radius:
                    # Außerhalb Lichtradius -> keine Streuung mehr
                    # Aber Transmittance weiter abnehmen lassen (Mist)
                    pass
                
                # NEU: Point Light Falloff / Attenuation
                # Standard: 1 / (falloff_start + dist^falloff_exponent)
                # Verhindert Singularität bei dist=0
                falloff = 1.0 / (params.falloff_start + dist_light ** params.falloff_exponent)
                
                # Mist Density (Höhenabhängig, hier flach)
                # sz ist Höhe. Mist sinkt zu Boden (sz=0).
                height_factor = max(0.0, 1.0 - abs(sz) * params.mist_height_falloff)
                local_density = params.mist_density * height_factor
                
                # Absorption
                transmittance *= math.exp(-params.absorption_coeff * local_density * (max_depth / params.march_steps))
                if transmittance < 0.001:
                    break
                
                # Scattering (Single Scattering Approximation)
                # Phase Function: Henyey-Greenstein
                # View Dir: (0,0,1) -> Camera. Light Dir: (-dlx, -dly, -dlz) -> Light
                # Cos Theta = View . Light
                if dist_light > 1e-4:
                    lx = -dlx / dist_light
                    ly = -dly / dist_light
                    lz = -dlz / dist_light
                    cos_theta = lz # View Dir ist (0,0,1)
                    phase = henyey_greenstein(cos_theta, params.phase_g)
                else:
                    phase = 1.0
                
                scatter = params.scattering_coeff * local_density * phase * falloff * shadow * transmittance
                radiance += scatter * (max_depth / params.march_steps)
            
            accum[y][x] = radiance * params.volumetric_gain + params.ambient
    
    # Blur
    if params.blur_radius > 0:
        print("  Blur...")
        gew = gauß_gewichte(params.blur_radius)
        accum = box_blur_1d(accum, gew, True)
        accum = box_blur_1d(accum, gew, False)
    
    # Gamma & ASCII
    ascii_frame = []
    for y in range(hoehe):
        row = ''
        for x in range(breite):
            row += intensitaet_zu_ascii(accum[y][x], params.gamma)
        ascii_frame.append(row)
    
    return ascii_frame


def main():
    params = ShaderParams()
    breite, hoehe = 80, 40
    radius = 12.0
    quelle = (0.0, 0.0)
    # Bäume: (x, y, radius)
    bäume = [
        (-3.0, 2.0, 1.2),
        (4.5, -1.5, 0.8),
        (-6.0, -4.0, 1.5),
        (7.0, 3.0, 1.0),
        (0.0, -8.0, 1.8),
        (-2.0, 6.0, 0.9),
        (5.0, 5.0, 1.1),
    ]
    
    print("=== 3D-Lichtspiel: Herbspark (Teil 10) ===")
    print("Fifo der Dodo justiert die Falloff-Kurve.")
    
    while True:
        print(f"\n--- 3D-Lichtspiel Parameter (Teil 10) ---")
        print(f"1. March Steps: {params.march_steps} (Speed vs Quality)")
        print(f"2. Scattering Coeff: {params.scattering_coeff:.2f}")
        print(f"3. Mist Density: {params.mist_density:.2f}")
        print(f"4. Phase G (Forward): {params.phase_g:.2f}")
        print(f"5. Color Temp (K): {int(params.color_temp)}")
        print(f"6. Jitter: {'An' if params.jitter_enabled else 'Aus'} (Strength: {params.jitter_strength:.2f})")
        print(f"7. Noise Seed: {params.noise_seed}")
        print(f"8. Volumetric Gain: {params.volumetric_gain:.2f}")
        print(f"9. Blur Radius: {params.blur_radius}")
        print(f"10. Falloff Exponent: {params.falloff_exponent:.1f}")
        print(f"11. Falloff Start: {params.falloff_start:.2f}")
        print(f"0. Rendern & Beenden")
        
        try:
            wahl = input("Wähle (0-11): ").strip()
        except EOFError:
            print("\nKein Input, Fifo fliegt nach Hause. Tschüss!")
            break
        
        if wahl == '0':
            break
        elif wahl == '1':
            try: params.march_steps = max(4, int(input(f"March Steps [{params.march_steps}]: ") or params.march_steps))
            except: pass
        elif wahl == '2':
            try: params.scattering_coeff = float(input(f"Scattering [{params.scattering_coeff}]: ") or params.scattering_coeff)
            except: pass
        elif wahl == '3':
            try: params.mist_density = float(input(f"Mist Density [{params.mist_density}]: ") or params.mist_density)
            except: pass
        elif wahl == '4':
            try: params.phase_g = max(-0.99, min(0.99, float(input(f"Phase G [{params.phase_g}]: ") or params.phase_g)))
            except: pass
        elif wahl == '5':
            try: params.color_temp = max(1000, min(12000, float(input(f"Color Temp [{int(params.color_temp)}]: ") or params.color_temp)))
            except: pass
        elif wahl == '6':
            params.jitter_enabled = not params.jitter_enabled
            if params.jitter_enabled:
                try: params.jitter_strength = float(input(f"Jitter Strength [{params.jitter_strength}]: ") or params.jitter_strength)
                except: pass
        elif wahl == '7':
            try: params.noise_seed = int(input(f"Noise Seed [{params.noise_seed}]: ") or params.noise_seed)
            except: pass
        elif wahl == '8':
            try: params.volumetric_gain = float(input(f"Gain [{params.volumetric_gain}]: ") or params.volumetric_gain)
            except: pass
        elif wahl == '9':
            try: params.blur_radius = max(0, int(input(f"Blur Radius [{params.blur_radius}]: ") or params.blur_radius))
            except: pass
        elif wahl == '10':
            try: params.falloff_exponent = max(0.1, min(5.0, float(input(f"Falloff Exponent [{params.falloff_exponent}]: ") or params.falloff_exponent)))
            except: pass
        elif wahl == '11':
            try: params.falloff_start = max(0.01, float(input(f"Falloff Start [{params.falloff_start}]: ") or params.falloff_start))
            except: pass
        else:
            print("Unbekannte Option.")
    
    # Final Render
    print("\nRendere finales Bild...")
    start = time.time()
    frame = berechne_volumetrisch(breite, hoehe, quelle, radius, bäume, params)
    dauer = time.time() - start
    
    print(f"\nRenderzeit: {dauer:.2f}s")
    print(f"Quelle: {quelle}, Radius: {radius}")
    print(f"Falloff: 1/({params.falloff_start} + d^{params.falloff_exponent})")
    print("\n" + "=" * breite)
    for row in frame:
        print(row)
    print("=" * breite)
    print("\nFifo nickt zufrieden. Das Licht fällt jetzt natürlich ab.")

if __name__ == "__main__":
    main()