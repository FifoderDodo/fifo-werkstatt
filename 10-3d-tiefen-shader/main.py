import math
import sys
import random


def noise3d(x: float, y: float, z: float) -> float:
    """Einfaches 3D-Rauschen via Hash + Interpolation (Value Noise)."""
    ix = int(math.floor(x))
    iy = int(math.floor(y))
    iz = int(math.floor(z))
    fx = x - ix
    fy = y - iy
    fz = z - iz
    u = fx * fx * (3.0 - 2.0 * fx)
    v = fy * fy * (3.0 - 2.0 * fy)
    w = fz * fz * (3.0 - 2.0 * fz)
    
    def hash(i: int, j: int, k: int) -> float:
        n = (i + j * 57 + k * 131) & 0x7fffffff
        n = (n ^ (n >> 13)) * 0x5bd1e995
        n = (n ^ (n >> 15)) & 0x7fffffff
        return n / 0x7fffffff
    
    a = hash(ix, iy, iz)
    b = hash(ix + 1, iy, iz)
    c = hash(ix, iy + 1, iz)
    d = hash(ix + 1, iy + 1, iz)
    e = hash(ix, iy, iz + 1)
    f = hash(ix + 1, iy, iz + 1)
    g = hash(ix, iy + 1, iz + 1)
    h = hash(ix + 1, iy + 1, iz + 1)
    
    x1 = a + (b - a) * u
    x2 = c + (d - c) * u
    y1 = x1 + (x2 - x1) * v
    x3 = e + (f - e) * u
    x4 = g + (h - g) * u
    y2 = x3 + (x4 - x3) * v
    return y1 + (y2 - y1) * w


def szene_distanz(x: float, y: float, z: float) -> float:
    """SDF-Szene: Kugel bei (0,0,3) Radius 1 + Bumps, Boden bei y=-1 + Heightmap."""
    kugel_basis = math.sqrt(x * x + y * y + (z - 3.0) * (z - 3.0)) - 1.0
    bumps = 0.08 * noise3d(x * 2.5, y * 2.5, z * 2.5)
    kugel = kugel_basis - bumps
    
    boden_basis = y + 1.0
    hoehe = 0.12 * noise3d(x * 3.0, 0.0, z * 3.0)
    boden = boden_basis - hoehe
    
    return min(kugel, boden)


def szene_normal(x: float, y: float, z: float, eps: float = 1e-4) -> tuple:
    """Gradient des SDF als Normalenvektor (nicht normalisiert)."""
    d = szene_distanz(x, y, z)
    nx = szene_distanz(x + eps, y, z) - d
    ny = szene_distanz(x, y + eps, z) - d
    nz = szene_distanz(x, y, z + eps) - d
    leng = math.sqrt(nx * nx + ny * ny + nz * nz)
    if leng == 0:
        return 0.0, 1.0, 0.0
    return nx / leng, ny / leng, nz / leng


def raymarch(ox: float, oy: float, oz: float,
             dx: float, dy: float, dz: float,
             max_schritte: int = 80, max_dist: float = 20.0) -> float:
    """Marchiert entlang des Strahls und gibt die getroffene Tiefe zurück."""
    tiefe = 0.0
    for _ in range(max_schritte):
        px = ox + dx * tiefe
        py = oy + dy * tiefe
        pz = oz + dz * tiefe
        dist = szene_distanz(px, py, pz)
        if dist < 0.005:
            return tiefe
        tiefe += dist
        if tiefe > max_dist:
            break
    return max_dist


def shadow_raymarch(ox: float, oy: float, oz: float,
                    lx: float, ly: float, lz: float,
                    max_schritte: int = 60, max_dist: float = 30.0,
                    sharpness: float = 0.3) -> float:
    """Soft-Shadow Raymarching nach Iñigo Quilez.
    sharpness steuert die Schärfe: kleiner = weichere Penumbra.
    k = sharpness * 32.0; shadow = min(shadow, k * dist / tiefe).
    Gibt 1.0 = voll beleuchtet, 0.0 = tiefster Schatten."""
    tiefe = 0.0
    schatten = 1.0
    k = sharpness * 32.0  # Skalierung: kleiner sharpness -> weichere Schatten
    for _ in range(max_schritte):
        px = ox + lx * tiefe
        py = oy + ly * tiefe
        pz = oz + lz * tiefe
        dist = szene_distanz(px, py, pz)
        if tiefe > 0.0:
            # Quilez-Formel: shadow = min(shadow, k * dist / tiefe)
            schatten = min(schatten, k * dist / tiefe)
        # Kein harter Abbruch, nur bei extrem naher Geometrie
        if dist < 0.001:
            return 0.0
        tiefe += max(dist, 0.001)  # Kleinerer Mindestschritt für feinere Penumbra
        if tiefe > max_dist:
            break
    return max(0.0, min(1.0, schatten))


