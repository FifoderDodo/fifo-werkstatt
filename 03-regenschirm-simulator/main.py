# Fifo der Dodo bastelt am Regenschirm-Simulator!
# Krächz! Der versehentliche Text ist weg, jetzt gibt es eine saubere main()-Funktion.

import random

SCHIRM = [
    "      .---.      ",
    "    ./     \\.    ",
    "   /         \\   ",
    "  '-----------'  ",
    "        |        ",
    "        |        ",
    "       '-'       "
]

def erzeuge_regenzeile(breite=17, dichte=0.25):
    tropfen_symbole = [".", "|", "'", " "]
    gewichte = [0.1, 0.1, 0.05, 0.75]
    return "".join(random.choices(tropfen_symbole, weights=gewichte, k=breite))

def main():
    print("=== Fifos Regenschirm-Simulator (Teil 5) ===")
    random.seed(42)  # Fester Startwert für zuverlässige Regentropfen
    
    # Ein paar Tropfen über dem Schirm fallen lassen
    for _ in range(3):
        print(erzeuge_regenzeile())
    
    # Den stolzen Dodo-Schirm drucken
    for zeile in SCHIRM:
        print(zeile)
        
    print("Plitsch, platsch! Der Schirm hält dicht!")

if __name__ == "__main__":
    main()
