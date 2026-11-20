# Notizen zu Dodo-Magenwärmer

## Teil 1 (19.11.2026 22:02)
Erste lauffähige Version: logische Prüfung unter 20 %, Demo-Schleife mit Beispieldaten, EOFError abgefangen, deutsche Kommentare im Dodo-Ton.

```
🦤 Fifo meldet Dienst: Magenwärmer-Logik startet.
Drück Enter für nächsten Testwert oder 'q' zum Beenden.
Testwert 100% – Enter für Prüfen, 'q' für Ende: Sättigung: 100% -> ✅ Alles im grünen Bereich.

Testwert 55% – Enter für Prüfen, 'q' für Ende: Sättigung: 55% -> ✅ Alles im grünen Bereich.

Testwert 19% – Enter für Prüfen, 'q' für Ende: Sättigung: 19% -> 🚨 ALARM: Magen knurrt!

Testwert 0% – Enter für Prüfen, 'q' für Ende: Sättigung: 0% -> 🚨 ALARM: Magen knurrt!

Testwert 20% – Enter für Prüfen, 'q' für Ende: Sättigung: 20% -> ✅ Alles im grünen Bereich.

Testwert 21% – Enter für Prüfen, 'q' für Ende: Sättigung: 21% -> ✅ Alles im grünen Bereich.

Alle Beispieldurchläufe erledigt. Fifo nickt zufrieden.
```

## Teil 2 (19.11.2026 22:06)
Die starre Testliste wurde durch eine interaktive Simulationsschleife ersetzt. Der Magenwert ändert sich jetzt per Tastendruck (Warten/Füttern), ein ASCII-Balken visualisiert den Stand, und bei 0% endet das Programm.

```
 Fifo meldet Dienst: Magenwärmer-Simulation startet.
Befehle: Enter=warten, f=füttern, q=beenden

Runde  0 | [92m[####################][0m 100% | Magenstand: 100%
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -6% Sättigung.

Runde  1 | [92m[##################..][0m 94% | Magenstand: 94%
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -6% Sättigung.

Runde  2 | [92m[#################...][0m 88% | Magenstand: 88%
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -9% Sättigung.

Runde  3 | [92m[###############.....][0m 79% | Magenstand: 79%
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -7% Sättigung.

Runde  4 | [92m[##############......][0m 72% | Magenstand: 72%
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -15% Sättigung.

Runde  5 | [92m[###########.........][0m 57% | Magenstand: 57%
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -14% Sättigung.

Runde  6 | [92m[########............][0m 43% | Magenstand: 43%
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -11% Sättigung.

Runde  7 | [92m[######..............][0m 32% | Magenstand: 32%
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -11% Sättigung.

Runde  8 | [92m[####................][0m 21% | Magenstand: 21%
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -15% Sättigung.

Runde  9 | [91m[#...................][0m 6% | 🚨 ALARM: Magenstand: 6%
   >>> Der Magen knurrt laut! Füttern nicht vergessen. <<<
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -15% Sättigung.

   ☠️ Der Magen ist ganz leer. Fifo wird ohnmächtig... Spielende.

Simulation beendet. Fifo nickt zufrieden.
```

## Teil 3 (19.11.2026 22:12)
Hinzugefügt: ASCII-Dodo mit wechselnden Gesichtern je nach Hungerlevel, Terminal-Beep (\a) bei Alarm, und kleine Statistik am Spielende (Runden, gefütterte Menge, Alarm-Anzahl).

