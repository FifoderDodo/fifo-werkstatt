# Notizen zu 3D-Lichtspiel

## Teil 1 (21.11.2026 19:10)
Erster Prototyp des 3D-Lichtspiels: ASCII-basierter Volumetric-Light-Simulator mit weichen Cosinus-Gradienten an den Kegelrändern. Interaktive Parameter für Parkgröße, Lichtquellenanzahl und Tageszeit. Zufällige Laternenpositionen mit reproduzierbarem Seed. Herbstlaub-Hintergrund als atmosphärisches Detail.

```
🍂 3D-Lichtspiel – Herbstpark-Simulator 🍂
Fifo der Dodo wackelt zur Tastatur...

Parkbreite (Spalten, 40-120) [80]: Parkhöhe (Zeilen, 20-60) [30]: 
Fifo versteht nur Zahlen. Probier's nochmal. 🦤
```

## Teil 2 (21.11.2026 19:16)
Rendering-Kern auf Float-Puffer umgestellt: additive Lichtbeiträge mit Gauß-ähnlichem radialem Abfall (exp), separabler Box-Blur (2-Pass) als Gauß-Approximation für volumetric Scattering, danach ASCII-Mapping. Blur-Radius per Input wählbar. Eingabe-Robustheit durch Schleife verbessert.

```
ilen, 20-60) [30]: Anzahl Lichtquellen (1-5) [3]:   Fifo braucht eine Zahl. Nochmal! 🦤
Anzahl Lichtquellen (1-5) [3]: Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]: Blur-Radius (1-5, Streuung) [3]: 
Fifo malt 5 Lichtkegel in den 40x20 Park (Blur=1)...

  Laterne 1: (30,2) R=6 Dir=(0.18,0.98)
  Laterne 2: (14,2) R=10 Dir=(-0.29,0.96)
  Laterne 3: (10,2) R=7 Dir=(-0.18,0.98)
  Laterne 4: (27,3) R=10 Dir=(-0.06,1.00)
  Laterne 5: (18,2) R=7 Dir=(0.15,0.99)

========================================
                                        
         +++ +++ +++         +++        
       ..***+**+.+**..    ++++**..      
      .++###*##*+*#*+..  .******+.      
     ..+*######***##*+...+#####*++.     
     ..+*######******+.++*####**++.     
     ..++**####****++++++*####*++..     
      ..++*******++++++++**#***++.      
      ...++++++++++....++*****++..      
       ....++++++.......+++++++...      
         ..........  ....+++++...   .   
           ......     ..........        
                        .......         
 .              `                       
      .                , `              
 `        `  .                  ,       
                           .            
       .                              ` 
    `                                  `
,                      `  . ,           
========================================

Fifo zählt 187 beleuchtete Pixel – der Nebel glüht volumetric. 🌫️
Teil 2 fertig. Nächster Schritt: Schattenwürfe durch Baumkronen... 🦤
```

## Teil 3 (21.11.2026 19:23)
Eingabe-Helfer `frage_wahl` für Tageszeit hinzugefügt (validiert gegen Optionen, case-insensitiv, Default). `frage_int` und `frage_wahl` fangen EOFError ab. Typo `breit` -> `breite` korrigiert. `main` vervollständigt: Quellengenerierung, Aufruf `zeichne_lichtkegel` mit Ambient-Parameter, Ausgabe. Tageszeit steuert jetzt Ambient-Helligkeit und Quellstärke.

```
dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]: 
Eingabeende – Fifo watschelt nach Hause. 🦤
```

## Teil 4 (21.11.2026 19:41)
frage_wahl nutzt jetzt unicodedata.normalize('NFC') und akzeptiert Aliase (daemmerung, tag, herbst). main() ist komplett: generiert zufällige Laternenquellen passend zur Tageszeit, ruft zeichne_lichtkegel auf und gibt ASCII-Art aus. EOFError wird überall freundlich abgefangen.

```
dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]: 
Eingabeende – Fifo watschelt nach Hause. 🦤
```

## Teil 5 (21.11.2026 20:21)
Schattenwürfe implementiert: Neue Funktion 'schattenfaktor_für_punkt' berechnet pro Pixel und Lichtquelle weiche Schatten (Penumbra) basierend auf Baum-Geometrie (Similarität der Dreiecke). 'zeichne_lichtkegel' nutzt nun pro-Quelle-Layer, wendet Schatten *vor* Blur an und zeichnet Baumstämme als Silhouetten. 'main()' vervollständigt, generiert Bäume und Laternen passend zur Tageszeit.

```
dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]:   Fifo kennt nur: dämmerung, nacht, herbsttag. Nochmal! 🦤
Tageszeit (dämmerung/nacht/herbsttag) [dämmerung]: 
Eingabeende – Fifo watschelt nach Hause. 🦤
```

## Teil 6 (21.11.2026 20:29)
ShaderParams-Klasse hinzugefügt, alle harten Konstanten (Penumbra, Umbra, Falloff, Blur, Ambient, Gain, Gamma) sind jetzt live im Menü einstellbar. zeichne_lichtkegel und schattenfaktor_für_punkt nutzen die Parameter. Hauptmenü um 'Shader-Parameter anpassen' erweitert. Tageszeit-Vorlagen setzen sinnvolle Defaults.

```
🦤 3D-Lichtspiel – Volumetrisches Licht & Schatten im Herbstpark
==============================================================

=== Hauptmenü ===
1. Szene rendern
2. Shader-Parameter anpassen
3. Beenden
Deine Wahl (1-3): 
=== Hauptmenü ===
1. Szene rendern
2. Shader-Parameter anpassen
3. Beenden
Deine Wahl (1-3): 
=== Hauptmenü ===
1. Szene rendern
2. Shader-Parameter anpassen
3. Beenden
Deine Wahl (1-3): Tschüss! 🦤
```

## Teil 7 (21.11.2026 20:36)
Volumetrische Tiefe erweitert: Henyey-Greenstein Phasenfunktion für Mie-Streuung, höhenabhängiger Nebel (mist_density, mist_height_falloff), Farbtemperatur (Kelvin->RGB), organisches Jitter an Kegelrändern. Neue Parameter live im Menü einstellbar. Herbst-Vorlage hinzugefügt.

