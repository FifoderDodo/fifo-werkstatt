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
    
    # Auf 0-255 skalieren, V=0.9 (230) für angenehme Helligkeit
    r = int((r + m) * 230)
    g = int((g + m) * 230)
    b = int((b + m) * 230)
    return f"\033[38;2;{r};{g};{b}m"


def draw_feder(saettigung: int, schritt: int) -> str:
    """Zeichnet eine kleine leuchtende Feder als Sättigungs-Indikator.
    
    Farbe: Grün(>75) -> Gelb(>45) -> Orange(>20) -> Rot(>5) -> Grau(<=5).
    Nutzt Bézier-Easing für Pulsieren (Skalierung), horizontales Wackeln und Neigungs-Charakter.
    
    Args:
        saettigung: Aktueller Sättigungswert 0-100
        schritt: Animationsschritt für zyklische Effekte
    """
    if USE_ANSI:
        # Basisfarbe über Interpolation für sanften Übergang
        farbe = interpolate_color(saettigung / 100.0)
        reset = "\033[0m"
        
        # Zeichenwahl basierend auf Sättigung (grobe Stufen für Charakter)
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
        
        # Animations-Zyklen mit verschiedenen Frequenzen
        cycle_puls = (schritt * 0.07) % 1.0
        cycle_wackel = (schritt * 0.13) % 1.0
        cycle_bend = (schritt * 0.11) % 1.0
        
        # 1. Pulsieren: ease_in_out_quad für sanftes An-/Abschwellten
        p = ease_in_out_quad(cycle_puls)
        scale = 1 + 0.5 * p
        show_double = scale > 1.25
        
        # 2. Horizontales Wackeln: nur bei niedriger Sättigung stark
        wackel_amp = 1.0 if saettigung < 20 else (0.3 if saettigung < 50 else 0.0)
        w = ease_out_cubic(cycle_wackel) * wackel_amp
        wackel_str = " " if w > 0.5 else ""
        
        # 3. Neigung: Zeichenwechsel für 'Biegen' der Feder
        b = ease_in_out_quad(cycle_bend)
        bend_idx = int(b * (len(bend_chars) - 1))
        char = bend_chars[bend_idx]
        
        if show_double and saettigung > 5:
            return f"{wackel_str}{farbe}{char}{char}{reset}"
        return f"{wackel_str}{farbe}{char}{reset}"
    else:
        # Fallback ohne ANSI
        if saettigung > 75: return ">"
        if saettigung > 45: return "-~"
        if saettigung > 20: return "~"
        if saettigung > 5:  return "!"
        return "."


def draw_bar(wert: int, breite: int = 24, waerme: int = 0) -> str:
    """Baut einen farbigen Balken für die Sättigung mit sanftem Farbverlauf.
    
    Jedes Zeichen wird einzeln per interpolate_color gefärbt,
    sodass ein kontinuierlicher Rot->Gelb->Grün Übergang entsteht.
    
    Args:
        wert: Sättigung 0-100
        breite: Balkenbreite in Zeichen
        waerme: Wenn >0, gelber Rand als Wärme-Indikator
    """
    voll = int((wert / 100) * breite)
    leer = breite - voll
    if USE_ANSI:
        rand = "\033[93m" if waerme > 0 else "\033[0m"
        reset = "\033[0m"
        bar_parts = []
        for i in range(breite):
            ratio = (i + 0.5) / breite  # Mitte des Zeichens für gleichmäßige Verteilung
            if i < voll:
                farbe = interpolate_color(ratio)
                bar_parts.append(f"{farbe}█{reset}")
            else:
                bar_parts.append(f"{reset}░{reset}")
        return f"{rand}[{reset}{''.join(bar_parts)}{rand}]{reset} {wert:3d}%"
    return f"[{'#' * voll}{'.' * leer}] {wert:3d}%"