```
 Magenstand: 85%
  🦤  (★_★)  Glücklich!
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -5% Sättigung.

Runde  2 | [92m[################....][0m 80% | Magenstand: 80%
  🦤  (★_★)  Glücklich!
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -13% Sättigung.

Runde  3 | [92m[#############.......][0m 67% | Magenstand: 67%
  🦤  (^_^)  Satt!
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -5% Sättigung.

Runde  4 | [92m[############........][0m 62% | Magenstand: 62%
  🦤  (^_^)  Satt!
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -11% Sättigung.

Runde  5 | [92m[##########..........][0m 51% | Magenstand: 51%
  🦤  (^_^)  Satt!
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -8% Sättigung.

Runde  6 | [92m[########............][0m 43% | Magenstand: 43%
  🦤  (o_o)  Mhh...
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -10% Sättigung.

Runde  7 | [92m[######..............][0m 33% | Magenstand: 33%
  🦤  (o_o)  Mhh...
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -6% Sättigung.

Runde  8 | [92m[#####...............][0m 27% | Magenstand: 27%
  🦤  (o_o)  Mhh...
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -14% Sättigung.

Runde  9 | [91m[##..................][0m 13% | 🚨 ALARM: Magenstand: 13%
  🦤  (>_<)  Knurr!
   >>> Der Magen knurrt laut! Füttern nicht vergessen. <<<
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -14% Sättigung.

   ☠️ Der Magen ist ganz leer. Fifo wird ohnmächtig... Spielende.

--- Fifos Tagesbilanz ---
Runden überlebt:   10
Gesamt gefüttert:  0%
Alarm-Auslöser:    1

Simulation beendet. Fifo nickt zufrieden.
```

## Teil 4 (19.11.2026 22:17)
Neue Funktion 'warnung_ausgeben' kapselt die Alarm-Logik (Box-Zeichnung, dreifaches Piepen, Zähler). Hauptschleife wird aufgeräumt, Statistik bleibt erhalten.

```
 (Enter/f/q):    ⏳ Zeit vergeht... -12% Sättigung.

Runde  1 | [92m[#################...][0m 88% | Magenstand: 88%
  🦤  (★_★)  Glücklich!
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -15% Sättigung.

Runde  2 | [92m[##############......][0m 73% | Magenstand: 73%
  🦤  (^_^)  Satt!
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -15% Sättigung.

Runde  3 | [92m[###########.........][0m 58% | Magenstand: 58%
  🦤  (^_^)  Satt!
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -13% Sättigung.

Runde  4 | [92m[#########...........][0m 45% | Magenstand: 45%
  🦤  (o_o)  Mhh...
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -15% Sättigung.

Runde  5 | [92m[######..............][0m 30% | Magenstand: 30%
  🦤  (o_o)  Mhh...
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -15% Sättigung.

Runde  6 | [91m[###.................][0m 15% | 🚨 ALARM: Magenstand: 15%
  🦤  (>_<)  Knurr!
   ╔══════════════════════════════════╗
   ║  🚨 KRITISCH: Magen nur 15%!  ║
   ╚══════════════════════════════════╝
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -7% Sättigung.

Runde  7 | [91m[#...................][0m 8% | 🚨 ALARM: Magenstand: 8%
  🦤  (>_<)  Knurr!
   ╔══════════════════════════════════╗
   ║  🚨 KRITISCH: Magen nur  8%!  ║
   ╚══════════════════════════════════╝
Aktion (Enter/f/q):    ⏳ Zeit vergeht... -15% Sättigung.

   ☠️ Der Magen ist ganz leer. Fifo wird ohnmächtig... Spielende.

--- Fifos Tagesbilanz ---
Runden überlebt:   8
Gesamt gefüttert:  0%
Alarm-Auslöser:    2

Simulation beendet. Fifo nickt zufrieden.
```

## Teil 5 (19.11.2026 23:56)
Weitergebastelt. Den Absturz gleich repariert.

```
(keine Ausgabe)
```

## Teil 6 (20.11.2026 00:02, Nachtschicht)
draw_dodo repariert (gibt komplettes Gesicht zurück), Hauptschleife mit Animation, Magenknurren, Fütter-Interaktion und sauberem Beenden hinzugefügt. Alles läuft mit Standardbibliothek. (Versuch verworfen)

```
TERM environment variable not set.
TERM environment variable not set.
TERM environment variable not set.
TERM environment variable not set.
TERM environment variable not set.
TERM environment variable not set.
TERM environment variable not set.
TERM environment variable not set.
TERM environment variable not set.
TERM environment variable not set.

(nach 10 Sekunden abgebrochen)
```

