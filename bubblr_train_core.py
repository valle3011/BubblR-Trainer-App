# -*- coding: utf-8 -*-
"""Pure (GUI-free) training helpers for BubblR Model Trainer.

Kept separate from the PyQt5 app so the exact command/script the GUI runs can be
unit-tested and reused without importing Qt."""

import glob
import json
import os
import re
import subprocess

# --- shared model distribution (the BubblR-Model repo) ---
MODEL_URL = ("https://github.com/valle3011/BubblR-Model/releases/"
             "latest/download/bubblr-model.pt")
MODEL_META_URL = ("https://raw.githubusercontent.com/valle3011/"
                  "BubblR-Model/main/model.json")

# Where a normal user gets Python (the "Get Python" button opens this).
PYTHON_DOWNLOAD_URL = "https://www.python.org/downloads/"
# PyTorch needs the VC++ runtime; on a fresh Windows it is often missing and
# torch then dies with a "DLL load failed" that says nothing to the user.
VCREDIST_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"


def _no_window():
    """subprocess flag so probing Python never flashes a console (Windows)."""
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def is_store_stub(py):
    """True for the Microsoft-Store 'python.exe' app-execution alias. It is a
    0-byte-ish stub that just opens the Store, so running it never produces a
    working interpreter — it must never be picked as the AI Python."""
    p = os.path.normpath(py or "").lower()
    if "windowsapps" not in p:
        return False
    try:
        # the real Store Python lives in WindowsApps too, but the alias stub is
        # a reparse point of ~0 bytes; a genuine interpreter is far bigger
        return os.path.getsize(py) < 1024
    except OSError:
        return True


def find_python_candidates():
    """Every python.exe we can find on this machine: PATH, the py launcher, the
    usual install dirs, and the BubblR AI venv. De-duplicated, existing only.
    The Microsoft-Store alias stub is skipped (it only opens the Store)."""
    import shutil
    out, seen = [], set()

    def add(p):
        if not p:
            return
        p = os.path.normpath(p)
        key = p.lower()
        if key in seen or not os.path.isfile(p) or is_store_stub(p):
            return
        seen.add(key)
        out.append(p)

    for name in ("python.exe", "python3.exe", "python", "python3"):
        add(shutil.which(name))
    # Windows py launcher lists every installed interpreter
    if os.name == "nt":
        try:
            r = subprocess.run(["py", "-0p"], capture_output=True, text=True,
                               timeout=8, creationflags=_no_window())
            for line in (r.stdout or "").splitlines():
                for tok in line.replace("*", " ").split():
                    if tok.lower().endswith("python.exe"):
                        add(tok)
        except Exception:                        # noqa: BLE001
            pass
        home = os.path.expanduser("~")
        roots = [os.path.join(home, "AppData", "Local", "Programs", "Python"),
                 r"C:\Program Files", r"C:\Program Files (x86)", r"C:\\"]
        for root in roots:
            for pat in ("Python3*", "Python 3*"):
                for d in glob.glob(os.path.join(root, pat)):
                    add(os.path.join(d, "python.exe"))
        # the BubblR AI venv, if it sits in the usual sibling spot
        base = os.path.dirname(os.path.abspath(__file__))
        add(os.path.join(base, "..", "BubblR-Test", "ai", ".venv",
                         "Scripts", "python.exe"))
    else:
        for d in ("/usr/bin", "/usr/local/bin"):
            for pat in ("python3", "python3.*"):
                for p in glob.glob(os.path.join(d, pat)):
                    add(p)
    return out


# Probe script: importing ultralytics alone is not enough. Detection needs torch
# (which fails to import without the VC++ redistributable) and ranking needs
# Pillow, so an env that passes 'import ultralytics' can still crash the run.
_PROBE = (
    "import json\n"
    "out = {'ok': True, 'errors': [], 'versions': {}, 'cuda': False}\n"
    "for mod in ('ultralytics', 'torch', 'PIL'):\n"
    "    try:\n"
    "        m = __import__(mod)\n"
    "        out['versions'][mod] = getattr(m, '__version__', '?')\n"
    "    except Exception as e:\n"
    "        out['ok'] = False\n"
    "        out['errors'].append('%s: %s' % (mod, e))\n"
    "try:\n"
    "    import torch\n"
    "    out['cuda'] = bool(torch.cuda.is_available())\n"
    "except Exception:\n"
    "    pass\n"
    "print('BUBBLR_PROBE', json.dumps(out))\n")


