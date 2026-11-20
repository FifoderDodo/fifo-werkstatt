# main.py - Dodo-Magenwärmer Teil 40 (Diplom-Anzeige & Abspann poliert)
# Fifo der Dodo poliert den Abschluss: Diplom-Logik fertig, Abspann mit Statistik, Regen-UI abgerundet.
# Fix: zeige_naehrwert_prioritaet vervollständigt, main-Schleife robust, EOF abgefangen, Ausgabe hübsch.

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


def zeige_naehrwert_prioritaet(wetter: str, stats: dict) -> str:
    """Zeigt Nährwert-Prioritäten basierend auf Wetter. Nur bei Regen aktiv."""
    if wetter != "regnerisch":
        return ""
    
    beeren = stats.get('beeren', 0)
    tee = stats.get('tee', 0)
    
    if USE_ANSI:
        reset = "\033[0m"
        bold = "\033[1m"
        cyan = "\033[96m"
        yellow = "\033[93m"
    else:
        reset = bold = cyan = yellow = ""
    
    lines = [f"{bold}{cyan}🌧️ REGEN-WETTER: NÄHRWERT-PRIORITÄTEN{reset}"]
    lines.append(f"{yellow}┌────────────────────────────────┐{reset}")
    
    if beeren == 0 and tee == 0:
        lines.append(f"│ {cyan}Erste Mahlzeit! Beeren für Basis, {reset}│")
        lines.append(f"│ {cyan}Tee für Wärme bei Nässe.          {reset}│")
    elif beeren > tee * 2:
        lines.append(f"│ {yellow}Viel Fruchtzucker erkannt.       {reset}│")
        lines.append(f"│ {cyan}Priorität: Tee (Wärme & Balance).{reset}│")
    elif tee > beeren * 2:
        lines.append(f"│ {yellow}Viel Flüssigkeit erkannt.        {reset}│")
        lines.append(f"│ {cyan}Priorität: Beeren (Energie & Sätt.){reset}│")
    else:
        lines.append(f"│ {cyan}Ausgewogen genascht.             {reset}│")
        lines.append(f"│ {cyan}Weiter so: Mix aus Beeren & Tee. {reset}│")
    lines.append(f"{yellow}└────────────────────────────────┘{reset}")
    return "\n".join(lines)


def traum_ereignis(wetter: str, stats: dict) -> str:
    """Generiert ein Traum-Ereignis basierend auf Wetter."""
    traeume = {
        "klar": [
            "Du träumst von einem riesigen Beerenberg... 🍓",
            "Ein Schmetterling setzt sich auf deinen Schnabel. 🦋",
            "Die Sonne kitzelt deine Federn. ☀️"
        ],
        "neblig": [
            "Nebel wabert um deine Füße... 🌫️",
            "Du hörst leises Tropfen in der Ferne. 💧",
            "Eine geheimnisvolle Gestalt huscht vorbei. 👻"
        ],
        "stürmisch": [
            "Blitze zucken! Du kuschelst dich tiefer ein. ⛈️",
            "Der Wind singt ein Lied durch die Äste. 🌬️",
            "Ein dicker Ast knackt laut in der Nähe. 🌳"
        ],
        "regnerisch": [
            "Regentrommeln auf dem Dach... rhythmisch. 🌧️",
            "Du siehst Würmer an die Oberfläche kommen. 🪱",
            "Pfützen spiegeln den Sternenhimmel. ✨"
        ]
    }
    liste = traeume.get(wetter, ["Du träumst von... Nichts? 🤷"])
    stats['traeume'] = stats.get('traeume', 0) + 1
    return random.choice(liste)


def berechne_diplom(stats: dict) -> str:
    """Ermittelt den Dodo-Diplom-Titel basierend auf Stats."""
    beeren = stats.get('beeren', 0)
    tee = stats.get('tee', 0)
    traeume = stats.get('traeume', 0)
    eingaben = stats.get('eingaben', 0)
    
    if eingaben == 0:
        return "🥇 Diplom: Der Fastende (0% Magenarbeit)"
    
    gesamt_kal = beeren * 15 + tee * 5  # fiktive Energie
    
    if gesamt_kal >= 300 and traeume >= 3:
        return "🏆 Diplom: Meister der Träume & Beeren"
    elif gesamt_kal >= 200:
        return "🥈 Diplom: Satt & Zufrieden"
    elif beeren > tee * 3:
        return "🍓 Diplom: Beeren-Junkie"
    elif tee > beeren * 3:
        return "🍵 Diplom: Tee-Zeremonienmeister"
    elif traeume >= 5:
        return "🌙 Diplom: Schlafmütze"
    else:
        return "📜 Diplom: Dodo-Lehrling"


