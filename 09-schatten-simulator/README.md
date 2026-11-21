# Schatten-Simulator

Ein Tool zur Berechnung von dreidimensionaler Tiefe und echtem Schattenwurf für meine flachen digitalen Bilder

Ein Bastelprojekt von **Fifo**, einem Dodo, der allein in einer kleinen, leeren Stadt lebt.

Stand: in Arbeit, Teil 19 von etwa 20

## Ausprobieren

```bash
python3 main.py
```

## Letzte Ausgabe

```
=== Schatten‑Simulator (Teil 19) ===
Formen: 1=Kugel, 2=Kegel, 3=Stufenpyramide, 4=Wellblech
Form wählen [1‑4]: Ungültig, nehme Kugel.
Lichtrichtung als drei Zahlen (x y z), z.B. "1 1 -2":
> Ungültig, nehme Standard (1, 1, -2).
Schatten‑Samples (Ray‑March Steps) [8‑64, Standard 32]:
> Weichzeichner‑Radius für weiche Schatten [0‑5, Standard 2]:
> Berechne Normalen …
Diffuse Beleuchtung …
Harte Schatten (Ray‑March) …
Weiche Schatten …
SSAO …
Blinn‑Phong Shading …
ASCII‑Art …
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                        

Fertig. Drücke Enter für Ende.
```

Fifos Notizen zu jedem Schritt stehen in NOTIZEN.md.
