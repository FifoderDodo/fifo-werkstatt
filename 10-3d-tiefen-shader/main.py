import math
import sys

def noise3d(x, y, z):
    ix, iy, iz = int(math.floor(x)), int(math.floor(y)), int(math.floor(z))
    fx, fy, fz = x - ix, y - iy, z - iz
    u, v, w = fx*fx*(3.0-2.0*fx), fy*fy*(3.0-2.0*fy), fz*fz*(3.0-2.0*fz)
    def hash(i, j, k):
        n = (i + j*57 + k*131) & 0x7fffffff
        n = (n ^ (n >> 13)) * 0x5bd1e995
        return (n ^ (n >> 15) & 0x7fffffff) / 0x7fffffff
    a, b = hash(ix, iy, iz), hash(ix+1, iy, iz)
    c, d = hash(ix, iy+1, iz), hash(ix+1, iy+1, iz)
    e, f = hash(ix, iy, iz+1), hash(ix+1, iy, iz+1)
    g, h = hash(ix, iy+1, iz+1), hash(ix+1, iy+1, iz+1)
    x1 = a + (b - a) * u
    x2 = c + (d - c) * u
    y1 = x1 + (x2 - x1) * v
    x3 = e + (f - e) * u
    x4 = g + (h - g) * u
    y2 = x3 + (x4 - x3) * v
    return y1 + (y2 - y1) * w

def szene_distanz(x, y, z):
    kugel = math.sqrt(x*x + y*y + (z-3.0)**2) - 1.0 - 0.08 * noise3d(x*2.5, y*2.5, z*2.5)
    boden = y + 1.0 - 0.12 * noise3d(x*3.0, 0.0, z*3.0)
    return min(kugel, boden)

def normal_berechnen(x, y, z, eps=0.001):
    """Berechnet Normalen via zentrale Differenzen – schärfere Kanten durch kleinere Eps."""
    d = szene_distanz(x, y, z)
    nx = szene_distanz(x + eps, y, z) - szene_distanz(x - eps, y, z)
    ny = szene_distanz(x, y + eps, z) - szene_distanz(x, y - eps, z)
    nz = szene_distanz(x, y, z + eps) - szene_distanz(x, y, z - eps)
    l = math.sqrt(nx*nx + ny*ny + nz*nz)
    if l > 0:
        return nx/l, ny/l, nz/l
    return 0.0, 1.0, 0.0

def kanten_schaerfe(normal, view_dir, schaerfe=8.0):
    """Laternen-Schatten-Effekt: Hebt Kanten hervor durch Normalen-View-Winkel."""
    ndotv = normal[0]*view_dir[0] + normal[1]*view_dir[1] + normal[2]*view_dir[2]
    return max(0.0, 1.0 - ndotv) ** schaerfe

def ambiente_okklusion(x, y, z, normal, schritte=5, radius=0.5):
    """Approximiert Ambient Occlusion durch Raymarching in Normalenrichtung."""
    nx, ny, nz = normal
    ao = 0.0
    for i in range(1, schritte + 1):
        h = radius * i / schritte
        d = szene_distanz(x + nx*h, y + ny*h, z + nz*h)
        ao += max(0.0, h - d)
    return 1.0 - min(1.0, ao * 2.0 / schritte)

def fresnel_effekt(normal, view_dir, stark=3.0):
    """Fresnel-Schimmer an Silhouetten – simuliert dünne Kanten-Lichter."""
    ndotv = normal[0]*view_dir[0] + normal[1]*view_dir[1] + normal[2]*view_dir[2]
    return max(0.0, 1.0 - ndotv) ** stark

def weicher_schatten(ox, oy, oz, licht_dir, max_dist=10.0, schritte=16):
    """Weiche Schatten durch Cone-Tracing entlang der Lichtrichtung."""
    lx, ly, lz = licht_dir
    schatten = 1.0
    for i in range(1, schritte + 1):
        h = max_dist * i / schritte
        d = szene_distanz(ox + lx*h, oy + ly*h, oz + lz*h)
        if d < 0.02:
            schatten = 0.0
            break
        # Penumbra: je näher an Hindernis, desto dunkler
        schatten = min(schatten, d * schritte / (h * 0.5))
    return max(0.0, min(1.0, schatten))

def depth_interpolate_smoothstep(tiefe_buffer, breite, hoehe):
    ergebnis = []
    for j in range(hoehe):
        zeile = []
        for i in range(breite):
            d = tiefe_buffer[j][i]
            if d >= 19.0:
                zeile.append(d)
                continue
            d_sum = 0.0
            count = 0
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    ni, nj = i + dx, j + dy
                    if 0 <= ni < breite and 0 <= nj < hoehe:
                        val = tiefe_buffer[nj][ni]
                        if abs(val - d) < 0.5:
                            d_sum += val
                            count += 1
            zeile.append(d_sum / count if count > 0 else d)
        ergebnis.append(zeile)
    return ergebnis

