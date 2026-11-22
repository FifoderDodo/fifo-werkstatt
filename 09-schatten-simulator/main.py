from __future__ import annotations
import math
import sys
from typing import List, Tuple

# ─── Typ-Aliase ──────────────────────────────────────────────────────
Vec3 = Tuple[float, float, float]

# ─── Konstanten ──────────────────────────────────────────────────────
# Kleiner Epsilon-Wert für Null-Checks
EPSILON = 1e-9
# Standard-Offset gegen Self-Shadowing-Artefakte (Peter Panning vermeiden)
OFFSET_BIAS = 0.15
# PCF-Kernel für weiche Schatten (3x3 Umfeld)
PCF_KERNEL_3X3: List[Tuple[float, float]] = [
    (0.0, 0.0),
    (-1.0, -1.0), (0.0, -1.0), (1.0, -1.0),
    (-1.0,  0.0),           (1.0,  0.0),
    (-1.0,  1.0), (0.0,  1.0), (1.0,  1.0),
]

# ─── Vektormathematik – minimal, aber ausreichend ────────────────────

def vec3_norm(v: Vec3) -> Vec3:
    """Normalisiert einen 3D-Vektor. Fällt bei Nullvektor auf (0,0,1) zurück."""
    x, y, z = v
    l = math.sqrt(x * x + y * y + z * z)
    if l < EPSILON:
        return (0.0, 0.0, 1.0)
    return (x / l, y / l, z / l)


