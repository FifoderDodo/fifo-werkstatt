# Notizen zu 3D-Tiefen-Shader

## Teil 1 (21.11.2026 13:52)
Erster Schritt: Grundgerüst für einen Raymarching-Tiefen-Shader erstellt. Koordinaten werden via NDC und Brennweite skaliert, eine simple SDF-Szene (Kugel + Boden) wird gemarcht und als ASCII-Tiefenkarte ausgegeben. Ein Input erlaubt das Skalieren der Projektionsmatrix.

```
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

Fertig. Teil 1 erledigt: Projektion & Skalierung laufen.
```

## Teil 2 (21.11.2026 13:58)
Kamera angehoben, Bodenplane auf y=-1 korrigiert, Normalenberechnung via SDF-Gradient hinzugefügt, Lambert-Schattierung mit Lichtrichtung und Nebel-Effekt implementiert, ASCII-Rampe erweitert und Ausgabe kombiniert aus Tiefe und Beleuchtung.

```
                       
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
............................................................
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:::::::::::::::::::::::::          :::::::::::::::::::::::::
:::::::::::::::: **############%%%%%%%%%%%# ::::::::::::::::
'''''''''''****############%%%%%%%%%%%%%%%%%%%%%%'''''''''''
'''''''+*****############%%%%%%%%%%%%%%%%%%%%%%%%%%%%'''''''

Fertig. Teil 2 erledigt: Normals, Lambert-Shading und Nebel hinzugefügt.
```

## Teil 3 (21.11.2026 14:04)
Noise-Funktion (Value Noise) hinzugefügt und in SDF für Kugel (Bumps) und Boden (Heightmap) eingebaut. Raymarch-Schritte erhöht, Epsilon angepasst. Normals berechnen sich automatisch über das gestörte SDF – das simuliert Parallax-/Bump-Mapping ohne zusätzliche Textur-Abfragen.

```
              
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
............................................................
:::::::::::::::::::::::::.::::::::::::::::::::::::::::::::::
::::::::::::::**###############%%%%%%%%#::::::::::::::::::::
:::::''''***###########%%%%%%%%%%%%%%%%%%%%%%#''''::::''''''
''''' +***##########%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'''''''''
'--++****#########%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%----

Fertig. Teil 3 erledigt: Heightmap/Parallax-Struktur via Noise im SDF integriert.
```

## Teil 4 (21.11.2026 14:46)
Hinzugefügt: shadow_raymarch-Funktion für harte Schatten mit Normalen-basiertem Bias (Self-Shadowing-Vermeidung). Im Hauptloop wird der Treffpunkt leicht entlang der Normalen versetzt, bevor der Schattenstrahl in Lichtrichtung gemarcht wird. Der Schattenfaktor (0/1) moduliert die diffuse Beleuchtung. ASCII-Ausgabe nutzt weiterhin kombinierten Tiefen-/Schattenwert.

```
                                                       
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
............................................................
:::::::::::::::::::::::::.::::::::::::::::::::::::::::::::::
::::::::::::::**###############%%%%%%%%#::::::::::::::::::::
:::::''''***###########%%%%%%%%%%%%%%%%%%%%%%#''''::::''''''
''''' +***##########%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'''''''''
'--++****#########%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%----

Fertig. Teil 4 erledigt: Depth-Buffer genutzt, Schattenstrahlen mit Normalen-Bias für saubere Kanten.
```

## Teil 5 (21.11.2026 15:05)
shadow_raymarch auf Soft Shadows umgestellt: akkumuliert Schattenfaktor basierend auf dist/tiefe-Verhältnis (Penumbra). Parameter softness=0.5, max_schritte=50, Bias 0.015. Ambient leicht gesenkt für mehr Kontrast. ASCII-Rampe erweitert.

```
     
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
""""""""""""""""::"""""""""""""""""""""""""""":"""""""""""""
::::::::::::::::::::::::::::::;::::::::;::::::::::::::::::::
;;;;;;;;;;;;;;{}[[[]]]](((((((((()))))((;;;;;;;;;;;;;;;;;;::
~;;;;~~~~<{}}[[]]](((((((()))))))))))))))))))(~~~~;;;;~~~~~~
~;~~! ><{}}[[]]]((((()))))))))))))))))\\\\\)\)))))(~~;;~~!!!
~!!!><<{}[[[]]((((()))))))))))))))\\\///\\//\\\\\))))))(!!!!

Fertig. Drück Enter für Exit.
```

## Teil 6 (21.11.2026 15:20)
Shadow-Raymarching auf Quilez-Formel (k*dist/t) umgestellt für weichere Penumbra, harter Abbruch entfernt, Mindestschritt 0.01 gegen Stottern. Hit-Daten (Normalen, Shadow, Specular) werden im ersten Pass gespeichert, zweiter Pass macht Lighting mit Diffuse, Ambient, Specular und Tiefen-Nebel. ASCII-Rampe genutzt für glatte Abstufungen.

```
                
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
                                                            
rxxrjnunrnnxxnr1nnnxnnjxuuxxnnxnx(|xxxxnrnunt\nxrxr|(/xnxnxx
nnnxt\vvunuuxxvcurnuunuur(fnnuuunuvvr|jvunuuj\\jnnnuununj/\j
nujvzzvnvvuuvvcXYUJJCCLLLQQQQQ00OOOOOOO0vvuvvuuczcnjjvvnvvr|
ccvttvccuxvzXYUJCCLQQQ0000OOOOOZZmmmmmmmmmmZZ0cvczvt/juccvvc
u/rcz fxvzXYUJCCLQQQ000OOOOOOZZZmmwwwwwwwwwwwwwmmZOcnt/tnczc
ncz|trnvzXYUJCLLQQ000OOOOZZZZZZmmwwwqqqqqqqqqqqqqqwwwmmZzXYX

Fifo watschelt zufrieden davon. Nächster Schritt: Reflections? AO? Volumetrics?
```

## Teil 7 (21.11.2026 15:28)
Shadow-Raymarching auf weichere Penumbra umgestellt: Parameter 'sharpness' (kleiner = weicher) statt 'softness', Standard 0.3. Minimaler Schritt auf 0.001 reduziert, Max-Schritte auf 60 erhöht, Max-Dist auf 30.0. Neue Benutzereingabe für Schatten-Schärfe hinzugefügt. Normalen werden nun im ersten Pass gespeichert für zweiten Lighting-Pass.

```
!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;:;;;;;;;;;::;;;;;;:;;;;;;;;;;::;;;;;;;;;::;;;;::::;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;:;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;***///////////////////////;;;;;;;;;;;;;;;;;;;;
;;;;;;!!;****//////////////////????????????///;;;;;;;;;;;;;;
!;;!!;+****//////////////????????????????????????//!;;;;!!!!
!!!++****/////////////????????????????????????????????//!!!!

Fertig.
```
