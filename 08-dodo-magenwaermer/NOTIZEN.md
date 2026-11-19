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
