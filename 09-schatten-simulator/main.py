# main.py – Schatten‑Simulator, Teil 20
# Fifo, der Dodo, träumt den letzten Schliff: Speichern, Batch‑Modus, kleine Aufräumarbeiten.

from __future__ import annotations
import math
import sys
import random
from typing import List, Tuple, Optional

Vec3 = Tuple[float, float, float]

# ---------- Vektor‑Hilfsfunktionen ----------

def vec3_norm(v: Vec3) -> Vec3:
    x, y, z = v
    l = math.sqrt(x * x + y * y + z * z)
    if l < 1e-9:
        return (0.0, 0.0, 1.0)
    return (x / l, y / l, z / l)

def vec3_dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

def vec3_add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

def vec3_scale(v: Vec3, s: float) -> Vec3:
    return (v[0] * s, v[1] * s, v[2] * s)

def vec3_sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def vec3_mul(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] * b[0], a[1] * b[1], a[2] * b[2])

# ---------- Tiefenkarte und Normalen ----------

class Tiefenkarte:
    """Hält ein 2D‑Höhenfeld und liefert Normalen, Statistik usw."""

    def __init__(self, daten: List[List[float]]):
        self.daten = [reihe[:] for reihe in daten]
        self.h = len(daten)
        self.b = len(daten[0]) if self.h > 0 else 0

    def get(self, y: int, x: int, default: float = 0.0) -> float:
        if 0 <= y < self.h and 0 <= x < self.b:
            return self.daten[y][x]
        return default

    def get_bilinear(self, y: float, x: float) -> float:
        y0 = max(0, min(self.h - 1, int(math.floor(y))))
        x0 = max(0, min(self.b - 1, int(math.floor(x))))
        y1 = max(0, min(self.h - 1, y0 + 1))
        x1 = max(0, min(self.b - 1, x0 + 1))
        dy = y - y0
        dx = x - x0
        h00 = self.daten[y0][x0]
        h01 = self.daten[y0][x1]
        h10 = self.daten[y1][x0]
        h11 = self.daten[y1][x1]
        h0 = h00 * (1.0 - dx) + h01 * dx
        h1 = h10 * (1.0 - dx) + h11 * dx
        return h0 * (1.0 - dy) + h1 * dy

    def setze(self, y: int, x: int, wert: float) -> bool:
        if 0 <= y < self.h and 0 <= x < self.b and 0.0 <= wert <= 1.0:
            self.daten[y][x] = wert
            return True
        return False

    def normalen(self, z_skalierung: float = 2.0) -> List[List[Vec3]]:
        normals: List[List[Vec3]] = []
        for y in range(self.h):
            reihe: List[Vec3] = []
            for x in range(self.b):
                hx = (self.get(y, x + 1) - self.get(y, x - 1)) * 0.5 * z_skalierung
                hy = (self.get(y + 1, x) - self.get(y - 1, x)) * 0.5 * z_skalierung
                reihe.append(vec3_norm((-hx, -hy, 1.0)))
            normals.append(reihe)
        return normals

    def statistik(self) -> Tuple[float, float, float]:
        flach = [w for reihe in self.daten for w in reihe]
        if not flach:
            return 0.0, 0.0, 0.0
        mn, mx = min(flach), max(flach)
        return mn, mx, mx - mn

# ---------- Formen erzeugen ----------

def erzeuge_kugel(h: int = 20, b: int = 40, r_rel: float = 0.42) -> Tiefenkarte:
    karte = [[0.0 for _ in range(b)] for _ in range(h)]
    cy, cx = (h - 1) / 2.0, (b - 1) / 2.0
    radius = min(h, b) * r_rel
    for y in range(h):
        for x in range(b):
            dy = y - cy
            dx = (x - cx) * 0.5
            dist_sq = dx * dx + dy * dy
            if dist_sq <= radius * radius:
                karte[y][x] = math.sqrt(radius * radius - dist_sq) / radius
    return Tiefenkarte(karte)

def erzeuge_kegel(h: int = 20, b: int = 40, r_rel: float = 0.45) -> Tiefenkarte:
    karte = [[0.0 for _ in range(b)] for _ in range(h)]
    cy, cx = (h - 1) / 2.0, (b - 1) / 2.0
    radius = min(h, b) * r_rel
    for y in range(h):
        for x in range(b):
            dy = y - cy
            dx = (x - cx) * 0.5
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= radius:
                karte[y][x] = 1.0 - (dist / radius)
    return Tiefenkarte(karte)

def erzeuge_stufenpyramide(h: int = 20, b: int = 40) -> Tiefenkarte:
    karte = [[0.0 for _ in range(b)] for _ in range(h)]
    cy, cx = (h - 1) / 2.0, (b - 1) / 2.0
    for y in range(h):
        for x in range(b):
            dy = abs(y - cy) / (h * 0.45)
            dx = abs(x - cx) / (b * 0.45)
            dist = max(dx, dy)
            if dist < 1.0:
                karte[y][x] = math.floor((1.0 - dist) * 4.0) / 4.0
    return Tiefenkarte(karte)