def probe_ai_python(py):
    """Really check a python.exe for the AI: it must import ultralytics, torch
    AND Pillow. Returns (ok, report) where report is
    {'python', 'versions': {...}, 'cuda': bool, 'errors': [str]} — 'errors' says
    exactly what is broken, so the UI can tell the user instead of failing with
    a generic message."""
    rep = {"python": py or "", "versions": {}, "cuda": False, "errors": []}
    if not py or not os.path.isfile(py):
        rep["errors"].append("python not found: %s" % (py or "(empty)"))
        return False, rep
    if is_store_stub(py):
        rep["errors"].append(
            "This is the Microsoft-Store placeholder, not a real Python. "
            "Install Python from python.org.")
        return False, rep
    try:
        r = subprocess.run([py, "-c", _PROBE], capture_output=True, text=True,
                           timeout=90, creationflags=_no_window())
    except Exception as e:                       # noqa: BLE001
        rep["errors"].append("could not run this Python: %s" % e)
        return False, rep
    for line in (r.stdout or "").splitlines():
        if line.startswith("BUBBLR_PROBE"):
            try:
                data = json.loads(line.split(" ", 1)[1])
            except ValueError:
                continue
            rep["versions"] = data.get("versions", {})
            rep["cuda"] = bool(data.get("cuda"))
            rep["errors"] = data.get("errors", [])
            return bool(data.get("ok")), rep
    # no probe line at all: the interpreter itself failed (bad exe, DLL error…)
    err = (r.stderr or r.stdout or "").strip()
    rep["errors"].append(err.splitlines()[-1] if err else
                         "this Python produced no output")
    return False, rep


def python_has_ultralytics(py):
    """True if this python.exe is actually usable for the AI (ultralytics, torch
    and Pillow all import). Kept for callers that only need a yes/no."""
    ok, _rep = probe_ai_python(py)
    return ok


def best_ai_python(candidates=None):
    """Pick the best python for the AI: one that can really run it if possible.
    Returns (python_path_or_"", usable_bool)."""
    cands = candidates if candidates is not None else find_python_candidates()
    for p in cands:
        if python_has_ultralytics(p):
            return p, True
    return (cands[0] if cands else ""), False


def is_venv(py):
    """True if this python.exe belongs to a virtual environment."""
    if not py:
        return False
    return os.path.isfile(os.path.join(os.path.dirname(py), "..",
                                       "pyvenv.cfg"))


def pip_install_args(py, package="ultralytics"):
    """The command that installs `package` into this Python.

    A Python installed for all users (Program Files) can't be written to without
    admin rights, so fall back to the user's own site-packages. Inside a venv
    --user is rejected, so it is only added outside one."""
    args = [py, "-m", "pip", "install", package]
    if not is_venv(py) and not os.access(os.path.dirname(py), os.W_OK):
        args.insert(4, "--user")
    return args


def model_path():
    """Local path where the downloaded shared model is kept."""
    d = os.path.join(os.path.expanduser("~"), ".bubblr_ai")
    return os.path.join(d, "bubblr-model.pt")


def is_valid_model(path):
    """True if the file really looks like a Torch checkpoint. A .pt is a zip
    archive, so it starts with 'PK\\x03\\x04'. Guards against a half-finished
    download or an HTML error page saved under a .pt name — which would
    otherwise surface as an unexplained 'detection failed'."""
    try:
        if os.path.getsize(path) < 100000:       # a real model is megabytes
            return False
        with open(path, "rb") as f:
            return f.read(4) == b"PK\x03\x04"
    except OSError:
        return False


