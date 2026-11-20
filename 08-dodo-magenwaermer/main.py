# main.py - Dodo-Magenwärmer Teil 30 (Traum-Edition)
# Fifo der Dodo träumt weiter: Fehler gefixt, Traum-Tagebuch eingebaut, Abschluss rund.
# Fix: Syntaxfehler im f-String behoben (ANSI-Codes als Variablen).
# Neu: Traum-Tagebuch sammelt Ereignisse und zeigt sie beim Aufwachen an.
# Polier: Eingabe-Limit nur für Aktionen, Enter frei; EOFError sanft; Zertifikat hübsch.
# Teil 30: Hauptschleife vervollständigt, Aufwachen-Logik, Traum-Tagebuch-Ausgabe, Zertifikat.

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
    # Basis-Chance 15%, wetterabhängig modifiziert
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
    startzeit = time.time()
    traum_tagebuch = []  # Neu: sammelt Ereignisse für das Traum-Tagebuch
    
    clear_screen()
    print("🦤 Dodo-Magenwärmer — Traum-Edition")
    print("Drücke Enter zum Träumen, 1 für Beere, 2 für Tee, q zum Aufwachen.")
    print("(Max 20 echte Eingaben, Enter zählt nicht.)\n")
    pause(1.0)
    
    while sat > 0 and eingaben < MAX_EINGABEN:
        schritt += 1
        
        # Wetterwechsel alle 10-20 Schritte
        wetter_timer -= 1
        if wetter_timer <= 0:
            wetter = random.choice(["klar", "neblig", "stürmisch"])
            wetter_timer = random.randint(10, 20)
        
        # Knurren bestimmen
        knurrt = satte_pruefung(sat)
        if knurrt:
            knurr_zaehler += 1
            stats['knurren'] += 1
        
        # Traum-Ereignis
        delta_sat, delta_waerme, msg = traum_ereignis(stats, wetter)
        if msg:
            traum_tagebuch.append(f"Schritt {schritt}: {msg}")
        sat = max(0, min(100, sat + delta_sat))
        waerme = max(0, waerme + delta_waerme)
        
        # Natürliche Sättigungsabnahme & Wärmedecay
        sat = max(0, sat - random.randint(1, 3))
        if waerme > 0:
            waerme -= 1
        
        # Stats aktualisieren
        stats['max_sat'] = max(stats['max_sat'], sat)
        stats['min_sat'] = min(stats['min_sat'], sat)
        
        # Zeichnen
        clear_screen(schritt)
        print(f"🦤 Dodo-Magenwärmer — Schritt {schritt}")
        print(f"{wetter_text(wetter)}")
        print(draw_bar(sat, waerme=waerme))
        print(draw_stomach(sat, knurrt, waerme, schritt))
        print(draw_dodo(sat, schritt, waerme))
        print(f"Wärme: {waerme} | Knurren: {knurr_zaehler} | Eingaben: {eingaben}/{MAX_EINGABEN}")
        
        # Eingabe
        try:
            raw = input("Deine Wahl (Enter/1/2/q): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n🌅 Aufwachen... (Eingabe ende)")
            break
        
        if raw == "q":
            print("🌅 Dodo wacht sanft auf.")
            break
        elif raw == "1":
            sat = min(100, sat + 15)
            waerme = min(10, waerme + 1)
            stats['beeren'] += 1
            eingaben += 1
            traum_tagebuch.append(f"Schritt {schritt}: 🍇 Beere gegessen! +15% Sättigung, +1 Wärme")
        elif raw == "2":
            waerme = min(10, waerme + 5)
            stats['tee'] += 1
            eingaben += 1
            traum_tagebuch.append(f"Schritt {schritt}: 🍵 Tee getrunken! +5 Wärme")
        elif raw == "":
            # Enter = träumen, zählt nicht als Eingabe
            pass
        else:
            print("Unbekannte Eingabe. Nur 1, 2, q oder Enter.")
            pause(0.5)
            continue
        
        pause(0.3)
    
    # Ende
    clear_screen()
    dauer = time.time() - startzeit
    print("🌅 === AUFWACHEN ===")
    print(f"Geträumt: {schritt} Schritte in {dauer:.1f} Sekunden")
    print(f"Beeren: {stats['beeren']} | Tee: {stats['tee']} | Ereignisse: {stats['events']} | Knurren: {stats['knurren']}")
    print(f"Sättigung: Max {stats['max_sat']}% | Min {stats['min_sat']}%")
    print()
    
    # Traum-Tagebuch
    if traum_tagebuch:
        print("📖 Traum-Tagebuch:")
        for eintrag in traum_tagebuch[-10:]:  # letzte 10 Einträge
            print(f"  {eintrag}")
        if len(traum_tagebuch) > 10:
            print(f"  ... und {len(traum_tagebuch) - 10} weitere Träume.")
    else:
        print("📖 Traum-Tagebuch: (keine besonderen Träume)")
    print()
    
    # Zertifikat
    print("🏆 DODO-MAGENWÄRMER ZERTIFIKAT")
    print("══════════════════════════════")
    titel = "Traum-Dodo" if schritt > 30 else "Schlafmütze"
    if stats['beeren'] > 5:
        titel = "Beeren-Prinz" if stats['beeren'] > 10 else "Beeren-Freund"
    if stats['tee'] > 5:
        titel = "Tee-Meister" if stats['tee'] > 10 else "Tee-Liebhaber"
    if waerme > 5:
        titel = "Wärme-Wächter"
    print(f"Titel: {titel}")
    print(f"Schritte: {schritt} | Dauer: {dauer:.1f}s")
    print(f"Finale Sättigung: {sat}% | Wärme: {waerme}")
    print("══════════════════════════════")
    print("Gute Reise, kleiner Dodo. 🦤\n")

if __name__ == "__main__":
    main()