# main.py - Dodo-Magenwärmer Teil 43 (Leuchtende Sättigungs-Feder)
# Fifo der Dodo krönt das UI mit einer kleinen, lebendigen Feder,
# die von sattem Grün über Gelb/Orange bis hin zu kränklichem Grau wechselt.
# Die Feder pulsiert leicht und steht als ikonischer Indikator links vom Balken.
# Diplom, Abspann, Kritische Warnung, HUD, Input-Handling bleiben stabil.
# EOF abgefangen, max 20 Eingaben.

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


def draw_feder(saettigung: int, schritt: int) -> str:
    """Zeichnet eine kleine leuchtende Feder als Sättigungs-Indikator.
    Farbe: Grün(>75) -> Gelb(>45) -> Orange(>20) -> Rot(>5) -> Grau(<=5).
    Pulsiert leicht (Skalierung) und wackelt bei kritischem Hunger."""
    # Farbstufen
    if USE_ANSI:
        if saettigung > 75:
            farbe = "\033[92m"      # Hellgrün
            char = "❈"
        elif saettigung > 45:
            farbe = "\033[93m"      # Gelb
            char = "✦"
        elif saettigung > 20:
            farbe = "\033[38;5;208m" # Orange
            char = "✧"
        elif saettigung > 5:
            farbe = "\033[91m"      # Rot
            char = "✦"
        else:
            farbe = "\033[90m"      # Dunkelgrau
            char = "·"
        reset = "\033[0m"
        
        # Pulsieren: Grösse wechseln (1-2 Zeichen Breite)
        # Wackeln bei < 20%
        wackel = ""
        if saettigung < 20 and (schritt % 4) < 2:
            wackel = " "
        
        # Puls Effekt: Alle 6 Schritte kurz grösser/heller
        puls = (schritt // 3) % 2 == 0
        if puls and saettigung > 5:
            return f"{wackel}{farbe}{char}{char}{reset}"
        return f"{wackel}{farbe}{char}{reset}"
    else:
        # Fallback ASCII
        if saettigung > 75: return ">"
        if saettigung > 45: return "-"
        if saettigung > 20: return "~"
        if saettigung > 5:  return "!"
        return "."


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
    
    lines = [f"{bold}🌿 NÄHRWERT-HUD {wetter_text(wetter)}{reset}"]
    
    # Empfehlungslogik
    if saettigung < 20:
        prio = f"{red}NOTFALL: Sofort essen!{reset}"
        tipp = f"Beeren: {beeren} | Tee: {tee}"
    elif saettigung < 50:
        prio = f"{yellow}Hunger wächst. Snack empfohlen.{reset}"
        tipp = f"Beeren: {beeren} (Enter=Essen)"
    elif waerme < 3 and wetter in ["regnerisch", "stürmisch", "neblig"]:
        prio = f"{cyan}Kühl. Tee wärmt.{reset}"
        tipp = f"Tee: {tee} (t=Trinken)"
    else:
        prio = f"{green}Alles im grünen Bereich.{reset}"
        tipp = f"Vorrat: B:{beeren} T:{tee}"
    
    lines.append(f"  Status: {prio}")
    lines.append(f"  Tipp:   {dim}{tipp}{reset}")
    return "\n".join(lines)


def traum_ereignis(saettigung: int, waerme: int, wetter: str, stats: dict, schritt: int) -> tuple[int, int, str, dict]:
    """Simuliert einen Traumpfad-Schritt: Verdauung, Wetterwechsel, Events.
    Gibt neue Werte zurück."""
    clear_screen(schritt)
    
    # 1. Kritische Warnung ganz oben
    warn = zeige_kritisch_warnung(saettigung, schritt)
    if warn:
        print(warn)
    
    # 2. Dodo & Magen Zeichnen
    knurrt = saettigung < 30 and random.random() < 0.3
    print(draw_dodo(saettigung, schritt, waerme))
    print(draw_stomach(saettigung, knurrt, waerme, schritt))
    
    # 3. UI Leiste: Feder + Balken + Wärme
    feder = draw_feder(saettigung, schritt)
    balken = draw_bar(saettigung, waerme=waerme)
    wbar = draw_waerme_bar(waerme)
    print(f"{feder} Sättigung: {balken}   {wbar}")
    
    # 4. Wetter & HUD
    print(f"Wetter: {wetter_text(wetter)}")
    print(zeige_naehrwert_hud(saettigung, waerme, wetter, stats))
    print("-" * 40)
    
    # 5. Logik Update
    # Verdauung
    saettigung = max(0, saettigung - random.randint(1, 3))
    # Wärmeverlust
    waerme = max(0, waerme - (1 if random.random() < 0.3 else 0))
    # Wetterwechsel
    if random.random() < 0.1:
        wetter = random.choice(["klar", "neblig", "stürmisch", "regnerisch"])
    
    # Event: Beere finden
    if random.random() < 0.15:
        stats['beeren'] = stats.get('beeren', 0) + 1
        print(f"🍇 Du findest eine Traube! Beeren: {stats['beeren']}")
    
    pause(0.3)
    return saettigung, waerme, wetter, stats


def diplom(name: str, stats: dict) -> None:
    """Druckt das Abschluss-Diplom."""
    clear_screen()
    print("╔" + "═" * 38 + "╗")
    print(f"║ {'DODO-MAGENWÄRMER DIPLOM':^36} ║")
    print("╠" + "═" * 38 + "╣")
    print(f"║ {'Ausgestellt für:':^36} ║")
    print(f"║ {name:^36} ║")
    print("╠" + "═" * 38 + "╣")
    print(f"║ {'Beeren genascht: ' + str(stats.get('beeren', 0)):^36} ║")
    print(f"║ {'Tee getrunken: ' + str(stats.get('tee', 0)):^36} ║")
    print(f"║ {'Schritte überlebt: ' + str(stats.get('schritte', 0)):^36} ║")
    print("╚" + "═" * 38 + "╝")
    if USE_ANSI:
        print("\033[92m" + "  🪶 Federleicht und satt! 🪶" + "\033[0m")
    else:
        print("  Federleicht und satt!")


def abspann() -> None:
    """Zeigt den Abspann."""
    print("\n" + "~" * 20)
    print("  Code & Federn: Fifo der Dodo")
    print("  Engine: Python 3 Standardbibliothek")
    print("  Danke fürs Spielen!")
    print("~" * 20)


def main() -> None:
    """Hauptschleife: 20 Schritte oder bis Abbruch."""
    print("🪶 Dodo-Magenwärmer startet... (Strg+C / EOF zum Beenden)")
    pause(0.5)
    
    # Init
    saettigung = 60
    waerme = 5
    wetter = "klar"
    stats = {'beeren': 3, 'tee': 2, 'schritte': 0}
    schritt = 0
    name = "Fifo"
    
    try:
        # Nameingabe am Start
        inp = input("Wie heisst dein Dodo? [Fifo]: ").strip()
        if inp:
            name = inp
        stats['schritte'] = 0
        
        while schritt < MAX_EINGABEN:
            schritt += 1
            stats['schritte'] = schritt
            
            # Simulationschritt
            saettigung, waerme, wetter, stats = traum_ereignis(
                saettigung, waerme, wetter, stats, schritt
            )
            
            # Input Handling
            print("[Enter] Warten  [b] Beere  [t] Tee  [q] Quit")
            try:
                cmd = input("> ").strip().lower()
            except EOFError:
                print("\n🌙 EOF erkannt. Dodo schläft ein.")
                break
            
            if cmd == 'q' or cmd == 'quit':
                print("👋 Tschüss!")
                break
            elif cmd == 'b':
                if stats.get('beeren', 0) > 0:
                    stats['beeren'] -= 1
                    heal = random.randint(15, 30)
                    saettigung = min(100, saettigung + heal)
                    print(f"🍇 Mjam! +{heal}% Sättigung.")
                else:
                    print("🍇 Keine Beeren da!")
                pause(0.5)
            elif cmd == 't':
                if stats.get('tee', 0) > 0:
                    stats['tee'] -= 1
                    waerme = min(10, waerme + 3)
                    print(f"🍵 Schlürf! +3 Wärme.")
                else:
                    print("🍵 Teekanne leer!")
                pause(0.5)
            elif cmd == '':
                # Warten / Schlafen -> kleine Regeneration
                if random.random() < 0.2:
                    saettigung = min(100, saettigung + 1)
                pass
            else:
                print(f"Unbekannt: '{cmd}'")
                pause(0.3)
            
            # Game Over Check
            if saettigung <= 0:
                clear_screen()
                print("\033[91m" + "☠️  Der Magen ist ganz leer... Dodo ist ohnmächtig geworden." + "\033[0m")
                pause(1)
                break
        else:
            # Schleife normal beendet (Max Schritte)
            pass
    except KeyboardInterrupt:
        print("\n🛑 Abbruch durch Nutzer.")
    finally:
        diplom(name, stats)
        abspann()

if __name__ == "__main__":
    main()