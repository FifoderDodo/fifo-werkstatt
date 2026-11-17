import time
import random

def main():
    # Dodo-Fluegel flattern ueber der Tastatur und bringen Ordnung ins Chaos
    breite = 40
    hoehe = 10
    schirm_mitte = 20
    
    print("Regenschirm-Simulator gestartet!")
    
    for schritt in range(5):
        tropfen_x = random.randint(0, breite - 1)
        # Pruefen ob der Tropfen den Schirm trifft
        if abs(tropfen_x - schirm_mitte) < 5:
            status = "abgefangen am Schirm"
        else:
            status = "platsch auf dem Boden"
        
        print(f"Tropfen bei {tropfen_x}: {status}")
        time.sleep(0.2)

if __name__ == "__main__":
    main()
