# 3D-Lichtspiel – Teil 7: Volumetrische Tiefe – Scattering, Mist, Farbtemperatur, Jitter
# Fifo der Dodo fügt atmosphärische Streuung und herbstlichen Nebel hinzu – Lichtkegel atmen jetzt

import math
import sys
import random
import unicodedata


class ShaderParams:
    """Container für alle einstellbaren Shader-Parameter mit Defaults."""
    def __init__(self):
        self.penumbra_breite = 0.15      # Weichheit des Schattenrandes (0.01 - 0.5)
        self.umbra_dunkelheit = 0.05     # Restlicht im Kernschatten (0.0 - 0.5)
        self.falloff_exponent = 2.0      # Lichtabfall mit Distanz (1.0 - 4.0)
        self.blur_radius = 3             # Box-Blur Kernel Radius (1 - 8)
        self.ambient = 0.02              # Grundhelligkeit (0.0 - 0.2)
        self.volumetric_gain = 1.2       # Verstärkung der Lichtkegel-Sichtbarkeit (0.5 - 3.0)
        self.gamma = 0.6                 # Gamma-Korrektur für ASCII-Mapping (0.3 - 1.0)
        # NEU: Volumetrische Tiefe & Herbst-Atmosphäre
        self.scattering_coeff = 0.35     # Mie-Streuungskoeffizient für Lichtkegel (0.1 - 1.0)
        self.absorption_coeff = 0.12     # Absorption im Medium / Nebel (0.0 - 0.3)
        self.mist_density = 0.18         # Nebeldichte für Tiefenwirkung (0.0 - 0.4)
        self.mist_height_falloff = 0.8   # Nebel nimmt nach oben ab (0.5 - 1.5)
        self.color_temp = 3200.0         # Farbtemperatur Kelvin – warmherbstlich (2500-5500)
        self.jitter_strength = 0.15      # Feines Rauschen für organische Kegelränder (0.0 - 0.3)
        self.phase_g = 0.6               # Henyey-Greenstein Asymmetrie (0.0-0.9, vorwärts)
    
    def klonen(self):
        klon = ShaderParams()
        klon.__dict__.update(self.__dict__)
        return klon


def _norm(s: str) -> str:
    """Normalisiert String für robusten Vergleich: NFC, lower, strip."""
    return unicodedata.normalize('NFC', s).strip().lower()


def gauß_gewichte(kernel_radius: int) -> list:
    """Erzeugt 1D-Gewichte für Box-Blur (näherungsweise Gauß). Summe = 1.0."""
    size = kernel_radius * 2 + 1
    gewicht = 1.0 / size
    return [gewicht] * size


def box_blur_1d(puffer: list, gewichte: list, horizontal: bool = True) -> list:
    """Wendet 1D-Box-Blur auf 2D-Float-Puffer an (separabel)."""
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
    """Phasenfunktion für Volumetrisches Streulicht (vorwärts-gerichtet)."""
    g2 = g * g
    denom = (1.0 + g2 - 2.0 * g * cos_theta) ** 1.5
    return (1.0 - g2) / (4.0 * math.pi * denom) if denom > 1e-6 else 1.0


def kelvin_to_rgb_factor(temp_k: float) -> tuple:
    """Näherung: Farbtemperatur -> RGB-Multiplikatoren (normalisiert auf Grün=1.0)."""
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
    # Normalisieren so dass Grün ~1.0 für Helligkeitserhalt
    g = max(0.01, g)
    return (r / g, 1.0, b / g)


def intensitaet_zu_ascii(wert: float, gamma: float = 0.6) -> str:
    """Mappt Float-Intensität (0.0-1.0+) auf ASCII-Stufen mit Gamma."""
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
    """
    Berechnet Schattierung (0.0 = voller Schatten, 1.0 = voll beleuchtet) für einen Punkt (px,py)
    relativ zur Lichtquelle (qx,qy) mit Reichweite radius.
    Nutzt Similarität der Dreiecke für Penumbra (weicher Schattenrand).
    """
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
        
        tiefe_diff = dist_q_p - proj
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
            t = max(0.0, min(1.0, t))
            faktor = umbra + (1.0 - umbra) * (t * t * (3.0 - 2.0 * t))
        
        if faktor < min_shadow:
            min_shadow = faktor
            if min_shadow <= umbra:
                break
    
    return min_shadow


