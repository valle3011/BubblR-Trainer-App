# -*- coding: utf-8 -*-
"""User-visible strings for BubblR Trainer (English + German).

Split out of bubblr_trainer_app.py: it is pure data and made up roughly a
seventh of that file. Both tables must have the SAME keys — bubblr_trainer_app's
_tr() falls back to English for anything missing.
"""

LANG = {
    "en": {
        "title": "BubblR Trainer",
        "intro": ("Load page images, draw a box around every bubble and SFX, "
                  "label them, optionally set the reading order, then export. "
                  "No AI here - this only makes the training data.  "
                  "Press F1 for keyboard shortcuts."),
        "load": "Load images…",
        "prev": "◀", "next": "▶",
        "fit": "Fit",
        "zoom_tip": "Wheel = zoom · middle-drag = pan · this button = fit to window",
        "page_none": "no page", "page": "{i} / {n}  -  {name}",
        "edit": "Draw / edit boxes", "set_order": "Set reading order",
        "auto_order": "Auto order",
        "auto_order_tip": "Number all bubbles automatically by reading order (fix a few after)",
        "rtl": "R→L (manga)",
        "rtl_tip": "Manga reads right-to-left; uncheck for left-to-right",
        "ranked": "Auto-ranked {n} box(es) - adjust as needed.",
        "delete": "Delete selected", "clear_order": "Clear order",
        "clear": "Clear all page",
        "kind": "New box is:", "bubble": "Bubble", "sfx": "SFX",
        "relabel": "(click a box first to relabel it)",
        "counts_this_page": "This page",
        "counts_pages": "Pages: {done}/{p} labelled, {exp} exported",
        "sort_by": "Sort pages:",
        "sort_name": "by name",
        "sort_unlabeled": "unlabelled first",
        "sort_unexported": "unexported first",
        "show": "Show:", "show_all": "All", "show_only": "Only {name}",
        "show_bubble": "Bubbles only", "show_sfx": "SFX only",
        "mi_set_class": "Set class", "settings_classes": "Classes",
        "class_add": "Add…", "class_rename": "Rename…", "class_color": "Colour…",
        "class_remove": "Remove", "class_reset": "Reset to manga",
        "class_import": "Import…", "class_name": "Class name:",
        "class_import_fail": "No class names found in that file.",
        "class_imported": "Imported {n} class(es).",
        "settings_classes_hint": "Define the object classes for your dataset — "
                                "each box's YOLO class number is its position "
                                "here (0, 1, 2 …). The manga default is Bubble / "
                                "SFX; add your own to train ANY object detector "
                                "(faces, cars, defects …). Keys 1–9 (and B / S) "
                                "set the class of the selection quickly.",
        "auto_order_live": "Auto order",
        "auto_order_live_tip": "Re-number the reading order automatically after "
                               "every add / move / delete.",
        "sort_fewest": "fewest boxes first",
        "sort_most": "most boxes first",
        "next_todo": "Next unlabelled",
        "all_labelled": "All pages have at least one box.",
        "all_exported": "All labelled pages are exported.",
        "tool": "Tool:",
        "tool_rect": "▭ Rectangle",
        "tool_ellipse": "◯ Ellipse",
        "tool_poly": "⬠ Polygon",
        "tool_lasso": "✎ Lasso",
        "tool_wand": "✨ Magic wand",
        "tool_rect_hint": "Drag a rectangle corner-to-corner.",
        "tool_ellipse_hint": "Drag an ellipse; the box is its bounding rectangle.",
        "tool_poly_hint": "Polygon: click to add points; click the first point, "
                          "double-click or Enter to close. Backspace undoes a "
                          "point, Esc cancels.",
        "tool_lasso_hint": "Draw a freehand outline; the box wraps around it.",
        "tool_wand_hint": "Click inside a bubble to auto-detect its region.",
        "wand_tol": "Wand tol.",
        "wand_tol_tip": "Magic-wand colour tolerance (higher = grabs more).",
        "center_marker": "Centre marker",
        "center_marker_tip": "Show a cross + dot at the centre of every marking.",
        "order_path": "Order path",
        "order_path_tip": "Draw the 1->2->3 reading-order path between the boxes "
                          "so you can check (and fix) the order at a glance.",
        "undo": "↶ Undo",
        "redo": "↷ Redo",
        "undo_tip": "Undo the last change (Ctrl+Z)",
        "redo_tip": "Redo (Ctrl+Y or Ctrl+Shift+Z)",
        "nothing_undo": "Nothing to undo.",
        "nothing_redo": "Nothing to redo.",
        "undone": "Undone.",
        "redone": "Redone.",
        "close_page": "✕ Close page",
        "close_page_tip": "Remove this page from the session (Ctrl+W). The image "
                          "file on disk is not touched.",
        "close_all": "Close all",
        "close_all_tip": "Remove every loaded page from the session.",
        "confirm_title": "Close page",
        "confirm_close": "\"{name}\" has {n} box(es) that are not exported.\n\n"
                         "Close this page and discard them?",
        "confirm_close_all": "{p} page(s) hold {n} box(es) that are not "
                             "exported.\n\nClose all pages and discard them?",
        "confirm_quit_title": "Quit BubblR Trainer",
        "confirm_quit_unexported": "{n} page(s) have boxes that aren't exported "
                                   "to the dataset yet.\n\nQuit anyway? The "
                                   "unexported boxes will be lost unless you "
                                   "export them or save a project first.",
        "closed": "Page closed.",
        "closed_all": "All pages closed.",
        "sc_title": "Create a shortcut?",
        "sc_msg": "Add a BubblR Trainer shortcut for quick access?",
        "sc_desktop": "On the Desktop",
        "sc_startmenu": "In the Start menu",
        "sc_create": "Create",
        "sc_skip": "Not now",
        "sc_done": "Shortcut created.",
        "sc_none": "No location selected.",
        "sh_title": "Keyboard shortcuts",
        "sh_text": ("1–9 (or B / S) — set the selected box's class\n"
                    "Delete / Backspace — delete the selected box\n"
                    "Arrow keys — nudge the selected box (Shift = 10 px)\n"
                    "Alt + arrows — resize the selected box (Shift = 10 px)\n"
                    "Ctrl+C / Ctrl+V — copy / paste a box (also across pages)\n"
                    "Ctrl+D — duplicate the selected box\n"
                    "Ctrl+click (or the Boxes list) — select several boxes; "
                    "delete/relabel act on all\n"
                    "F — fit the selected box tightly onto the bubble\n"
                    "Z — zoom the view onto the selection\n"
                    "Esc — deselect\n"
                    "[  /  ]  — previous / next page\n"
                    "Ctrl+Z — undo     Ctrl+Y or Ctrl+Shift+Z — redo\n"
                    "Ctrl+W — close the current page\n"
                    "Mouse wheel — zoom     middle-drag — pan\n"
                    "F1 — show this help"),
        "sh_extra": ("1–9 (or B / S) — set the selected box's class\n"
                     "Arrow keys — nudge the selected box (Shift = 10 px)\n"
                     "Alt + arrows — resize the selected box (Shift = 10 px)\n"
                     "Ctrl+click (or the Boxes list) — select several boxes\n"
                     "Mouse wheel — zoom     middle-drag — pan"),
        "sh_customize_hint": "Customize any of these in "
                             "Settings → Shortcuts.",
        "boxes": "Boxes",
        "boxes_tip": "All boxes on this page — click to select, "
                     "drag to reorder (sets the reading order).",
        "strip_tip": "Page thumbnails — click to jump. ✓ = exported to the "
                     "dataset, • = has boxes but not exported yet.",
        "prog": "{done} / {total} pages labelled",
        "fit_box": "Fit box to bubble",
        "fit_done": "Box fitted to the bubble.",
        "fit_fail": "Couldn't detect a bubble to fit — leave the box as is.",
        "rank_load": "🎯 Rank & load…",
        "rank_load_tip": "Rank a folder of pages with the BubblR AI tool (if "
                         "installed), then load the top pages to label first.",
        "rank_pick": "Choose a folder of pages to rank",
        "rank_no_ai_title": "BubblR AI not found",
        "rank_no_ai": "This needs the BubblR AI tool (its 'propose.py'). "
                      "Locate the AI folder now?",
        "rank_pick_ai": "Select the BubblR AI folder (contains propose.py)",
        "rank_no_venv": "The AI folder has no .venv — set it up first "
                        "(setup.ps1 -Training in the AI tool).",
        "rank_top_title": "Rank pages",
        "rank_top_q": "How many top pages to load?",
        "rank_running": "Ranking… (loads the model first, can take a while)",
        "rank_fail": "Ranking failed.",
        "rank_need_model_title": "No ranking model",
        "rank_need_model": "No AI model is set for ranking. Download the shared "
                           "model now? (Or pick one under Settings → Experimental.)",
        "rank_empty": "No ranked pages were produced.",
        "rank_loaded": "Loaded the top {n} ranked page(s).",
        "m_file": "File", "m_edit": "Edit", "m_page": "Page",
        "m_tools": "Tools", "mi_train_model": "Train a model…",
        "mi_get_model": "Download latest AI model",
        "mi_ai_detect": "AI-detect boxes on this page",
        "ai_downloading": "Downloading the latest AI model…",
        "model_update_btn": "⬆ Get new AI model (v{v})",
        "ai_model_ready": "AI model downloaded — use 'AI-detect boxes on this page'.",
        "ai_model_none": "No model available yet (none published, or offline).",
        "ai_need_model": "No AI model downloaded yet. Download the latest one now?",
        "ai_no_env": "No Python with Ultralytics found. Open Settings → "
                     "Experimental and use Find / Get Python next to 'AI Python'.",
        "ai_detecting": "Detecting boxes with the AI…",
        "ai_detect_fail": "AI detection failed.",
        "ai_detect_none": "The AI found nothing on this page.",
        "ai_detect_done": "AI added {n} box(es) — check and fix them.",
        # -- failure details + AI self-check --
        "ai_fail_title": "AI run failed",
        "ai_fail_intro": "The AI process stopped with an error.",
        "ai_fail_details": "Details",
        "ai_fail_check": "Check AI setup…",
        "ai_fail_nolog": "(the process produced no output)",
        "aicheck_title": "AI setup",
        "aicheck_run": "Checking the AI environment…",
        "aicheck_python": "AI Python",
        "aicheck_model": "AI model",
        "aicheck_gpu": "GPU (CUDA)",
        "aicheck_none": "not found",
        "aicheck_ok": "Everything is ready — AI detection and ranking will work.",
        "aicheck_bad": "The AI can't run yet:",
        "aicheck_no_python": "No usable Python was found. If Python 3 is "
                             "installed, press 'Install Ultralytics' below — "
                             "otherwise install Python 3 first.",
        "aicheck_model_missing": "not downloaded",
        "aicheck_model_bad": "the file is corrupt — download it again",
        "aicheck_get_model": "Download model",
        "aicheck_get_python": "Get Python",
        "aicheck_vcredist": "Get VC++ Redistributable",
        "aicheck_recheck": "Check again",
        "aicheck_yes": "yes", "aicheck_no": "no",
        "mi_ai_check": "Check AI setup…",
        "train_model_missing": "BubblR Model Trainer was not found next to this "
                               "app. Download it from the project's Releases page "
                               "(BubblR-Model-Trainer) and place it beside "
                               "BubblR Trainer.",
        "m_view": "View", "m_settings": "Settings", "m_help": "Help",
        "mi_language": "Language",
        "mi_load": "Load images…", "mi_load_folder": "Load folder…",
        "mi_rank": "Rank && load… (needs BubblR AI)",
        "no_imgs_folder": "No images in that folder.",
        "mi_open": "Open project…", "mi_save": "Save project…",
        "mi_folder": "Choose dataset folder…",
        "mi_exp_page": "Export this page", "mi_exp_all": "Export all pages",
        "mi_exit": "Exit",
        "mi_undo": "Undo", "mi_redo": "Redo",
        "mi_copy": "Copy box", "mi_paste": "Paste box",
        "mi_dup": "Duplicate box", "mi_del": "Delete box",
        "mi_select_all": "Select all boxes", "mi_deselect": "Deselect",
        "mi_goto_page": "Go to this page",
        "mi_bubble": "Mark as Bubble", "mi_sfx": "Mark as SFX",
        "mi_clear_order": "Clear reading order",
        "mi_prev": "Previous page", "mi_next": "Next page",
        "mi_next_todo": "Next unlabelled",
        "mi_next_unexported": "Next unexported",
        "mi_close": "Close page", "mi_close_all": "Close all pages",
        "mi_zoom_in": "Zoom in", "mi_zoom_out": "Zoom out",
        "mi_zoom_sel": "Zoom to selection", "mi_fit": "Fit to window",
        "mi_shortcuts": "Keyboard shortcuts…", "mi_about": "About…",
        "mi_train_help": "Model training guide…",
        "train_help_title": "How model training works",
        "train_help_html": (
            "<div style='color:#dfe3e7;font-size:13px;line-height:1.5'>"
            "<h2 style='color:#3daee9'>Train your own AI model</h2>"
            "<p>BubblR Trainer makes the <b>dataset</b>; the companion "
            "<b>BubblR Model Trainer</b> turns it into a trained <b>YOLO</b> "
            "model. The whole loop is: <b>label → export → train → best.pt</b>.</p>"
            "<h3 style='color:#3daee9'>What you need</h3>"
            "<ul>"
            "<li><b>A labelled dataset</b> — draw boxes on your pages here, then "
            "<i>File → Export all</i>. That writes <code>images/</code>, "
            "<code>labels/</code> and a <code>data.yaml</code>.</li>"
            "<li><b>Python with Ultralytics</b> — the Model Trainer has a "
            "<i>Check</i> button and an <i>Install Ultralytics</i> button (needs "
            "internet; it downloads PyTorch, which is large).</li>"
            "<li><b>A GPU is optional</b> — an NVIDIA GPU (CUDA) trains much "
            "faster, but a CPU also works, just slower.</li>"
            "<li><b>Enough examples</b> — aim for dozens of boxes per class; more "
            "and more varied images give a better model.</li>"
            "</ul>"
            "<h3 style='color:#3daee9'>Step by step</h3>"
            "<ol>"
            "<li>Label your pages and set a class for each box (keys 1–9).</li>"
            "<li><i>File → Export all</i> → note the folder with "
            "<code>data.yaml</code>.</li>"
            "<li>Open the Model Trainer (enable it under <i>Settings → "
            "Experimental</i>, then <i>Tools → Train a model…</i>).</li>"
            "<li>Set the <b>Python environment</b> (Check / Install Ultralytics).</li>"
            "<li>Pick your <b>data.yaml</b>, the <b>task</b> (detect or segment) "
            "and a <b>base model</b> (YOLO11/YOLOv8 n→x). To improve an existing "
            "model, choose <i>Custom model file…</i> and select its "
            "<code>.pt</code>.</li>"
            "<li>Set <b>epochs</b> (e.g. 100), <b>image size</b> (e.g. 640), "
            "<b>batch</b> (-1 = auto), <b>device</b> and a run name.</li>"
            "<li>Press <b>Start training</b> and watch the log/progress.</li>"
            "</ol>"
            "<h3 style='color:#3daee9'>Where your model ends up</h3>"
            "<p>Next to your <code>data.yaml</code>: "
            "<code>runs/&lt;run name&gt;/weights/best.pt</code> is your trained "
            "model (<i>best.pt</i> = best epoch). The <b>Open results</b> button "
            "opens that folder. Use it anywhere Ultralytics runs, e.g. "
            "<code>YOLO(\"best.pt\").predict(\"image.png\")</code>.</p>"
            "<h3 style='color:#3daee9'>Tips</h3>"
            "<ul>"
            "<li><b>Background images</b> (empty pages, <i>Settings → Storage</i>) "
            "reduce false detections.</li>"
            "<li>Keep classes <b>balanced</b> — the export summary warns if one "
            "class has far fewer examples.</li>"
            "<li>Starting from a <b>pretrained</b> base (the default) needs far "
            "fewer images than training from scratch.</li>"
            "<li>For <b>segmentation</b>, use the Polygon/Lasso tools and turn on "
            "<i>Export segmentation labels</i>.</li>"
            "</ul></div>"),
        "about_text": "Make YOLO training pages for BubblR — no Krita or "
                      "Photoshop needed.",
        "copied": "Box copied.",
        "pasted": "Box pasted.",
        "duplicated": "Box duplicated.",
        "rec_title": "Recover session?",
        "rec_msg": "The trainer didn't close normally last time. Restore your "
                   "unsaved session ({n} page(s))?",
        "rec_done": "Recovered {n} page(s).",
        "save": "Save project…", "load_proj": "Load project…",
        "folder_none": "Dataset folder: (none chosen)",
        "folder": "Dataset folder: {path}", "choose": "Choose folder…",
        "settings_display": "Display", "settings_tools": "Tools",
        "settings_newbox": "New boxes", "settings_storage": "Storage location",
        "settings_discord": "Discord",
        "start_sub": "Load manga pages, box every bubble and SFX, then export "
                     "the training data. No AI here. Tip: drag images or a "
                     "folder anywhere onto the window.",
        "start_load": "Load images…", "start_folder": "Load folder…",
        "start_open": "Open project…", "start_rank": "Rank && load…",
        "start_heading": "Start", "start_clear": "Clear",
        "start_recent": "Recent images", "start_news": "News",
        "news_loading": "Loading news…", "news_offline": "News unavailable (offline).",
        "news_none": "No news yet.",
        "news_update": "Update available: v{v}",
        "news_download": "Download",
        "settings_news": "Show news & check for updates",
        "settings_news_hint": "Fetches a small news file from the project's "
                              "GitHub on start (over HTTPS, no personal data "
                              "sent) and tells you when a newer version exists.",
        "settings_autoupd": "Download updates automatically",
        "settings_autoupd_hint": "When a newer version is found, download it in "
                                 "the background and offer a one-click install "
                                 "(Windows .exe only).",
        "settings_updates": "Updates",
        "settings_experimental": "Experimental",
        "settings_shortcuts": "Shortcuts",
        "sc_intro": "Click a field and press the key combo you want. Leave it "
                    "empty to unbind. Reset restores the default. A red border "
                    "means two actions share the same key.",
        "sc_reset": "Reset",
        "sc_reset_all": "Reset all to defaults",
        "sc_grp_sel": "Selection tools",
        "sc_grp_ord": "Reading order",
        "sc_grp_file": "File",
        "sc_grp_edit": "Edit",
        "sc_grp_page": "Pages",
        "sc_grp_view": "View",
        "sc_grp_help": "Help",
        "sc_tool_rect": "Rectangle tool",
        "sc_tool_ellipse": "Ellipse tool",
        "sc_tool_poly": "Polygon tool",
        "sc_tool_lasso": "Lasso tool",
        "sc_tool_wand": "Magic-wand tool",
        "exp_intro": "Opt-in switches for features that are still in testing. "
                     "They stay hidden until you turn them on here.",
        "exp_trainer_toggle": "Enable BubblR Model Trainer",
        "exp_trainer_hint": "Adds a Tools → Train a model… entry that opens the "
                            "companion training app. Off by default while the "
                            "Model Trainer is experimental.",
        "exp_ai_title": "AI model (ranking & detection)",
        "exp_rank_model": "Ranking model:",
        "exp_rank_download": "Download",
        "exp_rank_hint": "The .pt used to rank pages (File → Rank && load) and to "
                         "AI-detect boxes. Leave empty to use the downloaded "
                         "shared model. Pick your own to use this for other kinds "
                         "of images.",
        "exp_ai_python": "AI Python:",
        "exp_ai_python_ph": "empty = find it automatically",
        "exp_ai_python_hint": "The python.exe used for AI ranking, detection AND "
                              "training. Leave empty to auto-detect. Setting it "
                              "up: Get Python (if you have none) → Find → "
                              "Install Ultralytics. That last button installs "
                              "Ultralytics and PyTorch into this Python; it's a "
                              "big download and takes a few minutes.",
        "browse": "Browse…",
        "py_find": "Find",
        "py_finding": "Searching…",
        "py_get": "Get Python",
        "py_found_ultra": "Found a ready Python (has Ultralytics):\n{p}",
        "py_found_no_ultra": "Found Python:\n{p}\n\nIt still needs Ultralytics — "
                             "click 'Install Ultralytics' right next to this "
                             "button.",
        "py_none": "No Python found. Click 'Get Python' to install it from "
                   "python.org (tick 'Add to PATH'), then press Find again.",
        # -- Install Ultralytics, straight from Settings --
        "py_install": "Install Ultralytics",
        "py_install_title": "Install Ultralytics",
        "py_install_ask": "Install Ultralytics (and PyTorch) into:\n{p}\n\n"
                          "That's a big download and can take several minutes. "
                          "Continue?",
        "py_install_running": "Installing Ultralytics… this can take several "
                              "minutes.",
        "py_install_busy": "Installing…",
        "py_install_done": "Ultralytics is installed — the AI is ready.",
        "py_install_fail": "The installation failed.",
        "py_install_none": "No Python found to install into. Click 'Get Python', "
                           "install Python 3, then press Find.",
        "py_install_close": "Close",
        # -- Settings → Storage: where to look for already-labelled pages --
        "lbl_src_title": "Where to look for pages you already labelled",
        "lbl_src_hint": "When you rank a folder of raw pages, BubblR skips the "
                        "ones you have labelled before, so you never do the same "
                        "page twice. It always checks your dataset folder. Add "
                        "more folders here — an older dataset, or a helper's "
                        "export. Pages are matched by how they look, so a "
                        "re-saved JPG/PNG is still recognised.",
        "lbl_src_dataset": "Dataset folder (always checked): {p}",
        "lbl_src_dataset_none": "Dataset folder (always checked): none chosen yet",
        "lbl_src_add": "Add folder…",
        "lbl_src_remove": "Remove selected",
        "lbl_src_pick": "Choose a folder with pages you already labelled",
        "lbl_src_none": "No extra folders — only the dataset folder is checked.",
        "lbl_src_dupe": "That folder is already in the list.",
        # -- Train your own model (in-app) --
        "mi_train_own": "Train your own model…",
        "train_own_title": "Train your own model",
        "train_own_intro": "This teaches a model on the pages you labelled. It "
                           "runs on your PC and can take a while — minutes on a "
                           "GPU, longer on the CPU. You can keep working while "
                           "it runs.",
        "train_own_name": "Model name:",
        "train_own_name_hint": "The name of your model, e.g. 'my-bubbles-v1'. "
                               "It becomes the folder name of the result, so "
                               "give each attempt its own name to keep the old "
                               "one.",
        "train_own_out": "Save to:",
        "train_own_out_hint": "The folder your trained model is written to. You "
                              "get <folder>/<name>/weights/best.pt — that file "
                              "IS your model.",
        "train_own_data": "Learn from:",
        "train_own_data_hint": "The labelled pages it learns from — your "
                               "exported dataset. Export first (File → Export "
                               "all), otherwise there is nothing to learn.",
        "train_own_base": "Start from:",
        "train_own_base_hint": "What to build on. 'Shared BubblR model' keeps "
                               "what BubblR already knows and just adds your "
                               "pages — usually the best choice. A plain YOLO "
                               "base starts from scratch and needs many more "
                               "pages. Or continue from a model of your own.",
        "train_own_base_shared": "Shared BubblR model (recommended)",
        "train_own_base_yolo": "YOLO11 nano (small & fast, from scratch)",
        "train_own_base_yolos": "YOLO11 small (slower, a bit better)",
        "train_own_base_custom": "Continue from my own model file…",
        "train_own_epochs": "Rounds (epochs):",
        "train_own_epochs_hint": "How often it goes through all your pages. More "
                                 "rounds = better, up to a point, and slower. "
                                 "100 is a good start.",
        "train_own_imgsz": "Image size:",
        "train_own_imgsz_hint": "How large pages are scaled before learning. "
                                "Bigger catches small text but needs more "
                                "memory. Lower this to 512 if you run out of "
                                "memory.",
        "train_own_start": "Start training",
        "train_own_stop": "Stop",
        "train_own_running": "Training… round {c} of {t}",
        "train_own_starting": "Starting — loading the model…",
        "train_own_done": "Done. Your model: {p}",
        "train_own_fail": "Training failed.",
        "train_own_stopped": "Training stopped.",
        "train_own_use": "Use this model for AI-detect",
        "train_own_using": "AI-detect now uses your model.",
        "train_own_need_data": "No labelled pages found. Choose a dataset folder "
                               "in Settings → Storage and export your pages "
                               "first (File → Export all).",
        "train_own_need_py": "The AI isn't set up yet. Settings → Experimental → "
                             "Install Ultralytics, then try again.",
        "train_own_pick_base": "Choose a model file to continue from",
        "train_own_pick_out": "Where should the trained model be saved?",
        "train_own_close": "Close",
        "train_own_busy": "Training is already running.",
        # -- compare the result against an older model --
        "train_own_cmp": "Compare with:",
        "train_own_cmp_hint": "When training is done, the old model and your new "
                              "one are scored on the same pages, so you can see "
                              "whether it actually got better instead of "
                              "guessing. Costs an extra minute at the end.",
        "train_own_cmp_start": "The model I started from (recommended)",
        "train_own_cmp_shared": "The shared BubblR model",
        "train_own_cmp_pick": "Choose a model file…",
        "train_own_cmp_none": "Don't compare (finishes sooner)",
        "train_own_pick_cmp": "Choose the model to compare against",
        "train_own_cmp_running": "Scoring the old model on the same pages…",
        "train_own_cmp_better": "Your model is BETTER: {new} vs {old} ({d}).",
        "train_own_cmp_worse": "Your model is worse: {new} vs {old} ({d}). Keep "
                               "the old one, or label more pages and retry.",
        "train_own_cmp_same": "No real change: {new} vs {old} ({d}).",
        "train_own_cmp_fail": "Could not compare with the old model — your "
                              "trained model is fine, only the comparison "
                              "failed.",
        "train_own_cmp_scale": "(score = mAP50-95, higher is better, 0 to 1)",
        "train_own_cmp_untrained": "Note: a plain YOLO base has never seen your "
                                   "classes, so it scores near 0 and your model "
                                   "wins automatically. Compare against a BubblR "
                                   "model for a meaningful result.",
        "update_mode_auto": "Automatic",
        "update_mode_manual": "Manual",
        "update_mode_hint": "Automatic: a newer version is downloaded in the "
                            "background and installed on the next start. "
                            "Manual: you get an Update button and decide when. "
                            "(Windows .exe only.)",
        "update_btn": "Update",
        "update_contains": "New version: v{v}",
        "update_uptodate": "You're on the latest version.",
        "update_auto_note": "v{v} is downloaded — it installs on next start.",
        "update_pick_label": "Install a specific version:",
        "update_pick_btn": "Install",
        "update_pick_hint": "Pick any released version, e.g. to roll back. In "
                            "Automatic mode a newer version may re-install on the "
                            "next start — switch to Manual to stay on an older one.",
        "update_loading_versions": "Loading versions…",
        "update_no_versions": "No versions found (offline?)",
        "update_current": "Current version: {v}",
        "update_already_on": "You're already on version {v}.",
        "update_downloading": "Downloading update…",
        "update_install": "Install & restart",
        "update_ready_next": "Update v{v} downloaded — installs on next start.",
        "update_install_now": "Install now",
        "update_confirm": "Install version {v} now? BubblR Trainer will close "
                          "and reopen automatically.",
        "update_failed": "Update could not be installed.",
        "update_src_only": "Auto-install works on the Windows .exe build only. "
                           "For the source version, run: git pull",
        # -- updating the source checkout (no .exe) --
        "update_src_title": "Update from source",
        "update_src_ask": "You're running the source version. Fetch the latest "
                          "code with git now?",
        "update_src_pulling": "Updating the source…",
        "update_src_done": "Updated. Restart BubblR Trainer to use the new "
                           "version.",
        "update_src_fail": "git could not update this folder.",
        "update_src_nogit": "This copy isn't a git checkout, so it can't update "
                            "itself. Download the latest build from the Releases "
                            "page, or clone the repository with git.",
        "update_src_releases": "Open Releases page",
        "recent_missing": "That image no longer exists.",
        "mi_discord": "Show on Discord",
        "discord_need_id": "Set your Discord Application ID in Settings → Discord.",
        "discord_enable": "Show “in BubblR Trainer” on Discord",
        "discord_id": "Discord Application ID (optional)",
        "discord_hint": "Leave empty to use the built-in “BubblR Trainer” app — "
                        "then it just works (Discord must be running on the same "
                        "PC). Only fill this in to use your OWN Discord "
                        "application: create one at "
                        "discord.com/developers/applications and paste its "
                        "Application ID. (An Application ID is public, not a "
                        "secret.)",
        "settings_newbox_hint": "The class a freshly drawn box gets. You can "
                                "still change any box later with the right-click "
                                "menu or the B / S keys.",
        "settings_folder_title": "Dataset / export folder",
        "val_split": "Validation split:",
        "export_summary_toggle": "Show the summary dialog after Export all",
        "export_bg_toggle": "Export empty pages as background images",
        "export_bg_hint": "Pages with no boxes are exported with an empty label "
                          "file (YOLO negatives). Training on background images "
                          "reduces false detections.",
        "seg_export_toggle": "Export segmentation labels (YOLO-seg)",
        "seg_export_hint": "Write polygon outlines instead of boxes, so you can "
                           "train instance segmentation (task=segment). Polygon "
                           "and lasso shapes use their outline; other shapes use "
                           "the box (ellipses approximated).",
        "coco_export_toggle": "Also write COCO JSON",
        "coco_export_hint": "Additionally save annotations in COCO format "
                            "(annotations.coco.json) next to the YOLO files — for "
                            "Detectron2, MMDetection and other frameworks. Each "
                            "object gets a bbox and a polygon.",
        "val_split_hint": "Put this share of pages into images/val + labels/val "
                          "instead of train (0 = all to train). The split is "
                          "stable per page, and data.yaml points val there.",
        "settings_folder_none": "(no folder chosen yet)",
        "settings_open": "Settings…",
        "settings_layout": "Panels & layout",
        "settings_unlock": "Unlock panels (allow moving & docking)",
        "settings_unlock_hint": "When on, drag a panel by its title bar to move, "
                                "dock or float it. Turn off to lock the layout.",
        "dock_tools": "Tools", "dock_boxes": "Boxes", "dock_pages": "Pages",
        "bar_actions": "Actions",
        "mi_dockers": "Dockers", "mi_lock_panels": "Lock panels",
        "export_page": "Export this page", "export_all": "Export all pages",
        "ready": "Load page images to begin.",
        "loaded": "{n} image(s) loaded.",
        "no_page": "Load a page first.", "no_boxes": "Draw at least one box first.",
        "no_folder": "Choose a dataset folder first.",
        "order_hint": "Click the bubbles in reading order (1, 2, 3 …).",
        "order_cleared": "Reading order cleared.",
        "exported_one": "Exported: {name}",
        "exported_all": "Exported {n} page(s) to the dataset folder.",
        "summary_title": "Export summary",
        "summary_pages": "Exported {n} page(s)  —  {tr} train, {va} val.",
        "summary_bg": "Of these, {n} background image(s) (no objects).",
        "summary_objects": "Objects per class:",
        "summary_total": "Total: {n} box(es).",
        "summary_empty_cls": "⚠ No examples for: {cls}. That class won't be "
                             "learned until you label some.",
        "summary_imbalance": "⚠ Classes are imbalanced (10×+). Consider adding "
                             "examples for the rarer ones.",
        "export_fail": "Export failed: {msg}",
        "saved": "Project saved.", "loaded_proj": "Project loaded ({n} page(s)).",
        "load_fail": "Could not load: {msg}",
        "img_filter": "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        "proj_filter": "BubblR project (*.json)",
        "lang": "Language",
    },
    "de": {
        "title": "BubblR Trainer",
        "intro": ("Seitenbilder laden, um jede Bubble und jeden SFX eine Box "
                  "ziehen, labeln, optional die Lesereihenfolge festlegen, dann "
                  "exportieren. Hier läuft keine KI – das erzeugt nur die "
                  "Trainingsdaten.  F1 zeigt die Tastenkürzel."),
        "load": "Bilder laden…",
        "prev": "◀", "next": "▶",
        "fit": "Einpassen",
        "zoom_tip": "Rad = Zoom · Mittel-Ziehen = Verschieben · Knopf = einpassen",
        "page_none": "keine Seite", "page": "{i} / {n}  -  {name}",
        "edit": "Boxen zeichnen / bearbeiten", "set_order": "Lesereihenfolge festlegen",
        "auto_order": "Auto-Reihenfolge",
        "auto_order_tip": "Alle Bubbles automatisch nach Lesereihenfolge nummerieren (danach nur korrigieren)",
        "rtl": "R→L (Manga)",
        "rtl_tip": "Manga liest rechts-nach-links; für links-nach-rechts abwählen",
        "ranked": "{n} Box(en) automatisch geordnet – bei Bedarf anpassen.",
        "delete": "Ausgewählte löschen", "clear_order": "Reihenfolge löschen",
        "clear": "Seite leeren",
        "kind": "Neue Box ist:", "bubble": "Bubble", "sfx": "SFX",
        "relabel": "(erst eine Box anklicken, um sie umzulabeln)",
        "counts_this_page": "Diese Seite",
        "counts_pages": "Seiten: {done}/{p} gelabelt, {exp} exportiert",
        "sort_by": "Seiten sortieren:",
        "sort_name": "nach Name",
        "sort_unlabeled": "ungelabelte zuerst",
        "sort_unexported": "nicht exportierte zuerst",
        "show": "Zeigen:", "show_all": "Alle", "show_only": "Nur {name}",
        "show_bubble": "Nur Bubbles", "show_sfx": "Nur SFX",
        "mi_set_class": "Klasse setzen", "settings_classes": "Klassen",
        "class_add": "Hinzufügen…", "class_rename": "Umbenennen…",
        "class_color": "Farbe…", "class_remove": "Entfernen",
        "class_reset": "Auf Manga zurücksetzen", "class_name": "Klassenname:",
        "class_import": "Importieren…",
        "class_import_fail": "Keine Klassennamen in der Datei gefunden.",
        "class_imported": "{n} Klasse(n) importiert.",
        "settings_classes_hint": "Definiere die Objektklassen für deinen "
                                "Datensatz — die YOLO-Klassennummer jeder Box ist "
                                "ihre Position hier (0, 1, 2 …). Standard (Manga) "
                                "ist Bubble / SFX; füge eigene hinzu, um BELIEBIGE "
                                "Objektdetektoren zu trainieren (Gesichter, Autos, "
                                "Defekte …). Tasten 1–9 (und B / S) setzen die "
                                "Klasse der Auswahl schnell.",
        "auto_order_live": "Auto-Reihenfolge",
        "auto_order_live_tip": "Die Lesereihenfolge nach jedem Hinzufügen / "
                               "Verschieben / Löschen automatisch neu vergeben.",
        "sort_fewest": "wenigste Boxen zuerst",
        "sort_most": "meiste Boxen zuerst",
        "next_todo": "Nächste ungelabelte",
        "all_labelled": "Alle Seiten haben mindestens eine Box.",
        "all_exported": "Alle gelabelten Seiten sind exportiert.",
        "tool": "Werkzeug:",
        "tool_rect": "▭ Rechteck",
        "tool_ellipse": "◯ Ellipse",
        "tool_poly": "⬠ Polygon",
        "tool_lasso": "✎ Lasso",
        "tool_wand": "✨ Zauberstab",
        "tool_rect_hint": "Rechteck von Ecke zu Ecke ziehen.",
        "tool_ellipse_hint": "Ellipse ziehen; die Box ist ihr umschließendes Rechteck.",
        "tool_poly_hint": "Polygon: klicken, um Punkte zu setzen; ersten Punkt "
                          "anklicken, Doppelklick oder Enter zum Schließen. "
                          "Rücktaste nimmt einen Punkt zurück, Esc bricht ab.",
        "tool_lasso_hint": "Freihand-Umriss zeichnen; die Box umschließt ihn.",
        "tool_wand_hint": "In eine Blase klicken, um ihren Bereich automatisch zu erkennen.",
        "wand_tol": "Zauberst.-Tol.",
        "wand_tol_tip": "Farbtoleranz des Zauberstabs (höher = erfasst mehr).",
        "center_marker": "Mittelpunkt",
        "center_marker_tip": "Kreuz + Punkt in der Mitte jeder Markierung anzeigen.",
        "order_path": "Lesepfad",
        "order_path_tip": "Den Lesepfad 1->2->3 zwischen den Boxen einzeichnen, "
                          "damit man die Reihenfolge auf einen Blick prüfen (und "
                          "korrigieren) kann.",
        "undo": "↶ Rückgängig",
        "redo": "↷ Wiederh.",
        "undo_tip": "Letzte Änderung rückgängig (Strg+Z)",
        "redo_tip": "Wiederherstellen (Strg+Y oder Umschalt+Strg+Z)",
        "nothing_undo": "Nichts rückgängig zu machen.",
        "nothing_redo": "Nichts wiederherzustellen.",
        "undone": "Rückgängig gemacht.",
        "redone": "Wiederhergestellt.",
        "close_page": "✕ Seite schließen",
        "close_page_tip": "Diese Seite aus der Sitzung entfernen (Strg+W). Die "
                          "Bilddatei auf der Festplatte bleibt unberührt.",
        "close_all": "Alle schließen",
        "close_all_tip": "Alle geladenen Seiten aus der Sitzung entfernen.",
        "confirm_title": "Seite schließen",
        "confirm_close": "„{name}“ hat {n} Box(en), die nicht exportiert sind.\n\n"
                         "Diese Seite schließen und verwerfen?",
        "confirm_close_all": "{p} Seite(n) mit {n} Box(en), die nicht exportiert "
                             "sind.\n\nAlle Seiten schließen und verwerfen?",
        "confirm_quit_title": "BubblR Trainer beenden",
        "confirm_quit_unexported": "{n} Seite(n) haben Boxen, die noch nicht ins "
                                   "Dataset exportiert sind.\n\nTrotzdem beenden? "
                                   "Die nicht exportierten Boxen gehen verloren, "
                                   "wenn du sie nicht vorher exportierst oder ein "
                                   "Projekt speicherst.",
        "closed": "Seite geschlossen.",
        "closed_all": "Alle Seiten geschlossen.",
        "sc_title": "Verknüpfung anlegen?",
        "sc_msg": "BubblR Trainer für schnellen Zugriff verknüpfen?",
        "sc_desktop": "Auf dem Desktop",
        "sc_startmenu": "Im Startmenü",
        "sc_create": "Anlegen",
        "sc_skip": "Nicht jetzt",
        "sc_done": "Verknüpfung angelegt.",
        "sc_none": "Kein Ort ausgewählt.",
        "sh_title": "Tastenkürzel",
        "sh_text": ("1–9 (oder B / S) — Klasse der ausgewählten Box setzen\n"
                    "Entf / Rücktaste — ausgewählte Box löschen\n"
                    "Pfeiltasten — ausgewählte Box verschieben (Umschalt = 10 px)\n"
                    "Alt + Pfeile — ausgewählte Box vergrößern/verkleinern (Umschalt = 10 px)\n"
                    "Strg+C / Strg+V — Box kopieren / einfügen (auch seitenübergr.)\n"
                    "Strg+D — ausgewählte Box duplizieren\n"
                    "Strg+Klick (oder Boxen-Liste) — mehrere Boxen wählen; "
                    "Löschen/Umlabeln gilt für alle\n"
                    "F — ausgewählte Box eng an die Blase anpassen\n"
                    "Z — Ansicht auf die Auswahl zoomen\n"
                    "Esc — Auswahl aufheben\n"
                    "[  /  ]  — vorige / nächste Seite\n"
                    "Strg+Z — rückgängig     Strg+Y oder Umschalt+Strg+Z — wiederh.\n"
                    "Strg+W — aktuelle Seite schließen\n"
                    "Mausrad — Zoom     Mittel-Ziehen — verschieben\n"
                    "F1 — diese Hilfe anzeigen"),
        "sh_extra": ("1–9 (oder B / S) — Klasse der ausgewählten Box setzen\n"
                     "Pfeiltasten — Box verschieben (Umschalt = 10 px)\n"
                     "Alt + Pfeile — Box skalieren (Umschalt = 10 px)\n"
                     "Strg+Klick (oder Boxen-Liste) — mehrere Boxen wählen\n"
                     "Mausrad — Zoom     Mittel-Ziehen — verschieben"),
        "sh_customize_hint": "Alle hier unter "
                             "Einstellungen → Tastenkürzel anpassbar.",
        "boxes": "Boxen",
        "boxes_tip": "Alle Boxen dieser Seite — anklicken zum Auswählen, "
                     "ziehen zum Umsortieren (setzt die Lesereihenfolge).",
        "strip_tip": "Seiten-Miniaturen — anklicken zum Springen. ✓ = ins "
                     "Dataset exportiert, • = hat Boxen, aber noch nicht exportiert.",
        "prog": "{done} / {total} Seiten gelabelt",
        "fit_box": "Box an Blase anpassen",
        "fit_done": "Box an die Blase angepasst.",
        "fit_fail": "Keine Blase zum Anpassen erkannt — Box bleibt unverändert.",
        "rank_load": "🎯 Ranken & laden…",
        "rank_load_tip": "Einen Ordner mit Seiten über das BubblR-AI-Tool ranken "
                         "(falls installiert) und die Top-Seiten zum Labeln laden.",
        "rank_pick": "Ordner mit Seiten zum Ranken wählen",
        "rank_no_ai_title": "BubblR AI nicht gefunden",
        "rank_no_ai": "Dafür wird das BubblR-AI-Tool gebraucht (dessen "
                      "'propose.py'). Den AI-Ordner jetzt auswählen?",
        "rank_pick_ai": "BubblR-AI-Ordner wählen (enthält propose.py)",
        "rank_no_venv": "Im AI-Ordner fehlt die .venv — erst einrichten "
                        "(setup.ps1 -Training im AI-Tool).",
        "rank_top_title": "Seiten ranken",
        "rank_top_q": "Wie viele Top-Seiten laden?",
        "rank_running": "Ranking läuft… (lädt zuerst das Modell, dauert etwas)",
        "rank_fail": "Ranking fehlgeschlagen.",
        "rank_need_model_title": "Kein Ranking-Modell",
        "rank_need_model": "Es ist kein KI-Modell fürs Ranking gesetzt. Jetzt das "
                           "geteilte Modell laden? (Oder unter Einstellungen → "
                           "Experimentell eins wählen.)",
        "rank_empty": "Es wurden keine gerankten Seiten erzeugt.",
        "rank_loaded": "Top {n} gerankte Seite(n) geladen.",
        "m_file": "Datei", "m_edit": "Bearbeiten", "m_page": "Seite",
        "m_tools": "Werkzeuge", "mi_train_model": "Modell trainieren…",
        "mi_get_model": "Neuestes KI-Modell laden",
        "mi_ai_detect": "KI-Boxen auf dieser Seite erkennen",
        "ai_downloading": "Neuestes KI-Modell wird geladen…",
        "model_update_btn": "⬆ Neues KI-Modell laden (v{v})",
        "ai_model_ready": "KI-Modell geladen — nutze „KI-Boxen auf dieser Seite "
                          "erkennen“.",
        "ai_model_none": "Noch kein Modell verfügbar (nichts veröffentlicht oder "
                         "offline).",
        "ai_need_model": "Noch kein KI-Modell geladen. Jetzt das neueste laden?",
        "ai_no_env": "Kein Python mit Ultralytics gefunden. Öffne Einstellungen → "
                     "Experimentell und nutze „Finden“ / „Python holen“ neben "
                     "„KI-Python“.",
        "ai_detecting": "KI erkennt Boxen…",
        "ai_detect_fail": "KI-Erkennung fehlgeschlagen.",
        "ai_detect_none": "Die KI hat auf dieser Seite nichts gefunden.",
        "ai_detect_done": "KI hat {n} Box(en) hinzugefügt — prüfen und korrigieren.",
        # -- Fehlerdetails + KI-Selbsttest --
        "ai_fail_title": "KI-Lauf fehlgeschlagen",
        "ai_fail_intro": "Der KI-Prozess wurde mit einem Fehler beendet.",
        "ai_fail_details": "Details",
        "ai_fail_check": "KI-Setup prüfen…",
        "ai_fail_nolog": "(der Prozess hat keine Ausgabe geliefert)",
        "aicheck_title": "KI-Setup",
        "aicheck_run": "KI-Umgebung wird geprüft…",
        "aicheck_python": "KI-Python",
        "aicheck_model": "KI-Modell",
        "aicheck_gpu": "GPU (CUDA)",
        "aicheck_none": "nicht gefunden",
        "aicheck_ok": "Alles bereit — KI-Erkennung und Ranking funktionieren.",
        "aicheck_bad": "Die KI kann noch nicht laufen:",
        "aicheck_no_python": "Kein nutzbares Python gefunden. Falls Python 3 "
                             "installiert ist, klicke unten auf „Ultralytics "
                             "installieren“ — sonst zuerst Python 3 "
                             "installieren.",
        "aicheck_model_missing": "nicht geladen",
        "aicheck_model_bad": "die Datei ist beschädigt — bitte neu laden",
        "aicheck_get_model": "Modell laden",
        "aicheck_get_python": "Python holen",
        "aicheck_vcredist": "VC++-Redistributable holen",
        "aicheck_recheck": "Erneut prüfen",
        "aicheck_yes": "ja", "aicheck_no": "nein",
        "mi_ai_check": "KI-Setup prüfen…",
        "train_model_missing": "BubblR Model Trainer wurde nicht neben dieser App "
                               "gefunden. Lade ihn von der Releases-Seite des "
                               "Projekts (BubblR-Model-Trainer) und lege ihn "
                               "neben BubblR Trainer.",
        "m_view": "Ansicht", "m_settings": "Einstellungen", "m_help": "Hilfe",
        "mi_language": "Sprache",
        "mi_load": "Bilder laden…", "mi_load_folder": "Ordner laden…",
        "mi_rank": "Ranken && laden… (braucht BubblR AI)",
        "no_imgs_folder": "Keine Bilder in dem Ordner.",
        "mi_open": "Projekt öffnen…", "mi_save": "Projekt speichern…",
        "mi_folder": "Dataset-Ordner wählen…",
        "mi_exp_page": "Diese Seite exportieren",
        "mi_exp_all": "Alle Seiten exportieren", "mi_exit": "Beenden",
        "mi_undo": "Rückgängig", "mi_redo": "Wiederherstellen",
        "mi_copy": "Box kopieren", "mi_paste": "Box einfügen",
        "mi_dup": "Box duplizieren", "mi_del": "Box löschen",
        "mi_select_all": "Alle Boxen auswählen", "mi_deselect": "Auswahl aufheben",
        "mi_goto_page": "Zu dieser Seite springen",
        "mi_bubble": "Als Bubble markieren", "mi_sfx": "Als SFX markieren",
        "mi_clear_order": "Lesereihenfolge löschen",
        "mi_prev": "Vorige Seite", "mi_next": "Nächste Seite",
        "mi_next_todo": "Nächste ungelabelte",
        "mi_next_unexported": "Nächste nicht exportierte",
        "mi_close": "Seite schließen", "mi_close_all": "Alle Seiten schließen",
        "mi_zoom_in": "Vergrößern", "mi_zoom_out": "Verkleinern",
        "mi_zoom_sel": "Auf Auswahl zoomen", "mi_fit": "Einpassen",
        "mi_shortcuts": "Tastenkürzel…", "mi_about": "Über…",
        "mi_train_help": "Modell-Training-Anleitung…",
        "train_help_title": "Wie das Modell-Training funktioniert",
        "train_help_html": (
            "<div style='color:#dfe3e7;font-size:13px;line-height:1.5'>"
            "<h2 style='color:#3daee9'>Eigenes KI-Modell trainieren</h2>"
            "<p>BubblR Trainer erstellt den <b>Datensatz</b>; die begleitende "
            "App <b>BubblR Model Trainer</b> macht daraus ein trainiertes "
            "<b>YOLO</b>-Modell. Der Ablauf: <b>labeln → exportieren → "
            "trainieren → best.pt</b>.</p>"
            "<h3 style='color:#3daee9'>Was du brauchst</h3>"
            "<ul>"
            "<li><b>Ein gelabelter Datensatz</b> — hier Boxen auf die Seiten "
            "zeichnen, dann <i>Datei → Export all</i>. Das schreibt "
            "<code>images/</code>, <code>labels/</code> und eine "
            "<code>data.yaml</code>.</li>"
            "<li><b>Python mit Ultralytics</b> — der Model Trainer hat einen "
            "<i>Check</i>-Knopf und einen <i>Install Ultralytics</i>-Knopf "
            "(braucht Internet; lädt PyTorch, was groß ist).</li>"
            "<li><b>GPU optional</b> — eine NVIDIA-GPU (CUDA) trainiert viel "
            "schneller, aber CPU geht auch, nur langsamer.</li>"
            "<li><b>Genug Beispiele</b> — pro Klasse möglichst Dutzende Boxen; "
            "mehr und abwechslungsreichere Bilder = besseres Modell.</li>"
            "</ul>"
            "<h3 style='color:#3daee9'>Schritt für Schritt</h3>"
            "<ol>"
            "<li>Seiten labeln und jeder Box eine Klasse geben (Tasten 1–9).</li>"
            "<li><i>Datei → Export all</i> → den Ordner mit "
            "<code>data.yaml</code> merken.</li>"
            "<li>Model Trainer öffnen (unter <i>Einstellungen → Experimentell</i> "
            "aktivieren, dann <i>Werkzeuge → Modell trainieren…</i>).</li>"
            "<li><b>Python-Umgebung</b> setzen (Check / Install Ultralytics).</li>"
            "<li><b>data.yaml</b> wählen, <b>Aufgabe</b> (detect oder segment) und "
            "ein <b>Basismodell</b> (YOLO11/YOLOv8 n→x). Zum Verbessern eines "
            "bestehenden Modells <i>Custom model file…</i> wählen und dessen "
            "<code>.pt</code> nehmen.</li>"
            "<li><b>Epochen</b> (z. B. 100), <b>Bildgröße</b> (z. B. 640), "
            "<b>Batch</b> (-1 = auto), <b>Gerät</b> und Run-Name setzen.</li>"
            "<li><b>Start training</b> drücken und Log/Fortschritt beobachten.</li>"
            "</ol>"
            "<h3 style='color:#3daee9'>Wo dein Modell landet</h3>"
            "<p>Neben deiner <code>data.yaml</code>: "
            "<code>runs/&lt;Run-Name&gt;/weights/best.pt</code> ist dein "
            "trainiertes Modell (<i>best.pt</i> = beste Epoche). Der Knopf "
            "<b>Open results</b> öffnet den Ordner. Nutzbar überall, wo "
            "Ultralytics läuft, z. B. "
            "<code>YOLO(\"best.pt\").predict(\"bild.png\")</code>.</p>"
            "<h3 style='color:#3daee9'>Tipps</h3>"
            "<ul>"
            "<li><b>Hintergrundbilder</b> (leere Seiten, <i>Einstellungen → "
            "Speicherort</i>) verringern Fehlerkennungen.</li>"
            "<li>Klassen <b>ausgewogen</b> halten — die Export-Zusammenfassung "
            "warnt, wenn eine Klasse viel seltener ist.</li>"
            "<li>Von einem <b>vortrainierten</b> Basismodell (Standard) zu starten "
            "braucht viel weniger Bilder als von null.</li>"
            "<li>Für <b>Segmentierung</b> die Polygon/Lasso-Werkzeuge nutzen und "
            "<i>Segmentierungs-Labels exportieren</i> anschalten.</li>"
            "</ul></div>"),
        "about_text": "Erzeugt YOLO-Trainingsseiten für BubblR — ohne Krita "
                      "oder Photoshop.",
        "copied": "Box kopiert.",
        "pasted": "Box eingefügt.",
        "duplicated": "Box dupliziert.",
        "rec_title": "Sitzung wiederherstellen?",
        "rec_msg": "Der Trainer wurde letztes Mal nicht normal beendet. "
                   "Nicht gespeicherte Sitzung wiederherstellen ({n} Seite(n))?",
        "rec_done": "{n} Seite(n) wiederhergestellt.",
        "save": "Projekt speichern…", "load_proj": "Projekt laden…",
        "folder_none": "Datensatz-Ordner: (keiner gewählt)",
        "folder": "Datensatz-Ordner: {path}", "choose": "Ordner wählen…",
        "settings_display": "Anzeige", "settings_tools": "Werkzeuge",
        "settings_newbox": "Neue Boxen", "settings_storage": "Speicherort",
        "settings_discord": "Discord",
        "start_sub": "Manga-Seiten laden, jede Blase und jeden SFX einrahmen, "
                     "dann die Trainingsdaten exportieren. Keine KI hier. Tipp: "
                     "Bilder oder einen Ordner einfach ins Fenster ziehen.",
        "start_load": "Bilder laden…", "start_folder": "Ordner laden…",
        "start_open": "Projekt öffnen…", "start_rank": "Rank && load…",
        "start_heading": "Start", "start_clear": "Leeren",
        "start_recent": "Zuletzt geöffnet", "start_news": "News",
        "news_loading": "News werden geladen…",
        "news_offline": "News nicht verfügbar (offline).",
        "news_none": "Noch keine News.",
        "news_update": "Update verfügbar: v{v}",
        "news_download": "Herunterladen",
        "settings_news": "News anzeigen & auf Updates prüfen",
        "settings_news_hint": "Lädt beim Start eine kleine News-Datei vom GitHub "
                              "des Projekts (über HTTPS, keine persönlichen Daten) "
                              "und meldet, wenn eine neuere Version verfügbar ist.",
        "settings_autoupd": "Updates automatisch herunterladen",
        "settings_autoupd_hint": "Wenn eine neuere Version gefunden wird, wird "
                                 "sie im Hintergrund geladen und per Klick "
                                 "installiert (nur Windows-.exe).",
        "settings_updates": "Updates",
        "settings_experimental": "Experimentell",
        "settings_shortcuts": "Tastenkürzel",
        "sc_intro": "Feld anklicken und die gewünschte Tastenkombination "
                    "drücken. Leer lassen = kein Kürzel. „Zurücksetzen“ stellt "
                    "die Vorgabe wieder her. Ein roter Rand bedeutet, dass sich "
                    "zwei Aktionen dieselbe Taste teilen.",
        "sc_reset": "Zurücksetzen",
        "sc_reset_all": "Alle auf Vorgabe zurücksetzen",
        "sc_grp_sel": "Auswahlwerkzeuge",
        "sc_grp_ord": "Lesereihenfolge",
        "sc_grp_file": "Datei",
        "sc_grp_edit": "Bearbeiten",
        "sc_grp_page": "Seiten",
        "sc_grp_view": "Ansicht",
        "sc_grp_help": "Hilfe",
        "sc_tool_rect": "Rechteck-Werkzeug",
        "sc_tool_ellipse": "Ellipsen-Werkzeug",
        "sc_tool_poly": "Polygon-Werkzeug",
        "sc_tool_lasso": "Lasso-Werkzeug",
        "sc_tool_wand": "Zauberstab-Werkzeug",
        "exp_intro": "Schalter zum Aktivieren von Funktionen, die noch in der "
                     "Testphase sind. Sie bleiben verborgen, bis du sie hier "
                     "einschaltest.",
        "exp_trainer_toggle": "BubblR Model Trainer aktivieren",
        "exp_trainer_hint": "Fügt einen Eintrag „Werkzeuge → Modell trainieren…“ "
                            "hinzu, der die begleitende Trainings-App öffnet. "
                            "Standardmäßig aus, solange der Model Trainer "
                            "experimentell ist.",
        "exp_ai_title": "KI-Modell (Ranking & Erkennung)",
        "exp_rank_model": "Ranking-Modell:",
        "exp_rank_download": "Laden",
        "exp_rank_hint": "Das .pt zum Ranken der Seiten (Datei → Rank && load) und "
                         "für die KI-Box-Erkennung. Leer lassen = geteiltes "
                         "geladenes Modell. Ein eigenes wählen, um das Programm "
                         "für andere Bildarten zu nutzen.",
        "exp_ai_python": "KI-Python:",
        "exp_ai_python_ph": "leer = automatisch finden",
        "exp_ai_python_hint": "Die python.exe für KI-Ranking, -Erkennung UND "
                              "-Training. Leer lassen = automatisch finden. "
                              "Einrichten: „Python holen“ (falls keins da ist) → "
                              "„Finden“ → „Ultralytics installieren“. Der letzte "
                              "Knopf installiert Ultralytics und PyTorch in "
                              "dieses Python; großer Download, dauert ein paar "
                              "Minuten.",
        "browse": "Durchsuchen…",
        "py_find": "Finden",
        "py_finding": "Suche…",
        "py_get": "Python holen",
        "py_found_ultra": "Fertiges Python gefunden (mit Ultralytics):\n{p}",
        "py_found_no_ultra": "Python gefunden:\n{p}\n\nEs braucht noch "
                             "Ultralytics — klicke direkt daneben auf "
                             "„Ultralytics installieren“.",
        "py_none": "Kein Python gefunden. Klicke „Python holen“, installiere es "
                   "von python.org (Häkchen „Add to PATH“), dann „Finden“.",
        # -- Ultralytics direkt aus den Einstellungen installieren --
        "py_install": "Ultralytics installieren",
        "py_install_title": "Ultralytics installieren",
        "py_install_ask": "Ultralytics (und PyTorch) installieren in:\n{p}\n\n"
                          "Das ist ein großer Download und kann einige Minuten "
                          "dauern. Fortfahren?",
        "py_install_running": "Ultralytics wird installiert… das kann einige "
                              "Minuten dauern.",
        "py_install_busy": "Installiere…",
        "py_install_done": "Ultralytics ist installiert — die KI ist bereit.",
        "py_install_fail": "Die Installation ist fehlgeschlagen.",
        "py_install_none": "Kein Python zum Installieren gefunden. Klicke "
                           "„Python holen“, installiere Python 3, dann „Finden“.",
        "py_install_close": "Schließen",
        # -- Einstellungen → Speicherort: wo nach gelabelten Seiten gesucht wird --
        "lbl_src_title": "Wo nach schon gelabelten Seiten gesucht wird",
        "lbl_src_hint": "Beim Ranken eines Ordners mit Rohseiten überspringt "
                        "BubblR die Seiten, die du schon gelabelt hast — so "
                        "machst du keine Seite doppelt. Dein Dataset-Ordner wird "
                        "immer geprüft. Hier kannst du weitere Ordner "
                        "hinzufügen: einen älteren Datensatz oder den Export "
                        "eines Helfers. Erkannt wird am Aussehen der Seite, ein "
                        "neu gespeichertes JPG/PNG wird also trotzdem gefunden.",
        "lbl_src_dataset": "Dataset-Ordner (immer geprüft): {p}",
        "lbl_src_dataset_none": "Dataset-Ordner (immer geprüft): noch keiner "
                                "gewählt",
        "lbl_src_add": "Ordner hinzufügen…",
        "lbl_src_remove": "Ausgewählten entfernen",
        "lbl_src_pick": "Ordner mit schon gelabelten Seiten wählen",
        "lbl_src_none": "Keine zusätzlichen Ordner — nur der Dataset-Ordner wird "
                        "geprüft.",
        "lbl_src_dupe": "Dieser Ordner steht bereits in der Liste.",
        # -- Eigenes Modell trainieren (in der App) --
        "mi_train_own": "Eigenes Modell trainieren…",
        "train_own_title": "Eigenes Modell trainieren",
        "train_own_intro": "Das bringt einem Modell deine gelabelten Seiten bei. "
                           "Es läuft auf deinem PC und dauert etwas — Minuten "
                           "auf einer GPU, länger auf der CPU. Du kannst "
                           "nebenher weiterarbeiten.",
        "train_own_name": "Modellname:",
        "train_own_name_hint": "Der Name deines Modells, z. B. „meine-bubbles-v1“. "
                               "Er wird zum Ordnernamen des Ergebnisses — gib "
                               "jedem Versuch einen eigenen Namen, dann bleibt "
                               "der alte erhalten.",
        "train_own_out": "Speichern in:",
        "train_own_out_hint": "Der Ordner, in den dein trainiertes Modell "
                              "geschrieben wird. Du bekommst "
                              "<Ordner>/<Name>/weights/best.pt — diese Datei IST "
                              "dein Modell.",
        "train_own_data": "Lernt aus:",
        "train_own_data_hint": "Die gelabelten Seiten, aus denen gelernt wird — "
                               "dein exportierter Datensatz. Exportiere zuerst "
                               "(Datei → Alle exportieren), sonst gibt es nichts "
                               "zu lernen.",
        "train_own_base": "Startet von:",
        "train_own_base_hint": "Worauf aufgebaut wird. „Geteiltes BubblR-Modell“ "
                               "behält, was BubblR schon kann, und ergänzt nur "
                               "deine Seiten — meist die beste Wahl. Eine reine "
                               "YOLO-Basis fängt bei null an und braucht viel "
                               "mehr Seiten. Oder mach mit einem eigenen Modell "
                               "weiter.",
        "train_own_base_shared": "Geteiltes BubblR-Modell (empfohlen)",
        "train_own_base_yolo": "YOLO11 nano (klein & schnell, von null)",
        "train_own_base_yolos": "YOLO11 small (langsamer, etwas besser)",
        "train_own_base_custom": "Mit eigenem Modell weitermachen…",
        "train_own_epochs": "Durchgänge (Epochen):",
        "train_own_epochs_hint": "Wie oft alle deine Seiten durchlaufen werden. "
                                 "Mehr Durchgänge = besser, bis zu einem Punkt, "
                                 "und langsamer. 100 ist ein guter Start.",
        "train_own_imgsz": "Bildgröße:",
        "train_own_imgsz_hint": "Auf welche Größe die Seiten vor dem Lernen "
                                "skaliert werden. Größer erkennt kleine Schrift "
                                "besser, braucht aber mehr Speicher. Bei "
                                "Speicherproblemen auf 512 senken.",
        "train_own_start": "Training starten",
        "train_own_stop": "Stopp",
        "train_own_running": "Training… Durchgang {c} von {t}",
        "train_own_starting": "Start — Modell wird geladen…",
        "train_own_done": "Fertig. Dein Modell: {p}",
        "train_own_fail": "Training fehlgeschlagen.",
        "train_own_stopped": "Training abgebrochen.",
        "train_own_use": "Dieses Modell für KI-Erkennung nutzen",
        "train_own_using": "Die KI-Erkennung nutzt jetzt dein Modell.",
        "train_own_need_data": "Keine gelabelten Seiten gefunden. Wähle unter "
                               "Einstellungen → Speicherort einen Dataset-Ordner "
                               "und exportiere zuerst deine Seiten (Datei → Alle "
                               "exportieren).",
        "train_own_need_py": "Die KI ist noch nicht eingerichtet. Einstellungen → "
                             "Experimentell → „Ultralytics installieren“, dann "
                             "erneut versuchen.",
        "train_own_pick_base": "Modelldatei wählen, mit der weitergemacht wird",
        "train_own_pick_out": "Wohin soll das trainierte Modell gespeichert "
                              "werden?",
        "train_own_close": "Schließen",
        "train_own_busy": "Es läuft bereits ein Training.",
        # -- Ergebnis mit einem älteren Modell vergleichen --
        "train_own_cmp": "Vergleichen mit:",
        "train_own_cmp_hint": "Nach dem Training werden das alte und dein neues "
                              "Modell auf denselben Seiten bewertet — so siehst "
                              "du, ob es wirklich besser geworden ist, statt zu "
                              "raten. Kostet am Ende eine Minute extra.",
        "train_own_cmp_start": "Dem Modell, von dem ich gestartet bin (empfohlen)",
        "train_own_cmp_shared": "Dem geteilten BubblR-Modell",
        "train_own_cmp_pick": "Modelldatei wählen…",
        "train_own_cmp_none": "Nicht vergleichen (ist schneller fertig)",
        "train_own_pick_cmp": "Modell wählen, mit dem verglichen wird",
        "train_own_cmp_running": "Altes Modell wird auf denselben Seiten "
                                 "bewertet…",
        "train_own_cmp_better": "Dein Modell ist BESSER: {new} statt {old} ({d}).",
        "train_own_cmp_worse": "Dein Modell ist schlechter: {new} statt {old} "
                               "({d}). Behalte das alte, oder labele mehr Seiten "
                               "und versuch es erneut.",
        "train_own_cmp_same": "Kein echter Unterschied: {new} statt {old} ({d}).",
        "train_own_cmp_fail": "Vergleich mit dem alten Modell nicht möglich — "
                              "dein trainiertes Modell ist in Ordnung, nur der "
                              "Vergleich ist fehlgeschlagen.",
        "train_own_cmp_scale": "(Wert = mAP50-95, höher ist besser, 0 bis 1)",
        "train_own_cmp_untrained": "Hinweis: Eine reine YOLO-Basis kennt deine "
                                   "Klassen nicht, erreicht also fast 0 — dein "
                                   "Modell gewinnt automatisch. Für ein "
                                   "aussagekräftiges Ergebnis mit einem "
                                   "BubblR-Modell vergleichen.",
        "update_mode_auto": "Automatisch",
        "update_mode_manual": "Manuell",
        "update_mode_hint": "Automatisch: eine neuere Version wird im Hintergrund "
                            "geladen und beim nächsten Start installiert. "
                            "Manuell: du bekommst einen Update-Button und "
                            "entscheidest selbst wann. (Nur Windows-.exe.)",
        "update_btn": "Update",
        "update_contains": "Neue Version: v{v}",
        "update_uptodate": "Du hast die neueste Version.",
        "update_auto_note": "v{v} ist geladen — wird beim nächsten Start "
                            "installiert.",
        "update_pick_label": "Bestimmte Version installieren:",
        "update_pick_btn": "Installieren",
        "update_pick_hint": "Wähle eine beliebige veröffentlichte Version, z. B. "
                            "zum Zurückgehen. Im Automatik-Modus kann beim "
                            "nächsten Start wieder eine neuere Version installiert "
                            "werden — für eine ältere auf Manuell umstellen.",
        "update_loading_versions": "Versionen werden geladen…",
        "update_no_versions": "Keine Versionen gefunden (offline?)",
        "update_current": "Aktuelle Version: {v}",
        "update_already_on": "Du bist bereits auf Version {v}.",
        "update_downloading": "Update wird geladen…",
        "update_install": "Installieren & neu starten",
        "update_ready_next": "Update v{v} geladen — wird beim nächsten Start "
                             "installiert.",
        "update_install_now": "Jetzt installieren",
        "update_confirm": "Version {v} jetzt installieren? BubblR Trainer wird "
                          "geschlossen und automatisch neu gestartet.",
        "update_failed": "Update konnte nicht installiert werden.",
        "update_src_only": "Die Auto-Installation funktioniert nur mit der "
                           "Windows-.exe. Für die Quellcode-Version: git pull",
        # -- Update der Quellcode-Version (ohne .exe) --
        "update_src_title": "Update aus dem Quellcode",
        "update_src_ask": "Du nutzt die Quellcode-Version. Jetzt den neuesten "
                          "Code per git holen?",
        "update_src_pulling": "Quellcode wird aktualisiert…",
        "update_src_done": "Aktualisiert. Starte BubblR Trainer neu, um die neue "
                           "Version zu nutzen.",
        "update_src_fail": "git konnte diesen Ordner nicht aktualisieren.",
        "update_src_nogit": "Diese Kopie ist kein git-Checkout und kann sich "
                            "daher nicht selbst aktualisieren. Lade den neuesten "
                            "Build von der Releases-Seite oder klone das "
                            "Repository mit git.",
        "update_src_releases": "Releases-Seite öffnen",
        "recent_missing": "Dieses Bild existiert nicht mehr.",
        "mi_discord": "Auf Discord anzeigen",
        "discord_need_id": "Trage deine Discord-Application-ID unter "
                           "Einstellungen → Discord ein.",
        "discord_enable": "„in BubblR Trainer“ auf Discord anzeigen",
        "discord_id": "Discord-Application-ID (optional)",
        "discord_hint": "Leer lassen, um die eingebaute „BubblR Trainer“-App zu "
                        "nutzen — dann funktioniert es sofort (Discord muss auf "
                        "demselben PC laufen). Nur ausfüllen, wenn du deine "
                        "EIGENE Discord-Anwendung verwenden willst: eine unter "
                        "discord.com/developers/applications anlegen und die "
                        "Application ID einfügen. (Eine Application ID ist "
                        "öffentlich, kein Geheimnis.)",
        "settings_newbox_hint": "Die Klasse, die eine neu gezeichnete Box "
                                "bekommt. Jede Box lässt sich später per "
                                "Rechtsklick-Menü oder mit den Tasten B / S ändern.",
        "settings_folder_title": "Dataset-/Export-Ordner",
        "val_split": "Validierungs-Anteil:",
        "export_summary_toggle": "Zusammenfassungs-Dialog nach „Export all“ zeigen",
        "export_bg_toggle": "Leere Seiten als Hintergrundbilder exportieren",
        "export_bg_hint": "Seiten ohne Boxen werden mit leerer Label-Datei "
                          "exportiert (YOLO-Negative). Training mit "
                          "Hintergrundbildern verringert Fehlerkennungen.",
        "seg_export_toggle": "Segmentierungs-Labels exportieren (YOLO-seg)",
        "seg_export_hint": "Schreibt Polygon-Umrisse statt Boxen, damit du "
                           "Instanz-Segmentierung trainieren kannst "
                           "(task=segment). Polygon/Lasso nutzen ihren Umriss, "
                           "andere Formen die Box (Ellipsen angenähert).",
        "coco_export_toggle": "Zusätzlich COCO-JSON schreiben",
        "coco_export_hint": "Speichert die Annotationen zusätzlich im COCO-Format "
                            "(annotations.coco.json) neben den YOLO-Dateien — für "
                            "Detectron2, MMDetection u. a. Jedes Objekt erhält "
                            "eine Box und ein Polygon.",
        "val_split_hint": "Diesen Anteil der Seiten nach images/val + labels/val "
                          "statt train exportieren (0 = alles nach train). Der "
                          "Split ist pro Seite stabil, und data.yaml zeigt darauf.",
        "settings_folder_none": "(noch kein Ordner gewählt)",
        "settings_open": "Einstellungen…",
        "settings_layout": "Panels & Layout",
        "settings_unlock": "Panels entsperren (verschieben & andocken)",
        "settings_unlock_hint": "Wenn aktiv, ein Panel an seiner Titelleiste "
                                "ziehen zum Verschieben, Andocken oder Lösen. "
                                "Ausschalten sperrt das Layout.",
        "dock_tools": "Werkzeuge", "dock_boxes": "Boxen", "dock_pages": "Seiten",
        "bar_actions": "Aktionen",
        "mi_dockers": "Docker", "mi_lock_panels": "Panels sperren",
        "export_page": "Diese Seite exportieren", "export_all": "Alle Seiten exportieren",
        "ready": "Zum Start Seitenbilder laden.",
        "loaded": "{n} Bild(er) geladen.",
        "no_page": "Bitte zuerst eine Seite laden.",
        "no_boxes": "Bitte zuerst mindestens eine Box zeichnen.",
        "no_folder": "Bitte zuerst einen Datensatz-Ordner wählen.",
        "order_hint": "Klicke die Bubbles in Lesereihenfolge an (1, 2, 3 …).",
        "order_cleared": "Lesereihenfolge gelöscht.",
        "exported_one": "Exportiert: {name}",
        "exported_all": "{n} Seite(n) in den Datensatz-Ordner exportiert.",
        "summary_title": "Export-Zusammenfassung",
        "summary_pages": "{n} Seite(n) exportiert  —  {tr} train, {va} val.",
        "summary_bg": "Davon {n} Hintergrundbild(er) (ohne Objekte).",
        "summary_objects": "Objekte pro Klasse:",
        "summary_total": "Gesamt: {n} Box(en).",
        "summary_empty_cls": "⚠ Keine Beispiele für: {cls}. Diese Klasse wird "
                             "erst gelernt, wenn du sie labelst.",
        "summary_imbalance": "⚠ Klassen sind unausgewogen (10×+). Füge für die "
                             "selteneren mehr Beispiele hinzu.",
        "export_fail": "Export fehlgeschlagen: {msg}",
        "saved": "Projekt gespeichert.", "loaded_proj": "Projekt geladen ({n} Seite(n)).",
        "load_fail": "Konnte nicht laden: {msg}",
        "img_filter": "Bilder (*.png *.jpg *.jpeg *.webp *.bmp)",
        "proj_filter": "BubblR-Projekt (*.json)",
        "lang": "Sprache",
    },
}
