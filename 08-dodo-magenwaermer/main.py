# main.py - Dodo-Magenwärmer Teil 41 (Nährwert-HUD & Kontext-Prioritäten)
# Fifo der Dodo verfeinert die Nährwert-Anzeige: Kontext-sensitiv, kompakt, immer sichtbar bei Bedarf.
# Neu: zeige_naehrwert_hud ersetzt die alte Prioritäten-Box, zeigt Empfehlungen basierend auf Sättigung, Wärme & Wetter.
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
    
    # Prioritäten-Logik
    prio_lines = []
    
    # 1. Kritische Zustände
    if saettigung < 20:
        prio_lines.append(f"  {red}⚠ AKUT: Beeren essen! (Sättigung < 20%){reset}")
    elif waerme == 0 and wetter in ("regnerisch", "stürmisch", "neblig"):
        prio_lines.append(f"  {blue}⚠ Kälte-Risiko: Tee trinken für Wärme-Schutz.{reset}")
    
    # 2. Wetter-spezifisch
    if wetter == "regnerisch":
        if tee == 0:
            prio_lines.append(f"  {cyan}💧 Erster Regen: Tee aufbauen (Wärme-Puffer).{reset}")
        elif beeren > tee * 3:
            prio_lines.append(f"  {yellow}📊 Beeren-Dominanz: Tee priorisieren (Balance).{reset}")
        elif tee > beeren * 2:
            prio_lines.append(f"  {yellow}📊 Tee-Überhang: Beeren für Energie nachlegen.{reset}")
        else:
            prio_lines.append(f"  {green}✅ Ausgewogen: Mix halten.{reset}")
    elif wetter == "stürmisch":
        prio_lines.append(f"  {orange}🌬️ Sturm: Wärme verbraucht sich schneller -> Tee!{reset}")
    elif wetter == "neblig":
        prio_lines.append(f"  {dim}🌫️ Nebel: Sättigung sinkt schneller -> Beeren!{reset}")
    elif wetter == "klar":
        prio_lines.append(f"  {green}☀️ Klar: Entspannt naschen. Kein Druck.{reset}")
    
    # 3. Allgemeine Balance-Hinweise (nur wenn nix Kritisches)
    if not prio_lines:
        if beeren == 0 and tee == 0:
            prio_lines.append(f"  {cyan}🌱 Start: Erst Beeren für Basis, dann Tee.{reset}")
        elif saettigung > 80 and waerme < 3:
            prio_lines.append(f"  {yellow}💡 Tipp: Satt, aber kühl -> Teezeit.{reset}")
        elif waerme > 7 and saettigung < 50:
            prio_lines.append(f"  {yellow}💡 Tipp: Warm, aber leer -> Beerenzeit.{reset}")
        else:
            prio_lines.append(f"  {green}👍 Alles im grünen Bereich.{reset}")
    
    lines.extend(prio_lines[:3]) # Max 3 Prio-Zeilen für Kompaktheit
    
    # Visueller Rahmen
    max_len = max(len(l.replace('\033[91m','').replace('\033[92m','').replace('\033[93m','').replace('\033[96m','').replace('\033[94m','').replace('\033[38;5;208m','').replace('\033[1m','').replace('\033[2m','').replace('\033[0m','')) for l in lines)
    top = f"{yellow}┌{'─' * (max_len + 2)}┐{reset}"
    bot = f"{yellow}└{'─' * (max_len + 2)}┘{reset}"
    body = [f"{yellow}│{reset} {l.ljust(max_len)} {yellow}│{reset}" for l in lines]
    
    return "\n".join([top] + body + [bot])


def traum_ereignis(wetter: str, stats: dict, schritt: int) -> tuple[str, dict]:
    """Simuliert ein Traum-Ereignis, ändert Wetter & Stats leicht."""
    ereignisse = [
        ("Ein sanfter Wind weht...", "klar", {"saettigung": -2, "waerme": 0}),
        ("Nebel schwappt herein.", "neblig", {"saettigung": -5, "waerme": -1}),
        ("Donner grollt fern.", "stürmisch", {"saettigung": -3, "waerme": -2}),
        ("Ein Regenguss beginnt.", "regnerisch", {"saettigung": -4, "waerme": -3}),
        ("Sternschnuppe! Alles ruhiger.", "klar", {"saettigung": 0, "waerme": 1}),
    ]
    text, neues_wetter, delta = random.choice(ereignisse)
    
    # Stats anwenden
    stats["saettigung"] = max(0, min(100, stats.get("saettigung", 50) + delta.get("saettigung", 0)))
    stats["waerme"] = max(0, min(10, stats.get("waerme", 0) + delta.get("waerme", 0)))
    
    return neues_wetter, stats


def berechne_diplom(stats: dict) -> str:
    """Vergibt ein Diplom basierend auf Spielstil."""
    beeren = stats.get('beeren', 0)
    tee = stats.get('tee', 0)
    warten = stats.get('warten', 0)
    gesamt = beeren + tee + warten
    
    if gesamt == 0:
        return "🏅 Diplom: Träumer (Nichts getan, nur zugesehen)"
    
    if beeren > tee * 2 and beeren > warten * 2:
        return "🏅 Diplom: Beeren-Vernichter (Sättigung über Alles)"
    if tee > beeren * 2 and tee > warten * 2:
        return "🏅 Diplom: Tee-Meister (Wärme-Philosoph)"
    if warten > gesamt * 0.6:
        return "🏅 Diplom: Zen-Dodo (Meister des Wartens)"
    if abs(beeren - tee) <= 2 and beeren + tee > 5:
        return "🏅 Diplom: Ausgewogener Gourmet (Perfekter Mix)"
    if stats.get('kritisch_gerettet', 0) > 0:
        return "🏅 Diplom: Retter in der Not (Magen gerettet <20%)"
    
    return "🏅 Diplom: Dodo-Freund (Solide Bilanz)"