def build_detect_script(cfg):
    """Run a model on one image and print the detected boxes as JSON (normalised
    xywh + class index + confidence) on a 'BUBBLR_BOXES' line. For pre-labelling
    in BubblR Trainer. Guarded for Windows spawn safety."""
    return (
        "import json, sys, multiprocessing\n"
        "from ultralytics import YOLO\n"
        "\n"
        "def _run():\n"
        "    c = json.load(open(sys.argv[1], encoding='utf-8'))\n"
        "    m = YOLO(c['model'])\n"
        "    res = m.predict(source=c['source'], imgsz=c['imgsz'],\n"
        "                    conf=c['conf'], save=False, verbose=False)\n"
        "    out = []\n"
        "    for r in res:\n"
        "        b = r.boxes\n"
        "        if b is None:\n"
        "            continue\n"
        "        for (cx, cy, w, h), k, s in zip(b.xywhn.tolist(),\n"
        "                                        b.cls.tolist(), b.conf.tolist()):\n"
        "            out.append({'cls': int(k), 'cx': cx, 'cy': cy,\n"
        "                        'w': w, 'h': h, 'conf': s})\n"
        "    print('BUBBLR_BOXES', json.dumps(out))\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    multiprocessing.freeze_support()\n"
        "    _run()\n")


def detect_config(model, source, imgsz=640, conf=0.25):
    return {"model": model, "source": source, "imgsz": int(imgsz),
            "conf": float(conf)}


def build_val_script(cfg):
    """Validate a model on a dataset and print its mAP50-95 on a 'BUBBLR_VAL'
    line. Used to score a baseline model for comparison."""
    return (
        "import json, sys, multiprocessing\n"
        "from ultralytics import YOLO\n"
        "\n"
        "def _run():\n"
        "    c = json.load(open(sys.argv[1], encoding='utf-8'))\n"
        "    m = YOLO(c['model'])\n"
        "    kw = dict(data=c['data'], imgsz=c['imgsz'])\n"
        "    if c.get('device'):\n"
        "        kw['device'] = c['device']\n"
        "    r = m.val(**kw)\n"
        "    print('BUBBLR_VAL', float(r.box.map))\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    multiprocessing.freeze_support()\n"
        "    _run()\n")


def val_config(model, data, imgsz=640, device=""):
    return {"model": model, "data": data, "imgsz": int(imgsz),
            "device": device or ""}


def build_rank_script(cfg):
    """Rank every image in a folder (recursively) by how much the model detects
    (sum of detection confidences), best first. Pages already labelled — i.e.
    whose pixels are already exported into the dataset — are dropped, matched by
    a 16x16 average hash (robust to JPG/PNG re-encoding). Prints a 'BUBBLR_RANK'
    line with a JSON list of [path, score, count]."""
    return (
        "import json, os, sys, multiprocessing\n"
        "from ultralytics import YOLO\n"
        "from PIL import Image\n"
        "\n"
        "EXTS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')\n"
        "\n"
        "def _ahash(path):\n"
        "    try:\n"
        "        with Image.open(path) as im:\n"
        "            g = im.convert('L').resize((16, 16))\n"
        "        px = list(g.getdata())\n"
        "        avg = (sum(px) / len(px)) if px else 0\n"
        "        bits = 0\n"
        "        for i, v in enumerate(px):\n"
        "            if v > avg:\n"
        "                bits |= 1 << i\n"
        "        return '%064x' % bits\n"
        "    except Exception:\n"
        "        return None\n"
        "\n"
        "def _labeled(store):\n"
        "    out = set()\n"
        "    for sub in ('train', 'val'):\n"
        "        d = os.path.join(store, 'images', sub)\n"
        "        if os.path.isdir(d):\n"
        "            for f in os.listdir(d):\n"
        "                if f.lower().endswith(EXTS):\n"
        "                    h = _ahash(os.path.join(d, f))\n"
        "                    if h:\n"
        "                        out.add(h)\n"
        "    return out\n"
        "\n"
        "def _run():\n"
        "    c = json.load(open(sys.argv[1], encoding='utf-8'))\n"
        "    imgs = []\n"
        "    for root, dirs, files in os.walk(c['dir']):\n"
        "        dirs[:] = [d for d in dirs if d != '_label_first']\n"
        "        for f in files:\n"
        "            if f.lower().endswith(EXTS):\n"
        "                imgs.append(os.path.join(root, f))\n"
        "    imgs.sort()\n"
        "    labeled = _labeled(c['dataset']) if c.get('dataset') else set()\n"
        "    if labeled:\n"
        "        before = len(imgs)\n"
        "        imgs = [p for p in imgs if _ahash(p) not in labeled]\n"
        "        print('skipped %d already-labelled page(s)' % (before - len(imgs)),\n"
        "              flush=True)\n"
        "    m = YOLO(c['model'])\n"
        "    scored = []\n"
        "    for i in range(0, len(imgs), 16):\n"
        "        batch = imgs[i:i + 16]\n"
        "        res = m.predict(source=batch, imgsz=c['imgsz'], conf=c['conf'],\n"
        "                        save=False, verbose=False)\n"
        "        for img, r in zip(batch, res):\n"
        "            b = r.boxes\n"
        "            n = int(len(b)) if b is not None else 0\n"
        "            s = float(b.conf.sum()) if n else 0.0\n"
        "            scored.append([img, s, n])\n"
        "        print('scanned %d/%d' % (min(i + 16, len(imgs)), len(imgs)),\n"
        "              flush=True)\n"
        "    scored.sort(key=lambda t: t[1], reverse=True)\n"
        "    print('BUBBLR_RANK', json.dumps(scored))\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    multiprocessing.freeze_support()\n"
        "    _run()\n")


