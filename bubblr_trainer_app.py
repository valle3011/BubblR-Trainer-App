# -*- coding: utf-8 -*-
"""BubblR Trainer - standalone desktop app.

Same job as the Krita/Photoshop BubblR Trainer plugins, but a normal window
program: load page images from disk, draw + label bubble/SFX boxes, set the
reading order, and export a YOLO dataset. No Krita, no Photoshop.

Run:  python bubblr_trainer_app.py     (needs Python 3 + PyQt5)
"""
import copy
import json
import math
import os
import struct
import subprocess
import sys
import threading
import time
import zlib

from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy, QButtonGroup, QFileDialog, QComboBox,
    QMessageBox, QCheckBox, QSpinBox, QShortcut, QSplashScreen,
    QDialog, QDialogButtonBox, QListWidget, QListWidgetItem,
    QAbstractItemView, QInputDialog, QActionGroup, QMenu,
    QStackedWidget, QRadioButton, QDockWidget, QToolButton, QLayout,
    QStyle, QWidgetItem, QTabWidget, QToolBar, QLineEdit, QColorDialog,
    QTextBrowser)
from PyQt5.QtGui import (QColor, QFont, QPainter, QPen, QBrush, QImage,
                         QPalette, QPolygonF, QKeySequence, QIcon, QPixmap)
from PyQt5.QtCore import (Qt, pyqtSignal, QRectF, QRect, QPoint, QPointF, QTimer,
                          QSize, QProcess, QItemSelectionModel, QThread)

VERSION = "0.9.8"
KIND_CLASS = {"bubble": 0, "sfx": 1}
KIND_COLOR = {"bubble": (230, 60, 60), "sfx": (70, 130, 230)}
# The default (manga) class set. Classes are user-configurable in Settings;
# each box's "kind" is a class key, and the YOLO class number is the class's
# position in this list. Keeping bubble=0 / sfx=1 as the default preserves
# compatibility with existing datasets and the BubblR AI tools.
DEFAULT_CLASSES = [
    {"key": "bubble", "label": "Bubble", "color": [230, 60, 60]},
    {"key": "sfx", "label": "SFX", "color": [70, 130, 230]},
]
# a spare palette for new custom classes
CLASS_PALETTE = [
    [60, 180, 90], [235, 160, 40], [160, 90, 210], [40, 190, 200],
    [220, 90, 160], [120, 170, 60], [200, 70, 70], [90, 120, 230],
]
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".bubblr_trainer.json")
SHORTCUT_MARK = os.path.join(os.path.expanduser("~"),
                             ".bubblr_trainer_shortcut_asked")
RECOVERY_FILE = os.path.join(os.path.expanduser("~"),
                             ".bubblr_trainer_recovery.json")

# A Discord "Application ID" is PUBLIC (not a secret, unlike the client secret /
# bot token) and is meant to be shared: every user of this app can enable Rich
# Presence with the SAME id and Discord shows the app's name to all of them.
# Create ONE free application at discord.com/developers/applications named
# "BubblR Trainer" (optionally upload an art asset called "icon" under Rich
# Presence -> Art Assets), then paste its Application ID here so presence works
# for everyone out of the box, with no per-user setup. Leave "" to disable the
# built-in id (users can still enter their own in Settings -> Discord).
DEFAULT_DISCORD_CLIENT_ID = "1525654247394246686"
# News + update check: a tiny JSON in the repo, fetched over HTTPS (no server).
# {"latest_version": "0.9.8", "url": "...releases", "items": [{title,date,text,url}]}
NEWS_URL = ("https://raw.githubusercontent.com/valle3011/"
            "BubblR-Trainer-App/main/news.json")
RELEASES_URL = "https://github.com/valle3011/BubblR-Trainer-App/releases"


def _ver_tuple(v):
    """Turn '0.9.8' into (0, 9, 8) for comparison; ignores non-digits."""
    out = []
    for part in str(v).split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        out.append(int(digits) if digits else 0)
    return tuple(out)

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
        "tool_lasso": "✎ Lasso",
        "tool_wand": "✨ Magic wand",
        "tool_rect_hint": "Drag a rectangle corner-to-corner.",
        "tool_ellipse_hint": "Drag an ellipse; the box is its bounding rectangle.",
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
        "rank_fail": "Ranking failed — see the AI tool for details.",
        "rank_empty": "No ranked pages were produced.",
        "rank_loaded": "Loaded the top {n} ranked page(s).",
        "m_file": "File", "m_edit": "Edit", "m_page": "Page",
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
        "summary_objects": "Objects per class:",
        "summary_total": "Total: {n} box(es).",
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
        "tool_lasso": "✎ Lasso",
        "tool_wand": "✨ Zauberstab",
        "tool_rect_hint": "Rechteck von Ecke zu Ecke ziehen.",
        "tool_ellipse_hint": "Ellipse ziehen; die Box ist ihr umschließendes Rechteck.",
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
        "rank_fail": "Ranking fehlgeschlagen — Details im AI-Tool.",
        "rank_empty": "Es wurden keine gerankten Seiten erzeugt.",
        "rank_loaded": "Top {n} gerankte Seite(n) geladen.",
        "m_file": "Datei", "m_edit": "Bearbeiten", "m_page": "Seite",
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
        "summary_objects": "Objekte pro Klasse:",
        "summary_total": "Gesamt: {n} Box(en).",
        "export_fail": "Export fehlgeschlagen: {msg}",
        "saved": "Projekt gespeichert.", "loaded_proj": "Projekt geladen ({n} Seite(n)).",
        "load_fail": "Konnte nicht laden: {msg}",
        "img_filter": "Bilder (*.png *.jpg *.jpeg *.webp *.bmp)",
        "proj_filter": "BubblR-Projekt (*.json)",
        "lang": "Sprache",
    },
}


def make_yolo_label(boxes, img_w, img_h, class_index=None):
    ci = class_index if class_index is not None else KIND_CLASS
    lines = []
    for b in boxes:
        cls = ci.get(b.get("kind", "bubble"), 0)
        cx = min(1.0, max(0.0, (b["x"] + b["w"] / 2.0) / float(img_w)))
        cy = min(1.0, max(0.0, (b["y"] + b["h"] / 2.0) / float(img_h)))
        w = min(1.0, max(0.0, b["w"] / float(img_w)))
        h = min(1.0, max(0.0, b["h"] / float(img_h)))
        lines.append("%d %.6f %.6f %.6f %.6f" % (cls, cx, cy, w, h))
    return "\n".join(lines) + "\n" if lines else ""


def order_data(boxes, img_w, img_h, class_index=None):
    ci = class_index if class_index is not None else KIND_CLASS
    indexed = list(enumerate(boxes))
    indexed.sort(key=lambda p: (p[1].get("order") or 10 ** 9, p[0]))
    out = []
    for seq, (_i, b) in enumerate(indexed, start=1):
        kind = b.get("kind", "bubble")
        out.append({
            "order": seq, "set": bool(b.get("order")), "kind": kind,
            "class": ci.get(kind, 0),
            "x": int(b["x"]), "y": int(b["y"]),
            "w": int(b["w"]), "h": int(b["h"]),
            "cx": (b["x"] + b["w"] / 2.0) / float(img_w),
            "cy": (b["y"] + b["h"] / 2.0) / float(img_h),
            "nw": b["w"] / float(img_w), "nh": b["h"] / float(img_h),
        })
    return {"width": img_w, "height": img_h, "boxes": out}


def _tier_order(indices, boxes, rtl):
    """Order a leaf cluster (no clean panel cut left) by VERTICAL-OVERLAP tiers.

    Two bubbles share a tier when their vertical spans overlap by more than a
    third of the smaller one's height — scale-aware, so a big dramatic bubble
    next to a small one groups correctly and staggered side-by-side bubbles
    stay together. Each tier keeps its top-most bubble's span as a fixed
    reference (it does not grow downward), so a vertical stack does not chain
    into one giant horizontal tier."""
    idx = list(indices)
    if len(idx) <= 1:
        return idx
    spans = {i: (boxes[i]["y"], boxes[i]["y"] + boxes[i]["h"]) for i in idx}
    order_by_top = sorted(idx, key=lambda i: (spans[i][0], boxes[i]["x"]))
    tiers = []                       # each: {"top", "bot", "items": [...]}
    for i in order_by_top:
        top, bot = spans[i]
        h = bot - top
        best, best_ov = None, 0.0
        for tier in tiers:
            ov = min(bot, tier["bot"]) - max(top, tier["top"])
            ref_h = tier["bot"] - tier["top"]
            frac = ov / max(1.0, min(h, ref_h))
            if frac > 0.35 and ov > best_ov:
                best, best_ov = tier, ov
        if best is not None:
            best["items"].append(i)
        else:
            tiers.append({"top": top, "bot": bot, "items": [i]})
    tiers.sort(key=lambda t: t["top"])
    out = []
    for tier in tiers:
        # stable sort: equal-x bubbles keep their top-to-bottom order
        tier["items"].sort(
            key=lambda i: boxes[i]["x"] + boxes[i]["w"] / 2.0, reverse=rtl)
        out.extend(tier["items"])
    return out


def _axis_iv(i, boxes, axis):
    b = boxes[i]
    return (b["y"], b["y"] + b["h"]) if axis == "y" else (b["x"], b["x"] + b["w"])


def _best_gap(indices, boxes, axis):
    """Largest CLEAN gap along axis: a coordinate no box crosses, with boxes on
    both sides. Returns (gap, low_side_indices, high_side_indices) or None. The
    split is clean because, scanning boxes sorted by their leading edge, a gap
    only counts where the next box starts past the running far edge of every
    box before it — so the two sides never interleave along this axis."""
    iv = sorted(((_axis_iv(i, boxes, axis), i) for i in indices),
                key=lambda t: t[0][0])
    max_hi = iv[0][0][1]
    best_gap, best_split = 0.0, None
    for k in range(1, len(iv)):
        lo = iv[k][0][0]
        if lo > max_hi and (lo - max_hi) > best_gap:
            best_gap, best_split = lo - max_hi, k
        max_hi = max(max_hi, iv[k][0][1])
    if best_split is None:
        return None
    low = [iv[k][1] for k in range(best_split)]
    high = [iv[k][1] for k in range(best_split, len(iv))]
    return best_gap, low, high


def _axis_overlap(ga, gb, boxes, axis):
    """Do the bounding intervals of two groups overlap on the given axis?"""
    a = [_axis_iv(i, boxes, axis) for i in ga]
    b = [_axis_iv(i, boxes, axis) for i in gb]
    alo, ahi = min(x[0] for x in a), max(x[1] for x in a)
    blo, bhi = min(x[0] for x in b), max(x[1] for x in b)
    return min(ahi, bhi) - max(alo, blo) > 0


def _panel_order(indices, boxes, rtl):
    """Recursive XY-cut on the bubble positions (panel-aware reading order).

    At each step split the region at its most prominent clean gutter:
      * a horizontal gutter whose two sides share the same columns (they stack)
        is a TIER boundary -> read the top tier fully, then the bottom;
      * a vertical gutter whose two sides share the same rows (side by side) is
        a COLUMN/panel boundary -> read the right column fully first for manga.
    Manga is tier-primary, so a valid horizontal cut is preferred. When neither
    a stacked nor a side-by-side gutter exists, the cluster is an overlapping
    blob and is ordered by _tier_order. This nests panels correctly (e.g. a
    tall right panel beside a left column, or a 2x2 grid with a split cell)."""
    indices = list(indices)
    if len(indices) <= 1:
        return indices
    yc = _best_gap(indices, boxes, "y")
    xc = _best_gap(indices, boxes, "x")
    if yc and _axis_overlap(yc[1], yc[2], boxes, "x"):          # tier boundary
        return (_panel_order(yc[1], boxes, rtl)
                + _panel_order(yc[2], boxes, rtl))
    if xc and _axis_overlap(xc[1], xc[2], boxes, "y"):          # column boundary
        left, right = xc[1], xc[2]
        first, second = (right, left) if rtl else (left, right)
        return (_panel_order(first, boxes, rtl)
                + _panel_order(second, boxes, rtl))
    return _tier_order(indices, boxes, rtl)


def auto_order(boxes, rtl=True):
    """Assign a reading order to every box automatically. Manga (rtl) is read
    tier by tier top-to-bottom, each tier's panels right-to-left; a recursive
    panel cut (_panel_order) reproduces that from the bubble layout, falling
    back to overlap tiers where panels can't be separated. You only fix the few
    it gets wrong instead of clicking every bubble."""
    n = len(boxes)
    if n == 0:
        return
    for rank, i in enumerate(_panel_order(list(range(n)), boxes, rtl), 1):
        boxes[i]["order"] = rank


# ---------------------------------------------------------------------------
# Box overlay (pure Qt; ported from the Krita trainer plugin)
# ---------------------------------------------------------------------------