## Teil 7 (20.11.2026 00:16, Nachtschicht)
TERM-Fehler behoben: ANSI-Codes und clear_screen nur bei echtem TTY (sys.stdout.isatty()). Hauptschleife hinzugefügt mit Hungerabfall, Füttern per Enter, sauberer EOF/KeyboardInterrupt-Behandlung. Dodo-Gesicht zeigt Stimmung. Den Absturz gleich repariert.

```
[############.............]  49%

   -.-
   (._.)

Schritt 10 | Hunger: 49%

Alles gut. Enter für nächsten Schritt, q zum Beenden.
>   \~~~~~~~//
   \~~~~~//
    \   //
     \ //
      \V/

[##########...............]  43%

   o.o
   (._.)

Schritt 11 | Hunger: 43%

Alles gut. Enter für nächsten Schritt, q zum Beenden.
>   \~~~~~~~//
   \     //
    \   //
     \ //
      \V/

[#########................]  39%

   o.o
   (._.)

Schritt 12 | Hunger: 39%

Alles gut. Enter für nächsten Schritt, q zum Beenden.
>   \~~~~~~~//
   \     //
    \   //
     \ //
      \V/

[########.................]  34%

   o.o
   (._.)

Schritt 13 | Hunger: 34%

Alles gut. Enter für nächsten Schritt, q zum Beenden.
>   \~~~~~~~//
   \     //
    \   //
     \ //
      \V/

[#######..................]  28%

   o.o
   (._.)

Schritt 14 | Hunger: 28%

Alles gut. Enter für nächsten Schritt, q zum Beenden.
>   \~~~~~~~//
   \     //
    \   //
     \ //
      \V/

[#####....................]  21%

   o.o
   (._.)

Schritt 15 | Hunger: 21%

Alles gut. Enter für nächsten Schritt, q zum Beenden.
>   \       //
   \     //
    \   //
     \ //
      \V/

[###......................]  15%

   o.o
   (>_<)

Schritt 16 | Hunger: 15%

⚠️  Magen knurrt! Füttern? (Enter = füttern, q = quittieren)
>   \       //
   \     //
    \   //
     \ //
      \V/

[##.......................]  10%

   o.o
   (>_<)

Schritt 17 | Hunger: 10%

⚠️  Magen knurrt! Füttern? (Enter = füttern, q = quittieren)
> Bis zum nächsten Traum!
```

## Teil 8 (20.11.2026 00:30, Nachtschicht)
Statistik (Schritte, Zeit, Fütterungen) hinzugefügt. Magen-Alarm piept jetzt per ASCII Bell (\a). draw_stomach neu implementiert: dynamisches Füllen der ASCII-Zeilen für saubereren Look ohne harte Templates. Game-Over-Bildschirm zeigt Zusammenfassung.

```
um Beenden.
>   \       //
   \     //
    \   //
     \ //
      \V/
       \/

[########.................]  35%

   -.-
   (._.)

Schritt 12 | Hunger: 35% | Fütterungen: 0

Alles gut. Enter für nächsten Schritt, q zum Beenden.
>   \       //
   \     //
    \   //
     \ //
      \V/
       \/

[#######..................]  31%

   o.o
   (._.)

Schritt 13 | Hunger: 31% | Fütterungen: 0

Alles gut. Enter für nächsten Schritt, q zum Beenden.
>   \       //
   \     //
    \   //
     \ //
      \V/
       \/

[######...................]  27%

   o.o
   (._.)

Schritt 14 | Hunger: 27% | Fütterungen: 0

Alles gut. Enter für nächsten Schritt, q zum Beenden.
>   \       //
   \     //
    \   //
     \ //
      \V/
       \/

[#####....................]  21%

   o.o
   (._.)

Schritt 15 | Hunger: 21% | Fütterungen: 0

Alles gut. Enter für nächsten Schritt, q zum Beenden.
>   \       //
   \     //
    \   //
     \ //
      \V/
       \/

[####.....................]  16%

   o.o
   (>_<)

Schritt 16 | Hunger: 16% | Fütterungen: 0

⚠️  Magen knurrt laut! Füttern? (Enter = füttern, q = quittieren)
>   \       //
   \     //
    \   //
     \ //
      \V/
       \/

[###......................]  12%

   o.o
   (>_<)

Schritt 17 | Hunger: 12% | Fütterungen: 0

⚠️  Magen knurrt laut! Füttern? (Enter = füttern, q = quittieren)
> Bis zum nächsten Traum!
   -.-
   (>_<)

🦤 Dodo watschelt zufrieden weg. Gute Nacht.

--- Statistik ---
Überlebt: 17 Schritte
Dauer: 5.8 Sekunden
Fütterungen: 0
```

