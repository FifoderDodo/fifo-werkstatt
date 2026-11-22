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
    """Berechnet Normalen via zentrale Differenzen – schärfere Kanten durch kleineres Eps."""
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

def indirekter_schatten(ox, oy, oz, normal, licht_dir, max_dist=5.0, schritte=8):
    """Debug: Schattenwurf bei indirekter Beleuchtung (Bounce-Light).
    Prüft, ob der reflektierte Strahl auf Hindernisse trifft."""
    # Reflektionsrichtung: R = L - 2*(L·N)*N
    lx, ly, lz = licht_dir
    nx, ny, nz = normal
    ldotn = lx*nx + ly*ny + lz*nz
    rx = lx - 2.0 * ldotn * nx
    ry = ly - 2.0 * ldotn * ny
    rz = lz - 2.0 * ldotn * nz
    
    # Leicht versetzen, um Selbstschatten zu vermeiden
    ox += rx * 0.02
    oy += ry * 0.02
    oz += rz * 0.02
    
    schatten = 1.0
    for i in range(1, schritte + 1):
        h = max_dist * i / schritte
        d = szene_distanz(ox + rx*h, oy + ry*h, oz + rz*h)
        if d < 0.03:
            schatten = 0.0
            break
        schatten = min(schatten, d * schritte / (h * 0.8))
    return max(0.0, min(1.0, schatten))

def bilateral_filter(tiefe_buffer, normal_buffer, breite, hoehe, sigma_s=1.0, sigma_r=0.5):
    """Bilateral-Filter für Tiefe und Normalen – glättet Flächen, erhält Kanten."""
    neue_tiefe = [[0.0]*breite for _ in range(hoehe)]
    neue_normal = [[(0.0,0.0,0.0)]*breite for _ in range(hoehe)]
    for j in range(hoehe):
        for i in range(breite):
            d_center = tiefe_buffer[j][i]
            if d_center >= 19.0:
                neue_tiefe[j][i] = d_center
                neue_normal[j][i] = normal_buffer[j][i]
                continue
            n_center = normal_buffer[j][i]
            sum_w = 0.0
            sum_d = 0.0
            sum_nx, sum_ny, sum_nz = 0.0, 0.0, 0.0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ni, nj = i + dx, j + dy
                    if 0 <= ni < breite and 0 <= nj < hoehe:
                        d_n = tiefe_buffer[nj][ni]
                        if d_n >= 19.0:
                            continue
                        n_n = normal_buffer[nj][ni]
                        dist2 = dx*dx + dy*dy
                        w_s = math.exp(-dist2 / (2.0 * sigma_s * sigma_s))
                        diff = d_n - d_center
                        w_r = math.exp(-diff*diff / (2.0 * sigma_r * sigma_r))
                        w = w_s * w_r
                        sum_w += w
                        sum_d += d_n * w
                        sum_nx += n_n[0] * w
                        sum_ny += n_n[1] * w
                        sum_nz += n_n[2] * w
            if sum_w > 0:
                neue_tiefe[j][i] = sum_d / sum_w
                l = math.sqrt(sum_nx*sum_nx + sum_ny*sum_ny + sum_nz*sum_nz)
                if l > 0:
                    neue_normal[j][i] = (sum_nx/l, sum_ny/l, sum_nz/l)
                else:
                    neue_normal[j][i] = n_center
            else:
                neue_tiefe[j][i] = d_center
                neue_normal[j][i] = n_center
    return neue_tiefe, neue_normal

