# Notizen zu Schuppen-Ordnungs-Bot

## Teil 1 (19.11.2026 20:05)
Erste Version von neuer_tag implementiert. Logik wertet Stimmung, Wetter und Fehlschläge aus, um einen Tagesplan (max 3 Aktionen) zu erstellen. Fokus auf Projektarbeit am Schuppen-Bot, aber Grundbedürfnisse (Essen, Spazieren) haben Vorrang.

```
Test mit 2 Beispielen:
1. {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen" -> {"notiz": "Laune mittelmäßig. Kaffee wäre gut.", "plan": [{"aktion": "drink", "text": "Was
2. {"gestern": {}, "fehlschlaege": {}, "stimmung": 30, "wetter": ""} -> {"notiz": "Ran an den Speck: Schuppen-Bot Grundstruktur.", "plan": [{"aktion": "am_projekt
```
