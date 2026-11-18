import time, random

# Krächz! Windstärke bestimmt den Schräglauf der Tropfen!
windstaerke = 2
schirm_breite = 20

print("Regenschirm-Simulator gestartet (Teil 7)...")
for schritt in range(3):
    tropfen_pos = random.randint(0, schirm_breite - 1)
    versatz = tropfen_pos + windstaerke
    zeile = [" " for _ in range(schirm_breite + 5)]
    if 0 <= versatz < len(zeile):
        zeile[versatz] = "/"
    else:
        zeile[tropfen_pos] = "|"
    print("".join(zeile))
    time.sleep(0.2)
print("Tropfen gleiten am Griff vorbei!")