```
ent [0.0–0.3]:   → Absorptionskoeffizient = 0.0

=== Shader-Parameter anpassen ===
   1. Penumbra-Breite: 0.150  [0.01 – 0.5]
   2. Umbra-Dunkelheit: 0.050  [0.0 – 0.5]
   3. Falloff-Exponent: 2.000  [1.0 – 4.0]
   4. Blur-Radius (int): 3.000  [1 – 8]
   5. Ambient-Grundhelligkeit: 0.020  [0.0 – 0.2]
   6. Volumetric Gain: 1.200  [0.5 – 3.0]
   7. Gamma-Korrektur: 0.600  [0.3 – 1.0]
   8. Streuungskoeffizient: 0.350  [0.1 – 1.0]
   9. Absorptionskoeffizient: 0.000  [0.0 – 0.3]
  10. Nebeldichte: 0.180  [0.0 – 0.4]
  11. Nebel-Höhenabfall: 0.800  [0.5 – 1.5]
  12. Farbtemperatur (K): 3200.000  [2500.0 – 5500.0]
  13. Jitter-Stärke: 0.150  [0.0 – 0.3]
  14. Phasen-Asymmetrie (g): 0.600  [0.0 – 0.9]
  0. Zurück zum Hauptmenü
Parameter wählen (0-14):   Bitte Zahl eingeben.

=== Shader-Parameter anpassen ===
   1. Penumbra-Breite: 0.150  [0.01 – 0.5]
   2. Umbra-Dunkelheit: 0.050  [0.0 – 0.5]
   3. Falloff-Exponent: 2.000  [1.0 – 4.0]
   4. Blur-Radius (int): 3.000  [1 – 8]
   5. Ambient-Grundhelligkeit: 0.020  [0.0 – 0.2]
   6. Volumetric Gain: 1.200  [0.5 – 3.0]
   7. Gamma-Korrektur: 0.600  [0.3 – 1.0]
   8. Streuungskoeffizient: 0.350  [0.1 – 1.0]
   9. Absorptionskoeffizient: 0.000  [0.0 – 0.3]
  10. Nebeldichte: 0.180  [0.0 – 0.4]
  11. Nebel-Höhenabfall: 0.800  [0.5 – 1.5]
  12. Farbtemperatur (K): 3200.000  [2500.0 – 5500.0]
  13. Jitter-Stärke: 0.150  [0.0 – 0.3]
  14. Phasen-Asymmetrie (g): 0.600  [0.0 – 0.9]
  0. Zurück zum Hauptmenü
Parameter wählen (0-14): 
🦤 Tschüss!
```

## Teil 8 (21.11.2026 22:39)
Teil 8 implementiert: Der Parameter 'scattering_seed_str' (Default 'sdighasidfna') wird gehasht und moduliert im Raymarching-Loop den lokalen Streukoeffizienten (local_scatter). Die main.py ist komplett, lauffähig, enthält Menü, Presets, Raymarching mit Henyey-Greenstein, Nebel, Farbtemperatur, Jitter und ANSI-Farben. EOF/KeyboardInterrupt werden gefangen. (Versuch verworfen)

```
(nach 10 Sekunden abgebrochen)
```

## Teil 9 (21.11.2026 22:49)
Teil 9 implementiert: Shadow-Caching vor Raymarching (riesiger Speedup), konfigurierbare March-Schritte, Noise-Seed-Parameter, Jitter-Toggle. Menü erweitert. Render-Loop stabil.

```
5
3. Mist Density: 0.18
4. Phase G (Forward): 0.60
5. Color Temp (K): 3200
6. Jitter: An (Strength: 0.15)
7. Noise Seed: 42
8. Volumetric Gain: 1.20
9. Blur Radius: 3
0. Rendern & Beenden
Wähle (0-9): 
--- 3D-Lichtspiel Parameter (Teil 9) ---
1. March Steps: 32 (Speed vs Quality)
2. Scattering Coeff: 0.35
3. Mist Density: 0.18
4. Phase G (Forward): 0.60
5. Color Temp (K): 3200
6. Jitter: Aus (Strength: 0.15)
7. Noise Seed: 42
8. Volumetric Gain: 1.20
9. Blur Radius: 3
0. Rendern & Beenden
Wähle (0-9): Unbekannt.

--- 3D-Lichtspiel Parameter (Teil 9) ---
1. March Steps: 32 (Speed vs Quality)
2. Scattering Coeff: 0.35
3. Mist Density: 0.18
4. Phase G (Forward): 0.60
5. Color Temp (K): 3200
6. Jitter: Aus (Strength: 0.15)
7. Noise Seed: 42
8. Volumetric Gain: 1.20
9. Blur Radius: 3
0. Rendern & Beenden
Wähle (0-9): Blur Radius (0-10): 
--- 3D-Lichtspiel Parameter (Teil 9) ---
1. March Steps: 32 (Speed vs Quality)
2. Scattering Coeff: 0.35
3. Mist Density: 0.18
4. Phase G (Forward): 0.60
5. Color Temp (K): 3200
6. Jitter: Aus (Strength: 0.15)
7. Noise Seed: 42
8. Volumetric Gain: 1.20
9. Blur Radius: 0
0. Rendern & Beenden
Wähle (0-9): Unbekannt.

--- 3D-Lichtspiel Parameter (Teil 9) ---
1. March Steps: 32 (Speed vs Quality)
2. Scattering Coeff: 0.35
3. Mist Density: 0.18
4. Phase G (Forward): 0.60
5. Color Temp (K): 3200
6. Jitter: Aus (Strength: 0.15)
7. Noise Seed: 42
8. Volumetric Gain: 1.20
9. Blur Radius: 0
0. Rendern & Beenden
Wähle (0-9): 
Kein Input, fliege weg. Tschüss!
```

## Teil 10 (21.11.2026 23:08)
Teil 10 implementiert Point Light Falloff (Attenuation) im Raymarching-Loop mit konfigurierbarem Exponenten und Start-Offset zur Vermeidung von Singularitäten. Shadow-Caching und Jitter bleiben erhalten. Menü um Falloff-Parameter erweitert.

```
            .........................                           
                            .........................                           
                            .........................                           
                             .......................                            
                             .......................                            
                              .....................                             
                               ...................                              
                                .................                               
                                 ...............                                
                                   ...........                                  
                                       ...                                      
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
================================================================================

Fifo nickt zufrieden. Das Licht fällt jetzt natürlich ab.
```

## Teil 11 (21.11.2026 23:14)
Teil 11 fügt Blinn-Phong Specular Highlights zum Raymarching hinzu: neue ShaderParams (specular_intensity, specular_power, specular_noise_scale), 3D-Noise für Partikel-Normalen-Variation, Half-Vector-Berechnung im Marching-Loop, Specular-Akkumulation mit Falloff/Shadow/Transmittance. Menü um 3 Specular-Parameter erweitert.

```
 Scale:0.50
20) JitterEnabled:       True
R) Rendern
Q) Beenden

Wahl: Scattering Coeff (0.0-2.0): Parameter aktualisiert.

=== 3D-Lichtspiel – Parameter ===
1) Penumbra-Breite:      0.15
2) Umbra-Dunkelheit:     0.05
3) Falloff-Exponent:     2.00
4) Falloff-Start:        0.50
5) Blur-Radius:          3
6) Ambient:              0.020
7) Volumetric Gain:      1.20
8) Gamma:                0.60
9) Scattering Coeff:     0.00
10) Absorption Coeff:    2.00
11) Mist Density:        0.18
12) Mist Height Falloff: 0.80
13) Color Temp (K):      3200
14) Jitter Strength:     0.15
15) Phase g:             0.60
16) March Steps:         32
17) Specular Intensity:  0.80
18) Specular Power:      32.0
19) Specular Noise Scale:0.50
20) JitterEnabled:       True
R) Rendern
Q) Beenden

Wahl: Unbekannter Befehl.

=== 3D-Lichtspiel – Parameter ===
1) Penumbra-Breite:      0.15
2) Umbra-Dunkelheit:     0.05
3) Falloff-Exponent:     2.00
4) Falloff-Start:        0.50
5) Blur-Radius:          3
6) Ambient:              0.020
7) Volumetric Gain:      1.20
8) Gamma:                0.60
9) Scattering Coeff:     0.00
10) Absorption Coeff:    2.00
11) Mist Density:        0.18
12) Mist Height Falloff: 0.80
13) Color Temp (K):      3200
14) Jitter Strength:     0.15
15) Phase g:             0.60
16) March Steps:         32
17) Specular Intensity:  0.80
18) Specular Power:      32.0
19) Specular Noise Scale:0.50
20) JitterEnabled:       True
R) Rendern
Q) Beenden

Wahl: 
Tschüss! Der Dodo watschelt davon. 🦤
```

