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
    k = sharpness * 32.0
    for _ in range(max_schritte):
        px = ox + lx * tiefe
        py = oy + ly * tiefe
        pz = oz + lz * tiefe
        dist = szene_distanz(px, py, pz)
        if tiefe > 0.0:
            schatten = min(schatten, k * dist / tiefe)
        if dist < 0.001:
            return 0.0
        tiefe += max(dist, 0.001)
        if tiefe > max_dist:
            break
    return max(0.0, min(1.0, schatten))


def depth_interpolate_bilateral(tiefe_buffer: list, normal_buffer: list,
                                 breite: int, hoehe: int,
                                 sigma_r: float = 0.15, sigma_s: float = 1.5) -> list:
    """Bilateral-Filter auf Tiefenpuffer mit Normalen als Kantenführung.
    Glättet Tiefe, aber respektiert Materialgrenzen (Normalensprünge).
    sigma_r: Bereichs-Sigma (Tiefendifferenz-Gewichtung)
    sigma_s: Räumliches Sigma (Distanz-Gewichtung)"""
    # 3x3 Kernel vorberechnen
    kernel = []
    for ky in range(-1, 2):
        for kx in range(-1, 2):
            dist2 = kx*kx + ky*ky
            w_s = math.exp(-dist2 / (2.0 * sigma_s * sigma_s))
            kernel.append((kx, ky, w_s))
    
    ergebnis = []
    for j in range(hoehe):
        zeile = []
        for i in range(breite):
            d_center = tiefe_buffer[j][i]
            if d_center >= 20.0:  # Hintergrund nicht filtern
                zeile.append(d_center)
                continue
            
            n_center = normal_buffer[j][i]
            sum_w = 0.0
            sum_d = 0.0
            
            for kx, ky, w_s in kernel:
                ni = i + kx
                nj = j + ky
                if 0 <= ni < breite and 0 <= nj < hoehe:
                    d_n = tiefe_buffer[nj][ni]
                    if d_n >= 20.0:
                        continue
                    n_n = normal_buffer[nj][ni]
                    # Normalen-Ähnlichkeit als Kanten-Stopper
                    ndot = n_center[0]*n_n[0] + n_center[1]*n_n[1] + n_center[2]*n_n[2]
                    ndot = max(-1.0, min(1.0, ndot))
                    diff = 1.0 - ndot  # 0 = gleiche Normalen, 2 = entgegengesetzt
                    w_r = math.exp(-diff * diff / (2.0 * sigma_r * sigma_r))
                    
                    w = w_s * w_r
                    sum_w += w
                    sum_d += w * d_n
            
            if sum_w > 0:
                zeile.append(sum_d / sum_w)
            else:
                zeile.append(d_center)
        ergebnis.append(zeile)
    return ergebnis


def depth_interpolate_smoothstep(tiefe_buffer: list, breite: int, hoehe: int) -> list:
    """Einfache Smoothstep-Interpolation zwischen Nachbarpixeln.
    Mildert harte Stufen ohne Kanten-Erkennung."""
    ergebnis = []
    for j in range(hoehe):
        zeile = []
        for i in range(breite):
            d = tiefe_buffer[j][i]
            if d >= 20.0:
                zeile.append(d)
                continue
            # 4-Nachbarschaft sammeln
            nachbarn = []
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                ni, nj = i+dx, j+dy
                if 0 <= ni < breite and 0 <= nj < hoehe:
                    dn = tiefe_buffer[nj][ni]
                    if dn < 20.0:
                        nachbarn.append(dn)
            if nachbarn:
                # Smoothstep-Gewichtung: näher an Center = höheres Gewicht
                # Wir nutzen einfach einen gewichteten Mittelwert mit smoothstep auf Distanz
                gew_sum = 0.0
                val_sum = 0.0
                for dn in nachbarn:
                    diff = abs(dn - d)
                    # smoothstep(0, 0.5, diff) -> 1 bei diff=0, 0 bei diff>=0.5
                    t = max(0.0, min(1.0, diff / 0.5))
                    w = 1.0 - (t * t * (3.0 - 2.0 * t))  # inverse smoothstep
                    gew_sum += w
                    val_sum += w * dn
                # Zentrum mit einbeziehen
                gew_sum += 1.0
                val_sum += d
                zeile.append(val_sum / gew_sum)
            else:
                zeile.append(d)
        ergebnis.append(zeile)
    return ergebnis


