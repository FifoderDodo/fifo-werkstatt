# 3D-Lichtspiel – Teil 9: Optimierung der Lichtkegel & Streuungs-Seed
# Fifo der Dodo feilt an der Performance und gibt dem Nebel einen festen Samen.

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
        # NEU: Seed für reproduzierbares Rauschen & Optimierung
        self.noise_seed = 42
        self.march_steps = 32        # Raymarch-Schritte (16-64, weniger = schneller)
        self.jitter_enabled = True   # Jitter an/aus für Performance-Vergleich
    
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
    # Großer Primzahl-Mix für Pseudo-Zufall
    n = int(x * 123.45) ^ int(y * 678.91) ^ seed
    n = (n ^ (n >> 13)) * 0x5bd1e995
    n = (n ^ (n >> 15)) * 0x5bd1e995
    n = n ^ (n >> 15)
    return (n & 0x7fffffff) / 0x7fffffff * 2.0 - 1.0  # -1 bis 1


def berechne_volumetrisch(breite: int, hoehe: int, quelle: tuple, radius: float, 
                          bäume: list, params: ShaderParams) -> list:
    """Raymarching für volumetrische Lichtkegel mit Schatten & Streuung.
    Optimiert: Weniger Schritte, früher Abbruch, separater Shadow-Cache."""
    qx, qy = quelle
    rgb_factors = kelvin_to_rgb_factor(params.color_temp)
    
    # Shadow-Cache: Berechne Schattenfaktor pro Pixel einmal (2D), 
    # damit Raymarching nur noch Transparenz akkumuliert.
    print("  Berechne Shadow-Map...")
    shadow_map = [[1.0 for _ in range(breite)] for __ in range(hoehe)]
    for y in range(hoehe):
        for x in range(breite):
            # Weltkoordinaten (Zentrum = 0,0)
            wx = (x - breite * 0.5) * 0.1
            wy = (y - hoehe * 0.5) * 0.1
            shadow_map[y][x] = schattenfaktor_für_punkt(wx, wy, qx, qy, radius, bäume, params)
    
    print(f"  Raymarching ({params.march_steps} Schritte)...")
    vol_buffer = [[0.0 for _ in range(breite)] for __ in range(hoehe)]
    
    # Vorberechnete Schrittgröße
    step_len = radius / params.march_steps
    inv_steps = 1.0 / params.march_steps
    
    for y in range(hoehe):
        wy = (y - hoehe * 0.5) * 0.1
        for x in range(breite):
            wx = (x - breite * 0.5) * 0.1
            
            dx = wx - qx
            dy = wy - qy
            dist = math.hypot(dx, dy)
            
            if dist > radius or dist < 0.01:
                continue
            
            # Richtung von Licht zum Pixel
            ux = dx / dist
            uy = dy / dist
            
            # View-Richtung (Kamera schaut von -Z, hier vereinfacht von oben -Y Richtung?)
            # Wir simulieren "God Rays" von der Seite: View-Dir = (0, -1) oder ähnlich.
            # Einfacher: Phase-Funktion nutzt Winkel zwischen Lichtstrahl und Blickrichtung.
            # Blickrichtung fest: Kamera steht "vor" der Szene (Richtung +Y in Welt?)
            # Hier: Licht kommt von oben links, Kamera schaut von vorn (+Z projiziert auf -Y).
            view_dx, view_dy = 0.0, -1.0 
            cos_theta = ux * view_dx + uy * view_dy
            phase = henyey_greenstein(cos_theta, params.phase_g)
            
            transmittance = 1.0
            scatter_acc = 0.0
            
            # Raymarching vom Licht zum Pixel (Forward Marching)
            for i in range(params.march_steps):
                t = (i + 0.5) * inv_steps  # 0.5/steps ... 1.0
                sample_dist = dist * t
                
                sx = qx + ux * sample_dist
                sy = qy + uy * sample_dist
                
                # Nebeldichte mit Höhenabfall (sy ist "Höhe" in 2D-Schnitt)
                # Annahme: y=0 ist Boden, y>0 ist oben. Kamera schaut entlang -y.
                # Mist fällt mit sy ab (je höher, desto weniger).
                height_factor = max(0.0, 1.0 - sy * params.mist_height_falloff)
                density = params.mist_density * height_factor
                
                # Jitter für organische Kanten (nur wenn an)
                if params.jitter_enabled:
                    jitter = noise_2d(sx * 10.0, sy * 10.0, params.noise_seed + i) * params.jitter_strength
                    density += jitter
                
                # Extinktion (Absorption + Out-Scattering)
                extinction = (params.absorption_coeff + params.scattering_coeff) * density
                transmittance *= math.exp(-extinction * step_len * 10.0)  # Skalierung
                
                if transmittance < 0.001:
                    break
                
                # In-Scattering: Licht, das in Blickrichtung gestreut wird
                # Schatten an dieser Sample-Position holen (Bilinear filtern wäre schöner, nearest ist schnell)
                sample_x = int((sx / 0.1) + breite * 0.5)
                sample_y = int((sy / 0.1) + hoehe * 0.5)
                shadow = 1.0
                if 0 <= sample_x < breite and 0 <= sample_y < hoehe:
                    shadow = shadow_map[sample_y][sample_x]
                
                # Lichtintensität an Sample-Stelle (Inverse Square Falloff)
                light_intensity = shadow * (1.0 / max(0.01, sample_dist ** params.falloff_exponent))
                
                scatter_acc += light_intensity * params.scattering_coeff * density * phase * transmittance * step_len * 10.0
            
            vol_buffer[y][x] = scatter_acc * params.volumetric_gain
    
    return vol_buffer