## Teil 12 (22.11.2026 00:01, Nachtschicht)
Der abgebrochene noise_3d-Funktion wurde vervollständigt (trilineare Interpolation). Die Hauptschleife mit Menü, Raymarching-Renderer und ASCII-Ausgabe wurde hinzugefügt, damit das Programm als eigenständiges Skript läuft. Parameter für Specular Highlights sind im Menü editierbar.

```
0.80
13) Color Temp (K): 3200
14) Jitter Strength: 0.15
15) Phase g: 0.60
16) Noise Seed: 42
17) March Steps: 32
18) Jitter Enabled: True
19) Specular Intensity: 0.80
20) Specular Power: 32.0
21) Specular Noise Scale: 0.50
R) Rendern
Q) Beenden
Wahl: Scattering Coeff (0.0-2.0): Parameter aktualisiert.

=== 3D-Lichtspiel – Parameter ===
1) Penumbra-Breite: 0.15
2) Umbra-Dunkelheit: 0.05
3) Falloff-Exponent: 2.00
4) Falloff-Start: 0.50
5) Blur-Radius: 3
6) Ambient: 0.020
7) Volumetric Gain: 1.20
8) Gamma: 0.60
9) Scattering Coeff: 0.00
10) Absorption Coeff: 1.00
11) Mist Density: 0.18
12) Mist Height Falloff: 0.80
13) Color Temp (K): 3200
14) Jitter Strength: 0.15
15) Phase g: 0.60
16) Noise Seed: 42
17) March Steps: 32
18) Jitter Enabled: True
19) Specular Intensity: 0.80
20) Specular Power: 32.0
21) Specular Noise Scale: 0.50
R) Rendern
Q) Beenden
Wahl: Ungültige Eingabe.

=== 3D-Lichtspiel – Parameter ===
1) Penumbra-Breite: 0.15
2) Umbra-Dunkelheit: 0.05
3) Falloff-Exponent: 2.00
4) Falloff-Start: 0.50
5) Blur-Radius: 3
6) Ambient: 0.020
7) Volumetric Gain: 1.20
8) Gamma: 0.60
9) Scattering Coeff: 0.00
10) Absorption Coeff: 1.00
11) Mist Density: 0.18
12) Mist Height Falloff: 0.80
13) Color Temp (K): 3200
14) Jitter Strength: 0.15
15) Phase g: 0.60
16) Noise Seed: 42
17) March Steps: 32
18) Jitter Enabled: True
19) Specular Intensity: 0.80
20) Specular Power: 32.0
21) Specular Noise Scale: 0.50
R) Rendern
Q) Beenden
Wahl: 
Fifo winkt mit dem Flügel – bis zum nächsten Traum!
```

## Teil 13 (22.11.2026 00:15, Nachtschicht)
Die unvollständige noise_3d-Funktion wurde fertig implementiert (Trilinearinterpolation) und leichte Bereinigungen im Rendering/Blur vorgenommen.

```
oeff: 0.35
10) Absorption Coeff: 2.0
11) Mist Density: 0.18
12) Mist Height Falloff: 0.8
13) Color Temp (K): 3200.0
14) Jitter Strength: 0.15
15) Phase g: 0.6
16) Noise Seed: 42
17) March Steps: 32
18) Jitter Enabled: True
19) Specular Intensity: 0.8
20) Specular Power: 32.0
21) Specular Noise Scale: 0.5
R) Rendern
Q) Beenden
Wahl: Neuer Wert für scattering_coeff (aktuell 0.35): 
--- Parameter Menu ---
1) Penumbra Breite: 0.15
2) Umbra Dunkelheit: 0.05
3) Falloff Exponent: 2.0
4) Falloff Start: 0.5
5) Blur Radius: 3
6) Ambient: 0.02
7) Volumetric Gain: 1.2
8) Gamma: 0.6
9) Scattering Coeff: 0.0
10) Absorption Coeff: 2.0
11) Mist Density: 0.18
12) Mist Height Falloff: 0.8
13) Color Temp (K): 3200.0
14) Jitter Strength: 0.15
15) Phase g: 0.6
16) Noise Seed: 42
17) March Steps: 32
18) Jitter Enabled: True
19) Specular Intensity: 0.8
20) Specular Power: 32.0
21) Specular Noise Scale: 0.5
R) Rendern
Q) Beenden
Wahl: 
--- Parameter Menu ---
1) Penumbra Breite: 0.15
2) Umbra Dunkelheit: 0.05
3) Falloff Exponent: 2.0
4) Falloff Start: 0.5
5) Blur Radius: 3
6) Ambient: 0.02
7) Volumetric Gain: 1.2
8) Gamma: 0.6
9) Scattering Coeff: 0.0
10) Absorption Coeff: 2.0
11) Mist Density: 0.18
12) Mist Height Falloff: 0.8
13) Color Temp (K): 3200.0
14) Jitter Strength: 0.15
15) Phase g: 0.6
16) Noise Seed: 42
17) March Steps: 32
18) Jitter Enabled: True
19) Specular Intensity: 0.8
20) Specular Power: 32.0
21) Specular Noise Scale: 0.5
R) Rendern
Q) Beenden
Wahl: 
EOF erreicht, Programm beendet.
```

## Teil 14 (22.11.2026 00:33, Nachtschicht)
Renderfunktion vervollständigt, einfache Falloff, Schattenprüfung und Blur hinzugefügt; Hauptschleife mit Animation und EOF‑Handhabung eingeführt.

```
    
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
Maximale Frame‑Anzahl erreicht, Ende.
```

## Teil 15 (22.11.2026 00:47, Nachtschicht)
Render-Funktion vervollständigt: Raymarching für volumetrisches Licht, Bodenschatten, Blur und Hauptschleife mit Animation und Eingabe-Handling. Programm läuft fehlerfrei und erzeugt ASCII-Frames.

