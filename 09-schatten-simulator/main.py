# main.py – Schatten‑Simulator, Teil 17
# Fifo, der Dodo, träumt weiter: Fehler behoben, Ray‑March‑Loop fertig, weiche Schatten, AO, Blinn‑Phong, Menü und Rendering.

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
    step_z = lz * inv_xy * step_xy * 0.1  # 0.1 ≈ Z‑Skalierung der Tiefenkarte

    schatten: List[List[float]] = []
    for y in range(h):
        reihe: List[float] = []
        for x in range(b):
            cur_h = karte.get(y, x)
            cx_f, cy_f = float(x), float(y)
            blocked = False
            for _ in range(schritte):
                cx_f += dir_x
                cy_f += dir_y
                cur_h += step_z
                if cx_f < 0 or cx_f >= b or cy_f < 0 or cy_f >= h:
                    break
                sample_h = karte.get_bilinear(cy_f, cx_f)
                if sample_h > cur_h + bias:
                    blocked = True
                    break
            reihe.append(0.0 if blocked else 1.0)
        schatten.append(reihe)
    return schatten

def weiche_schatten(schatten: List[List[float]], radius: int = 1) -> List[List[float]]:
    """Box‑Blur für weiche Schatten."""
    h = len(schatten)
    b = len(schatten[0]) if h > 0 else 0
    if radius <= 0:
        return schatten
    tmp = [[0.0] * b for _ in range(h)]
    # horizontal
    for y in range(h):
        for x in range(b):
            s = 0.0
            cnt = 0
            for dx in range(-radius, radius + 1):
                nx = x + dx
                if 0 <= nx < b:
                    s += schatten[y][nx]
                    cnt += 1
            tmp[y][x] = s / cnt if cnt else 0.0
    # vertical
    result = [[0.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            s = 0.0
            cnt = 0
            for dy in range(-radius, radius + 1):
                ny = y + dy
                if 0 <= ny < h:
                    s += tmp[ny][x]
                    cnt += 1
            result[y][x] = s / cnt if cnt else 0.0
    return result

def ambient_occlusion(karte: Tiefenkarte, normals: List[List[Vec3]],
                      samples: int = 8, max_dist: float = 2.0) -> List[List[float]]:
    """Einfaches Screen‑Space Ambient Occlusion (SSAO) – nur Näherung."""
    h, b = karte.h, karte.b
    ao = [[1.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            n = normals[y][x]
            occ = 0.0
            for _ in range(samples):
                # zufällige Richtung in Hemisphäre
                u = random.random()
                v = random.random()
                theta = 2.0 * math.pi * u
                phi = math.acos(math.sqrt(v))
                dx = math.sin(phi) * math.cos(theta)
                dy = math.sin(phi) * math.sin(theta)
                dz = math.cos(phi)
                # in Welt‑Koordinaten (vereinfacht: Tangentenraum ≈ Welt)
                step_x = dx * max_dist
                step_y = dy * max_dist
                step_z = dz * max_dist
                sx, sy = x + step_x, y + step_y
                if 0 <= sx < b and 0 <= sy < h:
                    sample_h = karte.get_bilinear(sy, sx)
                    if sample_h > karte.get(y, x) + step_z * 0.1:
                        occ += 1.0
            ao[y][x] = 1.0 - occ / samples
    return ao

def blinn_phong(normals: List[List[Vec3]], licht_dir: Vec3,
                view_dir: Vec3 = (0.0, 0.0, 1.0),
                ka: float = 0.2, kd: float = 0.7, ks: float = 0.3, shininess: float = 32.0) -> List[List[float]]:
    """Blinn‑Phong Shading – gibt Helligkeitswert pro Pixel zurück."""
    l = vec3_norm(licht_dir)
    v = vec3_norm(view_dir)
    h_vec = vec3_norm(vec3_add(l, v))
    h, b = len(normals), len(normals[0])
    out = [[0.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            n = normals[y][x]
            ndotl = max(0.0, vec3_dot(n, l))
            ndoth = max(0.0, vec3_dot(n, h_vec))
            spec = ks * (ndoth ** shininess) if ndotl > 0.0 else 0.0
            out[y][x] = ka + kd * ndotl + spec
    return out

# ---------- Rendering ----------
ASCII_RAMP = " .'`^\"\\,;:Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8@$B@$"

def rendern(werte: List[List[float]], ramp: str = ASCII_RAMP) -> str:
    """Wandelt 2D‑Float‑Array (0..1) in ASCII‑Art um."""
    h = len(werte)
    if h == 0:
        return ""
    b = len(werte[0])
    max_idx = len(ramp) - 1
    zeilen = []
    for y in range(h):
        line_chars = []
        for x in range(b):
            v = max(0.0, min(1.0, werte[y][x]))
            idx = int(v * max_idx)
            line_chars.append(ramp[idx])
        zeilen.append("".join(line_chars))
    return "\n".join(zeilen)

def kombiniere_ebenen(basis: List[List[float]],
                      schatten: List[List[float]],
                      ao: List[List[float]],
                      spekulativ: List[List[float]]) -> List[List[float]]:
    """Multipliziert alle Ebenen komponentenweise."""
    h = len(basis)
    b = len(basis[0])
    out = [[0.0] * b for _ in range(h)]
    for y in range(h):
        for x in range(b):
            out[y][x] = basis[y][x] * schatten[y][x] * ao[y][x] * spekulativ[y][x]
    return out

# ---------- Hauptprogramm / Menü ----------

def main() -> None:
    random.seed(42)
    # Start‑Form
    form_funktionen = [
        ("Kugel", erzeuge_kugel),
        ("Kegel", erzeuge_kegel),
        ("Stufenpyramide", erzeuge_stufenpyramide),
        ("Wellblech", erzeuge_wellblech),
    ]
    form_index = 0
    karte = form_funktionen[form_index][1]()
    licht_dir = (1.0, -1.0, 2.0)
    view_dir = (0.0, 0.0, 1.0)
    modus = 3  # 1=harte, 2=weiche, 3=Blinn‑Phong+Schatten+AO

    def aktualisiere() -> None:
        nonlocal karte
        karte = form_funktionen[form_index][1]()

    def drucke_menue() -> None:
        print("\n=== Schatten‑Simulator ===")
        print("1 – Harte Schatten")
        print("2 – Diffuse + Weiche Schatten")
        print("3 – Blinn‑Phong + Schatten + AO")
        print("4 – Tiefenform wählen")
        print("5 – Lichtrichtung anpassen")
        print("6 – Höhen‑Rohdaten anzeigen")
        print("7 – Beenden")
        print("============================")
        print(f"Aktuelle Lichtrichtung: {licht_dir}")
        print(f"Aktuelle Form: {form_funktionen[form_index][0]}")
        print(f"Modus: {modus}")
        print("Deine Wahl: ", end="")

    while True:
        try:
            drucke_menue()
            eingabe = input().strip()
        except EOFError:
            print("\nTschüss! Der Dodo schläft weiter.")
            break

        if not eingabe:
            continue
        if eingabe == "1":
            modus = 1
        elif eingabe == "2":
            modus = 2
        elif eingabe == "3":
            modus = 3
        elif eingabe == "4":
            print("Verfügbare Formen:")
            for i, (name, _) in enumerate(form_funktionen):
                print(f"  {i}: {name}")
            try:
                idx = int(input("Nummer: ").strip())
                if 0 <= idx < len(form_funktionen):
                    form_index = idx
                    aktualisiere()
                else:
                    print("Ungültige Nummer.")
            except ValueError:
                print("Bitte eine Zahl eingeben.")
        elif eingabe == "5":
            print("Gib drei Zahlen ein (x y z): ", end="")
            try:
                parts = input().strip().split()
                if len(parts) == 3:
                    licht_dir = (float(parts[0]), float(parts[1]), float(parts[2]))
                else:
                    print("Erwarte drei Zahlen.")
            except ValueError:
                print("Ungültige Zahlen.")
        elif eingabe == "6":
            print("Höhen‑Rohdaten (min, max, range):", karte.statistik())
            for reihe in karte.daten:
                print(" ".join(f"{v:.2f}" for v in reihe))
        elif eingabe == "7":
            print("Tschüss! Der Dodo schläft weiter.")
            break
        else:
            print("Unbekannter Befehl.")
            continue

        # Rendern je nach Modus
        normals = karte.normalen()
        diffuse = diffuse_schatten(normals, licht_dir)
        harte = harte_schatten_raymarch(karte, licht_dir)
        weiche = weiche_schatten(harte, radius=2)
        ao = ambient_occlusion(karte, normals, samples=16, max_dist=3.0)
        spec = blinn_phong(normals, licht_dir, view_dir)

        if modus == 1:
            bild = kombiniere_ebenen(diffuse, harte, [[1.0]*karte.b for _ in range(karte.h)], [[1.0]*karte.b for _ in range(karte.h)])
        elif modus == 2:
            bild = kombiniere_ebenen(diffuse, weiche, [[1.0]*karte.b for _ in range(karte.h)], [[1.0]*karte.b for _ in range(karte.h)])
        else:  # modus == 3
            bild = kombiniere_ebenen(diffuse, weiche, ao, spec)

        print("\n" + rendern(bild))

if __name__ == "__main__":
    main()