# main.py - Dodo-Magenwärmer Teil 34 (Traum-Edition)
# Fifo der Dodo träumt weiter: Hauptschleife fertig, Aufwachen, Tagebuch, Zertifikat.
# Fix: While-Schleife vervollständigt, Wetter-Logik, Knurren, Abnahme, Ereignisse, Zeichnen, Eingabe.
# Neu: Sauberes Loop-Ende, Traum-Tagebuch (letzte 10), Wetter-Statistik, Dodo-Diplom.
# Teil 34: Letzter Feinschliff – Eingabe-Zähler robust, Tagebuch-Einträge limitiert, Diplom-Titel dynamisch.

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


def main() -> None:
    """Hauptschleife: Dodo schläft, Magen knurrt, Träume passieren."""
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
        
        # Sättigung sinkt
        sat -= random.randint(1, 3)
        sat = max(0, sat)
        
        # Wärme decay
        if waerme > 0:
            waerme -= 1
        
        # Stats aktualisieren
        stats['max_sat'] = max(stats['max_sat'], sat)
        stats['min_sat'] = min(stats['min_sat'], sat)
        
        # Knurren prüfen
        knurrt = satte_pruefung(sat)
        if knurrt:
            knurr_zaehler += 1
            stats['knurren'] = knurr_zaehler
        
        # Traum-Ereignis
        delta_sat, delta_waerme, msg = traum_ereignis(stats, wetter)
        if msg:
            traum_tagebuch.append(f"Schritt {schritt}: {msg}")
            # Nur letzte 10 behalten
            if len(traum_tagebuch) > 10:
                traum_tagebuch.pop(0)
        sat = max(0, min(100, sat + delta_sat))
        waerme = max(0, waerme + delta_waerme)
        
        # Zeichnen
        clear_screen(schritt)
        print(f"🦤 Dodo-Magenwärmer — Schritt {schritt} — {wetter_text(wetter)}")
        print(draw_bar(sat, waerme=waerme))
        print(draw_stomach(sat, knurrt, waerme, schritt))
        print(draw_dodo(sat, schritt, waerme))
        print(f"Wärme: {waerme} | Knurren: {knurr_zaehler} | Eingaben: {eingaben}/{MAX_EINGABEN}")
        if msg:
            print(f"💭 {msg}")
        
        # Eingabe
        try:
            raw = input("\n[1] Beere  [2] Tee  [Enter] Träumen  [q] Aufwachen > ").strip().lower()
        except EOFError:
            print("\n🌙 Keine Eingabe mehr – Dodo wacht sanft auf.")
            break
        
        if raw == '1':
            sat = min(100, sat + 15)
            waerme = min(10, waerme + 1)
            stats['beeren'] += 1
            eingaben += 1
            traum_tagebuch.append(f"Schritt {schritt}: 🍇 Beere genascht (+15%, +1 Wärme)")
        elif raw == '2':
            waerme = min(10, waerme + 5)
            sat = min(100, sat + 5)
            stats['tee'] += 1
            eingaben += 1
            traum_tagebuch.append(f"Schritt {schritt}: 🍵 Tee getrunken (+5%, +5 Wärme)")
        elif raw == 'q':
            print("\n🦤 Dodo beschließt aufzuwachen. Gute Reise!")
            break
        elif raw == '':
            # Enter zählt nicht als echte Eingabe
            pass
        else:
            print("🤔 Unbekannter Befehl. Träume einfach weiter...")
            pause(0.5)
    
    # --- Aufwachen & Auswertung ---
    clear_screen()
    dauer = time.time() - startzeit
    print("🌅 Dodo wacht auf. Federn sortieren, Magen prüfen...")
    pause(0.5)
    
    # Traum-Tagebuch
    print("\n📖 Traum-Tagebuch (letzte 10 Einträge):")
    if traum_tagebuch:
        for eintrag in traum_tagebuch:
            print(f"  {eintrag}")
    else:
        print("  (Keine besonderen Träume notiert.)")
    
    # Wetter-Statistik
    print("\n🌤️ Traum-Wetter-Statistik:")
    for w, d in wetter_dauer.items():
        if d > 0:
            print(f"  {wetter_text(w)}: {d} Schritte")
    
    # Dodo-Diplom
    print("\n" + "=" * 40)
    print("🎓 DODO-DIPLOM — OFFIZIELLES ZERTIFIKAT")
    print("=" * 40)
    print(f"Name: Fifo der Dodo")
    print(f"Traumdauer: {dauer:.1f} Sekunden ({schritt} Schritte)")
    print(f"Beeren genascht: {stats['beeren']}")
    print(f"Tee getrunken: {stats['tee']}")
    print(f"Traum-Ereignisse: {stats['events']}")
    print(f"Magen-Knurren: {stats['knurren']}")
    print(f"Höchste Sättigung: {stats['max_sat']}%")
    print(f"Niedrigste Sättigung: {stats['min_sat']}%")
    
    # Titel basierend auf Leistung
    if stats['beeren'] + stats['tee'] == 0:
        titel = "Traumwandler"
    elif stats['knurren'] == 0 and stats['min_sat'] >= 50:
        titel = "Meister der Sättigung"
    elif waerme > 0:
        titel = "Wärme-Hüter"
    elif stats['events'] >= 3:
        titel = "Traum-Forscher"
    elif sat > 0:
        titel = "Überlebender"
    else:
        titel = "Hungriger Träumer"
    
    print(f"\n🏆 TITEL: {titel}")
    print("=" * 40)
    print("\n🦤 Gute Erholung, kleiner Dodo. Bis zum nächsten Traum.")

if __name__ == "__main__":
    main()