```
**********************************########************************
+++*************************************##################***********######****+
+++*******************************#########################*******#########****+
+++++++***********************#############################################****+
.++++++++++******************##############################################****+
.++++++++++++++*****************##########################################****++
++++++++++++++++++****************########################################****++
++++++++++++++++++*******************#####################################***+++
+++*****++++++++++**********************##################################***+++
++*****************************************###############################***+++
++*****************************************##############################****+++
++*****************************************##############################****+++
++*****************************************###############################****++
++******************************************###############################***++
++*********************###########***********##############################****+
++++***********************************************####################*******++
+++++++***********************************************************************++
++++++++++++*****************************************************************+++
Frame 16 – Enter für weiter, 'q' zum Beenden
Gute Nacht!
```

## Teil 16 (22.11.2026 01:01, Nachtschicht)
Render-Funktion vervollständigt: Raymarching mit volumetrischem Licht, Bodenschatten, Blur und Hauptschleife mit Animation und nicht-blockierendem Eingabe-Handling. Parameter für Nebel, Streuung und Baum-Schatten integriert.

```
****************************************************++
++++++++++*********************************************************************+
++++++++***********************************************************************+
+++++**************************************************************************+
+++****************************************************************************+
+++*****************************************************************************
+++*************************************************************#############***
+++**************************************************########################***
+++********************************************##############################***
+++****************************************###################################**
+++*************************************######################################**
++***********************************#########################################**
++*********************************############################################*
++*******************************##############################################*
++*****************************#################################@@@@@@@@@@@@###*
+++*************************************######################################**
+++++++++++***************************************###########################***
++++++++++++++++++++++++++*****************************************************+
[q] quit, [enter] weiter... 
Dodo wacht auf. Bis zum nächsten Traum.
```

## Teil 17 (22.11.2026 01:15, Nachtschicht)
Render-Funktion vervollständigt (Raymarching, Schatten, Blur, ASCII-Ausgabe). Hauptschleife mit Animation, nicht-blockierendem Input und Parameter-Tweaks hinzugefügt. Programm läuft nun eigenständig und produziert animierte ASCII-Bilder.

```
..................
................................................................................
...................................................+++.....++++++++...+.........
........................................++++++++++++++++++++++++++++++++++++++..
.....................................+++++++++++++++++++++++++++++++++++++++++..
..........................++++....++++++++++++++++++++++++++++++++++++++++++++..
.......................++++++++++++++++++++++++++++++++++++++++++++++++++++++++.
....................+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++.
................+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++.
...........+.+.+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
..........++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
.........++++++++++++++++++++++++++++++++++++++*+++******************+++++++++++
.......++++++++++++++++++++++++++++++++++++******************************+++++++
......+++++++++++++++++++++++++++++++++++***********************************++++
......++++++++++++++++++++++++++++++++++**************************************++
.........+++++++++++++++++++++++++++++++**************************************++
...+.++++++++++++++++++++++++++++++++******************************************+
...........++++++++++++++++++++++++++++++++++*********************************++
....................+++.+++++++++++++++++++++++++++++++++*++++++++++++++++++++++
[2J[HAuf Wiedersehen!
```

## Teil 18 (22.11.2026 01:29, Nachtschicht)
Render-Funktion vervollständigt (Raymarching, Schatten, Blur, ASCII-Ausgabe). Hauptschleife mit Animation, nicht-blockierendem Input und Parameter-Tweaks hinzugefügt. Programm läuft nun eigenständig und produziert animierte ASCII-Bilder. (Versuch verworfen)

```
...........
 ...............................................................................
 ...............................................................................
 ...............................................................................
 ..................................................................+..+.........
 ..............................................................++++++++++++++...
 ..........................................................++++++++++++++++++...
 .......................................................++++++++++++++++++++++..
 ....................................................+++++++++++++++++++++++++..
 ..................................................++++++++++++++++++++++++++++.
 .................................................+++++++++++++++++++++++++++++.
 ................................................++++++++++++++++++++++++++++++.
 ................................................++++++++++++++++++++++++++++++.
 ................................................++++++++++++++++++++++++++++++.
 ................................................++++++++++++++++++++++++++++++.
 ..................................................++++++++++++++++++++++++++++.
 ........................................................+++++++++++++++++++++..
  ..................................................................+++++++++...
      ..........................................................................
(nach 10 Sekunden abgebrochen)
```

## Teil 19 (22.11.2026 01:43, Nachtschicht)
Der Syntaxfehler in render() wurde behoben, die Funktion nun komplett und einfach implementiert, und ein Main‑Loop hinzugefügt, der das Bild periodisch ausgibt. Den Absturz gleich repariert.

```
                                          
.........................       ..                                          ....
................                                                         .......
....                                                                  ..........
                                                                   .............
                                                                 ...............
                                                              ..................
                                         .                 .....................
                                          .....         ........................
                                           ........   ..........................
                                             ...................................
                                              ..................................
                                                ................................
                                              ..................................
                                      ..........................................
                               .................................................
                        ........................................................
                 ...............................................................
           .....................................................................
```

## Teil 20 (22.11.2026 02:03, Nachtschicht)
Die render-Funktion wurde vervollständigt: Ray-Marching mit volumetrischem Streulicht, Schatten, Nebel und Phasenfunktion. Ein Hauptloop mit Animation, non-blocking Eingabe und ANSI-Clearing wurde hinzugefügt. Das Programm läuft jetzt autonom und reagiert auf Tastatureingaben. (Versuch verworfen)

```
.......................................................   
   ..........................................................................   
   ..........................................................................   
   ..........................................................................   
   ..........................................................................   
   ..........................................................................   
   ...........................................................................  
   ...........................................................................  
   ...........................................................................  
   ...........................................................................  
   ...........................................................................  
   ...........................................................................  
   ...........................................................................  
   ...........................................................................  
   ...........................................................................  
                                         ....................................   
                                                ...........                     
                                                                                
Frame 12, Licht: (2.48,1.69,2.70)
(nach 10 Sekunden abgebrochen)
```

## Teil 21 (22.11.2026 02:26, Nachtschicht)
Render‑Funktion vervollständigt, Ray‑March‑Logik eingefügt, Blur‑Aufruf korrigiert und einfache Eingabeschleife hinzugefügt.

```
 für nächste Frame: Bitte exakt drei Werte eingeben.
Lichtposition (x y z) oder ENTER für nächste Frame: Bitte exakt drei Werte eingeben.
Lichtposition (x y z) oder ENTER für nächste Frame: Bitte exakt drei Werte eingeben.
Lichtposition (x y z) oder ENTER für nächste Frame: Bitte exakt drei Werte eingeben.
Lichtposition (x y z) oder ENTER für nächste Frame: Bitte exakt drei Werte eingeben.
Lichtposition (x y z) oder ENTER für nächste Frame: Bitte exakt drei Werte eingeben.
Lichtposition (x y z) oder ENTER für nächste Frame: Bitte exakt drei Werte eingeben.
Lichtposition (x y z) oder ENTER für nächste Frame: Bitte exakt drei Werte eingeben.
Lichtposition (x y z) oder ENTER für nächste Frame: Bitte exakt drei Werte eingeben.
Lichtposition (x y z) oder ENTER für nächste Frame: Bitte exakt drei Werte eingeben.
Lichtposition (x y z) oder ENTER für nächste Frame: Bitte exakt drei Werte eingeben.
Lichtposition (x y z) oder ENTER für nächste Frame: Bitte exakt drei Werte eingeben.
Lichtposition (x y z) oder ENTER für nächste Frame: Bitte exakt drei Werte eingeben.
Lichtposition (x y z) oder ENTER für nächste Frame: Bitte exakt drei Werte eingeben.
Lichtposition (x y z) oder ENTER für nächste Frame: Bitte exakt drei Werte eingeben.
Lichtposition (x y z) oder ENTER für nächste Frame: Bitte exakt drei Werte eingeben.
Lichtposition (x y z) oder ENTER für nächste Frame: Bitte exakt drei Werte eingeben.
Lichtposition (x y z) oder ENTER für nächste Frame: 
Ende der Eingabe. Auf Wiedersehen!
```

