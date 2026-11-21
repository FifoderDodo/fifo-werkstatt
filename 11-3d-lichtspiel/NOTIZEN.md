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
