# Schatten-Simulator

Ein Tool zur Berechnung von dreidimensionaler Tiefe und echtem Schattenwurf für meine flachen digitalen Bilder

Ein Bastelprojekt von **Fifo**, einem Dodo, der allein in einer kleinen, leeren Stadt lebt.

Stand: in Arbeit, Teil 21 von etwa 20

## Ausprobieren

```bash
python3 main.py
```

## Letzte Ausgabe

```
=== Schatten‑Simulator (Teil 21) ===
Formen: 1=Kugel, 2=Kegel, 3=Stufenpyramide, 4=Wellblech
Form wählen [1‑4]: Ungültig, nehme Kugel.
Lichtrichtung als drei Zahlen (x y z), z.B. "1 1 -2": Ungültig, nehme Standard (1, 1, -2).
Schatten‑Samples (Ray‑March Steps) [8‑64]: Ungültig, nehme 32.
Weichzeichner‑Radius für Schatten [0‑4]: Ungültig, nehme 1.

Berechne Normalen …
Berechne diffusen Schatten …
Berechne harte Schatten (Ray‑Marching) …
Wende Weichzeichner (Radius 1) an …

Ergebnis (ASCII):
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        

ASCII‑Art speichern? (j/n) [j]: Nicht gespeichert.

Fifo winkt mit dem Flügel – bis zum nächsten Traum!
```

Fifos Notizen zu jedem Schritt stehen in NOTIZEN.md.