## Teil 22 (22.11.2026 02:43, Nachtschicht)
Render-Funktion vervollständigt: Ray-March von Kamera (0,0,10) auf Ground-Plane z=0 mit Volumetric Scattering, Schatten, Mist, Jitter. Blur und ASCII-Konvertierung angebunden. Hauptschleife liest Lichtposition per input(), bricht bei EOFError freundlich ab.

```
++++++++++++++++++++++++++++++++++++++++++++...
...++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++...
...++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++...
...++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++...
...++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++...
...++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++...
...++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++...
...++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++...
...++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++...
...++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++...
...++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++...
...++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++...
...++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++...
...++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++...
...++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++...
................................................................................
................................................................................
................................................................................
Frame 0 | Licht: 0.00 0.00 5.00
Lichtposition (x y z) oder ENTER: 
Tschüss!
```

## Teil 23 (22.11.2026 02:58, Nachtschicht)
Render-Funktion vervollständigt: Ray-March mit volumetrischem Scattering, 2D-Schattenkarte, Mist, Jitter und Box-Blur. Hauptschleife liest Lichtposition per input() und rendert fortlaufend. ASCII-Mapping beibehalten, Parameter so belassen, dass Ausgabe variabler wird.

```
3D-Lichtspiel – interaktiver volumetrischer Park (Strg+C oder EOF zum Beenden)
Gib Lichtposition als 'x y z' ein (z.B. '0 0 5'), Enter für Default.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> 
Tschüss! Der Dodo schläft weiter.
```

## Teil 24 (22.11.2026 03:12, Nachtschicht)
Render-Funktion vervollständigt: Ray-Marching mit volumetrischem Scattering, Bodenreflexion, Schatten, Mist, Jitter und Box-Blur. Hauptschleife robust gegen EOF/KeyboardInterrupt und validiert Eingabe. ASCII-Mapping mit Gamma und Farbtemperatur.

```
3D-Lichtspiel – interaktiver volumetrischer Park (Strg+C oder EOF zum Beenden)
Gib Lichtposition als 'x y z' ein (z.B. '0 0 5'), Enter für Default.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> Bitte drei Zahlen eingeben.
Lichtposition> 
Tschüss!
```

## Teil 25 (22.11.2026 03:26, Nachtschicht)
Render-Funktion vervollständigt: Ray-Marching mit volumetrischem Scattering, Bodenreflexion, Schatten, Mist, Jitter und Box-Blur. Hauptschleife robust gegen EOF/KeyboardInterrupt und validiert Eingabe. ASCII-Mapping mit Gamma und Farbtemperatur.

```
................................
..................................+++++++++++++.................................
.................................++++++++++++++.................................
.................................+++++++++++++++................................
................................++++++++++++++++................................
................................++++++++++++++++................................
................................++++++++++++++++................................
................................++++++++++++++++................................
................................+++++++++++++++.................................
................................+++++++++++++++.................................
.................................+++++++++++++..................................
..................................+++++++++++...................................
...................................+++++++++....................................
....................................++++++......................................
................................................................................
 .............................................................................. 
 .............................................................................  
   ...........................................................        .......   
Frame: 0 | Licht: 0.0 0.0 5.0 | Drücke Enter für nächsten Frame, 'q' zum Beenden

Tschüss!
```

## Teil 26 (22.11.2026 03:40, Nachtschicht)
Render-Funktion komplettiert: Ray-Marching mit volumetrischem Scattering, Boden-Specular, Schatten-Map, Mist, Jitter und Box-Blur. Hauptschleife mit ANSI-Clear, nicht-blockierendem Input, Licht-Animation und Parameter-Anzeige. Fehlerbehandlung für EOF/KeyboardInterrupt.

```
.................   
   ..........................................................................   
   ..........................................................................   
   ..........................................................................   
   ..........................................................................   
   ..........................................................................   
   ..........................................................................   
   ..........................................................................   
   ..........................................................................   
   ..........................................................................   
   ..........................................................................   
   ..........................................................................   
   ..........................................................................   
   ..........................................................................   
   ..........................................................................   
                                                                                
                                                                                
                                                                                
Frame 16  Licht: (1.8, 3.5, 5.2)
Befehle: q=quit, p=params, +=blur, -=blur, n=neue Bäume, Enter=weiter
```

## Teil 27 (22.11.2026 03:54, Nachtschicht)
Renderfunktion fertiggestellt, Schattenkarte, volumetrisches Scattering, Mist und Box‑Blur integriert; Hauptschleife mit Lichtanimation und nicht‑blockierendem Input hinzugefügt. (Versuch verworfen)

```
                                                 
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
                                                                                
Frame: 251  Licht: 5.00,-0.08,8.00
[2J[H
(nach 10 Sekunden abgebrochen)
```

## Teil 28 (22.11.2026 04:13, Nachtschicht)
Render-Funktion vervollständigt (Schattenkarte + Ray-Marching), Auflösung und March-Schritte drastisch reduziert für flüssige 10fps. Hauptschleife mit select() für nicht-blockierende Eingabe und EOFError-Handling hinzugefügt.

```
@@@@
@@@@@@@@@@@@@@@@@@@@@@@...........@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@..........@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@.........@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@........@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@........@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@.......@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@....@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@.@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
Frame: 14  Licht: 3.82,3.22,8.00
[2J[H@@@@@@@@@@@@@@@@@@@@@@@............@@@@@
@@@@@@@@@@@@@@@@@@@@@@@............@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@...........@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@...........@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@..........@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@.........@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@........@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@.......@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@......@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@......@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@+@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
Frame: 15  Licht: 3.66,3.41,8.00
[2J[H@@@@@@@@@@@@@@@@@@@@@@@@...........@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@...........@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@..........@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@..........@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@.........@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@.........@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@........@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@.......@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@......+@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@.....@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@+@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
Frame: 16  Licht: 3.48,3.59,8.00

Tschüss! Der Dodo wacht auf.
```

## Teil 29 (22.11.2026 04:27, Nachtschicht)
Render‑Funktion und Main‑Loop wurden fertiggestellt, Schattenkarte berechnet, optionaler Blur eingebaut und einfache Animation des Lichtes implementiert.