def draw_waerme_bar(waerme: int, max_waerme: int = 10, breite: int = 12) -> str:
    """Visualisiert den Wärme-Level als kleinen Balken.
    
    Args:
        waerme: Aktueller Wärme-Wert
        max_waerme: Maximale Kapazität (default 10)
        breite: Anzeigebreite in Zeichen
    """
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
    """Zeichnet den ASCII-Magen mit Füllung, Knurren, animiertem Dampf, Peristaltik und Wellen.
    
    Struktur (6 Zeilen Körper + Header):
    
    Zeile 0: Header mit Feder-Indikator
    Zeile 1: Oberer Rand mit Dampf
    Zeile 2-3: Magenkörper mit Füllstand-Wellen
    Zeile 4: Unterer Rand mit Peristaltik
    Zeile 5: Knurren-Anzeige
    """
    if not USE_ANSI:
        # Einfacher Fallback
        voll = int((wert / 100) * 20)
        leer = 20 - voll
        bauch = "[" + "#" * voll + "." * leer + "]"
        knurr = " (KNURRT!)" if knurrt else ""
        return f"Magen: {bauch} {wert}%{knurr}"
    
    reset = "\033[0m"
    feder = draw_feder(wert, schritt)
    
    # Dampf-Animation oben
    dampf_phase = (schritt * 0.15) % 1.0
    dampf_chars = ["  ~  ", " ~ ~ ", "~   ~", " ~ ~ "]
    dampf_idx = int(dampf_phase * (len(dampf_chars) - 1))
    dampf = dampf_chars[dampf_idx] if wert > 10 else "     "
    
    # Füllstand für Wellen
    fuell_hoehe = int((wert / 100) * 3)  # 0-3 Zeilen Füllung
    
    # Wellen-Animation
    wellen_phase = (schritt * 0.2) % 1.0
    wellen = "~" if wellen_phase > 0.5 else "─"
    
    lines = []
    
    # Header
    lines.append(f"  {feder}  Dodo-Magen  {feder}  {draw_waerme_bar(waerme)}")
    
    # Oberer Rand mit Dampf
    rand_farbe = "\033[93m" if waerme > 0 else "\033[36m"
    lines.append(f" {rand_farbe}╭{dampf}╮{reset}")
    
    # Magenkörper - 3 Zeilen
    for zeile in range(3):
        # Obere Zeile (zeile=0) ist am höchsten
        ist_gefüllt = (2 - zeile) < fuell_hoehe
        
        if ist_gefüllt:
            # Wellen in Füllfarbe
            ratio = (fuell_hoehe - (2 - zeile)) / 3.0
            wellen_farbe = interpolate_color(ratio)
            inhalt = f"{wellen_farbe}{wellen * 7}{reset}"
        else:
            # Leer: dunkler Hintergrund
            inhalt = f"\033[90m{' ' * 7}{reset}"
        
        # Peristaltik-Wackeln an den Seiten
        peristaltik = (schritt * 0.3 + zeile * 0.5) % 1.0
        links = "(" if peristaltik > 0.5 else "<"
        rechts = ")" if peristaltik > 0.5 else ">"
        
        lines.append(f"{rand_farbe}{links}{reset}{inhalt}{rand_farbe}{rechts}{reset}")
    
    # Unterer Rand
    boden_welle = "~" if (schritt * 0.25) % 1.0 > 0.5 else "╰╯"
    lines.append(f" {rand_farbe}╰{boden_welle * 5}╯{reset}")
    
    # Knurren-Zeile
    if knurrt:
        knurr_phase = (schritt * 0.4) % 1.0
        knurr_intensität = int(knurr_phase * 3) + 1
        knurr_str = "\033[91m" + "⚡" * knurr_intensität + " KNURRT! " + "⚡" * knurr_intensität + reset
        lines.append(f"   {knurr_str}")
    else:
        lines.append(f"   \033[90m...ruhig...{reset}")
    
    return "\n".join(lines)


