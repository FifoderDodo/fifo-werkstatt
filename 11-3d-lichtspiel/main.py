# 3D-Lichtspiel – Teil 6: Shader-Parameter exponiert, Live-Tweaking im Menü
# Fifo der Dodo schraubt an den Reglern – Penumbra, Falloff, Blur, alles flüssig einstellbar

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
                
                # Schatten berechnen
                schatten = schattenfaktor_für_punkt(x, y, qx, qy, radius, bäume, params)
                
                # Volumetric Gain anwenden
                wert = falloff * kegel * schatten * params.volumetric_gain
                
                # Akkumulieren (additiv für mehrere Quellen)
                row[x] += wert
    
    # Baumstämme als harte Silhouetten (nach Licht, vor Blur)
    for bx, by, bradius in bäume:
        ix, iy = int(bx), int(by)
        if 0 <= ix < breite and 0 <= iy < hoehe:
            float_buf[iy][ix] = 0.0
            # Etwas Rinde andeuten
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                nx, ny = ix+dx, iy+dy
                if 0 <= nx < breite and 0 <= ny < hoehe:
                    float_buf[ny][nx] = min(float_buf[ny][nx], params.ambient * 0.5)
    
    # Separable Blur
    gewichte = gauß_gewichte(params.blur_radius)
    float_buf = box_blur_1d(float_buf, gewichte, True)
    float_buf = box_blur_1d(float_buf, gewichte, False)
    
    # ASCII Konvertierung mit Gamma
    ascii_art = []
    for y in range(hoehe):
        zeile = ''.join(intensitaet_zu_ascii(float_buf[y][x], params.gamma) for x in range(breite))
        ascii_art.append(zeile)
    
    return ascii_art


