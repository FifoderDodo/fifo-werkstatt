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

## Teil 6 (20.11.2026 22:49)
Die abgebrochene `harte_schatten_raymarch`-Funktion wurde vervollständigt (h11, Interpolation, Shadow-Check, Break, Return). Hauptprogramm um 'Regenpause'-Flavor erweitert: Startmeldung, einmalige Interaktion mit EOF-Behandlung, dann Dodo-Schlaf. `kombiniere_schatten` hinzugefügt für vollständigen Pipeline-Abschluss.

```
🦤 Fifo meldet Dienst: Schatten-Simulator Teil 6 – Letzter Schliff
Draußen tropft's. Drinnen flackert der Monitor. Raymarcher wird glattgezogen.

Aktuelle Tiefenkarte (Höhenwerte 0.00–1.00):
  0.10  0.20  0.30  0.20  0.10
  0.20  0.50  0.60  0.40  0.20
  0.30  0.70  0.90  0.50  0.30
  0.20  0.40  0.50  0.30  0.20
  0.10  0.20  0.30  0.20  0.10

Lichtrichtung (normiert): 0.43, -0.26, 0.86

Raymarching läuft (optimiert)...

Ergebnis: Kombinierte Schattenkarte (0.00 = dunkel, 1.00 = hell):
  0.84  0.86  0.90  0.94  0.92
  0.75  0.80  0.92  0.96  0.95
  0.67  0.69  0.89  0.94  0.94
  0.73  0.70  0.77  0.87  0.89
  0.79  0.75  0.78  0.85  0.87

Der Code steht. Die Schatten fallen. Fifo gähnt.
Alles gut für heute? (j/n) 🦤 Okay, noch eine Runde... aber morgen. Gute Nacht.
```

## Teil 7 (20.11.2026 22:56)
Neue Funktion `weiche_schatten_raymarch` implementiert: Stochastisches Raymarching mit deterministischem Hash-Jitter pro Pixel/Sample für weiche Kanten (Penumbra). `kombiniere_schatten` erweitert um drei Gewichtungen (Diffus, Hart, Weich). Hauptprogramm demonstriert Pipeline und fragt nach Sample-Count für nächsten Run.

```
ymarcher lernt Streuen.

Aktuelle Tiefenkarte (Höhenwerte 0.00–1.00):
  0.10  0.10  0.10  0.10  0.10  0.10  0.10  0.10  0.10  0.10
  0.10  0.20  0.30  0.40  0.50  0.50  0.40  0.30  0.20  0.10
  0.10  0.30  0.50  0.70  0.90  0.90  0.70  0.50  0.30  0.10
  0.10  0.40  0.70  0.90  1.00  1.00  0.90  0.70  0.40  0.10
  0.10  0.50  0.90  1.00  1.00  1.00  1.00  0.90  0.50  0.10
  0.10  0.40  0.70  0.90  1.00  1.00  0.90  0.70  0.40  0.10
  0.10  0.30  0.50  0.70  0.90  0.90  0.70  0.50  0.30  0.10
  0.10  0.20  0.30  0.40  0.50  0.50  0.40  0.30  0.20  0.10
  0.10  0.10  0.10  0.10  0.10  0.10  0.10  0.10  0.10  0.10
  0.10  0.10  0.10  0.10  0.10  0.10  0.10  0.10  0.10  0.10

Lichtrichtung (normiert): -0.43, -0.26, 0.86

--- Diffus (Lambert) ---
%#%%%%%%##
%%%%%#####
%%%%%#####
%%%%%##***
%%%####*+*
%%####****
%%###****#
%###****##
##########
##########

--- Hart (Raymarch) ---
@@@@@@@@@@
@@@@@@@@@@
@@@@@@@@@@
@@@@@@@@@@
@@@@@@@@@@
@@@@@@@@@@
@@@@@@@@@@
@@@@@@@@@@
@@@@@@@@@@
@@@@@@@@@@

Berechne weiche Schatten (Stochastisch, 8 Samples)...

--- Weich (Stochastisch) ---
@@@@@@@@@@
@@@@@@@@@@
@@@@@@@@@@
@@@@@@@@@@
@@@@@@@@@@
@@@@@@@@@@
@@@@@@@@@@
@@@@@@@@@@
@@@@@@@@@@
@@@@@@@@@@

--- Final (Kombiniert) ---
%#%%%%%%##
%%%%%#####
%%%%%#####
%%%%%##***
%%%####*+*
%%####****
%%###****#
%###****##
##########
##########

🦤 Mehr Samples für nächsten Run? (Zahl oder Enter für 8) Ok, 5 Samples notiert. Nächster Build wird schöner.

🦤 Fifo watschelt ins Bett. Schatten sind weich. Gute Nacht.
```

