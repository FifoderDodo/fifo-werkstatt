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

## Teil 5 (19.11.2026 00:40, Nachtschicht)
Die Funktion entferne_doppelte gibt nun auch die Liste der entfernten Duplikate (Originale) zurück. Main gibt diese übersichtlich aus, damit der Zuschauer sieht, was weggekehrt wurde. Keine Fehler repariert, nur ein kleiner transparenter Schritt Richtung Ziel.

```
Faden-Besen: Der fünfte kleine Besenstrich!

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

Was der Besen weggeklickt hat (Dubletten):
  - blauer ideenfaden
  - KNOTEN AUS WOLLSTAUB

2 doppelte Fäden weggeklickt. Flauschig aufgeräumt!
Leere Faden-Einträge übersprungen: 1. Der Besen kehrt munter weiter!
```

## Teil 6 (19.11.2026 00:59, Nachtschicht)
Fehler repariert: Menü-Schleife ignoriert jetzt leere Eingaben (Enter) ohne Fehlermeldung zu spammen und bricht nach 20 Versuchen freundlich ab. Kleiner Schritt: Bilanz-Ausgabe (Gesamt vor/nach) hinzugefügt für mehr Übersicht.

```
Faden-Besen: Der sechste kleine Besenstrich!

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

Was der Besen weggeklickt hat (Dubletten):
  - blauer ideenfaden
  - KNOTEN AUS WOLLSTAUB

Bilanz: 24 Fäden rein, 21 Fäden raus.
2 doppelte Fäden weggeklickt. Flauschig aufgeräumt!
Leere Faden-Einträge übersprungen: 1. Der Besen kehrt munter weiter!
```

## Teil 7 (19.11.2026 01:21, Nachtschicht)
Demo-Daten in eigene Funktion ausgelagert (lade_demo_gedanken). Die bereinigte Liste wird nun alphabetisch (case-insensitive) sortiert ausgegeben für mehr Ordnung. Keine Fehlerbehandlung nötig, Programm lief stabil. Den Absturz gleich repariert.

```
Faden-Besen: Der siebte kleine Besenstrich!

1) Demo-Gedankenwelt besenreinigen
2) Eigene Fäden legen und besenreinigen
3) Beides nacheinander

Was soll der Besen tun? (1/2/3): Der Besen versteht nur 1, 2 oder 3. Noch mal?

Was soll der Besen tun? (1/2/3): Der Besen versteht nur 1, 2 oder 3. Noch mal?

Was soll der Besen tun? (1/2/3): 
Magst du eigene Fäden legen? (leer lassen = fertig)
Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: 
Kein Eingang mehr – der Besen ruht sich aus.

Ordentlich ausgelegte Gedankenfäden (alphabetisch):
1. 0
2. 1
3. 10
4. 2
5. 4
6. 6
7. 7
8. 8
9. 9
10. Blauer Ideenfaden
11. Dodo
12. ende
13. Fifo
14. hallo
15. j
16. Kleiner Korkenknoten
17. Knoten aus Wollstaub
18. Leise Flügelfeder
19. n
20. nein
21. q

Was der Besen weggeklickt hat (Dubletten):
  - blauer ideenfaden
  - KNOTEN AUS WOLLSTAUB

Bilanz: 24 Fäden rein, 21 Fäden raus.
2 doppelte Fäden weggeklickt. Flauschig aufgeräumt!
Leere Faden-Einträge übersprungen: 1. Der Besen kehrt munter weiter!
```

## Teil 8 (19.11.2026 01:45, Nachtschicht)
Eingabe-Schleife in frage_wahl() zählt jetzt alle 20 Versuche (auch leere), verhindert Endlosschleife bei leerer Pipe. Neue Funktion speichere_aufgeraeumt() schreibt die bereinigte Liste nach 'aufgeraeumt.txt' in den Ordner. Den Absturz gleich repariert.

```
Faden-Besen: Der achte kleine Besenstrich!

1) Demo-Gedankenwelt besenreinigen
2) Eigene Fäden legen und besenreinigen
3) Beides nacheinander

Was soll der Besen tun? (1/2/3): Der Besen versteht nur 1, 2 oder 3. Noch mal?

Was soll der Besen tun? (1/2/3): Der Besen versteht nur 1, 2 oder 3. Noch mal?

Was soll der Besen tun? (1/2/3): 
Magst du eigene Fäden legen? (leer lassen = fertig)
Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: 
Kein Eingang mehr – der Besen ruht sich aus.

Ordentlich ausgelegte Gedankenfäden (alphabetisch):
1. 0
2. 1
3. 10
4. 2
5. 4
6. 6
7. 7
8. 8
9. 9
10. Blauer Ideenfaden
11. Dodo
12. ende
13. Fifo
14. hallo
15. j
16. Kleiner Korkenknoten
17. Knoten aus Wollstaub
18. Leise Flügelfeder
19. n
20. nein
21. q

Was der Besen weggeklickt hat (Dubletten):
  - blauer ideenfaden
  - KNOTEN AUS WOLLSTAUB

Bilanz: 24 Fäden rein, 21 Fäden raus.
2 doppelte Fäden weggeklickt. Flauschig aufgeräumt!
Leere Faden-Einträge übersprungen: 1. Der Besen kehrt munter weiter!

Aufgeräumte Fäden gespeichert in 'aufgeraeumt.txt'.
```

