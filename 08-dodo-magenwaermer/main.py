import random
import time
import sys
import math

USE_ANSI = sys.stdout.isatty()
MAX_EINGABEN = 20


def pause(sekunden: float) -> None:
    """Macht eine Pause, im Nicht-TTY-Modus fast verzögerungsfrei."""
    if USE_ANSI:
        time.sleep(sekunden)
    else:
        time.sleep(min(sekunden, 0.02))


def satte_pruefung(wert: int) -> bool:
    """Prüft, ob der Magen leerer als 20 % ist."""
    return wert < 20


def clear_screen(schritt: int = None) -> None:
    """Löscht Terminal bei TTY oder druckt Trennzeile."""
    if USE_ANSI:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
    else:
        if schritt is not None:
            print(f"\n--- Schritt {schritt} ---")
        else:
            print()


def ease_out_cubic(t: float) -> float:
    """Kubisches Auslaufen: t in [0,1] -> weicher Stopp."""
    return 1 - pow(1 - t, 3)


def ease_in_out_quad(t: float) -> float:
    """Quadratisches Ein/Aus: sanftes Anfahren und Abbremsen."""
    return 2 * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 2) / 2


def draw_feder(saettigung: int, schritt: int) -> str:
    """Zeichnet eine kleine leuchtende Feder als Sättigungs-Indikator.
    Farbe: Grün(>75) -> Gelb(>45) -> Orange(>20) -> Rot(>5) -> Grau(<=5).
    Nutzt Bézier-Easing für Pulsieren (Skalierung), horizontales Wackeln und Neigungs-Charakter."""
    # Farbstufen & Basis-Zeichen
    if USE_ANSI:
        if saettigung > 75:
            farbe = "\033[92m"      # Hellgrün
            base_char = "❈"
            bend_chars = ["❈", "✦", "✧"] # Leicht gebogen
        elif saettigung > 45:
            farbe = "\033[93m"      # Gelb
            base_char = "✦"
            bend_chars = ["✦", "✧", "❈"]
        elif saettigung > 20:
            farbe = "\033[38;5;208m" # Orange
            base_char = "✧"
            bend_chars = ["✧", "❈", "✦"]
        elif saettigung > 5:
            farbe = "\033[91m"      # Rot
            base_char = "✦"
            bend_chars = ["✦", "·", "·"]
        else:
            farbe = "\033[90m"      # Dunkelgrau
            base_char = "·"
            bend_chars = ["·", " ", " "]
        reset = "\033[0m"
        
        # Animations-Zyklus (0.0 - 1.0)
        # Unterschiedliche Frequenzen für organischen Look
        cycle_puls = (schritt * 0.07) % 1.0       # Langsam pulsieren
        cycle_wackel = (schritt * 0.13) % 1.0     # Wackeln
        cycle_bend = (schritt * 0.11) % 1.0       # Neigung
        
        # 1. Pulsieren (Skalierung 1.0 -> 1.5 -> 1.0)
        # Easing für weiches Aufblähen
        p = ease_in_out_quad(cycle_puls)
        scale = 1 + 0.5 * p # 1.0 bis 1.5
        # Da wir nur diskrete Zeichen haben: 1 Zeichen oder 2 Zeichen
        show_double = scale > 1.25
        
        # 2. Horizontales Wackeln (Offset 0 oder 1 Leerzeichen)
        # Nur bei niedriger Sättigung stark, sonst subtil
        wackel_amp = 1.0 if saettigung < 20 else (0.3 if saettigung < 50 else 0.0)
        w = ease_out_cubic(cycle_wackel) * wackel_amp
        wackel_str = " " if w > 0.5 else ""
        
        # 3. Neigung (Zeichenwechsel simuliert Biegung)
        b = ease_in_out_quad(cycle_bend)
        bend_idx = int(b * (len(bend_chars) - 1))
        char = bend_chars[bend_idx]
        
        # Zusammenbau
        if show_double and saettigung > 5:
            return f"{wackel_str}{farbe}{char}{char}{reset}"
        return f"{wackel_str}{farbe}{char}{reset}"
    else:
        # Fallback ASCII
        if saettigung > 75: return ">"
        if saettigung > 45: return "-~"
        if saettigung > 20: return "~"
        if saettigung > 5:  return "!"
        return "."


def draw_bar(wert: int, breite: int = 24, waerme: int = 0) -> str:
    """Baut einen farbigen Balken für die Sättigung, gelber Rand bei Wärme."""
    voll = int((wert / 100) * breite)
    leer = breite - voll
    if USE_ANSI:
        if wert >= 75:
            farbe = "\033[92m"
        elif wert >= 45:
            farbe = "\033[93m"
        elif wert >= 20:
            farbe = "\033[38;5;208m"
        else:
            farbe = "\033[91m"
        rand = "\033[93m" if waerme > 0 else "\033[0m"
        reset = "\033[0m"
        return f"{rand}[{reset}{farbe}{'#' * voll}{'.' * leer}{rand}]{reset} {wert:3d}%"
    return f"[{'#' * voll}{'.' * leer}] {wert:3d}%"


