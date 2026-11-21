# main.py – Schatten‑Simulator, Teil 15
# Fifo, der Dodo, träumt weiter: Fehler behoben, Ray‑March‑Loop fertig, weiche Schatten, AO, Blinn‑Phong, Rendering und Menü.

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
    """Einfacher harte Schatten per Ray‑Marching entlang Licht‑richtung."""
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

    schatten: List[List[float]] = []
    for y in range(h):
        reihe: List[float] = []
        for x in range(b):
            cur_h = karte.get(y, x) + bias
            cx, cy = float(x), float(y)
            im_schatten = False
            for _ in range(schritte):
                cx += dir_x
                cy += dir_y
                cur_h += step_z
                if not (0 <= cx < b - 1 and 0 <= cy < h - 1):
                    break
                sample = karte.get_bilinear(cy, cx)
                if sample > cur_h:
                    im_schatten = True
                    break
            reihe.append(0.0 if im_schatten else 1.0)
        schatten.append(reihe)
    return schatten

def weiche_schatten_gauss(schatten_hart: List[List[float]], radius: int = 2) -> List[List[float]]:
    """Einfacher Box‑Blur als weiche Schatten‑Approximation."""
    h = len(schatten_hart)
    b = len(schatten_hart[0]) if h else 0
    res: List[List[float]] = [[0.0 for _ in range(b)] for _ in range(h)]
    for y in range(h):
        for x in range(b):
            acc = 0.0
            cnt = 0
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < b:
                        acc += schatten_hart[ny][nx]
                        cnt += 1
            res[y][x] = acc / cnt if cnt else 1.0
    return res

def ambient_occlusion(karte: Tiefenkarte, radius: int = 2) -> List[List[float]]:
    """Sehr einfacher AO: je höher die Umgebung, desto dunkler."""
    h, b = karte.h, karte.b
    res: List[List[float]] = [[0.0 for _ in range(b)] for _ in range(h)]
    for y in range(h):
        for x in range(b):
            cur = karte.get(y, x)
            cnt = 0
            occ = 0.0
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < b:
                        cnt += 1
                        occ += max(0.0, karte.get(ny, nx) - cur)
            res[y][x] = 1.0 - (occ / cnt) if cnt else 1.0
    return res

def blinn_phong(karte: Tiefenkarte, licht_dir: Vec3,
                view_dir: Vec3 = (0.0, 0.0, 1.0),
                shininess: float = 32.0,
                ambient: float = 0.1) -> List[List[float]]:
    normals = karte.normalen()
    diff = diffuse_schatten(normals, licht_dir)
    h, b = karte.h, karte.b
    result: List[List[float]] = [[0.0 for _ in range(b)] for _ in range(h)]
    lx, ly, lz = vec3_norm(licht_dir)
    vx, vy, vz = vec3_norm(view_dir)
    for y in range(h):
        for x in range(b):
            nx, ny, nz = normals[y][x]
            # Halbvektor
            hx, hy, hz = vec3_norm((lx + vx, ly + vy, lz + vz))
            spec = max(0.0, vec3_dot((nx, ny, nz), (hx, hy, hz))) ** shininess
            result[y][x] = ambient + diff[y][x] * (1.0 - ambient) + spec * (1.0 - ambient)
    return result

# ---------- ASCII‑Renderer ----------

def render_ascii(intensitaet: List[List[float]]) -> str:
    chars = " .:-=+*#%@"
    h = len(intensitaet)
    b = len(intensitaet[0]) if h else 0
    lines: List[str] = []
    for y in range(h):
        line = []
        for x in range(b):
            v = intensitaet[y][x]
            idx = int(v * (len(chars) - 1))
            line.append(chars[idx])
        lines.append(''.join(line))
    return "\n".join(lines)

# ---------- Menü und Main‑Loop ----------

def auswahl_liste(prompt: str, optionen: List[str]) -> int:
    while True:
        print(prompt)
        for i, opt in enumerate(optionen, 1):
            print(f"{i} – {opt}")
        try:
            choice = input("Deine Wahl? ").strip()
        except EOFError:
            print("\nEOF erreicht – Programm wird beendet.")
            sys.exit(0)
        if not choice.isdigit():
            print("Bitte eine Zahl eingeben.")
            continue
        idx = int(choice) - 1
        if 0 <= idx < len(optionen):
            return idx
        print("Ungültige Option.")

def main() -> None:
    # Startparameter
    tiefenkarte = erzeuge_kugel()
    licht_dir: Vec3 = (1.0, 1.0, -1.0)
    while True:
        opt = auswahl_liste("--- Schatten‑Simulator ---", [
            "Diffuse (Lambert) + Harte Schatten",
            "Diffuse + Weiche Schatten",
            "Blinn‑Phong + Schatten + AO",
            "Tiefenform wählen",
            "Lichtrichtung anpassen",
            "Höhen‑Rohdaten anzeigen",
            "Beenden"
        ])
        if opt == 0:
            diff = diffuse_schatten(tiefenkarte.normalen(), licht_dir)
            hart = harte_schatten_raymarch(tiefenkarte, licht_dir)
            kombi = [[diff[y][x] * hart[y][x] for x in range(tiefenkarte.b)] for y in range(tiefenkarte.h)]
            print(render_ascii(kombi))
        elif opt == 1:
            diff = diffuse_schatten(tiefenkarte.normalen(), licht_dir)
            hart = harte_schatten_raymarch(tiefenkarte, licht_dir)
            weich = weiche_schatten_gauss(hart)
            kombi = [[diff[y][x] * weich[y][x] for x in range(tiefenkarte.b)] for y in range(tiefenkarte.h)]
            print(render_ascii(kombi))
        elif opt == 2:
            bp = blinn_phong(tiefenkarte, licht_dir)
            ao = ambient_occlusion(tiefenkarte)
            kombi = [[bp[y][x] * ao[y][x] for x in range(tiefenkarte.b)] for y in range(tiefenkarte.h)]
            print(render_ascii(kombi))
        elif opt == 3:
            shape_idx = auswahl_liste("Wähle eine Form:", ["Kugel", "Kegel", "Stufenpyramide", "Wellblech"])
            if shape_idx == 0:
                tiefenkarte = erzeuge_kugel()
            elif shape_idx == 1:
                tiefenkarte = erzeuge_kegel()
            elif shape_idx == 2:
                tiefenkarte = erzeuge_stufenpyramide()
            else:
                tiefenkarte = erzeuge_wellblech()
        elif opt == 4:
            try:
                lx = float(input("Licht‑X (z.B. 1.0): "))
                ly = float(input("Licht‑Y (z.B. 1.0): "))
                lz = float(input("Licht‑Z (z.B. -1.0): "))
                licht_dir = (lx, ly, lz)
            except EOFError:
                print("EOF – Rückkehr zum Menü.")
            except ValueError:
                print("Ungültige Zahl – Rückkehr zum Menü.")
        elif opt == 5:
            print("Roh‑Höhenwerte (0‑1):")
            for reihe in tiefenkarte.daten:
                print(' '.join(f"{v:.2f}" for v in reihe))
        else:
            print("Auf Wiedersehen!")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen.")