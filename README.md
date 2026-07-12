# BubblR Trainer — standalone app

A normal desktop program (not a plugin, not a website) for making BubblR
training pages. Same job as the Krita/Photoshop BubblR Trainer plugins, but it
runs on its own — **no Krita, no Photoshop needed**. Perfect for helpers who
just want to label images.

## Run it

- **No-Python `.exe` (easiest):** run **`dist/BubblR-Trainer/BubblR-Trainer.exe`**
  — no Python or PyQt5 install needed. It's a folder build (fastest start, no
  unpacking) — keep the `BubblR-Trainer` folder together and run the `.exe`
  inside it. Build it yourself with **`build_exe.bat`** (see Notes).
- **Windows (with Python):** double-click **`run.bat`** — installs PyQt5 the
  first time, then starts the app.
- **Shortcuts:** on its **first launch** (any way you start it) the app pops up a
  small **clickable dialog** — tick *Desktop*, *Start menu*, both or neither, and
  it creates the shortcut(s) with the app icon. No console, asked only once. You
  can also run **`make_shortcut.bat`** anytime to (re)create both (it targets the
  `.exe` if you built one, otherwise the Python app).
- **macOS / Linux / any OS (with Python):**
  ```
  pip3 install PyQt5
  python3 bubblr_trainer_app.py
  ```
  The app itself is cross-platform (PyQt5). The **`.exe` and the `.bat` files are
  Windows-only**, and the desktop/Start-menu *shortcut* helper is skipped on
  macOS/Linux (everything else — labelling, export, classes, Discord Rich
  Presence via the local socket — works). To get a double-clickable **macOS
  `.app`**, build it *on a Mac* with PyInstaller (`pyinstaller --windowed
  --name "BubblR Trainer" bubblr_trainer_app.py`); PyInstaller can't
  cross-compile, so a Windows `.exe` can't run on a Mac.

> No Python yet? Install it from https://www.python.org/downloads/ (Windows: tick
> "Add Python to PATH"; macOS: `brew install python`) — only needed for the
> manual / `run.bat` run, not for the prebuilt Windows `.exe`.

## Start page

When no pages are loaded, the canvas shows a **Krita-style start page**: big
**Load images / Load folder / Open project / Rank && load** buttons and a grid
of **recent images** — click a thumbnail to jump straight back into it. It
reappears whenever you close all pages.

**Drag & drop:** you can also drag image files, a whole folder, or a project
`.json` **anywhere onto the window** to load them — on the start page or while
editing.

**News & updates:** the start page has a **News** column that loads a small
`news.json` from the project's GitHub on startup and shows an **“Update
available”** banner when a newer version exists — so you don't have to check
GitHub yourself. It only does an HTTPS GET of a public file (no personal data
sent) and can be turned off under *Settings → Display*.

**Automatic updates (Windows .exe):** when a newer version is found, BubblR
Trainer downloads it in the background from the latest GitHub release and stages
it. It then installs itself **on the next launch** — during the splash it swaps
in the new build and relaunches once, with **no dialog and no restart prompt**
(Krita-style). If you'd rather not wait, an optional **“Install now”** button in
the News column applies it straight away. Auto-download can be turned off under
*Settings → Display*. The source (`.py`) version isn't self-replacing — update it
with `git pull`.

## How to label

1. **Load images…** — pick one or many manga page images (PNG/JPG/…). They become
   pages you can step through with ◀ / ▶.
   - **Zoom**: mouse wheel (zooms around the cursor). **Pan**: drag with the
     middle mouse button. **Fit** button resets to fit-the-window.
   - **Close pages** when you're done with them (no need to quit the app):
     **✕ Close page** (**Ctrl+W**) drops the current page, **Close all** clears
     everything. This only removes them from the session — the image files on
     disk are never touched. You're asked to confirm if a page still has boxes
     you haven't exported.
   - **Rank the pages for labelling**: the **Sort pages** dropdown reorders the
     loaded pages — *by name*, *unlabelled first*, *unexported first*, *fewest
     boxes first*, or *most boxes first* — so you always know what to do next.
     **Next unlabelled** jumps to the next page that still has no boxes and
     **Page → Next unexported** jumps to the next labelled-but-not-yet-exported
     page; the counter shows how many pages are labelled and exported (e.g.
     `12/20 labelled, 8 exported`).
