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

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox, QPlainTextEdit,
    QFileDialog, QProgressBar, QMessageBox, QGroupBox, QCheckBox, QDialog,
    QDialogButtonBox)
from PyQt5.QtGui import QColor, QPalette, QFont, QIcon
from PyQt5.QtCore import QProcess

from bubblr_train_core import (
    read_yaml_summary, build_train_script, train_config, parse_progress,
    strip_ansi)

VERSION = "0.1.0"
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
        py_browse = QPushButton("Browse…")
        py_browse.clicked.connect(self._pick_python)
        self.check_btn = QPushButton("Check")
        self.check_btn.clicked.connect(self._check_env)
        self.install_btn = QPushButton("Install Ultralytics")
        self.install_btn.clicked.connect(self._install_ultra)
        self.env_status = QLabel("—")
        eg.addWidget(QLabel("Python:"), 0, 0)
        eg.addWidget(self.py_edit, 0, 1)
        eg.addWidget(py_browse, 0, 2)
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
        dg.addWidget(data_browse, 0, 3)
        dg.addWidget(self.data_info, 1, 1, 1, 3)
        dg.addWidget(QLabel("Task:"), 2, 0)
        dg.addWidget(self.task_combo, 2, 1)
        dg.addWidget(QLabel("Base model:"), 3, 0)
        dg.addWidget(self.model_combo, 3, 1, 1, 2)
        dg.addWidget(self.custom_edit, 4, 1, 1, 2)
        dg.addWidget(self.custom_browse, 4, 3)
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
        hg.addWidget(QLabel("Epochs:"), 0, 0)
        hg.addWidget(self.epochs, 0, 1)
        hg.addWidget(QLabel("Image size:"), 0, 2)
        hg.addWidget(self.imgsz, 0, 3)
        hg.addWidget(QLabel("Batch:"), 1, 0)
        hg.addWidget(self.batch, 1, 1)
        hg.addWidget(QLabel("Device:"), 1, 2)
        hg.addWidget(self.device, 1, 3)
        hg.addWidget(QLabel("Run name:"), 2, 0)
        hg.addWidget(self.run_name, 2, 1, 1, 3)
        root.addWidget(hp_box)

        # -- Run controls + log --
        run_row = QHBoxLayout()
        self.start_btn = QPushButton("▶  Start training")
        self.start_btn.clicked.connect(self._start)
        self.stop_btn = QPushButton("■  Stop")
        self.stop_btn.clicked.connect(self._stop)
        self.stop_btn.setEnabled(False)
        self.results_btn = QPushButton("Open results")
        self.results_btn.clicked.connect(self._open_results)
        self.results_btn.setEnabled(False)
        run_row.addWidget(self.start_btn)
        run_row.addWidget(self.stop_btn)
        run_row.addStretch(1)
        run_row.addWidget(self.results_btn)
        root.addLayout(run_row)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        root.addWidget(self.progress)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Consolas", 9))
        self.log.setStyleSheet("background:#1b1e21;color:#cfe;")
        root.addWidget(self.log, 1)

        self._last_run_dir = None
        self._rebuild_models()
        if cfg.get("model") and cfg.get("model") != CUSTOM_LABEL:
            i = self.model_combo.findText(cfg["model"])
            if i >= 0:
                self.model_combo.setCurrentIndex(i)
        self._on_data_changed()

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

    def _pick_data(self):
        start = os.path.dirname(self.data_edit.text()) or os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(
            self, "Select data.yaml", start, "YAML (*.yaml *.yml)")
        if path:
            self.data_edit.setText(path)

    def _pick_custom(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select a .pt model", os.path.expanduser("~"),
            "PyTorch weights (*.pt)")
        if path:
            self.custom_edit.setText(path)

    # -- environment check / install --
    def _python(self):
        return self.py_edit.text().strip() or sys.executable

    def _check_env(self):
        self._run_side([self._python(), "-c",
                        "import ultralytics,torch;"
                        "print('ultralytics',ultralytics.__version__);"
                        "print('torch',torch.__version__);"
                        "print('cuda',torch.cuda.is_available())"],
                       "Checking environment…")

    def _install_ultra(self):
        if QMessageBox.question(
                self, "Install Ultralytics",
                "Run 'pip install ultralytics' in:\n%s\n\nThis downloads "
                "PyTorch and can take a while. Continue?" % self._python(),
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        self._run_side([self._python(), "-m", "pip", "install", "ultralytics"],
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
        project = os.path.join(os.path.dirname(os.path.abspath(data)), "runs")
        name = self.run_name.text().strip() or "bubblr_run"
        dev = self.device.currentText()
        cfg = train_config(
            model, data, self.epochs.value(), self.imgsz.value(),
            self.batch.value(), "" if dev == "auto" else dev, project, name)
        self._last_run_dir = os.path.join(project, name)
        # write the training script + its config to temp
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
        self._append("Training %s on %s\n" % (model, data))
        self._start_process([self._python(), "-u", self._script_path, cfg_path],
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
            pr = parse_progress(line)
            if pr:
                self.progress.setMaximum(pr[1])
                self.progress.setValue(pr[0])
            self._append(strip_ansi(line) + "\n")

    def _on_proc_error(self, _err):
        self._append("\n[could not start the process — check the Python path]\n")

    def _on_finished(self, code, side):
        self._proc = None
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.check_btn.setEnabled(True)
        self.install_btn.setEnabled(True)
        if side:
            self.env_status.setText("done (exit %d)" % code)
            return
        if code == 0:
            self.progress.setValue(self.progress.maximum())
            self.results_btn.setEnabled(bool(self._last_run_dir))
            best = os.path.join(self._last_run_dir or "", "weights", "best.pt")
            self._append("\n✅ Training finished. Best weights:\n%s\n" % best)
            QMessageBox.information(
                self, "Done", "Training finished.\n\nBest weights:\n%s" % best)
        else:
            self._append("\n❌ Training exited with code %d.\n" % code)

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
                "name": self.run_name.text().strip()}
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
    for name in ("icon.ico", "icon.png"):
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
    icon = _resource("assets", "icon.ico")
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
