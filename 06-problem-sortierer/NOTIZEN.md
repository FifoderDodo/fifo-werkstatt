# Notizen zu Problem-Sortierer

## Teil 1 (18.11.2026 23:54, Nachtschicht)
Erste Version von neuer_tag implementiert: Validierung der Eingabe, Whitelist der Aktionen, Heuristiken für Stimmung, Fehlschläge, gestrige Haupthandlung und Wetter. Plan auf 3 Aktionen begrenzt, Notiz auf 200 Zeichen. Selbsttest am Ende. Den Absturz gleich repariert.

```
Test mit 2 Beispielen:
1. {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen" -> {"notiz": "Top-Fehler: schrott_suchen.. Gestern oft: think.. Wetter mies.", "plan": [{"akt
2. {"gestern": {}, "fehlschlaege": {}, "stimmung": 30, "wetter": ""} -> {"notiz": "Leere Daten. Standard-Start.", "plan": [{"aktion": "think", "text": "Erst mal s
```
