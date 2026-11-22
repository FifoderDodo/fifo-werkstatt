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
    d = szene_distanz(x, y, z)
    nx = szene_distanz(x + eps, y, z) - szene_distanz(x - eps, y, z)
    ny = szene_distanz(x, y + eps, z) - szene_distanz(x, y - eps, z)
    nz = szene_distanz(x, y, z + eps) - szene_distanz(x, y, z - eps)
    l = math.sqrt(nx*nx + ny*ny + nz*nz)
    if l > 0:
        return nx/l, ny/l, nz/l
    return 0.0, 1.0, 0.0

def kanten_schaerfe(normal, view_dir, schaerfe=8.0):
    ndotv = normal[0]*view_dir[0] + normal[1]*view_dir[1] + normal[2]*view_dir[2]
    return max(0.0, 1.0 - ndotv) ** schaerfe

def ambiente_okklusion(x, y, z, normal, schritte=5, radius=0.5):
    nx, ny, nz = normal
    ao = 0.0
    for i in range(1, schritte + 1):
        h = radius * i / schritte
        d = szene_distanz(x + nx*h, y + ny*h, z + nz*h)
        ao += max(0.0, h - d)
    return 1.0 - min(1.0, ao * 2.0 / schritte)

def fresnel_effekt(normal, view_dir, stark=3.0):
    ndotv = normal[0]*view_dir[0] + normal[1]*view_dir[1] + normal[2]*view_dir[2]
    return max(0.0, 1.0 - ndotv) ** stark

def weicher_schatten(ox, oy, oz, licht_dir, max_dist=10.0, schritte=16):
    lx, ly, lz = licht_dir
    schatten = 1.0
    for i in range(1, schritte + 1):
        h = max_dist * i / schritte
        d = szene_distanz(ox + lx*h, oy + ly*h, oz + lz*h)
        if d < 0.02:
            schatten = 0.0
            break
        schatten = min(schatten, d * schritte / (h * 0.5))
    return max(0.0, min(1.0, schatten))