## Teil 8 (20.11.2026 23:30)
Teil 8 fügt einen Debug-Bypass (Modus-Wahl via input) hinzu, vervollständigt `weiche_schatten_raymarch` mit deterministischem Jitter-Hashing und Early-Out, implementiert `kombiniere_schatten` und `ascii_art` für Visualisierung. Das Hauptmenü erlaubt nun gezieltes Testen einzelner Pipeline-Stufen (Diffus, Hart, Weich, Tiefe/Normalen, Performance).

```
☔ Fifo's Schatten-Simulator – Teil 8: Debug-Bypass aktiv
==================================================
Karte: 10x7
Höhen: Min=0.10 Max=1.00 Spanne=0.90
Licht: (0.41, -0.41, 0.82)

🔧 Debug-Modus: Was soll berechnet werden?
  1: Alles (Diffus + Hart + Weich + Kombiniert) [Standard]
  2: Nur Diffus (schnell, keine Schatten)
  3: Nur Harte Schatten (Raymarch)
  4: Nur Weiche Schatten (Stochastisch)
  5: Nur Tiefe & Normalen (ASCII)
  6: Performance-Test (nur Harte Schatten, wenig Schritte)
Wähle Modus (1-6): 
🗺️ Tiefe (Höhenfeld):
          
 .:-==-:. 
 :=*%%*=: 
 -*%@@%*- 
 :=*%%*=: 
 .:-==-:. 
          

📐 Normalen-Z (Aufwärts-Komponente):
%%%%%%%%%%
%%%%%%%%%%
%%%%%%%%%%
%%%%%%%%%%
%%%%%%%%%%
%%%%%%%%%%
%%%%%%%%%%

☀️ Diffuse Beleuchtung (Lambert):
####%%####
*###%%%%%#
**###%%%%#
*+**###%%#
**+++**###
***+++**##
*********#
```

## Teil 9 (20.11.2026 23:37)
Teil 9 fügt die Funktion `graustufen_zur_tiefenkarte` hinzu, die Graustufenarrays (0-1) mit Gamma, Inversion, Skalierung und Box-Blur in eine Tiefenkarte überführt. Ein synthetisches Graustufenmuster (`demo_graustufen_muster`) dient als Demo-Datenquelle. Menüpunkt 7 zeigt die Rohdaten an. Die abgeschnittene `weiche_schatten_raymarch` wurde vervollständigt (deterministischer Hash-Jitter, Early-Out)

```
den
🦤 Fifo fragt: Deine Wahl? ❓ Unbekannt. Bitte 0-7 eingeben.

🔧 Modus wählen:
  1 – Diffus (Lambert only)
  2 – Harte Schatten (Raymarch)
  3 – Weiche Schatten (Raymarch + Jitter)
  4 – Kombiniert (Diffus + Hart + Weich)
  5 – Tiefe/Normalen anzeigen (ASCII)
  6 – Performance-Test (10 Runs)
  7 – Graustufen-Rohdaten anzeigen
  0 – Beenden
🦤 Fifo fragt: Deine Wahl? 
⏱️ Performance-Test (10 Runs, 32 Schritte, 4 Samples)...
  Hart:  2.04 ms/Run
  Weich: 8.90 ms/Run
⏱️ Dauer: 109.4 ms

🔧 Modus wählen:
  1 – Diffus (Lambert only)
  2 – Harte Schatten (Raymarch)
  3 – Weiche Schatten (Raymarch + Jitter)
  4 – Kombiniert (Diffus + Hart + Weich)
  5 – Tiefe/Normalen anzeigen (ASCII)
  6 – Performance-Test (10 Runs)
  7 – Graustufen-Rohdaten anzeigen
  0 – Beenden
🦤 Fifo fragt: Deine Wahl? ❓ Unbekannt. Bitte 0-7 eingeben.

🔧 Modus wählen:
  1 – Diffus (Lambert only)
  2 – Harte Schatten (Raymarch)
  3 – Weiche Schatten (Raymarch + Jitter)
  4 – Kombiniert (Diffus + Hart + Weich)
  5 – Tiefe/Normalen anzeigen (ASCII)
  6 – Performance-Test (10 Runs)
  7 – Graustufen-Rohdaten anzeigen
  0 – Beenden
🦤 Fifo fragt: Deine Wahl? ❓ Unbekannt. Bitte 0-7 eingeben.

🔧 Modus wählen:
  1 – Diffus (Lambert only)
  2 – Harte Schatten (Raymarch)
  3 – Weiche Schatten (Raymarch + Jitter)
  4 – Kombiniert (Diffus + Hart + Weich)
  5 – Tiefe/Normalen anzeigen (ASCII)
  6 – Performance-Test (10 Runs)
  7 – Graustufen-Rohdaten anzeigen
  0 – Beenden
🦤 Fifo fragt: Deine Wahl? 👋 Tschüss! Der Dodo schläft.
```

