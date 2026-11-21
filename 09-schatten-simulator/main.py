from __future__ import annotations
import math
import sys
import random
from typing import List, Tuple, Optional, Dict

Vec3 = Tuple[float, float, float]

# ---------- Vektor-Mathematik ----------

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

def vec3_sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def vec3_scale(v: Vec3, s: float) -> Vec3:
    return (v[0] * s, v[1] * s, v[2] * s)

def vec3_dist(a: Vec3, b: Vec3) -> float:
    dx, dy, dz = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)

# ---------- Tiefenkarte ----------

class Tiefenkarte:
    """Speichert Höhendaten und errechnet Normalenvektoren zur Tiefenerzwingung."""

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
        return (h00 * (1.0 - dx) + h01 * dx) * (1.0 - dy) + (h10 * (1.0 - dx) + h11 * dx) * dy

    def normalen(self, z_faktor: float = 2.5) -> List[List[Vec3]]:
        normals: List[List[Vec3]] = []
        for y in range(self.h):
            reihe: List[Vec3] = []
            for x in range(self.b):
                hx = (self.get(y, x + 1) - self.get(y, x - 1)) * 0.5 * z_faktor
                hy = (self.get(y + 1, x) - self.get(y - 1, x)) * 0.5 * z_faktor
                # Normalenvektor zeigt aus der Bildfläche nach oben-außen
                reihe.append(vec3_norm((-hx, -hy, 1.0)))
            normals.append(reihe)
        return normals

    def statistik(self) -> Tuple[float, float, float]:
        flach = [w for reihe in self.daten for w in reihe]
        if not flach:
            return 0.0, 0.0, 0.0
        mn, mx = min(flach), max(flach)
        return mn, mx, mx - mn

# ---------- Lichtquellen-System ----------

class Lichtquelle:
    """Punktförmiges oder gerichtetes Licht mit Vektorberechnung."""

    def __init__(self, typ: str, pos_oder_dir: Vec3, intensitaet: float = 1.0, abfall: float = 0.002):
        self.typ = typ  # 'gerichtet' oder 'punkt'
        self.vec = pos_oder_dir
        self.intensitaet = intensitaet
        self.abfall = abfall

    def vektor_und_distanz(self, p: Vec3) -> Tuple[Vec3, float]:
        if self.typ == 'gerichtet':
            # vec ist Richtung ZUR Lichtquelle
            return vec3_norm(self.vec), 1e6
        else:
            # Punktlicht: Vektor von Oberfläche P zur Lichtquelle
            diff = vec3_sub(self.vec, p)
            dist = math.sqrt(vec3_dot(diff, diff))
            l_dir = vec3_norm(diff) if dist > 1e-6 else (0.0, 0.0, 1.0)
            return l_dir, dist

    def energie_an(self, dist: float) -> float:
        if self.typ == 'gerichtet':
            return self.intensitaet
        # Physikalischer Abfall mit Distanzfaktor
        return self.intensitaet / (1.0 + self.abfall * dist * dist)

# ---------- 3D Raymarching & Shading ----------

def raymarch_schatten(tk: Tiefenkarte, start: Vec3, l_dir: Vec3, max_dist: float, schritte: int = 24) -> float:
    """Prüft entlang des Lichtvektors, ob die Tiefenkarte die Sichtlinie schneidet."""
    # Leicht anheben gegen Selbsteinkerbung
    curr_x = start[0] + l_dir[0] * 0.4
    curr_y = start[1] + l_dir[1] * 0.4
    curr_z = start[2] + l_dir[2] * 0.4
    
    schrittweite = max(0.5, min(2.0, max_dist / schritte))
    d = 0.4
    while d < max_dist:
        curr_x += l_dir[0] * schrittweite
        curr_y += l_dir[1] * schrittweite
        curr_z += l_dir[2] * schrittweite
        d += schrittweite
        
        if not (0 <= curr_x < tk.b and 0 <= curr_y < tk.h):
            break
            
        karten_h = tk.get_bilinear(curr_y, curr_x)
        if curr_z < karten_h:
            return 0.1  # Im Kernschatten
    return 1.0  # Volles Licht

