# Notizen zu Schatten-Simulator

## Teil 1 (20.11.2026 20:23)
Leere main.py durch ersten lauffähigen Prototyp ersetzt: 4×4-Beispielhöhengrid, Konsolenausgabe, eine optionale Benutzereingabe für ein einzelnes Grid-Feld, einfache Min/Max/Spannen-Berechnung und freundliche Dodo-Kommentare.

```
🦤 Fifo meldet Dienst: Schatten-Simulator startet …

Aktuelle Tiefenkarte (Höhenwerte):
  0.1  0.2  0.3  0.2
  0.2  0.5  0.6  0.3
  0.3  0.7  0.9  0.4
  0.2  0.4  0.5  0.3

Neue Höhe für [2][2] (0.0-1.0) oder Enter für Behalten:   → Wert außerhalb, bleibt unverändert.

Tiefenbereich: min=0.10, max=0.90, spanne=0.80

🦤 Fifo pickt sich den nächsten Wurm – Teil 1 erledigt.
```

## Teil 2 (20.11.2026 20:33)
Refactoring in eine Tiefenkarte-Klasse, Hinzufügen von Normalenberechnung (zentrale Differenzen) und erstem Lambert-Schattenwurf mit einer definierten Lichtquelle. Interaktion und Statistik bleiben erhalten, Ausgabe formatiert.

```
🦤 Fifo meldet Dienst: Schatten-Simulator Teil 2 – Normalen & Licht

Aktuelle Tiefenkarte (Höhenwerte 0.00–1.00):
  0.10  0.20  0.30  0.20
  0.20  0.50  0.60  0.30
  0.30  0.70  0.90  0.40
  0.20  0.40  0.50  0.30

Tiefenbereich: min=0.10, max=0.90, spanne=0.80

Neue Höhe für [2][2] (0.0-1.0) oder Enter für Behalten:   → Wert außerhalb oder Index ungültig, bleibt unverändert.

Normalenvektoren (x, y, z) an den vier Ecken:
  [0][0]: (-0.099, -0.099, +0.990)
  [0][3]: (+0.147, -0.147, +0.978)
  [3][0]: (-0.194, +0.146, +0.970)
  [3][3]: (+0.238, +0.190, +0.952)

Diffuse Helligkeit (0.0–1.0) an den vier Ecken:
  [0][0]: 0.000
  [0][3]: 0.000
  [3][0]: 0.000
  [3][3]: 0.000

🦤 Fifo pickt sich den nächsten Wurm – Teil 2 erledigt.
```

## Teil 3 (20.11.2026 20:43)
Lichtvektor korrigiert (zeigt jetzt +Z für Oberflächen-Normalen). Bilineare Interpolation und Raymarching-Funktion für harten Schattenwurf (Occlusion) hinzugefügt. Hauptschleife gibt nun Lambert, Schatten und Kombination aus.

```
🦤 Fifo meldet Dienst: Schatten-Simulator Teil 3 – Raymarching & Reparatur

Aktuelle Tiefenkarte (Höhenwerte 0.00–1.00):
  0.10  0.20  0.30  0.20
  0.20  0.50  0.60  0.30
  0.30  0.70  0.90  0.40
  0.20  0.40  0.50  0.30

Tiefenbereich: min=0.10, max=0.90, spanne=0.80

Neue Höhe für [2][2] (0.0-1.0) oder Enter für Behalten:   → Wert außerhalb oder Index ungültig, bleibt unverändert.

Normalenvektoren (x, y, z) an den vier Ecken:
  [0][0]: (-0.099, -0.099, +0.990)
  [0][3]: (+0.147, -0.147, +0.978)
  [3][0]: (-0.194, +0.146, +0.970)
  [3][3]: (+0.238, +0.190, +0.952)

Lichtrichtung (normiert): (-0.408, -0.408, +0.816)

Diffuse Helligkeit (Lambert, 0.0–1.0) an den Ecken:
  [0][0]: 0.889
  [0][3]: 0.799
  [3][0]: 0.812
  [3][3]: 0.603

🦤 Fifo marschiert Strahlen... (Raymarching für harte Schatten)
Schattenfaktor (1.0=Licht, 0.0=Schatten) an den Ecken:
  [0][0]: 1.000
  [0][3]: 1.000
  [3][0]: 1.000
  [3][3]: 1.000

Kombiniert (Diffuse * Schatten) an den Ecken:
  [0][0]: 0.889
  [0][3]: 0.799
  [3][0]: 0.812
  [3][3]: 0.603

🦤 Fifo pickt sich den nächsten Wurm – Teil 3 erledigt. Grundgerüst steht.
```