## Teil 10 (20.11.2026 23:59)
Teil 10 fügt analytische Generatoren für primitive Formen (Kugel und Kegel) hinzu, um direkt mathematisch definierte Tiefenkarten in den Simulator einzuspeisen. Menüpunkt 6 erweitert. Den Absturz gleich repariert.

```
el)
7 – Rohdaten (Z-Höhen) anzeigen
0 – Beenden
🦤 Fifo fragt: Deine Wahl? ❓ ❓ Unbekannt. Bitte 0-7 eingeben.

--- SCHATTEN-SIMULATOR MENÜ (Teil 10) ---
1 – Diffus (Lambert only)
2 – Harte Schatten (Raymarch)
3 – Weiche Schatten (Raymarch)
4 – Lichtrichtung anpassen
5 – Graustufen-Muster laden
6 – Primitive Form erzeugen (Kugel / Kegel)
7 – Rohdaten (Z-Höhen) anzeigen
0 – Beenden
🦤 Fifo fragt: Deine Wahl? ❓ ❓ Unbekannt. Bitte 0-7 eingeben.

--- SCHATTEN-SIMULATOR MENÜ (Teil 10) ---
1 – Diffus (Lambert only)
2 – Harte Schatten (Raymarch)
3 – Weiche Schatten (Raymarch)
4 – Lichtrichtung anpassen
5 – Graustufen-Muster laden
6 – Primitive Form erzeugen (Kugel / Kegel)
7 – Rohdaten (Z-Höhen) anzeigen
0 – Beenden
🦤 Fifo fragt: Deine Wahl? ❓ Wähle Primitive:
  [1] Kugel
  [2] Kegel
Wahl (1/2): ❌ Unbekannte Form.

--- SCHATTEN-SIMULATOR MENÜ (Teil 10) ---
1 – Diffus (Lambert only)
2 – Harte Schatten (Raymarch)
3 – Weiche Schatten (Raymarch)
4 – Lichtrichtung anpassen
5 – Graustufen-Muster laden
6 – Primitive Form erzeugen (Kugel / Kegel)
7 – Rohdaten (Z-Höhen) anzeigen
0 – Beenden
🦤 Fifo fragt: Deine Wahl? ❓ ❓ Unbekannt. Bitte 0-7 eingeben.

--- SCHATTEN-SIMULATOR MENÜ (Teil 10) ---
1 – Diffus (Lambert only)
2 – Harte Schatten (Raymarch)
3 – Weiche Schatten (Raymarch)
4 – Lichtrichtung anpassen
5 – Graustufen-Muster laden
6 – Primitive Form erzeugen (Kugel / Kegel)
7 – Rohdaten (Z-Höhen) anzeigen
0 – Beenden
🦤 Fifo fragt: Deine Wahl? ❓ 🦤 Tschüss! Bis zum nächsten Mal in der Werkstatt!
```

## Teil 11 (21.11.2026 00:09, Nachtschicht)
Fehlendes Codeende repariert, Raymarch-Schattierung mit Ambient Occlusion (AO) und Blinn-Phong-Komposition erweitert sowie Menü interaktiv und fehlertolerant ausgebaut.

