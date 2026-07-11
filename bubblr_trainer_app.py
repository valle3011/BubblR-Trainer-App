# -*- coding: utf-8 -*-
"""BubblR Trainer - standalone desktop app.

Same job as the Krita/Photoshop BubblR Trainer plugins, but a normal window
program: load page images from disk, draw + label bubble/SFX boxes, set the
reading order, and export a YOLO dataset. No Krita, no Photoshop.

Run:  python bubblr_trainer_app.py     (needs Python 3 + PyQt5)
"""
import copy
import json
import os
import subprocess
import sys
import time

from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy, QButtonGroup, QFileDialog, QComboBox,
    QMessageBox, QCheckBox, QSpinBox, QShortcut, QSplashScreen,
    QDialog, QDialogButtonBox)
from PyQt5.QtGui import (QColor, QFont, QPainter, QPen, QBrush, QImage,
                         QPalette, QPolygonF, QKeySequence, QIcon, QPixmap)
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPoint, QPointF

VERSION = "1.5"
KIND_CLASS = {"bubble": 0, "sfx": 1}
KIND_COLOR = {"bubble": (230, 60, 60), "sfx": (70, 130, 230)}
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".bubblr_trainer.json")
SHORTCUT_MARK = os.path.join(os.path.expanduser("~"),
                             ".bubblr_trainer_shortcut_asked")

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
        "counts": "This page - Bubbles: {b}   SFX: {s}   |   Pages: {done}/{p} labelled",
        "sort_by": "Sort pages:",
        "sort_name": "by name",
        "sort_unlabeled": "unlabelled first",
        "sort_fewest": "fewest boxes first",
        "sort_most": "most boxes first",
        "next_todo": "Next unlabelled",
        "all_labelled": "All pages have at least one box.",
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
        "sh_text": ("B / S — set the selected box to Bubble / SFX\n"
                    "Delete / Backspace — delete the selected box\n"
                    "Arrow keys — nudge the selected box (Shift = 10 px)\n"
                    "Esc — deselect\n"
                    "[  /  ]  — previous / next page\n"
                    "Ctrl+Z — undo     Ctrl+Y or Ctrl+Shift+Z — redo\n"
                    "Ctrl+W — close the current page\n"
                    "Mouse wheel — zoom     middle-drag — pan\n"
                    "F1 — show this help"),
        "save": "Save project…", "load_proj": "Load project…",
        "folder_none": "Dataset folder: (none chosen)",
        "folder": "Dataset folder: {path}", "choose": "Choose folder…",
        "export_page": "Export this page", "export_all": "Export all pages",
        "ready": "Load page images to begin.",
        "loaded": "{n} image(s) loaded.",
        "no_page": "Load a page first.", "no_boxes": "Draw at least one box first.",
        "no_folder": "Choose a dataset folder first.",
        "order_hint": "Click the bubbles in reading order (1, 2, 3 …).",
        "order_cleared": "Reading order cleared.",
        "exported_one": "Exported: {name}",
        "exported_all": "Exported {n} page(s) to the dataset folder.",
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
        "counts": "Diese Seite – Bubbles: {b}   SFX: {s}   |   Seiten: {done}/{p} gelabelt",
        "sort_by": "Seiten sortieren:",
        "sort_name": "nach Name",
        "sort_unlabeled": "ungelabelte zuerst",
        "sort_fewest": "wenigste Boxen zuerst",
        "sort_most": "meiste Boxen zuerst",
        "next_todo": "Nächste ungelabelte",
        "all_labelled": "Alle Seiten haben mindestens eine Box.",
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
        "sh_text": ("B / S — ausgewählte Box auf Bubble / SFX setzen\n"
                    "Entf / Rücktaste — ausgewählte Box löschen\n"
                    "Pfeiltasten — ausgewählte Box verschieben (Umschalt = 10 px)\n"
                    "Esc — Auswahl aufheben\n"
                    "[  /  ]  — vorige / nächste Seite\n"
                    "Strg+Z — rückgängig     Strg+Y oder Umschalt+Strg+Z — wiederh.\n"
                    "Strg+W — aktuelle Seite schließen\n"
                    "Mausrad — Zoom     Mittel-Ziehen — verschieben\n"
                    "F1 — diese Hilfe anzeigen"),
        "save": "Projekt speichern…", "load_proj": "Projekt laden…",
        "folder_none": "Datensatz-Ordner: (keiner gewählt)",
        "folder": "Datensatz-Ordner: {path}", "choose": "Ordner wählen…",
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
        "export_fail": "Export fehlgeschlagen: {msg}",
        "saved": "Projekt gespeichert.", "loaded_proj": "Projekt geladen ({n} Seite(n)).",
        "load_fail": "Konnte nicht laden: {msg}",
        "img_filter": "Bilder (*.png *.jpg *.jpeg *.webp *.bmp)",
        "proj_filter": "BubblR-Projekt (*.json)",
        "lang": "Sprache",
    },
}


