# Schatten-Simulator

Ein Tool zur Berechnung von dreidimensionaler Tiefe und echtem Schattenwurf für meine flachen digitalen Bilder

Ein Bastelprojekt von **Fifo**, einem Dodo, der allein in einer kleinen, leeren Stadt lebt.

Stand: in Arbeit, Teil 20 von etwa 20

## Ausprobieren

```bash
python3 main.py
```

## Letzte Ausgabe

```
=== Schatten‑Simulator (Teil 20) ===
Formen: 1=Kugel, 2=Kegel, 3=Stufenpyramide, 4=Wellblech
Form wählen [1‑4]: Ungültig, nehme Kugel.
Lichtrichtung als drei Zahlen (x y z), z.B. "1 1 -2": Ungültig, nehme Standard (1, 1, -2).
Schatten‑Samples (Ray‑March Steps) [8‑64]: Weichzeichner‑Radius für Schatten [0‑3]: AO‑Samples [4‑16]: 
Berechne Normalen...
Berechne diffuse Beleuchtung...
Ray‑Marching harte Schatten (8 Schritte)...
Weiche Schatten (Radius 1)...
Ambient Occlusion (7 Samples)...
Blinn‑Phong Specular...
Rendere ASCII...
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
ASCII in Datei speichern? (Dateiname oder Enter zum Überspringen): Gespeichert unter nein

Fertig. Gute Nacht, kleiner Dodo.
```

Fifos Notizen zu jedem Schritt stehen in NOTIZEN.md.
