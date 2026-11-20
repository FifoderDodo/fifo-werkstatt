# main.py - Dodo-Magenwärmer Teil 42 (Kritische-Hunger-Warnanzeige)
# Fifo der Dodo baut eine pulssende Warnanzeige, wenn der Magen unter 20 % rutscht.
# Neu: zeige_kritisch_warnung() liefert einen grossen, farbigen ASCII-Block,
# der im Hauptloop *vor* dem normalen UI gezeichnet wird (nach clear_screen).
# Diplom, Abspann, Hauptschleife bleiben stabil. EOF abgefangen, max 20 Eingaben.

import random
import time
import sys

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


def draw_bar(wert: int, breite: int = 24, waerme: int = 0) -> str:
    """Baut einen farbigen Balken für die Sättigung, gelber Rand bei Wärme."""
    voll = int((wert / 100) * breite)
    leer = breite - voll
    if USE_ANSI:
        if wert >= 75:
            farbe = "\033[92m"      # Grün
        elif wert >= 45:
            farbe = "\033[93m"      # Gelb
        elif wert >= 20:
            farbe = "\033[38;5;208m" # Orange
        else:
            farbe = "\033[91m"      # Rot
        
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
        farbe = "\033[93m"  # Gelb/Orange für Wärme
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
        if magen_farbe and waerme > 0:
            line = line.replace('\\', magen_farbe + '\\' + reset).replace('//', magen_farbe + '//' + reset).replace('V', magen_farbe + 'V' + reset)
        result.append(line)
    return "\n".join(result)


def draw_dodo(wert: int, schritt: int, waerme: int = 0) -> str:
    """Zeigt das Dodo-Gesicht mit Federkamm, Blinzeln und Wärmelächeln."""
    blinzelt = (schritt % 10) == 0
    augen = "-.- " if blinzelt else "o.o "
    
    if waerme > 0:
        mund = "^_^"
        notiz = " (Warm & kuschelig)"
    elif wert < 20:
        mund = ">_<"
        notiz = " (Magen knurrt!)"
    elif wert < 50:
        mund = "._."
        notiz = " (Könnte 'ne Beere vertragen)"
    else:
        mund = "^_^"
        notiz = " (Pummelig & warm)"
    return f"""   /\\/\\
   {augen}
   ({mund}){notiz}"""


def wetter_text(wetter: str) -> str:
    """Gibt kurzes Wetter-Symbol zurück."""
    return {
        "klar": "☀️ Klartraum",
        "neblig": "🌫️ Nebeltraum",
        "stürmisch": "⛈️ Sturmtraum",
        "regnerisch": "🌧️ Regenguss"
    }.get(wetter, "🌈 Traum")