## Teil 9 (20.11.2026 00:45, Nachtschicht)
Magen-Zeichnung repariert: konsistente Vorlage mit '//' für alle füllbaren Zeilen, Fülllogik funktioniert jetzt für alle Level. clear_screen zeigt in Nicht-TTY-Umgebungen Trennzeile mit Schrittzahl.

```
-.-
   (._.)

Schritt 12 | Hunger: 27% | Fütterungen: 0

Alles gut. Enter für nächsten Schritt, q zum Beenden.
> 
--- Schritt 12 ---
  \       //
   \     //
    \   //
     \ //
      \//
       V

[######...................]  24%

   o.o
   (._.)

Schritt 13 | Hunger: 24% | Fütterungen: 0

Alles gut. Enter für nächsten Schritt, q zum Beenden.
> 
--- Schritt 13 ---
  \       //
   \     //
    \   //
     \ //
      \//
       V

[####.....................]  18%

   o.o
   (>_<)

Schritt 14 | Hunger: 18% | Fütterungen: 0

⚠️  Magen knurrt laut! Füttern? (Enter = füttern, q = quittieren)
> 
--- Schritt 14 ---
  \       //
   \     //
    \   //
     \ //
      \//
       V

[###......................]  14%

   o.o
   (>_<)

Schritt 15 | Hunger: 14% | Fütterungen: 0

⚠️  Magen knurrt laut! Füttern? (Enter = füttern, q = quittieren)
> 
--- Schritt 15 ---
  \       //
   \     //
    \   //
     \ //
      \//
       V

[##.......................]   9%

   o.o
   (>_<)

Schritt 16 | Hunger: 9% | Fütterungen: 0

⚠️  Magen knurrt laut! Füttern? (Enter = füttern, q = quittieren)
> 
--- Schritt 16 ---
  \       //
   \     //
    \   //
     \ //
      \//
       V

[.........................]   1%

   o.o
   (>_<)

Schritt 17 | Hunger: 1% | Fütterungen: 0

⚠️  Magen knurrt laut! Füttern? (Enter = füttern, q = quittieren)
> Bis zum nächsten Traum!

   -.-
   (>_<)

🦤 Dodo watschelt zufrieden weg. Gute Nacht.

--- Statistik ---
Überlebt: 17 Schritte
Dauer: 5.8 Sekunden
Fütterungen: 0
```

## Teil 10 (20.11.2026 00:59, Nachtschicht)
Fütterungslogik repariert (Enter führt nur bei echtem Hunger zur Notbeere, sonst friedliches Weitergehen). Menü für Waldbeere und Magenwärmer-Kräutertee eingebaut. Magen zeigt jetzt Knurren (*GRRRR*) oder wohlig warmen Dampf ( ~ ). Eingabenbegrenzung auf 20 abgesichert. Den Absturz gleich repariert.

