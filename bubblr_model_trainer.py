# -*- coding: utf-8 -*-
"""BubblR Model Trainer — a small GUI to train (or continue-train) a YOLO model
on a dataset exported by BubblR Trainer.

The heavy lifting is done by Ultralytics (YOLO) running in a *separate* Python
environment that the user points at, so this GUI stays a light PyQt5 app. It
builds the training command, runs it with a QProcess and streams the log; when
training finishes the best weights sit in <project>/<name>/weights/best.pt.
"""

import json
import os
import subprocess
import sys
import tempfile
import time

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox, QPlainTextEdit,
    QFileDialog, QProgressBar, QMessageBox, QGroupBox, QCheckBox, QDialog,
    QDialogButtonBox, QToolButton, QMenu)
from PyQt5.QtGui import QColor, QPalette, QFont, QIcon, QDesktopServices
from PyQt5.QtCore import QProcess, QTimer, QThread, pyqtSignal, QUrl

from bubblr_train_core import (
    read_yaml_summary, build_train_script, train_config, parse_progress,
    strip_ansi, build_predict_script, predict_config, diagnose_error,
    check_dataset, parse_metrics, MODEL_URL, model_path, build_val_script,
    val_config, read_run_metric, PYTHON_DOWNLOAD_URL, best_ai_python,
    find_python_candidates, pip_install_args)


class ModelFetcher(QThread):
    """Download the shared model (bubblr-model.pt) from the BubblR-Model repo."""
    done = pyqtSignal(object)                     # local path, or None

    def run(self):
        dest = model_path()
        try:
            import urllib.request
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            req = urllib.request.Request(MODEL_URL,
                                         headers={"User-Agent": "BubblR-MT"})
            with urllib.request.urlopen(req, timeout=60) as r, \
                    open(dest, "wb") as f:
                f.write(r.read())
            if os.path.getsize(dest) < 1024:      # not a real .pt (error page)
                raise ValueError("no model published yet")
            self.done.emit(dest)
        except Exception:                        # noqa: BLE001
            try:
                if os.path.exists(dest):
                    os.remove(dest)
            except OSError:
                pass
            self.done.emit(None)


class NewsFetcher(QThread):
    """Fetch the project's news.json to see if a newer Model Trainer exists."""
    loaded = pyqtSignal(object)
    URL = ("https://raw.githubusercontent.com/valle3011/"
           "BubblR-Trainer-App/main/news.json")

    def run(self):
        try:
            import urllib.request
            req = urllib.request.Request(self.URL,
                                         headers={"User-Agent": "BubblR-MT"})
            with urllib.request.urlopen(req, timeout=6) as r:
                self.loaded.emit(json.loads(r.read().decode("utf-8")))
        except Exception:                        # noqa: BLE001 (offline etc.)
            self.loaded.emit(None)


def _ver_tuple(v):
    out = []
    for part in str(v or "0").split("."):
        try:
            out.append(int(part))
        except ValueError:
            out.append(0)
    return tuple(out)

VERSION = "0.4.3"
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".bubblr_model_trainer.json")
SHORTCUT_MARK = os.path.join(os.path.expanduser("~"),
                             ".bubblr_model_trainer_shortcut")

# Pretrained bases the user can start from (downloaded by Ultralytics on first
# use). Continue-training instead by choosing "Custom model file…".
DETECT_MODELS = ["yolo11n.pt", "yolo11s.pt", "yolo11m.pt", "yolo11l.pt",
                 "yolo11x.pt", "yolov8n.pt", "yolov8s.pt", "yolov8m.pt",
                 "yolov8l.pt", "yolov8x.pt"]
SEGMENT_MODELS = ["yolo11n-seg.pt", "yolo11s-seg.pt", "yolo11m-seg.pt",
                  "yolo11l-seg.pt", "yolo11x-seg.pt", "yolov8n-seg.pt",
                  "yolov8s-seg.pt", "yolov8m-seg.pt", "yolov8l-seg.pt",
                  "yolov8x-seg.pt"]
CUSTOM_LABEL = "Custom model file… (continue training)"