def make_yolo_label(boxes, img_w, img_h):
    lines = []
    for b in boxes:
        cls = KIND_CLASS.get(b.get("kind", "bubble"), 0)
        cx = min(1.0, max(0.0, (b["x"] + b["w"] / 2.0) / float(img_w)))
        cy = min(1.0, max(0.0, (b["y"] + b["h"] / 2.0) / float(img_h)))
        w = min(1.0, max(0.0, b["w"] / float(img_w)))
        h = min(1.0, max(0.0, b["h"] / float(img_h)))
        lines.append("%d %.6f %.6f %.6f %.6f" % (cls, cx, cy, w, h))
    return "\n".join(lines) + "\n" if lines else ""


def order_data(boxes, img_w, img_h):
    indexed = list(enumerate(boxes))
    indexed.sort(key=lambda p: (p[1].get("order") or 10 ** 9, p[0]))
    out = []
    for seq, (_i, b) in enumerate(indexed, start=1):
        kind = b.get("kind", "bubble")
        out.append({
            "order": seq, "set": bool(b.get("order")), "kind": kind,
            "class": KIND_CLASS.get(kind, 0),
            "x": int(b["x"]), "y": int(b["y"]),
            "w": int(b["w"]), "h": int(b["h"]),
            "cx": (b["x"] + b["w"] / 2.0) / float(img_w),
            "cy": (b["y"] + b["h"] / 2.0) / float(img_h),
            "nw": b["w"] / float(img_w), "nh": b["h"] / float(img_h),
        })
    return {"width": img_w, "height": img_h, "boxes": out}


