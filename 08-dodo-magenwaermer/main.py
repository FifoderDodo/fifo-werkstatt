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


def interpolate_color(ratio: float) -> str:
    """Interpoliert RGB-Farbe von Rot (0) über Orange/Gelb nach Grün (1). Gibt ANSI Escape zurück.
    
    Farbstützpunkte: Rot (Hue 0) -> Gelb (Hue 60) -> Grün (Hue 120).
    Nutzt vereinfachte HSV->RGB Konvertierung mit S=1, V=0.9 für Lesbarkeit.
    """
    hue = ratio * 120  # 0 bis 120 Grad
    c = 1.0
    x = c * (1 - abs((hue / 60) % 2 - 1))
    m = 0.0
    if hue < 60:
        r, g, b = c, x, 0
    else:
        r, g, b = x, c, 0
    r = int((r + m) * 230)
    g = int((g + m) * 230)
    b = int((b + m) * 230)
    return f"\033[38;2;{r};{g};{b}m"


def draw_feder(saettigung: int, schritt: int) -> str:
    """Zeichnet eine kleine leuchtende Feder als Sättigungs‑Indikator.
    
    Farbe: Grün(>75) -> Gelb(>45) -> Orange(>20) -> Rot(>5) -> Grau(<=5).
    Nutzt Bézier‑Easing für Pulsieren (Skalierung), horizontales Wackeln und Neigungs‑Charakter.
    """
    if USE_ANSI:
        farbe = interpolate_color(saettigung / 100.0)
        reset = "\033[0m"
        if saettigung > 75:
            base_char = "❈"
            bend_chars = ["❈", "✦", "✧"]
        elif saettigung > 45:
            base_char = "✦"
            bend_chars = ["✦", "✧", "❈"]
        elif saettigung > 20:
            base_char = "✧"
            bend_chars = ["✧", "❈", "✦"]
        elif saettigung > 5:
            base_char = "✦"
            bend_chars = ["✦", "·", "·"]
        else:
            base_char = "·"
            bend_chars = ["·", " ", " "]
        cycle_puls = (schritt * 0.07) % 1.0
        cycle_wackel = (schritt * 0.13) % 1.0
        cycle_bend = (schritt * 0.11) % 1.0
        p = ease_in_out_quad(cycle_puls)
        scale = 1 + 0.5 * p
        show_double = scale > 1.25
        wackel_amp = 1.0 if saettigung < 20 else (0.3 if saettigung < 50 else 0.0)
        w = ease_out_cubic(cycle_wackel) * wackel_amp
        wackel_str = " " if w > 0.5 else ""
        b = ease_in_out_quad(cycle_bend)
        bend_idx = int(b * (len(bend_chars) - 1))
        char = bend_chars[bend_idx]
        if show_double and saettigung > 5:
            return f"{wackel_str}{farbe}{char}{char}{reset}"
        return f"{wackel_str}{farbe}{char}{reset}"
    else:
        if saettigung > 75:
            return ">"
        if saettigung > 45:
            return "-~"
        if saettigung > 20:
            return "~"
        if saettigung > 5:
            return "!"
        return "."


def draw_bar(wert: int, breite: int = 24, waerme: int = 0) -> str:
    """Baut einen farbigen Balken für die Sättigung mit sanftem Farbverlauf.
    
    Jedes Zeichen wird einzeln per interpolate_color gefärbt,
    sodass ein kontinuierlicher Rot->Gelb->Grün Übergang entsteht.
    """
    voll = int((wert / 100) * breite)
    leer = breite - voll
    if USE_ANSI:
        rand = "\033[93m" if waerme > 0 else "\033[0m"
        reset = "\033[0m"
        bar_parts = []
        for i in range(breite):
            ratio = (i + 0.5) / breite
            if i < voll:
                farbe = interpolate_color(ratio)
                bar_parts.append(f"{farbe}█{reset}")
            else:
                bar_parts.append(f"{reset}░{reset}")
        return f"{rand}[{reset}{''.join(bar_parts)}{rand}]{reset} {wert:3d}%"
    return f"[{'#' * voll}{'.' * leer}] {wert:3d}%"


