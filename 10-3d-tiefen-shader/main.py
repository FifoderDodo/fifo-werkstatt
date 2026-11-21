import math
import sys


def szene_distanz(x: float, y: float, z: float) -> float:
    """SDF-Szene: Kugel bei (0, 0, 3) Radius 1, Boden bei y = -1."""
    # Kugel-Distanz
    kugel = math.sqrt(x * x + y * y + (z - 3.0) * (z - 3.0)) - 1.0
    # Bodenplane y = -1
    boden = y + 1.0
    return min(kugel, boden)


def szene_normal(x: float, y: float, z: float, eps: float = 1e-4) -> tuple:
    """Gradient des SDF als Normalenvektor (nicht normalisiert)."""
    d = szene_distanz(x, y, z)
    nx = szene_distanz(x + eps, y, z) - d
    ny = szene_distanz(x, y + eps, z) - d
    nz = szene_distanz(x, y, z + eps) - d
    leng = math.sqrt(nx * nx + ny * ny + nz * nz)
    if leng == 0:
        return 0.0, 1.0, 0.0
    return nx / leng, ny / leng, nz / leng


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
    print("Fifo's 3D-Tiefen-Shader - Teil 2: Tiefe & Schattierung")
    print("======================================================")
    
    # Bildgröße (klein für ASCII)
    breite = 60
    hoehe = 30
    
    # Kamera & Projektion
    brennweite = 1.0
    # Kamera etwas erhöht, damit sie den Boden und die Kugel sieht
    cam_x, cam_y, cam_z = 0.0, 1.5, 0.0
    
    print(f"Rendere {breite}x{hoehe} Pixel mit Raymarching...")
    
    # Input-Spaß: Skalierung der Szene beeinflussen
    skala = 1.0
    try:
        inp = input("Skalierungsfaktor für Szene (Enter=1.0, z.B. 0.5 oder 2.0): ").strip()
        if inp:
            skala = float(inp)
            print(f"Ok, Skalierung = {skala}")
    except (ValueError, EOFError):
        print("Keine gültige Zahl oder EOF, nehme Standard 1.0.")
    
    # Lichtrichtung (von oben rechts leicht von vorn)
    lx, ly, lz = 1.0, 2.0, -1.0
    lleng = math.sqrt(lx*lx + ly*ly + lz*lz)
    lx, ly, lz = lx/lleng, ly/lleng, lz/lleng
    
    # Framebuffer für Tiefe und Schattierung
    tiefe_buffer = []
    schatten_buffer = []
    
    for j in range(hoehe):
        zeile_tiefen = []
        zeile_schatten = []
        # NDC y: +1 (oben) nach -1 (unten)
        ndc_y = (1.0 - 2.0 * j / (hoehe - 1)) / skala
        for i in range(breite):
            # NDC x: -1 (links) nach +1 (rechts)
            ndc_x = (2.0 * i / (breite - 1) - 1.0) / skala
            
            # Strahlrichtung berechnen (Projektion)
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
            
            # Schattierung nur bei Treffer
            if t < 20.0:
                # Trefferpunkt
                hx = cam_x + rdx * t
                hy = cam_y + rdy * t
                hz = cam_z + rdz * t
                # Normalen
                nx, ny, nz = szene_normal(hx, hy, hz)
                # Diffuses Licht (Lambert)
                diff = max(0.0, nx*lx + ny*ly + nz*lz)
                # Ambient + Diffus, leicht tiefenabhängig (Nebel)
                ambient = 0.2
                nebelfaktor = 1.0 - min(1.0, t / 20.0)
                helligkeit = ambient + diff * nebelfaktor
                zeile_schatten.append(helligkeit)
            else:
                zeile_schatten.append(0.0)  # Hintergrund = dunkel
        tiefe_buffer.append(zeile_tiefen)
        schatten_buffer.append(zeile_schatten)
    
    # ASCII Ausgabe: Kombination aus Tiefe und Schattierung
    # Helle Zeichen für hohe Helligkeit
    ascii_rampe = " .:'-=+*#%@"
    max_tiefe = 15.0
    
    print("\nSchattierte Tiefenkarte (Nah & beleuchtet = hell):")
    for j in range(hoehe):
        out = ""
        for i in range(breite):
            t = tiefe_buffer[j][i]
            s = schatten_buffer[j][i]
            # Helligkeit aus Schattierung (0..1) und Tiefe (Nah = heller)
            # Wir mischen: 70% Schattierung, 30% Tiefen-Nähe
            tiefe_faktor = 1.0 - min(1.0, t / max_tiefe)
            wert = 0.7 * s + 0.3 * tiefe_faktor
            idx = int(min(len(ascii_rampe) - 1, max(0, wert * (len(ascii_rampe) - 1))))
            out += ascii_rampe[idx]
        print(out)
    
    print("\nFertig. Teil 2 erledigt: Normals, Lambert-Shading und Nebel hinzugefügt.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbbruch durch User. Tschüss!")
    except Exception as e:
        print(f"\nUps, Fehler: {e}")
        sys.exit(1)