def zeichne_lichtkegel(breite: int, hoehe: int, quellen: list, bäume: list, params: ShaderParams) -> list:
    """Erzeugt 2D-Gitter mit volumetric Licht & Schatten: Float-Puffer -> Blur -> ASCII."""
    float_buf = [[params.ambient for _ in range(breite)] for __ in range(hoehe)]
    
    # Farbtemperatur-Faktoren für herbstliche Stimmung
    r_mult, g_mult, b_mult = kelvin_to_rgb_factor(params.color_temp)
    
    for qx, qy, radius, richtung_x, richtung_y in quellen:
        r2 = radius * radius
        x0 = max(0, int(qx - radius))
        x1 = min(breite, int(qx + radius) + 1)
        y0 = max(0, int(qy - radius))
        y1 = min(hoehe, int(qy + radius) + 1)
        
        for y in range(y0, y1):
            dy = y - qy
            dy2 = dy * dy
            row = float_buf[y]
            for x in range(x0, x1):
                dx = x - qx
                dist2 = dx * dx + dy2
                
                if dist2 > r2:
                    continue
                
                dist = math.sqrt(dist2)
                # Falloff mit einstellbarem Exponenten
                falloff = 1.0 / (1.0 + (dist / max(1.0, radius * 0.3)) ** params.falloff_exponent)
                
                # Richtungsfaktor (Kegelform)
                if radius > 0.01:
                    dot = (dx * richtung_x + dy * richtung_y) / radius
                    kegel = max(0.0, dot)  # Nur Vorwärts
                else:
                    kegel = 1.0
                
                # Schatten
                shadow = schattenfaktor_für_punkt(x, y, qx, qy, radius, bäume, params)
                
                # Volumetrisches Streulicht (Mie) – Henyey-Greenstein
                # cos_theta ≈ Ausrichtung zur Blickrichtung (hier vereinfacht: Kegelrichtung)
                cos_theta = kegel
                phase = henyey_greenstein(cos_theta, params.phase_g)
                
                # Nebel/Absorption mit Höhenabhängigkeit (y nach oben = kleiner y-Index)
                # Normalisierte Höhe: 0.0 unten, 1.0 oben
                norm_h = 1.0 - (y / max(1, hoehe - 1))
                mist_factor = math.exp(-params.absorption_coeff * dist * (1.0 + params.mist_density * norm_h * params.mist_height_falloff))
                
                # Jitter für organische Kanten
                jitter = 1.0
                if params.jitter_strength > 0.0:
                    # Deterministisches Rauschen basierend auf Position
                    seed_val = (x * 73.14 + y * 19.41 + qx * 11.73 + qy * 31.09) % 1.0
                    jitter = 1.0 + params.jitter_strength * (seed_val - 0.5) * 2.0
                
                # Kombinierte Intensität
                intensität = (falloff * kegel * shadow * phase 
                              * params.volumetric_gain * params.scattering_coeff 
                              * mist_factor * jitter)
                
                # Additiv auf Buffer (mehrere Quellen addieren)
                row[x] += intensität
    
    # Blur-Pass für weiche Kegelränder
    if params.blur_radius > 0:
        gewichte = gauß_gewichte(params.blur_radius)
        float_buf = box_blur_1d(float_buf, gewichte, True)
        float_buf = box_blur_1d(float_buf, gewichte, False)
    
    # ASCII-Mapping
    ascii_buf = []
    for y in range(hoehe):
        zeile = ''.join(intensitaet_zu_ascii(float_buf[y][x], params.gamma) for x in range(breite))
        ascii_buf.append(zeile)
    
    return ascii_buf


