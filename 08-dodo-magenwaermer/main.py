# main.py - Dodo-Magenwärmer Teil 38 (Finaler Schliff & Projektabschluss)
# Fifo der Dodo putzt die letzte Feder zurecht: Diplom-Logik vollendet, Highscore dauerhaft im RAM,
# schicker Abspann, saubere Statuszeile. Das Ei ist ausgebrütet – das Projekt ist fertig!
# Fix: berechne_diplom vervollständigt, main() robust, Abspann-Funktion neu, Statusanzeige poliert.

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
        "stürmisch": "⛈️ Sturmtraum"
    }.get(wetter, "🌈 Traum")


def traum_ereignis(stats: dict, wetter: str) -> tuple[int, int, str]:
    """Würfelt ein Traum-Ereignis. Gibt IMMER (delta_sat, delta_waerme, nachricht)."""
    chance = 0.15
    if wetter == "stürmisch":
        chance = 0.25
    elif wetter == "neblig":
        chance = 0.10
    
    if random.random() < chance:
        stats['events'] = stats.get('events', 0) + 1
        r = random.random()
        if r < 0.35:
            return (10, 0, "✨ Traum-Beere gefunden! +10% Sättigung")
        elif r < 0.65:
            return (0, 3, "🍵 Dampfender Traum-Tee erscheint! +3 Wärme")
        elif r < 0.85:
            return (-5, 0, "👻 Albtraum! Magen zieht sich zusammen -5% Sättigung")
        else:
            return (5, 1, "🦋 Schmetterling summt beruhigend. +5% Sättigung, +1 Wärme")
    return (0, 0, "")


def draw_pokal(grad: str) -> str:
    """ASCII Pokal je nach Diplom-Grad."""
    pokale = {
        "Platin": """      |~~~|
      |     |
      |  #1 |
      |_____|
     /  ___  \\
    /  /   \\  \\
   |  |     |  |
   |  |_____|  |
    \\        //
     `"""""""`""",
        "Gold": """      |~~~|
      |     |
      |  1. |
      |_____|
     /  ___  \\
    /  /   \\  \\
   |  |     |  |
    \\       //
     `"""""""`""",
        "Silber": """      |~~~|
      |  2. |
      |_____|
     /  ___  \\
    /  /   \\  \\
   |  |     |  |
    \\       //
     `"""""""`""",
        "Bronze": """      |~~~|
      |  3. |
      |_____|
     /  ___  \\
    /  /   \\  \\
    \\       //
     `"""""""`""",
        "Teilnahme": """      |~~~|
      |     |
      |_____|
     /  ___  \\
    /  /   \\  \\
    \\       //
     `"""""""`"""
    }
    return pokale.get(grad, pokale["Teilnahme"])


def berechne_diplom(stats: dict) -> tuple[str, int]:
    """Berechnet Diplom-Grad basierend auf Stats. Gibt (Grad, Punkte)."""
    punkte = 0
    # Basis: Durchschnittliche Sättigung (0-100 Pkt)
    avg_sat = stats.get('sat_sum', 0) / max(1, stats.get('steps', 1))
    punkte += int(avg_sat * 0.5)
    
    # Wärme-Phasen Bonus (pro Schritt mit Wärme > 0)
    punkte += stats.get('warm_phases', 0) * 10
    
    # Events erlebt
    punkte += stats.get('events', 0) * 5
    
    # Knurr-Count Malus (weniger ist besser)
    punkte -= stats.get('knurr_count', 0) * 3
    
    # Eingaben-Effizienz (weniger Eingaben bei hohem Score = besser)
    eingaben = stats.get('eingaben', 0)
    if eingaben > 0 and stats.get('steps', 0) > 0:
        effizienz = stats['steps'] / eingaben
        punkte += int(effizienz * 2)
    
    # Beeren/Tees verbraucht
    punkte += stats.get('beeren', 0) * 2
    punkte += stats.get('tees', 0) * 3
    
    punkte = max(0, punkte)
    
    if punkte >= 300:
        return ("Platin", punkte)
    elif punkte >= 200:
        return ("Gold", punkte)
    elif punkte >= 120:
        return ("Silber", punkte)
    elif punkte >= 60:
        return ("Bronze", punkte)
    else:
        return ("Teilnahme", punkte)