def main() -> None:
    print("Fifo's 3D-Tiefen-Shader - Teil 9: Depth-Interpolation für weichere Schatten")
    print("=====================================================================")
    
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
    
    shadow_sharpness = 0.3
    try:
        inp = input("Schatten-Schärfe 0.1..1.0 (Enter=0.3, kleiner = weicher): ").strip()
        if inp:
            shadow_sharpness = float(inp)
            print(f"Ok, Schatten-Schärfe = {shadow_sharpness}")
    except (ValueError, EOFError):
        print("Keine gültige Zahl oder EOF, nehme Standard 0.3.")
    
    # Interpolationsmethode wählen
    print("\nInterpolationsmethode für Tiefenpuffer:")
    print("  1 = Keine (Original)")
    print("  2 = Bilateral (kantenerhaltend, Normalen-geführt)")
    print("  3 = Smoothstep (einfach, schnell)")
    interp_mode = 2
    try:
        inp = input("Wähle 1/2/3 (Enter=2): ").strip()
        if inp:
            interp_mode = int(inp)
            if interp_mode not in (1,2,3):
                interp_mode = 2
            print(f"Ok, Modus = {interp_mode}")
    except (ValueError, EOFError):
        print("Ungültig, nehme Bilateral (2).")
    
    # Lichtrichtung
    lx, ly, lz = 1.0, 2.0, -1.0
    lleng = math.sqrt(lx*lx + ly*ly + lz*lz)
    lx, ly, lz = lx/lleng, ly/lleng, lz/lleng
    
    tiefe_buffer = []
    normal_buffer = []
    hit_buffer = []
    
    # Erster Pass: Raymarching + Normalen/Hitpoints speichern
    print("\nPass 1: Raymarching ...")
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
                zeile_normalen.append((0.0, 1.0, 0.0))
                zeile_hits.append((0.0, 0.0, 0.0))
        tiefe_buffer.append(zeile_tiefen)
        normal_buffer.append(zeile_normalen)
        hit_buffer.append(zeile_hits)
    
    # NEU: Tiefen-Interpolation anwenden
    print("Pass 1.5: Tiefen-Interpolation ...")
    if interp_mode == 2:
        tiefe_buffer = depth_interpolate_bilateral(tiefe_buffer, normal_buffer, breite, hoehe)
        print("  -> Bilateral-Filter angewendet")
    elif interp_mode == 3:
        tiefe_buffer = depth_interpolate_smoothstep(tiefe_buffer, breite, hoehe)
        print("  -> Smoothstep-Interpolation angewendet")
    else:
        print("  -> Keine Interpolation (Original)")
    
    # Zweiter Pass: Lighting mit interpolierter Tiefe
    print("Pass 2: Lighting + Shadows ...")
    ascii_ramp = " .:-=+*#%@"
    out_lines = []
    
    for j in range(hoehe):
        zeile_chars = []
        for i in range(breite):
            t = tiefe_buffer[j][i]
            
            if t >= 20.0:
                # Himmel: simpler vertikaler Gradient
                sky_t = j / (hoehe - 1)
                val = sky_t * 0.3 + 0.1
            else:
                hx, hy, hz = hit_buffer[j][i]
                nx, ny, nz = normal_buffer[j][i]
                
                # Diffuse (Lambert)
                ndotl = nx*lx + ny*ly + nz*lz
                diff = max(0.0, ndotl)
                
                # Schatten vom Hit-Punkt aus
                bias = 0.01
                sh = shadow_raymarch(hx + nx*bias, hy + ny*bias, hz + nz*bias,
                                     lx, ly, lz, sharpness=shadow_sharpness)
                
                # Depth Fog
                fog = math.exp(-t * 0.07)
                
                # Kombinieren
                val = diff * sh * 0.85 + 0.15  # Ambient 0.15
                val = val * fog + 0.1 * (1.0 - fog)  # Fog mischt zu Himmel
            
            idx = int(max(0.0, min(1.0, val)) * (len(ascii_ramp) - 1))
            zeile_chars.append(ascii_ramp[idx])
        out_lines.append(''.join(zeile_chars))
    
    print("\n" + "=" * 60)
    for line in out_lines:
        print(line)
    print("=" * 60)
    print(f"\nFertig. Interpolationsmodus: {interp_mode} (1=Original, 2=Bilateral, 3=Smoothstep)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen. Tschüss!")
    except EOFError:
        print("\nKeine Eingabe möglich. Tschüss!")