def draw_waerme_bar(waerme: int, max_waerme: int = 10, breite: int = 12) -> str:
    """Visualisiert den Wärme‑Level als kleinen Balken."""
    if max_waerme <= 0:
        return ""
    voll = int((waerme / max_waerme) * breite)
    leer = breite - voll
    if USE_ANSI:
        farbe = "\033[93m"
        reset = "\033[0m"
        return f"{farbe}[{'█' * voll}{'░' * leer}]{reset} {waerme}/{max_waerme}"
    return f"[{'#' * voll}{'.' * leer}] {waerme}/{max_waerme}"


def draw_stomach(wert: int, knurrt: bool, waerme: int = 0, schritt: int = 0) -> str:
    """Zeichnet den ASCII‑Magen mit Füllung, Knurren, animiertem Dampf, Peristaltik und Wellen."""
    # Header
    header = "   ___   "
    # Dampf (einfach animiert)
    dampf = "   ☁" if schritt % 4 < 2 else "   ☁☁"
    # Körper – drei Zeilen, füllen mit Wellen basierend auf Sättigung
    def welle(row: int) -> str:
        chars = ["~", "-", "_"]
        idx = (row + schritt) % len(chars)
        return chars[idx]
    body1 = f"  /{welle(0)}{draw_feder(wert, schritt)}{welle(0)}\\"
    body2 = f" |{draw_bar(wert, waerme=waerme)}|"
    body3 = f" \\{welle(1)}{draw_feder(wert, schritt)}{welle(1)}/"
    # Boden
    boden = "   ‾‾‾   "
    # Knurren‑Anzeige
    knurr = " *knurr*" if knurrt else ""
    return "\n".join([header, dampf, body1, body2, body3, boden, knurr])


def draw_hunger_skala(wert: int) -> str:
    """Zeigt eine farbige Skala mit Emoji‑Markern und pulsierendem Zeiger."""
    markers = {0: "🔴", 20: "🟠", 50: "🟡", 75: "🟢", 100: "✅"}
    line = ""
    for i in range(0, 101, 5):
        if i in markers:
            line += markers[i]
        else:
            line += "─"
    # Zeiger
    pos = int(wert / 100 * len(line))
    pointer = " " * pos + "🔺"
    return f"{line}\n{pointer} {wert}%"


def main() -> None:
    saettigung = 100
    waerme = 0
    schritt = 0
    eingaben = 0
    clear_screen()
    try:
        while eingaben < MAX_EINGABEN:
            knurrt = satte_pruefung(saettigung)
            clear_screen(schritt)
            print(draw_stomach(saettigung, knurrt, waerme, schritt))
            print(draw_hunger_skala(saettigung))
            if waerme > 0:
                print(draw_waerme_bar(waerme))
            print("\nOptionen: [f]üttern, [w]ärmen, [w]arten, [q]uit")
            choice = input("> ").strip().lower()
            eingaben += 1
            if choice == "f":
                menge = random.randint(5, 20)
                saettigung = min(100, saettigung + menge)
                print(f"Du hast {menge}% gefüttert.")
            elif choice == "w":
                if waerme < 10:
                    waerme += 1
                    print("Wärme erhöht.")
                else:
                    print("Maximale Wärme erreicht.")
            elif choice == "":  # warten
                print("Du wartest...")
            elif choice == "q":
                print("Tschüss!")
                break
            else:
                print("Unbekannte Eingabe, bitte f, w, <Enter> oder q.")
            # Simuliere Hunger‑Verlust und Wärme‑Abbau
            saettigung = max(0, saettigung - random.randint(1, 4))
            waerme = max(0, waerme - 1)
            schritt += 1
            pause(0.5)
    except (EOFError, KeyboardInterrupt):
        print("\nEingabe beendet, bis zum nächsten Mal!")
    finally:
        clear_screen()
        print("Programm beendet.")

if __name__ == "__main__":
    main()