# Qt-Programme schneller starten (viele Schriftarten)

**Betrifft:** BubblR Trainer, aber auch **jedes** Qt-Programm auf deinem PC
(z. B. Krita) — sie starten langsam, weil beim ersten Text **alle installierten
Schriften** eingelesen werden.

## Warum es langsam ist

Gemessen auf diesem PC: der Start hängt **~9 Sekunden** an einer einzigen
Stelle — sobald Qt zum ersten Mal Text darstellt, liest es die **komplette
Windows-Schrift-Datenbank** ein. Auf diesem PC sind **~8356 Schriften**
installiert; das Einlesen dauert entsprechend lang.

Das ist **kein App-Fehler** und lässt sich nicht im Programm abschalten
(PyQt5 **und** PyQt6 sind gleich langsam). Der einzige echte Hebel: **weniger
Schriften systemweit installiert haben.** Bei ein paar hundert statt tausenden
startet alles in ~1 Sekunde.

> Die App zeigt inzwischen sofort ein Ladebild, damit sie nicht „eingefroren"
> wirkt — die Wartezeit selbst kommt aber von den Schriften.

## Schritt 0: Wie viele Schriften sind es?

PowerShell öffnen und eingeben:

```powershell
(Get-ChildItem C:\Windows\Fonts -Include *.ttf,*.otf,*.ttc -Recurse).Count
```

Alles über ~800 macht Qt-Programme spürbar langsamer.

## Empfohlen: Font-Manager (Schriften nur bei Bedarf aktivieren)

Ein Font-Manager hält deine Schriften in einem Ordner und **aktiviert nur die,
die du gerade brauchst** — statt tausende dauerhaft in Windows zu installieren.
Ideal fürs Typesetting: die volle Sammlung bleibt griffbereit, Windows (und
damit Qt) sieht aber nur wenige.

**Gratis-Optionen:** FontBase, NexusFont.

So gehst du vor (grober Ablauf, mit FontBase als Beispiel):

1. **Vorher sichern:** kopiere `C:\Windows\Fonts` in einen Backup-Ordner
   (z. B. `D:\Fonts-Backup`). So kann nichts verloren gehen.
2. Font-Manager installieren und deine Schrift-Sammlung als **Ordner**
   hinzufügen (z. B. den Backup-Ordner).
3. Die vielen **manuell installierten** Schriften aus Windows **deinstallieren**
   (siehe nächster Abschnitt) — die Systemschriften bleiben.
4. Ab jetzt: im Font-Manager die Schriften, die du für ein Projekt brauchst,
   **aktivieren**; danach wieder **deaktivieren**. Krita/Photoshop sehen die
   aktivierten Schriften ganz normal.

Ergebnis: Windows hat nur noch die Systemschriften + gerade aktive → Qt-Start
in ~1 Sekunde.

## Alternative: Schriften manuell aussortieren

Wenn du keinen Font-Manager willst, entferne einfach die Schriften, die du nicht
brauchst:

1. **Backup zuerst!** `C:\Windows\Fonts` woanders hinkopieren.
2. **Einstellungen → Personalisierung → Schriftarten** öffnen
   (oder `Win + R` → `ms-settings:fonts`).
3. Nicht benötigte Schrift anklicken → **Deinstallieren**.
   (Mehrere auf einmal: im alten `C:\Windows\Fonts`-Fenster markieren und
   löschen.)

### ⚠️ NICHT entfernen (Windows braucht sie)

Finger weg von diesen — sonst sehen Programme/Windows kaputt aus:

- **Segoe UI** (die ganze Familie) — die Windows-Oberflächenschrift
- **Arial, Tahoma, Verdana, Times New Roman, Courier New**
- **Calibri, Cambria, Consolas**
- **Symbol-Schriften:** Segoe UI Emoji, Segoe MDL2/Fluent Icons, Marlett,
  Webdings, Wingdings

Im Zweifel: nur Schriften entfernen, die du selbst mal für Manga/Design
installiert hast.

## Hat es geholfen? (schneller Test)

Nach dem Aufräumen den Trainer neu starten — er sollte in ~1 s da sein.
Genauer messen (Prozessstart → Fenster) geht so in PowerShell:

```powershell
$p = Start-Process pythonw "`"$PWD\bubblr_trainer_app.py`"" -PassThru
$sw = [Diagnostics.Stopwatch]::StartNew()
while (-not $p.HasExited -and $p.MainWindowHandle -eq 0) { $p.Refresh(); Start-Sleep -Milliseconds 20 }
"$([math]::Round($sw.Elapsed.TotalSeconds,2)) s bis Fenster"
$p.CloseMainWindow() | Out-Null
```

(Wichtig: `pythonw`, nicht `python` — bei `python` würde die Messung fälschlich
das Konsolenfenster erkennen.)

## Kurzfassung

| Maßnahme | Aufwand | Effekt |
| --- | --- | --- |
| Splash-Ladebild (schon eingebaut) | – | fühlt sich sofort an, Zeit gleich |
| Schriften mit Font-Manager verwalten | mittel | **Start ~1 s**, Sammlung bleibt |
| Unnötige Schriften deinstallieren | klein–mittel | **Start ~1 s** |

Der Font-Manager ist die beste Lösung, weil du deine ganze Schrift-Sammlung
behältst und trotzdem alle Programme schnell starten.
