# main.py – Schatten‑Simulator, Teil 23
# Fifo, der Dodo, träumt den letzten Schliff: Speichern, Batch‑Modus, kleine Aufräumarbeiten.
# Diesmal: Ray‑Marching fertig, Weichzeichner, ASCII‑Export, EOF‑Sicherheit, Batch‑Modus.

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
            start_h = karte.daten[y][x] + bias
            sx = x + dir_x
            sy = y + dir_y
            sz = start_h + step_z
            blocked = False
            for _ in range(schritte):
                if not (0 <= sy < h and 0 <= sx < b):
                    break
                h_here = karte.get_bilinear(sy, sx)
                if h_here > sz:
                    blocked = True
                    break
                sx += dir_x
                sy += dir_y
                sz += step_z
            schatten[y][x] = 0.0 if blocked else 1.0
    return schatten

def box_blur(src: List[List[float]], radius: int) -> List[List[float]]:
    """Trennbarer Box‑Blur (horizontal + vertikal)."""
    if radius <= 0:
        return [row[:] for row in src]
    h, w = len(src), len(src[0])
    tmp = [[0.0] * w for _ in range(h)]
    # horizontal
    for y in range(h):
        row = src[y]
        summe = sum(row[:radius + 1])
        for x in range(w):
            tmp[y][x] = summe / (min(x + radius, w - 1) - max(x - radius, 0) + 1)
            if x + radius + 1 < w:
                summe += row[x + radius + 1]
            if x - radius > 0:
                summe -= row[x - radius - 1]
    # vertikal
    dst = [[0.0] * w for _ in range(h)]
    for x in range(w):
        summe = sum(tmp[y][x] for y in range(min(radius + 1, h)))
        for y in range(h):
            dst[y][x] = summe / (min(y + radius, h - 1) - max(y - radius, 0) + 1)
            if y + radius + 1 < h:
                summe += tmp[y + radius + 1][x]
            if y - radius > 0:
                summe -= tmp[y - radius - 1][x]
    return dst

def weiche_schatten(karte: Tiefenkarte, licht_dir: Vec3,
                    raymarch_steps: int = 32, blur_radius: int = 1) -> List[List[float]]:
    """Kombiniert Ray‑Marching‑Härte mit Box‑Blur für weiche Kanten."""
    hart = harte_schatten_raymarch(karte, licht_dir, schritte=raymarch_steps)
    if blur_radius > 0:
        return box_blur(hart, blur_radius)
    return hart

# ---------- Ausgabe & Export ----------

ASCII_RAMP = " .:-=+*#%@"

def zu_ascii(wert: float, rampe: str = ASCII_RAMP) -> str:
    idx = int(max(0.0, min(1.0, wert)) * (len(rampe) - 1))
    return rampe[idx]

def drucke_schatten(karte: Tiefenkarte, schatten: List[List[float]],
                    diffuse: Optional[List[List[float]]] = None) -> None:
    """Kombinierte Ansicht: Höhe + Schatten + optional Diffuse."""
    for y in range(karte.h):
        zeile = []
        for x in range(karte.b):
            h_val = karte.daten[y][x]
            s_val = schatten[y][x]
            if diffuse:
                d_val = diffuse[y][x]
                komb = (h_val + s_val + d_val) / 3.0
            else:
                komb = (h_val + s_val) * 0.5
            zeile.append(zu_ascii(komb))
        print(''.join(zeile))

def speichere_ppm(karte: Tiefenkarte, schatten: List[List[float]],
                  diffuse: Optional[List[List[float]]] = None, dateiname: str = "schatten.ppm") -> None:
    """Speichert als einfaches PPM (P3 ASCII)."""
    h, w = karte.h, karte.b
    with open(dateiname, 'w', encoding='ascii') as f:
        f.write(f"P3\n{w} {h}\n255\n")
        for y in range(h):
            zeile = []
            for x in range(w):
                h_val = karte.daten[y][x]
                s_val = schatten[y][x]
                if diffuse:
                    d_val = diffuse[y][x]
                    r = int((h_val * 0.5 + s_val * 0.3 + d_val * 0.2) * 255)
                    g = int((h_val * 0.3 + s_val * 0.5 + d_val * 0.2) * 255)
                    b = int((h_val * 0.2 + s_val * 0.2 + d_val * 0.6) * 255)
                else:
                    val = (h_val + s_val) * 0.5
                    r = g = b = int(val * 255)
                zeile.append(f"{r} {g} {b}")
            f.write(' '.join(zeile) + '\n')
    print(f"Gespeichert: {dateiname}")

