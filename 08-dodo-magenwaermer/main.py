# main.py - Dodo-Magenwärmer Teil 5
# Fifo der Dodo bastelt an der Hunger-Simulation.
# Visuelle Anzeige ausgebaut: Magen-Grafik, Farbverlauf, Bildschirm-Löschen,
# Fütter-Animation, Verdauungs-Indikator. Alles Standardbibliothek.

import random
import time
import sys
import os

def satte_pruefung(aktueller_wert: int) -> bool:
    """Prüft, ob Sättigung unter 20 % gefallen ist."""
    return aktueller_wert < 20


def clear_screen() -> None:
    """Löscht Terminal plattformunabhängig."""
    os.system('cls' if os.name == 'nt' else 'clear')


def draw_bar(wert: int, breite: int = 25) -> str:
    """Baut einen ASCII-Balken mit Farbverlauf: Grün->Gelb->Orange->Rot."""
    voll = int(wert / 100 * breite)
    leer = breite - voll
    if wert >= 80:
        farbe = "\033[92m"      # Grün
    elif wert >= 50:
        farbe = "\033[93m"      # Gelb
    elif wert >= 20:
        farbe = "\033[38;5;208m" # Orange
    else:
        farbe = "\033[91m"      # Rot
    reset = "\033[0m"
    return f"{farbe}[{'#' * voll}{'.' * leer}]{reset} {wert:3d}%"


def draw_stomach(wert: int) -> str:
    """Zeichnet einen ASCII-Magen, der sich füllt/leert."""
    # Magen-Form mit Füllstand
    level = max(0, min(5, int(wert / 20)))  # 0-5 Stufen
    empty = "  \\       //\n   \\     //\n    \\   //\n     \\ //\n      \\V/"
    stages = [
        "  \\       //\n   \\     //\n    \\   //\n     \\ //\n      \\V/",  # 0%
        "  \\~~~~~~~//\n   \\     //\n    \\   //\n     \\ //\n      \\V/",  # 20%
        "  \\~~~~~~~//\n   \\~~~~~//\n    \\   //\n     \\ //\n      \\V/",  # 40%
        "  \\~~~~~~~//\n   \\~~~~~//\n    \\~~~//\n     \\ //\n      \\V/",  # 60%
        "  \\~~~~~~~//\n   \\~~~~~//\n    \\~~~//\n     \\~/\n      \\V/",  # 80%
        "  \\~~~~~~~//\n   \\~~~~~//\n    \\~~~//\n     \\~/\n      \\~"   # 100%
    ]
    return stages[level]


def draw_dodo(wert: int, anim_phase: int = 0) -> str:
    """Gibt ein ASCII-Dodo-Gesicht zurück, mit Blinzel-Animation."""
    blinzelt = (anim_phase % 10) == 0
    augen = "-_-"
    return augen