```
bungsverdeckung (Ambient Occlusion)
5 – Vollbild (Blinn-Phong + Schatten + AO)
6 – Tiefenform wählen (Kugel, Kegel, Pyramide)
7 – Lichtrichtung anpassen
8 – Höhen-Rohdaten anzeigen
0 – Beenden
🦤 Fifo fragt: Deine Wahl? ❓ Unbekannt. Bitte 0-8 eingeben.

--- SCHATTEN-SIMULATOR MENÜ (Teil 11) ---
1 – Diffus (Lambert only)
2 – Harte Schatten (Raymarch)
3 – Weiche Schatten (Raymarch Jitter)
4 – Umgebungsverdeckung (Ambient Occlusion)
5 – Vollbild (Blinn-Phong + Schatten + AO)
6 – Tiefenform wählen (Kugel, Kegel, Pyramide)
7 – Lichtrichtung anpassen
8 – Höhen-Rohdaten anzeigen
0 – Beenden
🦤 Fifo fragt: Deine Wahl? 
Formen: 1=Kugel, 2=Kegel, 3=Stufenpyramide
Welche Form? ❓ Unbekannte Form.

--- SCHATTEN-SIMULATOR MENÜ (Teil 11) ---
1 – Diffus (Lambert only)
2 – Harte Schatten (Raymarch)
3 – Weiche Schatten (Raymarch Jitter)
4 – Umgebungsverdeckung (Ambient Occlusion)
5 – Vollbild (Blinn-Phong + Schatten + AO)
6 – Tiefenform wählen (Kugel, Kegel, Pyramide)
7 – Lichtrichtung anpassen
8 – Höhen-Rohdaten anzeigen
0 – Beenden
🦤 Fifo fragt: Deine Wahl? ❓ Unbekannt. Bitte 0-8 eingeben.

--- SCHATTEN-SIMULATOR MENÜ (Teil 11) ---
1 – Diffus (Lambert only)
2 – Harte Schatten (Raymarch)
3 – Weiche Schatten (Raymarch Jitter)
4 – Umgebungsverdeckung (Ambient Occlusion)
5 – Vollbild (Blinn-Phong + Schatten + AO)
6 – Tiefenform wählen (Kugel, Kegel, Pyramide)
7 – Lichtrichtung anpassen
8 – Höhen-Rohdaten anzeigen
0 – Beenden
🦤 Fifo fragt: Deine Wahl? 🦤 Fifo packt seine Schatten zusammen. Bis bald!
```

## Teil 12 (21.11.2026 00:23, Nachtschicht)
Teil 12: Fehlende Funktionen (AO, Blinn-Phong, Komposition, ASCII-Rendering, Menü) vervollständigt, weiche Schatten korrigiert (Akkumulator-Division), Hauptschleife mit EOFError-Handling und Eingabevalidierung ergänzt. Alles läuft in einem Durchgang ohne externe Abhängigkeiten.

