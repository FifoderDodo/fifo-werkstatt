# Schatten-Simulator

Ein Tool zur Berechnung von dreidimensionaler Tiefe und echtem Schattenwurf für meine flachen digitalen Bilder

Ein Bastelprojekt von **Fifo**, einem Dodo, der allein in einer kleinen, leeren Stadt lebt.

Stand: in Arbeit, Teil 22 von etwa 20

## Ausprobieren

```bash
python3 main.py
```

## Letzte Ausgabe

```
=== Schatten‑Simulator (Teil 22) ===
Formen: 1=Kugel, 2=Kegel, 3=Stufenpyramide, 4=Wellblech
Form wählen [1‑4]: Ungültig, nehme Kugel.
Lichtrichtung als drei Zahlen (x y z), z.B. "1 1 -2": Schatten‑Samples (Ray‑March Steps) [8‑64]: Weichzeichner‑Radius (Box‑Blur) [0‑4]: 
Berechne Normalen …
Berechne diffuse Beleuchtung …
Berechne harte Schatten (Ray‑Marching) …
Wende Weichzeichner an …

=== Ergebnis (diffus * weicher Schatten) ===
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
In Datei speichern? (j/n) [n]: Batch‑Modus für alle Formen? (j/n) [n]: 
Fertig. Gute Nacht!
```

Fifos Notizen zu jedem Schritt stehen in NOTIZEN.md.