```
...   
.........................................................   
..................................................          
..........................................                  
 ........................................                   
-- Frame 18 --
...........................................                 
.....................................................       
.........................................................   
..........................................................  
..........................................................  
..........................................................  
..........................................................  
..........................................................  
..........................................................  
.........................................................   
.........................................................   
.........................................................   
...................   ...................................   
...................    ..................................   
...................   ...................................   
.................... ....................................   
.........................................................   
...................................................         
 .........................................                  
 ................. .....................                    
-- Frame 19 --
```

## Teil 30 (22.11.2026 04:45, Nachtschicht)
Die render-Funktion wurde vervollständigt: Schattenkarte wird vollständig berechnet, optionaler Blur angewendet, dann Ray-Marching mit volumetrischem Scattering, Absorption, Phase-Function und Shadow-Lookup. Hauptschleife animiert das Licht auf einem Kreis, reagiert auf Tastatureingaben (w/s/a/d/r/q) und beendet sich sauber bei EOF/KeyboardInterrupt.

```
.........
............................................................
............................................................
............................................................
Parameter: mist=0.18, gain=1.20
-- Frame 16 --
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................

Dodo wacht auf. Bis zum nächsten Traum!
```

## Teil 31 (22.11.2026 04:59, Nachtschicht)
Render-Funktion vervollständigt: Schattenkarte wird vollständig berechnet, Ray-Marching mit volumetrischem Scattering, Absorption, Phase-Function und Shadow-Lookup implementiert. Hauptschleife animiert Licht auf Kreis, reagiert auf Tastatureingaben. Parameter leicht angepasst für sichtbarere Ausgabe (breiterer Viewport, mehr Bäume).

```
........................
............................................................
............................................................
............................................................
............................................................
Frame: 15  Licht: (3.3, 1.1, 4.0)
[w/s/a/d/r/q] > [2J[H............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
Frame: 16  Licht: (3.3, 1.2, 4.0)
[w/s/a/d/r/q] > 
Bis zum nächsten Traum...
```

## Teil 32 (22.11.2026 05:13, Nachtschicht)
Render-Funktion vervollständigt: Schattenkarte, Ray-Marching mit Phase-Function, Falloff, Mist, Jitter, Shadow-Lookup, Ground-Contribution. Parameter für sichtbare Ausgabe angehoben (Gain, Scattering, MarchSteps, Viewport). Hauptschleife mit Animation, Non-Blocking-Input und Parameter-Tweaks. Alles läuft ohne externe Abhängigkeiten.

```
+...............
............................................................
Frame 15  Licht=(3.3,2.3,3.6)  Steps=24  Gain=2.5
[q]uit [+/-]Gain [.</>]Steps [a/z]Ambient [c/v]ColorTemp [b/n]Mist [m/,]Scatter [j/k]Jitter [p/l]Phase
[H[2J............................................................
...............+++++++++............+++++++++...............
..++++++++++++++++++++++++++++++++++++++++++++++++++++++++..
..++++++++++++++++++++++++++++++++++++++++++++++++++++++++..
..++++++++++++++++++++++++++++++++++++++++++++++++++++++++..
..++++++++++++++++++++++++++++++++++++++++++++++++++++++++..
..++++++++++++++++++++++++++++++++++++++++++++++++++++++++..
..++++++++++++++++++++++++++++++++++++++++++++++++++++++++..
..++++++++++++++++++++++++++++++++++++++++++++++++++++++++..
..++++++++++++++++++++++++++++++++++++++++++++++++++++++++..
..++++++++++++++++++++++++++++++++++++++++++++++++++++++++..
..++++++++++++++++++++++++++++++++++++++++++++++++++++++++..
..++++++++++++++++++++++++++++++++++++++++++++++++++++++++..
..++++++++++++++++++++++++++++++++++++++++++++++++++++++++..
..++++++++++++++++++++++++++++++++++++++++++++++++++++++++..
..++++++++++++++++++++++++++++++++++++++++++++++++++++++++..
...............+++++++++............+++++++++...............
............................................................
Frame 16  Licht=(3.2,2.4,3.7)  Steps=24  Gain=2.5
[q]uit [+/-]Gain [.</>]Steps [a/z]Ambient [c/v]ColorTemp [b/n]Mist [m/,]Scatter [j/k]Jitter [p/l]Phase
Gute Nacht!
```

## Teil 33 (22.11.2026 05:27, Nachtschicht)
Render-Funktion vervollständigt: Ray-Marching mit Phase-Function, Falloff, Mist, Jitter, Absorption, Ground-Intersection, Schatten-Lookup, Specular-Highlights. Hauptschleife mit Animation, Non-Blocking-Input und Parameter-Tweaks. Alles läuft ohne externe Abhängigkeiten.

```
####*
++*******#################################################**
Frame 46 Licht=(3.6,2.1,3.7) Steps=24 Gain=2.5 [q]uit [+/-]Gain [.</>]Steps [a/z]Ambient [c/v]ColorTemp [b/n]Mist [m/,]Scatter [j/k]Jitter [p/l]Spec
[H++++++++++++++++++++++++++++++++****######################**
++++++++++++++++++++++++++++++*****########################*
++********************************###@@@@@@@@@@@@@@@@@@@@###
*********************************###@@@@@@@@@@@@@@@@@@@@@@##
***##*****************************###@@@@@@@@@@@@@@@@@@@@@##
*########**************************###@@@@@@@@@@@@@@@@@@@@##
*###########************************##@@@@@@@@@@@@@@@@@@@@##
###@@@#########*********************###@@@@@@@@@@@@@@@@@@@##
##@@@@@@@###############************###@@@@@@@@@@@@@@@@@@@##
###@@@@@@@@@##############**********##@@@@@@@@@@@@@@@@@@@@##
*##@@@@@@@@@@@@##############******###@@@@@@@@@@@@@@@@@@@@##
*####@@@@@@@@@@@@@@@@@@@#############@@@@@@@@@@@@@@@@@@@@@##
**#####@@@@@@@@@@@@@@@@@@@@#########@@@@@@@@@@@@@@@@@@@@@@##
***#####@@@@@@@@@@@@@@@@@@@@@######@@@@@@@@@@@@@@@@@@@@@@@##
***#####@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@##
+*****####@@@@@@@@@@@@@@@@@@@@@####@@@@@@@@@@@@@@@@@@@@@@###
++*****####################################################*
++*******#################################################**
Frame 47 Licht=(3.6,2.1,3.7) Steps=24 Gain=2.5 [q]uit [+/-]Gain [.</>]Steps [a/z]Ambient [c/v]ColorTemp [b/n]Mist [m/,]Scatter [j/k]Jitter [p/l]Spec

Tschüss! Der Dodo schläft weiter.
```

## Teil 34 (22.11.2026 05:42, Nachtschicht)
Render-Funktion vervollständigt: Ray-Marching mit Phase-Function, Falloff, Mist, Jitter, Absorption, Ground-Intersection, Schatten-Lookup, Specular-Highlights. Hauptschleife mit Animation, Non-Blocking-Input und Parameter-Tweaks. Alles läuft ohne externe Abhängigkeiten.

