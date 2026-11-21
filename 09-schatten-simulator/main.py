from __future__ import annotations
import math
import sys
import random
from typing import List, Tuple, Optional

Vec3 = Tuple[float, float, float]
Color = Tuple[int, int, int]

# ---------- Vektor-Hilfsfunktionen ----------

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

def vec3_lerp(a: Vec3, b: Vec3, t: float) -> Vec3:
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t)

# ---------- Tiefenkarte und Normalen ----------

class Tiefenkarte:
    """Hält ein 2D-Höhenfeld und liefert Normalen, Statistik usw."""

    def __init__(self, daten: List[List[float]]):
        self.daten = [reihe[:] for reihe in daten]
        self.h = len(daten)
        self.b = len(daten[0]) if self.h > 0 else 0

    def get(self, y: int, x: int, default: float = 0.0) -> float:
        if 0 <= y < self.h and 0 <= x < self.b:
            return self.daten[y][x]
        return default

    def get_bilinear(self, y: float, x: float) -> float:
        if self.h == 0 or self.b == 0:
            return 0.0
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

def erzeuge_zufaellige_huegel(h: int = 20, b: int = 40, anzahl: int = 5, seed: int = 42) -> Tiefenkarte:
    """Einfache Perlin-ish Hügel: Summe von ein paar Gauß-Glocken."""
    random.seed(seed)
    karte = [[0.0 for _ in range(b)] for _ in range(h)]
    centers = []
    for _ in range(anzahl):
        cy = random.uniform(0.2, 0.8) * (h - 1)
        cx = random.uniform(0.2, 0.8) * (b - 1)
        rad = random.uniform(0.15, 0.35) * min(h, b)
        hoehe = random.uniform(0.5, 1.0)
        centers.append((cy, cx, rad, hoehe))
    for y in range(h):
        for x in range(b):
            val = 0.0
            for cy, cx, rad, hoehe in centers:
                dy = y - cy
                dx = (x - cx) * 0.5
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < rad:
                    val += hoehe * (1.0 - dist / rad)
            karte[y][x] = min(1.0, val)
    return Tiefenkarte(karte)

# ---------- Beleuchtungs- und Schatten-Funktionen ----------

def diffuse_schatten(tk: Tiefenkarte, normals: List[List[Vec3]], light_dir: Vec3, z_skalierung: float = 2.0) -> List[List[float]]:
    """Berechnet diffusen Schattenwurf (harter Schatten) für jeden Pixel.
    light_dir zeigt VON der Lichtquelle ZUM Objekt (also z.B. (-1, -1, -2) für oben-links)."""
    h, b = tk.h, tk.b
    shadow = [[1.0 for _ in range(b)] for _ in range(h)]
    lx, ly, lz = vec3_norm(light_dir)
    if lz >= 0:
        return shadow
    step = 0.5
    max_steps = max(h, b) * 2
    for y in range(h):
        for x in range(b):
            height = tk.daten[y][x]
            px = x + 0.5
            py = y + 0.5
            pz = height * z_skalierung + 0.01
            dx = -lx * step
            dy = -ly * step
            dz = -lz * step
            in_shadow = False
            for _ in range(max_steps):
                px += dx
                py += dy
                pz += dz
                if px < 0 or px >= b or py < 0 or py >= h:
                    break
                if pz <= 0:
                    break
                terrain_h = tk.get_bilinear(py, px) * z_skalierung
                if pz <= terrain_h:
                    in_shadow = True
                    break
            if in_shadow:
                shadow[y][x] = 0.3
    return shadow

def ambient_occlusion(tk: Tiefenkarte, normals: List[List[Vec3]], z_skalierung: float = 2.0, samples: int = 8, radius: float = 1.5) -> List[List[float]]:
    """Einfaches Screen-Space Ambient Occlusion (SSAO) auf dem Höhenfeld."""
    h, b = tk.h, tk.b
    ao = [[1.0 for _ in range(b)] for _ in range(h)]
    for y in range(h):
        for x in range(b):
            n = normals[y][x]
            occ = 0.0
            for i in range(samples):
                angle = 2.0 * math.pi * i / samples
                if abs(n[0]) > 0.1 or abs(n[1]) > 0.1:
                    t = vec3_norm((-n[1], n[0], 0.0))
                else:
                    t = (1.0, 0.0, 0.0)
                b_vec = vec3_norm((n[1]*t[2] - n[2]*t[1], n[2]*t[0] - n[0]*t[2], n[0]*t[1] - n[1]*t[0]))
                r = radius * math.sqrt(random.random())
                dx = r * math.cos(angle)
                dy = r * math.sin(angle)
                wx = n[0] * 0.01 + t[0] * dx + b_vec[0] * dy
                wy = n[1] * 0.01 + t[1] * dx + b_vec[1] * dy
                wz = n[2] * 0.01 + t[2] * dx + b_vec[2] * dy
                px = x + 0.5 + wx
                py = y + 0.5 + wy
                pz = tk.daten[y][x] * z_skalierung + wz
                steps = 5
                hit = False
                for s in range(1, steps + 1):
                    sx = x + 0.5 + wx * s / steps
                    sy = y + 0.5 + wy * s / steps
                    sz = tk.daten[y][x] * z_skalierung + wz * s / steps
                    if sx < 0 or sx >= b or sy < 0 or sy >= h:
                        break
                    terrain_h = tk.get_bilinear(sy, sx) * z_skalierung
                    if sz <= terrain_h:
                        hit = True
                        break
                if hit:
                    occ += 1.0
            ao[y][x] = 1.0 - (occ / samples) * 0.5
    return ao

def gamma_korrektur(wert: float, gamma: float = 2.2) -> float:
    if wert <= 0:
        return 0.0
    return min(1.0, max(0.0, wert ** (1.0 / gamma)))

