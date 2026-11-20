# main.py - Dodo-Magenwärmer Teil 39 (Nährwert-Prioritäten bei Regenwetter)
# Fifo der Dodo hängt eine Regenrinne an die PC-Ecke: Neues Wetter 'regnerisch' mit Nährwert-Anzeige.
# Fix: berechne_diplom vervollständigt, main() robust, Abspann-Funktion neu, Statusanzeige poliert.
# Neu: wetter_text erweitert, traum_ereignis angepasst, zeige_naehrwert_prioritaet() implementiert.

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
    
    # Analyse der Stats für Empfehlung
    beeren = stats.get('beeren', 0)
    tee = stats.get('tee', 0)
    gesamt = stats.get('eingaben', 1)
    
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
        lines.append(f"│ {cyan}Erste Mahlzeit!{reset} Beeren für Basis, │")
        lines.append(f"│ {cyan}Tee für Wärme bei Nässe.          {reset}│")
    elif beeren > tee * 2:
        lines.append(f"│ {yellow}Viel Fruchtzucker erkannt.{reset}       │")
        lines.append(f"│ {cyan}Priorität: Tee (Wärme & Balance). {reset}│")
    elif tee > beeren * 2:
        lines.append(f"│ {yellow}Viel Flüssigkeit erkannt.         {reset}│")
        lines.append(f"│ {cyan}Priorität: Beeren (Energie & Sätt.).{reset}│")
    else:
        lines.append(f"│ {cyan}Ausgewogen genascht.             {reset}│")
        lines.append(f"│ {cyan}Weiter so: Mix aus Beeren & Tee.  {reset}│")
    
    # Spezial-Tipp bei niedriger Sättigung
    if stats.get('sat_history'):
        avg_sat = sum(stats['sat_history']) / len(stats['sat_history'])
        if avg_sat < 30:
            lines.append(f"│ {yellow}⚠ Chronisch hungrig!{reset}             │")
            lines.append(f"│ {cyan}Fokus: Beeren (Sättigung pur).    {reset}│")
    
    lines.append(f"{yellow}└────────────────────────────────┘{reset}")
    return "\n".join(lines)


def traum_ereignis(stats: dict, wetter: str) -> tuple[int, int, str]:
    """Würfelt ein Traum-Ereignis. Gibt IMMER (delta_sat, delta_waerme, nachricht)."""
    chance = 0.15
    if wetter == "stürmisch":
        chance = 0.25
    elif wetter == "neblig":
        chance = 0.10
    elif wetter == "regnerisch":
        chance = 0.20  # Etwas höher bei Regen
    
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
    # Basis: Durchschnittliche Sättigung 
    if stats.get('sat_history'):
        avg_sat = sum(stats['sat_history']) / len(stats['sat_history'])
        punkte += int(avg_sat * 0.5)  # Max ~50 Pkt
    
    # Wärme-Bonus
    punkte += stats.get('max_waerme_reached', 0) * 5  # Max ~50 Pkt bei 10 Wärme
    
    # Event-Bonus
    punkte += stats.get('events', 0) * 10
    
    # Effizienz: Wenig Eingaben, hohe Sättigung
    eingaben = max(1, stats.get('eingaben', 1))
    final_sat = stats.get('final_sat', 0)
    if eingaben > 0:
        punkte += int((final_sat / max(1, eingaben)) * 10)
    
    # Beeren/Tea Balance Bonus
    beeren = stats.get('beeren', 0)
    tee = stats.get('tee', 0)
    if beeren > 0 and tee > 0:
        balance = min(beeren, tee) / max(beeren, tee)
        punkte += int(balance * 20)
    
    # Grad-Zuordnung
    if punkte >= 200:
        return ("Platin", punkte)
    elif punkte >= 150:
        return ("Gold", punkte)
    elif punkte >= 100:
        return ("Silber", punkte)
    elif punkte >= 50:
        return ("Bronze", punkte)
    else:
        return ("Teilnahme", punkte)


def zeige_abspann(stats: dict, grad: str, punkte: int) -> None:
    """Zeigt den finalen Abspann mit Credits und Statistiken."""
    clear_screen()
    print(draw_pokal(grad))
    print(f"\n🎓 DIPLOM: {grad.upper()} ({punkte} Punkte)")
    print("=" * 40)
    print("   FIFO'S DODO-MAGENWÄRMER")
    print("   Ein kleines Python-Projekt")
    print("   Teil 39 von ~43")
    print("=" * 40)
    print("\n📊 STATISTIKEN:")
    print(f"   Beeren gegessen: {stats.get('beeren', 0)}")
    print(f"   Tee getrunken:   {stats.get('tee', 0)}")
    print(f"   Eingaben genutzt: {stats.get('eingaben', 0)} / {MAX_EINGABEN}")
    print(f"   Traum-Events:    {stats.get('events', 0)}")
    if stats.get('sat_history'):
        avg = sum(stats['sat_history']) / len(stats['sat_history'])
        print(f"   Ø Sättigung:     {avg:.1f}%")
    print(f"   Max Wärme:       {stats.get('max_waerme_reached', 0)}")
    print("\n💻 Code: Fifo der Dodo (mit human assistance)")
    print("🎨 ASCII: Feder für Feder getippt")
    print("☕ Getrunken: Virtueller Beeren-Tee")
    print("\nDanke fürs Spielen! Das Ei ist ausgebrütet. 🥚➡️🐣")
    print("\nDrücke Enter zum Beenden...")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass


