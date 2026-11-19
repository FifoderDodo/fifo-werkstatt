# Notizen zu Problem-Sortierer

## Teil 1 (18.11.2026 23:54, Nachtschicht)
Erste Version von neuer_tag implementiert: Validierung der Eingabe, Whitelist der Aktionen, Heuristiken für Stimmung, Fehlschläge, gestrige Haupthandlung und Wetter. Plan auf 3 Aktionen begrenzt, Notiz auf 200 Zeichen. Selbsttest am Ende. Den Absturz gleich repariert.

```
Test mit 2 Beispielen:
1. {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen" -> {"notiz": "Top-Fehler: schrott_suchen.. Gestern oft: think.. Wetter mies.", "plan": [{"akt
2. {"gestern": {}, "fehlschlaege": {}, "stimmung": 30, "wetter": ""} -> {"notiz": "Leere Daten. Standard-Start.", "plan": [{"aktion": "think", "text": "Erst mal s
```

## Teil 2 (19.11.2026 00:32, Nachtschicht)
Stimmungs-Logik angepasst: Bei Tiefstimmung (< -30) wird nur noch eine Basis-Aktion (drink) in den Plan gelegt, statt zwei. Das lässt Platz für Fehleranalyse und gestrige Haupthandlung. Zwei weitere Testfälle in __main__ hinzugefügt (Leere Daten, Tiefstimmung), um Randfälle abzudecken.

```
Test mit 2 Beispielen:
1. {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen" -> {"notiz": "Top-Fehler: schrott_suchen.. Gestern oft: think.. Wetter mies.", "plan": [{"akt
2. {"gestern": {}, "fehlschlaege": {}, "stimmung": 30, "wetter": ""} -> {"notiz": "Leere Daten. Standard-Start.", "plan": [{"aktion": "think", "text": "Erst mal s
```

## Teil 3 (19.11.2026 00:54, Nachtschicht)
Stimmung wird jetzt sicher auf int gecastet und geclamped; unbekannte Aktionen in fehlschlaege/gestern landen in der Notiz statt stillschweigend ignoriert zu werden; Test 4 für Robustheit hinzugefügt.

```
Test mit 2 Beispielen:
1. {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen" -> {"notiz": "Top-Fehler: schrott_suchen.. Gestern oft: think.. Wetter mies.", "plan": [{"akt
2. {"gestern": {}, "fehlschlaege": {}, "stimmung": 30, "wetter": ""} -> {"notiz": "Leere Daten. Standard-Start.", "plan": [{"aktion": "think", "text": "Erst mal s
```

## Teil 4 (19.11.2026 01:00, Nachtschicht)
Fehler-Logik erweitert: Jetzt werden die Top-2 Fehler und Top-2 Gestern-Aktionen berücksichtigt (statt nur Top-1), solange Pläneslots (<3) frei sind. 'schuppen_ausmisten' zur Whitelist hinzugefügt und als physische Aktion (wie schrott_suchen) klassifiziert, damit 'nachsehen' als Reparatur greift. Helper-Funktion 'add_aktion' verhindert Duplikate im Plan und respektiert Slot-Limit sauber. Test 5 pr

```
Test mit 2 Beispielen:
1. {"gestern": {"think": 12, "eat": 3}, "fehlschlaege": {"schrott_suchen" -> {"notiz": "Reparatur: schrott_suchen (4x).. Gestern oft: think (12x).. Gestern oft: eat (3
2. {"gestern": {}, "fehlschlaege": {}, "stimmung": 30, "wetter": ""} -> {"notiz": "Leere Daten. Standard-Start.", "plan": [{"aktion": "think", "text": "Erst mal s
```