def rank_config(model, folder, imgsz=640, conf=0.25, dataset=""):
    return {"model": model, "dir": folder, "imgsz": int(imgsz),
            "conf": float(conf), "dataset": dataset or ""}


def read_yaml_summary(path):
    """Small reader for a BubblR/YOLO data.yaml: returns (nc, [names])."""
    names, nc = [], None
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return None, []
    in_names = False
    for raw in lines:
        t = raw.strip()
        if t.startswith("nc:"):
            try:
                nc = int(t.split(":", 1)[1].strip())
            except ValueError:
                pass
        if t.startswith("names:"):
            rest = t.split(":", 1)[1].strip()
            if rest.startswith("["):                 # inline list form
                names = [s.strip().strip("'\"") for s in
                         rest.strip("[]").split(",") if s.strip()]
            else:
                in_names = True
            continue
        if in_names:
            m = re.match(r"^-?\s*(?:\d+\s*:\s*)?(.+)$", t)
            if t and (t[0] == "-" or ":" in t) and m:
                names.append(m.group(1).strip().strip("'\""))
            elif t and not raw.startswith((" ", "\t", "-")):
                in_names = False
    if nc is None and names:
        nc = len(names)
    return nc, names


def build_train_script(cfg):
    """Text of a tiny Ultralytics training script driven by a JSON config file
    (path passed as argv[1]).

    The training is guarded by ``if __name__ == '__main__'`` (+ freeze_support):
    on Windows, PyTorch's DataLoader spawns worker processes that re-import this
    script, so an unguarded ``m.train(...)`` at module level makes each worker
    re-launch training and crash ('worker exited unexpectedly')."""
    return (
        "import json, sys, multiprocessing\n"
        "from ultralytics import YOLO\n"
        "\n"
        "def _run():\n"
        "    c = json.load(open(sys.argv[1], encoding='utf-8'))\n"
        "    m = YOLO(c['model'])\n"
        "    kw = dict(data=c['data'], epochs=c['epochs'], imgsz=c['imgsz'],\n"
        "              batch=c['batch'], project=c['project'], name=c['name'],\n"
        "              exist_ok=True)\n"
        "    if c.get('device'):\n"
        "        kw['device'] = c['device']\n"
        "    for k in ('patience', 'cache', 'pretrained', 'workers'):\n"
        "        if c.get(k) is not None:\n"
        "            kw[k] = c[k]\n"
        "    if c.get('resume'):\n"
        "        kw['resume'] = True\n"
        "    r = m.train(**kw)\n"
        "    print('BUBBLR_DONE', getattr(r, 'save_dir', ''))\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    multiprocessing.freeze_support()\n"
        "    _run()\n")


