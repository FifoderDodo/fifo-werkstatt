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
    """Gradient des SDF als Normalenvektor (normalisiert)."""
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
            # 4-Nachbarschaft sampeln
            sum_d = d
            count = 1
            for ni, nj in [(i-1, j), (i+1, j), (i, j-1), (i, j+1)]:
                if 0 <= ni < breite and 0 <= nj < hoehe:
                    dn = tiefe_buffer[nj][ni]
                    if dn < 20.0:
                        sum_d += dn
                        count += 1
            # Smoothstep-Gewichtung: Mitte stärker, Rand weicher
            # Einfaches Mittel reicht hier als Approximation
            zeile.append(sum_d / count)
        ergebnis.append(zeile)
    return ergebnis


def shade_pixel(tiefe: float, normal: tuple, schatten: float,
                ro: tuple, rd: tuple, licht_dir: tuple) -> tuple:
    """Farbberechnung mit spektraler Tiefe (Part 10: Kanal-abhängige Streuung).
    Simuliert wellenlängenabhängige Absorption/Streuung (Rot dringt tiefer)."""
    if tiefe >= 20.0:
        # Himmel: leichter Farbverlauf nach oben
        t = (rd[1] + 1.0) * 0.5
        r = 0.4 + 0.3 * t
        g = 0.5 + 0.3 * t
        b = 0.7 + 0.2 * t
        return (r, g, b)
    
    nx, ny, nz = normal
    lx, ly, lz = licht_dir
    vx, vy, vz = -rd[0], -rd[1], -rd[2]  # View Richtung (zur Kamera)
    
    # Diffuse (Lambert)
    ndotl = max(0.0, nx*lx + ny*ly + nz*lz)
    
    # Specular (Blinn-Phong)
    hx = lx + vx
    hy = ly + vy
    hz = lz + vz
    hlen = math.sqrt(hx*hx + hy*hy + hz*hz)
    if hlen > 0:
        hx, hy, hz = hx/hlen, hy/hlen, hz/hlen
        ndoth = max(0.0, nx*hx + ny*hy + nz*hz)
        spec = ndoth ** 32.0
    else:
        spec = 0.0
    
    # Fresnel-Schicht (Schlick-Approximation)
    vdotn = max(0.0, vx*nx + vy*ny + vz*nz)
    fresnel = 0.04 + 0.96 * (1.0 - vdotn) ** 5
    
    # --- Part 10: Spektrale Tiefe / Kanal-abhängige Dämpfung ---
    # Tiefe normalisieren (0..1 im nahen Bereich)
    t_norm = min(1.0, tiefe / 8.0)
    
    # Basis-Albedo (Materialfarbe)
    base_r, base_g, base_b = 0.85, 0.75, 0.65  # warmer Sand/Lehm Ton
    
    # Subsurface / Transluzenz Approximation: Licht dringt ein, streut, tritt aus
    # Rotes Licht streut stärker / dringt tiefer -> bei Grazwinkeln mehr Rot
    scatter_r = 1.0 + 0.4 * (1.0 - vdotn) * (1.0 - ndotl)
    scatter_g = 1.0 + 0.2 * (1.0 - vdotn) * (1.0 - ndotl)
    scatter_b = 1.0 + 0.05 * (1.0 - vdotn) * (1.0 - ndotl)
    
    # Tiefen-Dämpfung (Fog/Atmosphäre im Material)
    # Blau wird schneller absorbiert -> Tiefe wirkt wärmer
    depth_damp_r = math.exp(-t_norm * 0.15)
    depth_damp_g = math.exp(-t_norm * 0.25)
    depth_damp_b = math.exp(-t_norm * 0.45)
    
    # Diffuse Beleuchtung pro Kanal
    diff_r = base_r * ndotl * scatter_r * depth_damp_r
    diff_g = base_g * ndotl * scatter_g * depth_damp_g
    diff_b = base_b * ndotl * scatter_b * depth_damp_b
    
    # Specular ist meist achromatisch (dielektrisch) aber leicht gefärbt durch Fresnel
    spec_r = spec * (0.9 + 0.1 * fresnel)
    spec_g = spec * (0.9 + 0.1 * fresnel)
    spec_b = spec * (0.95 + 0.05 * fresnel)
    
    # Ambient / Himmel Licht (füllt Schatten)
    amb_r = base_r * 0.15 * depth_damp_r
    amb_g = base_g * 0.18 * depth_damp_g
    amb_b = base_b * 0.25 * depth_damp_b
    
    # Kombinieren mit Schatten
    r = (diff_r + spec_r) * schatten + amb_r
    g = (diff_g + spec_g) * schatten + amb_g
    b = (diff_b + spec_b) * schatten + amb_b
    
    # Gamma-Korrektur (sRGB approx)
    r = r ** (1.0/2.2)
    g = g ** (1.0/2.2)
    b = b ** (1.0/2.2)
    
    # Clamp
    return (min(1.0, max(0.0, r)), min(1.0, max(0.0, g)), min(1.0, max(0.0, b)))


