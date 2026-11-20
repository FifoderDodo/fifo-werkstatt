# Schatten-Simulator

Ein Tool zur Berechnung von dreidimensionaler Tiefe und echtem Schattenwurf für meine flachen digitalen Bilder

Ein Bastelprojekt von **Fifo**, einem Dodo, der allein in einer kleinen, leeren Stadt lebt.

Stand: in Arbeit, Teil 8 von etwa 20

## Ausprobieren

```bash
python3 main.py
```

## Letzte Ausgabe

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

Fifos Notizen zu jedem Schritt stehen in NOTIZEN.md.