# --------------------------------------------------------------------------- #
# Main window
# --------------------------------------------------------------------------- #
class TrainerWindow(QMainWindow):
    def __init__(self):
        super(TrainerWindow, self).__init__()
        self.setWindowTitle("BubblR Model Trainer %s" % VERSION)
        self.resize(760, 620)
        self._proc = None
        self._script_path = None
        cfg = self._load()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # -- Python environment (must have ultralytics) --
        env_box = QGroupBox("1 · Python environment (with Ultralytics)")
        eg = QGridLayout(env_box)
        self.py_edit = QLineEdit(cfg.get("python", ""))
        self.py_edit.setPlaceholderText("path to python.exe with 'ultralytics' installed")
        self.find_btn = QPushButton("Find")
        self.find_btn.setToolTip("Auto-detect a Python that already has "
                                 "Ultralytics installed")
        self.find_btn.clicked.connect(self._find_python)
        py_browse = QPushButton("Browse…")
        py_browse.clicked.connect(self._pick_python)
        self.get_py_btn = QPushButton("Get Python")
        self.get_py_btn.setToolTip("Open python.org to download Python "
                                   "(if you don't have it yet)")
        self.get_py_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(PYTHON_DOWNLOAD_URL)))
        self.check_btn = QPushButton("Check")
        self.check_btn.clicked.connect(self._check_env)
        self.install_btn = QPushButton("Install Ultralytics")
        self.install_btn.clicked.connect(self._install_ultra)
        self.env_status = QLabel("—")
        # buttons that follow the field: Find | Browse | Get Python
        py_btns = QWidget()
        pbl = QHBoxLayout(py_btns)
        pbl.setContentsMargins(0, 0, 0, 0)
        pbl.addWidget(self.find_btn)
        pbl.addWidget(py_browse)
        pbl.addWidget(self.get_py_btn)
        eg.addWidget(QLabel("Python:"), 0, 0)
        eg.addWidget(self.py_edit, 0, 1)
        eg.addWidget(py_btns, 0, 2)
        eg.addWidget(self.check_btn, 0, 3)
        eg.addWidget(self.install_btn, 1, 3)
        eg.addWidget(self.env_status, 1, 1, 1, 2)
        root.addWidget(env_box)

        # -- Dataset + model --
        ds_box = QGroupBox("2 · Dataset & model")
        dg = QGridLayout(ds_box)
        self.data_edit = QLineEdit(cfg.get("data", ""))
        self.data_edit.setPlaceholderText("data.yaml exported by BubblR Trainer")
        self.data_edit.textChanged.connect(self._on_data_changed)
        data_browse = QPushButton("Browse…")
        data_browse.clicked.connect(self._pick_data)
        self.recent_btn = QToolButton()
        self.recent_btn.setText("Recent ▾")
        self.recent_btn.setPopupMode(QToolButton.InstantPopup)
        self.recent_menu = QMenu(self.recent_btn)
        self.recent_btn.setMenu(self.recent_menu)
        self._recent = [p for p in cfg.get("recent", []) if isinstance(p, str)]
        browse_cell = QWidget()
        bc = QHBoxLayout(browse_cell)
        bc.setContentsMargins(0, 0, 0, 0)
        bc.addWidget(data_browse)
        bc.addWidget(self.recent_btn)
        self.data_info = QLabel("—")
        self.data_info.setStyleSheet("color:#9aa;")
        self.task_combo = QComboBox()
        self.task_combo.addItems(["detect", "segment"])
        self.task_combo.setCurrentText(cfg.get("task", "detect"))
        self.task_combo.currentTextChanged.connect(self._rebuild_models)
        self.model_combo = QComboBox()
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        self.custom_edit = QLineEdit(cfg.get("custom_model", ""))
        self.custom_edit.setPlaceholderText("existing .pt to continue training")
        self.custom_edit.setVisible(False)
        self.custom_browse = QPushButton("Browse…")
        self.custom_browse.clicked.connect(self._pick_custom)
        self.custom_browse.setVisible(False)
        dg.addWidget(QLabel("data.yaml:"), 0, 0)
        dg.addWidget(self.data_edit, 0, 1, 1, 2)
        dg.addWidget(browse_cell, 0, 3)
        dg.addWidget(self.data_info, 1, 1, 1, 3)
        dg.addWidget(QLabel("Task:"), 2, 0)
        dg.addWidget(self.task_combo, 2, 1)
        self.getmodel_btn = QPushButton("Download latest")
        self.getmodel_btn.setToolTip("Fetch the shared BubblR model and use it "
                                     "as the base (to continue training / test)")
        self.getmodel_btn.clicked.connect(self._download_model)
        dg.addWidget(QLabel("Base model:"), 3, 0)
        dg.addWidget(self.model_combo, 3, 1, 1, 2)
        dg.addWidget(self.getmodel_btn, 3, 3)
        dg.addWidget(self.custom_edit, 4, 1, 1, 2)
        dg.addWidget(self.custom_browse, 4, 3)
        # optional baseline to compare the trained model against
        self.baseline_edit = QLineEdit(cfg.get("baseline", ""))
        self.baseline_edit.setPlaceholderText(
            "optional: a .pt to compare against (e.g. the current model)")
        base_browse = QPushButton("Browse…")
        base_browse.clicked.connect(self._pick_baseline)
        base_dl = QToolButton()
        base_dl.setText("Use downloaded")
        base_dl.setToolTip("Use the downloaded shared model as the baseline")
        base_dl.clicked.connect(
            lambda: self.baseline_edit.setText(model_path())
            if os.path.isfile(model_path()) else
            QMessageBox.information(self, "No model",
                                   "Download the shared model first."))
        base_cell = QWidget()
        bcl = QHBoxLayout(base_cell)
        bcl.setContentsMargins(0, 0, 0, 0)
        bcl.addWidget(base_browse)
        bcl.addWidget(base_dl)
        dg.addWidget(QLabel("Baseline:"), 5, 0)
        dg.addWidget(self.baseline_edit, 5, 1, 1, 2)
        dg.addWidget(base_cell, 5, 3)
        root.addWidget(ds_box)

        # -- Hyper-parameters --
        hp_box = QGroupBox("3 · Training settings")
        hg = QGridLayout(hp_box)
        self.epochs = QSpinBox()
        self.epochs.setRange(1, 10000)
        self.epochs.setValue(int(cfg.get("epochs", 100)))
        self.imgsz = QSpinBox()
        self.imgsz.setRange(64, 4096)
        self.imgsz.setSingleStep(32)
        self.imgsz.setValue(int(cfg.get("imgsz", 640)))
        self.batch = QSpinBox()
        self.batch.setRange(-1, 512)
        self.batch.setValue(int(cfg.get("batch", 16)))
        self.batch.setToolTip("-1 lets Ultralytics auto-pick the batch size")
        self.device = QComboBox()
        self.device.addItems(["auto", "cpu", "0", "1"])
        self.device.setCurrentText(cfg.get("device", "auto"))
        self.run_name = QLineEdit(cfg.get("name", "bubblr_run"))
        self.patience = QSpinBox()
        self.patience.setRange(0, 10000)
        self.patience.setValue(int(cfg.get("patience", 100)))
        self.patience.setToolTip("Stop early if no improvement for N epochs "
                                 "(0 = never stop early)")
        self.resume_box = QCheckBox("Resume interrupted run (from last.pt)")
        self.resume_box.setChecked(False)
        hg.addWidget(QLabel("Epochs:"), 0, 0)
        hg.addWidget(self.epochs, 0, 1)
        hg.addWidget(QLabel("Image size:"), 0, 2)
        hg.addWidget(self.imgsz, 0, 3)
        hg.addWidget(QLabel("Batch:"), 1, 0)
        hg.addWidget(self.batch, 1, 1)
        hg.addWidget(QLabel("Device:"), 1, 2)
        hg.addWidget(self.device, 1, 3)
        hg.addWidget(QLabel("Patience:"), 2, 0)
        hg.addWidget(self.patience, 2, 1)
        hg.addWidget(self.resume_box, 2, 2, 1, 2)
        hg.addWidget(QLabel("Run name:"), 3, 0)
        hg.addWidget(self.run_name, 3, 1, 1, 3)
        root.addWidget(hp_box)

        # -- Advanced (collapsible; off by default) --
        adv_box = QGroupBox("Advanced")
        adv_box.setCheckable(True)
        adv_box.setChecked(bool(cfg.get("advanced_open", False)))
        ag = QGridLayout(adv_box)
        self.workers = QSpinBox()
        self.workers.setRange(0, 32)
        self.workers.setValue(int(cfg.get("workers", 8)))
        self.workers.setToolTip("DataLoader workers. Set 0 if training crashes "
                                "with 'worker exited unexpectedly'.")
        self.cache_box = QCheckBox("Cache images (faster, more RAM)")
        self.cache_box.setChecked(bool(cfg.get("cache", False)))
        self.pretrained_box = QCheckBox("Start from pretrained weights")
        self.pretrained_box.setChecked(bool(cfg.get("pretrained", True)))
        ag.addWidget(QLabel("Workers:"), 0, 0)
        ag.addWidget(self.workers, 0, 1)
        ag.addWidget(self.cache_box, 0, 2)
        ag.addWidget(self.pretrained_box, 1, 2)
        root.addWidget(adv_box)
        self.adv_box = adv_box

        # -- Run controls + log --
        run_row = QHBoxLayout()
        self.start_btn = QPushButton("▶  Start training")
        self.start_btn.clicked.connect(self._start)
        self.stop_btn = QPushButton("■  Stop")
        self.stop_btn.clicked.connect(self._stop)
        self.stop_btn.setEnabled(False)
        self.test_btn = QPushButton("Test on image…")
        self.test_btn.clicked.connect(self._test_model)
        self.results_btn = QPushButton("Open results")
        self.results_btn.clicked.connect(self._open_results)
        self.results_btn.setEnabled(False)
        run_row.addWidget(self.start_btn)
        run_row.addWidget(self.stop_btn)
        run_row.addStretch(1)
        run_row.addWidget(self.test_btn)
        run_row.addWidget(self.results_btn)
        root.addLayout(run_row)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        root.addWidget(self.progress)
        self.stat_lbl = QLabel("")
        self.stat_lbl.setStyleSheet("color:#9aa;")
        root.addWidget(self.stat_lbl)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Consolas", 9))
        self.log.setStyleSheet("background:#1b1e21;color:#cfe;")
        root.addWidget(self.log, 1)

        self._last_run_dir = None
        self._train_log = []               # collected log lines (metrics/errors)
        self._start_time = None
        self._cuda = None                  # set once the env Check reports it
        self._eta_timer = QTimer(self)
        self._eta_timer.setInterval(1000)
        self._eta_timer.timeout.connect(self._tick)
        self._rebuild_models()
        if cfg.get("model") and cfg.get("model") != CUSTOM_LABEL:
            i = self.model_combo.findText(cfg["model"])
            if i >= 0:
                self.model_combo.setCurrentIndex(i)
        self._on_data_changed()
        self._rebuild_recent()
        # background: is a newer Model Trainer available?
        self._news = NewsFetcher(self)
        self._news.loaded.connect(self._on_news)
        self._news.start()

    # -- recent datasets --
    def _rebuild_recent(self):
        self.recent_menu.clear()
        self._recent = [p for p in self._recent if p][:8]
        if not self._recent:
            act = self.recent_menu.addAction("(none yet)")
            act.setEnabled(False)
            return
        for p in self._recent:
            act = self.recent_menu.addAction(p)
            act.triggered.connect(lambda _c=False, path=p: self.data_edit.setText(path))

    def _remember_recent(self, path):
        if not path:
            return
        self._recent = [path] + [p for p in self._recent if p != path]
        self._recent = self._recent[:8]
        self._rebuild_recent()

    # -- update check --
    def _on_news(self, data):
        try:
            latest = (data or {}).get("model_trainer_version")
            if latest and _ver_tuple(latest) > _ver_tuple(VERSION):
                self.env_status.setText(
                    "A newer Model Trainer (v%s) is available — see the project "
                    "Releases." % latest)
        except Exception:                        # noqa: BLE001
            pass

    # -- model list depends on task --
    def _rebuild_models(self):
        task = self.task_combo.currentText()
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(
            SEGMENT_MODELS if task == "segment" else DETECT_MODELS)
        self.model_combo.addItem(CUSTOM_LABEL)
        self.model_combo.blockSignals(False)
        self._on_model_changed()

    def _on_model_changed(self):
        custom = self.model_combo.currentText() == CUSTOM_LABEL
        self.custom_edit.setVisible(custom)
        self.custom_browse.setVisible(custom)

    def _on_data_changed(self):
        path = self.data_edit.text().strip()
        if path and os.path.isfile(path):
            nc, names = read_yaml_summary(path)
            if nc is not None:
                self.data_info.setText(
                    "%d classes: %s" % (nc, ", ".join(names) if names else "—"))
            else:
                self.data_info.setText("could not read nc/names from this file")
        else:
            self.data_info.setText("—")

    # -- file pickers --
    def _pick_python(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select python.exe")
        if path:
            self.py_edit.setText(path)

    def _find_python(self):
        """Scan the machine for a Python that already has Ultralytics, and
        fall back to any Python it can find — so the user doesn't have to hunt
        for python.exe."""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            found, ok = best_ai_python()
        finally:
            QApplication.restoreOverrideCursor()
        if found:
            self.py_edit.setText(found)
            if ok:
                self.env_status.setText("Found a Python with Ultralytics ✓")
                QMessageBox.information(
                    self, "Python found",
                    "Found a Python that already has Ultralytics:\n\n%s" % found)
            else:
                self.env_status.setText("Found Python (no Ultralytics yet)")
                QMessageBox.information(
                    self, "Python found",
                    "Found Python, but it doesn't have Ultralytics yet:\n\n%s"
                    "\n\nClick 'Install Ultralytics' to set it up." % found)
        else:
            QMessageBox.warning(
                self, "No Python found",
                "Couldn't find a Python install automatically.\n\n"
                "Click 'Get Python' to download it from python.org, then use "
                "'Browse…' to select python.exe.")

    def _pick_data(self):
        start = os.path.dirname(self.data_edit.text()) or os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(
            self, "Select data.yaml", start, "YAML (*.yaml *.yml)")
        if path:
            self.data_edit.setText(path)
            self._remember_recent(path)

    def _pick_custom(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select a .pt model", os.path.expanduser("~"),
            "PyTorch weights (*.pt)")
        if path:
            self.custom_edit.setText(path)

    def _pick_baseline(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select a baseline .pt model", os.path.expanduser("~"),
            "PyTorch weights (*.pt)")
        if path:
            self.baseline_edit.setText(path)

    # -- environment check / install --
    def _python(self):
        """A REAL python.exe to run pip/ultralytics with.

        sys.executable is not usable as a fallback: in the PyInstaller build it
        is BubblR-Model-Trainer.exe, so 'Install Ultralytics' would have run
        'BubblR-Model-Trainer.exe -m pip install …' and never install anything.
        Returns '' when the machine has no Python at all — callers must say so
        rather than running nonsense."""
        p = self.py_edit.text().strip()
        if p:
            return p
        if not getattr(sys, "frozen", False):
            return sys.executable                # source mode: we ARE a python
        found, _ok = best_ai_python()
        if not found:
            cands = find_python_candidates()
            found = cands[0] if cands else ""
        if found:
            self.py_edit.setText(found)          # show what we picked
        return found

    def _need_python(self):
        """The Python for pip/ultralytics, or '' after telling the user."""
        py = self._python()
        if not py:
            QMessageBox.warning(
                self, "No Python found",
                "No Python installation was found on this PC.\n\n"
                "Install Python 3 from python.org (tick 'Add Python to PATH'), "
                "then press Find.")
        return py

    def _check_env(self):
        py = self._need_python()
        if not py:
            return
        # Pillow matters too: page ranking imports it, so an env without it
        # fails later with a message that points nowhere.
        self._run_side([py, "-c",
                        "import ultralytics,torch,PIL;"
                        "print('ultralytics',ultralytics.__version__);"
                        "print('torch',torch.__version__);"
                        "print('pillow',PIL.__version__);"
                        "print('cuda',torch.cuda.is_available())"],
                       "Checking environment…")

    def _install_ultra(self):
        py = self._need_python()
        if not py:
            return
        if QMessageBox.question(
                self, "Install Ultralytics",
                "Run 'pip install ultralytics' in:\n%s\n\nThis downloads "
                "PyTorch and can take a while. Continue?" % py,
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        self._run_side(pip_install_args(py),
                       "Installing Ultralytics (this can take several minutes)…")

    def _run_side(self, args, note):
        """Run a short side command (check/install) streaming into the log."""
        if self._proc is not None:
            QMessageBox.information(self, "Busy", "A process is already running.")
            return
        self.env_status.setText(note)
        self._append("\n$ " + " ".join(args) + "\n")
        self._start_process(args, side=True)

    # -- training --
    def _resolve_model(self):
        if self.model_combo.currentText() == CUSTOM_LABEL:
            return self.custom_edit.text().strip()
        return self.model_combo.currentText()

    def _start(self):
        if self._proc is not None:
            return
        data = self.data_edit.text().strip()
        model = self._resolve_model()
        if not data or not os.path.isfile(data):
            QMessageBox.warning(self, "No dataset", "Pick a valid data.yaml first.")
            return
        if not model:
            QMessageBox.warning(self, "No model", "Pick a base model or a .pt file.")
            return
        # pre-flight dataset check
        ok, msgs = check_dataset(data)
        if not ok:
            QMessageBox.warning(self, "Dataset problem", "\n".join(msgs))
            return
        if any(m.startswith("⚠") for m in msgs):
            if QMessageBox.question(
                    self, "Dataset check", "\n".join(msgs) + "\n\nStart anyway?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes) != QMessageBox.Yes:
                return
        project = os.path.join(os.path.dirname(os.path.abspath(data)), "runs")
        name = self.run_name.text().strip() or "bubblr_run"
        dev = self.device.currentText()
        resume = self.resume_box.isChecked()
        if resume:                             # continue from the run's last.pt
            last = os.path.join(project, name, "weights", "last.pt")
            if not os.path.isfile(last):
                QMessageBox.warning(self, "Resume", "No last.pt found for run "
                                    "'%s' — uncheck Resume to start fresh." % name)
                return
            model = last
        workers = self.workers.value() if self.adv_box.isChecked() else None
        cfg = train_config(
            model, data, self.epochs.value(), self.imgsz.value(),
            self.batch.value(), "" if dev == "auto" else dev, project, name,
            patience=self.patience.value(), workers=workers,
            cache=self.cache_box.isChecked() if self.adv_box.isChecked() else False,
            pretrained=self.pretrained_box.isChecked(), resume=resume)
        self._last_run_dir = os.path.join(project, name)
        self._remember_recent(data)
        d = tempfile.mkdtemp(prefix="bubblr_train_")
        self._script_path = os.path.join(d, "train.py")
        cfg_path = os.path.join(d, "cfg.json")
        with open(self._script_path, "w", encoding="utf-8") as f:
            f.write(build_train_script(cfg))
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        self._save()
        self.progress.setValue(0)
        self.log.clear()
        self._train_log = []
        self._start_time = time.time()
        self._eta_timer.start()
        for m in msgs:
            self._append(m + "\n")
        self._append("Training %s on %s\n" % (model, data))
        py = self._need_python()
        if not py:
            return
        self._start_process([py, "-u", self._script_path, cfg_path],
                            side=False)

    def _start_process(self, args, side):
        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.MergedChannels)
        self._proc.readyReadStandardOutput.connect(self._on_output)
        self._proc.finished.connect(lambda code, _s: self._on_finished(code, side))
        self._proc.errorOccurred.connect(self._on_proc_error)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(not side)
        self.check_btn.setEnabled(False)
        self.install_btn.setEnabled(False)
        self._proc.start(args[0], args[1:])

    def _stop(self):
        if self._proc is not None:
            self._append("\n[stopping…]\n")
            self._proc.kill()

    def _on_output(self):
        if self._proc is None:
            return
        data = bytes(self._proc.readAllStandardOutput()).decode(
            "utf-8", "replace")
        for line in data.splitlines():
            clean = strip_ansi(line)
            self._train_log.append(clean)
            if "cuda True" in clean:
                self._cuda = True
                if self.device.currentText() in ("auto", "cpu"):
                    self.device.setCurrentText("0")
            elif "cuda False" in clean:
                self._cuda = False
                self.device.setCurrentText("cpu")
            pr = parse_progress(line)
            if pr:
                self.progress.setMaximum(pr[1])
                self.progress.setValue(pr[0])
            self._append(clean + "\n")

    def _on_proc_error(self, _err):
        self._append("\n[could not start the process — check the Python path]\n")

    def _on_finished(self, code, side):
        self._proc = None
        self._eta_timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.check_btn.setEnabled(True)
        self.install_btn.setEnabled(True)
        if side:
            self.env_status.setText("done (exit %d)" % code)
            return
        log = "\n".join(self._train_log)
        if code == 0:
            self.progress.setValue(self.progress.maximum())
            self.results_btn.setEnabled(bool(self._last_run_dir))
            best = os.path.join(self._last_run_dir or "", "weights", "best.pt")
            metrics = parse_metrics(log)
            mtxt = ""
            if metrics:
                mtxt = ("\n\nmAP50: %.3f   mAP50-95: %.3f   P: %.3f   R: %.3f"
                        % (metrics["mAP50"], metrics["mAP50_95"],
                           metrics["P"], metrics["R"]))
            elapsed = self._fmt(time.time() - (self._start_time or time.time()))
            self.stat_lbl.setText("Done in %s.%s" % (
                elapsed, mtxt.replace("\n", "  ")))
            self._append("\n✅ Training finished in %s. Best weights:\n%s%s\n"
                         % (elapsed, best, mtxt))
            box = QMessageBox(self)
            box.setWindowTitle("Done")
            box.setIcon(QMessageBox.Information)
            box.setText("Training finished in %s.\n\nBest weights:\n%s%s"
                        % (elapsed, best, mtxt))
            plot = os.path.join(self._last_run_dir or "", "results.png")
            if os.path.isfile(plot):
                box.addButton("Show plots", QMessageBox.ActionRole)
            box.addButton(QMessageBox.Ok)
            box.exec_()
            clicked = box.clickedButton()      # "Show plots" opens results.png
            if clicked and box.buttonRole(clicked) == QMessageBox.ActionRole:
                self._open_path(plot)
            # optional: score a baseline on the same data and compare
            base = self.baseline_edit.text().strip()
            new_score = read_run_metric(self._last_run_dir or "")
            if base and os.path.isfile(base) and new_score is not None:
                self._compare_baseline(base, new_score)
        else:
            hint = diagnose_error(log)
            self.stat_lbl.setText("Failed (exit %d)." % code)
            self._append("\n❌ Training exited with code %d.\n" % code)
            if hint:
                self._append("Hint: %s\n" % hint)
                QMessageBox.warning(self, "Training failed", hint)

    def _tick(self):
        """Update the elapsed / ETA line once a second while training."""
        if not self._start_time:
            return
        elapsed = time.time() - self._start_time
        cur, total = self.progress.value(), self.progress.maximum()
        eta = ""
        if cur > 0 and total > 0 and cur < total:
            per = elapsed / cur
            eta = "   ETA ~%s" % self._fmt(per * (total - cur))
        self.stat_lbl.setText("Epoch %d/%d   elapsed %s%s"
                              % (cur, total, self._fmt(elapsed), eta))

    @staticmethod
    def _fmt(secs):
        secs = int(secs)
        h, r = divmod(secs, 3600)
        m, s = divmod(r, 60)
        return ("%dh %02dm" % (h, m)) if h else ("%dm %02ds" % (m, s))

    # -- download the shared model from the BubblR-Model repo --
    def _download_model(self):
        self.getmodel_btn.setEnabled(False)
        self.getmodel_btn.setText("Downloading…")
        self._model_thread = ModelFetcher(self)
        self._model_thread.done.connect(self._on_model_downloaded)
        self._model_thread.start()

    def _on_model_downloaded(self, path):
        self._model_thread = None
        self.getmodel_btn.setEnabled(True)
        self.getmodel_btn.setText("Download latest")
        if not path:
            QMessageBox.information(
                self, "No model yet",
                "Couldn't download a model — none has been published to the "
                "BubblR-Model repo yet, or you're offline.")
            return
        # select it as the custom base model, ready to use / continue-train
        i = self.model_combo.findText(CUSTOM_LABEL)
        if i >= 0:
            self.model_combo.setCurrentIndex(i)
        self.custom_edit.setText(path)
        self._append("\nDownloaded shared model:\n%s\n" % path)
        QMessageBox.information(self, "Model ready",
                                "Latest model downloaded and selected as the "
                                "base model:\n%s" % path)

    # -- test a trained model on an image --
    def _test_model(self):
        if self._proc is not None:
            QMessageBox.information(self, "Busy", "A process is already running.")
            return
        best = os.path.join(self._last_run_dir or "", "weights", "best.pt")
        model = best if os.path.isfile(best) else self._resolve_model()
        if not model:
            QMessageBox.warning(self, "No model", "Train first, or pick a model "
                                "(base / Custom model file).")
            return
        img, _ = QFileDialog.getOpenFileName(
            self, "Pick an image to test on", os.path.expanduser("~"),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not img:
            return
        py = self._need_python()
        if not py:
            return
        outdir = os.path.join(tempfile.gettempdir(), "bubblr_predict")
        cfg = predict_config(model, img, outdir, "test", self.imgsz.value())
        d = tempfile.mkdtemp(prefix="bubblr_pred_")
        sp = os.path.join(d, "predict.py")
        cp = os.path.join(d, "cfg.json")
        open(sp, "w", encoding="utf-8").write(build_predict_script(cfg))
        json.dump(cfg, open(cp, "w"))
        self._predict_dir = os.path.join(outdir, "test")
        self._predict_stem = os.path.splitext(os.path.basename(img))[0]
        self.log.clear()
        self._train_log = []
        self._append("Testing %s on %s …\n" % (os.path.basename(model), img))
        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.MergedChannels)
        self._proc.readyReadStandardOutput.connect(self._on_output)
        self._proc.finished.connect(lambda code, _s: self._on_predict_done(code))
        self._proc.errorOccurred.connect(self._on_proc_error)
        self.start_btn.setEnabled(False)
        self.test_btn.setEnabled(False)
        self._proc.start(py, ["-u", sp, cp])

    def _on_predict_done(self, code):
        self._proc = None
        self.start_btn.setEnabled(True)
        self.test_btn.setEnabled(True)
        if code != 0:
            hint = diagnose_error("\n".join(self._train_log))
            self._append("\n❌ Prediction failed (exit %d).\n" % code)
            if hint:
                QMessageBox.warning(self, "Prediction failed", hint)
            return
        # find the annotated image: Ultralytics saves it (as .jpg) in save_dir,
        # reported on the BUBBLR_PREDICT line; fall back to our expected folder.
        save_dir = self._predict_dir
        for line in self._train_log:
            if line.startswith("BUBBLR_PREDICT"):
                d = line.split(" ", 1)[1].strip()
                if d:
                    save_dir = d
        found = ""
        if os.path.isdir(save_dir):
            for f in os.listdir(save_dir):
                stem, ext = os.path.splitext(f)
                if stem == self._predict_stem and ext.lower() in (
                        ".jpg", ".jpeg", ".png", ".webp", ".bmp"):
                    found = os.path.join(save_dir, f)
                    break
        if found:
            self._append("\n✅ Result saved:\n%s\n" % found)
            self._open_path(found)
        else:
            self._append("\n✅ Prediction done — see:\n%s\n" % save_dir)
            self._open_path(save_dir)

    # -- baseline comparison (validate a baseline model, compare mAP) ----------
    def _compare_baseline(self, baseline, new_score):
        data = self.data_edit.text().strip()
        if not (data and os.path.isfile(data)):
            return
        dev = self.device.currentText()
        cfg = val_config(baseline, data, self.imgsz.value(),
                         "" if dev == "auto" else dev)
        py = self._need_python()
        if not py:
            return
        d = tempfile.mkdtemp(prefix="bubblr_val_")
        sp = os.path.join(d, "val.py")
        cp = os.path.join(d, "cfg.json")
        open(sp, "w", encoding="utf-8").write(build_val_script(cfg))
        json.dump(cfg, open(cp, "w"))
        self._new_score = new_score
        self._val_out = None
        self._append("\nScoring baseline %s on the same data…\n"
                     % os.path.basename(baseline))
        self.start_btn.setEnabled(False)
        self.test_btn.setEnabled(False)
        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.MergedChannels)
        self._proc.readyReadStandardOutput.connect(self._val_output)
        self._proc.finished.connect(lambda code, _s: self._on_baseline_done(code))
        self._proc.errorOccurred.connect(self._on_proc_error)
        self._proc.start(py, ["-u", sp, cp])

    def _val_output(self):
        data = bytes(self._proc.readAllStandardOutput()).decode("utf-8", "replace")
        for line in data.splitlines():
            clean = strip_ansi(line)
            self._append(clean + "\n")
            if clean.startswith("BUBBLR_VAL"):
                try:
                    self._val_out = float(clean.split()[1])
                except (ValueError, IndexError):
                    self._val_out = None

    def _on_baseline_done(self, code):
        self._proc = None
        self.start_btn.setEnabled(True)
        self.test_btn.setEnabled(True)
        new = getattr(self, "_new_score", None)
        base = getattr(self, "_val_out", None)
        if code != 0 or base is None or new is None:
            self._append("\nBaseline comparison unavailable.\n")
            return
        diff = new - base
        verdict = "BETTER" if diff > 0 else ("worse" if diff < 0 else "equal")
        msg = ("New model mAP50-95: %.4f\nBaseline mAP50-95: %.4f\n"
               "Difference: %+.4f  →  the new model is %s."
               % (new, base, diff, verdict))
        self._append("\n%s\n" % msg)
        self.stat_lbl.setText("New %.4f vs baseline %.4f (%+.4f) — %s"
                              % (new, base, diff, verdict))
        QMessageBox.information(self, "Baseline comparison", msg)

    def _open_path(self, path):
        if path and os.path.exists(path) and sys.platform.startswith("win"):
            try:
                os.startfile(path)             # noqa: S606 (user-invoked)
            except OSError:
                pass

    def _open_results(self):
        d = self._last_run_dir
        if d and os.path.isdir(d):
            if sys.platform.startswith("win"):
                os.startfile(d)               # noqa: S606 (user asked to open)
            else:
                self._append("\nResults: %s\n" % d)

    def _append(self, text):
        self.log.moveCursor(self.log.textCursor().End)
        self.log.insertPlainText(text)
        self.log.moveCursor(self.log.textCursor().End)

    # -- settings --
    def _load(self):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:                        # noqa: BLE001
            return {}

    def _save(self):
        data = {"python": self.py_edit.text().strip(),
                "data": self.data_edit.text().strip(),
                "task": self.task_combo.currentText(),
                "model": self.model_combo.currentText(),
                "custom_model": self.custom_edit.text().strip(),
                "epochs": self.epochs.value(), "imgsz": self.imgsz.value(),
                "batch": self.batch.value(),
                "device": self.device.currentText(),
                "name": self.run_name.text().strip(),
                "patience": self.patience.value(),
                "workers": self.workers.value(),
                "cache": self.cache_box.isChecked(),
                "pretrained": self.pretrained_box.isChecked(),
                "advanced_open": self.adv_box.isChecked(),
                "baseline": self.baseline_edit.text().strip(),
                "recent": self._recent[:8]}
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
        except OSError:
            pass

    # -- desktop / start-menu shortcuts (Windows) --
    def maybe_prompt_shortcut(self):
        """On the first launch (Windows only), offer to create shortcuts. A
        marker file keeps it from asking again."""
        if os.name != "nt" or os.path.exists(SHORTCUT_MARK):
            return
        try:
            dlg = QDialog(self)
            dlg.setWindowTitle("BubblR Model Trainer")
            dlg.setWindowIcon(app_icon())
            lay = QVBoxLayout(dlg)
            lay.addWidget(QLabel("Create shortcuts for BubblR Model Trainer?"))
            cb_desktop = QCheckBox("On the Desktop")
            cb_desktop.setChecked(True)
            cb_start = QCheckBox("In the Start menu")
            cb_start.setChecked(True)
            lay.addWidget(cb_desktop)
            lay.addWidget(cb_start)
            bb = QDialogButtonBox()
            bb.addButton("Create", QDialogButtonBox.AcceptRole)
            bb.addButton("Skip", QDialogButtonBox.RejectRole)
            bb.accepted.connect(dlg.accept)
            bb.rejected.connect(dlg.reject)
            lay.addWidget(bb)
            if dlg.exec_() == QDialog.Accepted:
                self.create_shortcuts(cb_desktop.isChecked(),
                                      cb_start.isChecked())
        finally:
            try:
                with open(SHORTCUT_MARK, "w", encoding="utf-8") as fh:
                    fh.write("1")
            except OSError:
                pass

    def create_shortcuts(self, desktop, startmenu):
        if not (desktop or startmenu):
            return
        cmd = _shortcut_command(desktop, startmenu)
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-Command", cmd], creationflags=flags, timeout=30)
            self._append("\nShortcuts created.\n")
        except Exception as exc:                 # noqa: BLE001
            self._append("\nShortcut error: %s\n" % exc)

    def closeEvent(self, event):
        self._save()
        if self._proc is not None:
            self._proc.kill()
        super(TrainerWindow, self).closeEvent(event)


def apply_dark(app):
    app.setStyle("Fusion")
    C = QColor
    win, base, text = C(0x31, 0x36, 0x3b), C(0x23, 0x26, 0x29), C(0xef, 0xf0, 0xf1)
    accent = C(0x3d, 0xae, 0xe9)
    p = QPalette()
    p.setColor(QPalette.Window, win)
    p.setColor(QPalette.WindowText, text)
    p.setColor(QPalette.Base, base)
    p.setColor(QPalette.AlternateBase, win)
    p.setColor(QPalette.Text, text)
    p.setColor(QPalette.Button, C(0x3a, 0x40, 0x45))
    p.setColor(QPalette.ButtonText, text)
    p.setColor(QPalette.Highlight, accent)
    p.setColor(QPalette.HighlightedText, base)
    p.setColor(QPalette.ToolTipBase, win)
    p.setColor(QPalette.ToolTipText, text)
    app.setPalette(p)
    app.setStyleSheet(
        "QGroupBox{border:1px solid #4d4d4d;border-radius:4px;margin-top:8px;"
        "padding-top:8px;}"
        "QGroupBox::title{subcontrol-origin:margin;left:8px;padding:0 4px;"
        "color:#3daee9;}"
        "QPushButton{padding:5px 9px;border:1px solid #4d4d4d;border-radius:3px;"
        "background:#3a4045;}"
        "QPushButton:hover{background:#454b50;}"
        "QPushButton:disabled{color:#7f8c8d;background:#33383c;}"
        "QLineEdit,QComboBox,QSpinBox{padding:3px 6px;border:1px solid #4d4d4d;"
        "border-radius:3px;background:#232629;color:#eff0f1;}")


def _resource(*parts):
    """Path to a bundled resource, both as a .py and as a PyInstaller exe."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def app_icon():
    for name in ("model_icon.ico", "model_icon.png", "icon.ico", "icon.png"):
        p = _resource("assets", name)
        if os.path.exists(p):
            return QIcon(p)
    return QIcon()


def _pythonw():
    d = os.path.dirname(sys.executable)
    for name in ("pythonw.exe", "python.exe"):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return sys.executable


def _ps_quote(s):
    return "'" + str(s).replace("'", "''") + "'"


def _shortcut_command(desktop, startmenu):
    """PowerShell that creates the chosen 'BubblR Model Trainer' shortcut(s):
    the frozen exe directly, else the Python app via pythonw (no console)."""
    if getattr(sys, "frozen", False):
        target, args, workdir = sys.executable, "", os.path.dirname(sys.executable)
    else:
        script = os.path.abspath(__file__)
        target, args, workdir = _pythonw(), '"%s"' % script, os.path.dirname(script)
    icon = _resource("assets", "model_icon.ico")
    folders = []
    if desktop:
        folders.append("[Environment]::GetFolderPath('Desktop')")
    if startmenu:
        folders.append("[Environment]::GetFolderPath('Programs')")
    lines = ["$w = New-Object -ComObject WScript.Shell"]
    for folder in folders:
        lines += [
            "$l = Join-Path (%s) 'BubblR Model Trainer.lnk'" % folder,
            "$s = $w.CreateShortcut($l)",
            "$s.TargetPath = %s" % _ps_quote(target),
            "$s.Arguments = %s" % _ps_quote(args),
            "$s.WorkingDirectory = %s" % _ps_quote(workdir),
        ]
        if os.path.exists(icon):
            lines.append("$s.IconLocation = %s" % _ps_quote(icon + ",0"))
        lines += ["$s.Description = 'BubblR Model Trainer'", "$s.Save()"]
    return "; ".join(lines)


def dark_titlebar(win):
    """Dark native Windows title bar to match the theme (see BubblR Trainer)."""
    if os.name != "nt":
        return
    try:
        import ctypes
        hwnd = int(win.winId())
        dwm = ctypes.windll.dwmapi
        val = ctypes.c_int(1)
        for attr in (20, 19):                   # DWMWA_USE_IMMERSIVE_DARK_MODE
            dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val),
                                      ctypes.sizeof(val))
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(ctypes.c_int(0x003b3631)), 4)
        dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(ctypes.c_int(0x00f1f0ef)), 4)
    except Exception:                           # noqa: BLE001
        pass


def main():
    app = QApplication(sys.argv)
    apply_dark(app)
    app.setWindowIcon(app_icon())
    win = TrainerWindow()
    win.setWindowIcon(app_icon())
    dark_titlebar(win)
    win.show()
    win.maybe_prompt_shortcut()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