def main() -> None:
    """Haupt-Loop: Füttern, Trinken, Träumen, Status."""
    random.seed()
    
    # State
    saettigung = 50
    waerme = 0
    max_waerme = 10
    schritt = 0
    stats = {
        'beeren': 0,
        'tee': 0,
        'eingaben': 0,
        'events': 0,
        'sat_history': [],
        'max_waerme_reached': 0,
        'final_sat': 0
    }
    
    # Initiales Wetter
    wetter_liste = ["klar", "neblig", "stürmisch", "regnerisch"]
    wetter = random.choice(wetter_liste)
    wetter_counter = 0
    
    print("🦤 FIFO'S DODO-MAGENWÄRMER - TEIL 39")
    print("Tippe: 1=Beere, 2=Tee, 3=Warten, 4=Status, q=Ende")
    pause(1.5)
    
    while stats['eingaben'] < MAX_EINGABEN:
        schritt += 1
        wetter_counter += 1
        
        # Wetterwechsel alle 5-8 Schritte
        if wetter_counter >= random.randint(5, 8):
            wetter = random.choice(wetter_liste)
            wetter_counter = 0
            clear_screen(schritt)
            print(f"🌤️ Wetterumschwung: {wetter_text(wetter)}!")
            pause(1.0)
        
        clear_screen(schritt)
        
        # Statuszeile
        knurrt = satte_pruefung(saettigung)
        if waerme > 0:
            waerme = max(0, waerme - 0.1)  # Langsame Abkühlung
        stats['max_waerme_reached'] = max(stats['max_waerme_reached'], int(waerme))
        stats['sat_history'].append(saettigung)
        
        print(f"Schritt {schritt}/{MAX_EINGABEN} | {wetter_text(wetter)} | Wärme: {draw_waerme_bar(int(waerme), max_waerme)}")
        print(draw_bar(saettigung, waerme=int(waerme)))
        print(draw_stomach(saettigung, knurrt, int(waerme), schritt))
        print(draw_dodo(saettigung, schritt, int(waerme)))
        
        # NEU: Nährwert-Prioritäten bei Regen
        prioritaet = zeige_naehrwert_prioritaet(wetter, stats)
        if prioritaet:
            print(prioritaet)
        
        # Traum-Ereignis
        delta_sat, delta_waerme, msg = traum_ereignis(stats, wetter)
        if msg:
            print(f"\n{msg}")
            saettigung = max(0, min(100, saettigung + delta_sat))
            waerme = min(max_waerme, waerme + delta_waerme)
            pause(1.5)
            continue
        
        # Input
        print("\n[1] Beere essen (+15%)  [2] Tee trinken (+3 Wärme)")
        print("[3] Warten (Traum?)      [4] Status-Details")
        print("[q] Beenden")
        
        try:
            choice = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Tschüss! Dodo winkt mit der Flügel.")
            break
        
        stats['eingaben'] += 1
        
        if choice == '1':
            saettigung = min(100, saettigung + 15)
            stats['beeren'] += 1
            print("🍓 Mmmh, saftige Beere!")
            pause(0.5)
        elif choice == '2':
            waerme = min(max_waerme, waerme + 3)
            saettigung = min(100, saettigung + 5)  # Tee sättigt leicht
            stats['tee'] += 1
            print("🍵 Wärmender Schluck Tee.")
            pause(0.5)
        elif choice == '3':
            saettigung = max(0, saettigung - 5)  # Warten macht hungrig
            print("💤 Dodo döst... Magen knurrt leiser.")
            pause(1.0)
        elif choice == '4':
            clear_screen(schritt)
            print("📋 DETAIL-STATUS")
            print(f"Sättigung: {saettigung}%")
            print(f"Wärme: {int(waerme)}/{max_waerme}")
            print(f"Wetter: {wetter_text(wetter)}")
            print(f"Beeren: {stats['beeren']}, Tee: {stats['tee']}")
            print(f"Träume: {stats['events']}")
            print(f"Schritte: {schritt}")
            if stats['sat_history']:
                avg = sum(stats['sat_history']) / len(stats['sat_history'])
                print(f"Ø Sättigung: {avg:.1f}%")
            print("\nDrücke Enter...")
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                break
            continue
        elif choice == 'q':
            print("👋 Dodo winkt zum Abschied.")
            pause(0.5)
            break
        else:
            print("🤔 Verstanden nicht. 1, 2, 3, 4 oder q.")
            pause(0.5)
            stats['eingaben'] -= 1  # Nicht zählen bei Fehleingabe
            continue
        
        # Natürlicher Sättigungsverlust pro Aktion
        saettigung = max(0, saettigung - 2)
    
    # Loop Ende / Abspann
    stats['final_sat'] = saettigung
    grad, punkte = berechne_diplom(stats)
    zeige_abspann(stats, grad, punkte)

if __name__ == "__main__":
    main()