2. **Pick a marking tool** (in the **Tools** panel) — that alone puts you in
   draw mode, no separate button:
   - drag on empty space = new box,
   - drag inside a box = move,
   - drag a **corner or edge** = resize (the cursor shows what you'll grab),
   - right-click a box (or a row in the Boxes list) = **context menu**
     (delete, duplicate, fit to bubble, **mark as Bubble/SFX**),
   - right-click **empty space** = canvas menu (**paste a box right where you
     clicked**, select all, deselect, fit to window).

   When boxes overlap, the **currently selected box has priority** — click a box
   to select it, then editing stays on that box instead of grabbing whatever
   overlaps it.

   The tools (icon-only, Krita-style):
   - **▭ Rectangle** — the classic corner-to-corner box.
   - **◯ Ellipse** — drag an oval (nice for round bubbles); the saved box is its
     bounding rectangle.
   - **✎ Lasso** — draw a freehand outline; the box wraps tightly around it.
   - **✨ Magic wand** — *click once* inside a bubble and it auto-detects the
     same-colour region and boxes it. Set the **wand tolerance** under
     *Settings → Tools* (higher = grabs more, lower = grabs less).

   The **Centre marker** checkbox shows a cross + dot at the middle of every
   marking (and a live one while you drag), so you can see exactly where the
   centre lands. The **Order path** checkbox draws the `1 → 2 → 3` reading-order
   path (with arrows) between the boxes, so after **Auto order** you can check
   the sequence at a glance and fix only the few steps it got wrong. Every tool
   still exports as a normal YOLO bounding box, so the dataset format never
   changes.

   **Undo / Redo** (**Ctrl+Z** / **Ctrl+Y**, also in the Edit menu) step through
   adds, moves, resizes, deletes, relabels and ordering changes.
3. Set the **class** per box: a new box gets the **default class** (pick it once
   under *Settings → New boxes*, defaults to Bubble); **right-click → SFX** (or
   press **B** / **S**) to change any box. Colours: Bubble = red, SFX = blue.
4. *(optional)* **Set reading order** (button, top row) → click the bubbles in
   order (1, 2, 3 …), or **Auto order** (top row) to number them automatically.
   *Edit → Clear reading order* restarts. Manga right-to-left is set under
   *Settings → Tools*.
5. Choose a **dataset folder** (once — can be a shared Drive folder).
6. **File → Export this page / Export all pages** (**Ctrl+E** / **Ctrl+Shift+E**).

The canvas fills the window — undo/redo, delete, clear, class and export live in
the **Edit / File menus** and the **right-click menu** rather than button rows.
A small row under the canvas has a **Show** filter (All / Bubbles only / SFX
only — hides the other class on the canvas and dims it in the Boxes list) and an
**Auto order** toggle
that re-numbers the reading order automatically after every add/move/delete.

There's a **menu bar** (File / Edit / Page / View / Settings / Help) with
everything the
buttons do, each item showing its shortcut.

### Keyboard shortcuts (press **F1** in the app for this list)

| Key | Action |
| --- | --- |
| **B** / **S** | set the selected box to Bubble / SFX |
| **Delete** / **Backspace** | delete the selected box |
| **Arrow keys** | nudge the selected box (**Shift** = 10 px) |
| **Alt + arrows** | resize the selected box (**Shift** = 10 px) |
| **Ctrl+C** / **Ctrl+V** | copy / paste a box (also from one page onto another) |
| **Ctrl+D** | duplicate the selected box |
| **Ctrl+click** (or the Boxes list) | select several boxes — delete/relabel act on all |
| **drag on empty space** (view mode) | rubber-band: select every box the rectangle covers |
| **Ctrl+A** | select all boxes on the page |
| **F** | fit the selected box tightly onto the bubble |
| **Z** | zoom the view onto the selection |
| **Esc** | deselect |
| **[** / **]** | previous / next page |
| **Ctrl+Z** / **Ctrl+Y** (or **Ctrl+Shift+Z**) | undo / redo |
| **Ctrl+W** | close the current page |
| Mouse wheel / middle-drag | zoom / pan |

- **Dockable panels (Krita-style):** the **Tools** (icon-only marking tools +
  wand tolerance), **Boxes** and **Pages** (thumbnails) panels are dock widgets
  you can rearrange around the canvas — drag them by their title bar to any
  edge (**left, right, top or bottom**) or float them. When two panels share an
  edge they **tab together with the tabs on top**. Turn *View → Lock panels* on
  to freeze the layout so nothing moves by accident; off again to rearrange.
  The **Pages** panel adapts automatically: a scrolling row of thumbnails on
  the top/bottom, and a **grid on the left/right** that grows the thumbnails as
  you widen it and then **reflows to 2, then 3 … columns** instead of one
  ever-bigger column. Panel **positions and sizes** (how wide/tall you dragged
  each dock) and the window size are all remembered between runs.
- A **page thumbnail strip** lets you jump to any page with a
  click. Each thumbnail shows its status: **✓** = exported to the dataset,
  **•** = has boxes but not exported yet, nothing = still empty (editing an
  exported page flips it back to **•** so you know it needs re-exporting).
  **Right-click a thumbnail** to jump to that page or close it (without
  switching to it first).
- A **Boxes** list on the right shows every box on the page — click one to
  select it (handy when boxes overlap), **Ctrl/Shift-click for several**, or
  **drag items to reorder them**, which sets the reading order (1, 2, 3 …)
  top-to-bottom. Delete/relabel then act on the whole selection.
- A **progress bar** shows how many pages already have boxes (`12 / 40 pages
  labelled`).
- **F** tightens the selected box onto the bubble inside it (flood-fill) — a
  quick way to snap a loose box to the balloon.
- **Auto-recovery:** the session is auto-saved every minute; if the app closed
  unexpectedly, it offers to restore your unsaved work on the next start.
- **Quit guard:** if any page still has boxes you haven't exported, quitting
  asks for confirmation first (the counter and the • thumbnail markers show
  which pages), so you don't lose labelling work by accident.
- The window also remembers its size and position between sessions.

**Save project… / Load project…** stores every page + its boxes (and order) as a
`.json` so you can pause and resume. (It references the image paths, so keep the
images where they are.)

## What export writes

Into the chosen dataset folder — identical to the plugins, so all four tools feed
the same dataset:

```
images/train/<page>_<id>.png   the page (full colour, full resolution)
labels/train/<page>_<id>.txt   YOLO: "class cx cy w h", normalized 0..1
order/<page>_<id>.json         boxes sorted by reading order (+ class)
preview/<page>_<id>.png        the page with boxes + reading-order numbers drawn
                               (and the order path if "Order path" is on) to
                               check by eye
classes.txt                    one class name per line (index order)
data.yaml                      YOLO / Ultralytics dataset config (path, train,
                               val, nc, names) — train straight from it
```

Set a **validation split** under *Settings → Storage location* (e.g. 10–20 %):
that share of pages goes to `images/val` + `labels/val` instead of `train`, the
split is **stable per page** (so a page never lands in both across exports), and
`data.yaml`'s `val:` points at it. 0 % keeps everything in `train`.

**Background / negative images:** turn on *Export empty pages as background
images* (*Settings → Storage location*) to also export pages that have **no
boxes**, each with an empty label file. Training on backgrounds teaches the model
what *isn't* an object and cuts down false detections. The export summary then
reports how many negatives went out, flags any class with **no examples**, and
warns when your classes are badly **imbalanced**.

Classes: **bubble = 0**, **sfx = 1** by default.

## Not just manga — any object detector

The export is plain **YOLO detection data** (image + `class cx cy w h`), so the
classes are just *whatever you define*. Under **Settings → Classes** you can
add / rename / recolour / reorder your own classes (each box's YOLO number is
its position in the list). That turns BubblR Trainer into a general
bounding-box annotator for **any** detector — faces, cars/plates, products,
manufacturing defects, UI elements, etc. Press **1–9** (or **B** / **S**) to set
the selected box's class, and *Reset to manga* restores the Bubble / SFX
default. **Import…** reads the class names from an existing `classes.txt` or
YOLO `data.yaml` so you can match another dataset in one click. The reading-order
export is a manga bonus you can simply ignore.

## Notes

- **🎯 Rank & load… (optional):** if the BubblR AI tool is present, this button
  ranks a folder of raw pages by how much they'd teach the model (active
  learning) and loads the top ones straight in — so you label the most useful
  pages first. The trainer stays AI-free otherwise: without the AI tool the
  button just points you to it (it looks for the AI folder next to the app, or
  you pick it once). The ranking runs in the background; the model load makes
  the first run take a moment.