def render_szene(breite=80, hoehe=40):
    """Raymarch-Renderer mit verbesserter Schattierung: AO, Fresnel, weiche Schatten, Kantenglättung, indirekte Schatten."""
    # Kamera-Setup
    cam_x, cam_y, cam_z = 0.0, 0.5, -4.0
    fov = math.pi / 3.0
    aspect = breite / hoehe
    
    # Lichtrichtung (normalisiert)
    licht_dir = (0.5, 1.0, 0.3)
    l_len = math.sqrt(licht_dir[0]**2 + licht_dir[1]**2 + licht_dir[2]**2)
    licht_dir = (licht_dir[0]/l_len, licht_dir[1]/l_len, licht_dir[2]/l_len)
    
    # Buffer für Tiefe und Normalen
    tiefe_buffer = [[0.0]*breite for _ in range(hoehe)]
    normal_buffer = [[(0.0,0.0,0.0)]*breite for _ in range(hoehe)]
    pos_buffer = [[(0.0,0.0,0.0)]*breite for _ in range(hoehe)]
    hit_buffer = [[False]*breite for _ in range(hoehe)]
    
    # Raymarching-Schleife
    for j in range(hoehe):
        for i in range(breite):
            # NDC-Koordinaten
            u = (i + 0.5) / breite * 2.0 - 1.0
            v = (j + 0.5) / hoehe * 2.0 - 1.0
            v *= aspect  # Korrektur für Seitenverhältnis
            
            # Strahlrichtung
            dir_x = u * math.tan(fov * 0.5)
            dir_y = v * math.tan(fov * 0.5)
            dir_z = 1.0
            dir_len = math.sqrt(dir_x*dir_x + dir_y*dir_y + dir_z*dir_z)
            dir_x /= dir_len
            dir_y /= dir_len
            dir_z /= dir_len
            
            # Raymarching
            x, y, z = cam_x, cam_y, cam_z
            dist = 0.0
            for _ in range(64):
                d = szene_distanz(x, y, z)
                if d < 0.001:
                    break
                if dist > 20.0:
                    dist = 20.0
                    break
                x += dir_x * d
                y += dir_y * d
                z += dir_z * d
                dist += d
            
            if dist < 20.0:
                hit_buffer[j][i] = True
                tiefe_buffer[j][i] = dist
                pos_buffer[j][i] = (x, y, z)
                normal_buffer[j][i] = normal_berechnen(x, y, z)
            else:
                tiefe_buffer[j][i] = 20.0
                normal_buffer[j][i] = (0.0, 1.0, 0.0)
                pos_buffer[j][i] = (0.0, 0.0, 0.0)
    
    # Bilateraler Filter anwenden (glättet Tiefe und Normalen)
    tiefe_buffer, normal_buffer = bilateral_filter(tiefe_buffer, normal_buffer, breite, hoehe)
    
    # Shading
    ascii_ramp = " .'`^\"\,;:Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8@$B@$"  # erweiterte Rampe für feinere Abstufungen
    ramp_len = len(ascii_ramp)
    
    output_lines = []
    for j in range(hoehe):
        line_chars = []
        for i in range(breite):
            if not hit_buffer[j][i]:
                line_chars.append(' ')
                continue
            
            x, y, z = pos_buffer[j][i]
            normal = normal_buffer[j][i]
            view_dir = (-x + cam_x, -y + cam_y, -z + cam_z)
            v_len = math.sqrt(view_dir[0]**2 + view_dir[1]**2 + view_dir[2]**2)
            if v_len > 0:
                view_dir = (view_dir[0]/v_len, view_dir[1]/v_len, view_dir[2]/v_len)
            else:
                view_dir = (0.0, 0.0, 1.0)
            
            # Diffuse Beleuchtung
            ndotl = normal[0]*licht_dir[0] + normal[1]*licht_dir[1] + normal[2]*licht_dir[2]
            diff = max(0.0, ndotl)
            
            # Specular (Blinn-Phong)
            half_x = (licht_dir[0] + view_dir[0]) * 0.5
            half_y = (licht_dir[1] + view_dir[1]) * 0.5
            half_z = (licht_dir[2] + view_dir[2]) * 0.5
            h_len = math.sqrt(half_x**2 + half_y**2 + half_z**2)
            if h_len > 0:
                half_x /= h_len; half_y /= h_len; half_z /= h_len
                ndoth = normal[0]*half_x + normal[1]*half_y + normal[2]*half_z
                spec = max(0.0, ndoth) ** 32.0
            else:
                spec = 0.0
            
            # Weiche Schatten
            shadow = weicher_schatten(x, y, z, licht_dir)
            
            # Indirekter Schatten (Bounce-Light Occlusion)
            indirect_shadow = indirekter_schatten(x, y, z, normal, licht_dir)
            
            # Ambient Occlusion
            ao = ambiente_okklusion(x, y, z, normal)
            
            # Fresnel & Kantenschärfe
            fresnel = fresnel_effekt(normal, view_dir)
            kante = kanten_schaerfe(normal, view_dir)
            
            # Kombinierte Helligkeit mit Gamma-Korrektur für natürlichere Abstufung
            brightness = (0.15 * ao * indirect_shadow + 0.6 * diff * shadow + 0.15 * spec * shadow + 0.05 * fresnel + 0.05 * kante)
            brightness = max(0.0, min(1.0, brightness))
            # Gamma 2.2
            brightness = brightness ** (1.0/2.2)
            
            # Nebel (Depth Cueing)
            fog = 1.0 - min(1.0, tiefe_buffer[j][i] / 15.0)
            brightness *= fog
            
            # Mapping auf ASCII-Rampe
            idx = int(brightness * (ramp_len - 1))
            line_chars.append(ascii_ramp[idx])
        output_lines.append(''.join(line_chars))
    return '\n'.join(output_lines)

if __name__ == '__main__':
    try:
        # Optionale Eingabe für Breite/Höhe (Standard 80x40)
        breite_in = input('Breite (Default 80): ').strip()
        hoehe_in = input('Höhe (Default 40): ').strip()
        breite = int(breite_in) if breite_in else 80
        hoehe = int(hoehe_in) if hoehe_in else 40
    except (EOFError, ValueError):
        breite, hoehe = 80, 40
    
    print('Rendering...')
    result = render_szene(breite, hoehe)
    print(result)
    print('\nFertig.')