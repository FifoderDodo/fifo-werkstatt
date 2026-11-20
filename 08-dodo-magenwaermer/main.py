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


def draw_hunger_skala(wert: int, schritt: int = 0) -> str:
    """Zeigt eine farbige Skala mit Emoji‑Markern und pulsierendem Zeiger.
    
    Verfeinert: Kontinuierlicher Farbverlauf entlang der Skala, interpolierter Zeiger,
    farblich passend zum aktuellen Wert, plus Legende für Zonen.
    """
    if not USE_ANSI:
        # Fallback ohne ANSI
        markers = {0: "[R]", 20: "[O]", 50: "[Y]", 75: "[G]", 100: "[OK]"}
        line = ""
        for i in range(0, 101, 5):
            if i in markers:
                line += markers[i]
            else:
                line += "-"
        pos = int((wert / 100) * len(line))
        line = line[:pos] + "^" + line[pos+1:]
        return f"{line} {wert}%"
    
    # ANSI-Version mit echter Farbinterpolation
    breite = 60  # Zeichenbreite der Skala
    segments = []
    
    # Baue Skala Zeichen für Zeichen mit Farbverlauf
    for i in range(breite):
        ratio = i / (breite - 1)
        farbe = interpolate_color(ratio)
        # Marker an markanten Stellen
        wert_at_i = int(ratio * 100)
        if wert_at_i in (0, 20, 50, 75, 100) and i % (breite // 4) == 0:
            segments.append(f"{farbe}◆\033[0m")
        else:
            segments.append(f"{farbe}━\033[0m")
    
    skala_str = "".join(segments)
    
    # Pulsierender Zeiger - Position interpoliert
    zeiger_pos = (wert / 100) * (breite - 1)
    zeiger_idx = int(zeiger_pos)
    
    # Puls-Animation für Zeiger
    puls = (schritt * 0.15) % 1.0
    puls_eased = ease_in_out_quad(puls)
    zeiger_chars = ["▼", "▽", "▼", "▽"]
    zeiger_char = zeiger_chars[int(puls_eased * 3)]
    
    # Zeiger-Farbe passend zum Wert
    zeiger_farbe = interpolate_color(wert / 100.0)
    
    # Baue Zeiger-Zeile
    zeiger_line = "" 
    for i in range(breite):
        if i == zeiger_idx:
            zeiger_line += f"{zeiger_farbe}{zeiger_char}\033[0m"
        elif i == zeiger_idx + 1 and (zeiger_pos - zeiger_idx) > 0.5:
            # Interpolation zwischen zwei Positionen
            zeiger_line += f"{zeiger_farbe}{zeiger_char}\033[0m"
        else:
            zeiger_line += " "
    
    # Zonen-Legende
    zones = [
        (0, 20, "🔴 Kritisch", "\033[38;2;230;0;0m"),
        (20, 50, "🟠 Niedrig", "\033[38;2;230;115;0m"),
        (50, 75, "🟡 Mittel", "\033[38;2;230;230;0m"),
        (75, 100, "🟢 Gut", "\033[38;2;0;230;0m"),
    ]
    
    # Finde aktuelle Zone
    aktuelle_zone = ""
    for start, end, label, farbe in zones:
        if start <= wert < end or (wert == 100 and end == 100):
            aktuelle_zone = f"{farbe}{label}\033[0m"
            break
    
    return f"{skala_str}\n{zeiger_line} {zeiger_farbe}{wert:3d}%\033[0m  {aktuelle_zone}"


def main() -> None:
    """Hauptschleife: Magen füttern, wärmen, warten – bis 20 Eingaben oder Abbruch."""
    saettigung = 50
    waerme = 0
    schritt = 0
    eingaben = 0
    
    print("🦤 Dodo-Magenwärmer gestartet. Strg+C oder 'q' zum Beenden.")
    
    while eingaben < MAX_EINGABEN:
        try:
            clear_screen(schritt)
            knurrt = satte_pruefung(saettigung)
            print(draw_stomach(saettigung, knurrt, waerme, schritt))
            print()
            print(draw_hunger_skala(saettigung, schritt))
            print()
            print(draw_waerme_bar(waerme))
            print()
            print(f"Eingaben: {eingaben}/{MAX_EINGABEN}")
            print("Optionen: [f]üttern, [w]ärmen, [Enter]warten, [q]uit")
            
            inp = input("> ").strip().lower()
            eingaben += 1
            schritt += 1
            
            if inp == 'q' or inp == 'quit':
                print("🦤 Dodo watschelt weg. Tschüss!")
                break
            elif inp == 'f':
                saettigung = min(100, saettigung + random.randint(10, 25))
                waerme = min(10, waerme + 1)
                print("🍎 Mampf! Sättigung steigt.")
                pause(0.5)
            elif inp == 'w':
                waerme = min(10, waerme + 2)
                saettigung = max(0, saettigung - 2)
                print("🔥 Wärmekissen aktiviert.")
                pause(0.5)
            elif inp == '' or inp == 'warten':
                saettigung = max(0, saettigung - random.randint(1, 5))
                waerme = max(0, waerme - 1)
                print("⏳ Zeit vergeht... Magen knurrt leiser.")
                pause(0.5)
            else:
                print("Unbekannte Eingabe, bitte f, w, <Enter> oder q.")
                pause(0.5)
        except EOFError:
            print("\n🦤 Eingabe zu Ende. Dodo schläft ein. Gute Nacht!")
            break
        except KeyboardInterrupt:
            print("\n🦤 Abgebrochen. Dodo watschelt weg.")
            break
    else:
        print(f"\n🦤 {MAX_EINGABEN} Eingaben erreicht. Dodo ist satt und zufrieden.")


if __name__ == "__main__":
    main()