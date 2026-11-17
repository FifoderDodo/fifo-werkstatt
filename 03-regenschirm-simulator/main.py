import time
import random

def main():
    # Dodo-Schnabel pickt die mathematische Form fuer die gewoelbte Schirmkappe zusammen
    breite = 40
    hoehe = 10
    schirm_mitte = 20
    schirm_hoehe_start = 4
    
    print("Regenschirm-Simulator gestartet!")
    
    for schritt in range(5):
        tropfen_x = random.randint(0, breite - 1)
        tropfen_y = random.randint(0, hoehe - 1)
        
        # Erweiterte Kollisionsabfrage mit einer angedeuteten Schirmkappen-Wloebung
        abstand_mitte = abs(tropfen_x - schirm_mitte)
        if tropfen_y >= schirm_hoehe_start and abstand_mitte < (6 - (tropfen_y - schirm_hoehe_start)):
            status = "abgefangen am gewoelbten Schirm"
        elif tropfen_y >= hoehe - 2:
            status = "platsch auf dem Boden"
        else:
            status = "faellt durch die Luft"
        
        print(f"Tropfen bei X:{tropfen_x} Y:{tropfen_y}: {status}")
        time.sleep(0.2)

if __name__ == "__main__":
    main()
