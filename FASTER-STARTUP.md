# Making Qt programs start faster (large font collections)

**Applies to:** BubblR Trainer, but also **every** Qt program on your PC
(e.g. Krita) — they start slowly because, on the first text they draw, Qt loads
**all installed fonts**.

## Why it's slow

Measured on this PC: startup hangs for **~9 seconds** at a single point — the
moment Qt first draws text, it reads the **whole Windows font database**. This
PC has **~8356 fonts** installed, so reading them takes that long.

This is **not an app bug** and can't be turned off in the program (PyQt5 **and**
PyQt6 are equally slow). The only real lever is **having fewer fonts installed
system-wide.** With a few hundred instead of thousands, everything starts in
~1 second.

> The app now shows a splash screen instantly so it doesn't look frozen — but
> the wait itself comes from the fonts.

### Why does it load *my whole* font library?

Not because the app wants your fonts — **Qt** builds one global font database
the first time any text is measured, and to do that it enumerates every
installed font. It needs the full list for **fallback** (when the UI font lacks
a character — Japanese, emoji, symbols — Qt searches your other fonts) and for
**name lookup**. It happens once per launch and is proportional to the number of
installed fonts, so thousands of fonts = a long wait.

## Step 0: How many fonts do you have?

Open PowerShell and run:

```powershell
(Get-ChildItem C:\Windows\Fonts -Include *.ttf,*.otf,*.ttc -Recurse).Count
```

Anything over ~800 makes Qt programs noticeably slower.

## Recommended: a font manager (activate fonts only when needed)

A font manager keeps your fonts in a folder and **activates only the ones you're
currently using** — instead of permanently installing thousands into Windows.
Perfect for typesetting: the full collection stays at hand, but Windows (and
therefore Qt) only sees a few.

**Free options:** FontBase, NexusFont.

Rough workflow (FontBase as an example):

1. **Back up first:** copy `C:\Windows\Fonts` to a backup folder
   (e.g. `D:\Fonts-Backup`). Then nothing can be lost.
2. Install the font manager and add your font collection as a **folder**
   (e.g. the backup folder).
3. **Uninstall** the many manually installed fonts from Windows (see next
   section) — the system fonts stay.
4. From now on: in the font manager, **activate** the fonts you need for a
   project, then **deactivate** them again afterwards. Krita/Photoshop see the
   active fonts normally.

Result: Windows only has the system fonts + whatever is currently active → Qt
startup in ~1 second.

## Alternative: remove fonts manually

If you don't want a font manager, just remove the fonts you don't need:

1. **Back up first!** Copy `C:\Windows\Fonts` somewhere else.
2. Open **Settings → Personalization → Fonts**
   (or `Win + R` → `ms-settings:fonts`).
3. Click a font you don't need → **Uninstall**.
   (Several at once: select them in the old `C:\Windows\Fonts` window and delete.)

### ⚠️ Do NOT remove (Windows needs these)

Leave these alone, or apps/Windows will look broken:

- **Segoe UI** (the whole family) — the Windows UI font
- **Arial, Tahoma, Verdana, Times New Roman, Courier New**
- **Calibri, Cambria, Consolas**
- **Symbol fonts:** Segoe UI Emoji, Segoe MDL2/Fluent Icons, Marlett,
  Webdings, Wingdings

When in doubt: only remove fonts you installed yourself for manga/design work.

## Did it help? (quick test)

After cleaning up, relaunch the trainer — it should appear in ~1 s. To measure
process-start → window in PowerShell:

```powershell
$p = Start-Process pythonw "`"$PWD\bubblr_trainer_app.py`"" -PassThru
$sw = [Diagnostics.Stopwatch]::StartNew()
while (-not $p.HasExited -and $p.MainWindowHandle -eq 0) { $p.Refresh(); Start-Sleep -Milliseconds 20 }
"$([math]::Round($sw.Elapsed.TotalSeconds,2)) s to window"
$p.CloseMainWindow() | Out-Null
```

(Use `pythonw`, not `python` — with `python` the measurement would wrongly catch
the console window.)

## Summary

| Measure | Effort | Effect |
| --- | --- | --- |
| Splash screen (already built in) | – | feels instant, same total time |
| Manage fonts with a font manager | medium | **~1 s start**, collection kept |
| Uninstall fonts you don't need | small–medium | **~1 s start** |

The font manager is the best solution: you keep your whole font collection and
still get fast startup in every program.