def render_frame(breite: int, hoehe: int, params: ShaderParams) -> list:
    """Haupt-Render-Funktion: Baut Szene, rendert Volumetrik, blurrt, mapped zu ASCII."""
    # Szenen-Definition: (x, y, radius)
    bäume = [
        (-3.0, 2.0, 0.8), (4.0, -1.5, 1.0), (-5.0, -3.0, 0.6),
        (6.0, 4.0, 1.2), (0.0, -5.0, 0.9), (-2.0, -6.0, 0.7),
        (7.0, -2.0, 1.1), (-6.0, 5.0, 0.5)
    ]
    quelle = (0.0, 0.0)  # Lichtquelle in der Mitte
    radius = 12.0
    
    # 1. Volumetrische Berechnung
    vol = berechne_volumetrisch(breite, hoehe, quelle, radius, bäume, params)
    
    # 2. Blur für weiche Kegel
    if params.blur_radius > 0:
        gew = gauß_gewichte(params.blur_radius)
        vol = box_blur_1d(vol, gew, True)
        vol = box_blur_1d(vol, gew, False)
    
    # 3. Ambient & Tonemapping
    frame = []
    for y in range(hoehe):
        row = ''
        for x in range(breite):
            val = vol[y][x] + params.ambient
            row += intensitaet_zu_ascii(val, params.gamma)
        frame.append(row)
    return frame


def parameter_menue(params: ShaderParams):
    """Interaktives Menü zum Tweaken."""
    while True:
        print("\n--- 3D-Lichtspiel Parameter (Teil 9) ---")
        print(f"1. March Steps: {params.march_steps} (Speed vs Quality)")
        print(f"2. Scattering Coeff: {params.scattering_coeff:.2f}")
        print(f"3. Mist Density: {params.mist_density:.2f}")
        print(f"4. Phase G (Forward): {params.phase_g:.2f}")
        print(f"5. Color Temp (K): {params.color_temp:.0f}")
        print(f"6. Jitter: {'An' if params.jitter_enabled else 'Aus'} (Strength: {params.jitter_strength:.2f})")
        print(f"7. Noise Seed: {params.noise_seed}")
        print(f"8. Volumetric Gain: {params.volumetric_gain:.2f}")
        print(f"9. Blur Radius: {params.blur_radius}")
        print("0. Rendern & Beenden")
        try:
            wahl = input("Wähle (0-9): ").strip()
        except EOFError:
            print("\nKein Input, fliege weg. Tschüss!")
            sys.exit(0)
        
        if wahl == '0':
            break
        elif wahl == '1':
            try: params.march_steps = max(8, min(128, int(input("Steps (8-128): "))))
            except: pass
        elif wahl == '2':
            try: params.scattering_coeff = max(0.0, min(2.0, float(input("Scattering (0-2): "))))
            except: pass
        elif wahl == '3':
            try: params.mist_density = max(0.0, min(1.0, float(input("Mist (0-1): "))))
            except: pass
        elif wahl == '4':
            try: params.phase_g = max(0.0, min(0.99, float(input("Phase G (0-0.99): "))))
            except: pass
        elif wahl == '5':
            try: params.color_temp = max(1000.0, min(10000.0, float(input("Temp K (1000-10000): "))))
            except: pass
        elif wahl == '6':
            params.jitter_enabled = not params.jitter_enabled
            if params.jitter_enabled:
                try: params.jitter_strength = max(0.0, min(0.5, float(input("Jitter Strength (0-0.5): "))))
                except: pass
        elif wahl == '7':
            try: params.noise_seed = int(input("Seed (int): "))
            except: pass
        elif wahl == '8':
            try: params.volumetric_gain = max(0.1, min(5.0, float(input("Gain (0.1-5): "))))
            except: pass
        elif wahl == '9':
            try: params.blur_radius = max(0, min(10, int(input("Blur Radius (0-10): "))))
            except: pass
        else:
            print("Unbekannt.")

def main():
    print("~~~ 3D-Lichtspiel: Herbst-Park ~~~")
    print("Fifo der Dodo optimiert die Lichtkegel (Teil 9).")
    
    params = ShaderParams()
    
    # Standard-Größe für Terminal
    breite, hoehe = 80, 40
    
    parameter_menue(params)
    
    print("\nRendering...")
    start = time.time()
    frame = render_frame(breite, hoehe, params)
    dauer = time.time() - start
    
    print(f"\nFertig in {dauer:.2f}s. Seed: {params.noise_seed}, Steps: {params.march_steps}")
    print("=" * breite)
    for row in frame:
        print(row)
    print("=" * breite)
    
    # Nochmal?
    try:
        if input("\nNochmal mit neuen Parametern? (j/n): ").strip().lower() == 'j':
            main()
        else:
            print("Fifo watschelt ins Laub. Tschüss!")
    except EOFError:
        print("\nEOF. Tschüss!")

if __name__ == "__main__":
    main()