def berechne_tiefen_schattierung(
    tk: Tiefenkarte,
    lichter: List[Lichtquelle],
    z_tiefe: float = 6.0,
    ambient: float = 0.15,
    glanz_staerke: float = 0.4,
    glanz_haerte: float = 16.0
) -> List[List[float]]:
    """Berechnet vollständige 3D-Lichtvektoren, Glanzpunkte und Raymarch-Schatten."""
    normalen_feld = tk.normalen(z_faktor=z_tiefe * 0.4)
    ausgabe: List[List[float]] = []
    sicht_vektor: Vec3 = (0.0, 0.0, 1.0)  # Beobachter schaut frontal auf die Szene

    for y in range(tk.h):
        reihe: List[float] = []
        for x in range(tk.b):
            z_val = tk.get(y, x) * z_tiefe
            p: Vec3 = (float(x), float(y), z_val)
            n = normalen_feld[y][x]
            
            gesamt_helligkeit = ambient * (0.3 + 0.7 * tk.get(y, x))
            
            for licht in lichter:
                l_dir, dist = licht.vektor_und_distanz(p)
                diffus = max(0.0, vec3_dot(n, l_dir))
                
                if diffus > 0.001:
                    schatten = raymarch_schatten(tk, (p[0], p[1], tk.get(y, x)), l_dir, min(dist, 40.0))
                    energie = licht.energie_an(dist) * schatten
                    
                    # Diffuser Anteil
                    gesamt_helligkeit += diffus * energie
                    
                    # Blinn-Phong Glanzlicht (erzeugt greifbare 3D-Rundung)
                    halb_vektor = vec3_norm(vec3_add(l_dir, sicht_vektor))
                    n_dot_h = max(0.0, vec3_dot(n, halb_vektor))
                    if n_dot_h > 0.0 and schatten > 0.5:
                        spekular = math.pow(n_dot_h, glanz_haerte) * glanz_staerke * energie
                        gesamt_helligkeit += spekular
            
            # Begrenzung auf [0.0, 1.0]
            reihe.append(max(0.0, min(1.0, gesamt_helligkeit)))
        ausgabe.append(reihe)
    return ausgabe

# ---------- Form-Generatoren ----------

def erzeuge_kugel(h: int = 22, b: int = 44, r_rel: float = 0.42) -> Tiefenkarte:
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

def erzeuge_kegel(h: int = 22, b: int = 44, r_rel: float = 0.45) -> Tiefenkarte:
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

def erzeuge_pyramide(h: int = 22, b: int = 44) -> Tiefenkarte:
    karte = [[0.0 for _ in range(b)] for _ in range(h)]
    cy, cx = (h - 1) / 2.0, (b - 1) / 2.0
    for y in range(h):
        for x in range(b):
            dy = abs(y - cy) / (h * 0.42)
            dx = abs(x - cx) / (b * 0.42)
            dist = max(dx, dy)
            if dist < 1.0:
                karte[y][x] = 1.0 - dist
    return Tiefenkarte(karte)

def erzeuge_huegelkette(h: int = 22, b: int = 44, seed: int = 17) -> Tiefenkarte:
    random.seed(seed)
    karte = [[0.0 for _ in range(b)] for _ in range(h)]
    zentren = [
        (h * 0.45, b * 0.35, min(h, b) * 0.35, 1.0),
        (h * 0.55, b * 0.65, min(h, b) * 0.30, 0.85),
        (h * 0.25, b * 0.70, min(h, b) * 0.22, 0.60)
    ]
    for y in range(h):
        for x in range(b):
            v = 0.0
            for cy, cx, rad, amp in zentren:
                dist = math.hypot((x - cx) * 0.5, y - cy)
                if dist < rad:
                    v += amp * math.cos((dist / rad) * (math.pi / 2.0))
            karte[y][x] = min(1.0, v)
    return Tiefenkarte(karte)

# ---------- Renderer ----------

PALETTE = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"

def render_ascii(helligkeit: List[List[float]]) -> str:
    h = len(helligkeit)
    b = len(helligkeit[0]) if h > 0 else 0
    p_len = len(PALETTE) - 1
    zeilen = []
    for y in range(h):
        z = []
        for x in range(b):
            val = helligkeit[y][x]
            idx = int(round(val * p_len))
            idx = max(0, min(p_len, idx))
            z.append(PALETTE[idx])
        zeilen.append("".join(z))
    return "\n".join(zeilen)

