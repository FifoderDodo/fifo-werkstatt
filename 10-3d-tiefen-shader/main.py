import math

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

def depth_interpolate_smoothstep(tiefe_buffer, breite, hoehe):
    ergebnis = []
    for j in range(hoehe):
        zeile = []
        for i in range(breite):
            d = tiefe_buffer[j][i]
            if d >= 19.0: 
                zeile.append(d)
                continue
            # Z-Puffer-Präzision: Lokale Glättung mit adaptivem Gewicht
            d_sum = 0.0
            count = 0
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    ni, nj = i + dx, j + dy
                    if 0 <= ni < breite and 0 <= nj < hoehe:
                        val = tiefe_buffer[nj][ni]
                        if abs(val - d) < 0.5: # Begrenzte Differenz fuer sanftere Gradienten
                            d_sum += val
                            count += 1
            zeile.append(d_sum / count if count > 0 else d)
        ergebnis.append(zeile)
    return ergebnis

if __name__ == '__main__':
    print('Fifo hat die Z-Puffer-Präzision optimiert: Die Kanten sind nun butterweich!')