# ---------- Eingabe‑Hilfen ----------

def safe_input(prompt: str, default: str = "") -> str:
    """input() mit EOFError‑Abfangen."""
    try:
        return input(prompt)
    except EOFError:
        print("\nEOF – tschüss!")
        sys.exit(0)

def parse_licht(s: str) -> Vec3:
    try:
        parts = s.strip().split()
        if len(parts) != 3:
            raise ValueError
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    except Exception:
        print("Ungültig, nehme (1, 1, -2)")
        return (1.0, 1.0, -2.0)

def parse_int(s: str, min_v: int, max_v: int, default: int) -> int:
    try:
        v = int(s.strip())
        return max(min_v, min(max_v, v))
    except Exception:
        return default

# ---------- Hauptprogramm ----------

def menue_form() -> Tiefenkarte:
    print("\n=== Schatten‑Simulator (Teil 23) ===")
    print("Formen: 1=Kugel, 2=Kegel, 3=Stufenpyramide, 4=Wellblech")
    wahl = safe_input("Form wählen [1‑4]: ").strip()
    if wahl == "1":
        return erzeuge_kugel()
    elif wahl == "2":
        return erzeuge_kegel()
    elif wahl == "3":
        return erzeuge_stufenpyramide()
    elif wahl == "4":
        return erzeuge_wellblech()
    else:
        print("Ungültig, nehme Kugel.")
        return erzeuge_kugel()

def main() -> None:
    karte = menue_form()
    
    licht_str = safe_input("Lichtrichtung als drei Zahlen (x y z), z.B. \"1 1 -2\": ")
    licht = parse_licht(licht_str)
    
    steps = parse_int(safe_input("Schatten‑Samples (Ray‑March Steps) [8‑64]: "), 8, 64, 32)
    blur = parse_int(safe_input("Weichzeichner‑Radius (Box‑Blur) [0‑4]: "), 0, 4, 1)
    
    print("\nBerechne Normalen …")
    normals = karte.normalen()
    
    print("Berechne diffuse Beleuchtung …")
    diffuse = diffuse_schatten(normals, licht)
    
    print(f"Ray‑Marching ({steps} Schritte) …")
    schatten = weiche_schatten(karte, licht, raymarch_steps=steps, blur_radius=blur)
    
    print("\n--- Ergebnis (ASCII) ---")
    drucke_schatten(karte, schatten, diffuse)
    
    # Speichern?
    if safe_input("\nAls PPM speichern? (j/n): ").strip().lower().startswith('j'):
        name = safe_input("Dateiname [schatten.ppm]: ").strip()
        if not name:
            name = "schatten.ppm"
        speichere_ppm(karte, schatten, diffuse, name)
    
    # Batch‑Modus
    if safe_input("\nBatch‑Modus? (j/n): ").strip().lower().startswith('j'):
        anzahl = parse_int(safe_input("Wie viele zufällige Variationen? [1‑20]: "), 1, 20, 5)
        for i in range(anzahl):
            # zufällige Parameter
            forms = [erzeuge_kugel, erzeuge_kegel, erzeuge_stufenpyramide, erzeuge_wellblech]
            k = random.choice(forms)()
            lx = random.uniform(-2, 2)
            ly = random.uniform(-2, 2)
            lz = random.uniform(-3, -0.5)
            l = (lx, ly, lz)
            s = random.randint(16, 48)
            b = random.randint(0, 3)
            n = k.normalen()
            d = diffuse_schatten(n, l)
            sh = weiche_schatten(k, l, raymarch_steps=s, blur_radius=b)
            fname = f"batch_{i:03d}.ppm"
            speichere_ppm(k, sh, d, fname)
        print(f"\n{anzahl} Batch‑Dateien erzeugt.")
    
    print("\nFertig. Gute Nacht! 🦤")

if __name__ == "__main__":
    main()