def zeige_abspann(stats: dict, schritte: int) -> None:
    """Zeigt den finalen Abspann mit Statistik & Diplom."""
    clear_screen()
    print("""    \\   //
     \\ //
      \\/\/\n     (o.o)
     (^_^)  Danke fürs Spielen!
    """)
    print(f"{ '=' * 40 }")
    print(f"Schritte gesamt: {schritte}")
    print(f"Beeren gegessen: {stats.get('beeren', 0)}")
    print(f"Tee getrunken:   {stats.get('tee', 0)}")
    print(f"Mal gewartet:    {stats.get('warten', 0)}")
    print(f"Wetter-Wechsel:  {stats.get('wetter_wechsel', 0)}")
    print(f"Kritisch gerettet: {stats.get('kritisch_gerettet', 0)}")
    print(f"{ '=' * 40 }")
    print(berechne_diplom(stats))
    print("\nFifo winkt: \\o/  Bis zum nächsten Hunger!\n")


def main() -> None:
    """Haupt-Schleife: Magen füttern, Tee wärmen, Träumen, Leben."""
    stats = {
        "saettigung": 50,
        "waerme": 0,
        "beeren": 0,
        "tee": 0,
        "warten": 0,
        "wetter_wechsel": 0,
        "kritisch_gerettet": 0,
    }
    wetter = "klar"
    schritt = 0
    eingaben = 0
    
    clear_screen(schritt)
    print(f"{'🦤 DODO-MAGENWÄRMER START':^40}")
    print(f"Tippe 1, 2, 3 oder 'q'. Max {MAX_EINGABEN} Aktionen.\n")
    pause(1.0)
    
    while eingaben < MAX_EINGABEN:
        schritt += 1
        knurrt = satte_pruefung(stats["saettigung"])
        
        # Passiver Verbrauch
        if wetter == "neblig":
            stats["saettigung"] = max(0, stats["saettigung"] - 1)
        elif wetter == "stürmisch":
            stats["waerme"] = max(0, stats["waerme"] - 1)
        elif wetter == "regnerisch":
            stats["saettigung"] = max(0, stats["saettigung"] - 1)
            stats["waerme"] = max(0, stats["waerme"] - 1)
        else:
            stats["saettigung"] = max(0, stats["saettigung"] - 0) # Klar: kein Verbrauch
        
        # Kritisch gerettet Check
        if stats["saettigung"] < 20 and stats.get("letzter_stand", 100) >= 20:
            stats["kritisch_gerettet"] = stats.get("kritisch_gerettet", 0) + 1
        stats["letzter_stand"] = stats["saettigung"]
        
        clear_screen(schritt)
        
        # UI Zeichnen
        print(f"Schritt {schritt} | {wetter_text(wetter)} | Eingaben: {eingaben}/{MAX_EINGABEN}")
        print(draw_bar(stats["saettigung"], waerme=stats["waerme"]))
        print(f"Wärme: {draw_waerme_bar(stats['waerme'])}")
        print()
        print(draw_stomach(stats["saettigung"], knurrt, stats["waerme"], schritt))
        print()
        print(draw_dodo(stats["saettigung"], schritt, stats["waerme"]))
        print()
        
        # NEU: Nährwert-HUD immer anzeigen (kompakt)
        print(zeige_naehrwert_hud(stats["saettigung"], stats["waerme"], wetter, stats))
        print()
        
        print("[1] Beere essen (+15% Sättigung)")
        print("[2] Tee trinken (+3 Wärme)")
        print("[3] Warten (Traum...)")
        print("[q] Beenden & Abspann")
        
        try:
            choice = input("\nDeine Wahl: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n\nEOF/Ende erkannt. Fifo verabschiedet sich...\n")
            break
        
        if choice == 'q':
            break
        
        if choice == '1':
            stats["saettigung"] = min(100, stats["saettigung"] + 15)
            stats["beeren"] += 1
            print("🍇 Mjam! Beere verputzt.")
        elif choice == '2':
            stats["waerme"] = min(10, stats["waerme"] + 3)
            stats["tee"] += 1
            print("🍵 Schlürf. Wärme breitet sich aus.")
        elif choice == '3':
            stats["warten"] += 1
            print("💤 Dodo träumt...", end="", flush=True)
            pause(0.5)
            wetter, stats = traum_ereignis(wetter, stats, schritt)
            stats["wetter_wechsel"] += 1
            print(f" -> {wetter_text(wetter)}!")
        else:
            print("? Unbekannt. 1, 2, 3 oder q.")
            continue # Keine Eingabe zählen bei Fehlbedienung? Eher doch zählen. Prompt sagt max 20 Eingaben.
        
        eingaben += 1
        pause(0.3)
    
    # Ende
    zeige_abspann(stats, schritt)

if __name__ == "__main__":
    main()