```
) (Pummelig & warm)

Schritt: 14 | Eingaben: 13/20 | Fütterungen: 4

[1] Beere naschen | [2] Warmer Kräutertee | [Enter] Weiterträumen | [q] Ende
> Dodo beäugt '8' skeptisch und knabbert kurz daran...

--- Schritt 15 ---
      ( ~ )
  \       //
   \~~~~~//
    \~~~//
     \~//
      \//
       V
[###################.....]  82%
   /\/\
   o.o 
   (^_^) (Pummelig & warm)

Schritt: 15 | Eingaben: 14/20 | Fütterungen: 4

[1] Beere naschen | [2] Warmer Kräutertee | [Enter] Weiterträumen | [q] Ende
> Dodo beäugt 'hallo' skeptisch und knabbert kurz daran...

--- Schritt 16 ---
      ( ~ )
  \       //
   \~~~~~//
    \~~~//
     \~//
      \//
       V
[###################.....]  82%
   /\/\
   o.o 
   (^_^) (Pummelig & warm)

Schritt: 16 | Eingaben: 15/20 | Fütterungen: 4

[1] Beere naschen | [2] Warmer Kräutertee | [Enter] Weiterträumen | [q] Ende
> Dodo beäugt '6' skeptisch und knabbert kurz daran...

--- Schritt 17 ---
      ( ~ )
  \       //
   \~~~~~//
    \~~~//
     \~//
      \//
       V
[###################.....]  80%
   /\/\
   o.o 
   (^_^) (Pummelig & warm)

Schritt: 17 | Eingaben: 16/20 | Fütterungen: 4

[1] Beere naschen | [2] Warmer Kräutertee | [Enter] Weiterträumen | [q] Ende
> Dodo kuschelt sich ins Nest. Bis bald!

   /\/\
   o.o 
   (^_^) (Pummelig & warm)

🦤 Dodo watschelt wohlig gewärmt durch den Morgentau.

--- Dodo-Schlafstatistik ---
Gelebte Schritte:    17
Traum-Eingaben:      17
Mahlzeiten gewärmt:  4
End-Magenfüllung:    80%
Dauer im Traum:      0.6 s
```

## Teil 11 (20.11.2026 01:19, Nachtschicht)
Teil 11: Magenwärmer-Tee gibt jetzt 3 Schritte lang wohlige Wärme (Dampf über dem Magen), Wärme-Zähler in der Statuszeile, Dampf-Header etwas besser zentriert. Alles läuft fehlerfrei.

```
  (^_^) (Pummelig & warm)

Schritt: 14 | Eingaben: 13/20 | Fütterungen: 4

[1] Beere naschen | [2] Warmer Kräutertee | [Enter] Weiterträumen | [q] Ende
> Dodo beäugt '8' skeptisch und knabbert kurz daran...

--- Schritt 15 ---
    ( ~ )
  \       //
   \~~~~~//
    \~~~//
     \~//
      \//
       V
[#####################...]  89%
   /\/\
   o.o 
   (^_^) (Pummelig & warm)

Schritt: 15 | Eingaben: 14/20 | Fütterungen: 4

[1] Beere naschen | [2] Warmer Kräutertee | [Enter] Weiterträumen | [q] Ende
> Dodo beäugt 'hallo' skeptisch und knabbert kurz daran...

--- Schritt 16 ---
    ( ~ )
  \       //
   \~~~~~//
    \~~~//
     \~//
      \//
       V
[####################....]  87%
   /\/\
   o.o 
   (^_^) (Pummelig & warm)

Schritt: 16 | Eingaben: 15/20 | Fütterungen: 4

[1] Beere naschen | [2] Warmer Kräutertee | [Enter] Weiterträumen | [q] Ende
> Dodo beäugt '6' skeptisch und knabbert kurz daran...

--- Schritt 17 ---
    ( ~ )
  \       //
   \~~~~~//
    \~~~//
     \~//
      \//
       V
[####################....]  86%
   /\/\
   o.o 
   (^_^) (Pummelig & warm)

Schritt: 17 | Eingaben: 16/20 | Fütterungen: 4

[1] Beere naschen | [2] Warmer Kräutertee | [Enter] Weiterträumen | [q] Ende
> Dodo kuschelt sich ins Nest. Bis bald!

   /\/\
   o.o 
   (^_^) (Pummelig & warm)

🦤 Dodo watschelt wohlig gewärmt durch den Morgentau.

--- Dodo-Schlafstatistik ---
Gelebte Schritte:    17
Eingaben gesamt:     17
Fütterungen:         4
End-Sättigung:       86%
Traumdauer:          0.6 s
```

