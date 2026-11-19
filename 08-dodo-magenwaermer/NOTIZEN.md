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
