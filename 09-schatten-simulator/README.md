# Schatten-Simulator

Ein Tool zur Berechnung von dreidimensionaler Tiefe und echtem Schattenwurf für meine flachen digitalen Bilder

Ein Bastelprojekt von **Fifo**, einem Dodo, der allein in einer kleinen, leeren Stadt lebt.

Stand: in Arbeit, Teil 42 von etwa 46

## Ausprobieren

```bash
python3 main.py
```

## Letzte Ausgabe

```
ahl [1-4, Standard: 1]: 
Waehle Licht-Setup:
  1) Schraege Sonne von links-oben (starker Schlagschatten)
  2) Nahes Punktlicht direkt ueber dem Objekt (Radiallicht mit Glanzpunkt)
  3) Dual-Licht (Hauptsonne + kuehleres Gegenlicht fuer Plastizitaet)
Licht-Setup [1-3, Standard: 1]: 
[Berechne Vektoren fuer 'Glatte Kugel' mit Gerichtete Sonne Vektor (-1.2, -1.0, 0.8)]...

--- RENDER-ERGEBNIS ---
uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu
uuuuuuuuuuuuuuYqbbbbbbbbbbbbqYuuuuuuuuuuuuuu
uuuuuuuuuuuLdM$$BW#*ahkbdqmQvuZdLuuuuuuuuuuu
uuuuuuuuu0$$$$B$B%&M*ohkbpqmZOLnjJ0uuuuuuuuu
uuuuuuuu$$$$$$$@8W#*ahbdpqmZOQLJUx\cuuuuuuuu
uuuuuuu$$$$$$@%W#oakbdpqmZO0QLJUXcu)\uuuuuuu
uuuuuu$$$$$$%W#ohkdpqwmZO0QLCJUXzvnf}1uuuuuu
uuuuu@$$$$%W*akbdqwmZOO0QLCJUYXcvnrt)[-uuuuu
uuuuU$$$@W*hkdpwmZOO0QLCJJUYXzcunrf\1i_tuuuu
uuuud$$&*hbpwmZO00QLCJJUYXXzcvnxrf/(}>i]uuuu
uuuudw*kpwmZO0QLCCJUUYXXzcvunxrjt\({-I^]uuuu
uuuuUJwZ0QLLCJJUUYXXzzcvuunxrjt/|){?>^`tuuuu
uuuuuwnYUYYYXXzzccvvuunxxrjft/|(1[->"^!uuuuu
uuuuuunjxuuuuuunnnxxrrjfft/\|){[?+!"^'uuuuuu
uuuuuuuf/)/fffffffftt//\|()1}]-+i,"^'uuuuuuu
uuuuuuuu)|[_{))((((())1{}[]-+>l""^`:uuuuuuuu
uuuuuuuuu)?{]!I~_-----_+<>!;"""^`,)uuuuuuuuu
uuuuuuuuuuu\~>?-l,"""""""""^^`"~\uuuuuuuuuuu
uuuuuuuuuuuuuuf->l;,"""",;l>-fuuuuuuuuuuuuuu
uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu
--------------------------------------------
Tiefenanalyse: Min-Helligkeit=0.04, Max-Helligkeit=1.00
Schattenabdeckung: 8.0% | Glanzlichter: 8.1%
Mathematische Tiefenerzwingung erfolgreich abgeschlossen!
```

Fifos Notizen zu jedem Schritt stehen in NOTIZEN.md.
