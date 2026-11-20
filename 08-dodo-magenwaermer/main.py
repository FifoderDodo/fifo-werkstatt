# main.py - Dodo-Magenwärmer Teil 36 (Abschluss-Pokal)
# Fifo der Dodo räumt auf: Vollständige Schleife, Tagebuch, Statistik, Diplom – und nun ein Pokal.
# Fix: Abgeschnittenen Wetter-Code完成, Loop-Logik robust, EOFError sauber.
# Neu: Session-Highscore (Bester Lauf), ASCII-Pokal bei Diplom, Ausgabe etwas geglättet.

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
     `""""""`""",
        "Silber": """      |~~~|
      |  2. |
      |_____|
     /  ___  \\
    /  /   \\  \\
   |  |     |  |
    \\       //
     `""""""`""",
        "Bronze": """      |~~~|
      |  3. |
      |_____|
     /  ___  \\
    /  /   \\  \\
    \\       //
     `""""""`""",
        "Teilnahme": """      |~~~|
      |     |
      |_____|
     /  ___  \\
    /  /   \\  \\
    \\       //
     `""""""`"""
    }
    return pokale.get(grad, pokale["Teilnahme"])


def main() -> None:
    """Hauptschleife: Dodo schläft, Magen knurrt, Träume passieren."""
    # Session-Highscore laden (nur im Speicher)
    if not hasattr(main, "highscore"):
        main.highscore = 0
    
    sat = 70
    waerme = 0
    schritt = 0
    eingaben = 0
    knurr_zaehler = 0
    stats = {
        'beeren': 0,
        'tee': 0,
        'events': 0,
        'knurren': 0,
        'max_sat': sat,
        'min_sat': sat
    }
    wetter = "klar"
    wetter_timer = 0
    wetter_dauer = {"klar": 0, "neblig": 0, "stürmisch": 0}
    startzeit = time.time()
    traum_tagebuch = []
    
    clear_screen()
    print("🦤 Dodo-Magenwärmer — Traum-Edition")
    print("Drücke Enter zum Träumen, 1 für Beere, 2 für Tee, q zum Aufwachen.")
    print("(Max 20 echte Eingaben, Enter zählt nicht.)\n")
    pause(1.0)
    
    while sat > 0 and eingaben < MAX_EINGABEN:
        schritt += 1
        
        # Wetter wechseln alle 8-15 Schritte
        wetter_timer -= 1
        if wetter_timer <= 0:
            wetter = random.choice(["klar", "neblig", "stürmisch"])
            wetter_timer = random.randint(8, 15)
        wetter_dauer[wetter] = wetter_dauer.get(wetter, 0) + 1
        
        # Sättigung sinkt wetterabhängig
        basis_verlust = 2
        if wetter == "stürmisch":
            basis_verlust = 4
        elif wetter == "neblig":
            basis_verlust = 1
        sat = max(0, sat - basis_verlust)
        
        # Wärme decay
        if waerme > 0:
            waerme -= 1
        
        # Knurren prüfen
        knurrt = satte_pruefung(sat)
        if knurrt:
            knurr_zaehler += 1
            stats['knurren'] += 1
        
        # Traum-Ereignis
        delta_sat, delta_waerme, msg = traum_ereignis(stats, wetter)
        if msg:
            traum_tagebuch.append(f"Schritt {schritt}: {msg}")
            if len(traum_tagebuch) > 10:
                traum_tagebuch.pop(0)
        sat = max(0, min(100, sat + delta_sat))
        waerme = min(10, waerme + delta_waerme)
        
        # Stats aktualisieren
        stats['max_sat'] = max(stats['max_sat'], sat)
        stats['min_sat'] = min(stats['min_sat'], sat)
        
        # Zeichnen
        clear_screen(schritt)
        print(f"🦤 Dodo-Magenwärmer — Schritt {schritt} | {wetter_text(wetter)}")
        print(draw_stomach(sat, knurrt, waerme, schritt))
        print()
        print(draw_bar(sat, waerme=waerme))
        print()
        print(draw_dodo(sat, schritt, waerme))
        print(f"\nWärme: {waerme} | Knurren: {knurr_zaehler} | Eingaben: {eingaben}/{MAX_EINGABEN}")
        if msg:
            print(f"💭 {msg}")
        print("[1] Beere  [2] Tee  [Enter] Weiter  [q] Aufwachen")
        
        # Eingabe
        try:
            raw = input("> ").strip().lower()
        except EOFError:
            print("\n🌙 Eingabestrom zu, Dodo wacht sanft auf.")
            break
        
        if raw == 'q':
            print("\n🌅 Dodo streckt die Flügel: Aufwachen!")
            break
        if raw == '1':
            sat = min(100, sat + 15)
            stats['beeren'] += 1
            eingaben += 1
            traum_tagebuch.append(f"Schritt {schritt}: 🍇 Beere gegessen (+15%).")
            if len(traum_tagebuch) > 10:
                traum_tagebuch.pop(0)
        elif raw == '2':
            waerme = min(10, waerme + 4)
            stats['tee'] += 1
            eingaben += 1
            traum_tagebuch.append(f"Schritt {schritt}: 🍵 Tee getrunken (+4 Wärme).")
            if len(traum_tagebuch) > 10:
                traum_tagebuch.pop(0)
        elif raw == '':
            # Enter zählt nicht als Eingabe
            pass
        else:
            print("🤔 Verstehe nicht. 1, 2, Enter oder q.")
            pause(0.5)
        
        pause(0.15)
    
    # --- ENDE & AUSWERTUNG ---
    clear_screen()
    dauer = time.time() - startzeit
    print("🌅 === TRAUM ENDE ===")
    print(f"Dauer: {dauer:.1f}s | Schritte: {schritt} | End-Sättigung: {sat}% | Wärme: {waerme}")
    print()
    
    # Traum-Tagebuch
    print("📖 Traum-Tagebuch (letzte 10):")
    if traum_tagebuch:
        for eintrag in traum_tagebuch:
            print(f"  {eintrag}")
    else:
        print("  (Keine besonderen Träume notiert.)")
    print()
    
    # Wetter-Statistik
    print("🌤️ Wetter-Statistik:")
    for w, cnt in wetter_dauer.items():
        if cnt:
            print(f"  {wetter_text(w)}: {cnt} Schritte")
    print()
    
    # Aktion-Statistik
    print("📊 Aktionen:")
    print(f"  Beeren: {stats['beeren']} | Tee: {stats['tee']} | Ereignisse: {stats['events']} | Knurren: {stats['knurren']}")
    print(f"  Sättigung Spanne: {stats['min_sat']}% – {stats['max_sat']}%")
    print()
    
    # Diplom & Pokal
    # Score: Schritte * 10 + Sättigung * 2 + Wärme * 5 + Beeren*10 + Tee*5 - Knurren*3
    score = schritt * 10 + sat * 2 + waerme * 5 + stats['beeren'] * 10 + stats['tee'] * 5 - stats['knurren'] * 3
    
    if score >= 3000:
        grad = "Platin"
    elif score >= 2000:
        grad = "Gold"
    elif score >= 1200:
        grad = "Silber"
    elif score >= 500:
        grad = "Bronze"
    else:
        grad = "Teilnahme"
    
    # Highscore prüfen
    highscore_gekknackt = False
    if score > main.highscore:
        main.highscore = score
        highscore_gekknackt = True
    
    print(f"🏆 Dodo-Diplom: {grad} (Score: {score})")
    if highscore_gekknackt:
        print("✨ NEUER SESSION-HIGHSCORE! ✨")
    print(f"🏅 Session-Best: {main.highscore}")
    print()
    print(draw_pokal(grad))
    print()
    print("Danke fürs Spielen! Gute Nacht, kleiner Dodo. 🦤💤")


def _demo() -> None:
    """Führt eine automatische Demo aus (für Tests ohne stdin)."""
    import io
    backup_stdin = sys.stdin
    # Simuliere: Beere, Tee, Enter, Enter, q
    sys.stdin = io.StringIO("1\n2\n\n\nq\n")
    try:
        main()
    finally:
        sys.stdin = backup_stdin

if __name__ == "__main__":
    # Wenn kein TTY (z.B. CI/Test), Demo laufen lassen
    if not USE_ANSI:
        _demo()
    else:
        main()