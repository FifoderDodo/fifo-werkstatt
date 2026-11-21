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
    sharpness (ehemals softness) steuert die Schärfe: kleiner = weichere Penumbra.
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
    print("Fifo's 3D-Tiefen-Shader - Teil 7: Weichere Soft-Shadows & Konfiguration")
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
    schatten_buffer = []
    normal_buffer = []  # Speichere Normalen für zweiten Pass
    
    for j in range(hoehe):
        zeile_tiefen = []
        zeile_schatten = []
        zeile_normalen = []
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
                
                # Normal-Map-Bias für Schattenstrahl-Startpunkt
                bias = 0.015
                sx = hx + nx * bias
                sy = hy + ny * bias
                sz = hz + nz * bias
                
                # Soft Shadow Raymarch mit einstellbarer Schärfe
                shadow = shadow_raymarch(sx, sy, sz, lx, ly, lz,
                                         max_schritte=60, max_dist=30.0,
                                         sharpness=shadow_sharpness)
                zeile_schatten.append(shadow)
            else:
                zeile_normalen.append((0.0, 1.0, 0.0))
                zeile_schatten.append(1.0)
        tiefe_buffer.append(zeile_tiefen)
        schatten_buffer.append(zeile_schatten)
        normal_buffer.append(zeile_normalen)
    
    # Zweiter Pass: Lighting mit Diffuse, Ambient, Specular, Tiefen-Nebel
    ascii_ramp = " .'`^\"~,:;!<+*/?#&@"  # 20 Stufen
    ramp_len = len(ascii_ramp) - 1
    
    print("\nErgebnis:")
    for j in range(hoehe):
        line_chars = []
        for i in range(breite):
            t = tiefe_buffer[j][i]
            shadow = schatten_buffer[j][i]
            nx, ny, nz = normal_buffer[j][i]
            
            if t >= 20.0:
                # Himmel: nur Nebel-Farbe basierend auf y-Richtung des Strahls
                # Einfacher Farbverlauf: oben dunkler, unten heller
                ndc_y = (1.0 - 2.0 * j / (hoehe - 1)) / skala
                sky_val = 0.3 + 0.5 * (ndc_y + 1.0) * 0.5
                idx = int(max(0.0, min(1.0, sky_val)) * ramp_len)
                line_chars.append(ascii_ramp[idx])
                continue
            
            # Trefferpunkt
            hx = cam_x + ( (2.0 * i / (breite - 1) - 1.0) / skala ) * brennweite / math.sqrt( ((2.0 * i / (breite - 1) - 1.0) / skala)**2 * brennweite**2 + ((1.0 - 2.0 * j / (hoehe - 1)) / skala)**2 * brennweite**2 + 1.0 ) * t
            hy = cam_y + ( (1.0 - 2.0 * j / (hoehe - 1)) / skala ) * brennweite / math.sqrt( ((2.0 * i / (breite - 1) - 1.0) / skala)**2 * brennweite**2 + ((1.0 - 2.0 * j / (hoehe - 1)) / skala)**2 * brennweite**2 + 1.0 ) * t
            hz = cam_z + 1.0 / math.sqrt( ((2.0 * i / (breite - 1) - 1.0) / skala)**2 * brennweite**2 + ((1.0 - 2.0 * j / (hoehe - 1)) / skala)**2 * brennweite**2 + 1.0 ) * t
            
            # Diffuse (Lambert)
            diffuse = max(0.0, nx * lx + ny * ly + nz * lz)
            
            # Specular (Blinn-Phong)
            vx, vy, vz = - ( (2.0 * i / (breite - 1) - 1.0) / skala ) * brennweite / math.sqrt( ((2.0 * i / (breite - 1) - 1.0) / skala)**2 * brennweite**2 + ((1.0 - 2.0 * j / (hoehe - 1)) / skala)**2 * brennweite**2 + 1.0 ), \
                                 - ( (1.0 - 2.0 * j / (hoehe - 1)) / skala ) * brennweite / math.sqrt( ((2.0 * i / (breite - 1) - 1.0) / skala)**2 * brennweite**2 + ((1.0 - 2.0 * j / (hoehe - 1)) / skala)**2 * brennweite**2 + 1.0 ), \
                                 - 1.0 / math.sqrt( ((2.0 * i / (breite - 1) - 1.0) / skala)**2 * brennweite**2 + ((1.0 - 2.0 * j / (hoehe - 1)) / skala)**2 * brennweite**2 + 1.0 )
            hx_dir = lx + vx
            hy_dir = ly + vy
            hz_dir = lz + vz
            hlen = math.sqrt(hx_dir*hx_dir + hy_dir*hy_dir + hz_dir*hz_dir)
            if hlen > 0:
                hx_dir /= hlen; hy_dir /= hlen; hz_dir /= hlen
                spec = max(0.0, nx * hx_dir + ny * hy_dir + nz * hz_dir)
                spec = spec ** 32.0  # Glanz
            else:
                spec = 0.0
            
            # Ambient
            ambient = 0.25
            
            # Kombinieren
            color = ambient + shadow * (diffuse * 0.7 + spec * 0.5)
            
            # Tiefen-Nebel (exponentiell)
            fog = math.exp(-t * 0.12)
            color = color * fog + (1.0 - fog) * 0.15
            
            # Gamma-Korrektur für linearen Look
            color = color ** 0.4545
            
            idx = int(max(0.0, min(1.0, color)) * ramp_len)
            line_chars.append(ascii_ramp[idx])
        print(''.join(line_chars))
    
    print("\nFertig.")

if __name__ == "__main__":
    main()