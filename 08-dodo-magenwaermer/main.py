# main.py - Dodo-Magenwärmer Teil 37 (Diplom-Logik & Highscore-Anzeige)
# Fifo der Dodo feilt am Abschluss: Diplom-Berechnung, Pokal-Verleihung, Highscore-Vergleich, sauberer Abschied.
# Fix: main()-Funktion vervollständigt, Loop-Ende robust, EOFError/KeyboardInterrupt abgefangen.
# Neu: Detaillierte Diplom-Logik (Punkte-System), Highscore-Vergleich bei Neustart, "Gute Reise"-Text.

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
        # Füllung zeichnen
        if i >= fill_start and level > 0 and i < 5:
            left = line.find('\\')
            right = line.find('//')
            if left != -1 and right != -1 and right > left:
                mid = line[left+2:right]
                filled = (wave * (len(mid) // 3 + 1))[:len(mid)]
                line = line[:left+2] + filled + line[right:]
        # Farbe anwenden
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
    """Berechnet Diplom-Grad basierend auf Stats. Gibt (Grad, Punktzahl)."""
    punkte = 0
    # Basis: Durchschnittliche Sättigung (0-100 Pkt)
    if stats.get('steps', 0) > 0:
        punkte += int(stats.get('total_sat', 0) / stats['steps'])
    # Wärme-Bonus (max 20)
    punkte += min(20, stats.get('total_waerme', 0) * 2)
    # Event-Bonus (max 15)
    punkte += min(15, stats.get('events', 0) * 3)
    # Langlebigkeits-Bonus (max 15)
    punkte += min(15, stats.get('steps', 0))
    # Knurr-Penalty
    punkte -= stats.get('knurr_count', 0) * 5
    
    punkte = max(0, punkte)
    
    if punkte >= 130:
        return ("Platin", punkte)
    elif punkte >= 100:
        return ("Gold", punkte)
    elif punkte >= 70:
        return ("Silber", punkte)
    elif punkte >= 40:
        return ("Bronze", punkte)
    else:
        return ("Teilnahme", punkte)


def main() -> None:
    """Hauptschleife: Dodo schläft, Magen knurrt, Träume passieren."""
    # Session-Highscore laden (nur im Speicher an Function-Objekt gehängt)
    if not hasattr(main, "highscore"):
        main.highscore = {"punkte": 0, "grad": "Teilnahme", "runde": 0}
    
    main.highscore["runde"] += 1
    runde_nr = main.highscore["runde"]
    
    # Init
    satt = 50
    waerme = 0
    schritt = 0
    eingaben = 0
    tagebuch = []
    stats = {
        'total_sat': 0,
        'total_waerme': 0,
        'steps': 0,
        'events': 0,
        'knurr_count': 0,
        'best_sat': 50,
        'worst_sat': 50
    }
    wetter = random.choice(["klar", "neblig", "stürmisch"])
    
    print(f"🦤 Dodo-Magenwärmer — Runde {runde_nr}")
    if main.highscore['punkte'] > 0:
        print(f"🏆 Session-Bestwert: {main.highscore['punkte']} Pkt ({main.highscore['grad']})")
    print("Drücke Enter zum Starten...")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        print("\n👋 Bis zum nächsten Traum.")
        return

    while eingaben < MAX_EINGABEN:
        schritt += 1
        stats['steps'] += 1
        
        # Nachtliche Verdauung
        satt = max(0, satt - random.randint(1, 4))
        if waerme > 0:
            waerme = max(0, waerme - 1)
        
        knurrt = satte_pruefung(satt)
        if knurrt:
            stats['knurr_count'] += 1
        
        # Stats aktualisieren
        stats['total_sat'] += satt
        stats['total_waerme'] += waerme
        stats['best_sat'] = max(stats['best_sat'], satt)
        stats['worst_sat'] = min(stats['worst_sat'], satt)
        
        # Traum-Ereignis würfeln (alle 3 Schritte)
        traum_msg = ""
        if schritt % 3 == 0:
            delta_sat, delta_waerme, traum_msg = traum_ereignis(stats, wetter)
            satt = max(0, min(100, satt + delta_sat))
            waerme = min(10, waerme + delta_waerme)
            if traum_msg:
                tagebuch.append(f"Schritt {schritt}: {traum_msg}")
        
        # Wetterwechsel (alle 7 Schritte)
        if schritt % 7 == 0:
            wetter = random.choice(["klar", "neblig", "stürmisch"])
            tagebuch.append(f"Schritt {schritt}: Wetter dreht auf {wetter_text(wetter)}.")
        
        # Zeichnen
        clear_screen(schritt if not USE_ANSI else None)
        print(f"🦤 Dodo-Magenwärmer — Schritt {schritt} | {wetter_text(wetter)}")
        print(draw_stomach(satt, knurrt, waerme, schritt))
        print(draw_bar(satt, waerme=waerme))
        print(draw_dodo(satt, schritt, waerme))
        print(f"Wärme: {waerme} | Knurren: {stats['knurr_count']} | Eingaben: {eingaben}/{MAX_EINGABEN}")
        if traum_msg:
            print(f"💭 {traum_msg}")
        
        # Menü
        print("[1] Beere essen  [2] Tee trinken  [Enter] Weiter träumen  [q] Aufwachen")
        
        try:
            raw = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n🌙 Dodo wacht sanft auf (Eingabe ende).")
            break
        
        eingaben += 1
        
        if raw == 'q':
            tagebuch.append(f"Schritt {schritt}: Dodo wacht freiwillig auf.")
            break
        elif raw == '1':
            gain = random.randint(8, 18)
            satt = min(100, satt + gain)
            tagebuch.append(f"Schritt {schritt}: Beere gegessen (+{gain}%).")
        elif raw == '2':
            gain = random.randint(2, 4)
            waerme = min(10, waerme + gain)
            tagebuch.append(f"Schritt {schritt}: Tee getrunken (+{gain} Wärme).")
        elif raw == '':
            tagebuch.append(f"Schritt {schritt}: Weiter geträumt.")
        else:
            tagebuch.append(f"Schritt {schritt}: Unbekanntes Signal '{raw}' ignoriert.")
            eingaben -= 1 # Ungültige Eingabe zählt nicht zum Limit
            pause(0.3)
            continue
        
        pause(0.4)
    
    # --- ENDE & DIPLOM ---
    clear_screen()
    print("=" * 40)
    print("🌅 DODO WACHT AUF — DIPLOMZEIT")
    print("=" * 40)
    
    grad, punkte = berechne_diplom(stats)
    
    print(f"\n📊 Statistik:")
    print(f"   Schritte: {stats['steps']}")
    print(f"   Ø Sättigung: {stats['total_sat'] // max(1, stats['steps'])}%")
    print(f"   Beste Sättigung: {stats['best_sat']}% | Schlechteste: {stats['worst_sat']}%")
    print(f"   Gesamt-Wärme: {stats['total_waerme']}")
    print(f"   Traum-Ereignisse: {stats['events']}")
    print(f"   Magenknurren: {stats['knurr_count']}")
    print(f"\n🎓 Diplom: {grad} ({punkte} Punkte)")
    print(draw_pokal(grad))
    
    # Highscore prüfen
    if punkte > main.highscore['punkte']:
        print("\n🌟 NEUER SESSION-HIGHSCORE! 🌟")
        main.highscore['punkte'] = punkte
        main.highscore['grad'] = grad
    else:
        print(f"\n🏆 Session-Bestwert bleibt: {main.highscore['punkte']} Pkt ({main.highscore['grad']})")
    
    # Tagebuch-Ausgabe
    if tagebuch:
        print("\n📖 Traum-Tagebuch:")
        for eintrag in tagebuch[-10:]: # Letzten 10 Einträge
            print(f"  - {eintrag}")
    
    print("\n🍃 Gute Reise, kleiner Dodo. Der Magen ist warm, das Herz auch.")
    print("Drücke Enter zum Beenden...")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass

if __name__ == "__main__":
    main()