class BoxOverlay(QWidget):
    boxClicked = pyqtSignal(int)
    boxRemoved = pyqtSignal(int)
    # x, y, w, h, shape ("rect"/"ellipse"/"lasso"/"wand"), points (list or None)
    boxAdded = pyqtSignal(float, float, float, float, str, object)
    boxChanged = pyqtSignal(int, float, float, float, float)
    rubberSelect = pyqtSignal(float, float, float, float)  # x, y, w, h in doc
    boxContextMenu = pyqtSignal(int, QPoint)               # idx, global pos
    canvasContextMenu = pyqtSignal(float, float, QPoint)   # doc x, y, global pos

    _HANDLE = 9
    # which box edges a handle moves ('l'eft 'r'ight 't'op 'b'ottom)
    _HANDLE_EDGES = {"nw": ("l", "t"), "ne": ("r", "t"), "sw": ("l", "b"),
                     "se": ("r", "b"), "n": ("t",), "s": ("b",),
                     "e": ("r",), "w": ("l",)}

    def __init__(self):
        super(BoxOverlay, self).__init__()
        self._img = None
        self._doc_w = 1
        self._doc_h = 1
        self._boxes = []
        self._current = -1
        self._selected = set()
        self._edit = False
        self._drag = None
        self._zoom = 1.0          # 1.0 = fit to the widget
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._panning = None      # last pos while middle-drag panning
        self._rubber = None       # rubber-band rectangle while view-mode drag
        self._tool = "rect"       # rect | ellipse | lasso | wand
        self._show_center = True  # draw a marker at each box's centre
        self._show_order_path = False  # draw the 1->2->3 reading-order path
        self._kind_filter = None       # None | class key (show only that class)
        # class key -> (QColor, badge letter); set by the window from its classes
        self._class_colors = dict(
            bubble=(QColor(230, 60, 60), "B"), sfx=(QColor(70, 130, 230), "S"))
        self._wand_tol = 40       # magic-wand colour tolerance (0..255)
        self.setMinimumHeight(260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)   # so arrow keys nudge the box

    def set_edit_mode(self, on):
        self._edit = bool(on)
        self._drag = None
        self.setCursor(Qt.CrossCursor if on else Qt.ArrowCursor)
        self.update()

    def set_tool(self, name):
        if name in ("rect", "ellipse", "lasso", "wand"):
            self._tool = name
            self._drag = None
            self.update()

    def set_center_marker(self, on):
        self._show_center = bool(on)
        self.update()

    def set_order_path(self, on):
        self._show_order_path = bool(on)
        self.update()

    def set_kind_filter(self, kind):
        """Show only boxes of this class key; None shows all."""
        self._kind_filter = kind if kind in self._class_colors else None
        self.update()

    def set_class_colors(self, mapping):
        """mapping: class key -> (QColor, badge letter)."""
        self._class_colors = dict(mapping)
        self.update()

    def _kind_color(self, kind):
        c = self._class_colors.get(kind)
        return c[0] if c else QColor(150, 150, 150)

    def _kind_letter(self, kind):
        c = self._class_colors.get(kind)
        return c[1] if c else "?"

    def _hidden(self, b):
        """Is this box hidden by the active class filter?"""
        f = self._kind_filter
        if f is None:
            return False
        return b.get("kind", "bubble") != f

    def set_wand_tolerance(self, value):
        self._wand_tol = max(1, min(255, int(value)))

    def set_page(self, img, doc_w, doc_h):
        self._img = img
        self._doc_w = max(1, doc_w)
        self._doc_h = max(1, doc_h)
        self.fit()                # a new page starts fitted

    def set_boxes(self, boxes, current=-1, selected=None):
        self._boxes = boxes
        self._current = current
        self._selected = set(selected) if selected else set()
        self.update()

    def _base_scale(self):
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return 1.0
        return min(w / float(self._doc_w), h / float(self._doc_h))

    def _target(self):
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return QRectF(0, 0, 1, 1)
        s = self._base_scale() * self._zoom
        tw = self._doc_w * s
        th = self._doc_h * s
        x = (w - tw) / 2.0 + self._pan_x
        y = (h - th) / 2.0 + self._pan_y
        return QRectF(x, y, tw, th)

    # -- zoom / pan --
    def fit(self):
        self._zoom = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self.update()

    def zoom_to_rect(self, x, y, w, h, margin=0.18):
        """Zoom + pan so the doc-rect (x, y, w, h) fills the view with a margin."""
        if self._img is None or self._img.isNull():
            return
        vw, vh = self.width(), self.height()
        base = self._base_scale()
        if vw <= 0 or vh <= 0 or w <= 0 or h <= 0 or base <= 0:
            return
        fit = min(vw * (1 - margin) / w, vh * (1 - margin) / h)
        self._zoom = max(0.1, min(12.0, fit / base))
        s = base * self._zoom
        rcx, rcy = x + w / 2.0, y + h / 2.0     # centre the rect in the view
        self._pan_x = vw / 2.0 - rcx * s - (vw - self._doc_w * s) / 2.0
        self._pan_y = vh / 2.0 - rcy * s - (vh - self._doc_h * s) / 2.0
        self.update()

    def _zoom_at(self, pos, factor):
        z2 = max(0.1, min(12.0, self._zoom * factor))
        if abs(z2 - self._zoom) < 1e-9:
            return
        w, h = self.width(), self.height()
        base = self._base_scale()
        s = base * self._zoom
        s2 = base * z2
        cx0 = (w - self._doc_w * s) / 2.0 + self._pan_x
        cy0 = (h - self._doc_h * s) / 2.0 + self._pan_y
        ix = (pos.x() - cx0) / s if s else 0.0
        iy = (pos.y() - cy0) / s if s else 0.0
        self._pan_x = (pos.x() - ix * s2) - (w - self._doc_w * s2) / 2.0
        self._pan_y = (pos.y() - iy * s2) - (h - self._doc_h * s2) / 2.0
        self._zoom = z2
        self.update()

    def zoom_step(self, factor):
        self._zoom_at(QPoint(self.width() // 2, self.height() // 2), factor)

    def wheelEvent(self, ev):
        if self._img is None:
            return
        d = ev.angleDelta().y()
        if d:
            self._zoom_at(ev.pos(), 1.18 if d > 0 else 1.0 / 1.18)
        ev.accept()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QColor(60, 60, 60))
        t = self._target()
        if self._img is not None and not self._img.isNull():
            p.drawImage(t, self._img,
                        QRectF(0, 0, self._img.width(), self._img.height()))
        scale = t.width() / float(self._doc_w)
        fnt = QFont()
        fnt.setBold(True)
        fnt.setPixelSize(13)
        p.setFont(fnt)
        for k, b in enumerate(self._boxes):
            if self._hidden(b):                 # class filter hides this box
                continue
            r = QRectF(t.x() + b["x"] * scale, t.y() + b["y"] * scale,
                       b["w"] * scale, b["h"] * scale)
            kind = b.get("kind", "bubble")
            color = self._kind_color(kind)
            sel = (k == self._current) or (k in self._selected)
            p.setPen(QPen(color, 3 if sel else 2))
            p.setBrush(Qt.NoBrush)
            self._draw_shape(p, r, b.get("shape", "rect"),
                             b.get("points"), t, scale)
            if self._show_center:
                self._draw_center(p, r.center(), color, big=sel)
            order = b.get("order", 0)
            label = str(order) if order else self._kind_letter(kind)
            badge = QRectF(r.x(), r.y(), max(18, 8 + 8 * len(label)), 16)
            p.fillRect(badge, color)
            p.setPen(QPen(QColor(255, 255, 255)))
            p.drawText(badge, Qt.AlignCenter, label)
            if self._edit:
                p.setBrush(QBrush(QColor(255, 255, 255)))
                p.setPen(QPen(QColor(30, 30, 30), 1))
                hs = [(r.left(), r.top()), (r.right(), r.top()),
                      (r.left(), r.bottom()), (r.right(), r.bottom())]
                if k == self._current:            # edge handles on the active box
                    cxp, cyp = r.center().x(), r.center().y()
                    hs += [(cxp, r.top()), (cxp, r.bottom()),
                           (r.left(), cyp), (r.right(), cyp)]
                for hx, hy in hs:
                    p.drawRect(QRectF(hx - 3, hy - 3, 6, 6))
        if self._show_order_path:
            self._draw_order_path(p, t, scale)
        # live preview of the shape being drawn
        rect = self._rect_of(self._drag) if self._drag else None
        if rect is not None:
            x, y, w, h = rect
            pr = QRectF(t.x() + x * scale, t.y() + y * scale,
                        w * scale, h * scale)
            p.setPen(QPen(QColor(60, 200, 90), 2, Qt.DashLine))
            p.setBrush(QBrush(Qt.NoBrush))
            shape = self._drag.get("shape", "rect")
            pts = self._drag.get("pts")
            self._draw_shape(p, pr, shape, pts, t, scale, closed=False)
            # centre marker + live size read-out while marking
            c = pr.center()
            self._draw_center(p, c, QColor(60, 200, 90), big=True)
            p.setPen(QPen(QColor(20, 40, 20)))
            info = "%d x %d" % (int(round(w)), int(round(h)))
            tag = QRectF(c.x() + 8, c.y() + 8, 8 + 7 * len(info), 15)
            p.fillRect(tag, QColor(60, 200, 90))
            p.setPen(QPen(QColor(255, 255, 255)))
            p.drawText(tag, Qt.AlignCenter, info)
        # rubber-band selection rectangle
        if self._rubber is not None:
            rx, ry, rw, rh = self._norm(self._rubber["x0"], self._rubber["y0"],
                                        self._rubber["cx"], self._rubber["cy"])
            rr = QRectF(t.x() + rx * scale, t.y() + ry * scale,
                        rw * scale, rh * scale)
            p.setPen(QPen(QColor(255, 255, 255, 200), 1, Qt.DashLine))
            p.setBrush(QBrush(QColor(120, 170, 255, 45)))
            p.drawRect(rr)
        p.end()

    def _draw_shape(self, p, r, shape, points, t, scale, closed=True):
        """Outline a box as a rectangle, ellipse or lasso polygon."""
        if shape == "ellipse":
            p.drawEllipse(r)
        elif shape == "lasso" and points:
            poly = QPolygonF([QPointF(t.x() + px * scale, t.y() + py * scale)
                              for px, py in points])
            if closed:
                p.drawPolygon(poly)
            else:
                p.drawPolyline(poly)
        else:
            p.drawRect(r)

    def _draw_center(self, p, c, color, big=False):
        """Draw a small cross + dot at the centre of a marking."""
        arm = 9 if big else 5
        pen = QPen(QColor(255, 255, 255), 3 if big else 2)
        p.setBrush(Qt.NoBrush)
        p.setPen(pen)
        p.drawLine(QPointF(c.x() - arm, c.y()), QPointF(c.x() + arm, c.y()))
        p.drawLine(QPointF(c.x(), c.y() - arm), QPointF(c.x(), c.y() + arm))
        p.setPen(QPen(color, 1 if big else 1))
        p.drawLine(QPointF(c.x() - arm, c.y()), QPointF(c.x() + arm, c.y()))
        p.drawLine(QPointF(c.x(), c.y() - arm), QPointF(c.x(), c.y() + arm))
        p.setBrush(QBrush(color))
        p.setPen(QPen(QColor(255, 255, 255), 1))
        rad = 3.0 if big else 2.0
        p.drawEllipse(c, rad, rad)

    def _draw_order_path(self, p, t, scale):
        """Connect the boxes that have a reading order (1 -> 2 -> 3 …) with a
        line and arrowheads, so the reading order is visible at a glance and
        wrong steps are easy to spot after an auto-order."""
        pts = []
        for b in self._boxes:
            o = b.get("order", 0)
            if o:
                cx = t.x() + (b["x"] + b["w"] / 2.0) * scale
                cy = t.y() + (b["y"] + b["h"] / 2.0) * scale
                pts.append((o, cx, cy))
        if len(pts) < 2:
            return
        pts.sort(key=lambda z: z[0])
        col = QColor(255, 205, 40, 230)
        p.setPen(QPen(col, 2))
        p.setBrush(Qt.NoBrush)
        for (_o0, x0, y0), (_o1, x1, y1) in zip(pts, pts[1:]):
            p.drawLine(QPointF(x0, y0), QPointF(x1, y1))
        # arrowhead at each segment's midpoint, pointing along the path
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(col))
        for (_o0, x0, y0), (_o1, x1, y1) in zip(pts, pts[1:]):
            mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            ang = math.atan2(y1 - y0, x1 - x0)
            a1, a2 = ang + math.radians(148), ang - math.radians(148)
            head = QPolygonF([
                QPointF(mx + 8 * math.cos(ang), my + 8 * math.sin(ang)),
                QPointF(mx + 8 * math.cos(a1), my + 8 * math.sin(a1)),
                QPointF(mx + 8 * math.cos(a2), my + 8 * math.sin(a2)),
            ])
            p.drawPolygon(head)

    def _hit(self, pos):
        t = self._target()
        if t.width() <= 0:
            return -1
        scale = t.width() / float(self._doc_w)
        x = (pos.x() - t.x()) / scale
        y = (pos.y() - t.y()) / scale
        best, best_area = -1, None
        for k, b in enumerate(self._boxes):
            if self._hidden(b):                 # can't pick a filtered-out box
                continue
            if b["x"] <= x <= b["x"] + b["w"] and \
               b["y"] <= y <= b["y"] + b["h"]:
                area = b["w"] * b["h"]
                if best_area is None or area < best_area:
                    best, best_area = k, area
        return best

    def _to_doc(self, pos):
        t = self._target()
        if t.width() <= 0:
            return 0.0, 0.0
        scale = t.width() / float(self._doc_w)
        return (pos.x() - t.x()) / scale, (pos.y() - t.y()) / scale

    def _probe_box(self, k, pos, t, scale):
        """What the point hits on box `k`: (k, corner/edge) for a resize handle
        (nw/ne/sw/se or n/s/e/w), (k, 'move') inside the box, or None."""
        b = self._boxes[k]
        x0 = t.x() + b["x"] * scale
        y0 = t.y() + b["y"] * scale
        x1 = x0 + b["w"] * scale
        y1 = y0 + b["h"] * scale
        H = self._HANDLE
        px, py = pos.x(), pos.y()
        nl, nr = abs(px - x0) <= H, abs(px - x1) <= H
        nt, nb = abs(py - y0) <= H, abs(py - y1) <= H
        in_x, in_y = x0 <= px <= x1, y0 <= py <= y1
        if nl and nt:
            return (k, "nw")
        if nr and nt:
            return (k, "ne")
        if nl and nb:
            return (k, "sw")
        if nr and nb:
            return (k, "se")
        if nt and in_x:
            return (k, "n")
        if nb and in_x:
            return (k, "s")
        if nl and in_y:
            return (k, "w")
        if nr and in_y:
            return (k, "e")
        if in_x and in_y:
            return (k, "move")
        return None

    def _handle_at(self, pos):
        t = self._target()
        if t.width() <= 0:
            return None
        scale = t.width() / float(self._doc_w)
        # The currently selected box has priority: when boxes overlap, editing
        # stays on the box you picked instead of grabbing whatever is on top.
        cur = getattr(self, "_current", -1)
        if 0 <= cur < len(self._boxes) and not self._hidden(self._boxes[cur]):
            hit = self._probe_box(cur, pos, t, scale)
            if hit is not None:
                return hit
        # otherwise: any corner wins (resize), else the smallest box (move)
        best, best_area = None, None
        for k in range(len(self._boxes)):
            if self._hidden(self._boxes[k]):
                continue
            hit = self._probe_box(k, pos, t, scale)
            if hit is None:
                continue
            if hit[1] != "move":
                return hit
            area = self._boxes[k]["w"] * self._boxes[k]["h"]
            if best_area is None or area < best_area:
                best, best_area = hit, area
        return best

    @staticmethod
    def _norm(ax, ay, bx, by):
        return (min(ax, bx), min(ay, by), abs(bx - ax), abs(by - ay))

    def _rect_of(self, d):
        if not d:
            return None
        if d["mode"] == "new":
            if d.get("shape") == "lasso":
                pts = d.get("pts") or []
                if not pts:
                    return None
                xs = [px for px, _ in pts]
                ys = [py for _, py in pts]
                return (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
            return self._norm(d["x0"], d["y0"], d["cx"], d["cy"])
        if d["mode"] == "move":
            return (d["bx"] + (d["cx"] - d["px"]),
                    d["by"] + (d["cy"] - d["py"]), d["bw"], d["bh"])
        # resize: move only the grabbed edge(s) to the cursor, keep the rest
        x0, y0, x1, y1 = d["x0"], d["y0"], d["x1"], d["y1"]
        mv = d.get("mv", ())
        if "l" in mv:
            x0 = d["cx"]
        if "r" in mv:
            x1 = d["cx"]
        if "t" in mv:
            y0 = d["cy"]
        if "b" in mv:
            y1 = d["cy"]
        return self._norm(x0, y0, x1, y1)

    def _clamp(self, x, y, w, h):
        x = max(0.0, min(x, self._doc_w - 1))
        y = max(0.0, min(y, self._doc_h - 1))
        w = min(w, self._doc_w - x)
        h = min(h, self._doc_h - y)
        return x, y, w, h

    @staticmethod
    def _cursor_for(name):
        return {"nw": Qt.SizeFDiagCursor, "se": Qt.SizeFDiagCursor,
                "ne": Qt.SizeBDiagCursor, "sw": Qt.SizeBDiagCursor,
                "n": Qt.SizeVerCursor, "s": Qt.SizeVerCursor,
                "e": Qt.SizeHorCursor, "w": Qt.SizeHorCursor,
                "move": Qt.SizeAllCursor}.get(name, Qt.CrossCursor)

    def mousePressEvent(self, event):
        self.setFocus()                      # take keyboard focus for nudging
        if event.button() == Qt.MiddleButton:
            self._panning = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            return
        if event.button() == Qt.RightButton:
            idx = self._hit(event.pos())
            if idx >= 0:
                self.boxContextMenu.emit(idx, event.globalPos())
            else:
                dx, dy = self._to_doc(event.pos())
                self.canvasContextMenu.emit(dx, dy, event.globalPos())
            return
        if event.button() != Qt.LeftButton:
            return
        if self._edit:
            self._begin_edit(event.pos())
            return
        idx = self._hit(event.pos())
        if idx >= 0:
            self.boxClicked.emit(idx)
        else:                                # empty space -> rubber-band select
            dx, dy = self._to_doc(event.pos())
            self._rubber = {"x0": dx, "y0": dy, "cx": dx, "cy": dy}

    def keyPressEvent(self, event):
        # arrow keys nudge the selected box (Shift = 10 px); pan otherwise
        k = event.key()
        arrows = (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down)
        if k in arrows and 0 <= self._current < len(self._boxes):
            mods = event.modifiers()
            step = 10 if mods & Qt.ShiftModifier else 1
            b = self._boxes[self._current]
            if mods & Qt.AltModifier:
                # Alt + arrows resize: L/R change width, U/D change height
                # (Right/Down grow, Left/Up shrink) from the top-left corner.
                dw = -step if k == Qt.Key_Left else step if k == Qt.Key_Right else 0
                dh = -step if k == Qt.Key_Up else step if k == Qt.Key_Down else 0
                nw = max(4, min(b["w"] + dw, self._doc_w - b["x"]))
                nh = max(4, min(b["h"] + dh, self._doc_h - b["y"]))
                if nw != b["w"] or nh != b["h"]:
                    self.boxChanged.emit(self._current, b["x"], b["y"], nw, nh)
                event.accept()
                return
            dx = -step if k == Qt.Key_Left else step if k == Qt.Key_Right else 0
            dy = -step if k == Qt.Key_Up else step if k == Qt.Key_Down else 0
            nx = max(0, min(b["x"] + dx, self._doc_w - b["w"]))
            ny = max(0, min(b["y"] + dy, self._doc_h - b["h"]))
            if nx != b["x"] or ny != b["y"]:
                self.boxChanged.emit(self._current, nx, ny, b["w"], b["h"])
            event.accept()
            return
        super(BoxOverlay, self).keyPressEvent(event)

    def _begin_edit(self, pos):
        dx, dy = self._to_doc(pos)
        hit = self._handle_at(pos)
        # resizing an existing box (grabbing a corner or edge) always wins
        if hit is not None and hit[1] != "move":
            idx, name = hit
            b = self._boxes[idx]
            self._drag = {"mode": "resize", "idx": idx,
                          "x0": b["x"], "y0": b["y"],
                          "x1": b["x"] + b["w"], "y1": b["y"] + b["h"],
                          "mv": self._HANDLE_EDGES.get(name, ()),
                          "cx": dx, "cy": dy}
            self.update()
            return
        if self._tool == "wand":
            bbox = self._magic_wand(dx, dy)
            self._drag = None
            if bbox:
                x, y, w, h = self._clamp(*bbox)
                if w >= 4 and h >= 4:
                    self.boxAdded.emit(x, y, w, h, "wand", None)
            self.update()
            return
        if hit is not None and hit[1] == "move":
            b = self._boxes[hit[0]]
            self._drag = {"mode": "move", "idx": hit[0], "bx": b["x"],
                          "by": b["y"], "bw": b["w"], "bh": b["h"],
                          "px": dx, "py": dy, "cx": dx, "cy": dy}
        elif self._tool == "lasso":
            self._drag = {"mode": "new", "shape": "lasso",
                          "pts": [(dx, dy)], "cx": dx, "cy": dy}
        else:
            self._drag = {"mode": "new", "shape": self._tool,
                          "x0": dx, "y0": dy, "cx": dx, "cy": dy}
        self.update()

    def mouseMoveEvent(self, event):
        if self._panning is not None:
            d = event.pos() - self._panning
            self._pan_x += d.x()
            self._pan_y += d.y()
            self._panning = event.pos()
            self.update()
            return
        if self._rubber is not None:
            self._rubber["cx"], self._rubber["cy"] = self._to_doc(event.pos())
            self.update()
            return
        if not self._edit:
            return
        if self._drag is None:
            # hover feedback: resize/move cursor over a handle, else crosshair
            hit = self._handle_at(event.pos())
            self.setCursor(self._cursor_for(hit[1]) if hit else Qt.CrossCursor)
            return
        dx, dy = self._to_doc(event.pos())
        self._drag["cx"], self._drag["cy"] = dx, dy
        if self._drag.get("shape") == "lasso" and self._drag.get("pts") is not None:
            pts = self._drag["pts"]
            # keep the point list small: only record noticeable movement
            if not pts or abs(dx - pts[-1][0]) + abs(dy - pts[-1][1]) >= 2:
                pts.append((dx, dy))
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton and self._panning is not None:
            self._panning = None
            self.setCursor(Qt.CrossCursor if self._edit else Qt.ArrowCursor)
            return
        if self._rubber is not None and event.button() == Qt.LeftButton:
            r, self._rubber = self._rubber, None
            x, y, w, h = self._norm(r["x0"], r["y0"], r["cx"], r["cy"])
            self.update()
            self.rubberSelect.emit(x, y, w, h)
            return
        if not self._edit or self._drag is None:
            return
        d, self._drag = self._drag, None
        rect = self._rect_of(d)
        self.update()
        if rect is None:
            return
        x, y, w, h = rect
        if w < 8 or h < 8:
            return
        x, y, w, h = self._clamp(x, y, w, h)
        if d["mode"] == "new":
            shape = d.get("shape", "rect")
            points = None
            if shape == "lasso":
                points = [[round(px, 1), round(py, 1)] for px, py in d.get("pts", [])]
                if len(points) < 3:
                    return
            self.boxAdded.emit(x, y, w, h, shape, points)
        else:
            self.boxChanged.emit(d["idx"], x, y, w, h)

    def _magic_wand(self, dx, dy):
        """Flood-fill a same-colour region from (dx, dy); return its bbox."""
        img = self._img
        if img is None or img.isNull():
            return None
        w, h = img.width(), img.height()
        sx, sy = int(round(dx)), int(round(dy))
        if not (0 <= sx < w and 0 <= sy < h):
            return None
        conv = img.convertToFormat(QImage.Format_RGB32)
        bpl = conv.bytesPerLine()
        ptr = conv.bits()
        ptr.setsize(bpl * h)
        data = bytes(ptr)              # little-endian 0xAARRGGBB -> B, G, R, A
        o0 = sy * bpl + sx * 4
        sr, sg, sb = data[o0 + 2], data[o0 + 1], data[o0]
        tol = self._wand_tol
        visited = bytearray(w * h)
        cap = min(w * h, 4000000)      # guard against flooding a whole flat page
        count = 0
        minx = maxx = sx
        miny = maxy = sy
        stack = [(sx, sy)]
        visited[sy * w + sx] = 1
        while stack:
            x, y = stack.pop()
            o = y * bpl + x * 4
            if abs(data[o + 2] - sr) > tol or abs(data[o + 1] - sg) > tol \
                    or abs(data[o] - sb) > tol:
                continue
            count += 1
            if count > cap:
                break
            if x < minx:
                minx = x
            elif x > maxx:
                maxx = x
            if y < miny:
                miny = y
            elif y > maxy:
                maxy = y
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < w and 0 <= ny < h:
                    i = ny * w + nx
                    if not visited[i]:
                        visited[i] = 1
                        stack.append((nx, ny))
        if maxx - minx < 3 or maxy - miny < 3:
            return None
        pad = 2
        minx = max(0, minx - pad)
        miny = max(0, miny - pad)
        maxx = min(w - 1, maxx + pad)
        maxy = min(h - 1, maxy + pad)
        return (float(minx), float(miny),
                float(maxx - minx + 1), float(maxy - miny + 1))

    def _fit_box_bounds(self, b):
        """Tighten box `b` to the bubble inside it: find a bright seed near the
        box centre, flood-fill it, and return the bbox — but only if it stays
        within the original box (so a leak through a broken outline is ignored).
        Returns a bbox tuple or None."""
        img = self._img
        if img is None or img.isNull():
            return None
        conv = img.convertToFormat(QImage.Format_RGB32)
        bpl = conv.bytesPerLine()
        ptr = conv.bits()
        ptr.setsize(bpl * conv.height())
        data = bytes(ptr)
        w, h = img.width(), img.height()
        bx0 = max(0, int(b["x"]))
        by0 = max(0, int(b["y"]))
        bx1 = min(w - 1, int(b["x"] + b["w"]))
        by1 = min(h - 1, int(b["y"] + b["h"]))
        if bx1 - bx0 < 4 or by1 - by0 < 4:
            return None
        cx, cy = (bx0 + bx1) // 2, (by0 + by1) // 2
        step = max(1, int(((bx1 - bx0) * (by1 - by0) / 4000.0) ** 0.5))
        seed, best = None, None
        for y in range(by0, by1 + 1, step):
            row = y * bpl
            for x in range(bx0, bx1 + 1, step):
                o = row + x * 4
                lum = data[o + 2] * 0.30 + data[o + 1] * 0.59 + data[o] * 0.11
                if lum >= 200:                       # bright = bubble interior
                    d = (x - cx) ** 2 + (y - cy) ** 2
                    if best is None or d < best:
                        best, seed = d, (x, y)
        if seed is None:
            return None
        bb = self._magic_wand(seed[0], seed[1])
        if not bb:
            return None
        fx, fy, fw, fh = bb
        pad = 6                                       # tolerate the 2px wand pad
        if (fx < b["x"] - pad or fy < b["y"] - pad
                or fx + fw > b["x"] + b["w"] + pad
                or fy + fh > b["y"] + b["h"] + pad):
            return None                               # leaked out of the box
        return bb


class FlowLayout(QLayout):
    """A layout that lays its items left-to-right and wraps to the next line
    when it runs out of width — so a panel of tool buttons reflows to fit
    whether the dock is wide (buttons in a row) or narrow (buttons stacked)."""

    def __init__(self, parent=None, margin=4, spacing=4):
        super(FlowLayout, self).__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self._spacing = spacing
        self._items = []

    def addItem(self, item):            # noqa: N802 (Qt override)
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):                # noqa: N802
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):                # noqa: N802
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):      # noqa: N802
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):        # noqa: N802
        return True

    def heightForWidth(self, width):    # noqa: N802
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):        # noqa: N802
        super(FlowLayout, self).setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):                 # noqa: N802
        return self.minimumSize()

    def minimumSize(self):              # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect, test_only):
        m = self.contentsMargins()
        x = rect.x() + m.left()
        y = rect.y() + m.top()
        right = rect.right() - m.right()
        line_h = 0
        for item in self._items:
            w = item.sizeHint().width()
            h = item.sizeHint().height()
            if x + w > right and line_h > 0:      # wrap to the next line
                x = rect.x() + m.left()
                y = y + line_h + self._spacing
                line_h = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = x + w + self._spacing
            line_h = max(line_h, h)
        return y + line_h + m.bottom() - rect.y()


