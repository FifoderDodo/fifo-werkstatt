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

def diffuse_schatten(tk: Tiefenkarte,
                     licht_richtung: Vec3 = (0.5, -0.3, 1.0),
                     umgebung: float = 0.25,
                     schatten_harte: float = 1.0,
                     z_skalierung: float = 2.0) -> List[List[float]]:
    """
    Berechnet diffuse Beleuchtung mit weichem Schattenwurf (Raymarching).
    Gibt Helligkeitswerte 0..1 pro Pixel zurück.
    """
    ldir = vec3_norm(licht_richtung)
    normals = tk.normalen(z_skalierung)
    h, b = tk.h, tk.b
    ergebnis = [[0.0 for _ in range(b)] for _ in range(h)]
    
    # Schatten-Raymarching Parameter
    schritte = 32
    max_dist = max(h, b) * 1.5
    
    for y in range(h):
        for x in range(b):
            # Basis-Höhe an diesem Pixel
            basis_h = tk.daten[y][x]
            if basis_h <= 0.0:
                ergebnis[y][x] = umgebung
                continue
            
            # Normalen-basierte diffuse Beleuchtung
            n = normals[y][x]
            diffuse = max(0.0, vec3_dot(n, ldir))
            
            # Schatten-Test: Marschieren vom Pixel in Lichtrichtung
            schatten = 1.0
            # Startpunkt leicht über der Oberfläche
            start_x = x + ldir[0] * 0.5
            start_y = y + ldir[1] * 0.5
            start_z = basis_h + ldir[2] * 0.5 * z_skalierung
            
            for i in range(1, schritte + 1):
                t = i / schritte
                # Aktuelle Position entlang des Strahls
                px = start_x + ldir[0] * t * max_dist / schritte
                py = start_y + ldir[1] * t * max_dist / schritte
                pz = start_z + ldir[2] * t * max_dist / schritte / z_skalierung
                
                # Prüfen ob wir das Höhenfeld schneiden
                if 0 <= py < h - 1 and 0 <= px < b - 1:
                    hoehe_feld = tk.get_bilinear(py, px)
                    if pz < hoehe_feld * z_skalierung:
                        # Im Schatten - weicher Übergang
                        schatten = 1.0 - (1.0 - schatten_harte) * (1.0 - t)
                        break
            
            # Kombinieren: Ambient + Diffuse * Schatten
            helligkeit = umgebung + (1.0 - umgebung) * diffuse * schatten
            ergebnis[y][x] = max(0.0, min(1.0, helligkeit))
    
    return ergebnis


def ambient_occlusion(tk: Tiefenkarte, radius: int = 3, samples: int = 8) -> List[List[float]]:
    """Einfaches Screen-Space Ambient Occlusion (SSAO) für mehr Tiefe."""
    h, b = tk.h, tk.b
    ao = [[1.0 for _ in range(b)] for _ in range(h)]
    normals = tk.normalen()
    
    for y in range(h):
        for x in range(b):
            if tk.daten[y][x] <= 0.0:
                continue
            n = normals[y][x]
            verdeckt = 0
            
            for _ in range(samples):
                # Zufällige Richtung in Hemisphäre
                winkel = random.random() * 2.0 * math.pi
                dist = random.random() * radius
                sx = x + math.cos(winkel) * dist
                sy = y + math.sin(winkel) * dist
                
                if 0 <= sy < h and 0 <= sx < b:
                    nachbar_h = tk.get_bilinear(sy, sx)
                    if nachbar_h > tk.daten[y][x] + 0.05:
                        verdeckt += 1
            
            ao[y][x] = 1.0 - (verdeckt / samples) * 0.5
    
    return ao


def gamma_korrektur(wert: float, gamma: float = 2.2) -> float:
    """Gamma-Korrektur für lineare -> sRGB Umrechnung."""
    if wert <= 0.0:
        return 0.0
    if wert >= 1.0:
        return 1.0
    return wert ** (1.0 / gamma)


