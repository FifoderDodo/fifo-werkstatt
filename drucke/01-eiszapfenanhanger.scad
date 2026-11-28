// Eiszapfen-Anhänger für Kristallhöhle
// Druck stehend auf der breiten Basis (z=0), Spitze zeigt nach +Z
// Vertikales Loch in der Spitze für Aufhängeband (keine Überhänge)
// Hohlwand ab 3 mm Höhe, massive Spitze für Loch-Stabilität

$fn = 32;

// Parameter
hoehe = 80;
durchmesser_basis = 30;
durchmesser_spitze = 6;        // Flache Spitze für Loch
wandstaerke = 1.5;
boden_dicke = 3;               // Massiver Boden für Auflage
massiv_spitze_laenge = 10;     // Massiver Bereich an der Spitze
loch_durchmesser = 3;          // Aufhängebohrung

module eiszapfen() {
    difference() {
        // Außenkontur: Kegelstumpf
        cylinder(h = hoehe, d1 = durchmesser_basis, d2 = durchmesser_spitze);

        // Hohlraum: beginnt nach Boden, endet vor massiver Spitze
        // Innendurchmesser Basis = Außen - 2*Wand
        // Innendurchmesser Spitze = Außenspitze - 2*Wand
        translate([0, 0, boden_dicke])
            cylinder(h = hoehe - boden_dicke - massiv_spitze_laenge,
                     d1 = durchmesser_basis - 2 * wandstaerke,
                     d2 = durchmesser_spitze - 2 * wandstaerke);

        // Aufhängebohrung: vertikal durch die massive Spitze
        // Startet etwas tiefer, um sauber durch die Wand zu gehen
        translate([0, 0, hoehe - massiv_spitze_laenge - 2])
            cylinder(h = massiv_spitze_laenge + 4, d = loch_durchmesser, center = false);
    }
}

eiszapfen();