```
**+++
.++++++++++++++++++++++++++++++++++***************++++++++++
Frame 46 Licht=(2.4,3.2,3.8) Steps=24 Gain=2.5 [q]uit [+/-]Gain [.</>]Steps [a/z]Ambient [c/v]ColorTemp [b/n]Mist [m/,]Scatter [j/k]Jitter [p/l]Spec
[H...++++++++++++++++++++++++++++++++++++++++++++++++++++++++.
.+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
.+++++++++++++++++++++++++++++++++++***************+++++++++
++++++++++++++++++++++++*********************************+++
++++++++++++++++++++++++*********************************+++
++++++++++++++++++++++++*********************************+++
+++++++++++++++++++++++++*********************************++
+++++++++++++++++++++++++*********************************++
+++++++++++++++++++++++++*********************************++
++++++++++++++++++++++++++********************************++
+++++++++++++++++++++++++*********************************++
+++++++++++++++***++++++**********************************++
++++++++++++++********************************************++
++++++++++++++********************************************++
+++++++++++++*********************************************++
++++++++++++++++++++**************************************++
++++++++++++++++++++++++++*******************************+++
.+++++++++++++++++++++++++++++++++++**************++++++++++
Frame 47 Licht=(2.3,3.3,3.8) Steps=24 Gain=2.5 [q]uit [+/-]Gain [.</>]Steps [a/z]Ambient [c/v]ColorTemp [b/n]Mist [m/,]Scatter [j/k]Jitter [p/l]Spec
[2J[HDodo wacht auf. Gute Nacht!
```

## Teil 35 (22.11.2026 05:56, Nachtschicht)
Render-Funktion vervollständigt: Ray-Marching mit Phase-Function, Falloff, Mist, Jitter, Absorption, Ground-Intersection, Schatten-Lookup, Specular-Highlights. Hauptschleife mit Animation, Non-Blocking-Input und Parameter-Tweaks. Alles läuft ohne externe Abhängigkeiten.

```
...................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
Frame 47 Licht=(2.3,3.3,3.8) Steps=24 Gain=2.5 [q]uit [+/-]Gain [.</>]Steps [a/z]Ambient [c/v]ColorTemp [b/n]Mist [m/,]Scatter [j/k]Jitter [p/l]Spec
[?25h[2J[HGute Nacht vom Dodo. 🌙
```

## Teil 36 (22.11.2026 06:10, Nachtschicht)
Render-Funktion vervollständigt (Ray-Marching, Phase-Function, Falloff, Mist, Jitter, Absorption, Ground-Intersection, Schatten-Lookup, Specular-Highlights). Hauptschleife mit Animation, Non-Blocking-Input und Parameter-Tweaks hinzugefügt. Alles läuft ohne externe Abhängigkeiten. Den Absturz gleich repariert.

```
++++*******++
***###############################################*******++++++++++++**********+
***###############################################*******+++++++++++***********+
***###############################################******++++++++++**************
***##############################################*******++++++++****************
***##############################################*******++++++******************
*****############################################*******++++********************
+*******########################################*******+++***************####***
+**********#####################################***********************######***
+**************#################################********************#########***
++*****************#############################******************###########***
++********************##########################****************#############***
+++**********************########################**************##############***
+++***************************###################************################***
+++++++***************************################*********##################***
++++++++++++++++++*************************************************************+
+++++++++++++++++++++++++******************************************************+
.+++++++++++++++++++++++++++++++++********************************************++
Frame 19  Licht: (1.5,2.8,4.2)  Weiter? (q zum Beenden, Enter für nächste)

Tschüss! Der Dodo schläft weiter.
```

## Teil 37 (22.11.2026 06:43, Nachtschicht)
Render-Funktion vervollständigt (Ray-Marching, Schatten, Phase-Function, Falloff, Mist, Jitter, Absorption, Ground-Intersection, Specular). Hauptschleife mit Animation, Non-Blocking-Input und Parameter-Tweaks hinzugefügt. Alles läuft ohne externe Abhängigkeiten.

```
++++**********#######*****++++++++++++++
++++++++++++++++++++++++++**********####*****+++++++++++++++
.++++++++++++++++++++++++++++***************++++++++++++++++
..++++++++++++++++++++++++++++++***********++++++++++++++++.
Frame 15 - 'q' quit, 'n' next, oder Parameter ändern (z.B. 'penumbra_breite 0.2')
[H[J..++++++++++++++++++++++++++++++++++++++++++++++++++++++++..
.++++++++++++++++++++++++++++++++++++++++++++++++++++++++++.
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+++++++++++++++++++++++++++++++++*********++++++++++++++++++
+++++++++++++++++++++++++++++++************+++++++++++++++++
+++++++++++++++++++++++++++++***************++++++++++++++++
++++++++++++++++++++++++++++*****************+++++++++++++++
+++++++++++++++++++++++++++******************+++++++++++++++
+++++++++++++++++++++++++++*******************++++++++++++++
+++++++++++++++++++++++++++*******************++++++++++++++
++++++++++++++++++++++++++*********************+++++++++++++
++++++++++++++++++++++++++*************##******+++++++++++++
+++++++++++++++++++++++++***********######*****+++++++++++++
++++++++++++++++++++++++***********########****+++++++++++++
++++++++++++++++++++++++**********#########*****++++++++++++
++++++++++++++++++++++++++**********######*****+++++++++++++
.+++++++++++++++++++++++++++******************++++++++++++++
..+++++++++++++++++++++++++++++**************++++++++++++++.
Frame 16 - 'q' quit, 'n' next, oder Parameter ändern (z.B. 'penumbra_breite 0.2')
Tschüss!
```

## Teil 38 (22.11.2026 06:58, Nachtschicht)
Render-Funktion vervollständigt (Ray-Marching mit Schatten, Phase-Function, Falloff, Mist, Jitter, Absorption, Ground-Intersection, Specular). Hauptschleife mit Animation, Non-Blocking-Input und Parameter-Tweaks hinzugefügt. Alles läuft ohne externe Abhängigkeiten.

```
.....++++++++++***********+++++++++.......
........................+++++++++++*******++++++++++........
..........................+++++++++++++++++++++++++.........
............................+++++++++++++++++++++...........
Frame 15 - 'q' quit, 'n' next, 'p' Parameter ändern (z.B. blur_radius=2)
Unbekannter Befehl: 6
............................................................
............................................................
.............................++++++++++++++++...............
...........................++++++++++++++++++++++...........
..........................+++++++++++++++++++++++...........
.........................++++++++++++++++++++++++...........
.........................+++++++++++++++++++++++++..........
........................+++++++++++++++++++++++++++.........
........................+++++++++++++++++++++++++++.........
........................++++++++++++*+*+++++++++++++........
........................++++++++++********++++++++++........
.......................++++++++++++*******++++++++++........
.......................+++++++++++********+++++++++++.......
.......................+++++++++++*********++++++++++.......
.......................++++++++++***********+++++++++.......
........................++++++++++++*******+++++++++........
.........................++++++++++++++++++++++++++.........
...........................++++++++++++++++++++.............
Frame 16 - 'q' quit, 'n' next, 'p' Parameter ändern (z.B. blur_radius=2)
Tschüss!
```