def train_config(model, data, epochs, imgsz, batch, device, project, name,
                 patience=100, workers=None, cache=False, pretrained=True,
                 resume=False):
    """Assemble the JSON config the training script consumes. The last five
    arguments are the optional/advanced controls (early stop, DataLoader workers,
    image cache, pretrained weights, and resuming an interrupted run)."""
    cfg = {"model": model, "data": data, "epochs": int(epochs),
           "imgsz": int(imgsz), "batch": int(batch), "device": device or "",
           "project": project, "name": name, "patience": int(patience),
           "cache": bool(cache), "pretrained": bool(pretrained),
           "resume": bool(resume)}
    if workers is not None:
        cfg["workers"] = int(workers)
    return cfg


def build_predict_script(cfg):
    """Ultralytics prediction script (run best.pt on an image, save the annotated
    result). Guarded like the training script for Windows spawn safety."""
    return (
        "import json, sys, multiprocessing\n"
        "from ultralytics import YOLO\n"
        "\n"
        "def _run():\n"
        "    c = json.load(open(sys.argv[1], encoding='utf-8'))\n"
        "    m = YOLO(c['model'])\n"
        "    r = m.predict(source=c['source'], save=True, project=c['project'],\n"
        "                  name=c['name'], exist_ok=True, imgsz=c['imgsz'],\n"
        "                  conf=c['conf'])\n"
        "    print('BUBBLR_PREDICT', r[0].save_dir if r else '')\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    multiprocessing.freeze_support()\n"
        "    _run()\n")


def predict_config(model, source, project, name, imgsz=640, conf=0.25):
    return {"model": model, "source": source, "project": project,
            "name": name, "imgsz": int(imgsz), "conf": float(conf)}


def diagnose_error(text):
    """Map a failed run's log to a short, actionable hint (or None)."""
    t = (text or "").lower()
    if "out of memory" in t:
        return ("GPU out of memory — lower Batch (try 4 or -1) or Image size, "
                "or set Device to cpu.")
    if "no module named 'ultralytics'" in t:
        return ("Ultralytics isn't installed in this Python — use the "
                "'Install Ultralytics' button.")
    if "no module named 'torch'" in t:
        return "PyTorch is missing — 'Install Ultralytics' installs it too."
    if "no module named 'pil'" in t or "no module named 'pillow'" in t:
        return ("Pillow is missing in this Python (ranking needs it) — run "
                "'Install Ultralytics', which pulls it in.")
    if "dll load failed" in t or "fbgemm" in t or "c10.dll" in t:
        return ("PyTorch can't load its DLLs — install the Microsoft Visual "
                "C++ Redistributable (x64) and restart.")
    if "numpy" in t and ("1.x cannot be run in" in t or "_array_api" in t
                         or "binary incompatib" in t):
        return ("NumPy version clash — run: pip install \"numpy<2\" in the AI "
                "Python, then retry.")
    if "weights_only" in t or "unpicklingerror" in t or "invalid load key" in t:
        return ("The model file is corrupt or incomplete — delete it and "
                "download the shared model again.")
    if "worker" in t and "exited unexpectedly" in t:
        return "DataLoader crashed — in Advanced set workers to 0 and retry."
    if "no labels found" in t or "missing labels" in t:
        return ("No labels found — the labels/ folder must sit next to images/ "
                "and match data.yaml.")
    if "does not exist" in t or "no such file" in t:
        return ("A path from data.yaml can't be found — re-export, or fix the "
                "'path:' line in data.yaml.")
    if "winerror 5" in t or "permission denied" in t:
        return ("Access denied — this Python can't be written to. Use a Python "
                "in your user folder, or reinstall it for your user only.")
    return None