def zeige_abspann() -> None:
    """Zeigt den finalen Abspann mit Credits."""
    clear_screen()
    text = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║     🦤  D O D O - M A G E N W Ä R M E R   v1.0  🦤          ║
    ║                                                              ║
    ║     Ein kleines Python-Projekt in ~40 Schritten             ║
    ║     Vom leeren Magen zum warmen Diplom.                     ║
    ║                                                              ║
    ║     Idee, Code & ASCII-Art: Fifo der Dodo                   ║
    ║     Getestet von: Dem Zuschauer (Du!)                       ║
    ║                                                              ║
    ║     Danke fürs Mitbasteln, Füttern & Träumen.               ║
    ║     Bleib warm & knurr nicht so oft.                        ║
    ║                                                              ║
    ║     (Keine echten Dodos wurden beim Coding verletzt.)       ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    if USE_ANSI:
        # Bunt machen
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'DODO' in line:
                print(f"\033[93m{line}\033[0m")
            elif 'Fifo' in line or 'Zuschauer' in line:
                print(f"\033[96m{line}\033[0m")
            elif 'Danke' in line or 'warm' in line:
                print(f"\033[92m{line}\033[0m")
            else:
                print(line)
            pause(0.05)
    else:
        print(text)
    pause(1.5)


def main() -> None:
    """Hauptprogramm: Dodo-Magenwärmer Schleife."""
    random.seed()
    
    # State
    saettigung = 50
    waerme = 0
    schritt = 0
    eingaben = 0
    wetter = random.choice(["klar", "neblig", "stürmisch"])
    wetter_wechsel = random.randint(5, 10)
    
    # Stats für Diplom
    stats = {
        'sat_sum': 0,
        'steps': 0,
        'warm_phases': 0,
        'events': 0,
        'knurr_count': 0,
        'eingaben': 0,
        'beeren': 0,
        'tees': 0,
        'highscore': 0,
        'highscore_grad': "Teilnahme"
    }
    
    # Highscore laden (Simuliert: Session-Gedächtnis)
    # In einem echten File würde hier pickle/json stehen. Wir behalten es im RAM für die Session.
    
    clear_screen()
    print("🦤 Willkommen beim Dodo-Magenwärmer!")
    print("Dein Dodo schläft. Der Magen knurrt leise. Drück Enter zum Träumen...")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        print("\nSchon weg? Tschüss! 👋")
        return

    while eingaben < MAX_EINGABEN:
        schritt += 1
        stats['steps'] = schritt
        stats['sat_sum'] += saettigung
        if waerme > 0:
            stats['warm_phases'] += 1
        
        # Verdauung
        saettigung = max(0, saettigung - random.randint(1, 3))
        if waerme > 0:
            waerme = max(0, waerme - 1)
        
        # Wetterwechsel
        wetter_wechsel -= 1
        if wetter_wechsel <= 0:
            wetter = random.choice(["klar", "neblig", "stürmisch"])
            wetter_wechsel = random.randint(5, 10)
        
        # Traum-Ereignis
        delta_sat, delta_warm, msg = traum_ereignis(stats, wetter)
        saettigung = min(100, max(0, saettigung + delta_sat))
        waerme = min(10, waerme + delta_warm)
        
        knurrt = satte_pruefung(saettigung)
        if knurrt:
            stats['knurr_count'] += 1
        
        # Anzeige
        clear_screen(schritt)
        print(f"🦤 Dodo-Magenwärmer — Schritt {schritt} | {wetter_text(wetter)}")
        print(f"Sättigung: {draw_bar(saettigung, waerme=waerme)}")
        print(f"Wärme:     {'🔥' * waerme + '❄️' * (10 - waerme) if USE_ANSI else 'W' * waerme + '.' * (10 - waerme)} ({waerme}/10)")
        print()
        print(draw_stomach(saettigung, knurrt, waerme, schritt))
        print()
        print(draw_dodo(saettigung, schritt, waerme))
        print()
        if msg:
            print(f"💭 {msg}")
        print(f"Eingaben: {eingaben}/{MAX_EINGABEN}  [1] Beere  [2] Tee  [Enter] Weiter  [q] Aufwachen")
        
        # Highscore Anzeige (Session Best)
        if stats['highscore'] > 0:
            grad_short = stats['highscore_grad'][:3]
            print(f"🏆 Session-Best: {stats['highscore']} Pkt ({grad_short})")

        try:
            raw = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n*Gähn* Wach geworden? Bis bald! 👋")
            break
        
        if raw == 'q':
            print("\n🦤 Dodo streckt die Flügel. Gute Reise!")
            pause(0.5)
            break
        
        if raw == '1':
            saettigung = min(100, saettigung + random.randint(15, 25))
            stats['beeren'] += 1
            stats['eingaben'] += 1
            eingaben += 1
            print("🍇 Mmmh, saftige Beere!")
            pause(0.5)
        elif raw == '2':
            waerme = min(10, waerme + random.randint(2, 4))
            stats['tees'] += 1
            stats['eingaben'] += 1
            eingaben += 1
            print("🍵 Wärmender Schluck Tee.")
            pause(0.5)
        elif raw == '':
            # Nur träumen, keine Eingabe gezählt
            pass
        else:
            print("🤔 Verstehe ich nicht. 1, 2, Enter oder q.")
            pause(0.5)
    else:
        # Loop normal beendet (Eingaben aufgebraucht)
        print(f"\n🦤 {MAX_EINGABEN} Eingaben gemacht. Der Tag ist rum. Dodo wacht auf.")
        pause(1)
    
    # --- AUSWERTUNG & DIPLOM ---
    clear_screen()
    print("📜 === DIPLOM-AUSWERTUNG ===")
    print(f"Schritte geträumt:     {stats['steps']}")
    print(f"Ø Sättigung:           {stats['sat_sum'] / max(1, stats['steps']):.1f}%")
    print(f"Wärme-Phasen:          {stats['warm_phases']}")
    print(f"Traum-Ereignisse:      {stats['events']}")
    print(f"Magenknurren:          {stats['knurr_count']}")
    print(f"Beeren gegessen:       {stats['beeren']}")
    print(f"Tee getrunken:         {stats['tees']}")
    print(f"Eingaben genutzt:      {stats['eingaben']}")
    print()
    
    grad, punkte = berechne_diplom(stats)
    
    print(f"🎓 DIPLOM: {grad.upper()} ({punkte} Punkte)")
    print()
    print(draw_pokal(grad))
    print()
    
    # Highscore Vergleich
    if punkte > stats['highscore']:
        print(f"🌟 NEUER SESSION-REKORD! Vorher: {stats['highscore']} Pkt")
        stats['highscore'] = punkte
        stats['highscore_grad'] = grad
    elif stats['highscore'] > 0:
        print(f"🏆 Session-Best steht: {stats['highscore']} Pkt ({stats['highscore_grad']})")
    
    # Tagebuch
    print("\n📖 TAGESBUCH-EINTRAG:")
    if grad == "Platin":
        print('   "Legende! Der Magen glüht wie ein Vulkan. Dodos erzählen sich davon."')
    elif grad == "Gold":
        print('   "Meisterhaft warm. Selbst der kälteste Nebeltraum schmilzt dahin."')
    elif grad == "Silber":
        print('   "Solide Leistung. Der Magen ist zufrieden, die Federn flauschig."')
    elif grad == "Bronze":
        print('   "Bestanden. Nächstes Mal mehr Beeren, weniger Knurren."')
    else:
        print('   "Teilnahme ist alles! Der Dodo hat geträumt. Das zählt."')
    
    pause(2)
    
    # Finaler Abspann
    zeige_abspann()
    print("\n🦤 Programmende. Danke fürs Spielen!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Sicherheitsnetz für unerwartete Fehler
        print(f"\n💥 Uups, ein Fehler schlich sich ein: {e}")
        if not USE_ANSI:
            import traceback
            traceback.print_exc()
        print("🦤 Dodo flüchtet sich ins Gebüsch. Tschüss!")