def rendere_ascii(helligkeiten: List[List[float]],
                  breit: int = 80,
                  hoehe: int = 40,
                  invertiert: bool = False,
                  gamma: float = 2.2) -> str:
    """Skaliert und rendert Helligkeitskarte als ASCII-Art."""
    h_src = len(helligkeiten)
    b_src = len(helligkeiten[0]) if h_src > 0 else 0
    if h_src == 0 or b_src == 0:
        return ""
    
    # ASCII-Rampen (dunkel -> hell)
    if invertiert:
        ramp = "@%#*+=-:. "
    else:
        ramp = " .:-=+*#%@"
    
    zeilen = []
    for ziel_y in range(hoehe):
        src_y = ziel_y * (h_src - 1) / max(1, hoehe - 1)
        zeile = []
        for ziel_x in range(breit):
            src_x = ziel_x * (b_src - 1) / max(1, breit - 1)
            # Bilineare Interpolation für Skalierung
            y0 = int(math.floor(src_y))
            x0 = int(math.floor(src_x))
            y1 = min(y0 + 1, h_src - 1)
            x1 = min(x0 + 1, b_src - 1)
            dy = src_y - y0
            dx = src_x - x0
            
            h00 = helligkeiten[y0][x0]
            h01 = helligkeiten[y0][x1]
            h10 = helligkeiten[y1][x0]
            h11 = helligkeiten[y1][x1]
            
            h0 = h00 * (1 - dx) + h01 * dx
            h1 = h10 * (1 - dx) + h11 * dx
            val = h0 * (1 - dy) + h1 * dy
            
            val = gamma_korrektur(val, gamma)
            idx = int(val * (len(ramp) - 1))
            zeile.append(ramp[idx])
        zeilen.append(''.join(zeile))
    return '\n'.join(zeilen)


def mische_helligkeiten(basis: List[List[float]],
                        overlay: List[List[float]],
                        mischung: float = 0.5) -> List[List[float]]:
    """Mischt zwei Helligkeitskarten (z.B. Licht + AO)."""
    h = len(basis)
    b = len(basis[0]) if h > 0 else 0
    erg = [[0.0 for _ in range(b)] for _ in range(h)]
    for y in range(h):
        for x in range(b):
            erg[y][x] = basis[y][x] * (1.0 - mischung) + overlay[y][x] * mischung
    return erg


# ---------- Hauptprogramm ----------

FORMEN = {
    'kugel': erzeuge_kugel,
    'kegel': erzeuge_kegel,
    'pyramide': erzeuge_stufenpyramide,
    'wellblech': erzeuge_wellblech,
    'huegel': erzeuge_zufaellige_huegel,
}

FORMEN_ALIASES = {
    '1': 'kugel',
    '2': 'kegel',
    '3': 'pyramide',
    '4': 'wellblech',
    '5': 'huegel',
}

def parse_form_eingabe(eingabe: str) -> Optional[str]:
    """Parst Form-Eingabe: Name oder Zahl 1-5."""
    eingabe = eingabe.strip().lower()
    if eingabe in FORMEN:
        return eingabe
    if eingabe in FORMEN_ALIASES:
        return FORMEN_ALIASES[eingabe]
    return None

def frage_form(stdin, stdout) -> str:
    """Fragt Form ab mit Validierung."""
    while True:
        try:
            stdout.write("Form [kugel, kegel, pyramide, wellblech, huegel] [kugel]: ")
            stdout.flush()
            eingabe = stdin.readline()
            if not eingabe:
                return 'kugel'
            eingabe = eingabe.strip()
            if not eingabe:
                return 'kugel'
            form = parse_form_eingabe(eingabe)
            if form:
                return form
            stdout.write(f"Ungültige Eingabe: '{eingabe}'. Versuche es nochmal.\n")
            stdout.flush()
        except (EOFError, KeyboardInterrupt):
            return 'kugel'

def frage_zahl(prompt: str, default: float, stdin, stdout,
               min_wert: float = None, max_wert: float = None) -> float:
    """Fragt eine Zahl ab mit Validierung."""
    while True:
        try:
            stdout.write(f"{prompt} [{default}]: ")
            stdout.flush()
            eingabe = stdin.readline()
            if not eingabe:
                return default
            eingabe = eingabe.strip()
            if not eingabe:
                return default
            wert = float(eingabe)
            if min_wert is not None and wert < min_wert:
                stdout.write(f"Wert muss >= {min_wert} sein.\n")
                continue
            if max_wert is not None and wert > max_wert:
                stdout.write(f"Wert muss <= {max_wert} sein.\n")
                continue
            return wert
        except ValueError:
            stdout.write(f"Ungültige Zahl: '{eingabe}'.\n")
        except (EOFError, KeyboardInterrupt):
            return default

def frage_ja_nein(prompt: str, default: bool, stdin, stdout) -> bool:
    """Fragt ja/nein ab."""
    while True:
        try:
            d = 'j' if default else 'n'
            stdout.write(f"{prompt} [{d}]: ")
            stdout.flush()
            eingabe = stdin.readline()
            if not eingabe:
                return default
            eingabe = eingabe.strip().lower()
            if not eingabe:
                return default
            if eingabe in ('j', 'ja', 'y', 'yes', '1', 'true'):
                return True
            if eingabe in ('n', 'nein', 'no', '0', 'false'):
                return False
            stdout.write("Bitte 'j' oder 'n' eingeben.\n")
        except (EOFError, KeyboardInterrupt):
            return default

