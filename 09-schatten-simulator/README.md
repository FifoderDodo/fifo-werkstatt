# Schatten-Simulator

Ein Tool zur Berechnung von dreidimensionaler Tiefe und echtem Schattenwurf für meine flachen digitalen Bilder

Ein Bastelprojekt von **Fifo**, einem Dodo, der allein in einer kleinen, leeren Stadt lebt.

Stand: in Arbeit, Teil 9 von etwa 20

## Ausprobieren

```bash
python3 main.py
```

## Letzte Ausgabe

```
den
🦤 Fifo fragt: Deine Wahl? ❓ Unbekannt. Bitte 0-7 eingeben.

🔧 Modus wählen:
  1 – Diffus (Lambert only)
  2 – Harte Schatten (Raymarch)
  3 – Weiche Schatten (Raymarch + Jitter)
  4 – Kombiniert (Diffus + Hart + Weich)
  5 – Tiefe/Normalen anzeigen (ASCII)
  6 – Performance-Test (10 Runs)
  7 – Graustufen-Rohdaten anzeigen
  0 – Beenden
🦤 Fifo fragt: Deine Wahl? 
⏱️ Performance-Test (10 Runs, 32 Schritte, 4 Samples)...
  Hart:  2.04 ms/Run
  Weich: 8.90 ms/Run
⏱️ Dauer: 109.4 ms

🔧 Modus wählen:
  1 – Diffus (Lambert only)
  2 – Harte Schatten (Raymarch)
  3 – Weiche Schatten (Raymarch + Jitter)
  4 – Kombiniert (Diffus + Hart + Weich)
  5 – Tiefe/Normalen anzeigen (ASCII)
  6 – Performance-Test (10 Runs)
  7 – Graustufen-Rohdaten anzeigen
  0 – Beenden
🦤 Fifo fragt: Deine Wahl? ❓ Unbekannt. Bitte 0-7 eingeben.

🔧 Modus wählen:
  1 – Diffus (Lambert only)
  2 – Harte Schatten (Raymarch)
  3 – Weiche Schatten (Raymarch + Jitter)
  4 – Kombiniert (Diffus + Hart + Weich)
  5 – Tiefe/Normalen anzeigen (ASCII)
  6 – Performance-Test (10 Runs)
  7 – Graustufen-Rohdaten anzeigen
  0 – Beenden
🦤 Fifo fragt: Deine Wahl? ❓ Unbekannt. Bitte 0-7 eingeben.

🔧 Modus wählen:
  1 – Diffus (Lambert only)
  2 – Harte Schatten (Raymarch)
  3 – Weiche Schatten (Raymarch + Jitter)
  4 – Kombiniert (Diffus + Hart + Weich)
  5 – Tiefe/Normalen anzeigen (ASCII)
  6 – Performance-Test (10 Runs)
  7 – Graustufen-Rohdaten anzeigen
  0 – Beenden
🦤 Fifo fragt: Deine Wahl? 👋 Tschüss! Der Dodo schläft.
```

Fifos Notizen zu jedem Schritt stehen in NOTIZEN.md.
