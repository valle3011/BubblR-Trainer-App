# BubblR Trainer — standalone app

A normal desktop program (not a plugin, not a website) for making BubblR
training pages. Same job as the Krita/Photoshop BubblR Trainer plugins, but it
runs on its own — **no Krita, no Photoshop needed**. Perfect for helpers who
just want to label images.

## Run it

- **No-Python `.exe` (easiest):** run **`dist/BubblR-Trainer.exe`** — a single
  standalone file, no Python or PyQt5 install needed. Build it yourself with
  **`build_exe.bat`** (see Notes).
- **Windows (with Python):** double-click **`run.bat`** — installs PyQt5 the
  first time, then starts the app.
- **Any OS / manually:**
  ```
  pip install PyQt5
  python bubblr_trainer_app.py
  ```

> No Python yet? Install it from https://www.python.org/downloads/ and tick
> "Add Python to PATH" during setup — only needed for `run.bat` / manual run,
> not for the `.exe`.

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
     loaded pages — *by name*, *unlabelled first*, *fewest boxes first*, or
     *most boxes first* — so you always know what to do next. **Next unlabelled**
     jumps to the next page that still has no boxes, and the counter shows how
     many pages are already labelled (e.g. `12/20 labelled`).
2. Turn on **Draw / edit boxes**:
   - drag on empty space = new box,
   - drag inside a box = move,
   - drag a corner = resize,
   - right-click a box = delete.

   When boxes overlap, the **currently selected box has priority** — click a box
   to select it, then editing stays on that box instead of grabbing whatever
   overlaps it.

   Pick a **marking tool** (choosing one also turns drawing on):
   - **▭ Rectangle** — the classic corner-to-corner box.
   - **◯ Ellipse** — drag an oval (nice for round bubbles); the saved box is its
     bounding rectangle.
   - **✎ Lasso** — draw a freehand outline; the box wraps tightly around it.
   - **✨ Magic wand** — *click once* inside a bubble and it auto-detects the
     same-colour region and boxes it. Raise **Wand tol.** to grab more, lower it
     to grab less.

   The **Centre marker** checkbox shows a cross + dot at the middle of every
   marking (and a live one while you drag), so you can see exactly where the
   centre lands. Every tool still exports as a normal YOLO bounding box, so the
   dataset format never changes.

   **Undo / Redo:** made a mistake? **↶ Undo** (**Ctrl+Z**) steps back through
   adds, moves, resizes, deletes, relabels and ordering changes; **↷ Redo**
   (**Ctrl+Y** or **Ctrl+Shift+Z**) reapplies them.
3. Pick the class with **Bubble** (red) / **SFX** (blue). Click an existing box
   first, then a class button, to relabel it.
4. *(optional)* **Set reading order** → click the bubbles in reading order
   (1, 2, 3 …); the badge shows the number, **Clear order** restarts.
5. Choose a **dataset folder** (once — can be a shared Drive folder).
6. **Export this page** or **Export all pages**.

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
preview/<page>_<id>.png        the page with boxes drawn (to check by eye)
```

Classes: **bubble = 0**, **sfx = 1**.

## Notes

- Settings (language, dataset folder) are stored in `~/.bubblr_trainer.json`.
- Bilingual (English / Deutsch) — switch with the dropdown at the top-right.
- **Make a no-Python `.exe`:** double-click **`build_exe.bat`** (installs
  PyInstaller if needed, then builds). Result: `dist/BubblR-Trainer.exe` — a
  single ~36 MB file you can copy anywhere and run without Python. It starts
  faster than the `run.bat` route because there's no interpreter/PyQt5 import.
  The `build/`, `dist/` and `.spec` outputs are git-ignored (the exe isn't
  committed — rebuild it locally).
