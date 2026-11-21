import math
import sys


def szene_distanz(x: float, y: float, z: float) -> float:
    """Einfache SDF-Szene: eine Kugel bei (0, 0, 3) mit Radius 1."""
    # Kugel-Distanz
    kugel = math.sqrt(x * x + y * y + (z - 3.0) * (z - 3.0)) - 1.0
    # Bodenplane bei z = 0
    boden = z
    return min(kugel, boden)


def raymarch(ox: float, oy: float, oz: float,
             dx: float, dy: float, dz: float,
             max_schritte: int = 64, max_dist: float = 20.0) -> float:
    """Marchiert entlang des Strahls und gibt die getroffene Tiefe zurück."""
    tiefe = 0.0
    for _ in range(max_schritte):
        px = ox + dx * tiefe
        py = oy + dy * tiefe
        pz = oz + dz * tiefe
        dist = szene_distanz(px, py, pz)
        if dist < 0.01:  # Gehtroffen
            return tiefe
        tiefe += dist
        if tiefe > max_dist:
            break
    return max_dist  # Hintergrund


def main() -> None:
    print("Fifo's 3D-Tiefen-Shader - Teil 1: Koordinaten & Projektion")
    print("==========================================================")
    
    # Bildgröße (klein für ASCII)
    breite = 60
    hoehe = 30
    
    # Kamera & Projektion
    # Skalierung der Koordinaten: NDC (-1..1) -> Welt
    # Hier justiere ich die Zeilen für die Tiefenprojektion:
    # Brennweite / Field of View Einfluss
    brennweite = 1.0
    
    # Kamera steht bei (0, 0, 0), schaut in +Z
    cam_x, cam_y, cam_z = 0.0, 0.0, 0.0
    
    print(f"Rendere {breite}x{hoehe} Pixel mit Raymarching...")
    
    # Ein kleiner Input-Spaß: Skalierung der Szene beeinflussen
    skala = 1.0
    try:
        inp = input("Skalierungsfaktor für Szene (Enter=1.0, z.B. 0.5 oder 2.0): ").strip()
        if inp:
            skala = float(inp)
            print(f"Ok, Skalierung = {skala}")
    except (ValueError, EOFError):
        print("Keine gültige Zahl oder EOF, nehme Standard 1.0.")
    
    # Framebuffer für Tiefe
    tiefe_buffer = []
    
    for j in range(hoehe):
        zeile_tiefen = []
        # NDC y: +1 (oben) nach -1 (unten)
        ndc_y = (1.0 - 2.0 * j / (hoehe - 1)) / skala
        for i in range(breite):
            # NDC x: -1 (links) nach +1 (rechts)
            ndc_x = (2.0 * i / (breite - 1) - 1.0) / skala
            
            # Strahlrichtung berechnen (Projektion)
            # Koordinaten skaliert via NDC * Brennweite
            rdx = ndc_x * brennweite
            rdy = ndc_y * brennweite
            rdz = 1.0  # Schaut in +Z
            
            # Normalisieren
            leng = math.sqrt(rdx * rdx + rdy * rdy + rdz * rdz)
            rdx /= leng
            rdy /= leng
            rdz /= leng
            
            # Raymarch
            t = raymarch(cam_x, cam_y, cam_z, rdx, rdy, rdz)
            zeile_tiefen.append(t)
        tiefe_buffer.append(zeile_tiefen)
    
    # ASCII Ausgabe: Tiefe -> Zeichen
    # Nahe = hell (#), Fern = dunkel (.)
    ascii_rampe = " .:-=+*#%@"
    max_tiefe = 15.0
    
    print("\nTiefenkarte (Nah=hell, Fern=dunkel):")
    for zeile in tiefe_buffer:
        out = ""
        for t in zeile:
            idx = int(min(len(ascii_rampe) - 1, max(0, (t / max_tiefe) * (len(ascii_rampe) - 1))))
            # Umkehren: nah = Index 0 (dunkel in Rampe oben?), lieber: nah = helles Zeichen
            # Rampe ist dunkel -> hell. Nah = kleines t = kleiner Index = dunkler. 
            # Besser: Umkehren.
            idx = len(ascii_rampe) - 1 - idx
            out += ascii_rampe[idx]
        print(out)
    
    print("\nFertig. Teil 1 erledigt: Projektion & Skalierung laufen.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbbruch durch User. Tschüss!")
    except Exception as e:
        print(f"\nUps, Fehler: {e}")
        sys.exit(1)