def read_run_metric(run_dir, key="mAP50-95"):
    """Read a training run's final metric from results.csv (default mAP50-95).
    Returns a float, or None if unavailable."""
    csv = os.path.join(run_dir, "results.csv")
    if not os.path.isfile(csv):
        return None
    try:
        with open(csv, encoding="utf-8") as f:
            rows = [r for r in (line.strip() for line in f) if r]
        if len(rows) < 2:
            return None
        header = [h.strip() for h in rows[0].split(",")]
        idx = next((i for i, h in enumerate(header) if key in h), None)
        if idx is None:
            return None
        return float(rows[-1].split(",")[idx].strip())
    except Exception:                            # noqa: BLE001
        return None


def parse_metrics(text):
    """Extract the final validation metrics from the log's summary 'all …' row:
    returns {'P','R','mAP50','mAP50_95'} or None."""
    best = None
    for raw in (text or "").splitlines():
        line = strip_ansi(raw).strip()
        if line.startswith("all "):
            nums = line.split()[1:]
            try:
                if len(nums) >= 6:
                    best = {"P": float(nums[-4]), "R": float(nums[-3]),
                            "mAP50": float(nums[-2]), "mAP50_95": float(nums[-1])}
            except ValueError:
                pass
    return best


def check_dataset(yaml_path):
    """Light pre-flight check of a YOLO data.yaml. Returns (ok, [messages]) —
    ok is False only for hard problems (no images); other notes are warnings."""
    msgs = []
    if not os.path.isfile(yaml_path):
        return False, ["data.yaml not found."]
    base = os.path.dirname(os.path.abspath(yaml_path))
    root, train_rel, val_rel = base, "images/train", None
    try:
        for line in open(yaml_path, encoding="utf-8"):
            s = line.strip()
            if s.startswith("path:"):
                root = s.split(":", 1)[1].strip() or base
            elif s.startswith("train:"):
                train_rel = s.split(":", 1)[1].split("#")[0].strip()
            elif s.startswith("val:"):
                val_rel = s.split(":", 1)[1].split("#")[0].strip()
    except OSError:
        return False, ["Could not read data.yaml."]
    if not os.path.isabs(root):
        root = os.path.normpath(os.path.join(base, root))

    def count(rel):
        d = os.path.normpath(rel if os.path.isabs(rel)
                             else os.path.join(root, rel))
        if not os.path.isdir(d):
            return None, None, d
        imgs = [f for f in os.listdir(d)
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp"))]
        ldir = d.replace(os.sep + "images" + os.sep, os.sep + "labels" + os.sep)
        labels = ([f for f in os.listdir(ldir) if f.lower().endswith(".txt")]
                  if os.path.isdir(ldir) else [])
        return len(imgs), len(labels), d

    ni, nl, td = count(train_rel)
    if ni is None:
        return False, ["Train folder not found: %s" % td]
    if ni == 0:
        return False, ["No training images found in %s" % td]
    msgs.append("Train: %d images, %d label files." % (ni, nl))
    if nl == 0:
        msgs.append("⚠ No label files next to the training images.")
    elif nl < ni:
        msgs.append("⚠ %d images have no label (used as background)."
                    % (ni - nl))
    if val_rel:
        vi, vl, vd = count(val_rel)
        if vi:
            msgs.append("Val: %d images, %d label files." % (vi, vl))
    return True, msgs


_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def strip_ansi(line):
    """Remove ANSI colour/cursor escapes and keep only the final tqdm redraw
    segment (after the last carriage return)."""
    return _ANSI.sub("", line).split("\r")[-1]


def parse_progress(line):
    """Pull (current_epoch, total_epochs) from an Ultralytics epoch line, which
    starts with the epoch column, e.g. '        1/100      2.5G   …'. Anchored at
    the line start (after stripping ANSI/redraws) so dataset-scan ('16/16') and
    download bars don't match."""
    m = re.match(r"\s*(\d+)/(\d+)\b", strip_ansi(line))
    if not m:
        return None
    cur, total = int(m.group(1)), int(m.group(2))
    if total >= cur >= 0 and 0 < total < 100000:
        return cur, total
    return None