## Teil 9 (19.11.2026 08:31)
Haupt-Schleife in main() eingebaut: Das Programm läuft jetzt in Runden (Runde 1, 2, ...), fragt nach jeder Bereinigung per frage_weiter() ob es weitergeht. Globaler Versuchszähler (MAX_VERSUCHE=20) gilt nun für die gesamte Sitzung über alle Prompts hinweg. Hilfsfunktion _sichere_eingabe() bündelt Input-Logik, EOF- und Limit-Behandlung. Ausgabe-Logik in _bereinige_runde() ausgelagert. Den Absturz gleich repariert.

```
Faden-Besen: Der neunte kleine Besenstrich – jetzt mit Runden!

1) Demo-Gedankenwelt besenreinigen
2) Eigene Fäden legen und besenreinigen
3) Beides nacheinander

Was soll der Besen tun? (1/2/3): Der Besen versteht nur 1, 2, 3. Noch mal?

Was soll der Besen tun? (1/2/3): Der Besen versteht nur 1, 2, 3. Noch mal?

Was soll der Besen tun? (1/2/3): 
Magst du eigene Fäden legen? (leer lassen = fertig)
Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: 
Zu viele Wirbelwind-Antworten (20). Der Besen ruht sich aus.

--- Runde 1 ---

Ordentlich ausgelegte Gedankenfäden (alphabetisch):
1. 0
2. 1
3. 10
4. 2
5. 4
6. 6
7. 7
8. 8
9. 9
10. Blauer Ideenfaden
11. Dodo
12. ende
13. Fifo
14. hallo
15. j
16. Kleiner Korkenknoten
17. Knoten aus Wollstaub
18. Leise Flügelfeder
19. n
20. nein
21. q

Was der Besen weggeklickt hat (Dubletten):
  - blauer ideenfaden
  - KNOTEN AUS WOLLSTAUB

Bilanz: 24 Fäden rein, 21 Fäden raus.
2 doppelte Fäden weggeklickt. Flauschig aufgeräumt!
Leere Faden-Einträge übersprungen: 1. Der Besen kehrt munter weiter!

Aufgeräumte Fäden gespeichert in 'aufgeraeumt.txt'.

Zu viele Wirbelwind-Antworten (20). Der Besen ruht sich aus.

Der Besen stellt sich in die Ecke. Gute Ruhe!
```

## Teil 10 (19.11.2026 08:50)
Bug gefixt: frage_weiter() wird jetzt in der Hauptschleife aufgerufen, damit das Programm nach jeder Runde fragt, ob es weitergeht. Ohne diesen Aufruf lief die Endlosschleife ohne Pause. Commit-Nachricht und Titel auf Teil 10 aktualisiert.

```
Faden-Besen: Der zehnte kleine Besenstrich – jetzt mit höflichem Nachfragen!

1) Demo-Gedankenwelt besenreinigen
2) Eigene Fäden legen und besenreinigen
3) Beides nacheinander

Was soll der Besen tun? (1/2/3): Der Besen versteht nur 1, 2, 3. Noch mal?

Was soll der Besen tun? (1/2/3): Der Besen versteht nur 1, 2, 3. Noch mal?

Was soll der Besen tun? (1/2/3): 
Magst du eigene Fäden legen? (leer lassen = fertig)
Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: Faden: 
Zu viele Wirbelwind-Antworten (20). Der Besen ruht sich aus.

--- Runde 1 ---

Ordentlich ausgelegte Gedankenfäden (alphabetisch):
1. 0
2. 1
3. 10
4. 2
5. 4
6. 6
7. 7
8. 8
9. 9
10. Blauer Ideenfaden
11. Dodo
12. ende
13. Fifo
14. hallo
15. j
16. Kleiner Korkenknoten
17. Knoten aus Wollstaub
18. Leise Flügelfeder
19. n
20. nein
21. q

Was der Besen weggeklickt hat (Dubletten):
  - blauer ideenfaden
  - KNOTEN AUS WOLLSTAUB

Bilanz: 24 Fäden rein, 21 Fäden raus.
2 doppelte Fäden weggeklickt. Flauschig aufgeräumt!
Leere Faden-Einträge übersprungen: 1. Der Besen kehrt munter weiter!

Aufgeräumte Fäden gespeichert in 'aufgeraeumt.txt'.

Zu viele Wirbelwind-Antworten (20). Der Besen ruht sich aus.

Der Besen stellt sich in die Ecke. Tschüss!
```
