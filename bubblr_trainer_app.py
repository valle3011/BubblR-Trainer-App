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
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
import zlib

from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy, QButtonGroup, QFileDialog, QComboBox,
    QMessageBox, QCheckBox, QSpinBox, QShortcut, QSplashScreen,
    QDialog, QDialogButtonBox, QListWidget, QListWidgetItem,
    QAbstractItemView, QInputDialog, QActionGroup, QMenu,
    QStackedWidget, QRadioButton, QDockWidget, QToolButton, QLayout,
    QStyle, QWidgetItem, QTabWidget, QToolBar, QLineEdit, QColorDialog,
    QTextBrowser, QScrollArea, QGridLayout)
from PyQt5.QtGui import (QColor, QFont, QPainter, QPen, QBrush, QImage,
                         QPalette, QPolygonF, QKeySequence, QIcon, QPixmap,
                         QDesktopServices)
from PyQt5.QtWidgets import QKeySequenceEdit
from PyQt5.QtCore import (Qt, pyqtSignal, QRectF, QRect, QPoint, QPointF, QTimer,
                          QSize, QProcess, QItemSelectionModel, QThread, QUrl,
                          QEvent)

from bubblr_i18n import LANG
from bubblr_train_core import (MODEL_URL, MODEL_META_URL, model_path,
                               build_detect_script, detect_config,
                               build_rank_script, rank_config,
                               PYTHON_DOWNLOAD_URL, find_python_candidates,
                               python_has_ultralytics, best_ai_python,
                               probe_ai_python, is_valid_model, diagnose_error,
                               VCREDIST_URL, pip_install_args, strip_ansi)


class AiModelFetcher(QThread):
    """Download the shared model (bubblr-model.pt) in the background."""
    done = pyqtSignal(object)                     # local path, or None

    def run(self):
        dest = model_path()
        try:
            import urllib.request
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            req = urllib.request.Request(MODEL_URL,
                                         headers={"User-Agent": "BubblR"})
            with urllib.request.urlopen(req, timeout=60) as r, \
                    open(dest, "wb") as f:
                f.write(r.read())
            # A truncated download or an error page saved under a .pt name would
            # later blow up inside YOLO() as an unexplained "detection failed",
            # so reject anything that isn't a real Torch checkpoint right here.
            if not is_valid_model(dest):
                raise ValueError("downloaded file is not a valid model")
            self.done.emit(dest)
        except Exception:                        # noqa: BLE001
            try:
                if os.path.exists(dest):
                    os.remove(dest)
            except OSError:
                pass
            self.done.emit(None)


VERSION = "0.9.27"
# Bump when the DEFAULT dock layout changes so existing users get the new
# arrangement once (their saved dock state is ignored for that one launch).
LAYOUT_VERSION = 2

# Customizable keyboard shortcuts. Each entry: id -> (group, label_key, default).
# `group` orders the Settings → Shortcuts list; `label_key` is a translation key
# for the row label; `default` is the factory key sequence ("" = unbound).
# Menu items reuse their menu label key; selectors/order get their own.
SHORTCUT_GROUPS = ["sc_grp_sel", "sc_grp_ord", "sc_grp_file",
                   "sc_grp_edit", "sc_grp_page", "sc_grp_view", "sc_grp_help"]
SHORTCUT_DEFS = [
    # selectors
    ("tool_rect",     ("sc_grp_sel",  "sc_tool_rect",    "R")),
    ("tool_ellipse",  ("sc_grp_sel",  "sc_tool_ellipse", "E")),
    ("tool_poly",     ("sc_grp_sel",  "sc_tool_poly",    "P")),
    ("tool_lasso",    ("sc_grp_sel",  "sc_tool_lasso",   "L")),
    ("tool_wand",     ("sc_grp_sel",  "sc_tool_wand",    "W")),
    # reading order
    ("set_order",     ("sc_grp_ord",  "set_order",       "O")),
    ("auto_order",    ("sc_grp_ord",  "auto_order",      "Ctrl+R")),
    ("clear_order",   ("sc_grp_ord",  "mi_clear_order",  "")),
    # file
    ("mi_open",       ("sc_grp_file", "mi_open",         "Ctrl+O")),
    ("mi_save",       ("sc_grp_file", "mi_save",         "Ctrl+S")),
    ("mi_exp_page",   ("sc_grp_file", "mi_exp_page",     "Ctrl+E")),
    ("mi_exp_all",    ("sc_grp_file", "mi_exp_all",      "Ctrl+Shift+E")),
    ("mi_exit",       ("sc_grp_file", "mi_exit",         "Ctrl+Q")),
    # edit
    ("mi_undo",       ("sc_grp_edit", "mi_undo",         "Ctrl+Z")),
    ("mi_redo",       ("sc_grp_edit", "mi_redo",         "Ctrl+Y")),
    ("mi_copy",       ("sc_grp_edit", "mi_copy",         "Ctrl+C")),
    ("mi_paste",      ("sc_grp_edit", "mi_paste",        "Ctrl+V")),
    ("mi_dup",        ("sc_grp_edit", "mi_dup",          "Ctrl+D")),
    ("mi_del",        ("sc_grp_edit", "mi_del",          "Del")),
    ("fit_box",       ("sc_grp_edit", "fit_box",         "F")),
    ("mi_select_all", ("sc_grp_edit", "mi_select_all",   "Ctrl+A")),
    ("deselect",      ("sc_grp_edit", "mi_deselect",     "Esc")),
    # page
    ("mi_prev",       ("sc_grp_page", "mi_prev",         "[")),
    ("mi_next",       ("sc_grp_page", "mi_next",         "]")),
    ("mi_close",      ("sc_grp_page", "mi_close",        "Ctrl+W")),
    # view
    ("mi_zoom_in",    ("sc_grp_view", "mi_zoom_in",      "Ctrl++")),
    ("mi_zoom_out",   ("sc_grp_view", "mi_zoom_out",     "Ctrl+-")),
    ("mi_zoom_sel",   ("sc_grp_view", "mi_zoom_sel",     "Z")),
    # help
    ("mi_shortcuts",  ("sc_grp_help", "mi_shortcuts",    "F1")),
]
SHORTCUT_DEFAULT = {aid: meta[2] for aid, meta in SHORTCUT_DEFS}
SHORTCUT_META = {aid: meta for aid, meta in SHORTCUT_DEFS}
# Extra fixed aliases kept alongside the customizable primary (muscle memory).
SHORTCUT_ALIASES = {"mi_redo": ["Ctrl+Shift+Z"], "mi_del": ["Backspace"]}

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
RELEASES_API = ("https://api.github.com/repos/valle3011/"
                "BubblR-Trainer-App/releases")
# The auto-updater downloads this asset from the latest GitHub release (a zip of
# the onedir build). The "latest/download" URL always points at the newest one.
UPDATE_ASSET = "BubblR-Trainer-win.zip"
UPDATE_ZIP_URL = ("https://github.com/valle3011/BubblR-Trainer-App/releases/"
                  "latest/download/" + UPDATE_ASSET)
# A downloaded update is unpacked here (in the user's home, so it survives a
# restart) and applied on the *next* launch during the splash — no restart
# prompt, one quick auto-relaunch (Krita-style).
UPDATE_STAGE = os.path.join(os.path.expanduser("~"), ".bubblr_trainer_update")


def _ver_tuple(v):
    """Turn '0.9.8' into (0, 9, 8) for comparison; ignores non-digits."""
    out = []
    for part in str(v).split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        out.append(int(digits) if digits else 0)
    return tuple(out)



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