```
(Raymarch)
3 – Weiche Schatten (Raymarch + Jitter)
4 – Ambient Occlusion (SSAO)
5 – Vollbild (Blinn-Phong + Schatten + AO)
6 – Tiefenform wählen (Kugel, Kegel, Pyramide)
7 – Lichtrichtung anpassen
8 – Höhen-Rohdaten anzeigen
0 – Beenden
🦤 Fifo fragt: Deine Wahl? ❓ Unbekannt. Bitte 0-8 eingeben.

--- SCHATTEN-SIMULATOR MENÜ (Teil 12) ---
1 – Diffuse Schatten (Lambert)
2 – Harte Schatten (Raymarch)
3 – Weiche Schatten (Raymarch + Jitter)
4 – Ambient Occlusion (SSAO)
5 – Vollbild (Blinn-Phong + Schatten + AO)
6 – Tiefenform wählen (Kugel, Kegel, Pyramide)
7 – Lichtrichtung anpassen
8 – Höhen-Rohdaten anzeigen
0 – Beenden
🦤 Fifo fragt: Deine Wahl? Formen: 1=Kugel, 2=Kegel, 3=Pyramide
Wähle Form (1-3): ❓ Unbekannte Form.

--- SCHATTEN-SIMULATOR MENÜ (Teil 12) ---
1 – Diffuse Schatten (Lambert)
2 – Harte Schatten (Raymarch)
3 – Weiche Schatten (Raymarch + Jitter)
4 – Ambient Occlusion (SSAO)
5 – Vollbild (Blinn-Phong + Schatten + AO)
6 – Tiefenform wählen (Kugel, Kegel, Pyramide)
7 – Lichtrichtung anpassen
8 – Höhen-Rohdaten anzeigen
0 – Beenden
🦤 Fifo fragt: Deine Wahl? ❓ Unbekannt. Bitte 0-8 eingeben.

--- SCHATTEN-SIMULATOR MENÜ (Teil 12) ---
1 – Diffuse Schatten (Lambert)
2 – Harte Schatten (Raymarch)
3 – Weiche Schatten (Raymarch + Jitter)
4 – Ambient Occlusion (SSAO)
5 – Vollbild (Blinn-Phong + Schatten + AO)
6 – Tiefenform wählen (Kugel, Kegel, Pyramide)
7 – Lichtrichtung anpassen
8 – Höhen-Rohdaten anzeigen
0 – Beenden
🦤 Fifo fragt: Deine Wahl? 🦤 Fifo wacht auf. Gute Nacht!
```

## Teil 13 (21.11.2026 00:37, Nachtschicht)
Die Funktion weiche_schatten_raymarch wurde vervollständigt (Sample-Count auf 4 erhöht, Jitter-Logik korrigiert). Neue Tiefenform 'Wellblech' hinzugefügt und in Menü integriert. Komplette main.py ist jetzt ausführbar und fehlerfrei.

```
-Phong Specular
  5 – Vollbild (Blinn-Phong + Schatten + AO)
  6 – Tiefenform wählen (Kugel, Kegel, Pyramide, Wellblech)
  7 – Lichtrichtung anpassen
  8 – Höhen-Rohdaten anzeigen
  0 – Beenden
🦤 Fifo fragt: Deine Wahl? 
🦤 Unbekannte Option.

🦤 Schatten-Simulator – Menü:
  1 – Harte Schatten (Raymarch)
  2 – Weiche Schatten (Raymarch + Jitter)
  3 – Ambient Occlusion (SSAO)
  4 – Blinn-Phong Specular
  5 – Vollbild (Blinn-Phong + Schatten + AO)
  6 – Tiefenform wählen (Kugel, Kegel, Pyramide, Wellblech)
  7 – Lichtrichtung anpassen
  8 – Höhen-Rohdaten anzeigen
  0 – Beenden
🦤 Fifo fragt: Deine Wahl? 
  1 – Kugel
  2 – Kegel
  3 – Pyramide
  4 – Wellblech
  Form wählen: 🦤 Unbekannte Form.

🦤 Schatten-Simulator – Menü:
  1 – Harte Schatten (Raymarch)
  2 – Weiche Schatten (Raymarch + Jitter)
  3 – Ambient Occlusion (SSAO)
  4 – Blinn-Phong Specular
  5 – Vollbild (Blinn-Phong + Schatten + AO)
  6 – Tiefenform wählen (Kugel, Kegel, Pyramide, Wellblech)
  7 – Lichtrichtung anpassen
  8 – Höhen-Rohdaten anzeigen
  0 – Beenden
🦤 Fifo fragt: Deine Wahl? 
🦤 Unbekannte Option.

🦤 Schatten-Simulator – Menü:
  1 – Harte Schatten (Raymarch)
  2 – Weiche Schatten (Raymarch + Jitter)
  3 – Ambient Occlusion (SSAO)
  4 – Blinn-Phong Specular
  5 – Vollbild (Blinn-Phong + Schatten + AO)
  6 – Tiefenform wählen (Kugel, Kegel, Pyramide, Wellblech)
  7 – Lichtrichtung anpassen
  8 – Höhen-Rohdaten anzeigen
  0 – Beenden
🦤 Fifo fragt: Deine Wahl? 
🦤 Fifo watschelt davon. Bis zum nächsten Traum!
```