def make_tool_icon(kind, size=24):
    """A small Krita-style icon for a selection tool, drawn on the fly so no
    image assets are needed (light strokes for the dark theme)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    ink = QColor(225, 228, 232)
    pen = QPen(ink, 1.6)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    m = 4
    if kind == "rect":                       # rectangular marquee (dashed)
        pen.setStyle(Qt.DashLine)
        p.setPen(pen)
        p.drawRect(m, m + 1, size - 2 * m, size - 2 * m - 2)
    elif kind == "ellipse":                  # elliptical marquee (dashed)
        pen.setStyle(Qt.DashLine)
        p.setPen(pen)
        p.drawEllipse(m, m, size - 2 * m, size - 2 * m)
    elif kind == "lasso":                    # freehand / polygon lasso loop
        poly = QPolygonF([
            QPointF(m + 1, size - m), QPointF(m, m + 4),
            QPointF(size * 0.5, m), QPointF(size - m, m + 3),
            QPointF(size - m - 1, size - m - 3),
            QPointF(size * 0.55, size - m - 1)])
        p.drawPolyline(poly)
    else:                                    # magic wand: a stick + a spark
        p.drawLine(int(size - m - 1), int(m + 1),
                   int(m + 4), int(size - m - 1))
        star = QColor(120, 200, 250)
        p.setPen(QPen(star, 1.4))
        cx, cy, r = size - m - 3, m + 3, 3.2
        for ang in (0, 90, 180, 270):
            a = math.radians(ang)
            p.drawLine(QPointF(cx, cy),
                       QPointF(cx + r * math.cos(a), cy + r * math.sin(a)))
    p.end()
    return QIcon(pm)


class PageStrip(QListWidget):
    """Thumbnail list that reflows with the panel. On a side dock it is a GRID:
    thumbnails grow as you widen it, and once there is room they wrap to 2, then
    3 … columns (instead of one ever-bigger column). On top/bottom it is a
    single scrolling row whose height follows the dock."""

    PREF = 140          # preferred thumbnail cell width -> when to add a column

    def __init__(self):
        super(PageStrip, self).__init__()
        self._vertical = False
        self.setResizeMode(QListWidget.Adjust)

    def set_vertical(self, vertical):
        self._vertical = bool(vertical)
        self._resize_icons()

    def resizeEvent(self, ev):
        super(PageStrip, self).resizeEvent(ev)
        self._resize_icons()

    def _resize_icons(self):
        vp = self.viewport().size()
        if self._vertical:                       # grid: 1 -> 2 -> 3 … columns
            avail = max(60, vp.width() - 4)
            # add a column each time the cells would otherwise pass ~1.5*PREF,
            # so thumbnails grow a bit, then wrap, then grow again
            n = max(1, int(avail / self.PREF + 0.5))
            cellw = (avail - 2 * n) // n          # a little slack so n cells fit
            iconw = max(60, cellw - 8)
            iconh = int(iconw * 1.3)
            self.setGridSize(QSize(cellw, iconh + 22))
            self.setIconSize(QSize(iconw, iconh))
        else:                                    # single row, height = the dock
            self.setGridSize(QSize())            # no forced grid for the strip
            h = max(56, min(260, vp.height() - 16))
            self.setIconSize(QSize(int(h * 0.8), h))


class DiscordPresence:
    """Minimal Discord Rich Presence over the local IPC pipe (no dependency).

    Runs entirely in a daemon thread so a slow/unresponsive Discord can never
    freeze the UI, and silently does nothing if Discord isn't running or no
    application id is set."""

    def __init__(self, client_id, start_ts=None):
        self.client_id = str(client_id or "")
        self._pipe = None
        self._start = int(start_ts or time.time())
        self._details = "Labelling manga"
        self._state = ""
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread = None

    # public API (thread-safe) ------------------------------------------------
    def start(self):
        if not self.client_id or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def set_status(self, details, state):
        with self._lock:
            self._details = details or ""
            self._state = state or ""

    def stop(self):
        self._stop.set()
        self._close()

    # internals ---------------------------------------------------------------
    def _ipc_paths(self):
        if os.name == "nt":
            return [r"\\.\pipe\discord-ipc-%d" % i for i in range(10)]
        base = (os.environ.get("XDG_RUNTIME_DIR") or os.environ.get("TMPDIR")
                or "/tmp")
        return [os.path.join(base, "discord-ipc-%d" % i) for i in range(10)]

    def _connect(self):
        for path in self._ipc_paths():
            try:
                if os.name == "nt":
                    self._pipe = open(path, "r+b", buffering=0)
                else:
                    import socket
                    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    s.connect(path)
                    self._pipe = s
            except OSError:
                self._pipe = None
                continue
            try:
                self._send(0, {"v": 1, "client_id": self.client_id})
                self._recv()                 # READY / error
                return True
            except OSError:
                self._close()
        return False

    def _write(self, data):
        if os.name == "nt":
            self._pipe.write(data)
            self._pipe.flush()
        else:
            self._pipe.sendall(data)

    def _read(self, n):
        out = b""
        while len(out) < n:
            if os.name == "nt":
                chunk = self._pipe.read(n - len(out))
            else:
                chunk = self._pipe.recv(n - len(out))
            if not chunk:
                raise OSError("pipe closed")
            out += chunk
        return out

    def _send(self, op, payload):
        data = json.dumps(payload).encode("utf-8")
        self._write(struct.pack("<II", op, len(data)) + data)

    def _recv(self):
        op, ln = struct.unpack("<II", self._read(8))
        return self._read(ln) if ln else b""

    def _push(self):
        if not self._pipe:
            return False
        with self._lock:
            details, state = self._details, self._state
        activity = {"details": details[:128] or "Labelling manga",
                    "timestamps": {"start": self._start},
                    "assets": {"large_image": "icon",
                               "large_text": "BubblR Trainer"}}
        if state:
            activity["state"] = state[:128]
        try:
            self._send(1, {"cmd": "SET_ACTIVITY",
                           "args": {"pid": os.getpid(), "activity": activity},
                           "nonce": "%f" % time.time()})
            self._recv()
            return True
        except OSError:
            self._close()
            return False

    def _run(self):
        if not self._connect():
            return
        self._push()
        while not self._stop.wait(15):       # refresh / keep alive
            if not self._push() and not self._stop.is_set():
                if not self._connect():      # Discord went away; retry later
                    self._stop.wait(30)

    def _close(self):
        try:
            if self._pipe:
                self._pipe.close()
        except OSError:
            pass
        self._pipe = None


class NewsFetcher(QThread):
    """Fetch the repo's news.json in a background thread (no UI blocking); emits
    the parsed dict, or None on any failure (offline etc.)."""
    loaded = pyqtSignal(object)

    def run(self):
        data = None
        try:
            import urllib.request
            req = urllib.request.Request(
                NEWS_URL, headers={"User-Agent": "BubblR-Trainer"})
            with urllib.request.urlopen(req, timeout=6) as r:
                data = json.loads(r.read().decode("utf-8"))
        except Exception:                        # noqa: BLE001 (offline etc.)
            data = None
        self.loaded.emit(data)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class TrainerWindow(QMainWindow):
    def __init__(self):
        super(TrainerWindow, self).__init__()
        cfg = self._load_settings()
        self._lang = cfg.get("lang", "en")
        self._folder = cfg.get("folder", "")
        self._last_dir = cfg.get("last_dir", "")  # last place a dialog was used
        self._recent = [p for p in cfg.get("recent", []) if isinstance(p, str)]
        self._ai_dir = cfg.get("ai_dir", "")     # optional BubblR AI tool folder
        self._locked = cfg.get("locked", False)  # movable by default (Krita-style)
        self._wand_tol = int(cfg.get("wand_tol", 40))  # set in the Settings window
        self._val_split = max(0, min(50, int(cfg.get("val_split", 0))))  # % to val
        self._export_summary_on = bool(cfg.get("export_summary", True))
        self._news_enabled = bool(cfg.get("news_enabled", True))
        self._auto_order = bool(cfg.get("auto_order_on", False))
        self._rtl = bool(cfg.get("rtl", True))    # manga reading dir (Settings)
        self._center = bool(cfg.get("center_marker", True))  # in Settings now
        self._discord_enabled = bool(cfg.get("discord_enabled", False))
        self._discord_id = str(cfg.get("discord_client_id", ""))
        self._discord = None                      # DiscordPresence when running
        self._class_filter = None                 # None | "bubble" | "sfx"
        self._pages = []          # [{path, name, img: QImage, boxes: []}]
        self._cur = -1
        self._classes = self._sanitize_classes(cfg.get("classes"))
        _nk = cfg.get("new_kind", "bubble")
        keys = self._class_keys()
        self._new_kind = _nk if _nk in keys else keys[0]
        self._order_mode = False
        self._order_counter = 1
        self._undo = []           # snapshots of (page index, boxes, selection)
        self._redo = []
        self._clipboard_box = None  # copied box for paste / duplicate
        self._sel = set()           # selected box indices (multi-select)

        root = QWidget()
        lay = QVBoxLayout()
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)
        root.setLayout(lay)

        self.top_bar = QWidget()             # hidden on the start page
        top = QHBoxLayout(self.top_bar)
        top.setContentsMargins(0, 0, 0, 0)
        self.lbl_sort = QLabel(self._tr("sort_by"))
        top.addWidget(self.lbl_sort)
        self.sort_combo = QComboBox()
        for _k in ("name", "unlabeled", "unexported", "fewest", "most"):
            self.sort_combo.addItem(self._tr("sort_" + _k), _k)
        self.sort_combo.currentIndexChanged.connect(self._sort_pages)
        top.addWidget(self.sort_combo)
        self.next_todo_btn = QPushButton(self._tr("next_todo"))
        self.next_todo_btn.clicked.connect(self.on_next_todo)
        top.addWidget(self.next_todo_btn)
        top.addSpacing(12)
        # reading-order controls live up here now (next to Next unlabelled)
        self.order_btn = QPushButton(self._tr("set_order"))
        self.order_btn.setCheckable(True)
        self.order_btn.toggled.connect(self._on_order_toggle)
        top.addWidget(self.order_btn)
        self.auto_order_btn = QPushButton(self._tr("auto_order"))
        self.auto_order_btn.setToolTip(self._tr("auto_order_tip"))
        self.auto_order_btn.clicked.connect(self.on_auto_order)
        top.addWidget(self.auto_order_btn)
        top.addStretch(1)
        self.prev_btn = QPushButton(self._tr("prev"))
        self.prev_btn.clicked.connect(lambda: self._goto(self._cur - 1))
        top.addWidget(self.prev_btn)
        self.page_lbl = QLabel(self._tr("page_none"))
        self.page_lbl.setMinimumWidth(180)
        self.page_lbl.setAlignment(Qt.AlignCenter)
        top.addWidget(self.page_lbl)
        self.next_btn = QPushButton(self._tr("next"))
        self.next_btn.clicked.connect(lambda: self._goto(self._cur + 1))
        top.addWidget(self.next_btn)
        self.close_btn = QPushButton(self._tr("close_page"))
        self.close_btn.setToolTip(self._tr("close_page_tip"))
        self.close_btn.clicked.connect(self.on_close_page)
        top.addWidget(self.close_btn)
        self.close_all_btn = QPushButton(self._tr("close_all"))
        self.close_all_btn.setToolTip(self._tr("close_all_tip"))
        self.close_all_btn.clicked.connect(self.on_close_all)
        top.addWidget(self.close_all_btn)
        top.addSpacing(12)
        self.zoom_out_btn = QPushButton("−")
        self.zoom_out_btn.setFixedWidth(32)
        self.zoom_out_btn.clicked.connect(lambda: self.overlay.zoom_step(1 / 1.25))
        top.addWidget(self.zoom_out_btn)
        self.zoom_fit_btn = QPushButton(self._tr("fit"))
        self.zoom_fit_btn.setToolTip(self._tr("zoom_tip"))
        self.zoom_fit_btn.clicked.connect(lambda: self.overlay.fit())
        top.addWidget(self.zoom_fit_btn)
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedWidth(32)
        self.zoom_in_btn.clicked.connect(lambda: self.overlay.zoom_step(1.25))
        top.addWidget(self.zoom_in_btn)
        lay.addWidget(self.top_bar)

        self.overlay = BoxOverlay()
        self.overlay.boxAdded.connect(self._on_box_added)
        self.overlay.boxChanged.connect(self._on_box_changed)
        self.overlay.boxRemoved.connect(self._on_box_removed)
        self.overlay.boxClicked.connect(self._on_box_clicked)
        self.overlay.rubberSelect.connect(self._on_rubber_select)
        self.overlay.boxContextMenu.connect(self._on_box_context)
        self.overlay.canvasContextMenu.connect(self._on_canvas_context)
        # the canvas area shows either the editor (overlay) or, when nothing is
        # loaded, a Krita-style start page with recent images
        self.canvas_stack = QStackedWidget()
        self.canvas_stack.addWidget(self.overlay)          # index 0: editor
        self.canvas_stack.addWidget(self._build_start_page())  # index 1: start
        lay.addWidget(self.canvas_stack, 1)

        # --- Boxes list (moves into its own docker) ---
        self.box_list = QListWidget()
        self.box_list.setMinimumWidth(120)
        self.box_list.setToolTip(self._tr("boxes_tip"))
        self.box_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.box_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.box_list.itemSelectionChanged.connect(self._on_box_list_selection)
        self.box_list.model().rowsMoved.connect(self._on_boxes_reordered)
        self.box_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.box_list.customContextMenuRequested.connect(self._on_box_list_context)

        # --- Page thumbnails (docker; flow flips to vertical on a side dock) ---
        self.page_strip = PageStrip()
        self.page_strip.setViewMode(QListWidget.IconMode)
        self.page_strip.setFlow(QListWidget.LeftToRight)
        self.page_strip.setWrapping(False)
        self.page_strip.setMovement(QListWidget.Static)
        self.page_strip.setIconSize(QSize(88, 112))
        self.page_strip.setSpacing(4)
        self.page_strip.setToolTip(self._tr("strip_tip"))
        self.page_strip.currentRowChanged.connect(self._on_page_strip_row)
        self.page_strip.setContextMenuPolicy(Qt.CustomContextMenu)
        self.page_strip.customContextMenuRequested.connect(
            self._on_page_strip_context)

        # --- Marking tools: icon-only buttons (Krita-style select shapes) ---
        self._tg = QButtonGroup(self)
        self._tg.setExclusive(True)
        self.tool_btns = {}
        for _key in ("rect", "ellipse", "lasso", "wand"):
            btn = QToolButton()
            btn.setCheckable(True)
            btn.setIcon(make_tool_icon(_key))
            btn.setIconSize(QSize(24, 24))
            btn.setAutoRaise(True)
            btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
            btn.setToolTip(self._tr("tool_" + _key + "_hint"))
            btn.clicked.connect(lambda _c, k=_key: self._on_tool(k))
            btn.setStyleSheet(
                "QToolButton{padding:5px;} QToolButton:checked{background:#3daee9;}")
            self._tg.addButton(btn)
            self.tool_btns[_key] = btn
        self.tool_btns["rect"].setChecked(True)
        # wand tolerance is now set in the Settings window (keeps the Tools dock
        # small); apply the saved value to the overlay
        self.overlay.set_wand_tolerance(self._wand_tol)
        self.overlay.set_center_marker(self._center)   # toggled in Settings now
        self.overlay.set_edit_mode(True)   # a tool is always ready to draw

        self._build_docks()

        # compact view-option row: class filter, order path, auto order
        self.opt_bar = QWidget()             # hidden on the start page
        opt_row = QHBoxLayout(self.opt_bar)
        opt_row.setContentsMargins(0, 0, 0, 0)
        self.lbl_filter = QLabel(self._tr("show"))
        opt_row.addWidget(self.lbl_filter)
        self.filter_combo = QComboBox()
        self._rebuild_filter_combo()         # All + one entry per class
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        opt_row.addWidget(self.filter_combo)
        opt_row.addSpacing(12)
        self.path_chk = QCheckBox(self._tr("order_path"))
        self.path_chk.setChecked(False)
        self.path_chk.setToolTip(self._tr("order_path_tip"))
        self.path_chk.toggled.connect(self.overlay.set_order_path)
        opt_row.addWidget(self.path_chk)
        self.auto_chk = QCheckBox(self._tr("auto_order_live"))
        self.auto_chk.setToolTip(self._tr("auto_order_live_tip"))
        self.auto_chk.setChecked(self._auto_order)     # set before connecting
        self.auto_chk.toggled.connect(self.set_auto_order)
        opt_row.addWidget(self.auto_chk)
        opt_row.addStretch(1)
        lay.addWidget(self.opt_bar)

        # Undo/redo, delete, clear, class and export are all reachable from the
        # Edit / File menus (and the right-click menu); no button clutter here.
        self.setCentralWidget(root)

        # one thin status bar carries the message (left) + counts + version
        # (right), instead of several stacked labels under the canvas
        sb = self.statusBar()
        self.status = QLabel(self._tr("ready"))
        sb.addWidget(self.status, 1)
        self.lbl_counts = QLabel("")
        self.lbl_counts.setStyleSheet("color: #b0b3b8;")
        sb.addPermanentWidget(self.lbl_counts)
        ver = QLabel("v" + VERSION)
        ver.setStyleSheet("color: gray;")
        sb.addPermanentWidget(ver)
        self.setWindowTitle(self._tr("title") + " v" + VERSION)
        self.resize(760, 720)
        geo = cfg.get("geo")
        if geo:                              # restore last window size/position
            try:
                self.restoreGeometry(bytes.fromhex(geo))
            except Exception:                # noqa: BLE001
                pass
        # Restore the docker arrangement + sizes on the first show (not here):
        # in the constructor the layout isn't active yet, so restoreState gets
        # the dock POSITIONS but not their SIZES right. Deferring to showEvent
        # makes the panel widths/heights persist correctly across runs.
        self._pending_dockstate = cfg.get("dockstate")
        self._pending_dock_sizes = cfg.get("dock_sizes")

        # menu bar (also carries the keyboard shortcuts); Esc stays a shortcut
        self._build_menu()
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self._deselect)
        # class shortcuts: 1..9 pick the Nth class; B/S map to the first two
        # (so the manga bubble/sfx muscle memory still works)
        for _n in range(9):
            QShortcut(QKeySequence(str(_n + 1)), self,
                      activated=lambda i=_n: self._kbd_set_class_index(i))
        QShortcut(QKeySequence("B"), self,
                  activated=lambda: self._kbd_set_class_index(0))
        QShortcut(QKeySequence("S"), self,
                  activated=lambda: self._kbd_set_class_index(1))
        self._update_undo_buttons()

        # auto-save the session every minute for crash recovery
        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_timer.start(60000)

        self.setAcceptDrops(True)            # drop images/folders/projects to load
        self._apply_classes()                # push classes to overlay + filter
        self._refresh()
        self._start_discord()                # show "in BubblR Trainer" if enabled
        self._start_news()                   # fetch news / check for updates

    # -- settings / i18n --
    def _tr(self, key):
        table = LANG.get(self._lang, LANG["en"])
        return table.get(key, LANG["en"].get(key, key))

    def _load_settings(self):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}

    def _save_settings(self):
        data = {"lang": self._lang, "folder": self._folder,
                "ai_dir": self._ai_dir, "locked": self._locked,
                "wand_tol": self._wand_tol, "auto_order_on": self._auto_order,
                "rtl": self._rtl, "new_kind": self._new_kind,
                "center_marker": self._center, "last_dir": self._last_dir,
                "discord_enabled": self._discord_enabled,
                "discord_client_id": self._discord_id,
                "recent": self._recent[:40], "classes": self._classes,
                "val_split": self._val_split,
                "export_summary": self._export_summary_on,
                "news_enabled": self._news_enabled}
        try:
            data["geo"] = bytes(self.saveGeometry()).hex()
            # Only capture the docker layout while the EDITOR is showing AND the
            # saved layout has already been restored. On the start page the docks
            # are hidden (saving that hides them next time), and before the
            # restore runs they're at default size (saving that would clobber the
            # good layout). Keep the last good editor layout in those cases.
            if self._pages and getattr(self, "_state_restored", False):
                data["dockstate"] = bytes(self.saveState()).hex()
                sizes = {}
                for d in getattr(self, "_docks", []):
                    sizes[d.objectName()] = {"w": d.width(), "h": d.height(),
                                             "floating": d.isFloating()}
                data["dock_sizes"] = sizes
                self._pending_dockstate = data["dockstate"]
                self._pending_dock_sizes = sizes
            else:
                if getattr(self, "_pending_dockstate", None):
                    data["dockstate"] = self._pending_dockstate
                if getattr(self, "_pending_dock_sizes", None):
                    data["dock_sizes"] = self._pending_dock_sizes
        except Exception:                    # noqa: BLE001
            pass
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
        except Exception:
            pass

    # -- dockable panels (Tools / Boxes / Pages), Krita-style ----------------
    def _build_docks(self):
        """Wrap the tools, box list and thumbnail strip in movable dockers."""
        # Tools docker: icon-only marking tools (reflow). Wand tolerance lives
        # in the Settings window so this panel can shrink to just the icons.
        tools_w = QWidget()
        tv = QVBoxLayout(tools_w)
        tv.setContentsMargins(4, 4, 4, 4)
        flow_host = QWidget()
        self._tools_flow = FlowLayout(flow_host, margin=0, spacing=4)
        for k in ("rect", "ellipse", "lasso", "wand"):
            self._tools_flow.addWidget(self.tool_btns[k])
        tv.addWidget(flow_host)
        tv.addStretch(1)
        self.tools_dock = QDockWidget(self._tr("dock_tools"), self)
        self.tools_dock.setObjectName("toolsDock")
        self.tools_dock.setWidget(tools_w)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.tools_dock)

        # Boxes docker
        self.boxes_dock = QDockWidget(self._tr("dock_boxes"), self)
        self.boxes_dock.setObjectName("boxesDock")
        self.boxes_dock.setWidget(self.box_list)
        self.addDockWidget(Qt.RightDockWidgetArea, self.boxes_dock)

        # Pages (thumbnails) docker — flow adapts to which side it sits on
        self.thumbs_dock = QDockWidget(self._tr("dock_pages"), self)
        self.thumbs_dock.setObjectName("thumbsDock")
        self.thumbs_dock.setWidget(self.page_strip)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.thumbs_dock)
        self.thumbs_dock.dockLocationChanged.connect(self._apply_thumbs_flow)

        self._docks = [self.tools_dock, self.boxes_dock, self.thumbs_dock]
        for d in self._docks:
            d.setAllowedAreas(Qt.AllDockWidgetAreas)   # left, right, top, bottom
        # when two panels stack in one area, show their tabs at the top
        self.setTabPosition(Qt.AllDockWidgetAreas, QTabWidget.North)
        # let the left/right docks own the full height (corners), like Krita
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.TopRightCorner, Qt.RightDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)
        self._apply_thumbs_flow(Qt.BottomDockWidgetArea)
        self._apply_dock_lock()

    def _apply_thumbs_flow(self, area):
        """Thumbnails run in a row on the top/bottom, in a column on the sides.
        No maximum size, so you can enlarge the dock freely and the thumbnails
        grow with it (PageStrip scales its icons to the panel)."""
        vertical = area in (Qt.LeftDockWidgetArea, Qt.RightDockWidgetArea)
        s = self.page_strip
        if vertical:
            s.setFlow(QListWidget.LeftToRight)   # rows that wrap -> a grid
            s.setWrapping(True)
            s.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            # always-on keeps the viewport width stable so the column count
            # doesn't flip-flop when the scrollbar appears/disappears
            s.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            s.setMinimumHeight(0)
            s.setMinimumWidth(72)
        else:
            s.setFlow(QListWidget.LeftToRight)   # one horizontal strip
            s.setWrapping(False)
            s.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            s.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            s.setMinimumWidth(0)
            s.setMinimumHeight(80)
        s.set_vertical(vertical)

    def _apply_dock_lock(self):
        """Locked = titles stay but panels can't be dragged/floated; unlocked =
        movable & floatable (Krita/TypeR-style)."""
        for d in getattr(self, "_docks", []):
            if self._locked:
                d.setFeatures(QDockWidget.NoDockWidgetFeatures)
            else:
                d.setFeatures(QDockWidget.DockWidgetMovable
                              | QDockWidget.DockWidgetFloatable)

    def set_layout_locked(self, locked):
        self._locked = bool(locked)
        self._apply_dock_lock()
        self._save_settings()

    # -- classes (configurable) ----------------------------------------------
    @staticmethod
    def _sanitize_classes(raw):
        """Return a valid ordered class list (key/label/color), else the manga
        default. Keys are made unique and non-empty."""
        out, seen = [], set()
        for c in (raw or []):
            if not isinstance(c, dict):
                continue
            key = str(c.get("key") or c.get("label") or "").strip()
            if not key or key in seen:
                continue
            col = c.get("color")
            if not (isinstance(col, (list, tuple)) and len(col) == 3):
                col = CLASS_PALETTE[len(out) % len(CLASS_PALETTE)]
            out.append({"key": key, "label": str(c.get("label") or key),
                        "color": [int(col[0]), int(col[1]), int(col[2])]})
            seen.add(key)
        if not out:
            out = [dict(c) for c in DEFAULT_CLASSES]
        return out

    @staticmethod
    def _parse_class_names(path):
        """Read class names from a classes.txt (one per line) or a YOLO
        data.yaml ('names:' as a list or an index->name map). Returns [] on
        failure."""
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            return []
        if os.path.splitext(path)[1].lower() not in (".yaml", ".yml"):
            return [ln.strip() for ln in text.splitlines() if ln.strip()]
        lines = text.splitlines()
        for i, ln in enumerate(lines):
            if not ln.strip().startswith("names:"):
                continue
            rest = ln.strip()[len("names:"):].strip()
            if rest.startswith("["):                 # inline list
                inner = rest.strip("[]")
                return [p.strip().strip("'\"") for p in inner.split(",")
                        if p.strip()]
            entries, seq = [], 0                      # block list or map
            for ln2 in lines[i + 1:]:
                if not ln2.strip():
                    continue
                t = ln2.strip()
                if t.startswith("- "):                # sequence item (any indent)
                    entries.append((seq, t[2:].strip().strip("'\"")))
                    seq += 1
                    continue
                if not ln2[:1].isspace():             # next top-level key -> stop
                    break
                if ":" in t:
                    k, v = t.split(":", 1)
                    v = v.strip().strip("'\"")
                    try:
                        order = int(k.strip())
                    except ValueError:
                        order = seq
                    if v:
                        entries.append((order, v))
                seq += 1
            entries.sort(key=lambda e: e[0])
            return [v for _o, v in entries]
        return []

    def _class_keys(self):
        return [c["key"] for c in self._classes]

    def _class_index_map(self):
        return {c["key"]: i for i, c in enumerate(self._classes)}

    def _class_label(self, key):
        for c in self._classes:
            if c["key"] == key:
                return c["label"]
        return key

    def _class_color(self, key):
        for c in self._classes:
            if c["key"] == key:
                return tuple(c["color"])
        return (150, 150, 150)

    def _apply_classes(self):
        """Push the current class set to the overlay, filter combo and new-box
        default, then repaint."""
        colors = {c["key"]: (QColor(*c["color"]),
                             (c["label"][:1] or "?").upper())
                  for c in self._classes}
        self.overlay.set_class_colors(colors)
        if self._new_kind not in self._class_keys():
            self._new_kind = self._class_keys()[0]
        # drop a filter that no longer exists
        if self._class_filter and self._class_filter not in self._class_keys():
            self._class_filter = None
            self.overlay.set_kind_filter(None)
        self._rebuild_filter_combo()
        self._rebuild_class_menu()
        self._refresh()

    def _rebuild_class_menu(self):
        m = getattr(self, "_class_menu", None)
        if m is None:
            return
        m.clear()
        for i, c in enumerate(self._classes):
            label = c["label"] + ("  (%d)" % (i + 1) if i < 9 else "")
            m.addAction(label,
                        lambda _c=False, k=c["key"]: self._kbd_set_kind(k))

    def _kbd_set_class_index(self, n):
        keys = self._class_keys()
        if 0 <= n < len(keys):
            self._kbd_set_kind(keys[n])

    def _rebuild_filter_combo(self):
        if not hasattr(self, "filter_combo"):
            return
        cb = self.filter_combo
        cb.blockSignals(True)
        cb.clear()
        cb.addItem(self._tr("show_all"), "all")
        for c in self._classes:
            cb.addItem(self._tr("show_only").format(name=c["label"]), c["key"])
        # restore current filter selection
        want = self._class_filter or "all"
        idx = max(0, cb.findData(want))
        cb.setCurrentIndex(idx)
        cb.blockSignals(False)

    # -- class filter + live auto-order ---------------------------------------
    def _on_filter_changed(self):
        key = self.filter_combo.currentData() or "all"
        self._class_filter = None if key == "all" else key
        self.overlay.set_kind_filter(self._class_filter)
        self._current = -1              # drop selection (may now be hidden)
        self._sel = set()
        self._refresh()

    def set_auto_order(self, on):
        self._auto_order = bool(on)
        self._save_settings()
        if on:
            self._maybe_auto_order()
            self._refresh()

    def _maybe_auto_order(self):
        """Re-number the reading order after an edit, if the live toggle is on."""
        if not self._auto_order:
            return
        pg = self._page()
        if pg and pg["boxes"]:
            auto_order(pg["boxes"], rtl=self._rtl)

    # -- start page (Krita-style welcome with recent images) -----------------
    def _build_start_page(self):
        page = QWidget()
        page.setObjectName("startPage")
        outer = QHBoxLayout(page)
        outer.setContentsMargins(34, 26, 34, 26)
        outer.setSpacing(28)

        # --- left "Start" column: logo, title, stacked action buttons ---
        left = QVBoxLayout()
        left.setSpacing(6)
        self.start_logo = QLabel()
        pm = app_icon().pixmap(72, 72)
        if not pm.isNull():
            self.start_logo.setPixmap(pm)
        left.addWidget(self.start_logo)
        self.start_title = QLabel("BubblR Trainer")
        self.start_title.setStyleSheet("font-size: 24px; font-weight: bold;")
        left.addWidget(self.start_title)
        self.start_sub = QLabel(self._tr("start_sub"))
        self.start_sub.setStyleSheet("color: gray;")
        self.start_sub.setWordWrap(True)
        left.addWidget(self.start_sub)
        left.addSpacing(16)
        self.start_heading = QLabel(self._tr("start_heading"))
        self.start_heading.setStyleSheet("font-weight: bold; color: gray;")
        left.addWidget(self.start_heading)

        specs = [("start_load", self.on_load_images),
                 ("start_folder", self.on_load_folder),
                 ("start_open", self.on_load_project),
                 ("start_rank", self.on_rank_load)]
        self._start_btns = []
        for key, fn in specs:                # stacked vertically, Krita-style
            b = QPushButton(self._tr(key))
            b.setMinimumHeight(38)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _c=False, f=fn: f())
            left.addWidget(b)
            self._start_btns.append((b, key))
        left.addStretch(1)
        left_host = QWidget()
        left_host.setLayout(left)
        left_host.setFixedWidth(230)
        outer.addWidget(left_host)

        # --- right side: "Recent images" + Clear link, then the grid ---
        right = QVBoxLayout()
        right.setSpacing(8)
        head = QHBoxLayout()
        self.start_recent_lbl = QLabel(self._tr("start_recent"))
        self.start_recent_lbl.setStyleSheet("font-weight: bold;")
        head.addWidget(self.start_recent_lbl)
        self.start_clear = QPushButton(self._tr("start_clear"))
        self.start_clear.setFlat(True)
        self.start_clear.setCursor(Qt.PointingHandCursor)
        self.start_clear.setStyleSheet(
            "QPushButton{border:none;color:#3daee9;} "
            "QPushButton:hover{text-decoration:underline;}")
        self.start_clear.clicked.connect(self._on_clear_recent)
        head.addWidget(self.start_clear)
        head.addStretch(1)
        right.addLayout(head)

        self.recent_list = QListWidget()
        self.recent_list.setViewMode(QListWidget.IconMode)
        self.recent_list.setResizeMode(QListWidget.Adjust)
        self.recent_list.setMovement(QListWidget.Static)
        self.recent_list.setWrapping(True)
        self.recent_list.setSpacing(10)
        self.recent_list.setIconSize(QSize(140, 180))
        self.recent_list.setGridSize(QSize(160, 216))
        self.recent_list.setWordWrap(True)
        self.recent_list.setFrameShape(QFrame.NoFrame)
        self.recent_list.itemClicked.connect(self._on_recent_clicked)
        right.addWidget(self.recent_list, 1)
        outer.addLayout(right, 1)

        # --- News column (fetched from the repo; update banner on top) ---
        news_col = QVBoxLayout()
        news_col.setSpacing(8)
        self.start_news_lbl = QLabel(self._tr("start_news"))
        self.start_news_lbl.setStyleSheet("font-weight: bold;")
        news_col.addWidget(self.start_news_lbl)
        self.news_update = QLabel()
        self.news_update.setWordWrap(True)
        self.news_update.setOpenExternalLinks(True)
        self.news_update.setStyleSheet(
            "background:#2f6f3f;color:#eaffea;border-radius:5px;padding:7px;")
        self.news_update.setVisible(False)
        news_col.addWidget(self.news_update)
        self.news_view = QTextBrowser()
        self.news_view.setOpenExternalLinks(True)
        self.news_view.setFrameShape(QFrame.NoFrame)
        self.news_view.setStyleSheet("background:transparent;")
        news_col.addWidget(self.news_view, 1)
        self.news_host = QWidget()
        self.news_host.setLayout(news_col)
        self.news_host.setFixedWidth(300)
        outer.addWidget(self.news_host)
        return page

    def _on_clear_recent(self):
        self._recent = []
        self._save_settings()
        self._rebuild_recent()

    # -- news / update check --------------------------------------------------
    def _start_news(self):
        if not hasattr(self, "news_host"):
            return
        self.news_host.setVisible(self._news_enabled)
        if not self._news_enabled:
            return
        self.news_view.setHtml(
            "<p style='color:gray'>%s</p>" % self._tr("news_loading"))
        self._news_thread = NewsFetcher(self)
        self._news_thread.loaded.connect(self._on_news)
        self._news_thread.start()

    def _on_news(self, data):
        if not data:
            self.news_view.setHtml(
                "<p style='color:gray'>%s</p>" % self._tr("news_offline"))
            return
        latest = data.get("latest_version")
        if latest and _ver_tuple(latest) > _ver_tuple(VERSION):
            url = data.get("url") or RELEASES_URL
            self.news_update.setText(
                "%s &nbsp; <a href='%s' style='color:#bfffcf'>%s</a>" % (
                    self._tr("news_update").format(v=latest), url,
                    self._tr("news_download")))
            self.news_update.setVisible(True)
        else:
            self.news_update.setVisible(False)
        items = data.get("items") or []
        if not items:
            self.news_view.setHtml(
                "<p style='color:gray'>%s</p>" % self._tr("news_none"))
            return
        parts = []
        for it in items[:25]:
            title = it.get("title", "")
            url = it.get("url")
            head = ("<a href='%s' style='color:#6cc0ff;text-decoration:none'>"
                    "%s</a>" % (url, title)) if url else title
            body = ("<br>" + it["text"]) if it.get("text") else ""
            parts.append(
                "<p style='margin:0 0 12px 0'><b>%s</b>%s<br>"
                "<span style='color:gray;font-size:11px'>%s</span></p>"
                % (head, body, it.get("date", "")))
        self.news_view.setHtml(
            "<div style='color:#dfe3e7'>" + "".join(parts) + "</div>")

    def set_news_enabled(self, on):
        self._news_enabled = bool(on)
        self._save_settings()
        self._start_news()

    def _on_recent_clicked(self, item):
        path = item.data(Qt.UserRole)
        if path and os.path.exists(path):
            self.add_image_paths([path])
        elif path:
            self._status(self._tr("recent_missing"), error=True)
            self._recent = [p for p in self._recent if p != path]
            self._rebuild_recent()

    def _remember_recent(self, paths):
        """Push loaded image paths to the front of the recent list (dedup)."""
        for p in reversed(list(paths)):
            ap = os.path.abspath(p)
            self._recent = [q for q in self._recent if q != ap]
            self._recent.insert(0, ap)
        self._recent = self._recent[:40]
        self._save_settings()

    def _rebuild_recent(self):
        if not hasattr(self, "recent_list"):
            return
        lw = self.recent_list
        lw.clear()
        for p in self._recent[:40]:
            if not os.path.exists(p):
                continue
            img = QImage(p)
            if img.isNull():
                continue
            pm = QPixmap.fromImage(img.scaled(
                QSize(140, 180), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            it = QListWidgetItem(QIcon(pm), os.path.basename(p))
            it.setToolTip(p)
            it.setTextAlignment(Qt.AlignHCenter | Qt.AlignBottom)
            it.setData(Qt.UserRole, p)
            lw.addItem(it)

    def _sync_start_page(self):
        """Show the full-screen start page (no docks / bars) when nothing is
        loaded, else the editor with its panels."""
        if not hasattr(self, "canvas_stack"):
            return
        start = not self._pages
        if start:
            self._rebuild_recent()
        self.canvas_stack.setCurrentIndex(1 if start else 0)
        # hide the editor chrome on the start page, like Krita's welcome screen
        self.top_bar.setVisible(not start)
        self.opt_bar.setVisible(not start)
        for d in getattr(self, "_docks", []):
            d.setVisible(not start)
        if not start and not getattr(self, "_state_restored", False):
            # defer to the next tick so the editor layout is active before we
            # restoreState/resizeDocks (doing it synchronously here does not
            # stick and the docks fall back to their default sizes)
            QTimer.singleShot(0, self._restore_layout_once)

    def _unexported_count(self):
        """Pages that have boxes but have not been exported into the dataset."""
        return sum(1 for p in self._pages
                   if p["boxes"] and not p.get("exported"))

    # -- Discord Rich Presence ------------------------------------------------
    def _effective_discord_id(self):
        """The id to use: the user's own if set, else the built-in default."""
        return (self._discord_id.strip() or DEFAULT_DISCORD_CLIENT_ID).strip()

    def _toggle_discord(self, on):
        """Quick on/off from the View menu (mirrors the Settings checkbox)."""
        self._discord_enabled = bool(on)
        self._save_settings()
        if on and not self._effective_discord_id():
            self._status(self._tr("discord_need_id"), error=True)
        self._start_discord()

    def _start_discord(self):
        """(Re)start or stop the Discord presence to match the settings."""
        if self._discord is not None:
            self._discord.stop()
            self._discord = None
        cid = self._effective_discord_id()
        if self._discord_enabled and cid:
            self._discord = DiscordPresence(cid)
            self._discord.start()
            self._update_discord()
        # keep the View-menu toggle in sync with the current state
        if hasattr(self, "discord_action"):
            self.discord_action.blockSignals(True)
            self.discord_action.setChecked(self._discord_enabled)
            self.discord_action.blockSignals(False)

    def _update_discord(self):
        """Push the current page / progress to Discord (cheap; the presence
        thread only sends it every ~15s)."""
        if not self._discord:
            return
        n = len(self._pages)
        if n == 0:
            self._discord.set_status("Idle", "No pages loaded")
            return
        done = sum(1 for p in self._pages if p["boxes"])
        if 0 <= self._cur < n:
            details = "Labelling page %d/%d" % (self._cur + 1, n)
        else:
            details = "Labelling manga"
        self._discord.set_status(details, "%d/%d pages done" % (done, n))

    # -- drag & drop: images / folders / a project .json onto the window -------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        exts = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
        images, project = [], None
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if not p:
                continue
            if os.path.isdir(p):
                try:
                    for f in sorted(os.listdir(p)):
                        if f.lower().endswith(exts):
                            images.append(os.path.join(p, f))
                except OSError:
                    pass
            elif p.lower().endswith(exts):
                images.append(p)
            elif p.lower().endswith(".json") and project is None:
                project = p
        if images:
            self.add_image_paths(images)
            self._remember_dir(os.path.dirname(images[0]))
        elif project:
            pages = self._load_pages_from(project)
            if pages:
                self._pages = pages
                self._cur = -1
                self._reset_history()
                self._goto(0)
                self._remember_dir(os.path.dirname(project))
                self._status(self._tr("loaded_proj").format(n=len(pages)))
        event.acceptProposedAction()

    def showEvent(self, event):
        super(TrainerWindow, self).showEvent(event)
        self._restore_layout_once()

    def _restore_layout_once(self):
        """Restore the saved docker layout + sizes exactly once, and only when
        the window is visible AND the docks are shown (they're hidden on the
        start page, where restoring would not stick)."""
        if getattr(self, "_state_restored", False):
            return
        if not self.isVisible() or not self._pages:
            return
        self._state_restored = True
        ds = getattr(self, "_pending_dockstate", None)
        if ds:
            try:
                self.restoreState(bytes.fromhex(ds))
                self._apply_thumbs_flow(self.dockWidgetArea(self.thumbs_dock))
                self._apply_dock_lock()
            except Exception:                # noqa: BLE001
                pass
        for d in getattr(self, "_docks", []):    # never leave them hidden here
            d.setVisible(True)
        # restoreState is unreliable for dock SIZES, so force them, and again a
        # few times as the layout settles (the editor was just switched in)
        self._restore_dock_sizes()
        for delay in (0, 30, 120):
            QTimer.singleShot(delay, self._restore_dock_sizes)

    def _restore_dock_sizes(self):
        """Force each dock back to the width/height it had last session."""
        sizes = getattr(self, "_pending_dock_sizes", None)
        if not sizes:
            return
        hor_d, hor_w, ver_d, ver_h = [], [], [], []
        for d in getattr(self, "_docks", []):
            info = sizes.get(d.objectName())
            if not info or d.isFloating():
                continue
            area = self.dockWidgetArea(d)
            if area in (Qt.LeftDockWidgetArea, Qt.RightDockWidgetArea):
                hor_d.append(d)
                hor_w.append(int(info.get("w") or d.width()))
            elif area in (Qt.TopDockWidgetArea, Qt.BottomDockWidgetArea):
                ver_d.append(d)
                ver_h.append(int(info.get("h") or d.height()))
        if hor_d:
            self.resizeDocks(hor_d, hor_w, Qt.Horizontal)
        if ver_d:
            self.resizeDocks(ver_d, ver_h, Qt.Vertical)

    def closeEvent(self, event):
        n = self._unexported_count()
        if n and not self._confirm_discard(
                self._tr("confirm_quit_unexported").format(n=n),
                title=self._tr("confirm_quit_title")):
            event.ignore()                   # let the user export/save first
            return
        self._save_settings()                # remember window size/position
        if self._discord:                    # drop the Discord presence
            self._discord.stop()
        try:                                 # clean exit -> no crash recovery
            os.remove(RECOVERY_FILE)
        except OSError:
            pass
        super(TrainerWindow, self).closeEvent(event)

    # -- keyboard helpers --
    def _kbd_set_kind(self, kind):
        self._set_kind_buttons(kind)
        self._set_kind(kind)                 # relabels the selected box + default

    def _deselect(self):
        if self._current != -1 or self._sel:
            self._current = -1
            self._sel = set()
            self._refresh()

    def _on_rubber_select(self, x, y, w, h):
        """A drag-rectangle in view mode selects every box it overlaps; a click
        on empty space (tiny rectangle) clears the selection."""
        pg = self._page()
        if not pg:
            return
        if w < 3 and h < 3:
            self._deselect()
            return
        rx1, ry1 = x + w, y + h
        sel = {i for i, b in enumerate(pg["boxes"])
               if b["x"] < rx1 and b["x"] + b["w"] > x
               and b["y"] < ry1 and b["y"] + b["h"] > y}
        self._sel = sel
        self._current = max(sel) if sel else -1
        if 0 <= self._current < len(pg["boxes"]):
            k = pg["boxes"][self._current].get("kind", "bubble")
            self._set_kind_buttons(k)
            self._new_kind = k
        self._refresh()

    def on_select_all(self):
        pg = self._page()
        if pg and pg["boxes"]:
            self._sel = set(range(len(pg["boxes"])))
            self._current = len(pg["boxes"]) - 1
            self._refresh()

    def on_zoom_selection(self):
        """Zoom the view onto the selected box(es); no selection -> fit page."""
        pg = self._page()
        if not pg or not self._sel:
            self.overlay.fit()
            return
        boxes = [pg["boxes"][i] for i in self._sel if 0 <= i < len(pg["boxes"])]
        if not boxes:
            self.overlay.fit()
            return
        x0 = min(b["x"] for b in boxes)
        y0 = min(b["y"] for b in boxes)
        x1 = max(b["x"] + b["w"] for b in boxes)
        y1 = max(b["y"] + b["h"] for b in boxes)
        self.overlay.zoom_to_rect(x0, y0, x1 - x0, y1 - y0)

    # -- right-click context menu on a box / box-list row --
    def _on_box_context(self, idx, gpos):
        pg = self._page()
        if not pg or not (0 <= idx < len(pg["boxes"])):
            return
        if idx not in self._sel:             # right-click outside the selection
            self._current = idx              #   -> select just this box first
            self._sel = {idx}
            k = pg["boxes"][idx].get("kind", "bubble")
            self._set_kind_buttons(k)
            self._new_kind = k
            self._refresh()
        self._show_box_menu(gpos)

    def _on_box_list_context(self, pos):
        it = self.box_list.itemAt(pos)
        if it is None:
            return
        if self.box_list.row(it) not in self._sel:
            self.box_list.clearSelection()   # selecting fires the sel handler
            it.setSelected(True)
        self._show_box_menu(self.box_list.viewport().mapToGlobal(pos))

    def _on_canvas_context(self, docx, docy, gpos):
        t = self._tr
        menu = QMenu(self)
        act = menu.addAction(t("mi_paste"), lambda: self.on_paste_at(docx, docy))
        act.setEnabled(self._clipboard_box is not None)
        menu.addSeparator()
        menu.addAction(t("mi_select_all"), lambda: self.on_select_all())
        menu.addAction(t("mi_deselect"), lambda: self._deselect())
        menu.addAction(t("mi_fit"), lambda: self.overlay.fit())
        menu.exec_(gpos)

    def on_paste_at(self, docx, docy):
        """Paste the clipboard box centred at the given doc position."""
        b = self._clipboard_box
        if not b or not self._page():
            return
        dx = (docx - b["w"] / 2.0) - b["x"]
        dy = (docy - b["h"] / 2.0) - b["y"]
        self._place_box(b, dx, dy)
        self._status(self._tr("pasted"))

    def _show_box_menu(self, gpos):
        if not self._sel:
            return
        t = self._tr
        menu = QMenu(self)
        menu.addAction(t("mi_del"), lambda: self.on_delete())
        menu.addAction(t("mi_dup"), lambda: self.on_duplicate_box())
        menu.addAction(t("fit_box"), lambda: self.on_fit_box())
        menu.addSeparator()
        sub = menu.addMenu(t("mi_set_class"))
        for i, c in enumerate(self._classes):
            label = c["label"] + ("  (%d)" % (i + 1) if i < 9 else "")
            sub.addAction(label,
                          lambda _c=False, k=c["key"]: self._kbd_set_kind(k))
        menu.exec_(gpos)

    def _show_shortcuts(self):
        QMessageBox.information(self, self._tr("sh_title"), self._tr("sh_text"))

    def _show_about(self):
        QMessageBox.about(
            self, self._tr("mi_about"),
            "BubblR Trainer v%s\n\n%s" % (VERSION, self._tr("about_text")))

    # -- menu bar --
    def _build_menu(self):
        self._menu_titles = []               # (menu, key) for retranslation
        self._menu_actions = []              # (action, key)
        spec = [
            ("m_file", [
                ("mi_load", self.on_load_images, None),
                ("mi_load_folder", self.on_load_folder, None),
                ("mi_rank", self.on_rank_load, None),
                None,
                ("mi_open", self.on_load_project, "Ctrl+O"),
                ("mi_save", self.on_save_project, "Ctrl+S"),
                None,
                ("mi_exp_page", lambda: self.on_export(False), "Ctrl+E"),
                ("mi_exp_all", lambda: self.on_export(True), "Ctrl+Shift+E"),
                None,
                ("mi_exit", self.close, "Ctrl+Q"),
            ]),
            ("m_edit", [
                ("mi_undo", self.undo, "Ctrl+Z"),
                ("mi_redo", self.redo, ["Ctrl+Y", "Ctrl+Shift+Z"]),
                None,
                ("mi_copy", self.on_copy_box, "Ctrl+C"),
                ("mi_paste", self.on_paste_box, "Ctrl+V"),
                ("mi_dup", self.on_duplicate_box, "Ctrl+D"),
                ("mi_del", self.on_delete, ["Del", "Backspace"]),
                ("fit_box", self.on_fit_box, "F"),
                ("mi_select_all", self.on_select_all, "Ctrl+A"),
                None,
                ("mi_set_class", "__setclass__", None),
                None,
                ("mi_clear_order", self.on_clear_order, None),
                ("clear", self.on_clear, None),
            ]),
            ("m_page", [
                ("mi_prev", lambda: self._goto(self._cur - 1), "["),
                ("mi_next", lambda: self._goto(self._cur + 1), "]"),
                ("mi_next_todo", self.on_next_todo, None),
                ("mi_next_unexported", self.on_next_unexported, None),
                None,
                ("mi_close", self.on_close_page, "Ctrl+W"),
                ("mi_close_all", self.on_close_all, None),
            ]),
            ("m_view", [
                ("mi_zoom_in", lambda: self.overlay.zoom_step(1.25), "Ctrl++"),
                ("mi_zoom_out", lambda: self.overlay.zoom_step(1 / 1.25), "Ctrl+-"),
                ("mi_zoom_sel", self.on_zoom_selection, "Z"),
                ("mi_fit", lambda: self.overlay.fit(), None),
                None,
                ("mi_dockers", "__dockers__", None),
                ("mi_lock_panels", "__lock__", None),
                ("mi_discord", "__discord__", None),
            ]),
            ("m_settings", self._open_settings),   # opens the Settings window
            ("m_help", [
                ("mi_shortcuts", self._show_shortcuts, "F1"),
                ("mi_about", self._show_about, None),
            ]),
        ]
        mb = self.menuBar()
        for mkey, items in spec:
            if callable(items):            # a menu-bar entry that opens a dialog
                act = mb.addAction(self._tr(mkey))
                act.triggered.connect(lambda _c=False, f=items: f())
                self._menu_actions.append((act, mkey))
                continue
            menu = mb.addMenu(self._tr(mkey))
            self._menu_titles.append((menu, mkey))
            for item in items:
                if item is None:
                    menu.addSeparator()
                    continue
                akey, fn, sc = item
                if fn == "__dockers__":           # submenu: show/hide each dock
                    sub = menu.addMenu(self._tr(akey))
                    self._menu_titles.append((sub, akey))
                    for d in getattr(self, "_docks", []):
                        sub.addAction(d.toggleViewAction())
                    continue
                if fn == "__setclass__":          # submenu: set class of selection
                    self._class_menu = menu.addMenu(self._tr(akey))
                    self._menu_titles.append((self._class_menu, akey))
                    self._rebuild_class_menu()
                    continue
                if fn == "__lock__":              # checkable "Lock panels" toggle
                    act = menu.addAction(self._tr(akey))
                    act.setCheckable(True)
                    act.setChecked(self._locked)
                    act.toggled.connect(self.set_layout_locked)
                    self.lock_action = act
                    self._menu_actions.append((act, akey))
                    continue
                if fn == "__discord__":           # checkable Discord toggle
                    act = menu.addAction(self._tr(akey))
                    act.setCheckable(True)
                    act.setChecked(self._discord_enabled)
                    act.toggled.connect(self._toggle_discord)
                    self.discord_action = act
                    self._menu_actions.append((act, akey))
                    continue
                act = menu.addAction(self._tr(akey))
                if isinstance(sc, (list, tuple)):
                    act.setShortcuts([QKeySequence(s) for s in sc])
                elif sc:
                    act.setShortcut(QKeySequence(sc))
                act.triggered.connect(lambda _checked=False, f=fn: f())
                self._menu_actions.append((act, akey))

    def _open_settings(self):
        """Modal Settings window with a left-hand tab list: Display (language)
        and Storage location (dataset/export folder chooser + current path)."""
        dlg = QDialog(self)
        dlg.setMinimumSize(560, 320)
        outer = QHBoxLayout(dlg)
        nav = QListWidget()
        nav.setFixedWidth(150)
        stack = QStackedWidget()

        # -- Display page: language --
        disp = QWidget()
        dv = QVBoxLayout(disp)
        lang_title = QLabel()
        lang_title.setStyleSheet("font-weight: bold;")
        dv.addWidget(lang_title)
        grp = QButtonGroup(dlg)
        rb_en, rb_de = QRadioButton("English"), QRadioButton("Deutsch")
        grp.addButton(rb_en)
        grp.addButton(rb_de)
        rb_en.setChecked(self._lang == "en")
        rb_de.setChecked(self._lang == "de")
        dv.addWidget(rb_en)
        dv.addWidget(rb_de)
        dv.addSpacing(14)
        center_box = QCheckBox()
        center_box.setChecked(self._center)

        def on_center(on):
            self._center = bool(on)
            self.overlay.set_center_marker(on)
            self._save_settings()

        center_box.toggled.connect(on_center)
        dv.addWidget(center_box)
        center_hint = QLabel()
        center_hint.setWordWrap(True)
        center_hint.setStyleSheet("color: gray;")
        dv.addWidget(center_hint)
        dv.addSpacing(10)
        news_box = QCheckBox()
        news_box.setChecked(self._news_enabled)
        news_box.toggled.connect(lambda on: self.set_news_enabled(on))
        dv.addWidget(news_box)
        news_hint = QLabel()
        news_hint.setWordWrap(True)
        news_hint.setStyleSheet("color: gray;")
        dv.addWidget(news_hint)
        dv.addStretch(1)

        # -- New boxes page: default class for a freshly drawn box --
        newp = QWidget()
        nv = QVBoxLayout(newp)
        newk_title = QLabel()
        newk_title.setStyleSheet("font-weight: bold;")
        nv.addWidget(newk_title)
        newk_combo = QComboBox()
        for c in self._classes:
            newk_combo.addItem(c["label"], c["key"])
        i = max(0, newk_combo.findData(self._new_kind))
        newk_combo.setCurrentIndex(i)

        def on_newk(_i):
            k = newk_combo.currentData()
            if k and k != self._new_kind:
                self._new_kind = k
                self._save_settings()

        newk_combo.currentIndexChanged.connect(on_newk)
        nv.addWidget(newk_combo)
        newk_hint = QLabel()
        newk_hint.setWordWrap(True)
        newk_hint.setStyleSheet("color: gray;")
        nv.addWidget(newk_hint)
        nv.addStretch(1)

        # -- Classes page: configurable detection classes --
        clsp = QWidget()
        clv = QVBoxLayout(clsp)
        cls_title = QLabel()
        cls_title.setStyleSheet("font-weight: bold;")
        clv.addWidget(cls_title)
        cls_list = QListWidget()
        clv.addWidget(cls_list, 1)

        def cls_refill():
            cls_list.clear()
            for c in self._classes:
                it = QListWidgetItem(" " + c["label"])
                pm = QPixmap(16, 16)
                pm.fill(QColor(*c["color"]))
                it.setIcon(QIcon(pm))
                cls_list.addItem(it)

        cls_refill()
        crow = QHBoxLayout()
        b_add, b_ren, b_col = QPushButton(), QPushButton(), QPushButton()
        b_del, b_up, b_dn = QPushButton(), QPushButton("▲"), QPushButton("▼")
        b_import, b_reset = QPushButton(), QPushButton()
        for b in (b_add, b_ren, b_col, b_del, b_up, b_dn):
            crow.addWidget(b)
        crow.addStretch(1)
        crow.addWidget(b_import)
        crow.addWidget(b_reset)
        clv.addLayout(crow)
        cls_hint = QLabel()
        cls_hint.setWordWrap(True)
        cls_hint.setStyleSheet("color: gray;")
        clv.addWidget(cls_hint)

        def cls_sel():
            r = cls_list.currentRow()
            return r if 0 <= r < len(self._classes) else -1

        def cls_commit(select=None):
            self._classes = self._sanitize_classes(self._classes)
            self._apply_classes()
            self._save_settings()
            cls_refill()
            if select is not None:
                cls_list.setCurrentRow(max(0, min(select, len(self._classes) - 1)))
            newk_combo.blockSignals(True)
            newk_combo.clear()
            for c in self._classes:
                newk_combo.addItem(c["label"], c["key"])
            newk_combo.setCurrentIndex(max(0, newk_combo.findData(self._new_kind)))
            newk_combo.blockSignals(False)

        def cls_add():
            name, ok = QInputDialog.getText(dlg, self._tr("settings_classes"),
                                            self._tr("class_name"))
            name = name.strip()
            if ok and name and name not in self._class_keys():
                col = CLASS_PALETTE[len(self._classes) % len(CLASS_PALETTE)]
                self._classes.append({"key": name, "label": name,
                                      "color": list(col)})
                cls_commit(select=len(self._classes) - 1)

        def cls_rename():
            r = cls_sel()
            if r < 0:
                return
            name, ok = QInputDialog.getText(dlg, self._tr("settings_classes"),
                                            self._tr("class_name"),
                                            text=self._classes[r]["label"])
            if ok and name.strip():
                self._classes[r]["label"] = name.strip()
                cls_commit(select=r)

        def cls_color():
            r = cls_sel()
            if r < 0:
                return
            c = QColorDialog.getColor(QColor(*self._classes[r]["color"]), dlg)
            if c.isValid():
                self._classes[r]["color"] = [c.red(), c.green(), c.blue()]
                cls_commit(select=r)

        def cls_remove():
            r = cls_sel()
            if r < 0 or len(self._classes) <= 1:
                return
            del self._classes[r]
            cls_commit(select=r)

        def cls_move(d):
            r = cls_sel()
            j = r + d
            if r < 0 or not (0 <= j < len(self._classes)):
                return
            self._classes[r], self._classes[j] = self._classes[j], self._classes[r]
            cls_commit(select=j)

        def cls_reset():
            self._classes = [dict(c) for c in DEFAULT_CLASSES]
            cls_commit(select=0)

        def cls_import():
            path, _f = QFileDialog.getOpenFileName(
                dlg, self._tr("class_import"), self._start_dir(),
                "classes.txt / data.yaml (*.txt *.yaml *.yml)")
            if not path:
                return
            names, seen = [], set()
            for n in self._parse_class_names(path):     # dedup, keep order
                n = n.strip()
                if n and n not in seen:
                    names.append(n)
                    seen.add(n)
            if not names:
                self._status(self._tr("class_import_fail"), error=True)
                return
            old = {c["key"]: c["color"] for c in self._classes}
            self._classes = [
                {"key": n, "label": n,
                 "color": old.get(n) or CLASS_PALETTE[i % len(CLASS_PALETTE)]}
                for i, n in enumerate(names)]
            cls_commit(select=0)
            self._status(self._tr("class_imported").format(n=len(names)))

        b_add.clicked.connect(cls_add)
        b_ren.clicked.connect(cls_rename)
        b_col.clicked.connect(cls_color)
        b_del.clicked.connect(cls_remove)
        b_up.clicked.connect(lambda: cls_move(-1))
        b_dn.clicked.connect(lambda: cls_move(1))
        b_import.clicked.connect(cls_import)
        b_reset.clicked.connect(cls_reset)

        # -- Tools page: magic-wand tolerance --
        toolsp = QWidget()
        tvv = QVBoxLayout(toolsp)
        wand_title = QLabel()
        wand_title.setStyleSheet("font-weight: bold;")
        tvv.addWidget(wand_title)
        wand_row = QHBoxLayout()
        wand_lbl = QLabel()
        wand_spin = QSpinBox()
        wand_spin.setRange(1, 255)
        wand_spin.setValue(self._wand_tol)
        wand_spin.setFixedWidth(70)

        def on_wand(v):
            self._wand_tol = int(v)
            self.overlay.set_wand_tolerance(v)
            self._save_settings()

        wand_spin.valueChanged.connect(on_wand)
        wand_row.addWidget(wand_lbl)
        wand_row.addWidget(wand_spin)
        wand_row.addStretch(1)
        tvv.addLayout(wand_row)
        wand_hint = QLabel()
        wand_hint.setWordWrap(True)
        wand_hint.setStyleSheet("color: gray;")
        tvv.addWidget(wand_hint)
        tvv.addSpacing(14)
        rtl_box = QCheckBox()
        rtl_box.setChecked(self._rtl)

        def on_rtl(on):
            self._rtl = bool(on)
            self._save_settings()

        rtl_box.toggled.connect(on_rtl)
        tvv.addWidget(rtl_box)
        rtl_hint = QLabel()
        rtl_hint.setWordWrap(True)
        rtl_hint.setStyleSheet("color: gray;")
        tvv.addWidget(rtl_hint)
        tvv.addStretch(1)

        # -- Discord page: Rich Presence toggle + application id --
        disc = QWidget()
        cv = QVBoxLayout(disc)
        disc_title = QLabel()
        disc_title.setStyleSheet("font-weight: bold;")
        cv.addWidget(disc_title)
        disc_box = QCheckBox()
        disc_box.setChecked(self._discord_enabled)
        cv.addWidget(disc_box)
        disc_id_lbl = QLabel()
        cv.addWidget(disc_id_lbl)
        disc_id = QLineEdit()
        disc_id.setText(self._discord_id)
        disc_id.setPlaceholderText("1234567890...")
        cv.addWidget(disc_id)
        disc_hint = QLabel()
        disc_hint.setWordWrap(True)
        disc_hint.setStyleSheet("color: gray;")
        cv.addWidget(disc_hint)
        cv.addStretch(1)

        def apply_discord():
            self._discord_enabled = disc_box.isChecked()
            self._discord_id = disc_id.text().strip()
            self._save_settings()
            self._start_discord()

        disc_box.toggled.connect(lambda _on: apply_discord())
        disc_id.editingFinished.connect(apply_discord)

        # -- Storage page: dataset/export folder --
        store = QWidget()
        sv = QVBoxLayout(store)
        store_title = QLabel()
        store_title.setStyleSheet("font-weight: bold;")
        sv.addWidget(store_title)
        choose_btn = QPushButton()
        path_lbl = QLabel()
        path_lbl.setWordWrap(True)
        path_lbl.setStyleSheet("color: gray;")

        def choose():
            self.on_choose_folder()
            path_lbl.setText(self._folder or self._tr("settings_folder_none"))

        choose_btn.clicked.connect(choose)
        sv.addWidget(choose_btn)
        sv.addWidget(path_lbl)
        sv.addSpacing(14)
        val_row = QHBoxLayout()
        val_lbl = QLabel()
        val_spin = QSpinBox()
        val_spin.setRange(0, 50)
        val_spin.setValue(self._val_split)
        val_spin.setSuffix(" %")
        val_spin.setFixedWidth(80)

        def on_val(v):
            self._val_split = int(v)
            self._save_settings()

        val_spin.valueChanged.connect(on_val)
        val_row.addWidget(val_lbl)
        val_row.addWidget(val_spin)
        val_row.addStretch(1)
        sv.addLayout(val_row)
        val_hint = QLabel()
        val_hint.setWordWrap(True)
        val_hint.setStyleSheet("color: gray;")
        sv.addWidget(val_hint)
        sv.addSpacing(12)
        summ_box = QCheckBox()
        summ_box.setChecked(self._export_summary_on)

        def on_summ(on):
            self._export_summary_on = bool(on)
            self._save_settings()

        summ_box.toggled.connect(on_summ)
        sv.addWidget(summ_box)
        sv.addStretch(1)

        stack.addWidget(disp)
        stack.addWidget(newp)
        stack.addWidget(clsp)
        stack.addWidget(toolsp)
        stack.addWidget(disc)
        stack.addWidget(store)
        nav.currentRowChanged.connect(stack.setCurrentIndex)

        def apply_texts():
            tr = self._tr
            dlg.setWindowTitle(tr("m_settings"))
            row = nav.currentRow()
            nav.blockSignals(True)
            nav.clear()
            nav.addItem(tr("settings_display"))
            nav.addItem(tr("settings_newbox"))
            nav.addItem(tr("settings_classes"))
            nav.addItem(tr("settings_tools"))
            nav.addItem(tr("settings_discord"))
            nav.addItem(tr("settings_storage"))
            nav.setCurrentRow(row if row >= 0 else 0)
            nav.blockSignals(False)
            cls_title.setText(tr("settings_classes"))
            b_add.setText(tr("class_add"))
            b_ren.setText(tr("class_rename"))
            b_col.setText(tr("class_color"))
            b_del.setText(tr("class_remove"))
            b_import.setText(tr("class_import"))
            b_reset.setText(tr("class_reset"))
            cls_hint.setText(tr("settings_classes_hint"))
            lang_title.setText(tr("mi_language"))
            center_box.setText(tr("center_marker"))
            center_hint.setText(tr("center_marker_tip"))
            news_box.setText(tr("settings_news"))
            news_hint.setText(tr("settings_news_hint"))
            newk_title.setText(tr("settings_newbox"))
            newk_hint.setText(tr("settings_newbox_hint"))
            wand_title.setText(tr("settings_tools"))
            wand_lbl.setText(tr("wand_tol"))
            wand_hint.setText(tr("wand_tol_tip"))
            rtl_box.setText(tr("rtl"))
            rtl_hint.setText(tr("rtl_tip"))
            disc_title.setText(tr("settings_discord"))
            disc_box.setText(tr("discord_enable"))
            disc_id_lbl.setText(tr("discord_id"))
            disc_hint.setText(tr("discord_hint"))
            store_title.setText(tr("settings_folder_title"))
            choose_btn.setText(tr("mi_folder"))
            path_lbl.setText(self._folder or tr("settings_folder_none"))
            val_lbl.setText(tr("val_split"))
            val_hint.setText(tr("val_split_hint"))
            summ_box.setText(tr("export_summary_toggle"))

        def on_lang(code, on):
            if on and code != self._lang:
                self._set_lang(code)
                apply_texts()

        rb_en.toggled.connect(lambda on: on_lang("en", on))
        rb_de.toggled.connect(lambda on: on_lang("de", on))

        outer.addWidget(nav)
        outer.addWidget(stack, 1)
        apply_texts()
        nav.setCurrentRow(0)
        dlg.exec_()

    def _retranslate_menu(self):
        for menu, key in getattr(self, "_menu_titles", []):
            menu.setTitle(self._tr(key))
        for act, key in getattr(self, "_menu_actions", []):
            act.setText(self._tr(key))

    # -- box list panel --
    def _rebuild_box_list(self):
        lw = self.box_list
        self._rebuilding_list = True         # ignore model moves while filling
        lw.blockSignals(True)
        lw.clear()
        pg = self._page()
        flt = self._class_filter
        for i, b in enumerate(pg["boxes"] if pg else []):
            order = b.get("order", 0)
            num = str(order) if order else str(i + 1)
            kind = b.get("kind", "bubble")
            it = QListWidgetItem("%s   %s" % (num, self._class_label(kind)))
            if flt and kind != flt:
                it.setForeground(QColor(120, 120, 120))   # filtered out (dim)
            else:
                it.setForeground(QColor(*self._class_color(kind)))
            it.setData(Qt.UserRole, i)        # original box index, for reordering
            lw.addItem(it)
        cur = getattr(self, "_current", -1)
        lw.clearSelection()
        for i in self._sel:                  # reflect the multi-selection
            if 0 <= i < lw.count():
                lw.item(i).setSelected(True)
        if 0 <= cur < lw.count():
            lw.setCurrentRow(cur, QItemSelectionModel.NoUpdate)
        lw.blockSignals(False)
        self._rebuilding_list = False

    def _on_box_list_selection(self):
        if getattr(self, "_rebuilding_list", False):
            return
        pg = self._page()
        rows = sorted(self.box_list.row(it)
                      for it in self.box_list.selectedItems())
        self._sel = {r for r in rows if pg and 0 <= r < len(pg["boxes"])}
        cr = self.box_list.currentRow()
        self._current = cr if cr in self._sel else (max(self._sel)
                                                    if self._sel else -1)
        if pg and 0 <= self._current < len(pg["boxes"]):
            k = pg["boxes"][self._current].get("kind", "bubble")
            self._set_kind_buttons(k)
            self._new_kind = k
        self._refresh()

    def _on_boxes_reordered(self, *_args):
        """A drag in the box list reorders the boxes and (re)numbers the reading
        order to match the new top-to-bottom order."""
        if getattr(self, "_rebuilding_list", False):
            return
        pg = self._page()
        if not pg:
            return
        lw = self.box_list
        order = [lw.item(r).data(Qt.UserRole) for r in range(lw.count())]
        n = len(pg["boxes"])
        if len(order) != n or any(x is None for x in order) \
                or sorted(order) != list(range(n)):
            return                            # unexpected -> leave data untouched
        self._push_undo()
        old = pg["boxes"]
        cur_old = getattr(self, "_current", -1)
        pg["boxes"] = [old[i] for i in order]
        for pos, b in enumerate(pg["boxes"], 1):   # drag == set reading order
            b["order"] = pos
        self._order_counter = n + 1
        self._current = order.index(cur_old) if 0 <= cur_old < n else -1
        self._refresh()

    # -- page thumbnail strip --
    def _page_thumb(self, pg):
        px = pg.get("thumb")
        if px is None:
            # cache at a generous size so the thumbnails stay crisp when the
            # Pages dock is enlarged (the view scales this down for small icons)
            scaled = pg["img"].scaled(QSize(240, 300), Qt.KeepAspectRatio,
                                      Qt.SmoothTransformation)
            px = QPixmap.fromImage(scaled)
            pg["thumb"] = px
        return px

    @staticmethod
    def _page_strip_label(i, pg):
        if not pg["boxes"]:
            return str(i + 1)
        # ✓ = exported into the dataset, • = labelled but not yet exported
        return "%d ✓" % (i + 1) if pg.get("exported") else "%d •" % (i + 1)

    def _rebuild_page_strip(self):
        lw = self.page_strip
        lw.blockSignals(True)
        lw.clear()
        for i, pg in enumerate(self._pages):
            it = QListWidgetItem(QIcon(self._page_thumb(pg)),
                                 self._page_strip_label(i, pg))
            it.setToolTip("%s  (%d)" % (pg["name"], len(pg["boxes"])))
            it.setTextAlignment(Qt.AlignHCenter | Qt.AlignBottom)
            lw.addItem(it)
        lw.setCurrentRow(self._cur if 0 <= self._cur < len(self._pages) else -1)
        lw.blockSignals(False)
        self._strip_sig = [id(p) for p in self._pages]

    def _sync_page_strip(self):
        if not hasattr(self, "page_strip"):
            return
        sig = [id(p) for p in self._pages]
        if sig != getattr(self, "_strip_sig", None):
            self._rebuild_page_strip()       # pages added/removed/reordered
            return
        cur = self._cur
        lw = self.page_strip
        if 0 <= cur < lw.count():            # refresh current page's ✓ + highlight
            lw.blockSignals(True)
            lw.item(cur).setText(self._page_strip_label(cur, self._pages[cur]))
            if lw.currentRow() != cur:
                lw.setCurrentRow(cur)
            lw.blockSignals(False)

    def _on_page_strip_row(self, row):
        if 0 <= row < len(self._pages) and row != self._cur:
            self._goto(row)

    def _on_page_strip_context(self, pos):
        it = self.page_strip.itemAt(pos)
        if it is None:
            return
        idx = self.page_strip.row(it)
        if not (0 <= idx < len(self._pages)):
            return
        t = self._tr
        menu = QMenu(self)
        menu.addAction(t("mi_goto_page"), lambda: self._goto(idx))
        menu.addSeparator()
        menu.addAction(t("close_page"), lambda: self._close_page_at(idx))
        menu.exec_(self.page_strip.viewport().mapToGlobal(pos))

    # -- copy / paste / duplicate a box --
    def on_copy_box(self):
        pg = self._page()
        cur = getattr(self, "_current", -1)
        if pg and 0 <= cur < len(pg["boxes"]):
            self._clipboard_box = copy.deepcopy(pg["boxes"][cur])
            self._status(self._tr("copied"))

    def on_paste_box(self):
        if self._clipboard_box and self._page():
            self._place_box(self._clipboard_box, 12, 12)
            self._status(self._tr("pasted"))

    def on_duplicate_box(self):
        pg = self._page()
        cur = getattr(self, "_current", -1)
        if pg and 0 <= cur < len(pg["boxes"]):
            self._place_box(pg["boxes"][cur], 15, 15)
            self._status(self._tr("duplicated"))

    def on_fit_box(self):
        """Tighten the selected box onto the bubble inside it (flood-fill)."""
        pg = self._page()
        cur = getattr(self, "_current", -1)
        if not pg or not (0 <= cur < len(pg["boxes"])):
            return
        bb = self.overlay._fit_box_bounds(pg["boxes"][cur])
        if not bb or bb[2] < 4 or bb[3] < 4:
            self._status(self._tr("fit_fail"))
            return
        self._push_undo()
        b = pg["boxes"][cur]
        b["x"], b["y"] = int(bb[0]), int(bb[1])
        b["w"], b["h"] = int(bb[2]), int(bb[3])
        b.pop("points", None)                # tightened to a plain box
        self._refresh()
        self._status(self._tr("fit_done"))

    def _place_box(self, box, dx, dy):
        pg = self._page()
        if not pg:
            return
        self._push_undo()
        nb = copy.deepcopy(box)
        nb["order"] = 0
        w, h = pg["img"].width(), pg["img"].height()
        nx = int(max(0, min(nb["x"] + dx, w - nb["w"])))
        ny = int(max(0, min(nb["y"] + dy, h - nb["h"])))
        ddx, ddy = nx - nb["x"], ny - nb["y"]
        nb["x"], nb["y"] = nx, ny
        if isinstance(nb.get("points"), list):
            nb["points"] = [[px + ddx, py + ddy] for px, py in nb["points"]]
        pg["boxes"].append(nb)
        self._current = len(pg["boxes"]) - 1
        self._maybe_auto_order()
        self._refresh()

    # -- auto-save / crash recovery --
    def _autosave(self):
        if not self._pages:
            return
        data = {"pages": [{"path": p["path"], "name": p["name"],
                           "boxes": p["boxes"]} for p in self._pages]}
        try:
            with open(RECOVERY_FILE, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
        except OSError:
            pass

    def maybe_offer_recovery(self):
        if not os.path.exists(RECOVERY_FILE):
            return
        try:
            with open(RECOVERY_FILE, encoding="utf-8") as fh:
                n = len(json.load(fh).get("pages", []))
        except Exception:                    # noqa: BLE001
            n = 0
        if n <= 0:
            self._discard_recovery()
            return
        ans = QMessageBox.question(
            self, self._tr("rec_title"), self._tr("rec_msg").format(n=n),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if ans == QMessageBox.Yes:
            pages = self._load_pages_from(RECOVERY_FILE)
            if pages:
                self._pages = pages
                self._cur = -1
                self._reset_history()
                self._goto(0)
                self._status(self._tr("rec_done").format(n=len(pages)))
        else:
            self._discard_recovery()

    def _discard_recovery(self):
        try:
            os.remove(RECOVERY_FILE)
        except OSError:
            pass

    def _set_lang(self, code):
        if code == self._lang:
            return
        self._lang = code
        self._save_settings()
        self._retranslate()

    def _retranslate(self):
        t = self._tr
        self.setWindowTitle(t("title") + " v" + VERSION)
        self._retranslate_menu()
        self.tools_dock.setWindowTitle(t("dock_tools"))
        self.boxes_dock.setWindowTitle(t("dock_boxes"))
        self.thumbs_dock.setWindowTitle(t("dock_pages"))
        self.box_list.setToolTip(t("boxes_tip"))
        self.page_strip.setToolTip(t("strip_tip"))
        self.lbl_sort.setText(t("sort_by"))
        for i, _k in enumerate(("name", "unlabeled", "unexported",
                                "fewest", "most")):
            self.sort_combo.setItemText(i, t("sort_" + _k))
        self.next_todo_btn.setText(t("next_todo"))
        self.lbl_filter.setText(t("show"))
        for i, _fk in enumerate(("all", "bubble", "sfx")):
            self.filter_combo.setItemText(i, t("show_" + _fk))
        self.auto_chk.setText(t("auto_order_live"))
        self.auto_chk.setToolTip(t("auto_order_live_tip"))
        for _k, _btn in self.tool_btns.items():
            _btn.setToolTip(t("tool_" + _k + "_hint"))
        self.path_chk.setText(t("order_path"))
        self.path_chk.setToolTip(t("order_path_tip"))
        self.prev_btn.setText(t("prev"))
        self.next_btn.setText(t("next"))
        self.close_btn.setText(t("close_page"))
        self.close_btn.setToolTip(t("close_page_tip"))
        self.close_all_btn.setText(t("close_all"))
        self.close_all_btn.setToolTip(t("close_all_tip"))
        self.zoom_fit_btn.setText(t("fit"))
        self.zoom_fit_btn.setToolTip(t("zoom_tip"))
        self.order_btn.setText(t("set_order"))
        self.auto_order_btn.setText(t("auto_order"))
        self.auto_order_btn.setToolTip(t("auto_order_tip"))
        if hasattr(self, "start_sub"):
            self.start_sub.setText(t("start_sub"))
            self.start_heading.setText(t("start_heading"))
            self.start_recent_lbl.setText(t("start_recent"))
            self.start_clear.setText(t("start_clear"))
            self.start_news_lbl.setText(t("start_news"))
            for b, key in self._start_btns:
                b.setText(t(key))
        self._refresh()

    # -- helpers --
    def _status(self, msg, error=False):
        self.status.setText(msg)
        self.status.setStyleSheet("color:#c0392b;" if error else "color:gray;")

    def _page(self):
        return self._pages[self._cur] if 0 <= self._cur < len(self._pages) else None

    def _refresh(self):
        pg = self._page()
        boxes = pg["boxes"] if pg else []
        n = len(boxes)
        cur = getattr(self, "_current", -1)
        # reconcile selection: drop invalid; single-select ops collapse it
        self._sel = {i for i in self._sel if 0 <= i < n}
        if cur < 0:
            self._sel = set()
        elif cur not in self._sel:
            self._sel = {cur}
        self.overlay.set_boxes(boxes, cur, self._sel)
        # per-class object counts for the current page (all configured classes)
        per = {c["key"]: 0 for c in self._classes}
        for x in boxes:
            k = x.get("kind", "bubble")
            per[k] = per.get(k, 0) + 1
        cls_str = "   ".join("%s: %d" % (c["label"], per.get(c["key"], 0))
                             for c in self._classes)
        done = sum(1 for p in self._pages if p["boxes"])
        exp = sum(1 for p in self._pages if p.get("exported"))
        total = len(self._pages)
        self.lbl_counts.setText("%s — %s   |   %s" % (
            self._tr("counts_this_page"), cls_str,
            self._tr("counts_pages").format(p=total, done=done, exp=exp)))
        if pg:
            self.page_lbl.setText(self._tr("page").format(
                i=self._cur + 1, n=len(self._pages), name=pg["name"]))
        else:
            self.page_lbl.setText(self._tr("page_none"))
        if hasattr(self, "box_list"):
            self._rebuild_box_list()
        self._sync_page_strip()
        self._sync_start_page()
        self._update_discord()

    def _set_kind(self, kind):
        self._new_kind = kind
        pg = self._page()
        if not pg:
            return
        changed = [i for i in self._sel
                   if 0 <= i < len(pg["boxes"])
                   and pg["boxes"][i].get("kind") != kind]
        if changed:                          # relabel all selected boxes
            self._push_undo()
            for i in changed:
                pg["boxes"][i]["kind"] = kind
            self._refresh()

    def _set_kind_buttons(self, kind):
        # class is chosen via the right-click menu / B & S keys now (no buttons)
        pass

    # -- undo / redo --
    def _push_undo(self):
        """Snapshot the current page's boxes before a change; clears redo."""
        pg = self._page()
        if pg is None:
            return
        pg["exported"] = False       # any edit makes the exported copy stale
        self._undo.append((self._cur, copy.deepcopy(pg["boxes"]),
                           getattr(self, "_current", -1)))
        if len(self._undo) > 120:
            self._undo.pop(0)
        self._redo.clear()
        self._update_undo_buttons()

    def _capture(self, idx):
        """A snapshot of the boxes on page `idx` as it is right now."""
        if not (0 <= idx < len(self._pages)):
            return (idx, [], -1)
        cur = getattr(self, "_current", -1) if idx == self._cur else -1
        return (idx, copy.deepcopy(self._pages[idx]["boxes"]), cur)

    def _restore(self, snap):
        idx, boxes, cur = snap
        if not (0 <= idx < len(self._pages)):
            return
        if idx != self._cur:
            self._cur = idx
            pg = self._pages[idx]
            self.overlay.set_page(pg["img"], pg["img"].width(),
                                  pg["img"].height())
        self._pages[idx]["boxes"] = boxes
        n = len(boxes)
        self._current = cur if isinstance(cur, int) and 0 <= cur < n else -1
        self._order_counter = max([b.get("order", 0) for b in boxes] + [0]) + 1
        self._refresh()

    def _reset_history(self):
        self._undo = []
        self._redo = []
        self._update_undo_buttons()

    def _update_undo_buttons(self):
        # enable/disable the Edit-menu Undo/Redo actions to match the stacks
        for act, key in getattr(self, "_menu_actions", []):
            if key == "mi_undo":
                act.setEnabled(bool(self._undo))
            elif key == "mi_redo":
                act.setEnabled(bool(self._redo))

    def undo(self):
        if not self._undo:
            self._status(self._tr("nothing_undo"))
            return
        snap = self._undo.pop()
        self._redo.append(self._capture(snap[0]))
        self._restore(snap)
        self._update_undo_buttons()
        self._status(self._tr("undone"))

    def redo(self):
        if not self._redo:
            self._status(self._tr("nothing_redo"))
            return
        snap = self._redo.pop()
        self._undo.append(self._capture(snap[0]))
        self._restore(snap)
        self._update_undo_buttons()
        self._status(self._tr("redone"))

    # -- page navigation --
    def _goto(self, idx):
        if not self._pages:
            return
        self._cur = max(0, min(idx, len(self._pages) - 1))
        self._current = -1
        pg = self._pages[self._cur]
        self.overlay.set_page(pg["img"], pg["img"].width(), pg["img"].height())
        self._refresh()

    def _sort_pages(self):
        """Rank the loaded pages for labelling, keeping the current one visible."""
        if not self._pages:
            return
        cur_page = self._page()
        key = self.sort_combo.currentData() or "name"

        def nboxes(p):
            return len(p["boxes"])

        if key == "unlabeled":
            self._pages.sort(key=lambda p: (nboxes(p) > 0, p["name"].lower()))
        elif key == "unexported":
            # pages with boxes but not exported first, then empty, then exported
            def rank(p):
                if p["boxes"] and not p.get("exported"):
                    return 0
                return 1 if not p["boxes"] else 2
            self._pages.sort(key=lambda p: (rank(p), p["name"].lower()))
        elif key == "fewest":
            self._pages.sort(key=lambda p: (nboxes(p), p["name"].lower()))
        elif key == "most":
            self._pages.sort(key=lambda p: (-nboxes(p), p["name"].lower()))
        else:  # "name"
            self._pages.sort(key=lambda p: p["name"].lower())

        if cur_page in self._pages:
            self._cur = self._pages.index(cur_page)
        self._refresh()

    def on_next_todo(self):
        """Jump to the next page that has no boxes yet (wraps around)."""
        n = len(self._pages)
        if n == 0:
            return
        for step in range(1, n + 1):
            idx = (self._cur + step) % n
            if not self._pages[idx]["boxes"]:
                self._goto(idx)
                return
        self._status(self._tr("all_labelled"))

    def on_next_unexported(self):
        """Jump to the next page with boxes that hasn't been exported yet."""
        n = len(self._pages)
        if n == 0:
            return
        for step in range(1, n + 1):
            idx = (self._cur + step) % n
            p = self._pages[idx]
            if p["boxes"] and not p.get("exported"):
                self._goto(idx)
                return
        self._status(self._tr("all_exported"))

    # -- closing pages --
    def _close_page_at(self, idx):
        """Remove the page at idx from the session (does not touch files)."""
        if not (0 <= idx < len(self._pages)):
            return
        pg = self._pages[idx]
        if pg["boxes"] and not self._confirm_discard(
                self._tr("confirm_close").format(n=len(pg["boxes"]),
                                                 name=pg["name"])):
            return
        del self._pages[idx]
        if self._cur > idx:
            self._cur -= 1
        self._after_pages_removed()
        self._status(self._tr("closed"))

    def on_close_page(self):
        """Remove the current page from the session (does not touch files)."""
        if self._page():
            self._close_page_at(self._cur)

    def on_close_all(self):
        """Remove every loaded page from the session."""
        if not self._pages:
            return
        total_boxes = sum(len(p["boxes"]) for p in self._pages)
        if total_boxes and not self._confirm_discard(
                self._tr("confirm_close_all").format(p=len(self._pages),
                                                     n=total_boxes)):
            return
        self._pages = []
        self._after_pages_removed()
        self._status(self._tr("closed_all"))

    def _confirm_discard(self, msg, title=None):
        return QMessageBox.question(
            self, title or self._tr("confirm_title"), msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes

    def _after_pages_removed(self):
        """Re-anchor the view after one or all pages were closed."""
        self._reset_history()             # page indices changed -> history stale
        if not self._pages:
            self._cur = -1
            self._current = -1
            self.overlay.set_page(QImage(), 0, 0)   # blank the canvas
            self._refresh()
        else:
            self._cur = max(0, min(self._cur, len(self._pages) - 1))
            self._goto(self._cur)

    # -- overlay callbacks --
    def _on_box_added(self, x, y, w, h, shape="rect", points=None):
        pg = self._page()
        if not pg:
            return
        self._push_undo()
        box = {"x": int(round(x)), "y": int(round(y)),
               "w": int(round(w)), "h": int(round(h)),
               "kind": self._new_kind, "order": 0, "shape": shape}
        if points:
            box["points"] = points
        pg["boxes"].append(box)
        self._current = len(pg["boxes"]) - 1
        self._maybe_auto_order()
        self._refresh()

    def _on_box_changed(self, idx, x, y, w, h):
        pg = self._page()
        if not (pg and 0 <= idx < len(pg["boxes"])):
            return
        self._push_undo()
        b = pg["boxes"][idx]
        nx, ny, nw, nh = (int(round(x)), int(round(y)),
                          int(round(w)), int(round(h)))
        pts = b.get("points")
        if pts and b["w"] > 0 and b["h"] > 0:
            # remap the lasso polygon from the old bbox to the new one
            ox, oy, ow, oh = b["x"], b["y"], b["w"], b["h"]
            sx, sy = nw / float(ow), nh / float(oh)
            b["points"] = [[nx + (px - ox) * sx, ny + (py - oy) * sy]
                           for px, py in pts]
        b.update({"x": nx, "y": ny, "w": nw, "h": nh})
        self._current = idx
        self._maybe_auto_order()
        self._refresh()

    def _on_box_removed(self, idx):
        pg = self._page()
        if pg and 0 <= idx < len(pg["boxes"]):
            self._push_undo()
            del pg["boxes"][idx]
            self._current = min(getattr(self, "_current", -1), len(pg["boxes"]) - 1)
            self._maybe_auto_order()
            self._refresh()

    def _on_box_clicked(self, idx):
        pg = self._page()
        if not pg or not (0 <= idx < len(pg["boxes"])):
            return
        if self._order_mode:
            self._current = idx
            self._push_undo()
            pg["boxes"][idx]["order"] = self._order_counter
            self._order_counter += 1
            self._refresh()
            return
        if QApplication.keyboardModifiers() & Qt.ControlModifier:
            if idx in self._sel:             # Ctrl+click toggles multi-selection
                self._sel.discard(idx)
            else:
                self._sel.add(idx)
            self._current = idx if idx in self._sel else (
                max(self._sel) if self._sel else -1)
        else:
            self._current = idx
            self._sel = {idx}
        if 0 <= self._current < len(pg["boxes"]):
            kind = pg["boxes"][self._current].get("kind", "bubble")
            self._set_kind_buttons(kind)
            self._new_kind = kind
        self._refresh()

    def _on_tool(self, key):
        # picking a marking tool leaves reading-order mode and is ready to draw
        if self.order_btn.isChecked():
            self.order_btn.setChecked(False)      # fires _on_order_toggle(False)
        self.overlay.set_tool(key)
        self.overlay.set_edit_mode(True)
        self._status(self._tr("tool_" + key + "_hint"))

    def _on_order_toggle(self, on):
        self._order_mode = bool(on)
        # reading-order mode: clicks set the order instead of drawing boxes
        self.overlay.set_edit_mode(not on)
        if on:
            self._order_counter = 1
            pg = self._page()
            if pg:
                for b in pg["boxes"]:
                    b["order"] = 0
            self._refresh()
            self._status(self._tr("order_hint"))

    def on_clear_order(self):
        pg = self._page()
        if pg and any(b.get("order") for b in pg["boxes"]):
            self._push_undo()
            for b in pg["boxes"]:
                b["order"] = 0
        self._order_counter = 1
        self._refresh()
        self._status(self._tr("order_cleared"))

    def on_auto_order(self):
        pg = self._page()
        if not pg or not pg["boxes"]:
            self._status(self._tr("no_boxes"), error=True)
            return
        self._push_undo()
        auto_order(pg["boxes"], rtl=self._rtl)
        self._order_counter = len(pg["boxes"]) + 1
        self._refresh()
        self._status(self._tr("ranked").format(n=len(pg["boxes"])))

    def on_delete(self):
        pg = self._page()
        if not pg:
            return
        targets = sorted((i for i in self._sel if 0 <= i < len(pg["boxes"])),
                         reverse=True)
        if not targets:
            return
        self._push_undo()
        for i in targets:                    # delete all selected boxes
            del pg["boxes"][i]
        self._current = -1
        self._sel = set()
        self._maybe_auto_order()
        self._refresh()

    def on_clear(self):
        pg = self._page()
        if pg and pg["boxes"]:
            self._push_undo()
            pg["boxes"] = []
            self._current = -1
            self._refresh()

    # -- file-dialog directory memory --
    def _start_dir(self):
        """Where a file/folder dialog should open: the last place used, else the
        home folder (deliberately not the dataset folder)."""
        if self._last_dir and os.path.isdir(self._last_dir):
            return self._last_dir
        return os.path.expanduser("~")

    def _remember_dir(self, directory):
        """Remember a chosen directory so the next dialog starts there."""
        if directory and os.path.isdir(directory) and directory != self._last_dir:
            self._last_dir = directory
            self._save_settings()

    # -- actions --
    def on_load_images(self):
        paths, _f = QFileDialog.getOpenFileNames(
            self, self._tr("load"), self._start_dir(),
            self._tr("img_filter"))
        if paths:
            self._remember_dir(os.path.dirname(paths[0]))
            self.add_image_paths(paths)

    def on_load_folder(self):
        """Load every image in a chosen folder as pages."""
        d = QFileDialog.getExistingDirectory(
            self, self._tr("mi_load_folder"), self._start_dir())
        if not d:
            return
        self._remember_dir(d)
        exts = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
        try:
            files = sorted(os.path.join(d, f) for f in os.listdir(d)
                           if f.lower().endswith(exts))
        except OSError:
            files = []
        if files:
            self.add_image_paths(files)
        else:
            self._status(self._tr("no_imgs_folder"), error=True)

    def add_image_paths(self, paths):
        """Load the given image files as pages (used by the file dialog and by
        image paths passed on the command line). Returns how many were added."""
        added = 0
        loaded = []
        for p in paths:
            img = QImage(p)
            if img.isNull():
                continue
            base = os.path.splitext(os.path.basename(p))[0]
            name = "".join(ch if (ch.isalnum() or ch in "-_") else "_"
                           for ch in base) or "page"
            self._pages.append({"path": p, "name": name,
                                "img": img.convertToFormat(QImage.Format_RGB888),
                                "boxes": []})
            loaded.append(p)
            added += 1
        if added:
            self._remember_recent(loaded)
            if self._cur < 0:
                self._goto(0)
            else:
                self._refresh()
            self._status(self._tr("loaded").format(n=added))
        return added

    def on_choose_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, self._tr("choose"), self._start_dir())
        if not path:
            return
        self._folder = path
        self._remember_dir(path)
        self._save_settings()

    # -- optional bridge to the BubblR AI ranking tool -----------------------
    def _find_ai_dir(self):
        """The BubblR AI tool folder (has propose.py): the saved setting, else
        the usual sibling location next to this app. '' if not found."""
        cands = []
        if self._ai_dir:
            cands.append(self._ai_dir)
        base = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
                else os.path.dirname(os.path.abspath(__file__)))
        cands.append(os.path.normpath(
            os.path.join(base, "..", "BubblR-Test", "ai")))
        for d in cands:
            if d and os.path.isfile(os.path.join(d, "propose.py")):
                return d
        return ""

    @staticmethod
    def _ai_python(ai_dir):
        # venv layout differs: Scripts/python.exe on Windows, bin/python elsewhere
        for sub in (("Scripts", "python.exe"), ("bin", "python3"),
                    ("bin", "python")):
            p = os.path.join(ai_dir, ".venv", *sub)
            if os.path.exists(p):
                return p
        return ""

    def on_rank_load(self):
        """Rank a folder of raw pages with the AI tool, then load the top ones."""
        folder = QFileDialog.getExistingDirectory(
            self, self._tr("rank_pick"), self._start_dir())
        if not folder:
            return
        self._remember_dir(folder)
        ai = self._find_ai_dir()
        if not ai:
            if QMessageBox.question(
                    self, self._tr("rank_no_ai_title"), self._tr("rank_no_ai"),
                    QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                return
            d = QFileDialog.getExistingDirectory(
                self, self._tr("rank_pick_ai"), self._start_dir())
            if not d or not os.path.isfile(os.path.join(d, "propose.py")):
                self._status(self._tr("rank_no_ai"), error=True)
                return
            ai = self._ai_dir = d
            self._save_settings()
        py = self._ai_python(ai)
        if not py:
            self._status(self._tr("rank_no_venv"), error=True)
            return
        if getattr(self, "_ranking", False):     # a rank job is already running
            return
        top, ok = QInputDialog.getInt(
            self, self._tr("rank_top_title"), self._tr("rank_top_q"), 30, 1, 500)
        if not ok:
            return
        self._rank_folder = folder
        self._ranking = True
        self._status(self._tr("rank_running"))
        self._rank_proc = QProcess(self)
        self._rank_proc.setWorkingDirectory(ai)
        self._rank_proc.setProcessChannelMode(QProcess.MergedChannels)
        self._rank_proc.readyReadStandardOutput.connect(self._rank_output)
        self._rank_proc.finished.connect(self._rank_finished)
        self._rank_proc.start(py, ["-u", os.path.join(ai, "propose.py"),
                                   "--dir", folder, "--top", str(top)])

    def _rank_output(self):
        txt = bytes(self._rank_proc.readAllStandardOutput()).decode(
            "utf-8", "replace").strip().splitlines()
        if txt:
            self._status(self._tr("rank_running") + "  " + txt[-1][:80])

    def _rank_finished(self, code, _status):
        self._ranking = False
        if code != 0:
            self._status(self._tr("rank_fail"), error=True)
            return
        out = os.path.join(self._rank_folder, "_label_first")
        try:
            files = sorted(f for f in os.listdir(out)
                           if f.lower().endswith(
                               (".png", ".jpg", ".jpeg", ".webp", ".bmp")))
        except OSError:
            files = []
        if not files:
            self._status(self._tr("rank_empty"), error=True)
            return
        n = self.add_image_paths([os.path.join(out, f) for f in files])
        self._status(self._tr("rank_loaded").format(n=n))

    def _render_preview(self, pg):
        img = pg["img"].convertToFormat(QImage.Format_ARGB32)
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing, True)
        fnt = QFont()
        fnt.setBold(True)
        fs = max(12, img.width() // 60)
        fnt.setPixelSize(fs)
        p.setFont(fnt)
        lw = max(2, img.width() // 400)
        boxes = pg["boxes"]
        for b in boxes:
            kind = b.get("kind", "bubble")
            color = QColor(*self._class_color(kind))
            p.setPen(QPen(color, lw))
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(b["x"], b["y"], b["w"], b["h"]))
            # reading-order number (or class-initial) badge, like the on-screen view
            order = b.get("order", 0)
            label = str(order) if order else (self._class_label(kind)[:1]
                                              or "?").upper()
            bw = max(fs + 6, 6 + int(fs * 0.7) * len(label))
            badge = QRectF(b["x"], b["y"], bw, fs + 6)
            p.fillRect(badge, color)
            p.setPen(QPen(QColor(255, 255, 255)))
            p.drawText(badge, Qt.AlignCenter, label)
        # reading-order path (mirrors the on-screen "Order path" toggle)
        if getattr(self, "path_chk", None) is not None and self.path_chk.isChecked():
            pts = sorted(((b["order"], b["x"] + b["w"] / 2.0,
                           b["y"] + b["h"] / 2.0)
                          for b in boxes if b.get("order")), key=lambda z: z[0])
            if len(pts) >= 2:
                col = QColor(255, 205, 40, 235)
                p.setPen(QPen(col, lw))
                p.setBrush(Qt.NoBrush)
                for (_a, x0, y0), (_b, x1, y1) in zip(pts, pts[1:]):
                    p.drawLine(QPointF(x0, y0), QPointF(x1, y1))
                ah = max(7, img.width() // 120)
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(col))
                for (_a, x0, y0), (_b, x1, y1) in zip(pts, pts[1:]):
                    mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
                    ang = math.atan2(y1 - y0, x1 - x0)
                    a1, a2 = ang + math.radians(148), ang - math.radians(148)
                    head = QPolygonF([
                        QPointF(mx + ah * math.cos(ang), my + ah * math.sin(ang)),
                        QPointF(mx + ah * math.cos(a1), my + ah * math.sin(a1)),
                        QPointF(mx + ah * math.cos(a2), my + ah * math.sin(a2)),
                    ])
                    p.drawPolygon(head)
        p.end()
        return img

    def _export_page(self, pg, images, labels, order, preview):
        w, h = pg["img"].width(), pg["img"].height()
        stem = "%s_%d" % (pg["name"], int(time.time() * 1000) % 10 ** 9)
        if not pg["img"].save(os.path.join(images, stem + ".png"), "PNG"):
            raise IOError("could not write page image")
        with open(os.path.join(labels, stem + ".txt"), "w", encoding="utf-8") as fh:
            fh.write(make_yolo_label(pg["boxes"], w, h, self._class_index_map()))
        with open(os.path.join(order, stem + ".json"), "w", encoding="utf-8") as fh:
            json.dump(order_data(pg["boxes"], w, h, self._class_index_map()),
                      fh, indent=2)
        try:
            self._render_preview(pg).save(os.path.join(preview, stem + ".png"), "PNG")
        except Exception:
            pass
        pg["exported"] = True         # mark it saved so the strip shows a ✓
        return stem

    @staticmethod
    def _page_bucket(pg):
        """A stable 0..99 bucket for a page (by its source path/name), so the
        same page always lands in the same train/val split across exports."""
        key = (pg.get("path") or pg.get("name") or "").encode("utf-8", "ignore")
        return zlib.crc32(key) % 100

    def _write_class_files(self):
        """Write classes.txt + data.yaml to the dataset root so the export can be
        trained with YOLO/Ultralytics straight away."""
        if not self._folder or not os.path.isdir(self._folder):
            return
        names = [c["label"] for c in self._classes]
        val = "images/val" if self._val_split > 0 else "images/train"
        val_note = ("" if self._val_split > 0
                    else "        # no held-out split is made here")
        try:
            with open(os.path.join(self._folder, "classes.txt"), "w",
                      encoding="utf-8") as fh:
                fh.write("\n".join(names) + "\n")
            root = os.path.abspath(self._folder).replace("\\", "/")
            lines = [
                "# BubblR Trainer export — YOLO / Ultralytics dataset config",
                "path: %s" % root,
                "train: images/train",
                "val: %s%s" % (val, val_note),
                "nc: %d" % len(names),
                "names:",
            ]
            for i, n in enumerate(names):
                safe = n.replace('"', "'")
                lines.append('  %d: "%s"' % (i, safe))
            with open(os.path.join(self._folder, "data.yaml"), "w",
                      encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
        except OSError:
            pass

    def on_export(self, all_pages):
        pages = self._pages if all_pages else ([self._page()] if self._page() else [])
        pages = [p for p in pages if p and p["boxes"]]
        if not self._pages:
            self._status(self._tr("no_page"), error=True)
            return
        if not pages:
            self._status(self._tr("no_boxes"), error=True)
            return
        if not self._folder or not os.path.isdir(self._folder):
            self._status(self._tr("no_folder"), error=True)
            return
        try:
            base = self._folder
            images_tr = os.path.join(base, "images", "train")
            labels_tr = os.path.join(base, "labels", "train")
            images_va = os.path.join(base, "images", "val")
            labels_va = os.path.join(base, "labels", "val")
            order = os.path.join(base, "order")
            preview = os.path.join(base, "preview")
            dirs = [images_tr, labels_tr, order, preview]
            if self._val_split > 0:
                dirs += [images_va, labels_va]
            for d in dirs:
                os.makedirs(d, exist_ok=True)
            last = ""
            for pg in pages:
                to_val = (self._val_split > 0
                          and self._page_bucket(pg) < self._val_split)
                imgs = images_va if to_val else images_tr
                lbls = labels_va if to_val else labels_tr
                last = self._export_page(pg, imgs, lbls, order, preview)
                time.sleep(0.002)      # keep timestamp stems unique
            self._write_class_files()  # classes.txt + data.yaml for YOLO
        except Exception as exc:
            self._status(self._tr("export_fail").format(msg=exc), error=True)
            return
        self._refresh()                    # update the exported counter
        if hasattr(self, "page_strip"):
            self._rebuild_page_strip()     # show the fresh ✓ export markers
        if all_pages:
            self._status(self._tr("exported_all").format(n=len(pages)))
            if self._export_summary_on:
                self._show_export_summary(pages)
        else:
            self._status(self._tr("exported_one").format(name=last + ".png"))

    def _show_export_summary(self, pages):
        """A short recap after an 'export all': pages, train/val split and how
        many objects of each class went out."""
        counts = {c["key"]: 0 for c in self._classes}
        train = val = 0
        for pg in pages:
            if self._val_split > 0 and self._page_bucket(pg) < self._val_split:
                val += 1
            else:
                train += 1
            for b in pg["boxes"]:
                k = b.get("kind", "bubble")
                counts[k] = counts.get(k, 0) + 1
        total = sum(counts.values())
        t = self._tr
        lines = [t("summary_pages").format(n=len(pages), tr=train, va=val), ""]
        lines.append(t("summary_objects"))
        for c in self._classes:
            lines.append("   %s: %d" % (c["label"], counts.get(c["key"], 0)))
        lines += ["", t("summary_total").format(n=total),
                  "", "%s" % os.path.abspath(self._folder)]
        QMessageBox.information(self, t("summary_title"), "\n".join(lines))

    def on_save_project(self):
        start = os.path.join(self._start_dir(), "project.json")
        path, _f = QFileDialog.getSaveFileName(
            self, self._tr("save"), start, self._tr("proj_filter"))
        if not path:
            return
        self._remember_dir(os.path.dirname(path))
        data = {"pages": [{"path": p["path"], "name": p["name"],
                           "boxes": p["boxes"]} for p in self._pages]}
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
        except Exception as exc:
            self._status(self._tr("load_fail").format(msg=exc), error=True)
            return
        self._status(self._tr("saved"))

    @staticmethod
    def _load_pages_from(path):
        """Build the page list from a project/recovery .json (skips missing
        images). Returns [] on error."""
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:                    # noqa: BLE001
            return []
        pages = []
        for pd in data.get("pages", []):
            img = QImage(pd.get("path", ""))
            if img.isNull():
                continue
            boxes = []
            for b in pd.get("boxes", []):
                nb = {"x": int(b["x"]), "y": int(b["y"]),
                      "w": int(b["w"]), "h": int(b["h"]),
                      "kind": "sfx" if b.get("kind") == "sfx" else "bubble",
                      "order": int(b.get("order", 0) or 0),
                      "shape": b.get("shape", "rect")}
                if isinstance(b.get("points"), list):
                    nb["points"] = b["points"]
                boxes.append(nb)
            pages.append({"path": pd.get("path", ""),
                          "name": pd.get("name", "page"),
                          "img": img.convertToFormat(QImage.Format_RGB888),
                          "boxes": boxes})
        return pages

    def on_load_project(self):
        path, _f = QFileDialog.getOpenFileName(
            self, self._tr("load_proj"), self._start_dir(),
            self._tr("proj_filter"))
        if not path:
            return
        self._remember_dir(os.path.dirname(path))
        pages = self._load_pages_from(path)
        self._pages = pages
        self._cur = -1
        self._reset_history()
        if pages:
            self._goto(0)
        else:
            self._refresh()
        self._status(self._tr("loaded_proj").format(n=len(pages)))

    # -- first-run desktop / start-menu shortcut --
    def maybe_prompt_shortcut(self):
        """On the very first launch (Windows only), offer to create shortcuts
        via a clickable dialog. A marker file keeps it from asking again."""
        if os.name != "nt" or os.path.exists(SHORTCUT_MARK):
            return
        try:
            self._shortcut_dialog()
        finally:
            try:
                with open(SHORTCUT_MARK, "w", encoding="utf-8") as fh:
                    fh.write("1")
            except OSError:
                pass

    def _shortcut_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(self._tr("sc_title"))
        dlg.setWindowIcon(app_icon())
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel(self._tr("sc_msg")))
        cb_desktop = QCheckBox(self._tr("sc_desktop"))
        cb_desktop.setChecked(True)
        cb_start = QCheckBox(self._tr("sc_startmenu"))
        cb_start.setChecked(True)
        lay.addWidget(cb_desktop)
        lay.addWidget(cb_start)
        bb = QDialogButtonBox()
        bb.addButton(self._tr("sc_create"), QDialogButtonBox.AcceptRole)
        bb.addButton(self._tr("sc_skip"), QDialogButtonBox.RejectRole)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        if dlg.exec_() == QDialog.Accepted:
            self._create_shortcuts(cb_desktop.isChecked(), cb_start.isChecked())

    def _create_shortcuts(self, desktop, startmenu):
        if not (desktop or startmenu):
            self._status(self._tr("sc_none"))
            return
        cmd = _shortcut_command(desktop, startmenu)
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)   # no console flash
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-Command", cmd],
                creationflags=flags, timeout=30)
            self._status(self._tr("sc_done"))
        except Exception as exc:                    # noqa: BLE001
            self._status(str(exc), error=True)


