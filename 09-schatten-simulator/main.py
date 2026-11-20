# main.py – Schatten-Simulator, Teil 1
# Fifo, der Dodo, wackelt mit dem Schwänzchen und legt los.


def main() -> None:
    """Einstiegspunkt: kleine Demo-Tiefenkarte erzeugen und anzeigen."""
    print("🦤 Fifo meldet Dienst: Schatten-Simulator startet …")

    # Beispieldaten: 4×4-Grid mit erfundenen Höhenwerten (0.0 – 1.0)
    hoehen = [
        [0.1, 0.2, 0.3, 0.2],
        [0.2, 0.5, 0.6, 0.3],
        [0.3, 0.7, 0.9, 0.4],
        [0.2, 0.4, 0.5, 0.3],
    ]

    print("\nAktuelle Tiefenkarte (Höhenwerte):")
    for reihe in hoehen:
        print("  " + "  ".join(f"{h:.1f}" for h in reihe))

    # Ein winziger Interaktions-Schritt: Zuschauer darf einen Wert ändern
    try:
        eingabe = input("\nNeue Höhe für [2][2] (0.0-1.0) oder Enter für Behalten: ").strip()
        if eingabe:
            neuer_wert = float(eingabe)
            if 0.0 <= neuer_wert <= 1.0:
                hoehen[2][2] = neuer_wert
                print(f"  → Geändert auf {neuer_wert:.1f}")
            else:
                print("  → Wert außerhalb, bleibt unverändert.")
    except (ValueError, EOFError):
        print("  → Keine gültige Eingabe, Fifo macht weiter.")

    # Einfache Tiefen-Statistik als erster „Berechnungsschritt"
    max_h = max(max(r) for r in hoehen)
    min_h = min(min(r) for r in hoehen)
    print(f"\nTiefenbereich: min={min_h:.2f}, max={max_h:.2f}, spanne={max_h - min_h:.2f}")
    print("\n🦤 Fifo pickt sich den nächsten Wurm – Teil 1 erledigt.")


if __name__ == "__main__":
    main()