def rgb_to_ascii(r: float, g: float, b: float) -> str:
    """Wandelt Farbwert in ASCII-Zeichen basierend auf Helligkeit um."""
    # Luminanz (Rec. 709)
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    # Zeichen-Rampe von dunkel nach hell
    ramp = " .'`^\"\,;:Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8@B@$"
    idx = int(lum * (len(ramp) - 1))
    return ramp[idx]


def main():
    print("🦤 Fifo's 3D-Tiefen-Shader — Part 10: Spektrale Kanal-Tiefe")
    print("======================================================")
    
    # Auflösung (klein für ASCII, groß für PPM)
    try:
        breite = int(input("Breite (z.B. 120): ") or "120")
        hoehe = int(input("Höhe (z.B. 60): ") or "60")
    except (EOFError, ValueError):
        breite, hoehe = 120, 60
    
    # Interpolations-Modus wählen
    print("\nTiefen-Interpolation:")
    print("  1 = Keine (Roh)")
    print("  2 = Bilateral (kantenerhaltend, langsamer)")
    print("  3 = Smoothstep (einfach, schnell)")
    try:
        modus = int(input("Wähle [1-3]: ") or "2")
    except (EOFError, ValueError):
        modus = 2
    
    # Kamera-Parameter
    fov = 0.8  # ~90 Grad
    aspect = breite / hoehe
    ro = (0.0, 0.8, -4.0)  # Kamera-Position
    # Blickrichtung: leicht nach unten auf die Kugel
    look_at = (0.0, 0.0, 3.0)
    forward = (look_at[0]-ro[0], look_at[1]-ro[1], look_at[2]-ro[2])
    flen = math.sqrt(forward[0]**2 + forward[1]**2 + forward[2]**2)
    forward = (forward[0]/flen, forward[1]/flen, forward[2]/flen)
    right = (forward[2], 0.0, -forward[0])  # Vereinfacht: keine Roll
    rlen = math.sqrt(right[0]**2 + right[2]**2)
    right = (right[0]/rlen, 0.0, right[2]/rlen)
    up = (0.0, 1.0, 0.0)
    
    licht_dir = (0.5, 1.0, -0.3)
    llen = math.sqrt(licht_dir[0]**2 + licht_dir[1]**2 + licht_dir[2]**2)
    licht_dir = (licht_dir[0]/llen, licht_dir[1]/llen, licht_dir[2]/llen)
    
    print(f"\nRendere {breite}x{hoehe} ...")
    
    # 1. Raymarching: Tiefen- & Normalen-Puffer füllen
    tiefe_buffer = []
    normal_buffer = []
    
    for j in range(hoehe):
        zeile_t = []
        zeile_n = []
        # Fortschrittsanzeige
        if j % max(1, hoehe//10) == 0:
            sys.stdout.write(f"\rZeile {j+1}/{hoehe}")
            sys.stdout.flush()
        
        for i in range(breite):
            # NDC Koordinaten
            u = (i + 0.5) / breite * 2.0 - 1.0
            v = (j + 0.5) / hoehe * 2.0 - 1.0  # y nach unten
            u *= aspect
            
            # Strahlrichtung
            dx = forward[0] + right[0] * u * fov + up[0] * v * fov
            dy = forward[1] + right[1] * u * fov + up[1] * v * fov
            dz = forward[2] + right[2] * u * fov + up[2] * v * fov
            dlen = math.sqrt(dx*dx + dy*dy + dz*dz)
            dx, dy, dz = dx/dlen, dy/dlen, dz/dlen
            
            # Marchieren
            t = raymarch(ro[0], ro[1], ro[2], dx, dy, dz)
            zeile_t.append(t)
            
            if t < 20.0:
                px = ro[0] + dx * t
                py = ro[1] + dy * t
                pz = ro[2] + dz * t
                n = szene_normal(px, py, pz)
                zeile_n.append(n)
            else:
                zeile_n.append((0.0, 1.0, 0.0))
        tiefe_buffer.append(zeile_t)
        normal_buffer.append(zeile_n)
    
    print("\nRaymarching fertig. Interpoliere Tiefe...")
    
    # 2. Tiefen-Interpolation
    if modus == 2:
        tiefe_buffer = depth_interpolate_bilateral(tiefe_buffer, normal_buffer, breite, hoehe)
    elif modus == 3:
        tiefe_buffer = depth_interpolate_smoothstep(tiefe_buffer, breite, hoehe)
    # else: Modus 1 = Roh
    
    print("Interoplation fertig. Berechne Schatten & Shading...")
    
    # 3. Schatten & Shading Pass + Ausgabe
    out_lines = []
    for j in range(hoehe):
        line_chars = []
        for i in range(breite):
            t = tiefe_buffer[j][i]
            n = normal_buffer[j][i]
            
            if t < 20.0:
                px = ro[0] + ( (i+0.5)/breite*2-1)*aspect*fov * t  # approx, besser: rd speichern
                # Wir rechnen rd neu für Shadow-Ray Origin Offset
                u = (i + 0.5) / breite * 2.0 - 1.0
                v = (j + 0.5) / hoehe * 2.0 - 1.0
                u *= aspect
                dx = forward[0] + right[0] * u * fov + up[0] * v * fov
                dy = forward[1] + right[1] * u * fov + up[1] * v * fov
                dz = forward[2] + right[2] * u * fov + up[2] * v * fov
                dlen = math.sqrt(dx*dx + dy*dy + dz*dz)
                rd = (dx/dlen, dy/dlen, dz/dlen)
                
                # Shadow Origin mit Normalen-Offset (Self-Shadowing Artifacts reduzieren)
                sox = ro[0] + rd[0] * t + n[0] * 0.01
                soy = ro[1] + rd[1] * t + n[1] * 0.01
                soz = ro[2] + rd[2] * t + n[2] * 0.01
                
                schatten = shadow_raymarch(sox, soy, soz,
                                           licht_dir[0], licht_dir[1], licht_dir[2])
            else:
                # Himmel braucht keinen Shadow-Ray
                rd = (0,0,1) # dummy
                schatten = 1.0
            
            r, g, b = shade_pixel(t, n, schatten, ro, rd, licht_dir)
            ch = rgb_to_ascii(r, g, b)
            line_chars.append(ch)
        out_lines.append("" .join(line_chars))
    
    print("\nFertig! Ausgabe:")
    print("=" * breite)
    for line in out_lines:
        print(line)
    print("=" * breite)
    
    # Optional: PPM speichern für Farb-Check
    try:
        save = input("\nAls PPM speichern? (j/n): ").strip().lower()
        if save == 'j':
            fname = "depth_shader_10.ppm"
            with open(fname, "w") as f:
                f.write(f"P3\n{breite} {hoehe}\n255\n")
                for j in range(hoehe):
                    line_vals = []
                    for i in range(breite):
                        t = tiefe_buffer[j][i]
                        n = normal_buffer[j][i]
                        if t < 20.0:
                            u = (i + 0.5) / breite * 2.0 - 1.0
                            v = (j + 0.5) / hoehe * 2.0 - 1.0
                            u *= aspect
                            dx = forward[0] + right[0] * u * fov + up[0] * v * fov
                            dy = forward[1] + right[1] * u * fov + up[1] * v * fov
                            dz = forward[2] + right[2] * u * fov + up[2] * v * fov
                            dlen = math.sqrt(dx*dx + dy*dy + dz*dz)
                            rd = (dx/dlen, dy/dlen, dz/dlen)
                            sox = ro[0] + rd[0] * t + n[0] * 0.01
                            soy = ro[1] + rd[1] * t + n[1] * 0.01
                            soz = ro[2] + rd[2] * t + n[2] * 0.01
                            schatten = shadow_raymarch(sox, soy, soz,
                                                       licht_dir[0], licht_dir[1], licht_dir[2])
                        else:
                            rd = (0,0,1)
                            schatten = 1.0
                        r, g, b = shade_pixel(t, n, schatten, ro, rd, licht_dir)
                        line_vals.append(f"{int(r*255)} {int(g*255)} {int(b*255)}")
                    f.write(" " .join(line_vals) + "\n")
            print(f"Gespeichert als {fname}")
    except EOFError:
        pass
    
    print("\n🦤 Fifo wackelt zufrieden mit den Flügeln. Nächster Part: Partikel & Volumen?")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🦤 Abgebrochen. Bis zum nächsten Mal!")
    except EOFError:
        print("\n🦤 Kein Input mehr. Tschüss!")