def skaliere_ascii(zeilen: List[str], faktor: float) -> List[str]:
    """Skaliert ASCII-Art durch Downsampling (einfaches Mittelwert-Bild)."""
    if faktor >= 1.0:
        return zeilen
    h = len(zeilen)
    if h == 0:
        return []
    b = len(zeilen[0])
    new_h = max(1, int(h * faktor))
    new_b = max(1, int(b * faktor))
    result = []
    ascii_ramp = " .'`^,:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
    for ny in range(new_h):
        src_y = ny / faktor
        y0 = int(src_y)
        y1 = min(h - 1, y0 + 1)
        dy = src_y - y0
        row = []
        for nx in range(new_b):
            src_x = nx / faktor
            x0 = int(src_x)
            x1 = min(b - 1, x0 + 1)
            dx = src_x - x0
            def char_dichte(c: str) -> float:
                return ascii_ramp.find(c) / (len(ascii_ramp) - 1)
            d00 = char_dichte(zeilen[y0][x0])
            d01 = char_dichte(zeilen[y0][x1])
            d10 = char_dichte(zeilen[y1][x0])
            d11 = char_dichte(zeilen[y1][x1])
            d0 = d00 * (1 - dx) + d01 * dx
            d1 = d10 * (1 - dx) + d11 * dx
            d = d0 * (1 - dy) + d1 * dy
            idx = int(d * (len(ascii_ramp) - 1))
            row.append(ascii_ramp[idx])
        result.append(''.join(row))
    return result

def rendere_ascii(tk: Tiefenkarte, shadow: List[List[float]], ao: List[List[float]], light_dir: Vec3, z_skalierung: float = 2.0) -> List[str]:
    """Erzeugt ASCII-Art aus Tiefenkarte, Schatten und AO."""
    h, b = tk.h, tk.b
    normals = tk.normalen(z_skalierung)
    ascii_ramp = " .'`^,:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
    zeilen = []
    for y in range(h):
        reihe = []
        for x in range(b):
            n = normals[y][x]
            diff = max(0.0, vec3_dot(n, vec3_norm((-light_dir[0], -light_dir[1], -light_dir[2]))))
            ambient = 0.3
            diffuse = 0.7 * diff * shadow[y][x] * ao[y][x]
            helligkeit = ambient + diffuse
            helligkeit = gamma_korrektur(helligkeit)
            idx = int(helligkeit * (len(ascii_ramp) - 1))
            reihe.append(ascii_ramp[idx])
        zeilen.append(''.join(reihe))
    return zeilen

# ---------- Hauptprogramm ----------

def eingabe_mit_default(prompt: str, default: str, validator) -> str:
    """Fragt Eingabe ab, nutzt Default bei Enter, validiert mit validator Funktion."""
    while True:
        try:
            val = input(prompt).strip()
        except EOFError:
            print("\nKeine Eingabe mehr, tschüss!", file=sys.stderr)
            sys.exit(0)
        if val == '':
            return default
        if validator(val):
            return val
        print(f"Ungültige Eingabe: '{val}'. Versuche es nochmal.", file=sys.stderr)

def main() -> None:
    print("Schatten-Simulator – Träumt weiter, kleiner Dodo.", file=sys.stderr)
    h_str = eingabe_mit_default("Höhe [20] ", "20", lambda s: s.isdigit() and 1 <= int(s) <= 200)
    h = int(h_str)
    b_str = eingabe_mit_default("Breite [40] ", "40", lambda s: s.isdigit() and 1 <= int(s) <= 200)
    b = int(b_str)
    formen = {
        'kugel': erzeuge_kugel,
        'kegel': erzeuge_kegel,
        'pyramide': erzeuge_stufenpyramide,
        'wellblech': erzeuge_wellblech,
        'huegel': erzeuge_zufaellige_huegel
    }
    formen_liste = ', '.join(formen.keys())
    form_key = eingabe_mit_default(f"Form [{formen_liste}] [kugel] ", "kugel", lambda s: s in formen).lower()
    if form_key not in formen:
        print(f"Unbekannte Wahl '{form_key}', nehme 'kugel'.", file=sys.stderr)
        form_key = 'kugel'
    skal_str = eingabe_mit_default("Ausgabe-Skalierung (1.0 = 1:1, 0.5 = halb so gross) [1.0] ", "1.0",
                                   lambda s: s.replace('.','',1).isdigit() and 0.0 < float(s) <= 2.0)
    skalierung = float(skal_str)
    tk = formen[form_key](h, b)
    light_dir = (-1.0, -1.0, -2.0)
    normals = tk.normalen(z_skalierung=2.0)
    shadow = diffuse_schatten(tk, normals, light_dir, z_skalierung=2.0)
    ao = ambient_occlusion(tk, normals, z_skalierung=2.0, samples=8, radius=1.5)
    ascii_zeilen = rendere_ascii(tk, shadow, ao, light_dir, z_skalierung=2.0)
    if skalierung != 1.0:
        ascii_zeilen = skaliere_ascii(ascii_zeilen, skalierung)
    preview_h = min(5, len(ascii_zeilen))
    for i in range(preview_h):
        print(ascii_zeilen[i], file=sys.stderr)
    if len(ascii_zeilen) > preview_h:
        print(f"... ({len(ascii_zeilen)} Zeilen insgesamt)", file=sys.stderr)
    for zeile in ascii_zeilen:
        print(zeile)
    print(f"Fertig: {len(ascii_zeilen)}x{len(ascii_zeilen[0]) if ascii_zeilen else 0}, Form={form_key}, Höhe {h}", file=sys.stderr)

if __name__ == "__main__":
    main()