def generiere_szene(tageszeit: str, breite: int, hoehe: int):
    """Erzeugt Bäume und Laternen passend zur Tageszeit."""
    random.seed(hash(tageszeit) % (2**32))
    bäume = []
    anzahl_bäume = max(3, (breite * hoehe) // 1200)
    for _ in range(anzahl_bäume):
        bx = random.uniform(2, breite - 3)
        by = random.uniform(2, hoehe - 3)
        bradius = random.uniform(1.5, 3.5)
        bäume.append((bx, by, bradius))
    
    quellen = []
    if tageszeit == 'nacht':
        anzahl = max(2, (breite * hoehe) // 2000)
        for _ in range(anzahl):
            qx = random.uniform(3, breite - 4)
            qy = random.uniform(3, hoehe - 4)
            radius = random.uniform(8, 14)
            winkel = random.uniform(0, 2 * math.pi)
            richtung_x = math.cos(winkel)
            richtung_y = math.sin(winkel) * 0.5  # Etwas abgeflacht
            quellen.append((qx, qy, radius, richtung_x, richtung_y))
    elif tageszeit == 'dämmerung':
        anzahl = max(1, (breite * hoehe) // 3000)
        for _ in range(anzahl):
            qx = random.uniform(3, breite - 4)
            qy = random.uniform(3, hoehe - 4)
            radius = random.uniform(10, 18)
            winkel = random.uniform(-0.5, 0.5)  # Mehr horizontal
            richtung_x = math.cos(winkel)
            richtung_y = math.sin(winkel) * 0.3
            quellen.append((qx, qy, radius, richtung_x, richtung_y))
    else:  # herbsttag
        # Keine künstlichen Quellen, nur Ambient (wird in Parametern geregelt)
        pass
    
    return bäume, quellen


def menü_shader_params(params: ShaderParams) -> ShaderParams:
    """Interaktives Untermenü zum Tweaken der Shader-Parameter."""
    while True:
        print("\n=== Shader-Parameter ===")
        print(f"1. Penumbra-Breite     : {params.penumbra_breite:.2f}  (0.01 - 0.5)")
        print(f"2. Umbra-Dunkelheit    : {params.umbra_dunkelheit:.2f}  (0.0 - 0.5)")
        print(f"3. Falloff-Exponent    : {params.falloff_exponent:.1f}  (1.0 - 4.0)")
        print(f"4. Blur-Radius         : {params.blur_radius}      (1 - 8)")
        print(f"5. Ambient-Helligkeit  : {params.ambient:.3f}  (0.0 - 0.2)")
        print(f"6. Volumetric Gain     : {params.volumetric_gain:.1f}  (0.5 - 3.0)")
        print(f"7. Gamma               : {params.gamma:.2f}  (0.3 - 1.0)")
        print("8. Zurück zum Hauptmenü")
        try:
            wahl = input("Wähle Parameter (1-8): ").strip()
        except EOFError:
            return params
        
        if wahl == '8':
            return params
        
        try:
            if wahl == '1':
                v = float(input(f"Neuer Wert [{params.penumbra_breite:.2f}]: ") or params.penumbra_breite)
                params.penumbra_breite = max(0.01, min(0.5, v))
            elif wahl == '2':
                v = float(input(f"Neuer Wert [{params.umbra_dunkelheit:.2f}]: ") or params.umbra_dunkelheit)
                params.umbra_dunkelheit = max(0.0, min(0.5, v))
            elif wahl == '3':
                v = float(input(f"Neuer Wert [{params.falloff_exponent:.1f}]: ") or params.falloff_exponent)
                params.falloff_exponent = max(1.0, min(4.0, v))
            elif wahl == '4':
                v = int(input(f"Neuer Wert [{params.blur_radius}]: ") or params.blur_radius)
                params.blur_radius = max(1, min(8, v))
            elif wahl == '5':
                v = float(input(f"Neuer Wert [{params.ambient:.3f}]: ") or params.ambient)
                params.ambient = max(0.0, min(0.2, v))
            elif wahl == '6':
                v = float(input(f"Neuer Wert [{params.volumetric_gain:.1f}]: ") or params.volumetric_gain)
                params.volumetric_gain = max(0.5, min(3.0, v))
            elif wahl == '7':
                v = float(input(f"Neuer Wert [{params.gamma:.2f}]: ") or params.gamma)
                params.gamma = max(0.3, min(1.0, v))
            else:
                print("Ungültige Auswahl.")
        except ValueError:
            print("Ungültige Zahl.")
        except EOFError:
            return params


def main() -> None:
    breite, hoehe = 100, 40
    params = ShaderParams()
    
    print("🦤 3D-Lichtspiel – Volumetrisches Licht & Schatten im Herbstpark")
    print("==============================================================")
    
    while True:
        print("\n=== Hauptmenü ===")
        print("1. Szene rendern")
        print("2. Shader-Parameter anpassen")
        print("3. Beenden")
        try:
            wahl = input("Deine Wahl (1-3): ").strip()
        except EOFError:
            print("\nTschüss! 🦤")
            break
        
        if wahl == '3':
            print("Tschüss! 🦤")
            break
        
        if wahl == '2':
            params = menü_shader_params(params)
            continue
        
        if wahl != '1':
            continue
        
        try:
            tageszeit = input("Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]: ").strip() or "dämmerung"
            tageszeit = _norm(tageszeit)
            if tageszeit not in ("dämmerung", "nacht", "herbsttag"):
                print("Fifo kennt nur: dämmerung, nacht, herbsttag.")
                continue
        except EOFError:
            break
        
        bäume, quellen = generiere_szene(tageszeit, breite, hoehe)
        
        # Tag-spezifische Defaults überschreiben
        if tageszeit == 'herbsttag':
            params.ambient = 0.15
            params.volumetric_gain = 0.8
        elif tageszeit == 'dämmerung':
            params.ambient = 0.03
            params.volumetric_gain = 1.2
        else:  # nacht
            params.ambient = 0.01
            params.volumetric_gain = 1.5
        
        print(f"\nRendere {tageszeit}... ({len(bäume)} Bäume, {len(quellen)} Laternen)")
        bild = zeichne_lichtkegel(breite, hoehe, quellen, bäume, params)
        print("\n" + "=" * breite)
        for zeile in bild:
            print(zeile)
        print("=" * breite)
        print(f"Parameter: Penumbra={params.penumbra_breite:.2f} Falloff={params.falloff_exponent:.1f} Blur={params.blur_radius} Gamma={params.gamma:.2f}")

if __name__ == "__main__":
    main()