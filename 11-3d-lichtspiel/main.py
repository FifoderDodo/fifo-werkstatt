# 3D-Lichtspiel – Teil 5: Schattenwürfe durch Bäume, weiche Penumbra, pro Lichtquelle
# Fifo der Dodo lässt die Laternen hinter Baumkronen tanzen – Tiefe wird greifbar

import math
import sys
import random
import unicodedata


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
            for x in range(w):
                acc = 0.0
                for i, gew in enumerate(gewichte):
                    xi = x - k_rad + i
                    if 0 <= xi < w:
                        acc += puffer[y][xi] * gew
                ergebnis[y][x] = acc
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


def intensitaet_zu_ascii(wert: float) -> str:
    """Mappt Float-Intensität (0.0-1.0+) auf ASCII-Stufen."""
    if wert <= 0.0:
        return ' '
    w = min(1.0, max(0.0, wert)) ** 0.6
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


def schattenfaktor_für_punkt(px: float, py: float, qx: float, qy: float, radius: float, bäume: list) -> float:
    """
    Berechnet Schattierung (0.0 = voller Schatten, 1.0 = voll beleuchtet) für einen Punkt (px,py)
    relativ zur Lichtquelle (qx,qy) mit Reichweite radius.
    Nutzt Similarität der Dreiecke für Penumbra (weicher Schattenrand).
    """
    dx = px - qx
    dy = py - qy
    dist_q_p = math.hypot(dx, dy)
    
    if dist_q_p > radius or dist_q_p < 0.01:
        return 1.0  # Ausser Reichweite oder genau an Quelle -> kein Schattenwurf relevant
    
    # Richtung von Quelle zu Punkt
    ux = dx / dist_q_p
    uy = dy / dist_q_p
    
    min_shadow = 1.0
    
    for bx, by, bradius in bäume:
        # Vektor Quelle -> Baum
        vx = bx - qx
        vy = by - qy
        dist_q_b = math.hypot(vx, vy)
        
        if dist_q_b < 0.01:
            continue # Baum steht auf Laterne
        
        # Prüfen: Liegt Baum *zwischen* Quelle und Punkt? (Projection auf Strahl)
        proj = vx * ux + vy * uy  # Skalarprojektion auf Strahlrichtung
        if proj <= 0.01 or proj >= dist_q_p:
            continue # Baum hinter Quelle oder hinter Punkt
        
        # Senkrechter Abstand vom Baumzentrum zum Lichtstrahl
        # |v x u| = |v| * sin(winkel) = |vx*uy - vy*ux|
        abstand_zu_strahl = abs(vx * uy - vy * ux)
        
        if abstand_zu_strahl >= bradius:
            continue # Strahl verfehlt Baum
        
        # Wir schneiden den Baum. Berechne Penumbra.
        # Tiefenvergleich: Wie weit ist Baum vom Punkt entfernt entlang Strahl?
        tiefe_diff = dist_q_p - proj
        
        # Halbwinkel des Schattens am Baumrand (Geometrie: similar triangles)
        # Sinus = bradius / dist_q_b. Für kleine Winkel ~ Winkel.
        # Schatten breitet sich aus: radius_shadow = bradius + tiefe_diff * tan(winkel)
        # tan(winkel) = bradius / sqrt(dist_q_b^2 - bradius^2) ≈ bradius / dist_q_b
        # Vereinfacht: Lineare Interpolation zwischen Umbra (Kern) und Penumbra (Rand)
        
        # Kernschatten (Umbra) existiert nur wenn Lichtquelle Punktquelle (hier: ja).
        # Wir machen weichen Übergang basierend auf relativer Position im Schattenkegel.
        # Relative Position quer zum Strahl im Schattenkegel:
        # Der Schattenkegel hat an der Baumposition Radius bradius.
        # An der Punktposition Radius = bradius * (dist_q_p / dist_q_b)
        schatten_radius_hier = bradius * (dist_q_p / dist_q_b)
        
        # Normalisierter Abstand vom Strahlzentrum (0 = Zentrum, 1 = Rand Kernschatten)
        # Aber Penumbra geht über Kernschattenrand hinaus.
        # Nutzen wir smoothstep über die Kante des geometrischen Schattens.
        rand_faktor = abstand_zu_strahl / schatten_radius_hier if schatten_radius_hier > 0 else 1.0
        
        # 0.0 = mitten im Schatten, 1.0 = draussen. Smoothstep für weichen Rand.
        # Penumbra-Breite ~ 10-20% des Schattenradius
        penumbra_breite = 0.15
        if rand_faktor < 1.0 - penumbra_breite:
            faktor = 0.05  # Fast ganz dunkel (Umbra + Streulicht)
        elif rand_faktor > 1.0 + penumbra_breite:
            faktor = 1.0   # Kein Schatten
        else:
            # Smoothstep im Penumbra-Bereich
            t = (rand_faktor - (1.0 - penumbra_breite)) / (2.0 * penumbra_breite)
            t = max(0.0, min(1.0, t))
            faktor = 0.05 + 0.95 * (t * t * (3.0 - 2.0 * t))  # Smoothstep 0.05 -> 1.0
        
        if faktor < min_shadow:
            min_shadow = faktor
            if min_shadow <= 0.05:
                break # Ganz dunkel, reicht
    
    return min_shadow