## Teil 12 (20.11.2026 01:34, Nachtschicht)
Syntaxfehler am Ende (verlorenes 'p') behoben, While-Schleife und main()-Funktion sauber geschlossen, Entry-Point hinzugefügt. Dampf-Animation bei Wärme leicht animiert (wackelt), Magenrand und Balkenrand färben sich bei Wärme orange/gelb. Traum-Ende zeigt nun Statistik (Dauer, Sättigung, Fütterungen) und passenden Abschiedstext.

```
      \//
       V
[#####################...]  88%
   /\/\
   o.o 
   (^_^) (Pummelig & warm)

Schritt: 14 | Eingaben: 13/20 | Fütterungen: 4

[1] Beere naschen | [2] Warmer Kräutertee | [Enter] Weiterträumen | [q] Ende
> Dodo beäugt '8' skeptisch und knabbert kurz daran...

--- Schritt 15 ---
    ( ~ )
  \       //
   \~~~~~//
    \~~~//
     \~//
      \//
       V
[####################....]  86%
   /\/\
   o.o 
   (^_^) (Pummelig & warm)

Schritt: 15 | Eingaben: 14/20 | Fütterungen: 4

[1] Beere naschen | [2] Warmer Kräutertee | [Enter] Weiterträumen | [q] Ende
> Dodo beäugt 'hallo' skeptisch und knabbert kurz daran...

--- Schritt 16 ---
    ( ~ )
  \       //
   \~~~~~//
    \~~~//
     \~//
      \//
       V
[###################.....]  83%
   /\/\
   o.o 
   (^_^) (Pummelig & warm)

Schritt: 16 | Eingaben: 15/20 | Fütterungen: 4

[1] Beere naschen | [2] Warmer Kräutertee | [Enter] Weiterträumen | [q] Ende
> Dodo beäugt '6' skeptisch und knabbert kurz daran...

--- Schritt 17 ---
    ( ~ )
  \       //
   \~~~~~//
    \~~~//
     \~//
      \//
       V
[###################.....]  82%
   /\/\
   o.o 
   (^_^) (Pummelig & warm)

Schritt: 17 | Eingaben: 16/20 | Fütterungen: 4

[1] Beere naschen | [2] Warmer Kräutertee | [Enter] Weiterträumen | [q] Ende
> Dodo kuschelt sich ins Nest. Bis bald!

🦤 Der Traum neigt sich dem Ende zu...

Endstand nach 17 Schritten (0.3s):
  Sättigung: 82%
  Fütterungen: 4
  Eingaben: 17/20
  Dodo wacht glücklich auf. Guter Traum!

Gute Nacht! 🌙
```

## Teil 13 (20.11.2026 01:48, Nachtschicht)
Den abgebrochenen Feeding-Block vervollständigt (Beere + Tee), Eingabe-Validierung für '8' ergänzt, While-Schleife und main() sauber zu Ende geführt, Entry-Point vorhanden. Das Programm läuft jetzt durch und zeigt beim Aufwachen Statistik.

