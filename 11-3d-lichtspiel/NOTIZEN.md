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