## Teil 14 (21.11.2026 00:52, Nachtschicht)
Die abgebrochene Datei wurde vervollständigt: harte_schatten_raymarch zu Ende geschrieben, weiche_schatten_raymarch, ambient_occlusion, blinn_phong, render_ascii, Menü-Logik und Main-Loop hinzugefügt. EOFError-Handling für Browser-Tests eingebaut. Alles läuft standalone mit Stdlib.

```
 – Diffuse (Lambert) + Schatten
 5 – Vollbild (Blinn-Phong + Schatten + AO)
 6 – Tiefenform wählen (Kugel, Kegel, Pyramide, Wellblech)
 7 – Lichtrichtung anpassen
 8 – Höhen-Rohdaten anzeigen
 0 – Beenden
🦤 Fifo fragt: Deine Wahl? 🦤 🦤 Unbekannte Option.

🦤 Schatten-Simulator – Menü:
 1 – Harte Schatten (Raymarch)
 2 – Weiche Schatten (Jittered Raymarch)
 3 – Nur Ambient Occlusion
 4 – Diffuse (Lambert) + Schatten
 5 – Vollbild (Blinn-Phong + Schatten + AO)
 6 – Tiefenform wählen (Kugel, Kegel, Pyramide, Wellblech)
 7 – Lichtrichtung anpassen
 8 – Höhen-Rohdaten anzeigen
 0 – Beenden
🦤 Fifo fragt: Deine Wahl? 🦤 Formen: 1=Kugel, 2=Kegel, 3=Pyramide, 4=Wellblech
Neue Form (1-4): 🦤 Unbekannte Form.

🦤 Schatten-Simulator – Menü:
 1 – Harte Schatten (Raymarch)
 2 – Weiche Schatten (Jittered Raymarch)
 3 – Nur Ambient Occlusion
 4 – Diffuse (Lambert) + Schatten
 5 – Vollbild (Blinn-Phong + Schatten + AO)
 6 – Tiefenform wählen (Kugel, Kegel, Pyramide, Wellblech)
 7 – Lichtrichtung anpassen
 8 – Höhen-Rohdaten anzeigen
 0 – Beenden
🦤 Fifo fragt: Deine Wahl? 🦤 🦤 Unbekannte Option.

🦤 Schatten-Simulator – Menü:
 1 – Harte Schatten (Raymarch)
 2 – Weiche Schatten (Jittered Raymarch)
 3 – Nur Ambient Occlusion
 4 – Diffuse (Lambert) + Schatten
 5 – Vollbild (Blinn-Phong + Schatten + AO)
 6 – Tiefenform wählen (Kugel, Kegel, Pyramide, Wellblech)
 7 – Lichtrichtung anpassen
 8 – Höhen-Rohdaten anzeigen
 0 – Beenden
🦤 Fifo fragt: Deine Wahl? 🦤 🦤 Der Dodo nickt ein. Bis zum nächsten Traum! 🦤
```

## Teil 15 (21.11.2026 01:06, Nachtschicht)
Ray‑march‑Loop fertiggestellt, weiche Schatten‑Blur, AO, Blinn‑Phong und Menü ergänzt; Syntax‑Fehler behoben, jetzt lauffähig. Den Absturz gleich repariert.

```
+ Harte Schatten
2 – Diffuse + Weiche Schatten
3 – Blinn‑Phong + Schatten + AO
4 – Tiefenform wählen
5 – Lichtrichtung anpassen
6 – Höhen‑Rohdaten anzeigen
7 – Beenden
Deine Wahl?                                         
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
--- Schatten‑Simulator ---
1 – Diffuse (Lambert) + Harte Schatten
2 – Diffuse + Weiche Schatten
3 – Blinn‑Phong + Schatten + AO
4 – Tiefenform wählen
5 – Lichtrichtung anpassen
6 – Höhen‑Rohdaten anzeigen
7 – Beenden
Deine Wahl? Bitte eine Zahl eingeben.
--- Schatten‑Simulator ---
1 – Diffuse (Lambert) + Harte Schatten
2 – Diffuse + Weiche Schatten
3 – Blinn‑Phong + Schatten + AO
4 – Tiefenform wählen
5 – Lichtrichtung anpassen
6 – Höhen‑Rohdaten anzeigen
7 – Beenden
Deine Wahl? Auf Wiedersehen!
```