def indirekter_schatten(ox, oy, oz, normal, licht_dir, max_dist=5.0, schritte=8):
    lx, ly, lz = licht_dir
    nx, ny, nz = normal
    ldotn = lx*nx + ly*ny + lz*nz
    rx = lx - 2.0 * ldotn * nx
    ry = ly - 2.0 * ldotn * ny
    rz = lz - 2.0 * ldotn * nz
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
    # Kamera-Position und Blickrichtung
    cam_x, cam_y, cam_z = 0.0, 0.5, -5.0
    # Blickrichtung: leicht nach unten auf die Kugel
    look_x, look_y, look_z = 0.0, 0.0, 3.0
    # Up-Vektor
    up_x, up_y, up_z = 0.0, 1.0, 0.0
    # Rechts-Vektor (Kreuzprodukt Blick x Up)
    right_x = look_y * up_z - look_z * up_y
    right_y = look_z * up_x - look_x * up_z
    right_z = look_x * up_y - look_y * up_x
    rl = math.sqrt(right_x*right_x + right_y*right_y + right_z*right_z)
    right_x, right_y, right_z = right_x/rl, right_y/rl, right_z/rl
    # Echter Up-Vektor (Rechts x Blick)
    up_x = right_y * look_z - right_z * look_y
    up_y = right_z * look_x - right_x * look_z
    up_z = right_x * look_y - right_y * look_x
    
    # FOV und Aspect
    fov = 0.8
    aspect = breite / hoehe
    
    # Lichtrichtung
    light_x, light_y, light_z = 0.5, 1.0, -0.3
    ll = math.sqrt(light_x*light_x + light_y*light_y + light_z*light_z)
    light_x, light_y, light_z = light_x/ll, light_y/ll, light_z/ll
    
    # Tiefe- und Normalen-Buffer
    tiefe_buffer = [[20.0]*breite for _ in range(hoehe)]
    normal_buffer = [[(0.0,0.0,0.0)]*breite for _ in range(hoehe)]
    hit_buffer = [[False]*breite for _ in range(hoehe)]
    
    max_steps = 80
    max_dist = 20.0
    
    for j in range(hoehe):
        for i in range(breite):
            # Pixel-Koordinaten [-1, 1]
            px = (i + 0.5) / breite * 2.0 - 1.0
            py = (j + 0.5) / hoehe * 2.0 - 1.0
            px *= aspect
            
            # Ray-Direktion
            dir_x = look_x * fov + right_x * px + up_x * py
            dir_y = look_y * fov + right_y * px + up_y * py
            dir_z = look_z * fov + right_z * px + up_z * py
            dl = math.sqrt(dir_x*dir_x + dir_y*dir_y + dir_z*dir_z)
            dir_x, dir_y, dir_z = dir_x/dl, dir_y/dl, dir_z/dl
            
            # Raymarching
            x, y, z = cam_x, cam_y, cam_z
            dist = 0.0
            for step in range(max_steps):
                d = szene_distanz(x, y, z)
                if d < 0.005:
                    hit_buffer[j][i] = True
                    tiefe_buffer[j][i] = dist
                    normal_buffer[j][i] = normal_berechnen(x, y, z)
                    break
                if dist > max_dist:
                    break
                x += dir_x * d
                y += dir_y * d
                z += dir_z * d
                dist += d
            else:
                tiefe_buffer[j][i] = 20.0
    
    # Bilateral Filter anwenden
    tiefe_buffer, normal_buffer = bilateral_filter(tiefe_buffer, normal_buffer, breite, hoehe)
    
    # ASCII-Rampe (erweitert für feinere Abstufungen)
    ascii_ramp = " .'`^\\\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8@B@$"
    
    # Bild rendern mit Beleuchtung
    out_lines = []
    for j in range(hoehe):
        line_chars = []
        for i in range(breite):
            if not hit_buffer[j][i]:
                # Himmel / Nebel
                tiefe = tiefe_buffer[j][i]
                neb = 1.0 - min(1.0, tiefe / max_dist)
                neb = neb * neb  # quadratisch für weicheren Übergang
                idx = int(neb * (len(ascii_ramp) - 1))
                line_chars.append(ascii_ramp[idx])
                continue
            
            # Trefferpunkt rekonstruieren
            # Wir nutzen die gespeicherte Tiefe und Normalen
            nx, ny, nz = normal_buffer[j][i]
            dist = tiefe_buffer[j][i]
            
            # Hit-Position
            hx = cam_x + (look_x * fov + right_x * ((i + 0.5) / breite * 2.0 - 1.0) * aspect + up_x * ((j + 0.5) / hoehe * 2.0 - 1.0)) * dist
            hy = cam_y + (look_y * fov + right_y * ((i + 0.5) / breite * 2.0 - 1.0) * aspect + up_y * ((j + 0.5) / hoehe * 2.0 - 1.0)) * dist
            hz = cam_z + (look_z * fov + right_z * ((i + 0.5) / breite * 2.0 - 1.0) * aspect + up_z * ((j + 0.5) / hoehe * 2.0 - 1.0)) * dist
            
            # View-Richtung (vom Hit zur Kamera)
            vx, vy, vz = -hx + cam_x, -hy + cam_y, -hz + cam_z
            vl = math.sqrt(vx*vx + vy*vy + vz*vz)
            if vl > 0:
                vx, vy, vz = vx/vl, vy/vl, vz/vl
            
            # Diffuse Beleuchtung
            ndotl = nx*light_x + ny*light_y + nz*light_z
            diffuse = max(0.0, ndotl) * 0.8
            
            # Ambient Occlusion
            ao = ambiente_okklusion(hx, hy, hz, (nx, ny, nz))
            
            # Weicher Schatten
            shadow = weicher_schatten(hx, hy, hz, (light_x, light_y, light_z))
            
            # Indirekter Schatten (subtil)
            indir_shadow = indirekter_schatten(hx, hy, hz, (nx, ny, nz), (light_x, light_y, light_z))
            
            # Fresnel
            fresnel = fresnel_effekt((nx, ny, nz), (vx, vy, vz)) * 0.3
            
            # Kantenschärfe
            edge = kanten_schaerfe((nx, ny, nz), (vx, vy, vz)) * 0.15
            
            # Gesamthelligkeit
            brightness = (diffuse * shadow * indir_shadow + 0.15) * ao + fresnel + edge
            brightness = max(0.0, min(1.0, brightness))
            
            # Gamma-Korrektur (2.2)
            brightness = brightness ** (1.0 / 2.2)
            
            # Nebel basierend auf Tiefe
            neb = 1.0 - min(1.0, dist / max_dist)
            brightness = brightness * (1.0 - neb * 0.4) + neb * 0.15
            
            idx = int(brightness * (len(ascii_ramp) - 1))
            line_chars.append(ascii_ramp[idx])
        out_lines.append(''.join(line_chars))
    
    return '\n'.join(out_lines)

def main():
    print("3D-Tiefen-Shader – Part 17: Gamma-Korrektur & Tiefen-Puffer")
    print("=========================================================")
    
    try:
        breite_in = input("Breite (Standard 80): ").strip()
        breite = int(breite_in) if breite_in else 80
        hoehe_in = input("Höhe (Standard 40): ").strip()
        hoehe = int(hoehe_in) if hoehe_in else 40
    except (ValueError, EOFError):
        breite, hoehe = 80, 40
    
    # Begrenzung
    breite = max(20, min(200, breite))
    hoehe = max(10, min(100, hoehe))
    
    print(f"\nRendere {breite}x{hoehe} ...")
    bild = render_szene(breite, hoehe)
    print(bild)
    print("\nFertig.")

if __name__ == "__main__":
    main()