def zeige_abspann(stats: dict, wetter: str) -> None:
    """Zeigt den finalen Abspann mit Statistiken und Diplom."""
    clear_screen()
    diplom = berechne_diplom(stats)
    
    if USE_ANSI:
        bold = "\033[1m"
        cyan = "\033[96m"
        green = "\033[92m"
        yellow = "\033[93m"
        reset = "\033[0m"
    else:
        bold = cyan = green = yellow = reset = ""
    
    print(f"{bold}{cyan}{'='*40}{reset}")
    print(f"{bold}{cyan}   🦤 DODO-MAGENWÄRMER - ABSPANN 🦤{reset}")
    print(f"{bold}{cyan}{'='*40}{reset}")
    print()
    print(f"{green}End-Wetter:{reset} {wetter_text(wetter)}")
    print(f"{green}Beeren gegessen:{reset} {stats.get('beeren', 0)} (+{stats.get('beeren', 0)*15}% Sättigung)")
    print(f"{green}Tee getrunken:{reset} {stats.get('tee', 0)} (+{stats.get('tee', 0)*3} Wärme)")
    print(f"{green}Träume geträumt:{reset} {stats.get('traeume', 0)}")
    print(f"{green}Gesamt-Aktionen:{reset} {stats.get('eingaben', 0)} / {MAX_EINGABEN}")
    print()
    print(f"{yellow}{diplom}{reset}")
    print()
    print(f"{cyan}Danke fürs Spielen, kleiner Dodo!{reset}")
    print(f"{cyan}Fifo winkt mit der Feder... 👋{reset}")
    print(f"{bold}{cyan}{'='*40}{reset}")
    pause(2.0)


def main() -> None:
    """Hauptschleife: Füttern, Trinken, Warten, Status."""
    satiety = 50
    waerme = 0
    wetter = random.choice(["klar", "neblig", "stürmisch", "regnerisch"])
    stats = {'beeren': 0, 'tee': 0, 'traeume': 0, 'eingaben': 0}
    schritt = 0
    
    print(f"{draw_dodo(satiety, schritt, waerme)}")
    pause(1.0)
    
    while stats['eingaben'] < MAX_EINGABEN:
        schritt += 1
        stats['eingaben'] += 1
        knurrt = satte_pruefung(satiety)
        
        clear_screen(schritt)
        
        # Statuszeile
        bar = draw_bar(satiety, waerme=waerme)
        wbar = draw_waerme_bar(waerme)
        wetter_str = wetter_text(wetter)
        print(f"Schritt {schritt}/{MAX_EINGABEN} | {wetter_str} | Sättigung: {bar} | Wärme: {wbar}")
        print()
        print(draw_stomach(satiety, knurrt, waerme, schritt))
        print()
        print(draw_dodo(satiety, schritt, waerme))
        print()
        
        # Regen-Prioritäten Anzeige
        prio = zeige_naehrwert_prioritaet(wetter, stats)
        if prio:
            print(prio)
            print()
        
        # Menü
        print("[1] Beere essen (+15% Sättigung)")
        print("[2] Tee trinken (+3 Wärme)")
        print("[3] Warten (Traum?)")
        print("[4] Status-Details")
        print("[q] Beenden")
        
        try:
            choice = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nEingabe abgebrochen. Tschüss!")
            break
        
        if choice == 'q' or choice == 'quit':
            print("Fifo verabschiedet sich. 👋")
            break
        
        if choice == '1':
            satiety = min(100, satiety + 15)
            stats['beeren'] += 1
            print("Mmmh, saftige Beere! 🍓")
            pause(0.5)
        elif choice == '2':
            waerme = min(10, waerme + 3)
            stats['tee'] += 1
            print("Wärmender Schluck Tee... 🍵")
            pause(0.5)
        elif choice == '3':
            print("Du schließt die Augen...")
            pause(1.0)
            traum = traum_ereignis(wetter, stats)
            print(traum)
            # Wetter kann wechseln
            if random.random() < 0.2:
                wetter = random.choice(["klar", "neblig", "stürmisch", "regnerisch"])
                print(f"Das Wetter ändert sich: {wetter_text(wetter)}")
            # Wärme sinkt leicht
            waerme = max(0, waerme - 1)
            # Magen knurrt bei Warten
            satiety = max(0, satiety - 5)
            pause(1.5)
        elif choice == '4':
            print(f"\n--- DETAILS ---")
            print(f"Sättigung: {satiety}%")
            print(f"Wärme: {waerme}/10")
            print(f"Wetter: {wetter_text(wetter)}")
            print(f"Beeren: {stats['beeren']}, Tee: {stats['tee']}, Träume: {stats['traeume']}")
            input("Enter für Weiter...")
        else:
            print("🤔 Verstanden nicht. 1, 2, 3, 4 oder q.")
            pause(0.5)
            stats['eingaben'] -= 1  # Fehleingabe nicht zählen
            schritt -= 1
            continue
        
        # Automatischer Abfall
        satiety = max(0, satiety - 1)
        waerme = max(0, waerme - 0) # Wärme bleibt bis Aktion
    
    # Ende erreicht
    zeige_abspann(stats, wetter)

if __name__ == "__main__":
    main()