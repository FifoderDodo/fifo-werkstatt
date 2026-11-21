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
                    
                    # Spekular (Blinn-Phong)
                    halb = vec3_norm(vec3_add(l_dir, sicht_vektor))
                    spek = max(0.0, vec3_dot(n, halb)) ** glanz_haerte
                    gesamt_helligkeit += spek * glanz_staerke * energie
            
            reihe.append(min(1.0, max(0.0, gesamt_helligkeit)))
        ausgabe.append(reihe)
    return ausgabe

# ---------- Hilfsfunktionen ----------

def generiere_beispieltiefe(breite: int = 80, hoehe: int = 40) -> List[List[float]]:
    """Erzeugt eine prozedurale Tiefenkarte: Hügel, Kugel, Rauschen."""
    daten = [[0.0 for _ in range(breite)] for _ in range(hoehe)]
    cx, cy = breite * 0.5, hoehe * 0.5
    for y in range(hoehe):
        for x in range(breite):
            dx = (x - cx) / (breite * 0.4)
            dy = (y - cy) / (hoehe * 0.4)
            dist = math.sqrt(dx * dx + dy * dy)
            # Großer weicher Hügel
            h = max(0.0, 1.0 - dist * 1.2)
            # Kleine Kugel oben drauf
            dx2 = (x - cx * 0.7) / (breite * 0.15)
            dy2 = (y - cy * 0.7) / (hoehe * 0.15)
            dist2 = math.sqrt(dx2 * dx2 + dy2 * dy2)
            h += max(0.0, 0.8 - dist2 * 1.5)
            # Etwas Rauschen für Textur
            h += (random.random() - 0.5) * 0.05
            daten[y][x] = max(0.0, min(1.0, h))
    return daten

def helligkeit_zu_ascii(wert: float) -> str:
    """Mappt 0.0-1.0 auf ASCII-Rampe."""
    rampe = " .'`^\":;Il!i><~+_-?][}{1)(|\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8@$B@$"
    idx = int(wert * (len(rampe) - 1))
    return rampe[idx]

def drucke_ergebnis(schattierung: List[List[float]]):
    """Gibt das gerenderte Bild als ASCII aus."""
    for reihe in schattierung:
        zeile = ''.join(helligkeit_zu_ascii(w) for w in reihe)
        print(zeile)

def waehle_licht_setup(tk: Tiefenkarte) -> List[Lichtquelle]:
    """Interaktive Auswahl der Lichtkonfiguration."""
    print("\nLicht-Setups:")
    print("1) Schräge Sonne von links-oben (starker Schlagschatten)")
    print("2) Nahes Punktlicht direkt über dem Objekt (Radiallicht mit Glanzpunkt)")
    print("3) Dual-Licht (Hauptsonne + kühleres Gegenlicht für Plastizität)")
    
    try:
        eingabe = input("Wähle [1-3, Standard: 1]: ").strip()
    except EOFError:
        print("\nKeine Eingabe möglich, nutze Standard.")
        eingabe = "1"
    
    wahl = eingabe if eingabe in ("1", "2", "3") else "1"
    cx, cy = tk.b * 0.5, tk.h * 0.5
    
    if wahl == "1":
        # Gerichtete Sonne von links-oben (Richtung Vektor zeigt ZUR Quelle)
        return [Lichtquelle('gerichtet', vec3_norm((0.6, -0.4, 1.0)), intensitaet=1.2)]
    elif wahl == "2":
        # Punktlicht mittig über der Szene
        return [Lichtquelle('punkt', (cx, cy, max(tk.b, tk.h) * 0.8), intensitaet=3.0, abfall=0.0015)]
    else:
        # Dual: Hauptlicht warm, Fill-Licht kühl von rechts
        return [
            Lichtquelle('gerichtet', vec3_norm((0.5, -0.3, 1.0)), intensitaet=1.0),
            Lichtquelle('gerichtet', vec3_norm((-0.4, 0.2, 0.8)), intensitaet=0.4)
        ]

# ---------- Hauptprogramm ----------

def main():
    random.seed(42)  # Reproduzierbar
    print("=== Schatten-Simulator Teil 43: Lichtquellen & Raymarch ===")
    
    # 1. Tiefenkarte erzeugen
    tk = Tiefenkarte(generiere_beispieltiefe(100, 50))
    mn, mx, sp = tk.statistik()
    print(f"Tiefenkarte: {tk.b}x{tk.h}, Range: {mn:.3f}-{mx:.3f} (Spanne {sp:.3f})")
    
    # 2. Licht-Setup wählen
    lichter = waehle_licht_setup(tk)
    print(f"Aktive Lichtquellen: {len(lichter)}")
    for i, l in enumerate(lichter):
        print(f"  {i+1}. Typ={l.typ}, Vec={l.vec}, Int={l.intensitaet}")
    
    # 3. Berechnung
    print("\n[Berechne Vektor-Raymarching & Blinn-Phong Shading...]")
    schattierung = berechne_tiefen_schattierung(
        tk, lichter,
        z_tiefe=8.0,
        ambient=0.12,
        glanz_staerke=0.5,
        glanz_haerte=32.0
    )
    
    # 4. Ausgabe
    print("\nErgebnis (ASCII-Tiefe mit Schatten & Glanz):")
    drucke_ergebnis(schattierung)
    print("\nFertig. Drücke Enter zum Beenden...")
    try:
        input()
    except EOFError:
        pass

if __name__ == "__main__":
    main()