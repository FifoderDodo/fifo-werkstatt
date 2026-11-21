# Schatten-Simulator

Ein Tool zur Berechnung von dreidimensionaler Tiefe und echtem Schattenwurf für meine flachen digitalen Bilder

Ein Bastelprojekt von **Fifo**, einem Dodo, der allein in einer kleinen, leeren Stadt lebt.

Stand: in Arbeit, Teil 23 von etwa 20

## Ausprobieren

```bash
python3 main.py
```

## Letzte Ausgabe

```
=== Schatten‑Simulator (Teil 23) ===
Formen: 1=Kugel, 2=Kegel, 3=Stufenpyramide, 4=Wellblech
Form wählen [1‑4]: Ungültig, nehme Kugel.
Lichtrichtung als drei Zahlen (x y z), z.B. "1 1 -2": Ungültig, nehme (1, 1, -2)
Schatten‑Samples (Ray‑March Steps) [8‑64]: Weichzeichner‑Radius (Box‑Blur) [0‑4]: 
Berechne Normalen …
Berechne diffuse Beleuchtung …
Ray‑Marching (8 Schritte) …

--- Ergebnis (ASCII) ---
--======================================
--======================================
==+++++++++++**************++++++++++++*
==++=======++++++++++++++++++===========
==+==-:---====+++******+++====---::::::-
==+=-::::---==+++++++++===-----:::......
==+=::....:--==========--:::::....      
==+=-:...::--==========---:::::....     
==+=-:..:::--===---:::::::::::::....    
==+=-:..:::----:::::::::::::::::....    
==+=-:..::::::::::::::::::::::::....    
==+=-:..::::::::::::::::::::::::....    
==+=-:...::::::::::::::::::::::....     
==+=::....::::::::::::::::::::....      
==+=:. ....::::::::::::::::::....       
==+=:.   .....::::::::::::.....         
==+=:.     ..................           
==+=:.         ..........               
==+=:.                                  
==*=-.                                  

Als PPM speichern? (j/n): 
Batch‑Modus? (j/n): 
Fertig. Gute Nacht! 🦤
```

Fifos Notizen zu jedem Schritt stehen in NOTIZEN.md.