def _box_polygon(b):
    """Outline points (absolute doc coords) for a box: its stored contour when it
    has one (poly/lasso/wand), an ellipse approximation, else the four corners."""
    pts = b.get("points")
    if pts and len(pts) >= 3:
        return [(float(px), float(py)) for px, py in pts]
    x, y, w, h = b["x"], b["y"], b["w"], b["h"]
    if b.get("shape") == "ellipse":
        cx, cy, rx, ry = x + w / 2.0, y + h / 2.0, w / 2.0, h / 2.0
        n = 24
        return [(cx + rx * math.cos(2 * math.pi * i / n),
                 cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def make_yolo_seg_label(boxes, img_w, img_h, class_index=None):
    """YOLO segmentation labels: one line per object as `class x1 y1 x2 y2 …`
    with normalised polygon points (uses the drawn outline where available)."""
    ci = class_index if class_index is not None else KIND_CLASS
    lines = []
    for b in boxes:
        cls = ci.get(b.get("kind", "bubble"), 0)
        coords = []
        for px, py in _box_polygon(b):
            nx = min(1.0, max(0.0, px / float(img_w)))
            ny = min(1.0, max(0.0, py / float(img_h)))
            coords.append("%.6f %.6f" % (nx, ny))
        if len(coords) >= 3:
            lines.append("%d %s" % (cls, " ".join(coords)))
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
    # x,y,w,h, shape ("rect"/"ellipse"/"poly"/"lasso"/"wand"), points (list|None)
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
        self._tool = "rect"       # rect | ellipse | poly | lasso | wand
        self._poly = None         # in-progress polygon: list of (dx, dy) vertices
        self._poly_cursor = None  # live cursor point while placing polygon points
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
        self._cancel_poly()
        self.setCursor(Qt.CrossCursor if on else Qt.ArrowCursor)
        self.update()

    def set_tool(self, name):
        if name in ("rect", "ellipse", "poly", "lasso", "wand"):
            self._cancel_poly()          # dropping the poly tool cancels a draw
            self._tool = name
            self._drag = None
            self.update()

    def _cancel_poly(self):
        self._poly = None
        self._poly_cursor = None

    def _poly_click(self, dx, dy):
        """Add a polygon vertex, or close the shape when clicking near the
        first point (needs at least 3 points)."""
        if self._poly is None:
            self._poly = [(dx, dy)]
            self._poly_cursor = (dx, dy)
            self.update()
            return
        t = self._target()
        scale = t.width() / float(self._doc_w) if t.width() > 0 else 1.0
        tol = 10.0 / max(scale, 1e-6)            # ~10 screen px, in doc units
        fx, fy = self._poly[0]
        if len(self._poly) >= 3 and abs(dx - fx) <= tol and abs(dy - fy) <= tol:
            self._finish_poly()
            return
        self._poly.append((dx, dy))
        self._poly_cursor = (dx, dy)
        self.update()

    def _finish_poly(self):
        pts = self._poly or []
        self._poly = None
        self._poly_cursor = None
        self.update()
        if len(pts) < 3:
            return
        xs = [px for px, _ in pts]
        ys = [py for _, py in pts]
        x, y, w, h = self._clamp(min(xs), min(ys),
                                 max(xs) - min(xs), max(ys) - min(ys))
        if w < 8 or h < 8:
            return
        points = [[round(px, 1), round(py, 1)] for px, py in pts]
        self.boxAdded.emit(x, y, w, h, "poly", points)

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
        # live preview of the polygon being placed (click-to-add-point tool)
        if self._poly:
            g = QColor(60, 200, 90)
            pts = [QPointF(t.x() + px * scale, t.y() + py * scale)
                   for px, py in self._poly]
            p.setBrush(Qt.NoBrush)
            if len(pts) >= 2:
                p.setPen(QPen(g, 2))
                p.drawPolyline(QPolygonF(pts))
            cur = self._poly_cursor
            if cur is not None:
                cp = QPointF(t.x() + cur[0] * scale, t.y() + cur[1] * scale)
                p.setPen(QPen(g, 1, Qt.DashLine))
                p.drawLine(pts[-1], cp)
                if len(pts) >= 2:                # hint the closing edge
                    p.drawLine(cp, pts[0])
            p.setPen(QPen(QColor(20, 40, 20), 1))
            for i, vp in enumerate(pts):
                # a bigger dot on the first vertex marks where to click to close
                rad = 5.0 if i == 0 else 3.5
                p.setBrush(QBrush(QColor(255, 235, 120) if i == 0 else g))
                p.drawEllipse(vp, rad, rad)
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
        elif shape in ("lasso", "poly") and points:
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
        k = event.key()
        # polygon in progress: Enter closes, Esc cancels, Backspace undoes a point
        if self._tool == "poly" and self._poly is not None:
            if k in (Qt.Key_Return, Qt.Key_Enter):
                self._finish_poly()
                event.accept()
                return
            if k == Qt.Key_Escape:
                self._cancel_poly()
                self.update()
                event.accept()
                return
            if k in (Qt.Key_Backspace, Qt.Key_Delete):
                self._poly.pop()
                if not self._poly:
                    self._cancel_poly()
                self.update()
                event.accept()
                return
        # arrow keys nudge the selected box (Shift = 10 px); pan otherwise
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
        # Polygon tool: each click drops a vertex; clicking near the first point
        # (or Enter / double-click) closes the shape. It never drags.
        if self._tool == "poly":
            self._poly_click(dx, dy)
            return
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
            # polygon in progress: rubber-band the next edge to the cursor
            if self._tool == "poly" and self._poly is not None:
                self._poly_cursor = self._to_doc(event.pos())
                self.setCursor(Qt.CrossCursor)
                self.update()
                return
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

    def mouseDoubleClickEvent(self, event):
        # double-click closes the polygon being placed
        if (self._edit and self._tool == "poly" and self._poly is not None
                and event.button() == Qt.LeftButton):
            self._finish_poly()
            return
        super(BoxOverlay, self).mouseDoubleClickEvent(event)

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
    elif kind == "poly":                     # polygon: straight edges + vertices
        verts = [QPointF(size * 0.5, m), QPointF(size - m, size * 0.42),
                 QPointF(size - m - 3, size - m), QPointF(m + 3, size - m - 2),
                 QPointF(m, size * 0.4)]
        p.drawPolygon(QPolygonF(verts))
        p.setBrush(QBrush(ink))
        for v in verts:                      # little handles at each corner
            p.drawEllipse(v, 1.5, 1.5)
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

    # portrait aspect (width/height) of a manga page thumbnail — matches the
    # 240x300 pixmap cached in _page_thumb. The cell always matches the icon at
    # this ratio so thumbnails are never squished or clipped.
    AR = 0.8

    def _resize_icons(self):
        vp = self.viewport().size()
        if self._vertical:                       # grid: 1 -> 2 -> 3 … columns
            avail = max(60, vp.width() - 4)
            # add a column each time the cells would otherwise pass ~1.5*PREF,
            # so thumbnails grow a bit, then wrap, then grow again
            n = max(1, int(avail / self.PREF + 0.5))
            cellw = max(48, (avail - 2 * n) // n)  # a little slack so n cells fit
            iconw = max(40, cellw - 8)
            iconh = int(iconw / self.AR)
        else:                                    # single row, height = the dock
            iconh = max(56, min(320, vp.height() - 16))
            iconw = int(iconh * self.AR)
            cellw = iconw + 12
        # ALWAYS force a grid so every cell is at least as big as its icon —
        # otherwise the icon can be wider than the cell and get clipped, which
        # looks like a distorted thumbnail (worst on the bottom/top strip).
        self.setIconSize(QSize(iconw, iconh))
        self.setGridSize(QSize(max(cellw, iconw + 8), iconh + 22))


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


class ModelMetaFetcher(QThread):
    """Fetch the BubblR-Model repo's model.json in the background; emits the
    parsed dict (with the published model 'version'), or None on failure."""
    loaded = pyqtSignal(object)

    def run(self):
        data = None
        try:
            import urllib.request
            req = urllib.request.Request(
                MODEL_META_URL, headers={"User-Agent": "BubblR-Trainer"})
            with urllib.request.urlopen(req, timeout=6) as r:
                data = json.loads(r.read().decode("utf-8"))
        except Exception:                        # noqa: BLE001 (offline etc.)
            data = None
        self.loaded.emit(data)


class UpdateDownloader(QThread):
    """Download the latest-release zip in the background (Krita-style: fetched
    automatically as soon as an update is detected). Emits the saved file path
    on success or None on any failure, plus coarse progress in percent."""
    progress = pyqtSignal(int)
    done = pyqtSignal(object)                     # str path, or None on failure

    def __init__(self, url, dest, parent=None):
        super(UpdateDownloader, self).__init__(parent)
        self._url = url
        self._dest = dest

    def run(self):
        try:
            import urllib.request
            req = urllib.request.Request(
                self._url, headers={"User-Agent": "BubblR-Trainer"})
            with urllib.request.urlopen(req, timeout=30) as r:
                total = int(r.headers.get("Content-Length", 0) or 0)
                got = 0
                with open(self._dest, "wb") as f:
                    while True:
                        chunk = r.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        got += len(chunk)
                        if total > 0:
                            self.progress.emit(min(100, int(got * 100 / total)))
            # A too-small file means we hit an HTML error page, not a real zip.
            if os.path.getsize(self._dest) < 4096 or not zipfile.is_zipfile(
                    self._dest):
                raise ValueError("downloaded file is not a valid zip")
            self.done.emit(self._dest)
        except Exception:                        # noqa: BLE001 (offline etc.)
            try:
                if os.path.exists(self._dest):
                    os.remove(self._dest)
            except OSError:
                pass
            self.done.emit(None)


class ReleasesFetcher(QThread):
    """List published releases (that ship the Windows asset) from the GitHub API
    in the background, so the user can pick any version. Emits a list of version
    strings (newest first), or None on failure."""
    loaded = pyqtSignal(object)

    def run(self):
        out = None
        try:
            import urllib.request
            req = urllib.request.Request(
                RELEASES_API, headers={"User-Agent": "BubblR-Trainer",
                                       "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode("utf-8"))
            vers = []
            for rel in data:
                if rel.get("draft") or rel.get("prerelease"):
                    continue
                if not any(a.get("name") == UPDATE_ASSET
                           for a in rel.get("assets", [])):
                    continue
                tag = rel.get("tag_name", "")
                vers.append(tag[1:] if tag.startswith("v") else tag)
            out = vers
        except Exception:                        # noqa: BLE001 (offline etc.)
            out = None
        self.loaded.emit(out)


def _version_zip_url(v):
    """Direct download URL for a specific release's Windows asset."""
    return ("https://github.com/valle3011/BubblR-Trainer-App/releases/"
            "download/v%s/%s" % (v, UPDATE_ASSET))


def _stage_update(zip_path):
    """Unpack a downloaded update zip into the staging area and return the
    folder that actually holds our .exe (the onedir root). Raises on trouble."""
    stage = os.path.join(UPDATE_STAGE, "new")
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(stage)
    exe_name = os.path.basename(sys.executable)
    for root, _dirs, files in os.walk(stage):
        if exe_name in files:
            return root
    raise ValueError("update package has no %s" % exe_name)


def _launch_swap_helper(src):
    """Write and launch a detached .bat that waits for this process to exit,
    mirror-copies the staged build (src) over the install dir and relaunches."""
    exe_name = os.path.basename(sys.executable)
    dst = os.path.dirname(sys.executable)
    os.makedirs(UPDATE_STAGE, exist_ok=True)
    bat = os.path.join(UPDATE_STAGE, "apply_update.bat")
    # /MIR mirrors src→dst (removing stale files); the staging area is outside
    # dst so it is never touched. The guard aborts if the source looks wrong.
    script = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        'if not exist "%s\\%s" ( exit /b 1 )\r\n'
        ":wait\r\n"
        'tasklist /fi "imagename eq %s" | find /i "%s" >nul '
        "&& ( timeout /t 1 /nobreak >nul & goto wait )\r\n"
        'robocopy "%s" "%s" /MIR /R:2 /W:1 /NFL /NDL /NJH /NJS /NP >nul\r\n'
        'start "" "%s\\%s"\r\n'
    ) % (src, exe_name, exe_name, exe_name, src, dst, dst, exe_name)
    with open(bat, "w", encoding="utf-8") as f:
        f.write(script)
    DETACHED = 0x00000008 | 0x00000200           # DETACHED | NEW_PROCESS_GROUP
    subprocess.Popen(["cmd", "/c", bat], creationflags=DETACHED, close_fds=True)


def _maybe_apply_pending_update():
    """Called at startup (during the splash): if a newer build was downloaded in
    a previous session, hand off to the swap helper and tell main() to quit so
    the update is applied and the app relaunches — no dialog, one quick restart.
    Returns True when a swap was launched (main() should exit)."""
    if not getattr(sys, "frozen", False):
        return False
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:                            # noqa: BLE001
        return False
    pu = cfg.get("pending_update")
    if not isinstance(pu, dict):
        return False
    ver, src = pu.get("version"), pu.get("src")
    exe_name = os.path.basename(sys.executable)
    ok = (ver and _ver_tuple(ver) > _ver_tuple(VERSION)
          and src and os.path.exists(os.path.join(src, exe_name)))
    # Clear the flag up front either way: if already applied (version matches) or
    # the staging is gone, drop it; if valid, clear so a failed swap can't loop.
    cfg.pop("pending_update", None)
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:                            # noqa: BLE001
        pass
    if not ok:
        if ver and _ver_tuple(ver) <= _ver_tuple(VERSION):
            shutil.rmtree(UPDATE_STAGE, ignore_errors=True)   # applied → clean up
        return False
    try:
        _launch_swap_helper(src)
        return True
    except Exception:                            # noqa: BLE001
        return False


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
        self._ai_python_path = cfg.get("ai_python", "")   # python w/ ultralytics
        self._rank_model_path = cfg.get("rank_model", "")  # model used for ranking
        self._ai_model_version = int(cfg.get("ai_model_version", 0))  # downloaded
        self._latest_model_version = 0            # newest in the BubblR-Model repo
        self._locked = cfg.get("locked", False)  # movable by default (Krita-style)
        self._wand_tol = int(cfg.get("wand_tol", 40))  # set in the Settings window
        self._val_split = max(0, min(50, int(cfg.get("val_split", 0))))  # % to val
        self._export_summary_on = bool(cfg.get("export_summary", True))
        self._export_bg = bool(cfg.get("export_bg", False))  # empty pages as negs
        self._seg_export = bool(cfg.get("seg_export", False))  # YOLO-seg polygons
        self._coco_export = bool(cfg.get("coco_export", False))  # + COCO JSON
        self._news_enabled = bool(cfg.get("news_enabled", True))
        self._experimental_trainer = bool(cfg.get("exp_model_trainer", False))
        self._auto_update = bool(cfg.get("auto_update", True))  # Krita-style
        self._update_zip = None                  # path once downloaded
        _pu = cfg.get("pending_update")          # staged update from last session
        self._pending_update = _pu if isinstance(_pu, dict) else None
        self._auto_order = bool(cfg.get("auto_order_on", False))
        # customizable keyboard shortcuts: only non-default overrides are stored
        raw_sc = cfg.get("shortcuts", {})
        self._sc_over = {k: str(v) for k, v in raw_sc.items()
                         if k in SHORTCUT_DEFAULT} if isinstance(raw_sc, dict) else {}
        self._sc_act = {}                         # id -> QAction (menu items)
        self._sc_qs = {}                          # id -> QShortcut (tool/global)
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
        for _key in ("rect", "ellipse", "poly", "lasso", "wand"):
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
        # which panels the user left open (objectName -> bool); missing = open
        self._dock_wanted = dict(cfg.get("dock_visible") or {})
        self._dock_syncing = False
        self._closing = False
        # When the built-in default layout changes, drop the user's saved dock
        # arrangement once so they actually see the new default (pages on the
        # right, sized for two columns). Their own moves are saved again after.
        if cfg.get("layout_version") != LAYOUT_VERSION:
            self._pending_dockstate = None
            self._pending_dock_sizes = None

        # menu bar (also carries the keyboard shortcuts)
        self._build_menu()
        self._install_shortcuts()            # selectors, order, deselect (Esc)
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
        self._start_model_check()            # green button if a newer AI model exists

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
                "ai_dir": self._ai_dir, "ai_python": self._ai_python_path,
                "rank_model": self._rank_model_path,
                "ai_model_version": self._ai_model_version, "locked": self._locked,
                "wand_tol": self._wand_tol, "auto_order_on": self._auto_order,
                "rtl": self._rtl, "new_kind": self._new_kind,
                "center_marker": self._center, "last_dir": self._last_dir,
                "discord_enabled": self._discord_enabled,
                "discord_client_id": self._discord_id,
                "recent": self._recent[:40], "classes": self._classes,
                "val_split": self._val_split,
                "export_summary": self._export_summary_on,
                "export_bg": self._export_bg,
                "seg_export": self._seg_export,
                "coco_export": self._coco_export,
                "news_enabled": self._news_enabled,
                "exp_model_trainer": self._experimental_trainer,
                "auto_update": self._auto_update,
                "shortcuts": dict(getattr(self, "_sc_over", {})),
                "dock_visible": dict(getattr(self, "_dock_wanted", {})),
                "pending_update": self._pending_update}
        try:
            data["geo"] = bytes(self.saveGeometry()).hex()
            data["layout_version"] = LAYOUT_VERSION
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
        for k in ("rect", "ellipse", "poly", "lasso", "wand"):
            self._tools_flow.addWidget(self.tool_btns[k])
        tv.addWidget(flow_host)
        tv.addStretch(1)
        self.tools_dock = QDockWidget(self._tr("dock_tools"), self)
        self.tools_dock.setObjectName("toolsDock")
        self.tools_dock.setWidget(tools_w)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.tools_dock)

        # Boxes docker — default: left, below the tools
        self.boxes_dock = QDockWidget(self._tr("dock_boxes"), self)
        self.boxes_dock.setObjectName("boxesDock")
        self.boxes_dock.setWidget(self.box_list)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.boxes_dock)
        self.splitDockWidget(self.tools_dock, self.boxes_dock, Qt.Vertical)

        # Pages (thumbnails) docker — default: right, wide enough for 2 columns.
        # Flow adapts to whichever side it ends up on.
        self.thumbs_dock = QDockWidget(self._tr("dock_pages"), self)
        self.thumbs_dock.setObjectName("thumbsDock")
        self.thumbs_dock.setWidget(self.page_strip)
        self.addDockWidget(Qt.RightDockWidgetArea, self.thumbs_dock)
        self.thumbs_dock.dockLocationChanged.connect(self._apply_thumbs_flow)

        self._docks = [self.tools_dock, self.boxes_dock, self.thumbs_dock]
        for d in self._docks:
            d.setAllowedAreas(Qt.AllDockWidgetAreas)   # left, right, top, bottom
            # Catch the panel's X button. We deliberately do NOT listen to
            # visibilityChanged: Qt emits it asynchronously and also for things
            # that are not a user decision (start page, window close, restore),
            # so it cannot tell "the user closed this" from "we hid it".
            d.installEventFilter(self)
        # when two panels stack in one area, show their tabs at the top
        self.setTabPosition(Qt.AllDockWidgetAreas, QTabWidget.North)
        # let the left/right docks own the full height (corners), like Krita
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.TopRightCorner, Qt.RightDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)
        self._apply_thumbs_flow(Qt.RightDockWidgetArea)
        self._apply_dock_lock()

    def _apply_default_dock_sizes(self):
        """Give the pages panel enough width for two thumbnail columns, and keep
        the tools panel slim — used for a fresh layout (no saved sizes)."""
        try:
            self.resizeDocks([self.thumbs_dock], [max(300, PageStrip.PREF * 2 + 40)],
                             Qt.Horizontal)
            self.resizeDocks([self.tools_dock], [150], Qt.Horizontal)
        except Exception:                        # noqa: BLE001
            pass

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
        # When dragged to a new edge the viewport hasn't resized yet, so the
        # icons would be sized from the OLD dock dimensions. Recompute once the
        # layout has settled at the new size.
        QTimer.singleShot(0, s._resize_icons)
        QTimer.singleShot(60, s._resize_icons)

    def _apply_dock_lock(self):
        """Locked = titles stay but panels can't be dragged/floated; unlocked =
        movable, floatable & closable (Krita/TypeR-style)."""
        for d in getattr(self, "_docks", []):
            if self._locked:
                d.setFeatures(QDockWidget.NoDockWidgetFeatures)
            else:
                d.setFeatures(QDockWidget.DockWidgetMovable
                              | QDockWidget.DockWidgetFloatable
                              | QDockWidget.DockWidgetClosable)

    def _sync_docker_menu(self):
        """Keep the View → Dockers checkmarks in sync with each dock's real
        visibility (and its current localized title)."""
        for act, d in getattr(self, "_docker_acts", []):
            act.blockSignals(True)
            act.setText(d.windowTitle())
            act.setChecked(d.isVisible())
            act.blockSignals(False)

    # -- which dockers the user wants open (persisted) ------------------------
    def _dock_is_wanted(self, d):
        """Has the user closed this panel? Unknown panels default to open."""
        return bool(getattr(self, "_dock_wanted", {}).get(d.objectName(), True))

    def _apply_dock_visibility(self, show):
        """Show/hide the docks WITHOUT recording it as a user choice. On the
        start page all panels are hidden; in the editor only the ones the user
        actually left open come back."""
        self._dock_syncing = True
        try:
            for d in getattr(self, "_docks", []):
                d.setVisible(bool(show) and self._dock_is_wanted(d))
        finally:
            self._dock_syncing = False

    def eventFilter(self, obj, event):
        """The only place a dock is recorded as closed: the user pressing its X.
        Hiding a panel any other way (start page, quitting, restoring a layout)
        must not count as a decision to close it."""
        if (event.type() == QEvent.Close and isinstance(obj, QDockWidget)
                and obj in getattr(self, "_docks", [])):
            self._set_dock_wanted(obj, False)
        return super(TrainerWindow, self).eventFilter(obj, event)

    def _set_dock_wanted(self, dock, on):
        """Remember that the user opened/closed this panel, and apply it."""
        self._dock_wanted[dock.objectName()] = bool(on)
        if dock.isHidden() == bool(on):          # only touch it if it disagrees
            self._apply_dock_visibility(bool(self._pages))
        self._save_settings()

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
        self.news_install_btn = QPushButton(self._tr("update_install"))
        self.news_install_btn.setStyleSheet(
            "background:#2f6f3f;color:#eaffea;font-weight:bold;"
            "border:none;border-radius:5px;padding:8px;")
        self.news_install_btn.clicked.connect(self._install_update)
        self.news_install_btn.setVisible(False)
        news_col.addWidget(self.news_install_btn)
        # green "new AI model" button (like the app-update button)
        self.model_update_btn = QPushButton()
        self.model_update_btn.setStyleSheet(
            "background:#2f6f3f;color:#eaffea;font-weight:bold;"
            "border:none;border-radius:5px;padding:8px;")
        self.model_update_btn.clicked.connect(self._get_ai_model_from_start)
        self.model_update_btn.setVisible(False)
        news_col.addWidget(self.model_update_btn)
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
            self._latest_version = latest
            url = data.get("url") or RELEASES_URL
            self.news_update.setText(
                "%s &nbsp; <a href='%s' style='color:#bfffcf'>%s</a>" % (
                    self._tr("news_update").format(v=latest), url,
                    self._tr("news_download")))
            self.news_update.setVisible(True)
            # Krita-style: on a frozen (.exe) build, pull the update down
            # automatically in the background, then offer one-click install.
            if getattr(sys, "frozen", False):
                if self._auto_update:
                    self._start_update_download()
            elif os.path.isdir(os.path.join(self._app_dir(), ".git")):
                # source checkout: it can still update itself with git pull
                self.news_install_btn.setText(self._tr("update_btn"))
                self.news_install_btn.setEnabled(True)
                self.news_install_btn.setVisible(True)
        else:
            self.news_update.setVisible(False)
            self.news_install_btn.setVisible(False)
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

    # -- new-AI-model check (green button on the start page) -------------------
    def _start_model_check(self):
        """Check the BubblR-Model repo for a newer published model version."""
        if not hasattr(self, "model_update_btn"):
            return
        self._model_thread = ModelMetaFetcher(self)
        self._model_thread.loaded.connect(self._on_model_meta)
        self._model_thread.start()

    def _on_model_meta(self, data):
        try:
            self._latest_model_version = int((data or {}).get("version", 0))
        except (TypeError, ValueError):
            self._latest_model_version = 0
        self._refresh_model_banner()

    def _refresh_model_banner(self):
        """Show the green 'new AI model' button only when the experimental AI
        features are on and the repo has a newer model than we downloaded."""
        if not hasattr(self, "model_update_btn"):
            return
        newer = self._latest_model_version > self._ai_model_version
        show = bool(self._experimental_trainer and newer
                    and self._latest_model_version > 0)
        if show:
            self.model_update_btn.setText(
                self._tr("model_update_btn").format(v=self._latest_model_version))
        self.model_update_btn.setVisible(show)

    def _get_ai_model_from_start(self):
        self.model_update_btn.setEnabled(False)
        self.model_update_btn.setText(self._tr("ai_downloading"))
        self._download_ai_model()

    def set_auto_update(self, on):
        self._auto_update = bool(on)
        self._save_settings()

    # -- auto-update (background download → apply on next start) ---------------
    def _start_update_download(self):
        """Fetch the latest-release zip into the staging area in the background.
        On success it is unpacked and applied on the *next* launch (no dialog)."""
        if getattr(self, "_update_thread", None) is not None:
            return                               # already running / downloaded
        if self._pending_update:                 # already staged from before
            self._show_update_ready()
            return
        os.makedirs(UPDATE_STAGE, exist_ok=True)
        dest = os.path.join(UPDATE_STAGE, UPDATE_ASSET)
        self._update_thread = UpdateDownloader(UPDATE_ZIP_URL, dest, self)
        self._update_thread.progress.connect(self._on_update_progress)
        self._update_thread.done.connect(self._on_update_ready)
        self._update_thread.start()

    def _on_update_progress(self, pct):
        pass                                     # silent background download

    def _on_update_ready(self, path):
        self._update_thread = None
        if not path:                             # download failed → keep link
            return
        try:
            src = _stage_update(path)            # unpack to a stable folder
        except Exception:                        # noqa: BLE001
            return
        try:
            os.remove(path)                      # zip no longer needed
        except OSError:
            pass
        self._pending_update = {
            "version": getattr(self, "_latest_version", ""), "src": src}
        self._save_settings()                    # picked up on next start
        self._show_update_ready()

    def _show_update_ready(self):
        """Tell the user the update is downloaded and will apply on next start,
        and offer an optional 'install now' button (no dialog)."""
        v = (self._pending_update or {}).get("version", "")
        self.news_update.setText(self._tr("update_ready_next").format(v=v))
        self.news_update.setVisible(True)
        self.news_install_btn.setText(self._tr("update_install_now"))
        self.news_install_btn.setEnabled(True)
        self.news_install_btn.setVisible(True)

    # -- updating a source checkout (no .exe) ---------------------------------
    def _app_dir(self):
        """The folder this app runs from (works frozen and from source)."""
        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def _source_update(self):
        """Update the source version in place with git. The .exe updater can't be
        used here, but 'you're on your own' isn't good enough either — if this is
        a git checkout we can simply pull."""
        root = self._app_dir()
        if not os.path.isdir(os.path.join(root, ".git")):
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Information)
            box.setWindowTitle(self._tr("update_src_title"))
            box.setText(self._tr("update_src_nogit"))
            rel = box.addButton(self._tr("update_src_releases"),
                                QMessageBox.ActionRole)
            box.addButton(QMessageBox.Close)
            box.exec_()
            if box.clickedButton() is rel:
                QDesktopServices.openUrl(QUrl(RELEASES_URL))
            return
        if QMessageBox.question(
                self, self._tr("update_src_title"), self._tr("update_src_ask"),
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        self._status(self._tr("update_src_pulling"))
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            r = subprocess.run(["git", "pull", "--ff-only"], cwd=root,
                               capture_output=True, text=True, timeout=120)
            out = ((r.stdout or "") + (r.stderr or "")).strip()
            ok = r.returncode == 0
        except Exception as e:                   # noqa: BLE001 (no git, offline)
            out, ok = str(e), False
        finally:
            QApplication.restoreOverrideCursor()
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Information if ok else QMessageBox.Warning)
        box.setWindowTitle(self._tr("update_src_title"))
        box.setText(self._tr("update_src_done") if ok
                    else self._tr("update_src_fail"))
        box.setDetailedText(out or "-")
        box.exec_()
        self._status(self._tr("update_src_done") if ok
                     else self._tr("update_src_fail"), error=not ok)

    def _install_update(self):
        """Optional 'install now': apply the staged update immediately and quit
        (the helper swaps files and relaunches). No confirmation dialog."""
        if not getattr(sys, "frozen", False):
            self._source_update()                # source mode: pull instead
            return
        pu = self._pending_update
        if not pu:
            return
        src = pu.get("src")
        exe_name = os.path.basename(sys.executable)
        if not src or not os.path.exists(os.path.join(src, exe_name)):
            return
        # Clear the pending flag so the next start doesn't try again after we
        # apply it here-and-now.
        self._pending_update = None
        self._save_settings()
        try:
            _launch_swap_helper(src)
        except Exception as e:                   # noqa: BLE001
            QMessageBox.warning(self, "BubblR Trainer",
                                self._tr("update_failed") + "\n\n%s" % e)
            return
        QApplication.quit()

    # -- explicit (manual) install of a chosen version ------------------------
    def _manual_update(self, button=None):
        """Download the newest release and install it right away."""
        self._download_install_now(UPDATE_ZIP_URL,
                                   getattr(self, "_latest_version", ""), button)

    def _install_version(self, version, button=None):
        """Download and install a specific chosen version (up- or downgrade)."""
        if not version:
            return
        if version == VERSION:
            QMessageBox.information(self, "BubblR Trainer",
                                    self._tr("update_already_on").format(v=version))
            return
        self._download_install_now(_version_zip_url(version), version, button)

    def _download_install_now(self, url, version, button=None):
        """Download a specific build in the background, then swap it in and
        relaunch immediately (used by the manual Update button and version
        picker). No 'apply on next start' — the user asked for it now."""
        if not getattr(sys, "frozen", False):
            self._source_update()                # source mode: git pull
            return
        if getattr(self, "_update_thread", None) is not None:
            return
        self._install_btn = button
        if button is not None:
            button.setEnabled(False)
            button.setText(self._tr("update_downloading"))
        os.makedirs(UPDATE_STAGE, exist_ok=True)
        dest = os.path.join(UPDATE_STAGE, UPDATE_ASSET)
        self._update_thread = UpdateDownloader(url, dest, self)
        self._update_thread.done.connect(self._on_install_download_done)
        self._update_thread.start()

    def _on_install_download_done(self, path):
        self._update_thread = None
        btn = getattr(self, "_install_btn", None)

        def _fail(msg):
            if btn is not None:
                btn.setEnabled(True)
                btn.setText(self._tr("update_btn"))
            QMessageBox.warning(self, "BubblR Trainer", msg)

        if not path:
            _fail(self._tr("update_failed"))
            return
        try:
            src = _stage_update(path)
            os.remove(path)
        except Exception as e:                   # noqa: BLE001
            _fail(self._tr("update_failed") + "\n\n%s" % e)
            return
        self._pending_update = None              # applying now, not next start
        self._save_settings()
        try:
            _launch_swap_helper(src)
        except Exception as e:                   # noqa: BLE001
            _fail(self._tr("update_failed") + "\n\n%s" % e)
            return
        QApplication.quit()

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
        self._apply_dock_visibility(not start)
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
            self._dock_syncing = True        # restoreState toggles visibility
            try:
                self.restoreState(bytes.fromhex(ds))
                self._apply_thumbs_flow(self.dockWidgetArea(self.thumbs_dock))
                self._apply_dock_lock()
            except Exception:                # noqa: BLE001
                pass
            finally:
                self._dock_syncing = False
        # restoreState() brings back whatever visibility was saved; re-apply the
        # user's own choice on top of it (this used to force every dock visible,
        # so a panel you closed was always back on the next start).
        self._apply_dock_visibility(True)
        # restoreState is unreliable for dock SIZES, so force them, and again a
        # few times as the layout settles (the editor was just switched in)
        if ds and getattr(self, "_pending_dock_sizes", None):
            self._restore_dock_sizes()
            for delay in (0, 30, 120):
                QTimer.singleShot(delay, self._restore_dock_sizes)
        else:
            # Fresh / reset layout: give the pages panel room for two columns.
            self._apply_default_dock_sizes()
            for delay in (0, 30, 120):
                QTimer.singleShot(delay, self._apply_default_dock_sizes)

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
        # Qt hides every dock while the window closes, which would otherwise be
        # recorded as "the user closed this panel" and leave them all shut on the
        # next start. Stop listening before that happens.
        self._closing = True
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
        tr = self._tr
        lines = []
        for grp in SHORTCUT_GROUPS:
            rows = []
            for aid, (g, lbl_key, _d) in SHORTCUT_DEFS:
                if g != grp:
                    continue
                seq = self._sc_seq(aid)
                keys = QKeySequence(seq).toString(QKeySequence.NativeText) \
                    if seq else "—"
                rows.append("   %-22s %s" % (tr(lbl_key), keys))
            if rows:
                lines.append(tr(grp))
                lines.extend(rows)
                lines.append("")
        lines.append(tr("sh_extra"))
        lines.append("")
        lines.append(tr("sh_customize_hint"))
        QMessageBox.information(self, tr("sh_title"), "\n".join(lines))

    def _show_about(self):
        QMessageBox.about(
            self, self._tr("mi_about"),
            "BubblR Trainer v%s\n\n%s" % (VERSION, self._tr("about_text")))

    def _show_train_help(self):
        """A scrollable guide: how model training works and what you need."""
        dlg = QDialog(self)
        dlg.setWindowTitle(self._tr("train_help_title"))
        dlg.setWindowIcon(app_icon())
        dlg.resize(640, 560)
        lay = QVBoxLayout(dlg)
        view = QTextBrowser()
        view.setOpenExternalLinks(True)
        view.setStyleSheet("background:#232629;")
        view.setHtml(self._tr("train_help_html"))
        lay.addWidget(view)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(dlg.reject)
        bb.accepted.connect(dlg.accept)
        lay.addWidget(bb)
        dark_titlebar(dlg)
        dlg.exec_()

    # -- menu bar --
    # -- customizable keyboard shortcuts -------------------------------------
    def _sc_seq(self, aid):
        """Effective key sequence for an action id (override, else default)."""
        return self._sc_over.get(aid, SHORTCUT_DEFAULT.get(aid, ""))

    def _sc_keys(self, aid):
        """All QKeySequences for an id: the (customizable) primary plus any
        fixed aliases. An empty primary yields no primary sequence."""
        seq = self._sc_seq(aid)
        out = [QKeySequence(seq)] if seq else []
        out += [QKeySequence(a) for a in SHORTCUT_ALIASES.get(aid, [])]
        return out

    def _sc_callable(self, aid):
        """The action to run for a non-menu shortcut id, or None."""
        return {
            "tool_rect":    lambda: self._kbd_tool("rect"),
            "tool_ellipse": lambda: self._kbd_tool("ellipse"),
            "tool_poly":    lambda: self._kbd_tool("poly"),
            "tool_lasso":   lambda: self._kbd_tool("lasso"),
            "tool_wand":    lambda: self._kbd_tool("wand"),
            "set_order":    lambda: self.order_btn.toggle(),
            "auto_order":   self.on_auto_order,
            "clear_order":  self.on_clear_order,
            "deselect":     self._deselect,
        }.get(aid)

    def _kbd_tool(self, key):
        """Pick a marking tool from the keyboard (updates the button too)."""
        btn = self.tool_btns.get(key)
        if btn:
            btn.setChecked(True)
        self._on_tool(key)

    def _install_shortcuts(self):
        """Create QShortcuts for the non-menu actions (selectors, reading order,
        deselect). Menu items get their sequences in _build_menu. Called once."""
        for aid, (grp, _lbl, _dflt) in SHORTCUT_DEFS:
            fn = self._sc_callable(aid)
            if fn is None:                       # menu items handled elsewhere
                continue
            qs = QShortcut(QKeySequence(), self)
            qs.activated.connect(fn)
            self._sc_qs[aid] = qs
            self._apply_shortcut(aid)

    def _apply_shortcut(self, aid):
        """Push the effective sequence(s) onto the live QAction / QShortcut."""
        keys = self._sc_keys(aid)
        act = self._sc_act.get(aid)
        if act is not None:
            act.setShortcuts(keys)
        qs = self._sc_qs.get(aid)
        if qs is not None:
            qs.setKey(keys[0] if keys else QKeySequence())
            qs.setEnabled(bool(keys))

    def _set_shortcut(self, aid, seq):
        """Change a shortcut (seq='' unbinds it), persist, and apply live."""
        seq = (seq or "").strip()
        if seq == SHORTCUT_DEFAULT.get(aid, ""):
            self._sc_over.pop(aid, None)         # back to default -> no override
        else:
            self._sc_over[aid] = seq
        self._apply_shortcut(aid)
        self._save_settings()

    def _reset_all_shortcuts(self):
        self._sc_over.clear()
        for aid, _ in SHORTCUT_DEFS:
            self._apply_shortcut(aid)
        self._save_settings()

    def _sc_conflicts(self):
        """Return the set of ids whose primary sequence collides with another
        (case-insensitive), so the Settings page can flag them."""
        seen, bad = {}, set()
        for aid, _ in SHORTCUT_DEFS:
            s = self._sc_seq(aid)
            if not s:
                continue
            norm = QKeySequence(s).toString(QKeySequence.PortableText).lower()
            if norm in seen:
                bad.add(aid)
                bad.add(seen[norm])
            else:
                seen[norm] = aid
        return bad

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
            ("m_tools", [
                ("mi_train_model", self._launch_model_trainer, None),
                None,
                ("mi_get_model", self._download_ai_model, None),
                ("mi_ai_detect", self._ai_detect_page, None),
                ("mi_ai_check", self._ai_check_dialog, None),
            ]),
            ("m_settings", self._open_settings),   # opens the Settings window
            ("m_help", [
                ("mi_shortcuts", self._show_shortcuts, "F1"),
                ("mi_train_help", self._show_train_help, None),
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
            if mkey == "m_tools":                 # gated behind the experimental flag
                self._tools_menu = menu
            for item in items:
                if item is None:
                    menu.addSeparator()
                    continue
                akey, fn, sc = item
                if fn == "__dockers__":           # submenu: show/hide each dock
                    sub = menu.addMenu(self._tr(akey))
                    self._menu_titles.append((sub, akey))
                    # own checkable actions (toggleViewAction is disabled when the
                    # docks aren't closable, e.g. when panels are locked)
                    self._docker_acts = []
                    for d in getattr(self, "_docks", []):
                        act = sub.addAction(d.windowTitle())
                        act.setCheckable(True)
                        act.setChecked(d.isVisible())
                        act.toggled.connect(
                            lambda on, dk=d: self._set_dock_wanted(dk, on))
                        self._docker_acts.append((act, d))
                    sub.aboutToShow.connect(self._sync_docker_menu)
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
                if akey in SHORTCUT_DEFAULT:          # customizable in Settings
                    self._sc_act[akey] = act
                    self._apply_shortcut(akey)
                elif isinstance(sc, (list, tuple)):
                    act.setShortcuts([QKeySequence(s) for s in sc])
                elif sc:
                    act.setShortcut(QKeySequence(sc))
                act.triggered.connect(lambda _checked=False, f=fn: f())
                self._menu_actions.append((act, akey))
        self._apply_experimental()

    def _apply_experimental(self):
        """Show the Tools menu (Model Trainer) only when the experimental flag
        is on, so the companion app stays hidden until opted in."""
        menu = getattr(self, "_tools_menu", None)
        if menu is not None:
            menu.menuAction().setVisible(bool(self._experimental_trainer))
        self._refresh_model_banner()             # the AI-model button is gated too

    def _launch_model_trainer(self):
        """Open the companion BubblR Model Trainer (YOLO training GUI). Looks for
        the bundled exe next to us (frozen) or the .py beside this script."""
        home = os.path.expanduser("~")
        if getattr(sys, "frozen", False):
            here = os.path.dirname(sys.executable)
            candidates = [
                os.path.join(home, "BubblR Model Trainer",
                             "BubblR-Model-Trainer.exe"),
                os.path.join(here, "BubblR-Model-Trainer.exe"),
                os.path.join(here, "BubblR-Model-Trainer",
                             "BubblR-Model-Trainer.exe"),
                os.path.join(os.path.dirname(here), "BubblR-Model-Trainer",
                             "BubblR-Model-Trainer.exe")]
            for exe in candidates:
                if os.path.isfile(exe):
                    try:
                        subprocess.Popen([exe], close_fds=True)
                        return
                    except OSError:
                        break
        else:
            script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "bubblr_model_trainer.py")
            if os.path.isfile(script):
                try:
                    subprocess.Popen([sys.executable, script], close_fds=True)
                    return
                except OSError:
                    pass
        QMessageBox.information(self, self._tr("mi_train_model"),
                                self._tr("train_model_missing"))

    # -- shared AI model: download + pre-labelling ---------------------------
    def _download_ai_model(self):
        if getattr(self, "_aimodel_thread", None) is not None:
            return
        self._status(self._tr("ai_downloading"))
        self._aimodel_thread = AiModelFetcher(self)
        self._aimodel_thread.done.connect(self._on_ai_model_downloaded)
        self._aimodel_thread.start()

    def _on_ai_model_downloaded(self, path):
        self._aimodel_thread = None
        if hasattr(self, "model_update_btn"):
            self.model_update_btn.setEnabled(True)
        if path:
            # remember which model version we now have, and drop the banner
            if self._latest_model_version:
                self._ai_model_version = self._latest_model_version
                self._save_settings()
            self._refresh_model_banner()
            self._status(self._tr("ai_model_ready"))
        else:
            self._refresh_model_banner()
            self._status(self._tr("ai_model_none"), error=True)

    def _ai_detect_page(self):
        """Run the shared model on the current page and add the detected boxes
        (pre-labelling). Uses the BubblR AI tool's Python env (has ultralytics)."""
        pg = self._page()
        if not pg:
            self._status(self._tr("no_page"), error=True)
            return
        mp = model_path()
        if not os.path.isfile(mp):
            if QMessageBox.question(
                    self, self._tr("mi_get_model"), self._tr("ai_need_model"),
                    QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                self._download_ai_model()
            return
        # use the full discovery (setting → AI folder → sibling venv → system
        # scan) so AI-detect works out of the box, not just when an AI folder
        # is configured
        if not is_valid_model(mp):
            self._ai_failed("ai_detect_fail",
                            "model file is corrupt: %s" % mp)
            return
        py = self._ultra_python()
        if not py:
            self._status(self._tr("ai_no_env"), error=True)
            self._ai_check_dialog()
            return
        # only bail if a detect run is GENUINELY still going; a process that
        # failed to start would otherwise block detection for the whole session
        proc = getattr(self, "_detect_proc", None)
        if proc is not None and proc.state() != QProcess.NotRunning:
            return
        # source image: the page's file if present, else write the QImage to temp
        src = pg.get("path", "")
        if not src or not os.path.isfile(src):
            src = os.path.join(tempfile.mkdtemp(prefix="bubblr_det_"), "page.png")
            pg["img"].save(src, "PNG")
        cfg = detect_config(mp, src, imgsz=max(320, min(1280,
                            (pg["img"].width() // 32) * 32 or 640)))
        d = tempfile.mkdtemp(prefix="bubblr_detect_")
        sp = os.path.join(d, "detect.py")
        cp = os.path.join(d, "cfg.json")
        with open(sp, "w", encoding="utf-8") as f:
            f.write(build_detect_script(cfg))
        with open(cp, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        self._detect_page = pg
        self._detect_out = []
        self._detect_log = ""
        self._status(self._tr("ai_detecting"))
        self._detect_proc = QProcess(self)
        self._detect_proc.setProcessChannelMode(QProcess.MergedChannels)
        self._detect_proc.readyReadStandardOutput.connect(self._detect_output)
        self._detect_proc.finished.connect(self._detect_finished)
        self._detect_proc.errorOccurred.connect(self._detect_error)
        self._detect_proc.start(py, ["-u", sp, cp])

    def _detect_error(self, _err):
        """The detect process couldn't even start (bad Python path). Without
        this, finished() never fires and _detect_proc stays set forever, which
        would silently block every later detection."""
        self._detect_proc = None
        self._ai_failed("ai_detect_fail",
                        "could not start the AI Python:\n%s"
                        % self._ultra_python())

    def _detect_output(self):
        data = bytes(self._detect_proc.readAllStandardOutput()).decode(
            "utf-8", "replace")
        # Keep the whole log (stdout+stderr are merged): if the run dies, this
        # is the only place the real reason exists.
        self._detect_log = getattr(self, "_detect_log", "") + data
        for line in data.splitlines():
            if line.startswith("BUBBLR_BOXES"):
                try:
                    self._detect_out = json.loads(line.split(" ", 1)[1])
                except Exception:                # noqa: BLE001
                    self._detect_out = []

    def _detect_finished(self, code, _status):
        self._detect_proc = None
        pg = getattr(self, "_detect_page", None)
        dets = getattr(self, "_detect_out", [])
        if code != 0 or pg is None:
            self._ai_failed("ai_detect_fail", getattr(self, "_detect_log", ""))
            return
        if not dets:
            self._status(self._tr("ai_detect_none"))
            return
        W, H = pg["img"].width(), pg["img"].height()
        keys = self._class_keys()
        self._push_undo()
        added = 0
        for det in dets:
            cw, ch = det["w"] * W, det["h"] * H
            x = det["cx"] * W - cw / 2.0
            y = det["cy"] * H - ch / 2.0
            if cw < 4 or ch < 4:
                continue
            ci = int(det.get("cls", 0))
            kind = keys[ci] if 0 <= ci < len(keys) else keys[0]
            pg["boxes"].append({
                "x": int(round(max(0, x))), "y": int(round(max(0, y))),
                "w": int(round(cw)), "h": int(round(ch)),
                "kind": kind, "order": 0, "shape": "rect"})
            added += 1
        self._current = len(pg["boxes"]) - 1 if added else self._current
        self._maybe_auto_order()
        self._refresh()
        self._status(self._tr("ai_detect_done").format(n=added))

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

        # -- Updates page: auto/manual, manual Update button, version picker --
        upd = QWidget()
        uv = QVBoxLayout(upd)
        upd_title = QLabel()
        upd_title.setStyleSheet("font-weight: bold;")
        uv.addWidget(upd_title)
        upd_grp = QButtonGroup(dlg)
        rb_auto = QRadioButton()
        rb_manual = QRadioButton()
        upd_grp.addButton(rb_auto)
        upd_grp.addButton(rb_manual)
        rb_auto.setChecked(self._auto_update)
        rb_manual.setChecked(not self._auto_update)
        uv.addWidget(rb_auto)
        uv.addWidget(rb_manual)
        upd_mode_hint = QLabel()
        upd_mode_hint.setWordWrap(True)
        upd_mode_hint.setStyleSheet("color: gray;")
        uv.addWidget(upd_mode_hint)
        uv.addSpacing(12)
        # available-update row: version on the left, "Update" button on the right
        upd_row = QWidget()
        rowl = QHBoxLayout(upd_row)
        rowl.setContentsMargins(0, 0, 0, 0)
        upd_avail_lbl = QLabel()
        upd_btn = QPushButton()
        upd_btn.setStyleSheet(
            "background:#2f6f3f;color:#eaffea;font-weight:bold;"
            "border:none;border-radius:5px;padding:7px 16px;")
        rowl.addWidget(upd_avail_lbl)
        rowl.addStretch(1)
        rowl.addWidget(upd_btn)
        uv.addWidget(upd_row)
        upd_status = QLabel()
        upd_status.setStyleSheet("color: gray;")
        upd_status.setWordWrap(True)
        uv.addWidget(upd_status)
        uv.addSpacing(18)
        # pick a specific version (up- or downgrade)
        pick_lbl = QLabel()
        uv.addWidget(pick_lbl)
        pick_row = QWidget()
        pl = QHBoxLayout(pick_row)
        pl.setContentsMargins(0, 0, 0, 0)
        ver_combo = QComboBox()
        ver_combo.setMinimumWidth(150)
        ver_combo.setEnabled(False)
        pick_btn = QPushButton()
        pick_btn.setEnabled(False)
        pl.addWidget(ver_combo)
        pl.addStretch(1)
        pl.addWidget(pick_btn)
        uv.addWidget(pick_row)
        pick_hint = QLabel()
        pick_hint.setWordWrap(True)
        pick_hint.setStyleSheet("color: gray;")
        uv.addWidget(pick_hint)
        uv.addStretch(1)
        # current version, centred at the bottom of the tab
        cur_ver_lbl = QLabel()
        cur_ver_lbl.setAlignment(Qt.AlignCenter)
        cur_ver_lbl.setStyleSheet("color: gray;")
        uv.addWidget(cur_ver_lbl)

        def refresh_update_ui():
            avail = getattr(self, "_latest_version", None)
            has = bool(avail and _ver_tuple(avail) > _ver_tuple(VERSION))
            manual = not self._auto_update
            upd_row.setVisible(manual)
            upd_btn.setEnabled(has)
            upd_btn.setText(self._tr("update_btn"))
            if has:
                upd_avail_lbl.setText(self._tr("update_contains").format(v=avail))
                upd_status.setText("" if manual
                                   else self._tr("update_auto_note").format(v=avail))
                upd_status.setVisible(not manual)
            else:
                upd_avail_lbl.setText(self._tr("update_uptodate"))
                upd_status.setText(self._tr("update_uptodate"))
                upd_status.setVisible(not manual)

        def on_mode(_=None):
            self._auto_update = rb_auto.isChecked()
            self._save_settings()
            refresh_update_ui()
            if self._auto_update and getattr(sys, "frozen", False):
                self._start_update_download()    # resume auto behaviour

        rb_auto.toggled.connect(on_mode)
        upd_btn.clicked.connect(lambda: self._manual_update(upd_btn))
        pick_btn.clicked.connect(
            lambda: self._install_version(ver_combo.currentText(), pick_btn))

        def on_versions(vers):
            try:                                 # dialog may already be closed
                ver_combo.clear()
                if not vers:
                    ver_combo.addItem(self._tr("update_no_versions"))
                    ver_combo.setEnabled(False)
                    pick_btn.setEnabled(False)
                    return
                for v in vers:                   # plain version = currentText()
                    ver_combo.addItem(v)
                ver_combo.setEnabled(True)
                pick_btn.setEnabled(True)
            except RuntimeError:
                pass

        ver_combo.addItem(self._tr("update_loading_versions"))
        self._rel_thread = ReleasesFetcher(self)
        self._rel_thread.loaded.connect(on_versions)
        self._rel_thread.start()

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
        sv.addSpacing(12)
        bg_box = QCheckBox()
        bg_box.setChecked(self._export_bg)

        def on_bg(on):
            self._export_bg = bool(on)
            self._save_settings()

        bg_box.toggled.connect(on_bg)
        sv.addWidget(bg_box)
        bg_hint = QLabel()
        bg_hint.setWordWrap(True)
        bg_hint.setStyleSheet("color: gray;")
        sv.addWidget(bg_hint)
        sv.addSpacing(12)
        seg_box = QCheckBox()
        seg_box.setChecked(self._seg_export)

        def on_seg(on):
            self._seg_export = bool(on)
            self._save_settings()

        seg_box.toggled.connect(on_seg)
        sv.addWidget(seg_box)
        seg_hint = QLabel()
        seg_hint.setWordWrap(True)
        seg_hint.setStyleSheet("color: gray;")
        sv.addWidget(seg_hint)
        sv.addSpacing(12)
        coco_box = QCheckBox()
        coco_box.setChecked(self._coco_export)

        def on_coco(on):
            self._coco_export = bool(on)
            self._save_settings()

        coco_box.toggled.connect(on_coco)
        sv.addWidget(coco_box)
        coco_hint = QLabel()
        coco_hint.setWordWrap(True)
        coco_hint.setStyleSheet("color: gray;")
        sv.addWidget(coco_hint)
        sv.addStretch(1)

        # -- Experimental page: opt-in switches for unfinished features --
        exp = QWidget()
        xv = QVBoxLayout(exp)
        exp_title = QLabel()
        exp_title.setStyleSheet("font-weight: bold;")
        xv.addWidget(exp_title)
        exp_intro = QLabel()
        exp_intro.setWordWrap(True)
        exp_intro.setStyleSheet("color: gray;")
        xv.addWidget(exp_intro)
        xv.addSpacing(10)
        exp_trainer_box = QCheckBox()
        exp_trainer_box.setChecked(self._experimental_trainer)

        def on_exp_trainer(on):
            self._experimental_trainer = bool(on)
            self._save_settings()
            self._apply_experimental()           # show/hide Tools menu live

        exp_trainer_box.toggled.connect(on_exp_trainer)
        xv.addWidget(exp_trainer_box)
        exp_trainer_hint = QLabel()
        exp_trainer_hint.setWordWrap(True)
        exp_trainer_hint.setStyleSheet("color: gray;")
        xv.addWidget(exp_trainer_hint)
        xv.addSpacing(14)
        # -- AI model used for ranking / detection --
        exp_ai_title = QLabel()
        exp_ai_title.setStyleSheet("font-weight: bold;")
        xv.addWidget(exp_ai_title)
        rmrow = QHBoxLayout()
        rank_lbl = QLabel()
        rank_model_edit = QLineEdit(self._rank_model_path)
        rank_model_edit.setPlaceholderText(
            "empty = use the downloaded shared model")

        def on_rank_model():
            self._rank_model_path = rank_model_edit.text().strip()
            self._save_settings()

        rank_model_edit.editingFinished.connect(on_rank_model)
        rank_browse = QPushButton(self._tr("mi_folder"))

        def pick_rank_model():
            p, _ = QFileDialog.getOpenFileName(
                self, self._tr("exp_rank_model"), self._start_dir(),
                "PyTorch weights (*.pt)")
            if p:
                rank_model_edit.setText(p)
                on_rank_model()

        rank_browse.clicked.connect(pick_rank_model)
        rank_browse.setText(self._tr("browse"))
        rank_dl = QPushButton(self._tr("exp_rank_download"))
        rank_dl.clicked.connect(self._download_ai_model)
        rmrow.addWidget(rank_lbl)
        rmrow.addWidget(rank_model_edit, 1)
        rmrow.addWidget(rank_browse)
        rmrow.addWidget(rank_dl)
        xv.addLayout(rmrow)
        rank_hint = QLabel()
        rank_hint.setWordWrap(True)
        rank_hint.setStyleSheet("color: gray;")
        xv.addWidget(rank_hint)
        xv.addSpacing(8)
        aprow = QHBoxLayout()
        aipy_lbl = QLabel()
        aipy_edit = QLineEdit(self._ai_python_path)
        aipy_edit.setPlaceholderText(self._tr("exp_ai_python_ph"))

        def on_aipy():
            self._ai_python_path = aipy_edit.text().strip()
            self._forget_ai_python()             # re-probe with the new setting
            self._save_settings()

        aipy_edit.editingFinished.connect(on_aipy)
        aipy_browse = QPushButton(self._tr("browse"))

        def pick_aipy():
            p, _ = QFileDialog.getOpenFileName(
                self, self._tr("exp_ai_python"), self._start_dir(),
                "Python (python*.exe python*)")
            if p:
                aipy_edit.setText(p)
                on_aipy()

        aipy_browse.clicked.connect(pick_aipy)
        aipy_find = QPushButton(self._tr("py_find"))

        def find_py():
            aipy_find.setEnabled(False)
            aipy_find.setText(self._tr("py_finding"))
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                found, ok = best_ai_python()
            finally:
                QApplication.restoreOverrideCursor()
                aipy_find.setEnabled(True)
                aipy_find.setText(self._tr("py_find"))
            if found:
                aipy_edit.setText(found)
                on_aipy()
                QMessageBox.information(
                    self, self._tr("py_find"),
                    self._tr("py_found_ultra" if ok else "py_found_no_ultra")
                    .format(p=found))
            else:
                QMessageBox.information(self, self._tr("py_find"),
                                        self._tr("py_none"))

        aipy_find.clicked.connect(find_py)
        aipy_get = QPushButton(self._tr("py_get"))
        aipy_get.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(PYTHON_DOWNLOAD_URL)))
        # Install Ultralytics without leaving the app: this used to live only in
        # the Model Trainer, which a labeller has no other reason to open.
        aipy_install = QPushButton(self._tr("py_install"))

        def installed(ok, py):
            if ok:
                aipy_edit.setText(py)            # show the env that now works

        aipy_install.clicked.connect(
            lambda: self._install_ultralytics(on_done=installed))
        aprow.addWidget(aipy_lbl)
        aprow.addWidget(aipy_edit, 1)
        aprow.addWidget(aipy_browse)
        aprow.addWidget(aipy_find)
        aprow.addWidget(aipy_get)
        aprow.addWidget(aipy_install)
        xv.addLayout(aprow)
        aipy_hint = QLabel()
        aipy_hint.setWordWrap(True)
        aipy_hint.setStyleSheet("color: gray;")
        xv.addWidget(aipy_hint)
        xv.addStretch(1)

        # -- Shortcuts page: customize every keyboard shortcut --
        scp = QWidget()
        scv = QVBoxLayout(scp)
        sc_title = QLabel()
        sc_title.setStyleSheet("font-weight: bold;")
        scv.addWidget(sc_title)
        sc_intro = QLabel()
        sc_intro.setWordWrap(True)
        sc_intro.setStyleSheet("color: gray;")
        scv.addWidget(sc_intro)
        sc_scroll = QScrollArea()
        sc_scroll.setWidgetResizable(True)
        sc_inner = QWidget()
        sc_grid = QGridLayout(sc_inner)
        sc_grid.setContentsMargins(0, 4, 0, 4)
        sc_grid.setHorizontalSpacing(10)
        sc_grid.setColumnStretch(0, 1)
        sc_scroll.setWidget(sc_inner)
        scv.addWidget(sc_scroll, 1)
        sc_reset_all = QPushButton()
        scv.addWidget(sc_reset_all, 0, Qt.AlignRight)
        # row widgets we must retranslate / refresh
        sc_row_labels = []                   # (QLabel, label_key)
        sc_group_labels = []                 # (QLabel, group_key)
        sc_edits = {}                        # id -> QKeySequenceEdit

        def sc_refresh_conflicts():
            bad = self._sc_conflicts()
            for aid, ed in sc_edits.items():
                ed.setStyleSheet("QKeySequenceEdit{border:1px solid #c0392b;}"
                                 if aid in bad else "")

        def sc_commit(aid, ed):
            ks = ed.keySequence()
            self._set_shortcut(aid, ks.toString(QKeySequence.PortableText))
            sc_refresh_conflicts()

        def sc_reset_one(aid, ed):
            ed.setKeySequence(QKeySequence(SHORTCUT_DEFAULT.get(aid, "")))
            self._set_shortcut(aid, SHORTCUT_DEFAULT.get(aid, ""))
            sc_refresh_conflicts()

        def sc_reset_every():
            self._reset_all_shortcuts()
            for aid, ed in sc_edits.items():
                ed.blockSignals(True)
                ed.setKeySequence(QKeySequence(self._sc_seq(aid)))
                ed.blockSignals(False)
            sc_refresh_conflicts()

        sc_reset_all.clicked.connect(sc_reset_every)

        # build one row per action, grouped by category
        _r = 0
        for grp in SHORTCUT_GROUPS:
            hdr = QLabel()
            hdr.setStyleSheet("font-weight: bold; margin-top: 8px;")
            sc_group_labels.append((hdr, grp))
            sc_grid.addWidget(hdr, _r, 0, 1, 3)
            _r += 1
            for aid, (g, lbl_key, _dflt) in SHORTCUT_DEFS:
                if g != grp:
                    continue
                lab = QLabel()
                sc_row_labels.append((lab, lbl_key))
                sc_grid.addWidget(lab, _r, 0)
                ed = QKeySequenceEdit(QKeySequence(self._sc_seq(aid)))
                ed.setMaximumWidth(160)
                sc_edits[aid] = ed
                sc_grid.addWidget(ed, _r, 1)
                rb = QPushButton()
                rb.setProperty("sc_reset", True)
                rb.clicked.connect(
                    lambda _c=False, a=aid, e=ed: sc_reset_one(a, e))
                sc_grid.addWidget(rb, _r, 2)
                ed.editingFinished.connect(
                    lambda a=aid, e=ed: sc_commit(a, e))
                _r += 1
        sc_grid.setRowStretch(_r, 1)
        sc_refresh_conflicts()

        stack.addWidget(disp)
        stack.addWidget(upd)
        stack.addWidget(newp)
        stack.addWidget(clsp)
        stack.addWidget(toolsp)
        stack.addWidget(disc)
        stack.addWidget(store)
        stack.addWidget(exp)
        stack.addWidget(scp)
        nav.currentRowChanged.connect(stack.setCurrentIndex)

        def apply_texts():
            tr = self._tr
            dlg.setWindowTitle(tr("m_settings"))
            row = nav.currentRow()
            nav.blockSignals(True)
            nav.clear()
            nav.addItem(tr("settings_display"))
            nav.addItem(tr("settings_updates"))
            nav.addItem(tr("settings_newbox"))
            nav.addItem(tr("settings_classes"))
            nav.addItem(tr("settings_tools"))
            nav.addItem(tr("settings_discord"))
            nav.addItem(tr("settings_storage"))
            nav.addItem(tr("settings_experimental"))
            nav.addItem(tr("settings_shortcuts"))
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
            upd_title.setText(tr("settings_updates"))
            rb_auto.setText(tr("update_mode_auto"))
            rb_manual.setText(tr("update_mode_manual"))
            upd_mode_hint.setText(tr("update_mode_hint"))
            pick_lbl.setText(tr("update_pick_label"))
            pick_btn.setText(tr("update_pick_btn"))
            pick_hint.setText(tr("update_pick_hint"))
            cur_ver_lbl.setText(tr("update_current").format(v=VERSION))
            refresh_update_ui()
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
            bg_box.setText(tr("export_bg_toggle"))
            bg_hint.setText(tr("export_bg_hint"))
            seg_box.setText(tr("seg_export_toggle"))
            seg_hint.setText(tr("seg_export_hint"))
            coco_box.setText(tr("coco_export_toggle"))
            coco_hint.setText(tr("coco_export_hint"))
            exp_title.setText(tr("settings_experimental"))
            exp_intro.setText(tr("exp_intro"))
            exp_trainer_box.setText(tr("exp_trainer_toggle"))
            exp_trainer_hint.setText(tr("exp_trainer_hint"))
            exp_ai_title.setText(tr("exp_ai_title"))
            rank_lbl.setText(tr("exp_rank_model"))
            rank_hint.setText(tr("exp_rank_hint"))
            aipy_lbl.setText(tr("exp_ai_python"))
            aipy_hint.setText(tr("exp_ai_python_hint"))
            aipy_install.setText(tr("py_install"))
            sc_title.setText(tr("settings_shortcuts"))
            sc_intro.setText(tr("sc_intro"))
            sc_reset_all.setText(tr("sc_reset_all"))
            for lab, key in sc_group_labels:
                lab.setText(tr(key))
            for lab, key in sc_row_labels:
                lab.setText(tr(key))
            for _btn in sc_inner.findChildren(QPushButton):
                if _btn.property("sc_reset"):
                    _btn.setText(tr("sc_reset"))

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
        dark_titlebar(dlg)                       # dark window header, like the app
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

    def _ultra_python(self):
        """A Python that can really run the AI (ultralytics + torch + Pillow):
        the setting, else a .venv in the AI folder or the sibling BubblR-Test/ai,
        else a system-wide scan. '' if none works.

        Every candidate is probed — a path that merely EXISTS is not enough. An
        unusable interpreter used to be handed to the subprocess, which then died
        with a generic 'failed' and no way to see why."""
        cached = getattr(self, "_ultra_python_cache", None)
        if cached is not None:
            return cached
        cands = []
        p = self._ai_python_path
        if p:
            cands.append(p)                      # the user's explicit choice
        base = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
                else os.path.dirname(os.path.abspath(__file__)))
        for d in (self._ai_dir,
                  os.path.normpath(os.path.join(base, "..", "BubblR-Test",
                                                "ai"))):
            if d:
                v = self._ai_python(d)
                if v:
                    cands.append(v)
        found = ""
        report = None
        for c in cands:
            ok, rep = probe_ai_python(c)
            if ok:
                found = c
                report = rep
                break
            if report is None:
                report = rep                     # remember the first failure
        if not found:
            # nothing configured works: scan the machine (cached — it is slow)
            sysfound, ok = best_ai_python()
            if ok:
                found = sysfound
                report = probe_ai_python(sysfound)[1]
        self._ultra_python_cache = found
        self._ai_report = report
        return found

    def _forget_ai_python(self):
        """Drop the cached probe so the next AI run re-checks the environment
        (after the user picks another Python or installs Ultralytics)."""
        self._ultra_python_cache = None
        self._ai_report = None

    def _install_target_python(self):
        """The Python to install Ultralytics INTO. Unlike _ultra_python() this
        does not require a working AI env — that is what we are about to create.
        Never sys.executable: in the .exe build that is BubblR-Trainer.exe."""
        p = self._ai_python_path
        if p and os.path.isfile(p):
            return p
        found, _ok = best_ai_python()            # prefers a ready one
        if found:
            return found
        cands = find_python_candidates()
        return cands[0] if cands else ""

    def _install_ultralytics(self, on_done=None):
        """Install Ultralytics (and PyTorch) into the chosen Python, right from
        Settings — so the AI can be set up without opening the Model Trainer.
        Streams pip's output into a dialog, because this takes minutes and a
        frozen window looks like a crash."""
        py = self._install_target_python()
        if not py:
            QMessageBox.information(self, self._tr("py_install_title"),
                                    self._tr("py_install_none"))
            return
        if QMessageBox.question(
                self, self._tr("py_install_title"),
                self._tr("py_install_ask").format(p=py),
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(self._tr("py_install_title"))
        v = QVBoxLayout(dlg)
        head = QLabel(self._tr("py_install_running"))
        head.setWordWrap(True)
        v.addWidget(head)
        log = QTextBrowser()
        log.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        v.addWidget(log, 1)
        close = QPushButton(self._tr("py_install_close"))
        close.setEnabled(False)                  # only once pip is done
        close.clicked.connect(dlg.accept)
        v.addWidget(close)
        dlg.resize(660, 380)

        args = pip_install_args(py)
        log.append("$ " + " ".join(args) + "\n")
        proc = QProcess(dlg)
        proc.setProcessChannelMode(QProcess.MergedChannels)

        def on_out():
            data = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
            for line in data.splitlines():
                log.append(strip_ansi(line))

        def on_fin(code, _s):
            ok = code == 0
            head.setText(self._tr("py_install_done") if ok
                         else self._tr("py_install_fail"))
            head.setStyleSheet("font-weight:bold;color:%s;"
                               % ("#7ec87e" if ok else "#e06c6c"))
            close.setEnabled(True)
            if ok:
                self._ai_python_path = py        # remember what now works
                self._forget_ai_python()         # re-probe on the next AI run
                self._save_settings()
            elif diagnose_error(log.toPlainText()):
                log.append("\n" + diagnose_error(log.toPlainText()))
            if on_done:
                on_done(ok, py)

        proc.readyReadStandardOutput.connect(on_out)
        proc.finished.connect(on_fin)
        proc.errorOccurred.connect(
            lambda _e: (log.append("could not start: %s" % py),
                        head.setText(self._tr("py_install_fail")),
                        close.setEnabled(True)))
        proc.start(args[0], args[1:])
        dlg.exec_()

    # -- AI failure reporting -------------------------------------------------
    def _ai_failed(self, key, log):
        """Report a failed AI run properly: a short hint in the status bar plus a
        dialog with the real subprocess log. The old code threw the log away and
        showed only 'failed', which made this impossible to debug on another
        machine."""
        log = (log or "").strip()
        hint = diagnose_error(log)
        self._status(self._tr(key) + ("  " + hint if hint else ""), error=True)
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(self._tr("ai_fail_title"))
        box.setText(self._tr(key))
        box.setInformativeText(hint or self._tr("ai_fail_intro"))
        box.setDetailedText(log[-6000:] if log else self._tr("ai_fail_nolog"))
        check = box.addButton(self._tr("ai_fail_check"),
                              QMessageBox.ActionRole)
        box.addButton(QMessageBox.Close)
        box.exec_()
        if box.clickedButton() is check:
            self._forget_ai_python()
            self._ai_check_dialog()

    def _ai_check_dialog(self):
        """Self-test of the AI setup: which Python, which versions, GPU yes/no,
        is the model there — and a button for each thing that is missing."""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            py = self._ultra_python()
            rep = getattr(self, "_ai_report", None) or {}
        finally:
            QApplication.restoreOverrideCursor()
        mp = model_path()
        if not os.path.isfile(mp):
            model_state = self._tr("aicheck_model_missing")
            model_ok = False
        elif not is_valid_model(mp):
            model_state = self._tr("aicheck_model_bad")
            model_ok = False
        else:
            model_state = mp
            model_ok = True
        vers = rep.get("versions") or {}
        problems = list(rep.get("errors") or [])
        if not py:
            problems.insert(0, self._tr("aicheck_no_python"))
        if not model_ok:
            problems.append("%s: %s" % (self._tr("aicheck_model"), model_state))

        dlg = QDialog(self)
        dlg.setWindowTitle(self._tr("aicheck_title"))
        v = QVBoxLayout(dlg)
        head = QLabel(self._tr("aicheck_ok") if (py and model_ok)
                      else self._tr("aicheck_bad"))
        head.setStyleSheet("font-weight:bold;color:%s;"
                           % ("#7ec87e" if (py and model_ok) else "#e06c6c"))
        v.addWidget(head)
        if problems:
            pl = QLabel("\n".join("• " + p for p in problems))
            pl.setWordWrap(True)
            v.addWidget(pl)
        rows = [
            (self._tr("aicheck_python"), py or self._tr("aicheck_none")),
            ("ultralytics", vers.get("ultralytics", "—")),
            ("torch", vers.get("torch", "—")),
            ("Pillow", vers.get("PIL", "—")),
            (self._tr("aicheck_gpu"), self._tr("aicheck_yes") if rep.get("cuda")
             else self._tr("aicheck_no")),
            (self._tr("aicheck_model"), model_state),
        ]
        grid = QGridLayout()
        for i, (k, val) in enumerate(rows):
            kl = QLabel(k + ":")
            kl.setStyleSheet("color:gray;")
            vl = QLabel(str(val))
            vl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            vl.setWordWrap(True)
            grid.addWidget(kl, i, 0, Qt.AlignTop)
            grid.addWidget(vl, i, 1)
        grid.setColumnStretch(1, 1)
        v.addLayout(grid)

        btns = QHBoxLayout()
        if not model_ok:
            b = QPushButton(self._tr("aicheck_get_model"))
            b.clicked.connect(lambda: (dlg.accept(), self._download_ai_model()))
            btns.addWidget(b)
        if not py:
            # a Python exists but lacks the packages -> offer to install them
            # here, instead of sending the user off to the Model Trainer
            if self._install_target_python():
                b = QPushButton(self._tr("py_install"))
                b.clicked.connect(lambda: (dlg.accept(),
                                           self._install_ultralytics(),
                                           self._ai_check_dialog()))
                btns.addWidget(b)
            else:
                b = QPushButton(self._tr("aicheck_get_python"))
                b.clicked.connect(lambda: QDesktopServices.openUrl(
                    QUrl(PYTHON_DOWNLOAD_URL)))
                btns.addWidget(b)
        if any("dll load failed" in p.lower() for p in problems):
            b = QPushButton(self._tr("aicheck_vcredist"))
            b.clicked.connect(lambda: QDesktopServices.openUrl(
                QUrl(VCREDIST_URL)))
            btns.addWidget(b)
        recheck = QPushButton(self._tr("aicheck_recheck"))
        recheck.clicked.connect(lambda: (dlg.accept(), self._forget_ai_python(),
                                         self._ai_check_dialog()))
        btns.addWidget(recheck)
        btns.addStretch(1)
        close = QPushButton("OK")
        close.clicked.connect(dlg.accept)
        btns.addWidget(close)
        v.addLayout(btns)
        dlg.resize(560, 320)
        dlg.exec_()

    def _rank_model(self):
        """The model used for ranking: the chosen one, else the downloaded shared
        model. '' if neither is usable (a corrupt file counts as missing, so the
        user is offered a fresh download instead of a crash)."""
        m = self._rank_model_path
        if m and os.path.isfile(m):
            return m
        return model_path() if is_valid_model(model_path()) else ""

    def on_rank_load(self):
        """Rank a folder of raw pages by how much the AI model detects, then load
        the top ones. Uses the chosen/downloaded model in-program; falls back to
        the external BubblR AI tool (propose.py) if no model is set up."""
        folder = QFileDialog.getExistingDirectory(
            self, self._tr("rank_pick"), self._start_dir())
        if not folder:
            return
        self._remember_dir(folder)
        # only bail if a rank job is GENUINELY still running; otherwise clear a
        # stale flag (e.g. a previous process that failed to start) so ranking
        # doesn't get permanently stuck doing nothing.
        proc = getattr(self, "_rank_proc", None)
        if proc is not None and proc.state() != QProcess.NotRunning:
            return
        self._ranking = False
        py = self._ultra_python()
        model = self._rank_model()
        # preferred: in-program ranking with a YOLO model
        if py and model:
            top, ok = QInputDialog.getInt(
                self, self._tr("rank_top_title"), self._tr("rank_top_q"),
                30, 1, 2000)
            if not ok:
                return
            cfg = rank_config(model, folder, dataset=self._folder or "")
            d = tempfile.mkdtemp(prefix="bubblr_rank_")
            sp = os.path.join(d, "rank.py")
            cp = os.path.join(d, "cfg.json")
            with open(sp, "w", encoding="utf-8") as f:
                f.write(build_rank_script(cfg))
            with open(cp, "w", encoding="utf-8") as f:
                json.dump(cfg, f)
            self._rank_top = top
            self._rank_buf = ""          # accumulate all stdout, parse at the end
            self._rank_mode = "model"
            self._ranking = True
            self._status(self._tr("rank_running"))
            self._rank_proc = QProcess(self)
            self._rank_proc.setProcessChannelMode(QProcess.MergedChannels)
            self._rank_proc.readyReadStandardOutput.connect(self._rank_output)
            self._rank_proc.finished.connect(self._rank_finished)
            self._rank_proc.errorOccurred.connect(self._rank_error)
            self._rank_proc.start(py, ["-u", sp, cp])
            return
        # fallback: the external propose.py tool
        ai = self._find_ai_dir()
        aipy = self._ai_python(ai) if ai else ""
        if ai and aipy:
            top, ok = QInputDialog.getInt(
                self, self._tr("rank_top_title"), self._tr("rank_top_q"),
                30, 1, 2000)
            if not ok:
                return
            self._rank_folder = folder
            self._rank_mode = "propose"
            self._ranking = True
            self._status(self._tr("rank_running"))
            self._rank_proc = QProcess(self)
            self._rank_proc.setWorkingDirectory(ai)
            self._rank_proc.setProcessChannelMode(QProcess.MergedChannels)
            self._rank_proc.readyReadStandardOutput.connect(self._rank_output)
            self._rank_proc.finished.connect(self._rank_finished)
            self._rank_proc.errorOccurred.connect(self._rank_error)
            self._rank_proc.start(aipy, ["-u", os.path.join(ai, "propose.py"),
                                         "--dir", folder, "--top", str(top)])
            return
        # nothing available: guide the user
        if py and QMessageBox.question(
                self, self._tr("rank_need_model_title"),
                self._tr("rank_need_model"),
                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self._download_ai_model()
        elif not py:
            self._status(self._tr("ai_no_env"), error=True)
            self._ai_check_dialog()              # show exactly what is missing

    def _rank_output(self):
        data = bytes(self._rank_proc.readAllStandardOutput()).decode(
            "utf-8", "replace")
        # Buffer everything: the final 'BUBBLR_RANK <json>' line can be long and
        # arrive split across several reads, so we parse it only once complete.
        self._rank_buf = getattr(self, "_rank_buf", "") + data
        for line in data.splitlines():
            s = line.strip()
            if s and not s.startswith("BUBBLR_RANK"):
                self._status(self._tr("rank_running") + "  " + s[:80])

    def _rank_error(self, _err):
        """The rank process couldn't start (e.g. bad Python path) — clear the
        busy flag so ranking isn't stuck, and tell the user."""
        self._ranking = False
        self._ai_failed("rank_fail", "could not start the AI Python:\n%s"
                        % self._ultra_python())

    def _rank_finished(self, code, _status):
        self._ranking = False
        if code != 0:
            self._ai_failed("rank_fail", getattr(self, "_rank_buf", ""))
            return
        if getattr(self, "_rank_mode", "") == "model":
            ranked = []
            for line in getattr(self, "_rank_buf", "").splitlines():
                if line.startswith("BUBBLR_RANK"):
                    try:
                        ranked = json.loads(line.split(" ", 1)[1])
                    except Exception:            # noqa: BLE001
                        ranked = []
            paths = [row[0] for row in ranked[:getattr(self, "_rank_top", 30)]
                     if row and os.path.isfile(row[0])]
            if not paths:
                self._status(self._tr("rank_empty"), error=True)
                return
            n = self.add_image_paths(paths)
            self._status(self._tr("rank_loaded").format(n=n))
            return
        # propose.py mode: read its _label_first folder
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
        make_label = make_yolo_seg_label if self._seg_export else make_yolo_label
        with open(os.path.join(labels, stem + ".txt"), "w", encoding="utf-8") as fh:
            fh.write(make_label(pg["boxes"], w, h, self._class_index_map()))
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

    def _coco_dict(self, group):
        """Build a COCO-format dict from [(stem, pg), …]. Every box carries a
        bbox and a polygon segmentation (from its outline, or the box corners),
        so the file works for both detection and segmentation frameworks."""
        ci = self._class_index_map()
        cats = [{"id": i + 1, "name": c["label"], "supercategory": "object"}
                for i, c in enumerate(self._classes)]
        images, annotations, ann_id = [], [], 1
        for img_id, (stem, pg) in enumerate(group, start=1):
            w, h = pg["img"].width(), pg["img"].height()
            images.append({"id": img_id, "file_name": stem + ".png",
                           "width": w, "height": h})
            for b in pg["boxes"]:
                cat = ci.get(b.get("kind", "bubble"), 0) + 1   # COCO ids are 1+
                bx, by = float(b["x"]), float(b["y"])
                bw, bh = float(b["w"]), float(b["h"])
                seg = []
                poly = _box_polygon(b)
                if poly and len(poly) >= 3:
                    flat = []
                    for px, py in poly:
                        flat += [round(float(px), 1), round(float(py), 1)]
                    seg = [flat]
                annotations.append({
                    "id": ann_id, "image_id": img_id, "category_id": cat,
                    "bbox": [round(bx, 1), round(by, 1),
                             round(bw, 1), round(bh, 1)],
                    "area": round(bw * bh, 1), "iscrowd": 0,
                    "segmentation": seg})
                ann_id += 1
        return {"images": images, "annotations": annotations,
                "categories": cats}

    def _write_coco(self, base, records):
        """Write COCO JSON alongside the YOLO export. One file per split when a
        validation split is used, otherwise a single annotations.coco.json."""
        try:
            if self._val_split > 0:
                groups = {
                    "annotations.train.coco.json":
                        [(s, pg) for s, pg, tv in records if not tv],
                    "annotations.val.coco.json":
                        [(s, pg) for s, pg, tv in records if tv],
                }
            else:
                groups = {"annotations.coco.json":
                          [(s, pg) for s, pg, _tv in records]}
            for fname, group in groups.items():
                if not group:
                    continue
                with open(os.path.join(base, fname), "w",
                          encoding="utf-8") as fh:
                    json.dump(self._coco_dict(group), fh, indent=2)
        except OSError:
            pass

    def on_export(self, all_pages):
        pages = self._pages if all_pages else ([self._page()] if self._page() else [])
        # Keep labelled pages; optionally add empty pages as background/negatives
        # (exported with an empty label file — good for reducing false positives).
        pages = [p for p in pages
                 if p and (p["boxes"] or self._export_bg)]
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
            records = []               # (stem, pg, to_val) for optional COCO
            for pg in pages:
                to_val = (self._val_split > 0
                          and self._page_bucket(pg) < self._val_split)
                imgs = images_va if to_val else images_tr
                lbls = labels_va if to_val else labels_tr
                last = self._export_page(pg, imgs, lbls, order, preview)
                records.append((last, pg, to_val))
                time.sleep(0.002)      # keep timestamp stems unique
            self._write_class_files()  # classes.txt + data.yaml for YOLO
            if self._coco_export:
                self._write_coco(base, records)
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
        train = val = bg = 0
        for pg in pages:
            if self._val_split > 0 and self._page_bucket(pg) < self._val_split:
                val += 1
            else:
                train += 1
            if not pg["boxes"]:
                bg += 1
            for b in pg["boxes"]:
                k = b.get("kind", "bubble")
                counts[k] = counts.get(k, 0) + 1
        total = sum(counts.values())
        t = self._tr
        lines = [t("summary_pages").format(n=len(pages), tr=train, va=val), ""]
        if bg:
            lines.append(t("summary_bg").format(n=bg))
            lines.append("")
        lines.append(t("summary_objects"))
        for c in self._classes:
            lines.append("   %s: %d" % (c["label"], counts.get(c["key"], 0)))
        lines += ["", t("summary_total").format(n=total)]
        # Gentle class-imbalance / empty-class heads-up.
        nonzero = [counts[c["key"]] for c in self._classes if counts[c["key"]] > 0]
        empty = [c["label"] for c in self._classes if counts.get(c["key"], 0) == 0]
        warn = []
        if empty:
            warn.append(t("summary_empty_cls").format(cls=", ".join(empty)))
        if len(nonzero) > 1 and max(nonzero) >= 10 * min(nonzero):
            warn.append(t("summary_imbalance"))
        if warn:
            lines += [""] + warn
        lines += ["", "%s" % os.path.abspath(self._folder)]
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
                      # keep any class key (custom classes), not just bubble/sfx
                      "kind": str(b.get("kind") or "bubble"),
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
        dark_titlebar(dlg)
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


def dark_titlebar(win):
    """Paint the native Windows title bar to match the dark theme instead of the
    default white. Uses DWM: immersive dark mode (Win10 1809+) and, on Windows 11,
    the exact caption + text colour. No-op / harmless on other OSes."""
    if os.name != "nt":
        return
    try:
        import ctypes
        hwnd = int(win.winId())                 # forces native handle creation
        dwm = ctypes.windll.dwmapi
        val = ctypes.c_int(1)
        for attr in (20, 19):                   # DWMWA_USE_IMMERSIVE_DARK_MODE
            dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val),
                                      ctypes.sizeof(val))
        # Windows 11 only: exact caption + text colour (COLORREF = 0x00BBGGRR)
        caption = ctypes.c_int(0x003b3631)      # #31363b (theme window bg)
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption),
                                  ctypes.sizeof(caption))
        text = ctypes.c_int(0x00f1f0ef)         # #eff0f1 (theme text)
        dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(text),
                                  ctypes.sizeof(text))
    except Exception:                           # noqa: BLE001 (best-effort only)
        pass


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

    # If a newer build was downloaded last session, apply it now (during the
    # splash) and relaunch — no dialog, one quick restart, Krita-style.
    if _maybe_apply_pending_update():
        return

    win = TrainerWindow()
    win.setWindowIcon(app_icon())
    dark_titlebar(win)                      # dark caption bar (matches the theme)
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