def zeige_kritisch_warnung(saettigung: int, schritt: int) -> str:
    """Liefert einen grossen, pulsenden Warn-Block bei kritischem Hunger (<20%).
    Nutzt ANSI-Blinken (5m) und Rot (91m) falls TTY, sonst ASCII-Rahmen."""
    if saettigung >= 20:
        return ""
    
    # Pulsieren: alle 4 Schritte an/aus
    sichtbar = (schritt // 2) % 2 == 0
    if not sichtbar:
        return ""
    
    if USE_ANSI:
        # Blinkender roter Hintergrund + weisser Text
        return "\033[5;91;97m" + "═" * 40 + "\033[0m\n" + \
               "\033[5;91;97m  ⚠⚠⚠  KRITISCHER HUNGER  ⚠⚠⚠  \033[0m\n" + \
               "\033[5;91;97m" + "═" * 40 + "\033[0m"
    else:
        return "=" * 40 + "\n  !!! KRITISCHER HUNGER !!!\n" + "=" * 40


def zeige_naehrwert_hud(saettigung: int, waerme: int, wetter: str, stats: dict) -> str:
    """Zeigt kompaktes Nährwert-HUD: Prioritäten basierend auf Zustand & Wetter.
    Ersetzt die alte reine Regen-Box durch kontext-sensitive Empfehlungen."""
    beeren = stats.get('beeren', 0)
    tee = stats.get('tee', 0)
    
    if USE_ANSI:
        reset = "\033[0m"
        bold = "\033[1m"
        dim = "\033[2m"
        red = "\033[91m"
        green = "\033[92m"
        yellow = "\033[93m"
        cyan = "\033[96m"
        blue = "\033[94m"
        orange = "\033[38;5;208m"
    else:
        reset = bold = dim = red = green = yellow = cyan = blue = orange = ""
    
    lines = []
    # Header
    wetter_icon = {"regnerisch": "🌧️", "stürmisch": "⛈️", "neblig": "🌫️", "klar": "☀️"}.get(wetter, "🌈")
    lines.append(f"{bold}{cyan}{wetter_icon} NÄHRWERT-HUD {wetter.upper()}{reset} {dim}(B:{beeren} T:{tee}){reset}")
    
    # Status-Zeile
    sat_status = f"{green}Satt{reset}" if saettigung >= 75 else f"{yellow}Okay{reset}" if saettigung >= 45 else f"{orange}Hunger{reset}" if saettigung >= 20 else f"{red}Kritisch{reset}"
    wae_status = f"{yellow}Warm{reset}" if waerme >= 5 else f"{blue}Kühl{reset}" if waerme > 0 else f"{dim}Kalt{reset}"
    lines.append(f"  Sättigung: {sat_status}  |  Wärme: {wae_status}")
    
    # Prioritäten
    prio = []
    if saettigung < 20:
        prio.append(f"{red}1. SOFORT ESSEN! (Beeren: {beeren}){reset}")
    elif saettigung < 45:
        prio.append(f"{orange}1. Beere essen ({beeren} da){reset}" if beeren > 0 else f"{orange}1. Futter suchen...{reset}")
    
    if waerme == 0 and wetter in ("regnerisch", "stürmisch", "neblig"):
        prio.append(f"{blue}2. Tee trinken ({tee} da) für Wärme{reset}" if tee > 0 else f"{blue}2. Wärmequelle suchen!{reset}")
    elif waerme < 3 and wetter == "klar":
        prio.append(f"{dim}2. Sonnenbad geniessen☀️{reset}")
    
    if not prio:
        prio.append(f"{green}✓ Alles im grünen Bereich.{reset}")
    
    for p in prio:
        lines.append(f"  {p}")
    
    return "\n".join(lines)


def traum_ereignis(saettigung: int, waerme: int, wetter: str, stats: dict, schritt: int) -> tuple[int, int, str, dict]:
    """Simuliert einen Traum-Schritt: Wetterwechsel, Knurren, Verbrauch, Funde."""
    # Wetter ändert sich manchmal
    if random.random() < 0.15:
        wetter = random.choice(["klar", "neblig", "stürmisch", "regnerisch"])
    
    # Sättigung sinkt
    verlust = random.randint(1, 4)
    if wetter == "stürmisch":
        verlust += 2
    elif wetter == "regnerisch":
        verlust += 1
    saettigung = max(0, saettigung - verlust)
    
    # Wärme sinkt
    if waerme > 0:
        waerme = max(0, waerme - (1 if random.random() < 0.3 else 0))
    
    # Knurren
    knurrt = satte_pruefung(saettigung) and random.random() < 0.6
    
    # Zufallsfunde
    fund_text = ""
    if random.random() < 0.1:
        stats['beeren'] = stats.get('beeren', 0) + 1
        fund_text = "🍇 Eine Beere plumpst in den Schnabel!"
    elif random.random() < 0.05:
        stats['tee'] = stats.get('tee', 0) + 1
        fund_text = "🍵 Ein Teebeutel segelt heran!"
    
    # Ausgabe
    clear_screen(schritt)
    
    # TEIL 42: Warnanzeige GANZ OBEN bei kritischem Hunger
    warnung = zeige_kritisch_warnung(saettigung, schritt)
    if warnung:
        print(warnung)
        print()
    
    print(draw_stomach(saettigung, knurrt, waerme, schritt))
    print()
    print(draw_dodo(saettigung, schritt, waerme))
    print()
    print(f"Sättigung: {draw_bar(saettigung, waerme=waerme)}")
    if waerme > 0:
        print(f"Wärme:     {draw_waerme_bar(waerme)}")
    print(f"Wetter:    {wetter_text(wetter)}")
    print()
    print(zeige_naehrwert_hud(saettigung, waerme, wetter, stats))
    if fund_text:
        print(f"\n{fund_text}")
    
    pause(0.6)
    return saettigung, waerme, wetter, stats


def diplom(saettigung: int, stats: dict) -> None:
    """Druckt das Abschluss-Diplom."""
    clear_screen()
    print("╔" + "═" * 38 + "╗")
    print("║" + " DODO-MAGENWÄRMER - DIPLOM ".center(38) + "║")
    print("╠" + "═" * 38 + "╣")
    print(f"║ {'End-Sättigung: ' + str(saettigung) + '%'.center(38)} ║")
    print(f"║ {'Beeren gesamt: ' + str(stats.get('beeren', 0)).center(38)} ║")
    print(f"║ {'Tee getrunken: ' + str(stats.get('tee', 0)).center(38)} ║")
    print("╚" + "═" * 38 + "╝")
    if saettigung >= 50:
        print("\n🎓 Fifo ist stolz: Du hast den Magen warm gehalten!")
    else:
        print("\n📚 Nächstes Mal mehr Beeren, kleiner Dodo.")
    pause(1.5)


def abspann() -> None:
    """Kleiner Abspann mit Credits."""
    clear_screen()
    texte = [
        "",
        "   ~~~ DODO-MAGENWÄRMER ~~~",
        "",
        "   Idee & Code: Fifo der Dodo",
        "   ASCII-Art:   Feder & Schnabel",
        "   Sound:       Magenknurren (im Kopf)",
        "",
        "   Danke fürs Spielen!",
        "",
        "   (Drück Enter zum Ende)"
    ]
    for zeile in texte:
        print(zeile)
        pause(0.2)
    try:
        input()
    except EOFError:
        pass


def main() -> None:
    """Hauptschleife: 20 Schritte oder bis EOF."""
    random.seed(42)  # Reproduzierbar für Tests
    
    saettigung = 100
    waerme = 0
    wetter = "klar"
    stats = {'beeren': 3, 'tee': 2}
    
    print("🐦 Dodo-Magenwärmer startet... (Strg+C / EOF zum Abbruch)")
    pause(1.0)
    
    for schritt in range(1, MAX_EINGABEN + 1):
        try:
            # Traum-Schritt simulieren
            saettigung, waerme, wetter, stats = traum_ereignis(
                saettigung, waerme, wetter, stats, schritt
            )
            
            # Eingabe-Möglichkeit (nur Demo, keine echte Logik nötig)
            if USE_ANSI and schritt < MAX_EINGABEN:
                print(f"\n[Schritt {schritt}/{MAX_EINGABEN}] Enter für weiter... (e=essen, t=tee, q=quit)", end=" ", flush=True)
                try:
                    eingabe = input().strip().lower()
                    if eingabe == 'q':
                        break
                    elif eingabe == 'e' and stats.get('beeren', 0) > 0:
                        stats['beeren'] -= 1
                        saettigung = min(100, saettigung + random.randint(15, 25))
                        print("🍇 Mjam!")
                        pause(0.4)
                    elif eingabe == 't' and stats.get('tee', 0) > 0:
                        stats['tee'] -= 1
                        waerme = min(10, waerme + random.randint(3, 5))
                        print("🍵 Schlürf, warm!")
                        pause(0.4)
                except EOFError:
                    print("\nEOF erkannt.")
                    break
            
            # Spielende bei 0%
            if saettigung <= 0:
                print("\n💀 Der Magen ist ganz leer... Fifo schläft ein.")
                pause(1.0)
                break
        except KeyboardInterrupt:
            print("\nAbbruch.")
            break
    
    diplom(saettigung, stats)
    abspann()

if __name__ == "__main__":
    main()