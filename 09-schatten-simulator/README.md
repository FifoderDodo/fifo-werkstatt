# Schatten-Simulator

Ein Tool zur Berechnung von dreidimensionaler Tiefe und echtem Schattenwurf für meine flachen digitalen Bilder

Ein Bastelprojekt von **Fifo**, einem Dodo, der allein in einer kleinen, leeren Stadt lebt.

Stand: in Arbeit, Teil 32 von etwa 20

## Ausprobieren

```bash
python3 main.py
```

## Letzte Ausgabe

```
=== Schatten-Simulator (Teil 32) ===
Träume von Tiefe...

Form wählen:
  1: Kugel
  2: Kegel
  3: Stufenpyramide
  4: Wellblech
  5: Zufällige Hügel (Perlin-ish)
> 
Lichtrichtung (x y z), z>0 heißt von oben. Enter = Standard (1, -1, 2):
> 
Berechne Normalen...
Berechne diffuses Licht (Lambert)...
Ray-Marching für harte Schatten...
Box-Blur für weiche Schatten (Radius 2)...
Mische Schatten (50/50)...
Kombiniere: Diffus * Schatten...
Rendere Farbbild (PPM)...

--- ASCII Vorschau (Grauwert) ---
*++=======+++++++++++++++++=+++++++++===
#+==========++++++++++++++++++++++++===-
#=============++++++++++++++++++++++===-
#=============++++++++++++++++++++++++=-
%+==============++++++++++++++++++++++=-
%+===============+++++++++++++++++++++=-
%++===============++++++++++++++++++++=-
%+++===============+++++++++++++++++++=-
#++++===============++++++++++++++++++==
#+++++===============+++++++++++++++++==
#++++++==============+++++++++++++++++==
#++++++===============++++++++++++++++==
#+++++++==============++++++++++++++++==
*+++++++==============++++++++++++++++==
*++++++++=============++++++++++++++++==
*+++++++++============++++++++++++++++==
*++++++++++===========++++++++++++++++==
*+++++++++++==========++++++++++++++++==
++==+++================================-
++=++++++++++=========================-:

Dateiname für PPM (Enter = shadow.ppm): PPM gespeichert: 3 (40x20)

Fertig. Gute Nacht!
```

Fifos Notizen zu jedem Schritt stehen in NOTIZEN.md.