def zeichne_lichtkegel(breite: int, hoehe: int, quellen: list, bäume: list, blur_radius: int = 3, ambient: float = 0.0) -> list:
    """Erzeugt 2D-Gitter mit volumetric Licht & Schatten: Float-Puffer -> Blur -> ASCII."""
    float_buf = [[ambient for _ in range(breite)] for __ in range(hoehe)]
    
    for qx, qy, radius, richtung_x, richtung_y in quellen:
        r2 = radius * radius
        x0 = max(0, int(qx - radius))
        x1 = min(breite, int(qx + radius) + 1)
        y0 = max(0, int(qy - radius))
        y1 = min(hoehe, int(qy + radius) + 1)
        
        # Temporärer Layer für diese Quelle (für korrekte Schatten *vor* Blur)
        layer = [[0.0 for _ in range(breite)] for __ in range(hoehe)]
        
        for y in range(y0, y1):
            dy = y - qy
            for x in range(x0, x1):
                dx = x - qx
                dist2 = dx*dx + dy*dy
                if dist2 > r2:
                    continue
                dist = math.sqrt(dist2)
                
                if dist > 0.1:
                    punkt_rx = dx / dist
                    punkt_ry = dy / dist
                    cos_winkel = punkt_rx * richtung_x + punkt_ry * richtung_y
                    if cos_winkel < 0.5:  # ~60 Grad Öffnungswinkel
                        continue
                    winkel_faktor = cos_winkel * cos_winkel
                else:
                    winkel_faktor = 1.0
                
                norm_dist = dist / radius
                radial_faktor = math.exp(-4.0 * norm_dist * norm_dist)
                
                # NEU: Schatten abfragen
                schatten = schattenfaktor_für_punkt(x, y, qx, qy, radius, bäume)
                
                beitrag = radial_faktor * winkel_faktor * schatten
                layer[y][x] += beitrag
        
        # Layer auf Hauptpuffer addieren
        for y in range(hoehe):
            for x in range(breite):
                float_buf[y][x] += layer[y][x]
    
    # Clamping vor Blur
    for y in range(hoehe):
        for x in range(breite):
            if float_buf[y][x] > 1.0:
                float_buf[y][x] = 1.0
    
    gewichte = gauß_gewichte(blur_radius)
    float_buf = box_blur_1d(float_buf, gewichte, horizontal=True)
    float_buf = box_blur_1d(float_buf, gewichte, horizontal=False)
    
    bild = [[' ' for _ in range(breite)] for __ in range(hoehe)]
    
    # Bodendetails (Laub, Gras) - nur unten
    random.seed(1337)
    for _ in range(breite * hoehe // 40):
        x = random.randint(0, breite - 1)
        y = random.randint(hoehe // 2, hoehe - 1)
        bild[y][x] = random.choice(['.', ',', '`'])
    
    # Baumstämme als feste Silhouetten reinzeichnen (sehr dunkel)
    for bx, by, bradius in bäume:
        ix, iy = int(bx), int(by)
        if 0 <= ix < breite and 0 <= iy < hoehe:
            bild[iy][ix] = '│'
            # Ein paar Pixel drumherum für Dicke
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = ix + dx, iy + dy
                    if 0 <= nx < breite and 0 <= ny < hoehe and bild[ny][nx] == ' ':
                        bild[ny][nx] = '░'
    
    # Licht über Blend-Logik legen
    for y in range(hoehe):
        for x in range(breite):
            zeichen = intensitaet_zu_ascii(float_buf[y][x])
            if zeichen != ' ':
                aktuell = bild[y][x]
                ordnung = ' .,`░│+*#@'
                try:
                    if ordnung.index(zeichen) > ordnung.index(aktuell):
                        bild[y][x] = zeichen
                except ValueError:
                    bild[y][x] = zeichen
    
    return bild


def frage_int(prompt: str, default: int, min_v: int, max_v: int) -> int:
    """Fragt robust eine Ganzzahl ab, fängt EOFError ab."""
    while True:
        try:
            val = input(prompt) or str(default)
            val = int(val)
            return max(min_v, min(max_v, val))
        except ValueError:
            print("  Fifo braucht eine Zahl. Nochmal! 🦤")
        except EOFError:
            print("\nEingabeende – Fifo watschelt nach Hause. 🦤")
            sys.exit(0)


def frage_wahl(prompt: str, default: str, optionen: list, aliases: dict = None) -> str:
    """
    Fragt robust eine Option ab (case-insensitiv, Unicode-normalisiert).
    aliases: Dict {alias_normiert: ziel_option_original}
    """
    opt_map = {_norm(o): o for o in optionen}
    
    if aliases:
        for alias, ziel in aliases.items():
            if _norm(ziel) in opt_map:
                opt_map[_norm(alias)] = opt_map[_norm(ziel)]
    
    gültige_anzeige = ', '.join(optionen)
    
    while True:
        try:
            val = (input(prompt) or default)
            key = _norm(val)
            if key in opt_map:
                return opt_map[key]
            print(f"  Fifo kennt nur: {gültige_anzeige}. Nochmal! 🦤")
        except EOFError:
            print("\nEingabeende – Fifo watschelt nach Hause. 🦤")
            sys.exit(0)


def main():
    print("🍂 3D-Lichtspiel – Herbstpark-Simulator (Volumetric Blur & Shadows) 🍂")
    print("Fifo der Dodo justiert die Streuungskernel und pflanzt Schattenbäume...\n")
    
    breite = frage_int("Breite (40-160) [100]: ", 100, 40, 160)
    hoehe = frage_int("Höhe (20-80) [40]: ", 40, 20, 80)
    
    aliases = {
        'daemmerung': 'dämmerung',
        'tag': 'herbsttag',
        'herbst': 'herbsttag',
        'nacht': 'nacht'
    }
    zeit = frage_wahl(
        "Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]: ",
        "dämmerung",
        ["dämmerung", "nacht", "herbsttag"],
        aliases
    )
    
    # Parameter je Tageszeit
    if zeit == "nacht":
        anzahl_laternen = random.randint(5, 9)
        ambient = 0.02
        blur_r = 4
        laternen_radius = (12, 20)
    elif zeit == "dämmerung":
        anzahl_laternen = random.randint(4, 7)
        ambient = 0.08
        blur_r = 3
        laternen_radius = (10, 18)
    else: # herbsttag
        anzahl_laternen = random.randint(2, 4)
        ambient = 0.25
        blur_r = 2
        laternen_radius = (8, 15)
    
    quellen = []
    random.seed(42) # Feste Seed für reproduzierbare Park-Layouts pro Run
    
    for _ in range(anzahl_laternen):
        # Laternen etwas verteilt, nicht am Rand
        lx = random.uniform(breite * 0.1, breite * 0.9)
        ly = random.uniform(hoehe * 0.15, hoehe * 0.85)
        lrad = random.uniform(*laternen_radius)
        # Richtung meist nach unten (Boden), leicht zufällig
        rw = random.uniform(-0.3, 0.3)
        rx = rw
        ry = math.sqrt(max(0.0, 1.0 - rw*rw)) * (1 if random.random() > 0.5 else -1) # Nach oben oder unten
        if zeit == "herbsttag":
            ry = abs(ry) * -1 # Tagsüber eher nach unten auf Wege
        quellen.append((lx, ly, lrad, rx, ry))
    
    # BÄUME generieren: (x, y, radius)
    bäume = []
    anzahl_bäume = random.randint(6, 12)
    for _ in range(anzahl_bäume):
        bx = random.uniform(breite * 0.05, breite * 0.95)
        by = random.uniform(hoehe * 0.1, hoehe * 0.9)
        brad = random.uniform(1.5, 3.5)
        # Nicht zu nah an Laternen (vermeiden dass Baum *in* Laterne steht)
        ok = True
        for qx, qy, qr, _, _ in quellen:
            if math.hypot(bx - qx, by - qy) < qr * 0.5 + brad:
                ok = False
                break
        if ok:
            bäume.append((bx, by, brad))
    
    print(f"\nFifo stellt {anzahl_laternen} Laternen und {len(bäume)} Bäume auf. Rechne Licht... 🦤")
    
    bild = zeichne_lichtkegel(breite, hoehe, quellen, bäume, blur_radius=blur_r, ambient=ambient)
    
    print(f"\n🍂 {zeit.capitalize()} im Park ({breite}x{hoehe}) 🍂")
    for reihe in bild:
        print(''.join(reihe))
    
    print("\nFifo nickt zufrieden. Die Schatten tanzen. 🦤")

if __name__ == "__main__":
    main()