## Teil 4 (20.11.2026 21:01)
Raymarching-Schleife optimiert: Lokale Variablen, Inline-Bilinear-Interpolation ohne Clamping-Overhead, Reziproke vorgezogen. Hauptprogramm vervollständigt mit Interaktionsschleife, Heatmap-Ausgabe und Kombinationsfunktion.

```
🦤 Fifo meldet Dienst: Schatten-Simulator Teil 4 – Raymarching optimiert
Aktuelle Tiefenkarte (Höhenwerte 0.00–1.00):
  0.10  0.20  0.30  0.20
  0.20  0.50  0.60  0.30
  0.30  0.70  0.90  0.40
  0.20  0.40  0.50  0.30
Tiefenbereich: min=0.10, max=0.90, spanne=0.80
Lichtrichtung (normiert): (-0.432, -0.259, 0.864)

Lambert (Diffuse):
  % % % # 
  % % # * 
  % % * + 
  # # + * 

Occlusion (Harter Schatten):
  @ @ @ @ 
  @ @ @ @ 
  @ @ @ @ 
  @ @ @ @ 

Final (Kombiniert + Ambient):
  % % % # 
  % % # * 
  % % # * 
  % # * * 

🦤 Tipp neue Höhenwerte ein (y x wert), 'q' zum Beenden.
   Beispiel: 2 2 0.5  (setzt Zentrum auf 0.5)
🦤 > 🦤 Drei Werte erwartet: y x wert
🦤 > 🦤 Drei Werte erwartet: y x wert
🦤 > 🦤 Drei Werte erwartet: y x wert
🦤 > 🦤 Drei Werte erwartet: y x wert
🦤 > 🦤 Drei Werte erwartet: y x wert
🦤 > 🦤 Drei Werte erwartet: y x wert
🦤 > 🦤 Drei Werte erwartet: y x wert
🦤 > 🦤 Drei Werte erwartet: y x wert
🦤 > 🦤 Drei Werte erwartet: y x wert
🦤 > 🦤 Drei Werte erwartet: y x wert
🦤 > 🦤 Drei Werte erwartet: y x wert
🦤 > 🦤 Drei Werte erwartet: y x wert
🦤 > 🦤 Drei Werte erwartet: y x wert
🦤 > 🦤 Drei Werte erwartet: y x wert
🦤 > 🦤 Drei Werte erwartet: y x wert
🦤 > 🦤 Drei Werte erwartet: y x wert
🦤 > 🦤 Fifo watschelt davon. Tschüss!
```

## Teil 5 (20.11.2026 21:30)
Die abgebrochene Raymarching-Funktion wurde vervollständigt (h11, Interpolation, Shadow-Check). Hauptprogramm um 'Regenpause'-Flavor erweitert: Startmeldung, einmalige Interaktion mit EOF-Behandlung, dann Dodo-Schlaf. Keine neuen Features, nur Abschluss und Atmosphäre.

```
🦤 Fifo meldet Dienst: Schatten-Simulator Teil 5 – Regenpause
Draußen tropft's. Drinnen flackert der Monitor. Code ist fertig.

Aktuelle Tiefenkarte (Höhenwerte 0.00–1.00):
  0.10  0.20  0.30  0.20  0.10
  0.20  0.50  0.60  0.40  0.20
  0.30  0.70  0.90  0.50  0.30
  0.20  0.40  0.50  0.30  0.20
  0.10  0.20  0.30  0.20  0.10
Tiefenbereich: min=0.10, max=0.90, spanne=0.80
Lichtrichtung (normiert): (-0.500, 0.500, 0.707)

--- Diffuses Licht (Lambert) ---
*+==+
*+===
##*++
###**
###**

Raymarching... (32 Schritte)

--- Harte Schatten (Raymarch) ---
@@@@@
@@@@@
@@@@@
@@@@@
@@@@@

--- Kombiniert (Final) ---
*+==+
*+===
##*++
###**
###**

💤 Fifo legt den Kopf auf die Tastatur. zzz...
   (Drück Enter zum Beenden oder 'n' für neues Licht, aber Fifo schläft schon.)
> Ruhe jetzt. Gute Nacht.
```
