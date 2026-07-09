# -*- coding: utf-8 -*-
"""BubblR Trainer - standalone desktop app.

Same job as the Krita/Photoshop BubblR Trainer plugins, but a normal window
program: load page images from disk, draw + label bubble/SFX boxes, set the
reading order, and export a YOLO dataset. No Krita, no Photoshop.

Run:  python bubblr_trainer_app.py     (needs Python 3 + PyQt5)
"""
import json
import os
import sys
import time

from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy, QButtonGroup, QFileDialog, QComboBox,
    QMessageBox)
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QBrush, QImage, QPalette
from PyQt5.QtCore import Qt, pyqtSignal, QRectF

VERSION = "1.0"
KIND_CLASS = {"bubble": 0, "sfx": 1}
KIND_COLOR = {"bubble": (230, 60, 60), "sfx": (70, 130, 230)}
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".bubblr_trainer.json")

LANG = {
    "en": {
        "title": "BubblR Trainer",
        "intro": ("Load page images, draw a box around every bubble and SFX, "
                  "label them, optionally set the reading order, then export. "
                  "No AI here - this only makes the training data."),
        "load": "Load images…",
        "prev": "◀", "next": "▶",
        "page_none": "no page", "page": "{i} / {n}  -  {name}",
        "edit": "Draw / edit boxes", "set_order": "Set reading order",
        "delete": "Delete selected", "clear_order": "Clear order",
        "clear": "Clear all page",
        "kind": "New box is:", "bubble": "Bubble", "sfx": "SFX",
        "relabel": "(click a box first to relabel it)",
        "counts": "This page - Bubbles: {b}   SFX: {s}   |   Pages: {p}",
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
                  "Trainingsdaten."),
        "load": "Bilder laden…",
        "prev": "◀", "next": "▶",
        "page_none": "keine Seite", "page": "{i} / {n}  -  {name}",
        "edit": "Boxen zeichnen / bearbeiten", "set_order": "Lesereihenfolge festlegen",
        "delete": "Ausgewählte löschen", "clear_order": "Reihenfolge löschen",
        "clear": "Seite leeren",
        "kind": "Neue Box ist:", "bubble": "Bubble", "sfx": "SFX",
        "relabel": "(erst eine Box anklicken, um sie umzulabeln)",
        "counts": "Diese Seite – Bubbles: {b}   SFX: {s}   |   Seiten: {p}",
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


# ---------------------------------------------------------------------------
# Box overlay (pure Qt; ported from the Krita trainer plugin)
# ---------------------------------------------------------------------------

class BoxOverlay(QWidget):
    boxClicked = pyqtSignal(int)
    boxRemoved = pyqtSignal(int)
    boxAdded = pyqtSignal(float, float, float, float)
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
        self.setMinimumHeight(260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

    def set_edit_mode(self, on):
        self._edit = bool(on)
        self._drag = None
        self.setCursor(Qt.CrossCursor if on else Qt.ArrowCursor)
        self.update()

    def set_page(self, img, doc_w, doc_h):
        self._img = img
        self._doc_w = max(1, doc_w)
        self._doc_h = max(1, doc_h)
        self.update()

    def set_boxes(self, boxes, current=-1):
        self._boxes = boxes
        self._current = current
        self.update()

    def _target(self):
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return QRectF(0, 0, 1, 1)
        scale = min(w / float(self._doc_w), h / float(self._doc_h))
        tw = self._doc_w * scale
        th = self._doc_h * scale
        return QRectF((w - tw) / 2.0, (h - th) / 2.0, tw, th)

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
            p.drawRect(r)
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
        rect = self._rect_of(self._drag) if self._drag else None
        if rect is not None:
            x, y, w, h = rect
            pr = QRectF(t.x() + x * scale, t.y() + y * scale,
                        w * scale, h * scale)
            p.setPen(QPen(QColor(60, 200, 90), 2, Qt.DashLine))
            p.setBrush(QBrush(Qt.NoBrush))
            p.drawRect(pr)
        p.end()

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

    def _handle_at(self, pos):
        t = self._target()
        if t.width() <= 0:
            return None
        scale = t.width() / float(self._doc_w)
        best, best_area = None, None
        for k, b in enumerate(self._boxes):
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
                area = b["w"] * b["h"]
                if best_area is None or area < best_area:
                    best, best_area = (k, "move"), area
        return best

    @staticmethod
    def _norm(ax, ay, bx, by):
        return (min(ax, bx), min(ay, by), abs(bx - ax), abs(by - ay))

    def _rect_of(self, d):
        if not d:
            return None
        if d["mode"] == "new":
            return self._norm(d["x0"], d["y0"], d["cx"], d["cy"])
        if d["mode"] == "move":
            return (d["bx"] + (d["cx"] - d["px"]),
                    d["by"] + (d["cy"] - d["py"]), d["bw"], d["bh"])
        return self._norm(d["fx"], d["fy"], d["cx"], d["cy"])

    def mousePressEvent(self, event):
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

    def _begin_edit(self, pos):
        dx, dy = self._to_doc(pos)
        hit = self._handle_at(pos)
        if hit is None:
            self._drag = {"mode": "new", "x0": dx, "y0": dy, "cx": dx, "cy": dy}
        elif hit[1] == "move":
            b = self._boxes[hit[0]]
            self._drag = {"mode": "move", "idx": hit[0], "bx": b["x"],
                          "by": b["y"], "bw": b["w"], "bh": b["h"],
                          "px": dx, "py": dy, "cx": dx, "cy": dy}
        else:
            idx, corner = hit
            b = self._boxes[idx]
            fx = b["x"] + b["w"] if corner in ("nw", "sw") else b["x"]
            fy = b["y"] + b["h"] if corner in ("nw", "ne") else b["y"]
            self._drag = {"mode": "resize", "idx": idx, "fx": fx, "fy": fy,
                          "cx": dx, "cy": dy}
        self.update()

    def mouseMoveEvent(self, event):
        if not self._edit or self._drag is None:
            return
        self._drag["cx"], self._drag["cy"] = self._to_doc(event.pos())
        self.update()

    def mouseReleaseEvent(self, event):
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
        x = max(0.0, min(x, self._doc_w - 1))
        y = max(0.0, min(y, self._doc_h - 1))
        w = min(w, self._doc_w - x)
        h = min(h, self._doc_h - y)
        if d["mode"] == "new":
            self.boxAdded.emit(x, y, w, h)
        else:
            self.boxChanged.emit(d["idx"], x, y, w, h)


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
        lay.addLayout(top)

        self.overlay = BoxOverlay()
        self.overlay.boxAdded.connect(self._on_box_added)
        self.overlay.boxChanged.connect(self._on_box_changed)
        self.overlay.boxRemoved.connect(self._on_box_removed)
        self.overlay.boxClicked.connect(self._on_box_clicked)
        lay.addWidget(self.overlay, 1)

        tools = QHBoxLayout()
        self.edit_btn = QPushButton(self._tr("edit"))
        self.edit_btn.setCheckable(True)
        self.edit_btn.toggled.connect(self._on_edit_toggle)
        tools.addWidget(self.edit_btn)
        self.order_btn = QPushButton(self._tr("set_order"))
        self.order_btn.setCheckable(True)
        self.order_btn.toggled.connect(self._on_order_toggle)
        tools.addWidget(self.order_btn)
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
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
                json.dump({"lang": self._lang, "folder": self._folder}, fh)
        except Exception:
            pass

    def _on_lang(self, _i):
        self._lang = self.lang_combo.currentData() or "en"
        self._save_settings()
        self._retranslate()

    def _retranslate(self):
        t = self._tr
        self.setWindowTitle(t("title") + " v" + VERSION)
        self.lbl_intro.setText(t("intro"))
        self.load_btn.setText(t("load"))
        self.prev_btn.setText(t("prev"))
        self.next_btn.setText(t("next"))
        self.edit_btn.setText(t("edit"))
        self.order_btn.setText(t("set_order"))
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
        self.lbl_counts.setText(self._tr("counts").format(
            b=b, s=s, p=len(self._pages)))
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
        if pg and 0 <= cur < len(pg["boxes"]):
            pg["boxes"][cur]["kind"] = kind
            self._refresh()

    def _set_kind_buttons(self, kind):
        self.bubble_btn.setChecked(kind != "sfx")
        self.sfx_btn.setChecked(kind == "sfx")

    # -- page navigation --
    def _goto(self, idx):
        if not self._pages:
            return
        self._cur = max(0, min(idx, len(self._pages) - 1))
        self._current = -1
        pg = self._pages[self._cur]
        self.overlay.set_page(pg["img"], pg["img"].width(), pg["img"].height())
        self._refresh()

    # -- overlay callbacks --
    def _on_box_added(self, x, y, w, h):
        pg = self._page()
        if not pg:
            return
        pg["boxes"].append({"x": int(round(x)), "y": int(round(y)),
                            "w": int(round(w)), "h": int(round(h)),
                            "kind": self._new_kind, "order": 0})
        self._current = len(pg["boxes"]) - 1
        self._refresh()

    def _on_box_changed(self, idx, x, y, w, h):
        pg = self._page()
        if pg and 0 <= idx < len(pg["boxes"]):
            pg["boxes"][idx].update({"x": int(round(x)), "y": int(round(y)),
                                     "w": int(round(w)), "h": int(round(h))})
            self._current = idx
            self._refresh()

    def _on_box_removed(self, idx):
        pg = self._page()
        if pg and 0 <= idx < len(pg["boxes"]):
            del pg["boxes"][idx]
            self._current = min(getattr(self, "_current", -1), len(pg["boxes"]) - 1)
            self._refresh()

    def _on_box_clicked(self, idx):
        pg = self._page()
        if not pg or not (0 <= idx < len(pg["boxes"])):
            return
        self._current = idx
        if self._order_mode:
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
        if pg:
            for b in pg["boxes"]:
                b["order"] = 0
        self._order_counter = 1
        self._refresh()
        self._status(self._tr("order_cleared"))

    def on_delete(self):
        pg = self._page()
        cur = getattr(self, "_current", -1)
        if pg and 0 <= cur < len(pg["boxes"]):
            del pg["boxes"][cur]
            self._current = min(cur, len(pg["boxes"]) - 1)
            self._refresh()

    def on_clear(self):
        pg = self._page()
        if pg:
            pg["boxes"] = []
            self._current = -1
            self._refresh()

    # -- actions --
    def on_load_images(self):
        paths, _f = QFileDialog.getOpenFileNames(
            self, self._tr("load"), self._folder or os.path.expanduser("~"),
            self._tr("img_filter"))
        if not paths:
            return
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
                    boxes.append({"x": int(b["x"]), "y": int(b["y"]),
                                  "w": int(b["w"]), "h": int(b["h"]),
                                  "kind": "sfx" if b.get("kind") == "sfx" else "bubble",
                                  "order": int(b.get("order", 0) or 0)})
                pages.append({"path": pd.get("path", ""),
                              "name": pd.get("name", "page"),
                              "img": img.convertToFormat(QImage.Format_RGB888),
                              "boxes": boxes})
        except Exception as exc:
            self._status(self._tr("load_fail").format(msg=exc), error=True)
            return
        self._pages = pages
        self._cur = -1
        if pages:
            self._goto(0)
        else:
            self._refresh()
        self._status(self._tr("loaded_proj").format(n=len(pages)))


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


def main():
    app = QApplication(sys.argv)
    apply_krita_dark(app)
    win = TrainerWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