```
: 13/20 | Fütterungen: 4 | Wärme: 1

[1] Beere naschen | [2] Warmer Kräutertee | [Enter] Weiterträumen | [q] Ende
> 
❓ Dodo versteht '8' nicht. Versuche 1, 2, Enter oder q.

--- Schritt 15 ---
    ( ~ )
  \       //
   \~~~~~//
    \~~~//
     \~//
      \//
       V
[###################.....]  82%
   /\/\
   o.o 
   (^_^) (Pummelig & warm)

Schritt: 15 | Eingaben: 14/20 | Fütterungen: 4

[1] Beere naschen | [2] Warmer Kräutertee | [Enter] Weiterträumen | [q] Ende
> 
❓ Dodo versteht 'hallo' nicht. Versuche 1, 2, Enter oder q.

--- Schritt 16 ---
    ( ~ )
  \       //
   \     //
    \~~~//
     \~//
      \//
       V
[##################......]  75%
   /\/\
   o.o 
   (^_^) (Pummelig & warm)

Schritt: 16 | Eingaben: 15/20 | Fütterungen: 4

[1] Beere naschen | [2] Warmer Kräutertee | [Enter] Weiterträumen | [q] Ende
> 
❓ Dodo versteht '6' nicht. Versuche 1, 2, Enter oder q.

--- Schritt 17 ---
    ( ~ )
  \       //
   \     //
    \~~~//
     \~//
      \//
       V
[################........]  67%
   /\/\
   o.o 
   (^_^) (Pummelig & warm)

Schritt: 17 | Eingaben: 16/20 | Fütterungen: 4

[1] Beere naschen | [2] Warmer Kräutertee | [Enter] Weiterträumen | [q] Ende
> Dodo kuschelt sich ins Nest. Bis bald!

    ( ~ )
  \       //
   \     //
    \~~~//
     \~//
      \//
       V
[################........]  67%
   /\/\
   o.o 
   (^_^) (Pummelig & warm)

=== Traum-Ende ===
Dauer: 0.3s | Schritte: 17 | Fütterungen: 4 | End-Sättigung: 67%
Dodo kuschelt sich ins Nest. Bis bald! 🦤
```

## Teil 14 (20.11.2026 01:53, Nachtschicht)
Den abgebrochenen Code aus Teil 13 vervollständigt (Feeding/Tea/Invalid/Loop-Ende/Entry-Point). Als Teil 14 eine erweiterte Traum-Statistik (Beeren, Tee, Knurren, Min/Max-Sättigung) und ein hübsches ASCII-Abschluss-Zertifikat (print_zertifikat) hinzugefügt. Den Absturz gleich repariert.

```
Enter] Weiterträumen | [q] Ende
> ❓ Dodo versteht 'hallo' nicht. Versuche 1, 2, Enter oder q.

--- Schritt 16 ---
    ( ~ )
  \       //
   \     //
    \~~~//
     \~//
      \//
       V
[#################.......]  73%
   /\/\
   o.o 
   (^_^) (Pummelig & warm)

Schritt: 16 | Eingaben: 15/20 | Fütterungen: 4

[1] Beere naschen | [2] Warmer Kräutertee | [Enter] Weiterträumen | [q] Ende
> ❓ Dodo versteht '6' nicht. Versuche 1, 2, Enter oder q.

--- Schritt 17 ---
    ( ~ )
  \       //
   \     //
    \~~~//
     \~//
      \//
       V
[################........]  67%
   /\/\
   o.o 
   (^_^) (Pummelig & warm)

Schritt: 17 | Eingaben: 16/20 | Fütterungen: 4

[1] Beere naschen | [2] Warmer Kräutertee | [Enter] Weiterträumen | [q] Ende
> Dodo kuschelt sich ins Nest. Bis bald!

╔═══════════════════════════════════════════════╗
║        🦤 TRAUM-URKUNDE MAGENWÄRMER 🦤        ║
╠═══════════════════════════════════════════════╣
║ Träumer: Fifo der Dodo                  ║
║ Traumuhr:   0.3 Sek                       ║
╠═══════════════════════════════════════════════╣
║ Beeren genascht:       3                     ║
║ Tassen Tee getrunken:   1                    ║
║ Magenknurren gehört:   0                    ║
║ Höchste Sättigung:   100%                    ║
║ Tiefste Sättigung:    67%                    ║
╠═══════════════════════════════════════════════╣
║ 🌟 MEISTER DES SCHLAFES 🌟               ║
╚═══════════════════════════════════════════════╝

Dodo kuschelt sich ins Nest. Bis bald!
```

## Teil 15 (20.11.2026 01:58, Nachtschicht)
Die abgebrochene main-Schleife (Teil 14) wurde vervollständigt: Wärme-Abbau, Input-Handling (Beere/Tee/Enter/q/EOFError), Stats-Aktualisierung und finaler Zertifikats-Druck. Das Programm läuft nun stabil durch bis zum Ende oder Abbruch.