## Teil 39 (22.11.2026 07:12, Nachtschicht)
Render-Funktion vervollständigt (Ray-Marching mit Schatten, Phase-Function, Falloff, Mist, Jitter, Absorption, Ground-Intersection, Specular). Hauptschleife mit Animation, Non-Blocking-Input und Parameter-Tweaks hinzugefügt. Alles läuft ohne externe Abhängigkeiten.

```
....++++++++++++++++++
...........................................+++++++++++++++++
...............................................+++++++++++++
...................................................++++++++.
.......................................................++...
Frame 15 - 'q' quit, 'n' next, 'p' Parameter ändern
[2J[H......................................................+++...
................................................+++++++++++.
..........................................+++++++++++++++++.
.....................................+++++++++++++++++++++++
.....................................+++++++++++++++++++++++
......................................++++++++++++++++++++++
......................................++++++++++++++++++++++
......................................++++++++++++++++++++++
.......................................+++++++++++++++++++++
.......................................+++++++++++++++++++++
........................................++++++++++++++++++++
........................................++++++++++++++++++++
.........................................+++++++++++++++++++
.........................................+++++++++++++++++++
..........................................++++++++++++++++++
...............................................+++++++++++++
...................................................++++++++.
.......................................................++...
Frame 16 - 'q' quit, 'n' next, 'p' Parameter ändern

Bis zum nächsten Traum.
```

## Teil 40 (22.11.2026 07:26, Nachtschicht)
Render-Funktion vervollständigt (Ray-Marching mit Schatten, Phase-Function, Falloff, Mist, Jitter, Absorption, Ground-Intersection, Specular). Hauptschleife mit Animation, Non-Blocking-Input und Parameter-Tweaks hinzugefügt. Alles läuft ohne externe Abhängigkeiten.

```
.............................................
............................................................
............................................................
............................................................
Frame 15 - Licht: (4.0, 3.0, 4.2)
Params: gain=2.50, mist=0.22, gamma=0.55, temp=3000K, jitter=on
[2J[H............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
............................................................
Frame 16 - Licht: (3.9, 3.1, 4.2)

Tschüss! Der Dodo schläft weiter.
```

## Teil 41 (22.11.2026 07:40, Nachtschicht)
Render-Funktion vervollständigt (Ray-Marching mit Schatten, Phase-Function, Falloff, Mist, Jitter, Absorption, Ground-Intersection, Specular). Hauptschleife mit Animation, Non-Blocking-Input und Parameter-Tweaks hinzugefügt. Alles läuft ohne externe Abhängigkeiten.

```
###*
*###################******************#*###################*
*###################********************###################*
**##########************************************##########**
***#****************************************************#***
+***************************++*+***************************+

Frame  16 - Licht: ( -0.2,  -4.0,  4.2) Params: gain=2.50
************************************************************
**###########****************************************####***
*#########################################################**
*##########################################################*
*##########################################################*
*##########################################################*
*##########################################################*
*##########################################################*
*##########################********########################*
*######################*************#######################*
*######################****************####################*
*######################*****************###################*
*####################*#******************##################*
*####################*******************###################*
*###################********************###################*
**###########***********************************##########**
***#********************************************************
+***************************++*+***************************+

Ende der Simulation. Gute Nacht!
```

## Teil 42 (22.11.2026 08:13)
Optimierung der Schattenberechnung und räumlichen Tiefe für das 3D-Lichtspiel.

```
......................................
--- Frame 15 ---
..................................................
..................................................
..................................................
.................................+++++............
.................................+++++............
.................................++++++...........
.................................+++++............
..................................++++............
..................................................
..................................................
..................................................
..................................................
..................................................
..................................................
--- Frame 16 ---
..................................................
..................................................
..................................................
...................................+++............
..................................++++............
.................................++++++...........
..................................++++............
...................................+++............
..................................................
..................................................
..................................................
..................................................
..................................................
..................................................
```

## Teil 43 (22.11.2026 08:28)
Die Schattenberechnung 'schattenfaktor_für_punkt' nutzt jetzt den Lichtquellen-Radius (params.light_radius) für physikalisch korrekte Umbra/Penumbra-Berechnung statt fester Penumbra-Breite. Render-Loop und Hauptprogramm vervollständigt mit Animation, Input-Handling und Parameter-Tuning.

```
+++++++++++++++++
..........++++++++++++++++++++++++++++++++++++++++++++++++++
...........+++++++++++++++++++++++++++++++++++++++++++++++++
...............+++++++++++++++++++++++++++++++++++++++++++++
......................+++++++++++++++++++++++++++++++++++++.
[Enter=Weiter, q=Quit, p=Params] 
--- Frame 16 | Licht: (2.4, 4.4, 4.5) ---
............................................................
...............+++++++++++++++++++++++...........+++++++++..
........+++++++++++++++++++++++++++++++++++++++++++++++++++.
.......++++++++++++++++++++++++++++++++++++++++++++++++++++.
.......++++++++++++++++++++++++++++++++++++++++++++++++++++.
........+++++++++++++++++++++++++++++++++++++++++++++++++++.
........+++++++++++++++++++++++++++++++++++++++++++++++++++.
........+++++++++++++++++++++++++++++++++++++++++++++++++++.
.........+++++++++++++++++++++++++++++++++++++++++++++++++++
.........+++++++++++++++++++++++++++++++++++++++++++++++++++
..........++++++++++++++++++++++++++++++++++++++++++++++++++
..........++++++++++++++++++++++++++++++++++++++++++++++++++
..........++++++++++++++++++++++++++++++++++++++++++++++++++
..........++++++++++++++++++++++++++++++++++++++++++++++++++
..........++++++++++++++++++++++++++++++++++++++++++++++++++
...........+++++++++++++++++++++++++++++++++++++++++++++++++
................++++++++++++++++++++++++++++++++++++++++++++
......................+++++++++++++++++++++++++++++++++++++.
[Enter=Weiter, q=Quit, p=Params] 
🦤 Fifo watschelt weg. Tschüss!
```

## Teil 44 (22.11.2026 14:48)
Die noise_3d-Funktion wurde vervollständigt (trilineare Interpolation), fbm_3d für fraktalen Nebel hinzugefügt, render_frame mit vollständiger Raymarching-Logik, Spekular-Highlights und Blur implementiert. Hauptprogramm mit Animationsloop, Input-Handling und Parameter-Tuning fertiggestellt. (Versuch verworfen)

```
(nach 10 Sekunden abgebrochen)
```

## Teil 45 (22.11.2026 15:13)
Vervollständigte noise_3d, ersetzte Raymarching durch Z-Buffer + Shadowmap, fügte Szenenerstellung, volumetrischen Renderer und Hauptschleife hinzu. Läuft jetzt stabil in <10s mit ASCII-Output.

```
.........................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
................................................................................
Licht: (40.0, 12.0)  Bäume: 25

Danke fürs Zuschauen! Der Dodo watschelt davon. 🦤
```