def auto_order(boxes, rtl=True):
    """Rank the boxes into a reading order automatically: group them into rows
    (top to bottom), then order within a row right-to-left for manga (rtl) or
    left-to-right otherwise. Fills each box's 'order'. You only fix the few it
    gets wrong instead of clicking every bubble."""
    n = len(boxes)
    if n == 0:
        return
    order_by_y = sorted(range(n),
                        key=lambda i: boxes[i]["y"] + boxes[i]["h"] / 2.0)
    heights = sorted(boxes[i]["h"] for i in order_by_y)
    band = max(1.0, heights[n // 2] * 0.6)     # ~60% of the median height
    rows = []
    for i in order_by_y:
        cy = boxes[i]["y"] + boxes[i]["h"] / 2.0
        if rows and cy - rows[-1]["anchor"] <= band:
            rows[-1]["items"].append(i)
        else:
            rows.append({"anchor": cy, "items": [i]})
    rank = 1
    for row in rows:
        row["items"].sort(
            key=lambda i: boxes[i]["x"] + boxes[i]["w"] / 2.0, reverse=rtl)
        for i in row["items"]:
            boxes[i]["order"] = rank
            rank += 1


# ---------------------------------------------------------------------------
# Box overlay (pure Qt; ported from the Krita trainer plugin)
# ---------------------------------------------------------------------------

class BoxOverlay(QWidget):
    boxClicked = pyqtSignal(int)
    boxRemoved = pyqtSignal(int)
    # x, y, w, h, shape ("rect"/"ellipse"/"lasso"/"wand"), points (list or None)
    boxAdded = pyqtSignal(float, float, float, float, str, object)
    boxChanged = pyqtSignal(int, float, float, float, float)

    _HANDLE = 9

    def __init__(self):
        super(BoxOverlay, self).__init__()
        self._img = None
        self._doc_w = 1
        self._doc_h = 1
        self._boxes = []
        self._current = -1
        self._edit = False
        self._drag = None
        self._zoom = 1.0          # 1.0 = fit to the widget
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._panning = None      # last pos while middle-drag panning
        self._tool = "rect"       # rect | ellipse | lasso | wand
        self._show_center = True  # draw a marker at each box's centre
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

    def set_wand_tolerance(self, value):
        self._wand_tol = max(1, min(255, int(value)))

    def set_page(self, img, doc_w, doc_h):
        self._img = img
        self._doc_w = max(1, doc_w)
        self._doc_h = max(1, doc_h)
        self.fit()                # a new page starts fitted

    def set_boxes(self, boxes, current=-1):
        self._boxes = boxes
        self._current = current
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
            r = QRectF(t.x() + b["x"] * scale, t.y() + b["y"] * scale,
                       b["w"] * scale, b["h"] * scale)
            color = QColor(*KIND_COLOR.get(b.get("kind", "bubble"),
                                           KIND_COLOR["bubble"]))
            p.setPen(QPen(color, 3 if k == self._current else 2))
            p.setBrush(Qt.NoBrush)
            self._draw_shape(p, r, b.get("shape", "rect"),
                             b.get("points"), t, scale)
            if self._show_center:
                self._draw_center(p, r.center(), color, big=(k == self._current))
            order = b.get("order", 0)
            label = str(order) if order else ("B" if b.get("kind") != "sfx" else "S")
            badge = QRectF(r.x(), r.y(), max(18, 8 + 8 * len(label)), 16)
            p.fillRect(badge, color)
            p.setPen(QPen(QColor(255, 255, 255)))
            p.drawText(badge, Qt.AlignCenter, label)
            if self._edit:
                p.setBrush(QBrush(QColor(255, 255, 255)))
                p.setPen(QPen(QColor(30, 30, 30), 1))
                for hx, hy in ((r.left(), r.top()), (r.right(), r.top()),
                               (r.left(), r.bottom()), (r.right(), r.bottom())):
                    p.drawRect(QRectF(hx - 3, hy - 3, 6, 6))
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

    def _hit(self, pos):
        t = self._target()
        if t.width() <= 0:
            return -1
        scale = t.width() / float(self._doc_w)
        x = (pos.x() - t.x()) / scale
        y = (pos.y() - t.y()) / scale
        best, best_area = -1, None
        for k, b in enumerate(self._boxes):
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
        """What the point hits on box `k`: (k, corner) for a resize handle,
        (k, 'move') inside the box, or None."""
        b = self._boxes[k]
        x0 = t.x() + b["x"] * scale
        y0 = t.y() + b["y"] * scale
        x1 = x0 + b["w"] * scale
        y1 = y0 + b["h"] * scale
        corners = {"nw": (x0, y0), "ne": (x1, y0),
                   "sw": (x0, y1), "se": (x1, y1)}
        for name, (cx, cy) in corners.items():
            if abs(pos.x() - cx) <= self._HANDLE \
                    and abs(pos.y() - cy) <= self._HANDLE:
                return (k, name)
        if x0 <= pos.x() <= x1 and y0 <= pos.y() <= y1:
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
        if 0 <= cur < len(self._boxes):
            hit = self._probe_box(cur, pos, t, scale)
            if hit is not None:
                return hit
        # otherwise: any corner wins (resize), else the smallest box (move)
        best, best_area = None, None
        for k in range(len(self._boxes)):
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
        return self._norm(d["fx"], d["fy"], d["cx"], d["cy"])

    def _clamp(self, x, y, w, h):
        x = max(0.0, min(x, self._doc_w - 1))
        y = max(0.0, min(y, self._doc_h - 1))
        w = min(w, self._doc_w - x)
        h = min(h, self._doc_h - y)
        return x, y, w, h

    def mousePressEvent(self, event):
        self.setFocus()                      # take keyboard focus for nudging
        if event.button() == Qt.MiddleButton:
            self._panning = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            return
        if event.button() == Qt.RightButton:
            idx = self._hit(event.pos())
            if idx >= 0:
                self.boxRemoved.emit(idx)
            return
        if event.button() != Qt.LeftButton:
            return
        if self._edit:
            self._begin_edit(event.pos())
            return
        idx = self._hit(event.pos())
        if idx >= 0:
            self.boxClicked.emit(idx)

    def keyPressEvent(self, event):
        # arrow keys nudge the selected box (Shift = 10 px); pan otherwise
        k = event.key()
        arrows = (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down)
        if k in arrows and 0 <= self._current < len(self._boxes):
            step = 10 if event.modifiers() & Qt.ShiftModifier else 1
            b = self._boxes[self._current]
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
        # resizing an existing box (grabbing a corner) always wins
        if hit is not None and hit[1] != "move":
            idx, corner = hit
            b = self._boxes[idx]
            fx = b["x"] + b["w"] if corner in ("nw", "sw") else b["x"]
            fy = b["y"] + b["h"] if corner in ("nw", "ne") else b["y"]
            self._drag = {"mode": "resize", "idx": idx, "fx": fx, "fy": fy,
                          "cx": dx, "cy": dy, "obx": b["x"], "oby": b["y"],
                          "obw": b["w"], "obh": b["h"]}
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
        if not self._edit or self._drag is None:
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


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class TrainerWindow(QMainWindow):
    def __init__(self):
        super(TrainerWindow, self).__init__()
        cfg = self._load_settings()
        self._lang = cfg.get("lang", "en")
        self._folder = cfg.get("folder", "")
        self._pages = []          # [{path, name, img: QImage, boxes: []}]
        self._cur = -1
        self._new_kind = "bubble"
        self._order_mode = False
        self._order_counter = 1
        self._undo = []           # snapshots of (page index, boxes, selection)
        self._redo = []

        root = QWidget()
        lay = QVBoxLayout()
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)
        root.setLayout(lay)

        head = QHBoxLayout()
        self.lbl_intro = QLabel(self._tr("intro"))
        self.lbl_intro.setWordWrap(True)
        self.lbl_intro.setStyleSheet("color: gray;")
        head.addWidget(self.lbl_intro, 1)
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("Deutsch", "de")
        self.lang_combo.setCurrentIndex(0 if self._lang == "en" else 1)
        self.lang_combo.currentIndexChanged.connect(self._on_lang)
        head.addWidget(self.lang_combo)
        lay.addLayout(head)

        top = QHBoxLayout()
        self.load_btn = QPushButton(self._tr("load"))
        self.load_btn.clicked.connect(self.on_load_images)
        top.addWidget(self.load_btn)
        self.lbl_sort = QLabel(self._tr("sort_by"))
        top.addWidget(self.lbl_sort)
        self.sort_combo = QComboBox()
        for _k in ("name", "unlabeled", "fewest", "most"):
            self.sort_combo.addItem(self._tr("sort_" + _k), _k)
        self.sort_combo.currentIndexChanged.connect(self._sort_pages)
        top.addWidget(self.sort_combo)
        self.next_todo_btn = QPushButton(self._tr("next_todo"))
        self.next_todo_btn.clicked.connect(self.on_next_todo)
        top.addWidget(self.next_todo_btn)
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
        lay.addLayout(top)

        self.overlay = BoxOverlay()
        self.overlay.boxAdded.connect(self._on_box_added)
        self.overlay.boxChanged.connect(self._on_box_changed)
        self.overlay.boxRemoved.connect(self._on_box_removed)
        self.overlay.boxClicked.connect(self._on_box_clicked)
        lay.addWidget(self.overlay, 1)

        shape_row = QHBoxLayout()
        self.lbl_tool = QLabel(self._tr("tool"))
        shape_row.addWidget(self.lbl_tool)
        self._tg = QButtonGroup(self)
        self._tg.setExclusive(True)
        self.tool_btns = {}
        for _key in ("rect", "ellipse", "lasso", "wand"):
            btn = QPushButton(self._tr("tool_" + _key))
            btn.setCheckable(True)
            btn.setToolTip(self._tr("tool_" + _key + "_hint"))
            btn.clicked.connect(lambda _c, k=_key: self._on_tool(k))
            btn.setStyleSheet("QPushButton:checked{background:#3daee9;color:white;}")
            self._tg.addButton(btn)
            shape_row.addWidget(btn)
            self.tool_btns[_key] = btn
        self.tool_btns["rect"].setChecked(True)
        shape_row.addSpacing(10)
        self.lbl_tol = QLabel(self._tr("wand_tol"))
        shape_row.addWidget(self.lbl_tol)
        self.tol_spin = QSpinBox()
        self.tol_spin.setRange(1, 255)
        self.tol_spin.setValue(40)
        self.tol_spin.setFixedWidth(58)
        self.tol_spin.setToolTip(self._tr("wand_tol_tip"))
        self.tol_spin.valueChanged.connect(self.overlay.set_wand_tolerance)
        shape_row.addWidget(self.tol_spin)
        shape_row.addSpacing(10)
        self.center_chk = QCheckBox(self._tr("center_marker"))
        self.center_chk.setChecked(True)
        self.center_chk.setToolTip(self._tr("center_marker_tip"))
        self.center_chk.toggled.connect(self.overlay.set_center_marker)
        shape_row.addWidget(self.center_chk)
        shape_row.addStretch(1)
        lay.addLayout(shape_row)

        tools = QHBoxLayout()
        self.undo_btn = QPushButton(self._tr("undo"))
        self.undo_btn.setToolTip(self._tr("undo_tip"))
        self.undo_btn.clicked.connect(self.undo)
        tools.addWidget(self.undo_btn)
        self.redo_btn = QPushButton(self._tr("redo"))
        self.redo_btn.setToolTip(self._tr("redo_tip"))
        self.redo_btn.clicked.connect(self.redo)
        tools.addWidget(self.redo_btn)
        self.edit_btn = QPushButton(self._tr("edit"))
        self.edit_btn.setCheckable(True)
        self.edit_btn.toggled.connect(self._on_edit_toggle)
        tools.addWidget(self.edit_btn)
        self.order_btn = QPushButton(self._tr("set_order"))
        self.order_btn.setCheckable(True)
        self.order_btn.toggled.connect(self._on_order_toggle)
        tools.addWidget(self.order_btn)
        self.auto_order_btn = QPushButton(self._tr("auto_order"))
        self.auto_order_btn.setToolTip(self._tr("auto_order_tip"))
        self.auto_order_btn.clicked.connect(self.on_auto_order)
        tools.addWidget(self.auto_order_btn)
        self.rtl_chk = QCheckBox(self._tr("rtl"))
        self.rtl_chk.setChecked(True)
        self.rtl_chk.setToolTip(self._tr("rtl_tip"))
        tools.addWidget(self.rtl_chk)
        self.del_btn = QPushButton(self._tr("delete"))
        self.del_btn.clicked.connect(self.on_delete)
        tools.addWidget(self.del_btn)
        self.clear_order_btn = QPushButton(self._tr("clear_order"))
        self.clear_order_btn.clicked.connect(self.on_clear_order)
        tools.addWidget(self.clear_order_btn)
        self.clear_btn = QPushButton(self._tr("clear"))
        self.clear_btn.clicked.connect(self.on_clear)
        tools.addWidget(self.clear_btn)
        lay.addLayout(tools)

        kind_row = QHBoxLayout()
        self.lbl_kind = QLabel(self._tr("kind"))
        kind_row.addWidget(self.lbl_kind)
        self._kg = QButtonGroup(self)
        self._kg.setExclusive(True)
        self.bubble_btn = QPushButton(self._tr("bubble"))
        self.bubble_btn.setCheckable(True)
        self.bubble_btn.setChecked(True)
        self.bubble_btn.clicked.connect(lambda: self._set_kind("bubble"))
        self.sfx_btn = QPushButton(self._tr("sfx"))
        self.sfx_btn.setCheckable(True)
        self.sfx_btn.clicked.connect(lambda: self._set_kind("sfx"))
        self._kg.addButton(self.bubble_btn)
        self._kg.addButton(self.sfx_btn)
        self.bubble_btn.setStyleSheet("QPushButton:checked{background:#e63c3c;color:white;}")
        self.sfx_btn.setStyleSheet("QPushButton:checked{background:#4682e6;color:white;}")
        kind_row.addWidget(self.bubble_btn)
        kind_row.addWidget(self.sfx_btn)
        kind_row.addStretch(1)
        lay.addLayout(kind_row)

        self.lbl_relabel = QLabel(self._tr("relabel"))
        self.lbl_relabel.setStyleSheet("color: gray;")
        lay.addWidget(self.lbl_relabel)
        self.lbl_counts = QLabel("")
        lay.addWidget(self.lbl_counts)

        io_row = QHBoxLayout()
        self.save_btn = QPushButton(self._tr("save"))
        self.save_btn.clicked.connect(self.on_save_project)
        io_row.addWidget(self.save_btn)
        self.loadp_btn = QPushButton(self._tr("load_proj"))
        self.loadp_btn.clicked.connect(self.on_load_project)
        io_row.addWidget(self.loadp_btn)
        lay.addLayout(io_row)

        fold_row = QHBoxLayout()
        self.folder_lbl = QLabel("")
        self.folder_lbl.setWordWrap(True)
        fold_row.addWidget(self.folder_lbl, 1)
        self.folder_btn = QPushButton(self._tr("choose"))
        self.folder_btn.clicked.connect(self.on_choose_folder)
        fold_row.addWidget(self.folder_btn)
        lay.addLayout(fold_row)

        exp_row = QHBoxLayout()
        self.exp_page_btn = QPushButton(self._tr("export_page"))
        self.exp_page_btn.clicked.connect(lambda: self.on_export(False))
        exp_row.addWidget(self.exp_page_btn)
        self.exp_all_btn = QPushButton(self._tr("export_all"))
        self.exp_all_btn.clicked.connect(lambda: self.on_export(True))
        exp_row.addWidget(self.exp_all_btn)
        lay.addLayout(exp_row)

        self.status = QLabel(self._tr("ready"))
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        build = QLabel("BubblR Trainer v" + VERSION)
        build.setStyleSheet("color: gray; font-size: 10px;")
        build.setAlignment(Qt.AlignRight)
        lay.addWidget(build)

        self.setCentralWidget(root)
        self.setWindowTitle(self._tr("title") + " v" + VERSION)
        self.resize(760, 720)
        geo = cfg.get("geo")
        if geo:                              # restore last window size/position
            try:
                self.restoreGeometry(bytes.fromhex(geo))
            except Exception:                # noqa: BLE001
                pass

        # keyboard shortcuts for fast labelling
        QShortcut(QKeySequence.Undo, self, activated=self.undo)          # Ctrl+Z
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, activated=self.redo)
        QShortcut(QKeySequence("Ctrl+Y"), self, activated=self.redo)
        QShortcut(QKeySequence("Ctrl+W"), self, activated=self.on_close_page)
        QShortcut(QKeySequence("B"), self,
                  activated=lambda: self._kbd_set_kind("bubble"))
        QShortcut(QKeySequence("S"), self,
                  activated=lambda: self._kbd_set_kind("sfx"))
        QShortcut(QKeySequence(Qt.Key_Delete), self, activated=self.on_delete)
        QShortcut(QKeySequence(Qt.Key_Backspace), self, activated=self.on_delete)
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self._deselect)
        QShortcut(QKeySequence("["), self,
                  activated=lambda: self._goto(self._cur - 1))
        QShortcut(QKeySequence("]"), self,
                  activated=lambda: self._goto(self._cur + 1))
        QShortcut(QKeySequence("F1"), self, activated=self._show_shortcuts)
        self._update_undo_buttons()

        self._refresh_folder_label()
        self._refresh()

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
        data = {"lang": self._lang, "folder": self._folder}
        try:
            data["geo"] = bytes(self.saveGeometry()).hex()
        except Exception:                    # noqa: BLE001
            pass
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
        except Exception:
            pass

    def closeEvent(self, event):
        self._save_settings()                # remember window size/position
        super(TrainerWindow, self).closeEvent(event)

    # -- keyboard helpers --
    def _kbd_set_kind(self, kind):
        self._set_kind_buttons(kind)
        self._set_kind(kind)                 # relabels the selected box + default

    def _deselect(self):
        if getattr(self, "_current", -1) != -1:
            self._current = -1
            self._refresh()

    def _show_shortcuts(self):
        QMessageBox.information(self, self._tr("sh_title"), self._tr("sh_text"))

    def _on_lang(self, _i):
        self._lang = self.lang_combo.currentData() or "en"
        self._save_settings()
        self._retranslate()

    def _retranslate(self):
        t = self._tr
        self.setWindowTitle(t("title") + " v" + VERSION)
        self.lbl_intro.setText(t("intro"))
        self.load_btn.setText(t("load"))
        self.lbl_sort.setText(t("sort_by"))
        for i, _k in enumerate(("name", "unlabeled", "fewest", "most")):
            self.sort_combo.setItemText(i, t("sort_" + _k))
        self.next_todo_btn.setText(t("next_todo"))
        self.lbl_tool.setText(t("tool"))
        for _k, _btn in self.tool_btns.items():
            _btn.setText(t("tool_" + _k))
            _btn.setToolTip(t("tool_" + _k + "_hint"))
        self.lbl_tol.setText(t("wand_tol"))
        self.tol_spin.setToolTip(t("wand_tol_tip"))
        self.center_chk.setText(t("center_marker"))
        self.center_chk.setToolTip(t("center_marker_tip"))
        self.undo_btn.setText(t("undo"))
        self.undo_btn.setToolTip(t("undo_tip"))
        self.redo_btn.setText(t("redo"))
        self.redo_btn.setToolTip(t("redo_tip"))
        self.prev_btn.setText(t("prev"))
        self.next_btn.setText(t("next"))
        self.close_btn.setText(t("close_page"))
        self.close_btn.setToolTip(t("close_page_tip"))
        self.close_all_btn.setText(t("close_all"))
        self.close_all_btn.setToolTip(t("close_all_tip"))
        self.zoom_fit_btn.setText(t("fit"))
        self.zoom_fit_btn.setToolTip(t("zoom_tip"))
        self.edit_btn.setText(t("edit"))
        self.order_btn.setText(t("set_order"))
        self.auto_order_btn.setText(t("auto_order"))
        self.auto_order_btn.setToolTip(t("auto_order_tip"))
        self.rtl_chk.setText(t("rtl"))
        self.rtl_chk.setToolTip(t("rtl_tip"))
        self.del_btn.setText(t("delete"))
        self.clear_order_btn.setText(t("clear_order"))
        self.clear_btn.setText(t("clear"))
        self.lbl_kind.setText(t("kind"))
        self.bubble_btn.setText(t("bubble"))
        self.sfx_btn.setText(t("sfx"))
        self.lbl_relabel.setText(t("relabel"))
        self.save_btn.setText(t("save"))
        self.loadp_btn.setText(t("load_proj"))
        self.folder_btn.setText(t("choose"))
        self.exp_page_btn.setText(t("export_page"))
        self.exp_all_btn.setText(t("export_all"))
        self._refresh_folder_label()
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
        self.overlay.set_boxes(boxes, getattr(self, "_current", -1))
        b = sum(1 for x in boxes if x.get("kind") != "sfx")
        s = sum(1 for x in boxes if x.get("kind") == "sfx")
        done = sum(1 for p in self._pages if p["boxes"])
        self.lbl_counts.setText(self._tr("counts").format(
            b=b, s=s, p=len(self._pages), done=done))
        if pg:
            self.page_lbl.setText(self._tr("page").format(
                i=self._cur + 1, n=len(self._pages), name=pg["name"]))
        else:
            self.page_lbl.setText(self._tr("page_none"))

    def _refresh_folder_label(self):
        self.folder_lbl.setText(
            self._tr("folder").format(path=self._folder) if self._folder
            else self._tr("folder_none"))

    def _set_kind(self, kind):
        self._new_kind = kind
        cur = getattr(self, "_current", -1)
        pg = self._page()
        if pg and 0 <= cur < len(pg["boxes"]) and \
                pg["boxes"][cur].get("kind") != kind:
            self._push_undo()
            pg["boxes"][cur]["kind"] = kind
            self._refresh()

    def _set_kind_buttons(self, kind):
        self.bubble_btn.setChecked(kind != "sfx")
        self.sfx_btn.setChecked(kind == "sfx")

    # -- undo / redo --
    def _push_undo(self):
        """Snapshot the current page's boxes before a change; clears redo."""
        pg = self._page()
        if pg is None:
            return
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
        if hasattr(self, "undo_btn"):
            self.undo_btn.setEnabled(bool(self._undo))
            self.redo_btn.setEnabled(bool(self._redo))

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

    # -- closing pages --
    def on_close_page(self):
        """Remove the current page from the session (does not touch files)."""
        pg = self._page()
        if not pg:
            return
        if pg["boxes"] and not self._confirm_discard(
                self._tr("confirm_close").format(n=len(pg["boxes"]),
                                                 name=pg["name"])):
            return
        del self._pages[self._cur]
        self._after_pages_removed()
        self._status(self._tr("closed"))

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

    def _confirm_discard(self, msg):
        return QMessageBox.question(
            self, self._tr("confirm_title"), msg,
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
        self._refresh()

    def _on_box_removed(self, idx):
        pg = self._page()
        if pg and 0 <= idx < len(pg["boxes"]):
            self._push_undo()
            del pg["boxes"][idx]
            self._current = min(getattr(self, "_current", -1), len(pg["boxes"]) - 1)
            self._refresh()

    def _on_box_clicked(self, idx):
        pg = self._page()
        if not pg or not (0 <= idx < len(pg["boxes"])):
            return
        self._current = idx
        if self._order_mode:
            self._push_undo()
            pg["boxes"][idx]["order"] = self._order_counter
            self._order_counter += 1
            self._refresh()
            return
        kind = pg["boxes"][idx].get("kind", "bubble")
        self._set_kind_buttons(kind)
        self._new_kind = kind
        self._refresh()

    def _on_edit_toggle(self, on):
        if on and self.order_btn.isChecked():
            self.order_btn.setChecked(False)
        self.overlay.set_edit_mode(bool(on))

    def _on_tool(self, key):
        self.overlay.set_tool(key)
        # picking a marking tool implies you want to draw
        if not self.edit_btn.isChecked():
            self.edit_btn.setChecked(True)
        self._status(self._tr("tool_" + key + "_hint"))

    def _on_order_toggle(self, on):
        self._order_mode = bool(on)
        if on:
            if self.edit_btn.isChecked():
                self.edit_btn.setChecked(False)
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
        auto_order(pg["boxes"], rtl=self.rtl_chk.isChecked())
        self._order_counter = len(pg["boxes"]) + 1
        self._refresh()
        self._status(self._tr("ranked").format(n=len(pg["boxes"])))

    def on_delete(self):
        pg = self._page()
        cur = getattr(self, "_current", -1)
        if pg and 0 <= cur < len(pg["boxes"]):
            self._push_undo()
            del pg["boxes"][cur]
            self._current = min(cur, len(pg["boxes"]) - 1)
            self._refresh()

    def on_clear(self):
        pg = self._page()
        if pg and pg["boxes"]:
            self._push_undo()
            pg["boxes"] = []
            self._current = -1
            self._refresh()

    # -- actions --
    def on_load_images(self):
        paths, _f = QFileDialog.getOpenFileNames(
            self, self._tr("load"), self._folder or os.path.expanduser("~"),
            self._tr("img_filter"))
        if paths:
            self.add_image_paths(paths)

    def add_image_paths(self, paths):
        """Load the given image files as pages (used by the file dialog and by
        image paths passed on the command line). Returns how many were added."""
        added = 0
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
            added += 1
        if added:
            if self._cur < 0:
                self._goto(0)
            else:
                self._refresh()
            self._status(self._tr("loaded").format(n=added))
        return added

    def on_choose_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, self._tr("choose"), self._folder or os.path.expanduser("~"))
        if not path:
            return
        self._folder = path
        self._save_settings()
        self._refresh_folder_label()

    def _render_preview(self, pg):
        img = pg["img"].convertToFormat(QImage.Format_ARGB32)
        p = QPainter(img)
        fnt = QFont()
        fnt.setBold(True)
        fnt.setPixelSize(max(12, img.width() // 60))
        p.setFont(fnt)
        for b in pg["boxes"]:
            color = QColor(*KIND_COLOR.get(b.get("kind", "bubble"),
                                           KIND_COLOR["bubble"]))
            p.setPen(QPen(color, max(2, img.width() // 400)))
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(b["x"], b["y"], b["w"], b["h"]))
        p.end()
        return img

    def _export_page(self, pg, images, labels, order, preview):
        w, h = pg["img"].width(), pg["img"].height()
        stem = "%s_%d" % (pg["name"], int(time.time() * 1000) % 10 ** 9)
        if not pg["img"].save(os.path.join(images, stem + ".png"), "PNG"):
            raise IOError("could not write page image")
        with open(os.path.join(labels, stem + ".txt"), "w", encoding="utf-8") as fh:
            fh.write(make_yolo_label(pg["boxes"], w, h))
        with open(os.path.join(order, stem + ".json"), "w", encoding="utf-8") as fh:
            json.dump(order_data(pg["boxes"], w, h), fh, indent=2)
        try:
            self._render_preview(pg).save(os.path.join(preview, stem + ".png"), "PNG")
        except Exception:
            pass
        return stem

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
            images = os.path.join(self._folder, "images", "train")
            labels = os.path.join(self._folder, "labels", "train")
            order = os.path.join(self._folder, "order")
            preview = os.path.join(self._folder, "preview")
            for d in (images, labels, order, preview):
                os.makedirs(d, exist_ok=True)
            last = ""
            for pg in pages:
                last = self._export_page(pg, images, labels, order, preview)
                time.sleep(0.002)      # keep timestamp stems unique
        except Exception as exc:
            self._status(self._tr("export_fail").format(msg=exc), error=True)
            return
        if all_pages:
            self._status(self._tr("exported_all").format(n=len(pages)))
        else:
            self._status(self._tr("exported_one").format(name=last + ".png"))

    def on_save_project(self):
        start = os.path.join(self._folder or os.path.expanduser("~"), "project.json")
        path, _f = QFileDialog.getSaveFileName(
            self, self._tr("save"), start, self._tr("proj_filter"))
        if not path:
            return
        data = {"pages": [{"path": p["path"], "name": p["name"],
                           "boxes": p["boxes"]} for p in self._pages]}
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
        except Exception as exc:
            self._status(self._tr("load_fail").format(msg=exc), error=True)
            return
        self._status(self._tr("saved"))

    def on_load_project(self):
        path, _f = QFileDialog.getOpenFileName(
            self, self._tr("load_proj"), self._folder or os.path.expanduser("~"),
            self._tr("proj_filter"))
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
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
        except Exception as exc:
            self._status(self._tr("load_fail").format(msg=exc), error=True)
            return
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
        "QToolTip{color:#eff0f1;background:#31363b;border:1px solid #4d4d4d;}"
        "QPushButton{padding:5px 9px;border:1px solid #4d4d4d;border-radius:3px;"
        "background:#3a4045;}"
        "QPushButton:hover{background:#454b50;}"
        "QPushButton:pressed{background:#2c3135;}"
        "QPushButton:checked{background:#2f6f9f;border-color:#3daee9;}"
        "QPushButton:disabled{color:#7f8c8d;background:#33383c;}"
        "QComboBox{padding:3px 6px;border:1px solid #4d4d4d;border-radius:3px;"
        "background:#232629;}"
        "QLabel{color:#eff0f1;}")


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
    # first launch: offer Desktop / Start-menu shortcuts (clickable dialog)
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