- **Settings** (menu bar → *Settings*) opens a small window with tabs on the
  left: **Display** (language, centre marker), **New boxes** (default class),
  **Tools** (magic-wand tolerance, manga right-to-left), **Discord** (Rich
  Presence — see below) and **Storage location** (dataset/export folder). All
  stored in `~/.bubblr_trainer.json`.
- **Discord Rich Presence** *(optional):* show “in BubblR Trainer” with your
  current page/progress on your Discord profile. Just tick *View → Show on
  Discord* (or *Settings → Discord*) — a **built-in Application ID is used, so
  no per-user setup is needed** (Discord must be running on the same PC). Power
  users can paste their own Application ID in *Settings → Discord* to show a
  different name. No extra install — it talks to Discord's local socket from a
  background thread and does nothing if Discord isn't there.
  - *(For the maintainer)* the built-in id is `DEFAULT_DISCORD_CLIENT_ID` near
    the top of `bubblr_trainer_app.py`: create one free application named
    *BubblR Trainer*, upload an `icon` art asset, and paste its **public**
    Application ID there so it works for everyone.
- Bilingual (English / Deutsch) — switch it under Settings → Display.
- **Make a no-Python `.exe`:** double-click **`build_exe.bat`** (installs
  PyInstaller if needed, then builds). Result: the folder
  `dist/BubblR-Trainer/` with **`BubblR-Trainer.exe`** inside — no Python or
  PyQt5 needed to run it.
  - This is a *one-folder* (`--onedir`) build. Share the **whole folder**
    (~90 MB). Want a single portable file instead? Edit `build_exe.bat` to use
    `--onefile` — then you get one `dist/BubblR-Trainer.exe`, at the cost of a
    short unpack on every start.
  - The `build/`, `dist/` and `.spec` outputs are git-ignored (the build isn't
    committed — rebuild it locally).
- **Slow to start?** On a PC with a huge font collection the first window can
  take several seconds while Qt loads the system fonts (this affects every Qt
  app, e.g. Krita — it's not the app itself). A splash appears instantly so it
  doesn't look frozen. To actually cut the wait, see
  **[FASTER-STARTUP.md](FASTER-STARTUP.md)**.