def erzeuge_wellblech(h: int = 20, b: int = 40, wellen: int = 8) -> Tiefenkarte:
    """Wellförmiges Höhenfeld (ähnlich Wellblech)."""
    karte = [[0.0 for _ in range(b)] for _ in range(h)]
    for y in range(h):
        for x in range(b):
            val = 0.5 + 0.5 * math.sin(2.0 * math.pi * wellen * x / b + 0.5 * math.sin(2.0 * math.pi * y / h))
            karte[y][x] = val
    return Tiefenkarte(karte)

# ---------- Beleuchtungs‑ und Schatten‑Funktionen ----------

def diffuse_schatten(normals: List[List[Vec3]], licht_dir: Vec3) -> List[List[float]]:
    lx, ly, lz = vec3_norm(licht_dir)
    result: List[List[float]] = []
    for reihe in normals:
        rreihe: List[float] = []
        for nx, ny, nz in reihe:
            dot = nx * lx + ny * ly + nz * lz
            rreihe.append(max(0.0, dot))
        result.append(rreihe)
    return result

def harte_schatten_raymarch(karte: Tiefenkarte, licht_dir: Vec3,
                            schritte: int = 32, bias: float = 0.005) -> List[List[float]]:
    """Einfacher harte Schatten per Ray‑Marching entlang Licht‑Richtung."""
    lx, ly, lz = vec3_norm(licht_dir)
    h, b = karte.h, karte.b
    l_xy = math.sqrt(lx * lx + ly * ly)
    if l_xy < 1e-6:
        return [[1.0] * b for _ in range(h)]

    max_d = math.sqrt(h * h + b * b)
    step_xy = max_d / schritte
    inv_xy = 1.0 / l_xy
    dir_x = -lx * inv_xy * step_xy
    dir_y = -ly * inv_xy * step_xy
    step_z = lz * inv_xy * step_xy * 0.1

    schatten: List[List[float]] = [[1.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            h0 = karte.daten[y][x]
            if h0 <= 0.0:
                continue
            px = float(x)
            py = float(y)
            pz = h0 + bias
            blocked = False
            for _ in range(schritte):
                px += dir_x
                py += dir_y
                pz += step_z
                if px < 0 or px >= b - 1 or py < 0 or py >= h - 1:
                    break
                h_hier = karte.get_bilinear(py, px)
                if pz <= h_hier:
                    blocked = True
                    break
            if blocked:
                schatten[y][x] = 0.0
    return schatten

def weiche_schatten(harte: List[List[float]], radius: int = 1) -> List[List[float]]:
    """Box‑Blur für weiche Schattenkanten."""
    h = len(harte)
    b = len(harte[0]) if h > 0 else 0
    if radius <= 0:
        return harte
    tmp = [[0.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            s = 0.0
            n = 0
            for dy in range(-radius, radius + 1):
                yy = y + dy
                if 0 <= yy < h:
                    for dx in range(-radius, radius + 1):
                        xx = x + dx
                        if 0 <= xx < b:
                            s += harte[yy][xx]
                            n += 1
            tmp[y][x] = s / n if n else 0.0
    return tmp

def ssao(karte: Tiefenkarte, normalen: List[List[Vec3]],
         samples: int = 8, radius: float = 1.5) -> List[List[float]]:
    """Sehr einfaches Screen‑Space Ambient Occlusion."""
    h, b = karte.h, karte.b
    ao = [[1.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            n = normalen[y][x]
            if n[2] < 0.1:
                continue
            occ = 0
            for _ in range(samples):
                angle = random.random() * 2.0 * math.pi
                dist = random.random() * radius
                sx = x + math.cos(angle) * dist
                sy = y + math.sin(angle) * dist
                if 0 <= sx < b - 1 and 0 <= sy < h - 1:
                    h_s = karte.get_bilinear(sy, sx)
                    if h_s > karte.get_bilinear(y, x) + 0.05:
                        occ += 1
            ao[y][x] = 1.0 - (occ / samples) * 0.5
    return ao

def blinn_phong(normalen: List[List[Vec3]], licht_dir: Vec3,
                view_dir: Vec3 = (0.0, 0.0, 1.0),
                shininess: float = 32.0) -> List[List[float]]:
    """Blinn‑Phong Specular Term."""
    l = vec3_norm(licht_dir)
    v = vec3_norm(view_dir)
    h_vec = vec3_norm(vec3_add(l, v))
    spec = [[0.0] * len(normalen[0]) for _ in range(len(normalen))]
    for y, reihe in enumerate(normalen):
        for x, n in enumerate(reihe):
            nh = max(0.0, vec3_dot(n, h_vec))
            spec[y][x] = nh ** shininess
    return spec

def zu_ascii(wert: float, palette: str = " .:-=+*#%@") -> str:
    idx = int(max(0.0, min(1.0, wert)) * (len(palette) - 1))
    return palette[idx]

def rendere_ascii(karte: Tiefenkarte,
                  diffuse: List[List[float]],
                  schatten: List[List[float]],
                  ao: List[List[float]],
                  spec: List[List[float]],
                  palette: str = " .:-=+*#%@") -> List[str]:
    """Kombiniert alle Terme zu einem ASCII‑Bild."""
    h, b = karte.h, karte.b
    zeilen: List[str] = []
    for y in range(h):
        reihe = []
        for x in range(b):
            if karte.daten[y][x] <= 0.0:
                reihe.append(' ')
                continue
            diff = diffuse[y][x]
            sh = schatten[y][x]
            oc = ao[y][x]
            sp = spec[y][x]
            helligkeit = diff * sh * oc + sp * 0.6
            reihe.append(zu_ascii(helligkeit, palette))
        zeilen.append(''.join(reihe))
    return zeilen

def speichere_ascii(zeilen: List[str], dateiname: str) -> bool:
    """Speichert ASCII‑Art in eine Textdatei."""
    try:
        with open(dateiname, 'w', encoding='utf-8') as f:
            f.write('\n'.join(zeilen))
        return True
    except Exception as e:
        print(f'Fehler beim Speichern: {e}')
        return False

# ---------- Hauptprogramm ----------

def waehle_form() -> Tiefenkarte:
    print('\n=== Schatten‑Simulator (Teil 20) ===')
    print('Formen: 1=Kugel, 2=Kegel, 3=Stufenpyramide, 4=Wellblech')
    try:
        wahl = input('Form wählen [1‑4]: ').strip()
    except EOFError:
        wahl = '1'
    if wahl == '2':
        return erzeuge_kegel()
    elif wahl == '3':
        return erzeuge_stufenpyramide()
    elif wahl == '4':
        return erzeuge_wellblech()
    else:
        print('Ungültig, nehme Kugel.')
        return erzeuge_kugel()

def lies_lichtrichtung() -> Vec3:
    try:
        s = input('Lichtrichtung als drei Zahlen (x y z), z.B. "1 1 -2": ').strip()
    except EOFError:
        s = ''
    if not s:
        print('Ungültig, nehme Standard (1, 1, -2).')
        return (1.0, 1.0, -2.0)
    try:
        x, y, z = map(float, s.split())
        return (x, y, z)
    except Exception:
        print('Ungültig, nehme Standard (1, 1, -2).')
        return (1.0, 1.0, -2.0)

def lies_schritte() -> int:
    try:
        s = input('Schatten‑Samples (Ray‑March Steps) [8‑64]: ').strip()
    except EOFError:
        s = '32'
    try:
        val = int(s)
        return max(8, min(64, val))
    except Exception:
        return 32

def lies_weicher_radius() -> int:
    try:
        s = input('Weichzeichner‑Radius für Schatten [0‑3]: ').strip()
    except EOFError:
        s = '1'
    try:
        val = int(s)
        return max(0, min(3, val))
    except Exception:
        return 1

def lies_ao_samples() -> int:
    try:
        s = input('AO‑Samples [4‑16]: ').strip()
    except EOFError:
        s = '8'
    try:
        val = int(s)
        return max(4, min(16, val))
    except Exception:
        return 8

def frage_speichern() -> Optional[str]:
    try:
        s = input('ASCII in Datei speichern? (Dateiname oder Enter zum Überspringen): ').strip()
    except EOFError:
        return None
    return s if s else None

def main() -> None:
    random.seed(42)
    karte = waehle_form()
    licht = lies_lichtrichtung()
    schritte = lies_schritte()
    blur_r = lies_weicher_radius()
    ao_s = lies_ao_samples()

    print('\nBerechne Normalen...')
    normalen = karte.normalen()

    print('Berechne diffuse Beleuchtung...')
    diffuse = diffuse_schatten(normalen, licht)

    print(f'Ray‑Marching harte Schatten ({schritte} Schritte)...')
    harte = harte_schatten_raymarch(karte, licht, schritte=schritte)

    print(f'Weiche Schatten (Radius {blur_r})...')
    weiche = weiche_schatten(harte, radius=blur_r)

    print(f'Ambient Occlusion ({ao_s} Samples)...')
    ao = ssao(karte, normalen, samples=ao_s)

    print('Blinn‑Phong Specular...')
    spec = blinn_phong(normalen, licht)

    print('Rendere ASCII...')
    ascii_zeilen = rendere_ascii(karte, diffuse, weiche, ao, spec)

    for zeile in ascii_zeilen:
        print(zeile)

    dateiname = frage_speichern()
    if dateiname:
        if speichere_ascii(ascii_zeilen, dateiname):
            print(f'Gespeichert unter {dateiname}')
        else:
            print('Speichern fehlgeschlagen.')
    else:
        print('Nicht gespeichert.')

    print('\nFertig. Gute Nacht, kleiner Dodo.')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nAbgebrochen. Schlaf gut!')
    except EOFError:
        print('\nKeine Eingabe möglich. Schlaf gut!')