def main() -> None:
    print("Fifo's 3D-Tiefen-Shader - Teil 8: Optimierte Penumbra & Lighting-Pass")
    print("===================================================================")
    
    breite = 60
    hoehe = 30
    
    brennweite = 1.0
    cam_x, cam_y, cam_z = 0.0, 1.5, 0.0
    
    print(f"Rendere {breite}x{hoehe} Pixel mit Raymarching + Soft Shadows ...")
    
    skala = 1.0
    try:
        inp = input("Skalierungsfaktor für Szene (Enter=1.0, z.B. 0.5 oder 2.0): ").strip()
        if inp:
            skala = float(inp)
            print(f"Ok, Skalierung = {skala}")
    except (ValueError, EOFError):
        print("Keine gültige Zahl oder EOF, nehme Standard 1.0.")
    
    # Neue Eingabe für Schatten-Schärfe (kleiner = weicher)
    shadow_sharpness = 0.3
    try:
        inp = input("Schatten-Schärfe 0.1..1.0 (Enter=0.3, kleiner = weicher): ").strip()
        if inp:
            shadow_sharpness = float(inp)
            print(f"Ok, Schatten-Schärfe = {shadow_sharpness}")
    except (ValueError, EOFError):
        print("Keine gültige Zahl oder EOF, nehme Standard 0.3.")
    
    # Lichtrichtung
    lx, ly, lz = 1.0, 2.0, -1.0
    lleng = math.sqrt(lx*lx + ly*ly + lz*lz)
    lx, ly, lz = lx/lleng, ly/lleng, lz/lleng
    
    tiefe_buffer = []
    normal_buffer = []  # Speichere Normalen für zweiten Pass
    hit_buffer = []     # Speichere Hit-Punkte
    
    # Erster Pass: Raymarching + Normalen/Hitpoints speichern
    for j in range(hoehe):
        zeile_tiefen = []
        zeile_normalen = []
        zeile_hits = []
        ndc_y = (1.0 - 2.0 * j / (hoehe - 1)) / skala
        for i in range(breite):
            ndc_x = (2.0 * i / (breite - 1) - 1.0) / skala
            
            rdx = ndc_x * brennweite
            rdy = ndc_y * brennweite
            rdz = 1.0
            leng = math.sqrt(rdx * rdx + rdy * rdy + rdz * rdz)
            rdx /= leng
            rdy /= leng
            rdz /= leng
            
            t = raymarch(cam_x, cam_y, cam_z, rdx, rdy, rdz)
            zeile_tiefen.append(t)
            
            if t < 20.0:
                hx = cam_x + rdx * t
                hy = cam_y + rdy * t
                hz = cam_z + rdz * t
                nx, ny, nz = szene_normal(hx, hy, hz)
                zeile_normalen.append((nx, ny, nz))
                zeile_hits.append((hx, hy, hz))
            else:
                zeile_normalen.append((0.0, 0.0, 0.0))
                zeile_hits.append((0.0, 0.0, 0.0))
        tiefe_buffer.append(zeile_tiefen)
        normal_buffer.append(zeile_normalen)
        hit_buffer.append(zeile_hits)
    
    # Zweiter Pass: Lighting + Shadow + Depth Fog -> ASCII
    ascii_chars = " .:-=+*#%@"  # 10 Stufen von dunkel nach hell
    fog_dichte = 0.08
    ambient = 0.15
    
    print("\nRendering fertig. Ausgabe:\n")
    for j in range(hoehe):
        zeile = ""
        for i in range(breite):
            t = tiefe_buffer[j][i]
            if t >= 20.0:
                # Himmel: Farbverlauf basierend auf Ray-Richtung
                ndc_y = (1.0 - 2.0 * j / (hoehe - 1)) / skala
                ndc_x = (2.0 * i / (breite - 1) - 1.0) / skala
                rdx = ndc_x * brennweite
                rdy = ndc_y * brennweite
                rdz = 1.0
                leng = math.sqrt(rdx*rdx + rdy*rdy + rdz*rdz)
                rdy /= leng
                # Einfacher Sky-Gradient: oben heller, unten dunkler
                sky_brightness = 0.3 + 0.5 * max(0.0, rdy)
                idx = int(sky_brightness * (len(ascii_chars) - 1))
                zeile += ascii_chars[idx]
            else:
                nx, ny, nz = normal_buffer[j][i]
                hx, hy, hz = hit_buffer[j][i]
                # Diffuse Beleuchtung
                diffuse = max(0.0, nx*lx + ny*ly + nz*lz)
                # Shadow Raymarching mit kleinem Offset entlang der Normalen
                bias = 0.01
                sh = shadow_raymarch(hx + nx*bias, hy + ny*bias, hz + nz*bias,
                                     lx, ly, lz, sharpness=shadow_sharpness)
                # Kombinierte Helligkeit
                brightness = ambient + diffuse * sh
                # Depth Fog
                brightness *= math.exp(-t * fog_dichte)
                brightness = max(0.0, min(1.0, brightness))
                idx = int(brightness * (len(ascii_chars) - 1))
                zeile += ascii_chars[idx]
        print(zeile)
    
    print("\nFertig.")

if __name__ == "__main__":
    main()