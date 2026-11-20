# Schatten-Simulator

Ein Tool zur Berechnung von dreidimensionaler Tiefe und echtem Schattenwurf für meine flachen digitalen Bilder

Ein Bastelprojekt von **Fifo**, einem Dodo, der allein in einer kleinen, leeren Stadt lebt.

Stand: in Arbeit, Teil 7 von etwa 20

## Ausprobieren

```bash
python3 main.py
```

## Letzte Ausgabe

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

Fifos Notizen zu jedem Schritt stehen in NOTIZEN.md.
