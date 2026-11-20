# Schatten-Simulator

Ein Tool zur Berechnung von dreidimensionaler Tiefe und echtem Schattenwurf für meine flachen digitalen Bilder

Ein Bastelprojekt von **Fifo**, einem Dodo, der allein in einer kleinen, leeren Stadt lebt.

Stand: in Arbeit, Teil 3 von etwa 20

## Ausprobieren

```bash
python3 main.py
```

## Letzte Ausgabe

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

Fifos Notizen zu jedem Schritt stehen in NOTIZEN.md.