def erzeuge_szene(params: ShaderParams) -> tuple:
    """Erzeugt Bäume und Lichtquellen für den Herbstpark."""
    breite, hoehe = 80, 40
    random.seed(42)  # Reproduzierbar
    
    # Bäume: (x, y, radius)
    bäume = []
    for _ in range(25):
        bx = random.uniform(5, breite - 5)
        by = random.uniform(5, hoehe - 5)
        br = random.uniform(1.5, 3.5)
        bäume.append((bx, by, br))
    
    # Lichtquellen: (x, y, radius, dir_x, dir_y)
    quellen = [
        (10.0, 10.0, 18.0, 0.8, 0.6),   # Sonne tief rechts-unten
        (70.0, 30.0, 15.0, -0.7, -0.3), # Laterne links oben
        (40.0, 20.0, 22.0, 0.0, -1.0),  # Mondlicht von oben
    ]
    
    return breite, hoehe, quellen, bäume


def menü_shader_parameter(params: ShaderParams) -> ShaderParams:
    """Interaktives Menü zum Live-Tweaken der Shader-Parameter."""
    felder = [
        ('penumbra_breite', 'Penumbra-Breite', 0.01, 0.5),
        ('umbra_dunkelheit', 'Umbra-Dunkelheit', 0.0, 0.5),
        ('falloff_exponent', 'Falloff-Exponent', 1.0, 4.0),
        ('blur_radius', 'Blur-Radius (int)', 1, 8),
        ('ambient', 'Ambient-Grundhelligkeit', 0.0, 0.2),
        ('volumetric_gain', 'Volumetric Gain', 0.5, 3.0),
        ('gamma', 'Gamma-Korrektur', 0.3, 1.0),
        ('scattering_coeff', 'Streuungskoeffizient', 0.1, 1.0),
        ('absorption_coeff', 'Absorptionskoeffizient', 0.0, 0.3),
        ('mist_density', 'Nebeldichte', 0.0, 0.4),
        ('mist_height_falloff', 'Nebel-Höhenabfall', 0.5, 1.5),
        ('color_temp', 'Farbtemperatur (K)', 2500.0, 5500.0),
        ('jitter_strength', 'Jitter-Stärke', 0.0, 0.3),
        ('phase_g', 'Phasen-Asymmetrie (g)', 0.0, 0.9),
    ]
    
    while True:
        print('\n=== Shader-Parameter anpassen ===')
        for i, (attr, name, mn, mx) in enumerate(felder, 1):
            val = getattr(params, attr)
            print(f'  {i:2d}. {name}: {val:.3f}  [{mn} – {mx}]')
        print('  0. Zurück zum Hauptmenü')
        
        try:
            wahl = input('Parameter wählen (0-{}): '.format(len(felder))).strip()
        except EOFError:
            print('\n🦤 Tschüss!')
            sys.exit(0)
        
        if not wahl:
            continue
        if wahl == '0':
            break
        
        try:
            idx = int(wahl) - 1
            if 0 <= idx < len(felder):
                attr, name, mn, mx = felder[idx]
                try:
                    neu = float(input(f'Neuer Wert für {name} [{mn}–{mx}]: ').strip())
                    neu = max(mn, min(mx, neu))
                    if attr == 'blur_radius':
                        neu = int(neu)
                    setattr(params, attr, neu)
                    print(f'  → {name} = {neu}')
                except ValueError:
                    print('  Ungültige Zahl.')
            else:
                print('  Ungültige Auswahl.')
        except ValueError:
            print('  Bitte Zahl eingeben.')
    
    return params