def sichere_eingabe(prompt: str, standard: str = "") -> str:
    try:
        sys.stdout.write(prompt)
        sys.stdout.flush()
        val = input().strip()
        return val if val else standard
    except EOFError:
        return standard

# ---------- Hauptprogramm ----------

def main():
    print("=== Fifos Schatten-Simulator: 3D-Tiefen-Erzwinger (Teil 42) ===")
    print("Mathematische Berechnung von Lichtquellen und Vektoren aktiv.\n")

    # Menü Formauswahl
    print("Waehle 3D-Geometrie:")
    print("  1) Glatte Kugel")
    print("  2) Kegelberg")
    print("  3) Scharfe Pyramide")
    print("  4) Huegelkette (Dodo-Landschaft)")
    wahl_form = sichere_eingabe("Auswahl [1-4, Standard: 1]: ", "1")

    hoehe, breite = 20, 44
    if wahl_form == "2":
        tk = erzeuge_kegel(hoehe, breite)
        form_name = "Kegelberg"
    elif wahl_form == "3":
        tk = erzeuge_pyramide(hoehe, breite)
        form_name = "Pyramide"
    elif wahl_form == "4":
        tk = erzeuge_huegelkette(hoehe, breite)
        form_name = "Huegelkette"
    else:
        tk = erzeuge_kugel(hoehe, breite)
        form_name = "Glatte Kugel"

    # Menü Lichtquellen-Setup
    print("\nWaehle Licht-Setup:")
    print("  1) Schraege Sonne von links-oben (starker Schlagschatten)")
    print("  2) Nahes Punktlicht direkt ueber dem Objekt (Radiallicht mit Glanzpunkt)")
    print("  3) Dual-Licht (Hauptsonne + kuehleres Gegenlicht fuer Plastizitaet)")
    wahl_licht = sichere_eingabe("Licht-Setup [1-3, Standard: 1]: ", "1")

    lichter: List[Lichtquelle] = []
    if wahl_licht == "2":
        # Punktlicht schwebend ueber dem Zentrum
        licht_pos: Vec3 = (breite * 0.4, hoehe * 0.35, 12.0)
        lichter.append(Lichtquelle('punkt', licht_pos, intensitaet=1.3, abfall=0.003))
        licht_info = "Punktlicht bei X=17 Y=7 Z=12"
    elif wahl_licht == "3":
        # Hauptsonne links-oben + Füllsonne rechts-unten
        lichter.append(Lichtquelle('gerichtet', (-1.0, -0.9, 0.9), intensitaet=0.85))
        lichter.append(Lichtquelle('gerichtet', (1.0, 0.7, 0.5), intensitaet=0.35))
        licht_info = "Dual-Licht: Hauptlicht (-1, -0.9, 0.9) + Fuelllicht (1, 0.7, 0.5)"
    else:
        # Schräge Sonne
        lichter.append(Lichtquelle('gerichtet', (-1.2, -1.0, 0.8), intensitaet=1.0))
        licht_info = "Gerichtete Sonne Vektor (-1.2, -1.0, 0.8)"

    print(f"\n[Berechne Vektoren fuer '{form_name}' mit {licht_info}]...")
    bild = berechne_tiefen_schattierung(tk, lichter, z_tiefe=8.0, ambient=0.12)

    # Statistiken auswerten
    alle_helligkeiten = [val for reihe in bild for val in reihe]
    min_h = min(alle_helligkeiten)
    max_h = max(alle_helligkeiten)
    schatten_anteil = sum(1 for val in alle_helligkeiten if val < 0.22) / len(alle_helligkeiten) * 100.0
    highlights = sum(1 for val in alle_helligkeiten if val > 0.85) / len(alle_helligkeiten) * 100.0

    print("\n--- RENDER-ERGEBNIS ---")
    print(render_ascii(bild))
    print("-" * breite)
    print(f"Tiefenanalyse: Min-Helligkeit={min_h:.2f}, Max-Helligkeit={max_h:.2f}")
    print(f"Schattenabdeckung: {schatten_anteil:.1f}% | Glanzlichter: {highlights:.1f}%")
    print("Mathematische Tiefenerzwingung erfolgreich abgeschlossen!")

if __name__ == '__main__':
    main()