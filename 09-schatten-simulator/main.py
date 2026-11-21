# main.py – Schatten‑Simulator, Teil 21
# Fifo, der Dodo, träumt den letzten Schliff: Speichern, Batch‑Modus, kleine Aufräumarbeiten.
# Diesmal: Ray‑Marching fertig, Weichzeichner, ASCII‑Export, EOF‑Sicherheit.

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
            z = karte.get(y, x)
            if z <= 0.0:
                schatten[y][x] = 1.0
                continue
            sx = float(x)
            sy = float(y)
            sz = z
            blocked = False
            for _ in range(schritte):
                sx += dir_x
                sy += dir_y
                sz += step_z
                if sx < 0 or sx >= b or sy < 0 or sy >= h:
                    break
                h_here = karte.get_bilinear(sy, sx)
                if h_here > sz + bias:
                    blocked = True
                    break
            schatten[y][x] = 0.0 if blocked else 1.0
    return schatten

def weiche_schatten(schatten: List[List[float]], radius: int) -> List[List[float]]:
    """Einfacher Box‑Blur für weiche Schatten."""
    if radius <= 0:
        return schatten
    h = len(schatten)
    b = len(schatten[0]) if h > 0 else 0
    # Horizontale Pass
    temp = [[0.0] * b for _ in range(h)]
    for y in range(h):
        row = schatten[y]
        for x in range(b):
            s = 0.0
            cnt = 0
            for dx in range(-radius, radius + 1):
                nx = x + dx
                if 0 <= nx < b:
                    s += row[nx]
                    cnt += 1
            temp[y][x] = s / cnt if cnt else 0.0
    # Vertikale Pass
    result = [[0.0] * b for _ in range(h)]
    for x in range(b):
        for y in range(h):
            s = 0.0
            cnt = 0
            for dy in range(-radius, radius + 1):
                ny = y + dy
                if 0 <= ny < h:
                    s += temp[ny][x]
                    cnt += 1
            result[y][x] = s / cnt if cnt else 0.0
    return result

# ---------- ASCII‑Rendering ----------

def render_ascii(werte: List[List[float]], palette: str = " .:-=+*#%@") -> List[str]:
    """Wandelt 0‑1 Werte in ASCII‑Zeilen um."""
    lines = []
    max_i = len(palette) - 1
    for row in werte:
        line = ''.join(palette[min(max_i, int(v * max_i + 0.5))] for v in row)
        lines.append(line)
    return lines

def speichere_ascii(lines: List[str], dateiname: str = "schatten.txt") -> bool:
    """Speichert ASCII‑Art in eine Datei."""
    try:
        with open(dateiname, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        return True
    except OSError as e:
        print(f"Fehler beim Speichern: {e}")
        return False

# ---------- Hauptprogramm ----------

def main() -> None:
    print("=== Schatten‑Simulator (Teil 21) ===")
    print("Formen: 1=Kugel, 2=Kegel, 3=Stufenpyramide, 4=Wellblech")
    eingaben = 0
    max_eingaben = 20
    
    def safe_input(prompt: str) -> Optional[str]:
        nonlocal eingaben
        if eingaben >= max_eingaben:
            return None
        try:
            s = input(prompt)
            eingaben += 1
            return s
        except EOFError:
            return None
    
    # Form wählen
    form_str = safe_input("Form wählen [1‑4]: ")
    if form_str is None:
        print("\nKeine Eingabe mehr – Tschüss!")
        return
    try:
        form = int(form_str.strip())
        if form not in (1, 2, 3, 4):
            raise ValueError
    except ValueError:
        print("Ungültig, nehme Kugel.")
        form = 1
    
    # Lichtrichtung
    licht_str = safe_input("Lichtrichtung als drei Zahlen (x y z), z.B. \"1 1 -2\": ")
    if licht_str is None:
        print("\nKeine Eingabe mehr – Tschüss!")
        return
    try:
        parts = licht_str.strip().split()
        if len(parts) != 3:
            raise ValueError
        lx, ly, lz = map(float, parts)
        licht_dir = (lx, ly, lz)
    except ValueError:
        print("Ungültig, nehme Standard (1, 1, -2).")
        licht_dir = (1.0, 1.0, -2.0)
    
    # Schatten‑Samples
    samples_str = safe_input("Schatten‑Samples (Ray‑March Steps) [8‑64]: ")
    if samples_str is None:
        print("\nKeine Eingabe mehr – Tschüss!")
        return
    try:
        samples = int(samples_str.strip())
        if samples < 8 or samples > 64:
            raise ValueError
    except ValueError:
        print("Ungültig, nehme 32.")
        samples = 32
    
    # Weichzeichner‑Radius
    blur_str = safe_input("Weichzeichner‑Radius für Schatten [0‑4]: ")
    if blur_str is None:
        print("\nKeine Eingabe mehr – Tschüss!")
        return
    try:
        blur_radius = int(blur_str.strip())
        if blur_radius < 0 or blur_radius > 4:
            raise ValueError
    except ValueError:
        print("Ungültig, nehme 1.")
        blur_radius = 1
    
    # Tiefenkarte erzeugen
    if form == 1:
        karte = erzeuge_kugel()
    elif form == 2:
        karte = erzeuge_kegel()
    elif form == 3:
        karte = erzeuge_stufenpyramide()
    else:
        karte = erzeuge_wellblech()
    
    print("\nBerechne Normalen …")
    normals = karte.normalen()
    
    print("Berechne diffusen Schatten …")
    diff = diffuse_schatten(normals, licht_dir)
    
    print("Berechne harte Schatten (Ray‑Marching) …")
    hart = harte_schatten_raymarch(karte, licht_dir, schritte=samples)
    
    # Kombinieren: multiplizieren
    kombiniert = [[diff[y][x] * hart[y][x] for x in range(karte.b)] for y in range(karte.h)]
    
    if blur_radius > 0:
        print(f"Wende Weichzeichner (Radius {blur_radius}) an …")
        kombiniert = weiche_schatten(kombiniert, blur_radius)
    
    print("\nErgebnis (ASCII):")
    ascii_lines = render_ascii(kombiniert)
    for line in ascii_lines:
        print(line)
    
    # Speichern?
    save = safe_input("\nASCII‑Art speichern? (j/n) [j]: ")
    if save is None:
        print("\nKeine Eingabe mehr – Tschüss!")
        return
    if save.strip().lower() in ('', 'j', 'ja', 'y', 'yes'):
        fname = safe_input("Dateiname [schatten.txt]: ")
        if fname is None:
            print("\nKeine Eingabe mehr – Tschüss!")
            return
        fname = fname.strip() or "schatten.txt"
        if speichere_ascii(ascii_lines, fname):
            print(f"Gespeichert unter {fname}")
        else:
            print("Speichern fehlgeschlagen.")
    else:
        print("Nicht gespeichert.")
    
    print("\nFifo winkt mit dem Flügel – bis zum nächsten Traum!")

if __name__ == "__main__":
    main()