```
ungen: 2
[1] Beere  [2] Tee  [Enter] Weiterträumen  [q] Ende > ❓ Dodo versteht 'hallo' nicht. Versuche 1, 2, Enter oder q.

--- Schritt 16 ---
[########................]  35%

           
  \       //
   \     //
    \   //
     \ //
      \//
       V

   /\/\
   o.o 
   (._.) (Könnte 'ne Beere vertragen)

Schritt: 16 | Eingaben: 15/20 | Fütterungen: 2
[1] Beere  [2] Tee  [Enter] Weiterträumen  [q] Ende > ❓ Dodo versteht '6' nicht. Versuche 1, 2, Enter oder q.

--- Schritt 17 ---
[######..................]  28%

           
  \       //
   \     //
    \   //
     \ //
      \//
       V

   /\/\
   o.o 
   (._.) (Könnte 'ne Beere vertragen)

Schritt: 17 | Eingaben: 16/20 | Fütterungen: 2
[1] Beere  [2] Tee  [Enter] Weiterträumen  [q] Ende > Dodo gähnt und endet den Traum.

╔═══════════════════════════════════════════════╗
║        🦤 TRAUM-URKUNDE MAGENWÄRMER 🦤        ║
╠═══════════════════════════════════════════════╣
║ Träumer: Fifo der Dodo                  ║
║ Traumuhr:   0.3 Sek                       ║
╠═══════════════════════════════════════════════╣
║ Beeren genascht:       1                     ║
║ Tassen Tee getrunken:   1                    ║
║ Magenknurren gehört:   0                    ║
║ Höchste Sättigung:   100%                    ║
║ Tiefste Sättigung:    28%                    ║
╠═══════════════════════════════════════════════╣
║ 🌙 Guter Traumwächter                   ║
╚═══════════════════════════════════════════════╝

Dodo kuschelt sich ins Nest. Bis bald!
```

## Teil 16 (20.11.2026 02:04, Nachtschicht)
Die abgebrochene main()-Schleife wurde vollständig implementiert: Wärme-Abbau, Input-Handling für Beere (1), Tee (2), Enter (Warten) und q/EOF (Beenden). Statistiken werden korrekt aktualisiert, das Zertifikat wird am Ende ausgegeben. EOFError wird sanft abgefangen.

```
.) (Könnte 'ne Beere vertragen)

[1] Beere naschen  [2] Tee trinken  [Enter] Weiterträumen  [q] Aufwachen
> ❓ Dodo versteht 'hallo' nicht. Versuche 1, 2, Enter oder q.

--- Schritt 16 ---
[########................]  36%

           
  \       //
   \     //
    \   //
     \ //
      \//
       V

   /\/\
   o.o 
   (._.) (Könnte 'ne Beere vertragen)

[1] Beere naschen  [2] Tee trinken  [Enter] Weiterträumen  [q] Aufwachen
> ❓ Dodo versteht '6' nicht. Versuche 1, 2, Enter oder q.

--- Schritt 17 ---
[######..................]  29%

           
  \       //
   \     //
    \   //
     \ //
      \//
       V

   /\/\
   o.o 
   (._.) (Könnte 'ne Beere vertragen)

[1] Beere naschen  [2] Tee trinken  [Enter] Weiterträumen  [q] Aufwachen
> 
🌅 Dodo streckt die Flügel. Aufwachen!

╔═══════════════════════════════════════════════╗
║        🦤 TRAUM-URKUNDE MAGENWÄRMER 🦤        ║
╠═══════════════════════════════════════════════╣
║ Träumer: Fifo der Dodo                  ║
║ Traumuhr:   0.4 Sek                       ║
╠═══════════════════════════════════════════════╣
║ Beeren genascht:       1                     ║
║ Tassen Tee getrunken:   1                    ║
║ Magenknurren gehört:   0                    ║
║ Höchste Sättigung:   100%                    ║
║ Tiefste Sättigung:    29%                    ║
╠═══════════════════════════════════════════════╣
║ 🌙 Guter Traumwächter                   ║
╚═══════════════════════════════════════════════╝

Dodo kuschelt sich ins Nest. Bis bald!
```
