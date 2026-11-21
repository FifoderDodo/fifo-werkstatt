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
                    
                    # Spekularer Anteil (Blinn-Phong)
                    h = vec3_norm(vec3_add(l_dir, sicht_vektor))
                    spek = max(0.0, vec3_dot(n, h)) ** glanz_haerte
                    gesamt_helligkeit += spek * glanz_staerke * energie
            
            # Clamping auf [0, 1] für saubere ASCII-Abbildung
            reihe.append(max(0.0, min(1.0, gesamt_helligkeit)))
        ausgabe.append(reihe)
    return ausgabe

# ---------- Hilfsfunktionen für Szenenaufbau ----------

def erzeuge_prozedurale_tiefenkarte(breite: int = 80, hoehe: int = 40) -> Tiefenkarte:
    """Erzeugt eine Tiefenkarte mit Hügeln, einer Kugel und etwas Rauschen."""
    daten = [[0.0 for _ in range(breite)] for _ in range(hoehe)]
    cx, cy = breite * 0.5, hoehe * 0.5
    
    for y in range(hoehe):
        for x in range(breite):
            # Zwei große Hügel
            dx1 = (x - cx * 0.4) / (breite * 0.3)
            dy1 = (y - cy * 0.6) / (hoehe * 0.3)
            h1 = math.exp(-(dx1*dx1 + dy1*dy1) * 2.0) * 0.6
            
            dx2 = (x - cx * 1.5) / (breite * 0.25)
            dy2 = (y - cy * 0.4) / (hoehe * 0.25)
            h2 = math.exp(-(dx2*dx2 + dy2*dy2) * 2.5) * 0.5
            
            # Eine Kugel in der Mitte
            dx3 = (x - cx) / (breite * 0.2)
            dy3 = (y - cy) / (hoehe * 0.2)
            r2 = dx3*dx3 + dy3*dy3
            h3 = math.sqrt(max(0.0, 1.0 - r2)) * 0.7 if r2 < 1.0 else 0.0
            
            # Feines Rauschen für Oberflächenstruktur
            noise = (random.random() - 0.5) * 0.03
            
            daten[y][x] = min(1.0, h1 + h2 + h3 + noise)
    
    return Tiefenkarte(daten)

def waehle_licht_setup() -> List[Lichtquelle]:
    """Interaktive Auswahl eines Licht-Setups."""
    print("\nVerfügbare Licht-Setups:")
    print("  1) Klassisch: Ein gerichtetes Licht von oben-links")
    print("  2) Dramatisch: Zwei Punktlichter (warm/kalt) + schwaches Fill")
    print("  3) Studio: Drei Punktlichter (Key, Fill, Rim)")
    
    while True:
        try:
            wahl = input("Wähle Setup (1-3) [1]: ").strip()
            if wahl == '':
                wahl = '1'
            if wahl in ('1', '2', '3'):
                break
            print("Bitte 1, 2 oder 3 eingeben.")
        except EOFError:
            print("\nKeine Eingabe möglich, nutze Standard (1).")
            wahl = '1'
            break
    
    if wahl == '1':
        # Gerichtetes Licht von oben-links (Richtung zur Quelle)
        return [Lichtquelle('gerichtet', vec3_norm((0.5, -0.3, 1.0)), intensitaet=1.2)]
    elif wahl == '2':
        # Zwei Punktlichter: warm (orange) links, kalt (blau) rechts
        return [
            Lichtquelle('punkt', ( -20.0, 10.0, 30.0), intensitaet=1.5, abfall=0.0015),
            Lichtquelle('punkt', ( 100.0, 10.0, 25.0), intensitaet=1.0, abfall=0.0015),
            Lichtquelle('gerichtet', vec3_norm((0.0, 0.2, 1.0)), intensitaet=0.2)  # Fill
        ]
    else:
        # Drei-Punkt-Beleuchtung
        return [
            Lichtquelle('punkt', ( 10.0, -10.0, 40.0), intensitaet=1.8, abfall=0.001),  # Key
            Lichtquelle('punkt', ( 70.0, 20.0, 30.0), intensitaet=0.6, abfall=0.0015),  # Fill
            Lichtquelle('punkt', ( 40.0, 20.0, -20.0), intensitaet=1.2, abfall=0.002)   # Rim (von hinten)
        ]

# ---------- Professionelles ASCII-Rendering ----------

# Erweiterter Zeichen-Rampe für bessere Tiefenwahrnehmung (von dunkel nach hell)
ASCII_RAMPE = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
# 70 Stufen, kann per Gamma korrigiert werden

def helligkeit_zu_ascii(helligkeit: float, gamma: float = 1.8) -> str:
    """Wandelt normierte Helligkeit (0-1) in ASCII-Zeichen um mit Gamma-Korrektur."""
    # Gamma-Korrektur für lineare Wahrnehmung
    korrigiert = helligkeit ** (1.0 / gamma)
    index = int(korrigiert * (len(ASCII_RAMPE) - 1))
    return ASCII_RAMPE[index]

def rendere_ascii(helligkeits_karte: List[List[float]]) -> str:
    """Erzeugt einen mehrzeiligen String aus der Helligkeitskarte."""
    zeilen = []
    for reihe in helligkeits_karte:
        zeile = ''.join(helligkeit_zu_ascii(w) for w in reihe)
        zeilen.append(zeile)
    return '\n'.join(zeilen)

# ---------- Hauptprogramm ----------

def main() -> None:
    print("=== Schatten-Simulator v44 ===")
    print("Berechne 3D-Tiefe und echten Schattenwurf für flache Bilder...")
    
    # 1. Tiefenkarte erzeugen
    print("\nErzeuge prozedurale Tiefenkarte (Hügel + Kugel + Rauschen)...")
    tk = erzeuge_prozedurale_tiefenkarte(80, 40)
    mn, mx, sp = tk.statistik()
    print(f"Tiefenbereich: {mn:.3f} - {mx:.3f} (Spannweite {sp:.3f})")
    
    # 2. Licht-Setup wählen
    lichter = waehle_licht_setup()
    print(f"Aktive Lichtquellen: {len(lichter)}")
    for i, l in enumerate(lichter):
        print(f"  {i+1}. {l.typ.capitalize()}, Intensität={l.intensitaet:.2f}")
    
    # 3. Schattierung berechnen
    print("\nRaymarching & Shading (kann einen Moment dauern)...")
    helligkeits_karte = berechne_tiefen_schattierung(tk, lichter, z_tiefe=6.0)
    
    # 4. ASCII-Ausgabe
    print("\n--- Gerendertes Bild (ASCII) ---")
    ascii_bild = rendere_ascii(helligkeits_karte)
    print(ascii_bild)
    print("--- Ende ---")
    
    # 5. Optional: Speichern als Textdatei
    try:
        speichern = input("\nAls Textdatei speichern? (j/N): ").strip().lower()
        if speichern == 'j':
            dateiname = input("Dateiname [schatten.txt]: ").strip() or "schatten.txt"
            with open(dateiname, 'w', encoding='utf-8') as f:
                f.write(ascii_bild)
            print(f"Gespeichert unter {dateiname}")
    except EOFError:
        pass
    
    print("\nFifo der Dodo sagt: Tiefe sieht gut aus! Bis zum nächsten Commit.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
    except Exception as e:
        print(f"\nFehler: {e}")
        import traceback
        traceback.print_exc()