def apply_krita_dark(app):
    """A dark, flat theme in the spirit of Krita's default 'dark' look:
    Fusion style + a dark palette (so menus, dialogs, combos and scrollbars are
    dark too) plus a few accents in Krita's blue."""
    app.setStyle("Fusion")
    C = QColor
    win_bg, base, text = C(0x31, 0x36, 0x3b), C(0x23, 0x26, 0x29), C(0xef, 0xf0, 0xf1)
    accent, disabled = C(0x3d, 0xae, 0xe9), C(0x7f, 0x8c, 0x8d)
    p = QPalette()
    p.setColor(QPalette.Window, win_bg)
    p.setColor(QPalette.WindowText, text)
    p.setColor(QPalette.Base, base)
    p.setColor(QPalette.AlternateBase, win_bg)
    p.setColor(QPalette.ToolTipBase, win_bg)
    p.setColor(QPalette.ToolTipText, text)
    p.setColor(QPalette.Text, text)
    p.setColor(QPalette.Button, C(0x3a, 0x40, 0x45))
    p.setColor(QPalette.ButtonText, text)
    p.setColor(QPalette.BrightText, C(0xff, 0x40, 0x40))
    p.setColor(QPalette.Link, accent)
    p.setColor(QPalette.Highlight, accent)
    p.setColor(QPalette.HighlightedText, base)
    for role in (QPalette.Text, QPalette.ButtonText, QPalette.WindowText):
        p.setColor(QPalette.Disabled, role, disabled)
    app.setPalette(p)
    app.setStyleSheet(
        "QMainWindow{background:#2b2e33;}"
        "QToolTip{color:#eff0f1;background:#31363b;border:1px solid #4d4d4d;}"
        "QPushButton{padding:5px 9px;border:1px solid #4d4d4d;border-radius:3px;"
        "background:#3a4045;}"
        "QPushButton:hover{background:#454b50;}"
        "QPushButton:pressed{background:#2c3135;}"
        "QPushButton:checked{background:#2f6f9f;border-color:#3daee9;}"
        "QPushButton:disabled{color:#7f8c8d;background:#33383c;}"
        "QComboBox{padding:3px 6px;border:1px solid #4d4d4d;border-radius:3px;"
        "background:#232629;}"
        "QLabel{color:#eff0f1;}"
        # menu bar + drop-down menus (were light on Windows)
        "QMenuBar{background:#31363b;color:#eff0f1;}"
        "QMenuBar::item{background:transparent;padding:4px 10px;}"
        "QMenuBar::item:selected{background:#3daee9;color:#ffffff;}"
        "QMenu{background:#232629;color:#eff0f1;border:1px solid #4d4d4d;}"
        "QMenu::item:selected{background:#3daee9;color:#ffffff;}"
        "QMenu::separator{height:1px;background:#4d4d4d;margin:4px 6px;}"
        # list widgets (Boxes list + page thumbnail strip)
        "QListWidget{background:#232629;color:#eff0f1;border:1px solid #4d4d4d;}"
        "QListWidget::item:selected{background:#2f6f9f;color:#ffffff;}"
        # labelling progress bar
        "QProgressBar{background:#232629;border:1px solid #4d4d4d;"
        "border-radius:3px;text-align:center;color:#eff0f1;}"
        "QProgressBar::chunk{background:#3daee9;border-radius:2px;}"
        # dockable panels (Tools / Boxes / Pages) — medium-height headers
        "QDockWidget{color:#eff0f1;font-weight:bold;}"
        "QDockWidget::title{background:#31363b;padding:6px 10px;"
        "border-bottom:1px solid #4d4d4d;}"
        "QDockWidget::close-button,QDockWidget::float-button{"
        "subcontrol-position:top right;padding:2px;}"
        "QTabBar::tab{background:#31363b;color:#eff0f1;padding:5px 12px;"
        "border:1px solid #4d4d4d;}"
        "QTabBar::tab:selected{background:#3daee9;color:#ffffff;}"
        "QMainWindow::separator{background:#31363b;width:5px;height:5px;}"
        # the movable actions toolbar
        "QToolBar{background:#31363b;border-top:1px solid #4d4d4d;spacing:3px;"
        "padding:3px;}"
        "QToolBar::separator{background:#4d4d4d;width:1px;margin:3px 5px;}"
        # thin bottom status bar
        "QStatusBar{background:#31363b;color:#eff0f1;}"
        "QStatusBar QLabel{color:#eff0f1;}"
        "QStatusBar::item{border:0;}")