def render_szene(breite=80, hoehe=40):
    """Raymarch-Renderer mit verbesserter Schattierung: AO, Fresnel, weiche Schatten."""
    tiefe_buffer = [[20.0]*breite for _ in range(hoehe)]
    normal_buffer = [[(0,1,0)]*breite for _ in range(hoehe)]
    pos_buffer = [[(0,0,0)]*breite for _ in range(hoehe)]
    
    cam_x, cam_y, cam_z = 0.0, 0.5, -5.0
    
    for j in range(hoehe):
        for i in range(breite):
            fx = (i - breite/2) / (breite/2) * 1.2
            fy = (j - hoehe/2) / (hoehe/2) * 0.8
            fz = 1.0
            rl = math.sqrt(fx*fx + fy*fy + fz*fz)
            rdx, rdy, rdz = fx/rl, fy/rl, fz/rl
            
            ox, oy, oz = cam_x, cam_y, cam_z
            dist = 0.0
            for _ in range(64):
                d = szene_distanz(ox, oy, oz)
                if d < 0.01:
                    tiefe_buffer[j][i] = dist
                    normal_buffer[j][i] = normal_berechnen(ox, oy, oz)
                    pos_buffer[j][i] = (ox, oy, oz)
                    break
                if dist > 20.0:
                    break
                ox += rdx * d
                oy += rdy * d
                oz += rdz * d
                dist += d
    
    tiefe_buffer = depth_interpolate_smoothstep(tiefe_buffer, breite, hoehe)
    
    # Licht-Setup
    licht = (0.3, 0.8, 0.5)
    ll = math.sqrt(licht[0]**2 + licht[1]**2 + licht[2]**2)
    licht = (licht[0]/ll, licht[1]/ll, licht[2]/ll)
    view = (0, 0, 1)
    
    # Erweiterte ASCII-Rampe für feinere Abstufungen
    ascii_ramp = "  .'`^\":;~!><{}[]()_+-=*#%@&$"
    
    bild = []
    for j in range(hoehe):
        zeile = ""
        for i in range(breite):
            d = tiefe_buffer[j][i]
            if d >= 19.0:
                zeile += " "
                continue
            
            nx, ny, nz = normal_buffer[j][i]
            px, py, pz = pos_buffer[j][i]
            
            # 1. Diffuses Licht (Lambert)
            diff = max(0.0, nx*licht[0] + ny*licht[1] + nz*licht[2])
            
            # 2. Ambient Occlusion – vertieft Ecken und Kanten
            ao = ambiente_okklusion(px, py, pz, (nx, ny, nz))
            
            # 3. Weiche Schatten – realistischer als harte Schatten
            schatten = weicher_schatten(px + nx*0.01, py + ny*0.01, pz + nz*0.01, licht)
            
            # 4. Kanten-Schärfung (Laternen-Look)
            kante = kanten_schaerfe((nx, ny, nz), view, 6.0)
            
            # 5. Fresnel-Schimmer an Silhouetten
            fresnel = fresnel_effekt((nx, ny, nz), view, 4.0)
            
            # 6. Tiefen-Nebel (Atmosphäre)
            nebelfaktor = max(0.0, 1.0 - d / 12.0)
            
            # Kombinieren: Basis + AO + Schatten + Kanten + Fresnel
            helligkeit = (diff * 0.5 + 0.15) * ao * schatten  # Basis-Beleuchtung
            helligkeit += kante * 0.35  # Laternen-Kanten
            helligkeit += fresnel * 0.25  # Silhouetten-Schimmer
            helligkeit *= nebelfaktor  # Entfernungs-Abschwächung
            
            # Gamma-Korrektur für natürlichere Helligkeitsverteilung
            helligkeit = helligkeit ** 0.9
            helligkeit = max(0.0, min(1.0, helligkeit))
            
            idx = int(helligkeit * (len(ascii_ramp) - 1))
            zeile += ascii_ramp[idx]
        bild.append(zeile)
    return bild

if __name__ == '__main__':
    print('Fifo schleift die Schattierung: AO, Fresnel, weiche Schatten – Tiefe wird greifbar!')
    print()
    try:
        bild = render_szene()
        for zeile in bild:
            print(zeile)
    except KeyboardInterrupt:
        pass
    print()
    print('Projekt 3D-Tiefen-Shader: Schattierungs-Routine getestet – Fifo nickt zufrieden.')