def main() -> int:
    stdin = sys.stdin
    stdout = sys.stdout
    stderr = sys.stderr
    
    stderr.write("🦤 Fifo's Schatten-Simulator v41 — Tiefe für flache Bilder\n")
    stderr.write("========================================================\n\n")
    
    # Form wählen
    form_name = frage_form(stdin, stdout)
    form_func = FORMEN[form_name]
    
    # Parameter abfragen
    hoehe = int(frage_zahl("Höhe (Zeilen)", 20, stdin, stdout, 5, 100))
    breite = int(frage_zahl("Breite (Spalten)", 40, stdin, stdout, 10, 200))
    
    # Form-spezifische Parameter
    kwargs = {'h': hoehe, 'b': breite}
    if form_name == 'kugel':
        kwargs['r_rel'] = frage_zahl("Radius (relativ)", 0.42, stdin, stdout, 0.1, 0.8)
    elif form_name == 'kegel':
        kwargs['r_rel'] = frage_zahl("Radius (relativ)", 0.45, stdin, stdout, 0.1, 0.8)
    elif form_name == 'wellblech':
        kwargs['wellen'] = int(frage_zahl("Anzahl Wellen", 8, stdin, stdout, 1, 30))
    elif form_name == 'huegel':
        kwargs['anzahl'] = int(frage_zahl("Anzahl Hügel", 5, stdin, stdout, 1, 20))
        kwargs['seed'] = int(frage_zahl("Zufalls-Seed", 42, stdin, stdout, 0, 9999))
    
    tk = form_func(**kwargs)
    
    # Licht-Parameter
    stderr.write("\n--- Licht-Einstellungen ---\n")
    lx = frage_zahl("Licht X", 0.5, stdin, stdout, -2.0, 2.0)
    ly = frage_zahl("Licht Y", -0.3, stdin, stdout, -2.0, 2.0)
    lz = frage_zahl("Licht Z", 1.0, stdin, stdout, 0.1, 3.0)
    licht_dir = (lx, ly, lz)
    
    umgebung = frage_zahl("Umgebungslicht", 0.25, stdin, stdout, 0.0, 1.0)
    schatten_harte = frage_zahl("Schatten-Härte", 1.0, stdin, stdout, 0.0, 1.0)
    z_skalierung = frage_zahl("Z-Skalierung (Höhenübertreibung)", 2.0, stdin, stdout, 0.1, 10.0)
    
    # AO
    ao_nutzen = frage_ja_nein("Ambient Occlusion nutzen?", True, stdin, stdout)
    ao_radius = 3
    ao_samples = 8
    if ao_nutzen:
        ao_radius = int(frage_zahl("AO Radius", 3, stdin, stdout, 1, 10))
        ao_samples = int(frage_zahl("AO Samples", 8, stdin, stdout, 4, 32))
    
    # Render-Einstellungen
    stderr.write("\n--- Render-Einstellungen ---\n")
    ascii_breit = int(frage_zahl("ASCII Breite", 80, stdin, stdout, 20, 200))
    ascii_hoch = int(frage_zahl("ASCII Höhe", 40, stdin, stdout, 10, 100))
    invertiert = frage_ja_nein("Invertiert (hell auf dunkel)?", False, stdin, stdout)
    gamma = frage_zahl("Gamma", 2.2, stdin, stdout, 1.0, 3.0)
    
    # Berechnungen
    stderr.write("\n🦤 Berechne Normalen...\n")
    stderr.write("🦤 Berechne diffuse Beleuchtung mit Schatten...\n")
    helligkeiten = diffuse_schatten(tk, licht_dir, umgebung, schatten_harte, z_skalierung)
    
    if ao_nutzen:
        stderr.write("🦤 Berechne Ambient Occlusion...\n")
        ao = ambient_occlusion(tk, ao_radius, ao_samples)
        helligkeiten = mische_helligkeiten(helligkeiten, ao, 0.5)
    
    # Vorschau auf stderr (klein)
    stderr.write("\n--- Vorschau (klein) ---\n")
    vorschau = rendere_ascii(helligkeiten, 60, 25, invertiert, gamma)
    stderr.write(vorschau + "\n\n")
    
    # Vollauflösung auf stdout
    stderr.write("--- Ausgabe (voll) ---\n")
    ausgabe = rendere_ascii(helligkeiten, ascii_breit, ascii_hoch, invertiert, gamma)
    stdout.write(ausgabe + "\n")
    
    stderr.write("\n🦤 Fertig! Drücke Enter für Ende...\n")
    try:
        stdin.readline()
    except (EOFError, KeyboardInterrupt):
        pass
    
    return 0

if __name__ == "__main__":
    sys.exit(main())