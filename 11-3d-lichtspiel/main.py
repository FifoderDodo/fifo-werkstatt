# 3D-Lichtspiel – Teil 1: Erste Lichtkegel im Herbstpark
# Fifo der Dodo hackt sich durch den Nebel

import math
import sys
import random


def weicher_gradient(entfernung: float, radius: float) -> str:
    """Gibt ein ASCII-Zeichen zurück, das die Helligkeit nach Entfernung simuliert."""
    if entfernung >= radius:
        return ' '
    # Normierte Distanz 0.0 (Zentrum) bis 1.0 (Rand)
    norm = entfernung / radius
    # Weicher Abfall: cosinus-förmig für sanfte Kanten
    intensitaet = math.cos(norm * math.pi / 2)
    # Stufen für ASCII-Art
    if intensitaet > 0.85:
        return '@'  # hellster Kern
    elif intensitaet > 0.65:
        return '#'
    elif intensitaet > 0.45:
        return '*'
    elif intensitaet > 0.25:
        return '+'
    elif intensitaet > 0.1:
        return '.'
    else:
        return ' '


def zeichne_lichtkegel(breite: int, hoehe: int, quellen: list) -> list:
    """Erzeugt ein 2D-Gitter mit überlagerten Lichtkegeln."""
    # Start mit dunklem Herbsthintergrund
    bild = [[' ' for _ in range(breite)] for __ in range(hoehe)]
    
    # Herstlaub am Boden (ein paar zufällige Punkte)
    for _ in range(breite * hoehe // 40):
        x = random.randint(0, breite - 1)
        y = random.randint(hoehe // 2, hoehe - 1)
        bild[y][x] = random.choice(['.', ',', '`'])
    
    for qx, qy, radius, richtung_x, richtung_y in quellen:
        # Lichtkegel als elliptischer Sektor zeichnen
        for y in range(hoehe):
            for x in range(breite):
                dx = x - qx
                dy = y - qy
                dist = math.hypot(dx, dy)
                if dist > radius:
                    continue
                # Prüfen ob im Kegel (Richtung + Öffnungswinkel)
                if dist > 0.1:
                    punkt_rx = dx / dist
                    punkt_ry = dy / dist
                    # Skalarprodukt für Winkel
                    cos_winkel = punkt_rx * richtung_x + punkt_ry * richtung_y
                    if cos_winkel < 0.5:  # ~60° Öffnungswinkel
                        continue
                # Weicher Gradient anwenden
                zeichen = weicher_gradient(dist, radius)
                if zeichen != ' ':
                    # Helligstes Zeichen gewinnt (einfache Überblendung)
                    aktuell = bild[y][x]
                    if aktuell == ' ' or zeichen in '@#*+.' and aktuell in ' .,+*#@':
                        # Nur überschreiben wenn neuer heller
                        hellerkeits_ordnung = ' .,`+*#@'
                        if hellerkeits_ordnung.index(zeichen) > hellerkeits_ordnung.index(aktuell):
                            bild[y][x] = zeichen
    return bild


def main():
    print("🍂 3D-Lichtspiel – Herbstpark-Simulator 🍂")
    print("Fifo der Dodo wackelt zur Tastatur...\n")
    
    try:
        # Ein paar kleine Eingaben für Interaktivität
        breite = int(input("Parkbreite (Spalten, 40-120) [80]: ") or "80")
        breite = max(40, min(120, breite))
        
        hoehe = int(input("Parkhöhe (Zeilen, 20-60) [30]: ") or "30")
        hoehe = max(20, min(60, hoehe))
        
        anzahl_quellen = int(input("Anzahl Lichtquellen (1-5) [3]: ") or "3")
        anzahl_quellen = max(1, min(5, anzahl_quellen))
        
        tageszeit = input("Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]: ") or "dämmerung"
        
        print(f"\nFifo malt {anzahl_quellen} Lichtkegel in den {breite}x{hoehe} Park...\n")
        
        # Lichtquellen erzeugen: (x, y, radius, dir_x, dir_y)
        quellen = []
        random.seed(42)  # Reproduzierbar für Fifo
        for i in range(anzahl_quellen):
            # Verteilen über die obere Hälfte (Laternen, Mond, Fenster)
            qx = random.randint(breite // 4, 3 * breite // 4)
            qy = random.randint(2, hoehe // 3)
            radius = random.randint(min(breite, hoehe) // 3, min(breite, hoehe) // 2)
            # Meist nach unten gerichtet
            richtung_x = random.uniform(-0.3, 0.3)
            richtung_y = random.uniform(0.7, 1.0)
            # Normalisieren
            rlen = math.hypot(richtung_x, richtung_y)
            richtung_x /= rlen
            richtung_y /= rlen
            quellen.append((qx, qy, radius, richtung_x, richtung_y))
            print(f"  Laterne {i+1}: Position ({qx},{qy}), Radius {radius}, Richtung ({richtung_x:.2f},{richtung_y:.2f})")
        
        # Bild rendern
        bild = zeichne_lichtkegel(breite, hoehe, quellen)
        
        print("\n" + "=" * breite)
        for zeile in bild:
            print(''.join(zeile))
        print("=" * breite)
        
        # Kleine Statistik
        hell_pixels = sum(1 for row in bild for c in row if c in '@#*+')
        print(f"\nFifo zählt {hell_pixels} beleuchtete Pixel – der Nebel leuchtet sanft.")
        print("Teil 1 fertig. Nächster Schritt: volumetrische Schattenwürfe... 🦤")
        
    except EOFError:
        print("\nFifo wird müde. Gute Nacht im Herbstpark. 🍂")
    except ValueError:
        print("\nFifo versteht nur Zahlen. Probier's nochmal. 🦤")
    except KeyboardInterrupt:
        print("\nFifo flattert weg. Tschüss! 🍂")


if __name__ == "__main__":
    main()