def tageszeit_vorlage(params: ShaderParams, vorlage: str) -> ShaderParams:
    """Setzt Parameter-Vorlagen für verschiedene Tageszeiten."""
    v = _norm(vorlage)
    if v in ('morgens', 'morgen', 'dawn', '1'):
        params.penumbra_breite = 0.12
        params.umbra_dunkelheit = 0.08
        params.falloff_exponent = 2.2
        params.blur_radius = 4
        params.ambient = 0.04
        params.volumetric_gain = 1.5
        params.gamma = 0.55
        params.scattering_coeff = 0.45
        params.absorption_coeff = 0.15
        params.mist_density = 0.28
        params.mist_height_falloff = 0.7
        params.color_temp = 3500.0
        params.jitter_strength = 0.18
        params.phase_g = 0.65
        print('🌅 Morgendämmerung – kühler Nebel, weiche Schatten')
    elif v in ('mittag', 'noon', '2'):
        params.penumbra_breite = 0.08
        params.umbra_dunkelheit = 0.02
        params.falloff_exponent = 1.8
        params.blur_radius = 2
        params.ambient = 0.08
        params.volumetric_gain = 0.8
        params.gamma = 0.7
        params.scattering_coeff = 0.2
        params.absorption_coeff = 0.05
        params.mist_density = 0.05
        params.mist_height_falloff = 1.0
        params.color_temp = 5500.0
        params.jitter_strength = 0.08
        params.phase_g = 0.5
        print('☀️ Mittag – harte Schatten, wenig Volumetrik')
    elif v in ('abends', 'abend', 'dusk', '3'):
        params.penumbra_breite = 0.18
        params.umbra_dunkelheit = 0.04
        params.falloff_exponent = 2.5
        params.blur_radius = 5
        params.ambient = 0.03
        params.volumetric_gain = 1.8
        params.gamma = 0.5
        params.scattering_coeff = 0.55
        params.absorption_coeff = 0.18
        params.mist_density = 0.22
        params.mist_height_falloff = 0.85
        params.color_temp = 2800.0
        params.jitter_strength = 0.22
        params.phase_g = 0.7
        print('🌇 Abenddämmerung – goldene Stunde, tiefe Kegel')
    elif v in ('nacht', 'night', '4'):
        params.penumbra_breite = 0.22
        params.umbra_dunkelheit = 0.01
        params.falloff_exponent = 3.0
        params.blur_radius = 6
        params.ambient = 0.01
        params.volumetric_gain = 2.2
        params.gamma = 0.45
        params.scattering_coeff = 0.6
        params.absorption_coeff = 0.1
        params.mist_density = 0.15
        params.mist_height_falloff = 1.2
        params.color_temp = 4200.0  # Mondlicht
        params.jitter_strength = 0.12
        params.phase_g = 0.6
        print('🌙 Nacht – Mondlicht, starker Kontrast, feiner Nebel')
    elif v in ('herbst', 'autumn', '5'):
        params.penumbra_breite = 0.16
        params.umbra_dunkelheit = 0.05
        params.falloff_exponent = 2.3
        params.blur_radius = 4
        params.ambient = 0.025
        params.volumetric_gain = 1.6
        params.gamma = 0.55
        params.scattering_coeff = 0.5
        params.absorption_coeff = 0.14
        params.mist_density = 0.25
        params.mist_height_falloff = 0.8
        params.color_temp = 3000.0
        params.jitter_strength = 0.2
        params.phase_g = 0.68
        print('🍂 Herbst-Spezial – warmer Nebel, tiefe Lichtkegel')
    else:
        print('Unbekannte Vorlage. Verfügbar: morgens, mittag, abends, nacht, herbst')
    return params


def main():
    print('🦤 3D-Lichtspiel – Volumetrisches Licht & Schatten im Herbstpark')
    print('=' * 60)
    
    params = ShaderParams()
    
    while True:
        print('\n=== Hauptmenü ===')
        print('  1. Szene rendern')
        print('  2. Shader-Parameter anpassen')
        print('  3. Tageszeit-Vorlage laden')
        print('  4. Beenden')
        
        try:
            wahl = input('Deine Wahl (1-4): ').strip()
        except EOFError:
            print('\n🦤 Tschüss!')
            break
        
        if wahl == '1':
            breite, hoehe, quellen, bäume = erzeuge_szene(params)
            ascii_art = zeichne_lichtkegel(breite, hoehe, quellen, bäume, params)
            print(f'\n--- Render: {breite}x{hoehe} ---')
            for zeile in ascii_art:
                print(zeile)
            print('--- Ende ---')
        
        elif wahl == '2':
            params = menü_shader_parameter(params)
        
        elif wahl == '3':
            try:
                v = input('Vorlage (morgens/mittag/abends/nacht/herbst): ').strip()
                params = tageszeit_vorlage(params, v)
            except EOFError:
                print('\n🦤 Tschüss!')
                break
        
        elif wahl == '4':
            print('🦤 Bis bald im Park!')
            break
        
        else:
            print('Unbekannte Option.')

if __name__ == '__main__':
    main()