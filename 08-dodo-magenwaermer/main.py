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
      Zeile 0: Header "MAGEN"
      Zeile 1: Dampf (animiert, abhängig von Wärme)
      Zeile 2: Obere Magenwand mit Wellen
      Zeile 3: Mittlere Füllung + Peristaltik-Welle
      Zeile 4: Untere Füllung
      Zeile 5: Magenboden
      Zeile 6: Knurren-Text falls aktiv
    """
    reset = "\033[0m" if USE_ANSI else ""
    lines = []
    
    # Zeile 0: Header
    if USE_ANSI:
        lines.append(f"\033[96m{'MAGEN':^22}\033[0m")
    else:
        lines.append(f"{'MAGEN':^22}")
    
    # Zeile 1: Dampf (animiert)
    dampf_phase = (schritt * 0.15) % 1.0
    dampf_chars = ["  ~ ~  ", " ~   ~ ", "~ ~ ~ ~", " ~   ~ "]
    dampf_idx = int(dampf_phase * len(dampf_chars))
    dampf = dampf_chars[dampf_idx]
    if waerme > 5:
        dampf = dampf.replace("~", "≈").replace(" ", "·")
    if USE_ANSI:
        lines.append(f"\033[90m  {dampf}  \033[0m")
    else:
        lines.append(f"  {dampf}  ")
    
    # Füllhöhe berechnen (0-3 für die 3 Körperzeilen)
    fuellhoehe = int((wert / 100) * 3)
    
    # Peristaltik-Welle (läuft von oben nach unten)
    peristaltik_phase = (schritt * 0.2) % 1.0
    peristaltik_pos = int(peristaltik_phase * 3)  # 0, 1, 2 für die 3 Körperzeilen
    
    # Wellen-Offset für seitliches Wackeln
    wellen_phase = (schritt * 0.1) % (2 * math.pi)
    
    # Zeilen 2-4: Körper (3 Zeilen)
    for zeile in range(3):  # 0=oben, 1=mitte, 2=unten
        ist_gefüllt = zeile >= (3 - fuellhoehe)
        ist_peristaltik = (zeile == peristaltik_pos) and (wert > 10)
        
        # Wellenform für linke/rechte Wand
        wellen_offset = int(math.sin(wellen_phase + zeile * 0.8) * 1.5)
        links = "(" + " " * max(0, 1 + wellen_offset)
        rechts = " " * max(0, 1 - wellen_offset) + ")"
        
        if ist_gefüllt:
            # Gefüllte Zeile: Farbe basierend auf Sättigung
            ratio = (zeile + 0.5) / 3.0
            if USE_ANSI:
                farbe = interpolate_color(ratio)
                inhalt = f"{farbe}{'█' * 16}{reset}"
                if ist_peristaltik:
                    inhalt = f"{farbe}{'▓' * 8}{'█' * 8}{reset}"
            else:
                inhalt = "#" * 16
                if ist_peristaltik:
                    inhalt = "@" * 8 + "#" * 8
        else:
            # Leere Zeile
            inhalt = " " * 16
            if ist_peristaltik and USE_ANSI:
                inhalt = f"\033[90m{'.' * 16}{reset}"
            elif ist_peristaltik:
                inhalt = "." * 16
        
        lines.append(f"{links}{inhalt}{rechts}")
    
    # Zeile 5: Magenboden
    wellen_boden = int(math.sin(wellen_phase + 3 * 0.8) * 1.5)
    links_b = "(" + " " * max(0, 1 + wellen_boden)
    rechts_b = " " * max(0, 1 - wellen_boden) + ")"
    if USE_ANSI:
        lines.append(f"\033[90m{links_b}{'▀' * 16}{rechts_b}{reset}")
    else:
        lines.append(f"{links_b}{'_' * 16}{rechts_b}")
    
    # Zeile 6: Knurren
    if knurrt:
        knurr_phase = (schritt * 0.3) % 1.0
        knurr_intens = int(knurr_phase * 3)
        knurr_text = "GRRR" + "R" * knurr_intens
        if USE_ANSI:
            lines.append(f"\033[91m  {knurr_text}  \033[0m")
        else:
            lines.append(f"  {knurr_text}  ")
    else:
        lines.append("")
    
    return "\n".join(lines)


def draw_hunger_skala(wert: int, schritt: int, breite: int = 40) -> str:
    """Zeichnet eine optische Hunger-Skala mit Farbverlauf, Emoji-Markern und pulsierendem Zeiger.
    
    Marker bei 0%, 20%, 50%, 75%, 100% mit Emojis.
    Zeiger pulsiert mit ease_in_out_quad.
    
    Args:
        wert: Hunger/Sättigung 0-100
        schritt: Animationsschritt für Pulsieren
        breite: Gesamtbreite der Skala in Zeichen
    """
    if not USE_ANSI:
        # Fallback: einfacher Textbalken
        pos = int((wert / 100) * (breite - 1))
        bar = "-" * pos + "▶" + "-" * (breite - 1 - pos)
        return f"Hunger: [{bar}] {wert}%"
    
    # Farbverlauf für den Hintergrund der Skala
    bar_parts = []
    for i in range(breite):
        ratio = i / (breite - 1)
        farbe = interpolate_color(ratio)
        bar_parts.append(f"{farbe}━\033[0m")
    bar_bg = "".join(bar_parts)
    
    # Marker-Positionen und Emojis
    marker = [
        (0, "💀"),   # 0% - verhungert
        (20, "😰"),  # 20% - kritisch
        (50, "😐"),  # 50% - okay
        (75, "😊"),  # 75% - gut
        (100, "😋"), # 100% - satt
    ]
    
    # Marker-Zeile über der Skala
    marker_line = ""
    last_pos = 0
    for m_wert, m_emoji in marker:
        m_pos = int((m_wert / 100) * (breite - 1))
        gap = m_pos - last_pos
        if gap > 0:
            marker_line += " " * gap
        marker_line += m_emoji
        last_pos = m_pos + 1  # Emoji nimmt ~1 Zeichenplatz (visuell)
    
    # Pulsierender Zeiger
    puls_phase = (schritt * 0.1) % 1.0
    puls = ease_in_out_quad(puls_phase)
    # Zeiger wechselt zwischen ▶ und ▷ für Puls-Effekt
    zeiger_char = "▶" if puls > 0.5 else "▷"
    zeiger_pos = int((wert / 100) * (breite - 1))
    
    # Zeiger-Zeile
    zeiger_line = " " * zeiger_pos + f"\033[97;1m{zeiger_char}\033[0m"
    
    # Status-Text
    if wert <= 5:
        status = "\033[91;1mAKUT - SOFORT FÜTTERN!\033[0m"
    elif wert <= 20:
        status = "\033[91mSehr hungrig\033[0m"
    elif wert <= 45:
        status = "\033[93mHungrig\033[0m"
    elif wert <= 75:
        status = "\033[92mGut gesättigt\033[0m"
    else:
        status = "\033[92;1mWohlgenährt\033[0m"
    
    return f"Hunger: [{bar_bg}]\n{zeiger_line} {wert:3d}%  Status: {status}"


def main() -> None:
    """Hauptschleife: Magen simulieren, füttern, wärmen, warten."""
    saettigung = 60
    waerme = 0
    schritt = 0
    eingaben = 0
    
    print("🦤 Dodo-Magenwärmer gestartet. Strg+C oder 'q' zum Beenden.")
    print(f"Maximal {MAX_EINGABEN} Aktionen möglich.\n")
    
    while eingaben < MAX_EINGABEN:
        schritt += 1
        
        # Zufällige Veränderungen
        verlust = random.randint(1, 5)
        saettigung = max(0, saettigung - verlust)
        
        if waerme > 0:
            waerme = max(0, waerme - 1)
        
        knurrt = saettigung < 20
        
        clear_screen(schritt)
        
        # Anzeige
        print(draw_stomach(saettigung, knurrt, waerme, schritt))
        print()
        print(draw_bar(saettigung, waerme=waerme))
        print(draw_waerme_bar(waerme))
        print()
        print(draw_hunger_skala(saettigung, schritt))
        print()
        print(f"\033[90mSchritt {schritt} | Feder: {draw_feder(saettigung, schritt)}\033[0m" if USE_ANSI else f"Schritt {schritt} | Feder: {draw_feder(saettigung, schritt)}")
        print()
        
        # Menü
        print("Aktionen: [1] Füttern (+15-25%)  [2] Wärmen (+3 Wärme)  [3] Warten  [q] Quit")
        
        try:
            choice = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n🦤 Dodo watschelt weg. Tschüss!")
            break
        
        eingaben += 1
        
        if choice in ("q", "quit", "exit", "4"):
            print("🦤 Dodo watschelt weg. Tschüss!")
            break
        elif choice == "1":
            futter = random.randint(15, 25)
            saettigung = min(100, saettigung + futter)
            print(f"🦤 *schluck* +{futter}% Sättigung!")
            pause(0.5)
        elif choice == "2":
            waerme = min(10, waerme + 3)
            print("🦤 *kuschelt sich an die Wärmequelle* +3 Wärme")
            pause(0.5)
        elif choice == "3":
            print("🦤 *wartet geduldig*")
            pause(0.3)
        else:
            print("🦤 *versteht nicht* - 1, 2, 3 oder q eingeben")
            pause(0.3)
    
    if eingaben >= MAX_EINGABEN:
        print(f"\n🦤 Maximale Aktionen ({MAX_EINGABEN}) erreicht. Dodo ist jetzt selbstständig.")
    
    # Endstand anzeigen
    clear_screen()
    print(draw_stomach(saettigung, saettigung < 20, waerme, schritt))
    print()
    print(draw_bar(saettigung, waerme=waerme))
    print(draw_hunger_skala(saettigung, schritt))
    print(f"\nEndstand: {saettigung}% Sättigung, {waerme} Wärme nach {schritt} Schritten.")

if __name__ == "__main__":
    main()