def draw_waerme_bar(waerme: int, max_waerme: int = 10, breite: int = 12) -> str:
    """Visualisiert den Wärme-Level als kleinen Balken."""
    if max_waerme <= 0:
        return ""
    voll = int((waerme / max_waerme) * breite)
    leer = breite - voll
    if USE_ANSI:
        farbe = "\033[93m"
        reset = "\033[0m"
        return f"{farbe}[{'#' * voll}{'.' * leer}]{reset} {waerme}/{max_waerme}"
    return f"[{'#' * voll}{'.' * leer}] {waerme}/{max_waerme}"


def draw_stomach(wert: int, knurrt: bool, waerme: int = 0, schritt: int = 0) -> str:
    """Zeichnet den ASCII-Magen mit Füllung, Knurren und animiertem Dampf bei Wärme."""
    level = max(0, min(5, int(wert / 20)))
    wave = "~~~"
    
    if waerme > 0:
        if (schritt // 2) % 2 == 0:
            header = "    ( ~ )"
        else:
            header = "   ( ~ ) "
    elif wert >= 50:
        header = "    ( ~ )"
    elif knurrt:
        header = "   *GRRRR*"
    else:
        header = "           "
    
    magen_farbe = "\033[38;5;208m" if (waerme > 0 and USE_ANSI) else ""
    reset = "\033[0m" if USE_ANSI else ""
    
    lines = [
        "  \\       //",
        "   \\     //",
        "    \\   //",
        "     \\ //",
        "      \\//",
        "       V"
    ]
    fill_start = 5 - level
    result = [header]
    
    for i, line in enumerate(lines):
        if i >= fill_start and level > 0 and i < 5:
            left = line.find('\\')
            right = line.find('//')
            if left != -1 and right != -1 and right > left:
                mid = line[left+2:right]
                filled = (wave * (len(mid) // 3 + 1))[:len(mid)]
                line = line[:left+2] + filled + line[right:]
        result.append(line)
    return "\n".join(result)


def main() -> None:
    """Hauptprogramm: Dodo-Magenwärmer Simulation."""
    saettigung = 100
    waerme = 0
    schritt = 0
    max_schritte = 20
    eingaben = 0
    
    print("Dodo-Magenwärmer gestartet. Drücke Enter für nächsten Schritt,")
    print("'f' zum Füttern, 'q' zum Beenden.")
    pause(1.5)
    
    while schritt < max_schritte and saettigung > 0:
        schritt += 1
        clear_screen(schritt)
        
        # Knurren prüfen
        knurrt = satte_pruefung(saettigung) and random.random() < 0.3
        
        # Feder zeichnen
        feder = draw_feder(saettigung, schritt)
        
        # Balken zeichnen
        bar = draw_bar(saettigung, 24, waerme)
        waerme_bar = draw_waerme_bar(waerme, 10, 12)
        
        # Magen zeichnen
        magen = draw_stomach(saettigung, knurrt, waerme, schritt)
        
        # Ausgabe
        print(f"Schritt: {schritt}/{max_schritte}")
        print(f"Sättigung: {bar}  Feder: {feder}")
        print(f"Wärme:     {waerme_bar}")
        print("Magen:")
        print(magen)
        if knurrt:
            print("\n*** Der Magen knurrt! ***")
            if USE_ANSI:
                sys.stdout.write("\a")  # Piep
                sys.stdout.flush()
        
        # Eingabe
        try:
            aktion = input("\nAktion (f=füttern, q=beenden, Enter=weiter): ").strip().lower()
            eingaben += 1
            if eingaben > MAX_EINGABEN:
                print("Maximale Anzahl an Eingaben erreicht.")
                break
        except EOFError:
            print("\nEingabeende erkannt. Tschüss!")
            break
        
        if aktion == 'q':
            print("Bis bald, kleiner Dodo!")
            break
        elif aktion == 'f':
            # Füttern: Sättigung erhöhen, Wärme etwas erhöhen
            saettigung = min(100, saettigung + random.randint(15, 30))
            waerme = min(10, waerme + 1)
            print("Mampf! Das hat gutgetan.")
            pause(0.8)
        
        # Natürlicher Verbrauch
        saettigung = max(0, saettigung - random.randint(5, 15))
        # Wärme nimmt langsam ab
        if waerme > 0 and random.random() < 0.2:
            waerme -= 1
        
        pause(0.3)
    
    if saettigung <= 0:
        clear_screen()
        print("Der Dodo ist vor Hunger ohnmächtig geworden...\n")
        print(draw_stomach(0, False, 0, schritt))
        print("\nSpiel zu Ende. Nächstes Mal besser füttern!")
    else:
        print("\nSimulation beendet. Der Dodo ist zufrieden.")

if __name__ == "__main__":
    main()