def vec3_dot(a: Vec3, b: Vec3) -> float:
    """Skalarprodukt zweier 3D-Vektoren."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vec3_add(a: Vec3, b: Vec3) -> Vec3:
    """Addiert zwei 3D-Vektoren komponentenweise."""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vec3_sub(a: Vec3, b: Vec3) -> Vec3:
    """Subtrahiert b von a komponentenweise."""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vec3_scale(v: Vec3, s: float) -> Vec3:
    """Skaliert einen 3D-Vektor mit einem Skalar."""
    return (v[0] * s, v[1] * s, v[2] * s)

# ─── Quasi-Zufallsfolgen für Area-Light-Sampling ────────────────────

def _radical_inverse_base2(index: int) -> float:
    """Radikale Inverse Basis 2 (Van-der-Corput-Sequenz). Gibt gleichverteilte Werte in [0,1)."""
    result = 0.0
    factor = 0.5
    i = index
    while i > 0:
        if i & 1:
            result += factor
        factor *= 0.5
        i >>= 1
    return result


def hammersley_2d(index: int, count: int) -> Tuple[float, float]:
    """Hammersley-Punkt in 2D für gegebenen Index und Gesamtzahl. Sehr gleichmäßig verteilt."""
    if count <= 0:
        return (0.0, 0.0)
    x = (index + 0.5) / count          # jitterter regulärer Grid in x
    y = _radical_inverse_base2(index)  # Van-der-Corput in y
    return (x, y)

# ─── Tiefenkarte (Höhenfeld) ────────────────────────────────────────

class Tiefenkarte:
    """Höhenfeld mit bilinearer Interpolation und Clamping an den Rändern."""
    
    def __init__(self, daten: List[List[float]]):
        self.daten = daten
        self.h = len(daten)                    # Zeilen (y)
        self.b = len(daten[0]) if daten else 0 # Spalten (x)
    
    def get_bilinear(self, y: float, x: float) -> float:
        """Bilineare Interpolation mit Clamping an Rändern.
        
        Koordinaten (y, x) entsprechen Zeile/Spalte. Werte außerhalb
        werden auf den gültigen Bereich geklemmt (kein Wrapping).
        """
        if self.h == 0 or self.b == 0:
            return 0.0
        
        # Ganzzahlige Koordinaten der vier Eckpunkte
        y0 = int(math.floor(y))
        x0 = int(math.floor(x))
        
        # Clamping auf gültigen Interpolationsbereich [0, h-2] × [0, b-2]
        if y0 < 0:
            y0 = 0
        elif y0 >= self.h - 1:
            y0 = self.h - 2
        if x0 < 0:
            x0 = 0
        elif x0 >= self.b - 1:
            x0 = self.b - 2
        
        y1 = y0 + 1
        x1 = x0 + 1
        
        # Bruchanteile für Interpolation
        dy = y - y0
        dx = x - x0
        
        # Vier Eckwerte holen
        v00 = self.daten[y0][x0]
        v10 = self.daten[y0][x1]
        v01 = self.daten[y1][x0]
        v11 = self.daten[y1][x1]
        
        # Bilineare Interpolation: erst x, dann y (oder umgekehrt)
        return (v00 * (1 - dx) * (1 - dy) +
                v10 * dx * (1 - dy) +
                v01 * (1 - dx) * dy +
                v11 * dx * dy)

# ─── Shadow-Raymarching mit PCF & Area Light ────────────────────────

def raymarch_schatten(tk: Tiefenkarte,
                      start: Vec3,
                      l_dir: Vec3,
                      max_dist: float,
                      z_skalierung: float,
                      schritte: int = 32,
                      pcf_radius: float = 0.6,
                      pcf_samples: int = 9,
                      light_radius: float = 0.0,
                      light_samples: int = 1) -> float:
    """Raymarching-Schatten mit PCF (Percentage Closer Filtering) und Area-Light-Sampling.
    
    Parameter:
        tk:             Tiefenkarte (Höhenfeld)
        start:          Startpunkt des Rays (x, y, z) – meist knapp über Oberfläche
        l_dir:          Normierte Lichtrichtung (zeigt VOM Licht ZUR Oberfläche)
        max_dist:       Maximale Marschdistanz
        z_skalierung:   Skalierung der Höhenwerte (Weltmaßstab)
        schritte:       Anzahl Raymarch-Schritte (mehr = genauer, langsamer)
        pcf_radius:     Radius des PCF-Kernels in Texel (weichere Kanten)
        pcf_samples:    Anzahl PCF-Taps (1 = hart, 9 = 3x3 Kernel)
        light_radius:   Radius des Area Lights (0 = Punktlichtquelle)
        light_samples:  Anzahl Samples auf Area Light (für Penumbra)
    
    Rückgabe:
        Schattenfaktor in [0, 1]: 0 = voller Schatten, 1 = voll beleuchtet
    """
    # PCF-Kernel wählen
    kernel = PCF_KERNEL_3X3
    if pcf_samples <= 1:
        kernel = [(0.0, 0.0)]
    
    # Area-Light Offsets generieren (Hammersley auf Disk)
    light_offsets = [(0.0, 0.0)]
    if light_radius > 1e-6 and light_samples > 1:
        light_offsets = []
        for i in range(light_samples):
            u, v = hammersley_2d(i, light_samples)
            phi = 2.0 * math.pi * u
            r = light_radius * math.sqrt(v)  # sqrt für gleichmäßige Verteilung auf Disk
            light_offsets.append((r * math.cos(phi), r * math.sin(phi)))
    
    schatten_summe = 0.0
    total_taps = len(kernel[:pcf_samples]) * len(light_offsets)
    
    if total_taps == 0:
        return 1.0

    # Basis-Schrittweite entlang des Rays
    step_dist = max_dist / schritte
    
    # Für jedes Area-Light-Sample
    for lx_off, ly_off in light_offsets:
        # Lichtrichtung leicht variieren für Area Light
        # Wir bauen eine Orthonormalbasis um l_dir herum (einfachheitshalber heuristisch)
        if light_radius > 1e-6:
            # Finde einen Vektor, der nicht parallel zu l_dir ist
            if abs(l_dir[0]) < 0.9:
                up = (1.0, 0.0, 0.0)
            else:
                up = (0.0, 1.0, 0.0)
            # Right = up x l_dir
            right = vec3_norm(vec3_sub(
                (up[1]*l_dir[2] - up[2]*l_dir[1],
                 up[2]*l_dir[0] - up[0]*l_dir[2],
                 up[0]*l_dir[1] - up[1]*l_dir[0]),
                (0,0,0)
            ))
            # TrueUp = l_dir x right
            true_up = vec3_norm((
                l_dir[1]*right[2] - l_dir[2]*right[1],
                l_dir[2]*right[0] - l_dir[0]*right[2],
                l_dir[0]*right[1] - l_dir[1]*right[0]
            ))
            # Neue Lichtrichtung
            varied_dir = vec3_norm(vec3_add(
                vec3_add(l_dir, vec3_scale(right, lx_off)),
                vec3_scale(true_up, ly_off)
            ))
        else:
            varied_dir = l_dir

        # Für jeden PCF-Tap
        for kx, ky in kernel[:pcf_samples]:
            # Startposition mit PCF-Offset (in Texel-Koordinaten)
            # Wir bewegen den Startpunkt auf der XY-Ebene
            cur_x = start[0] + kx * pcf_radius
            cur_y = start[1] + ky * pcf_radius
            cur_z = start[2]
            
            # Raymarching-Schleife
            hit = False
            for _ in range(schritte):
                # Aktuelle Höhe der Tiefenkarte an dieser XY-Position abfragen
                # Koordinaten in Textureinheiten (Pixel)
                map_h = tk.get_bilinear(cur_y, cur_x) * z_skalierung
                
                # Wenn Ray unter die Oberfläche taucht -> Shadow
                if cur_z <= map_h + OFFSET_BIAS:
                    hit = True
                    break
                
                # Nächster Schritt
                cur_x += varied_dir[0] * step_dist
                cur_y += varied_dir[1] * step_dist
                cur_z += varied_dir[2] * step_dist
                
                # Frühabbruch wenn Ray die Szene verlässt (optional, hier einfach max_dist)
                # Wir vertrauen auf die Schrittanzahl
            
            if not hit:
                schatten_summe += 1.0  # Kein Treffer = beleuchtet
            # else: hit -> summe += 0 (Schatten)
    
    return schatten_summe / total_taps

# ─── Demo & Interaktion ──────────────────────────────────────────────

def erzeuge_testkarte(groesse: int = 16) -> Tiefenkarte:
    """Erzeugt eine hübsche Test-Tiefenkarte (Hügel + Tal + Noise)."""
    daten = []
    for y in range(groesse):
        zeile = []
        for x in range(groesse):
            # Normalisierte Koordinaten -1..1
            nx = (x - groesse * 0.5) / (groesse * 0.5)
            ny = (y - groesse * 0.5) / (groesse * 0.5)
            dist = math.sqrt(nx*nx + ny*ny)
            # Ein großer Hügel in der Mitte
            hill = math.exp(-dist * dist * 3.0) * 1.5
            # Ein paar Wellen
            waves = math.sin(nx * 6.0) * math.cos(ny * 5.0) * 0.15
            # Kleines zufälliges Detail (deterministisch)
            noise = ((x * 17 + y * 23) % 11) / 11.0 * 0.05
            zeile.append(hill + waves + noise)
        daten.append(zeile)
    return Tiefenkarte(daten)


def demo_schatten() -> None:
    """Führt eine kleine Demo-Szene aus und druckt Schattenwerte."""
    print("\n🦤 Fifo startet Schatten-Demo...")
    tk = erzeuge_testkarte(16)
    print(f"Tiefenkarte erzeugt: {tk.b}x{tk.h} Pixel")
    
    # Licht von schräg oben-links
    l_dir = vec3_norm((-0.5, -0.3, -1.0))
    # Startpunkt in der Bildmitte, etwas über dem Gelände
    mid_x, mid_y = tk.b * 0.5, tk.h * 0.5
    ground_h = tk.get_bilinear(mid_y, mid_x) * 2.0
    start = (mid_x, mid_y, ground_h + 0.5)
    
    print(f"Start: ({start[0]:.1f}, {start[1]:.1f}, {start[2]:.2f})")
    print(f"Lichtdir: ({l_dir[0]:.2f}, {l_dir[1]:.2f}, {l_dir[2]:.2f})")
    
    # 1. Hartes Schatten (Punktlicht, kein PCF)
    s_hart = raymarch_schatten(tk, start, l_dir, max_dist=20.0, z_skalierung=2.0,
                               schritte=64, pcf_samples=1, light_radius=0.0)
    print(f"\n☀️  Hartes Schatten (Punktlicht): {s_hart:.3f}")
    
    # 2. Weiches Schatten (PCF 3x3)
    s_pcf = raymarch_schatten(tk, start, l_dir, max_dist=20.0, z_skalierung=2.0,
                              schritte=64, pcf_samples=9, pcf_radius=0.8,
                              light_radius=0.0)
    print(f"☁️  Weich (PCF 3x3):              {s_pcf:.3f}")
    
    # 3. Area Light (Penumbra)
    s_area = raymarch_schatten(tk, start, l_dir, max_dist=20.0, z_skalierung=2.0,
                               schritte=64, pcf_samples=9, pcf_radius=0.8,
                               light_radius=0.5, light_samples=16)
    print(f"💡 Area Light (r=0.5, 16 samp):   {s_area:.3f}")
    
    # 4. Kombiniert: Area Light + PCF (High Quality)
    s_hq = raymarch_schatten(tk, start, l_dir, max_dist=20.0, z_skalierung=2.0,
                             schritte=128, pcf_samples=9, pcf_radius=1.0,
                             light_radius=0.8, light_samples=32)
    print(f"🎨 High Quality (Area+PCF):       {s_hq:.3f}")
    print("\n✅ Demo fertig.")


def interaktiv() -> None:
    """Ermöglicht manuelles Herumspielen mit den Parametern."""
    print("\n🎮 Interaktiver Modus – 'q' zum Beenden.")
    tk = erzeuge_testkarte(32) # Größere Karte für mehr Spaß
    l_dir = vec3_norm((-0.5, -0.3, -1.0))
    mid_x, mid_y = tk.b * 0.5, tk.h * 0.5
    ground_h = tk.get_bilinear(mid_y, mid_x) * 2.0
    start = (mid_x, mid_y, ground_h + 0.5)
    
    # Defaults
    params = {
        'schritte': 64,
        'pcf_samples': 9,
        'pcf_radius': 0.8,
        'light_radius': 0.5,
        'light_samples': 16,
        'z_skalierung': 2.0,
    }
    
    while True:
        try:
            print(f"\nAktuell: {params}")
            print("Was ändern? (schritte, pcf_samples, pcf_radius, light_radius, light_samples, z_skalierung, enter=rechnen, q=quit)")
            cmd = input("> ").strip().lower()
            if cmd in ('q', 'quit', 'exit'):
                break
            if cmd == '':
                pass # Nur neu berechnen
            elif cmd in params:
                val = input(f"Neuer Wert für {cmd} (aktuell {params[cmd]}): ").strip()
                if val:
                    try:
                        # Typ beibehalten
                        if isinstance(params[cmd], int):
                            params[cmd] = int(float(val))
                        else:
                            params[cmd] = float(val)
                    except ValueError:
                        print("❌ Ungültige Zahl.")
            else:
                print("❓ Unbekannter Parameter.")
                continue
            
            # Berechnung
            shadow = raymarch_schatten(tk, start, l_dir, max_dist=30.0,
                                       z_skalierung=params['z_skalierung'],
                                       schritte=params['schritte'],
                                       pcf_samples=params['pcf_samples'],
                                       pcf_radius=params['pcf_radius'],
                                       light_radius=params['light_radius'],
                                       light_samples=params['light_samples'])
            print(f"🌑 Schattenfaktor: {shadow:.4f} ({'Schatten' if shadow < 0.5 else 'Licht'})")
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Tschüss!")
            break
        except Exception as e:
            print(f"💥 Fehler: {e}")

# ─── Hauptprogramm ───────────────────────────────────────────────────

def main() -> None:
    print("╔══════════════════════════════════════╗")
    print("║ Schatten-Simulator – Teil 63        ║")
    print("║ Raymarching: PCF & Area Light Done  ║")
    print("╚══════════════════════════════════════╝")
    
    while True:
        try:
            print("\nMenü:")
            print("  1 – Demo laufen lassen")
            print("  2 – Interaktiv parameterspieln")
            print("  3 – Beenden")
            choice = input("Wahl (1/2/3): ").strip()
            
            if choice == '1':
                demo_schatten()
            elif choice == '2':
                interaktiv()
            elif choice in ('3', 'q', 'quit'):
                print("🦤 Fifo watschelt weg. Bis bald!")
                break
            else:
                print("❓ Bitte 1, 2 oder 3 eingeben.")
        except (EOFError, KeyboardInterrupt):
            print("\n👋 EOF/Interrupt erkannt. Fifo klappt den Laptop zu.")
            break
        except Exception as e:
            print(f"💥 Unerwarteter Fehler im Hauptmenü: {e}")

if __name__ == "__main__":
    main()