def _resource(*parts):
    """Path to a bundled resource, both when run as a .py and as a PyInstaller
    exe (which unpacks data under sys._MEIPASS)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def app_icon():
    """The BubblR speech-bubble icon, if the asset is present."""
    for name in ("icon.ico", "icon.png"):
        p = _resource("assets", name)
        if os.path.exists(p):
            return QIcon(p)
    return QIcon()


def _pythonw():
    """A windowless interpreter (pythonw) next to the current one, else python."""
    d = os.path.dirname(sys.executable)
    for name in ("pythonw.exe", "python.exe"):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return sys.executable


def _ps_quote(s):
    """Single-quote a string for PowerShell (doubling any single quotes)."""
    return "'" + str(s).replace("'", "''") + "'"


def _shortcut_command(desktop, startmenu):
    """A PowerShell command that creates the chosen shortcut(s). Runs a frozen
    exe directly, else the Python app via pythonw (no console window)."""
    if getattr(sys, "frozen", False):
        target, args, workdir = sys.executable, "", os.path.dirname(sys.executable)
    else:
        script = os.path.abspath(__file__)
        target, args, workdir = _pythonw(), '"%s"' % script, os.path.dirname(script)
    icon = _resource("assets", "icon.ico")
    folders = []
    if desktop:
        folders.append("[Environment]::GetFolderPath('Desktop')")
    if startmenu:
        folders.append("[Environment]::GetFolderPath('Programs')")
    lines = ["$w = New-Object -ComObject WScript.Shell"]
    for folder in folders:
        lines += [
            "$l = Join-Path (%s) 'BubblR Trainer.lnk'" % folder,
            "$s = $w.CreateShortcut($l)",
            "$s.TargetPath = %s" % _ps_quote(target),
            "$s.Arguments = %s" % _ps_quote(args),
            "$s.WorkingDirectory = %s" % _ps_quote(workdir),
        ]
        if os.path.exists(icon):
            lines.append("$s.IconLocation = %s" % _ps_quote(icon + ",0"))
        lines += ["$s.Description = 'BubblR Trainer'", "$s.Save()"]
    return "; ".join(lines)


def main():
    app = QApplication(sys.argv)
    apply_krita_dark(app)
    app.setWindowIcon(app_icon())           # taskbar / window / alt-tab icon

    # Building the first widget triggers Qt's Windows font-database load, which
    # is slow on machines with a huge font collection (nothing the app can skip
    # — it's the OS font count). Show an instant splash first so startup does
    # not look frozen. The splash text is baked into the image, so drawing it
    # needs no font metrics and it appears immediately.
    splash = None
    sp = _resource("assets", "splash.png")
    if os.path.exists(sp):
        splash = QSplashScreen(QPixmap(sp))
        splash.show()
        app.processEvents()

    win = TrainerWindow()
    win.setWindowIcon(app_icon())
    win.show()
    if splash is not None:
        splash.finish(win)
    # offer to recover a session left over from a crash, then (first launch)
    # offer to create shortcuts
    win.maybe_offer_recovery()
    win.maybe_prompt_shortcut()
    # image paths passed on the command line open straight away as pages
    # (used by "Open in BubblR Trainer" in the BubblR AI ranking tool)
    args = [a for a in app.arguments()[1:]
            if a.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp"))
            and os.path.isfile(a)]
    if args:
        win.add_image_paths(args)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