def draw_hunger_skala(wert: int, schritt: int = 0) -> str:
    """Zeichnet eine horizontale Hunger-Skala mit Markierungen und aktuellem Wert.
    
    Skala: 0 (verhungert) ---- 20 (knurrt) ---- 50 (ok) ---- 75 (satt) ---- 100 (voll)
    """
    if not USE_ANSI:
        pos = int((wert / 100) * 40)
        skala = "[" + "-" * pos + "▶" + "-" * (40 - pos) + "]"
        return f"Hunger: {skala} {wert}%"
    
    reset = "\033[0m"
    breite = 50
    
    # Skala bauen
    skala_teile = []
    for i in range(breite):
        ratio = i / (breite - 1)
        farbe = interpolate_color(ratio)
        skala_teile.append(f"{farbe}▓{reset}")
    
    # Marker-Positionen
    marker_pos = {
        0: "💀",
        20: "😰",
        50: "😐",
        75: "😊",
        100: "😋"
    }
    
    # Aktuelle Position
    aktuelle_pos = int((wert / 100) * (breite - 1))
    
    # Marker-Zeile über der Skala
    marker_line = [" " for _ in range(breite)]
    for m_wert, m_char in marker_pos.items():
        m_pos = int((m_wert / 100) * (breite - 1))
        if 0 <= m_pos < breite:
            marker_line[m_pos] = m_char
    
    # Aktueller Zeiger mit Pulsieren
    puls = ease_in_out_quad((schritt * 0.1) % 1.0)
    zeiger = "▼" if puls > 0.5 else "▽"
    marker_line[aktuelle_pos] = f"\033[97;1m{zeiger}{reset}"
    
    marker_str = "".join(marker_line)
    skala_str = "".join(skala_teile)
    
    # Legende
    legende = f"\033[90m0{reset}         \033[91m20{reset}         \033[93m50{reset}         \033[92m75{reset}         \033[92m100{reset}"
    
    return f"Hunger-Skala:\n{marker_str}\n{skala_str}\n{legende}  {wert}%"


def main() -> None:
    """Hauptschleife: Dodo-Magenwärmer Simulation."""
    saettigung = 60
    waerme = 0
    schritt = 0
    eingaben = 0
    
    print("🦤 Dodo-Magenwärmer gestartet. Strg+C zum Beenden.\n")
    
    try:
        while eingaben < MAX_EINGABEN:
            clear_screen(schritt)
            
            # Zufällige Ereignisse
            if random.random() < 0.15:
                saettigung = max(0, saettigung - random.randint(1, 5))
            if random.random() < 0.1:
                waerme = min(10, waerme + 1)
            
            knurrt = satte_pruefung(saettigung)
            
            # Ausgabe
            print(draw_stomach(saettigung, knurrt, waerme, schritt))
            print()
            print(draw_bar(saettigung, waerme=waerme))
            print()
            print(draw_hunger_skala(saettigung, schritt))
            print()
            
            # Status-Text
            if saettigung <= 5:
                status = "\033[91mKRITISCH! Sofort füttern!\033[0m"
            elif saettigung <= 20:
                status = "\033[93mKnurrt laut...\033[0m"
            elif saettigung <= 50:
                status = "\033[36mEtwas hungrig.\033[0m"
            elif saettigung <= 75:
                status = "\033[92mGut gesättigt.\033[0m"
            else:
                status = "\033[92m😋 Rundum satt!\033[0m"
            print(f"Status: {status}")
            print(f"\033[90mSchritt {schritt} | Eingaben: {eingaben}/{MAX_EINGABEN}\033[0m")
            
            # Eingabe
            try:
                print("\nAktionen: [f]üttern, [w]ärmen, [w]arten, [q]uit")
                cmd = input("> ").strip().lower()
                eingaben += 1
                
                if cmd in ("q", "quit", "exit"):
                    print("\n🦤 Dodo watschelt davon. Tschüss!")
                    break
                elif cmd in ("f", "fuettern", "füttern", "feed"):
                    menge = random.randint(10, 25)
                    saettigung = min(100, saettigung + menge)
                    print(f"\n🍎 Gefüttert! +{menge}% Sättigung.")
                    pause(0.8)
                elif cmd in ("w", "waermen", "wärmen", "warm"):
                    if waerme < 10:
                        waerme += 1
                        print(f"\n🔥 Wärme erhöht: {waerme}/10")
                    else:
                        print("\n🔥 Bereits maximale Wärme!")
                    pause(0.6)
                elif cmd in ("", "wait", "warten", "w", "warter"):
                    print("\n⏳ Warten...")
                    pause(0.4)
                else:
                    print(f"\n❓ Unbekannt: '{cmd}'. Versuche f, w, oder q.")
                    pause(0.6)
            
            except EOFError:
                print("\n🦤 Eingabeende. Dodo schläft ein. Gute Nacht!")
                break
            except KeyboardInterrupt:
                print("\n🦤 Unterbrochen. Dodo watschelt weg.")
                break
            
            schritt += 1
            pause(0.1)
    
    except KeyboardInterrupt:
        print("\n🦤 Dodo wird weggedrückt. Bis bald!")
    
    print("\n--- Ende der Session ---")


if __name__ == "__main__":
    main()