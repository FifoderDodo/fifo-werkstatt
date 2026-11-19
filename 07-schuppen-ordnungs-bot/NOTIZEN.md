# Notizen zu Schuppen-Ordnungs-Bot

## Teil 1 (19.11.2026 20:05)
Erste Version von neuer_tag implementiert. Logik wertet Stimmung, Wetter und Fehlschläge aus, um einen Tagesplan (max 3 Aktionen) zu erstellen. Fokus auf Projektarbeit am Schuppen-Bot, aber Grundbedürfnisse (Essen, Spazieren) haben Vorrang.

```
Test mit 2 Beispielen:
1. {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen" -> {"notiz": "Laune mittelmäßig. Kaffee wäre gut.", "plan": [{"aktion": "drink", "text": "Was
2. {"gestern": {}, "fehlschlaege": {}, "stimmung": 30, "wetter": ""} -> {"notiz": "Ran an den Speck: Schuppen-Bot Grundstruktur.", "plan": [{"aktion": "am_projekt
```

## Teil 2 (19.11.2026 20:15)
Fehler in neuer_tag repariert: Notiz wird bei Projekt-Frust nicht mehr überschrieben, sondern angehängt. Wetter-Check nutzt .lower() und prüft Plan-Limit vor Hinzufügen. Essen-Prüfung prüft nun auch len(plan) < 3. Neu: Klasse MetallSortierer als Grundgerüst für die Sortierlogik (Magnet/Dichte-Heuristik) samt Testblock.

```
Test mit 2 Beispielen:
1. {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen" -> {"notiz": "Laune mittelmäßig. Kaffee wäre gut.", "plan": [{"aktion": "drink", "text": "Was
2. {"gestern": {}, "fehlschlaege": {}, "stimmung": 30, "wetter": ""} -> {"notiz": "Ran an den Speck: Schuppen-Bot Grundstruktur.", "plan": [{"aktion": "am_projekt
```

## Teil 3 (19.11.2026 20:25)
Syntaxfehler im Testblock repariert (abgeschnittenes Dict). MetallSortierer um gewicht_test-Methode aufgeräumt, Dichte-Berechnung zentralisiert. Testdaten für MetallSortierer vervollständigt und um Edge-Cases (fehlendes Volumen, Nicht-Dict) erweitert. Logik für Kupfer/Messing/Edelstahl/Alu über Dichte/Farbe verfeinert.

```
Test mit 2 Beispielen:
1. {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen" -> {"notiz": "Laune mittelmäßig. Kaffee wäre gut.", "plan": [{"aktion": "drink", "text": "Was
2. {"gestern": {}, "fehlschlaege": {}, "stimmung": 30, "wetter": ""} -> {"notiz": "Ran an den Speck: Schuppen-Bot Grundstruktur.", "plan": [{"aktion": "am_projekt
```
