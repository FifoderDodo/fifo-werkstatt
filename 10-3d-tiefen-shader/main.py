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
                    max_schritte: int = 50, max_dist: float = 20.0,
                    softness: float = 0.5) -> float:
    """Soft-Shadow Raymarching.
    Statt hart 0/1 wird ein Schattenfaktor akkumuliert:
    Bei jedem Schritt schauen wir, wie nah wir an Geometrie sind (dist).
    Je näher dist an 0, desto dunkler. Der Faktor softness steuert die Penumbra-Weite.
    Gibt 1.0 = voll beleuchtet, 0.0 = tiefster Schatten."""
    tiefe = 0.0
    schatten = 1.0
    # Start-Bias wird vom Aufrufer über den versetzten Startpunkt gemacht
    for _ in range(max_schritte):
        px = ox + lx * tiefe
        py = oy + ly * tiefe
        pz = oz + lz * tiefe
        dist = szene_distanz(px, py, pz)
        # Soft-Shadow-Formel: je kleiner dist / tiefe, desto stärkerer Schatten
        # softness ~ Penumbra-Größe (größer = weichere Kanten)
        if tiefe > 0.0:
            schatten = min(schatten, softness * dist / tiefe)
        if dist < 0.008:  # Harter Treffer -> fast vollständig im Schatten
            return 0.0
        tiefe += dist
        if tiefe > max_dist:
            break
    return max(0.0, min(1.0, schatten))


def main() -> None:
    print("Fifo's 3D-Tiefen-Shader - Teil 5: Soft-Shadow Raymarching & Parameter-Tuning")
    print("====================================================================")
    
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
    
    # Lichtrichtung
    lx, ly, lz = 1.0, 2.0, -1.0
    lleng = math.sqrt(lx*lx + ly*ly + lz*lz)
    lx, ly, lz = lx/lleng, ly/lleng, lz/lleng
    
    tiefe_buffer = []
    schatten_buffer = []
    
    for j in range(hoehe):
        zeile_tiefen = []
        zeile_schatten = []
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
                
                # Normal-Map-Bias für Schattenstrahl-Startpunkt
                bias = 0.015
                sx = hx + nx * bias
                sy = hy + ny * bias
                sz = hz + nz * bias
                
                # Soft Shadow Raymarch
                # softness: 0.3 = härter, 0.8 = weicher (Penumbra)
                # max_schritte: 50 für guten Kompromiss Geschwindigkeit/Qualität
                shadow = shadow_raymarch(sx, sy, sz, lx, ly, lz,
                                         max_schritte=50, max_dist=20.0, softness=0.5)
                
                diff = max(0.0, nx*lx + ny*ly + nz*lz)
                ambient = 0.15  # Etwas dunkleres Ambient für mehr Kontrast
                nebelfaktor = 1.0 - min(1.0, t / 20.0)
                helligkeit = ambient + diff * shadow * nebelfaktor
                zeile_schatten.append(helligkeit)
            else:
                zeile_schatten.append(0.0)
        tiefe_buffer.append(zeile_tiefen)
        schatten_buffer.append(zeile_schatten)
    
    # ASCII-Rampe: dunkler -> heller
    ascii_ramp = " .'`^\":;~!><{}[]()\\/|\\?-_+@#$%&*8BW"
    ramp_len = len(ascii_ramp) - 1
    
    print()
    for j in range(hoehe):
        zeile = ""
        for i in range(breite):
            val = schatten_buffer[j][i]
            idx = int(val * ramp_len)
            if idx < 0: idx = 0
            if idx > ramp_len: idx = ramp_len
            zeile += ascii_ramp[idx]
        print(zeile)
    
    print()
    print("Fertig. Drück Enter für Exit.")
    try:
        input()
    except EOFError:
        pass


if __name__ == "__main__":
    main()