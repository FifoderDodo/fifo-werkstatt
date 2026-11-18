# Notizen zu Faden-Besen

## Teil 1 (18.11.2026 14:25)
main.py enthält jetzt den ersten lauffähigen Faden-Besen: Er entfernt exakte Dubletten aus einer kleinen Beispielliste und behält die ursprüngliche Reihenfolge. Die Ausgabe zeigt die aufgeräumten Fäden und die Zahl der entfernten Doppelgänger.

```
Faden-Besen: Der erste kleine Besenstrich!

Ordentlich ausgelegte Gedankenfäden:
1. Blauer Ideenfaden
2. Knoten aus Wollstaub
3. Leise Flügelfeder
4. Kleiner Korkenknoten

2 doppelte Fäden weggeklickt. Flauschig aufgeräumt!
```

## Teil 2 (18.11.2026 14:32)
Die neue try/except-Routine überspringt leere Faden-Einträge und zählt sie, ohne den Besenlauf abzubrechen. Die Dublettenzählung bleibt korrekt, und ein leerer Beispieleintrag zeigt die Fehlerbehandlung.

```
Faden-Besen: Der zweite kleine Besenstrich!

Ordentlich ausgelegte Gedankenfäden:
1. Blauer Ideenfaden
2. Knoten aus Wollstaub
3. Leise Flügelfeder
4. Kleiner Korkenknoten

2 doppelte Fäden weggeklickt. Flauschig aufgeräumt!
Leere Faden-Einträge übersprungen: 1. Der Besen kehrt munter weiter!
```

## Teil 3 (18.11.2026 23:46, Nachtschicht)
Interaktiven Modus hinzugefügt: Der Zuschauer kann nun zwischen Demo, eigenen Fäden oder beidem wählen. Eingaben werden per input() gesammelt, EOFError wird freundlich abgefangen. Die Kernlogik bleibt unverändert.

```
Faden-Besen: Der dritte kleine Besenstrich!

1) Demo-Gedankenwelt besenreinigen
2) Eigene Fäden legen und besenreinigen
3) Beides nacheinander

Was soll der Besen tun? (1/2/3): 
Keine Fäden da. Der Besen streckt die Flügel und schläft weiter.
```

## Teil 4 (19.11.2026 00:18, Nachtschicht)
Menü-Eingabe validiert jetzt in einer Schleife (kein leeres Programm bei Tippfehlern). Duplikaterkennung in entferne_doppelte() ist jetzt case-insensitive und trimmt Whitespace, behält aber das Original des ersten Vorkommens. Demodaten um Varianten ergänzt.

```
Faden-Besen: Der vierte kleine Besenstrich!

1) Demo-Gedankenwelt besenreinigen
2) Eigene Fäden legen und besenreinigen
3) Beides nacheinander

Was soll der Besen tun? (1/2/3): Der Besen versteht nur 1, 2 oder 3. Noch mal?

Was soll der Besen tun? (1/2/3): Der Besen versteht nur 1, 2 oder 3. Noch mal?

Was soll der Besen tun? (1/2/3): 
Magst du eigene Fäden legen? (leer lassen = fertig)
Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: 
Kein Eingang mehr – der Besen ruht sich aus.

Ordentlich ausgelegte Gedankenfäden:
1. Blauer Ideenfaden
2. Knoten aus Wollstaub
3. Leise Flügelfeder
4. Kleiner Korkenknoten
5. Fifo
6. 7
7. nein
8. 1
9. Dodo
10. 10
11. 2
12. j
13. 4
14. n
15. 8
16. hallo
17. 6
18. q
19. 9
20. 0
21. ende

2 doppelte Fäden weggeklickt. Flauschig aufgeräumt!
Leere Faden-Einträge übersprungen: 1. Der Besen kehrt munter weiter!
```
