# -*- coding: utf-8 -*-
"""Pure (GUI-free) training helpers for BubblR Model Trainer.

Kept separate from the PyQt5 app so the exact command/script the GUI runs can be
unit-tested and reused without importing Qt."""

import os
import re

# --- shared model distribution (the BubblR-Model repo) ---
MODEL_URL = ("https://github.com/valle3011/BubblR-Model/releases/"
             "latest/download/bubblr-model.pt")
MODEL_META_URL = ("https://raw.githubusercontent.com/valle3011/"
                  "BubblR-Model/main/model.json")


def model_path():
    """Local path where the downloaded shared model is kept."""
    d = os.path.join(os.path.expanduser("~"), ".bubblr_ai")
    return os.path.join(d, "bubblr-model.pt")


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
    """Rank every image in a folder by how much the model detects (sum of
    detection confidences), best first. Prints a 'BUBBLR_RANK' line with a JSON
    list of [path, score, count]. Used to pick which raw pages to label first."""
    return (
        "import json, os, sys, multiprocessing\n"
        "from ultralytics import YOLO\n"
        "\n"
        "def _run():\n"
        "    c = json.load(open(sys.argv[1], encoding='utf-8'))\n"
        "    exts = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')\n"
        "    imgs = [os.path.join(c['dir'], f)\n"
        "            for f in sorted(os.listdir(c['dir']))\n"
        "            if f.lower().endswith(exts)]\n"
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


def rank_config(model, folder, imgsz=640, conf=0.25):
    return {"model": model, "dir": folder, "imgsz": int(imgsz),
            "conf": float(conf)}


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
    if "worker" in t and "exited unexpectedly" in t:
        return "DataLoader crashed — in Advanced set workers to 0 and retry."
    if "no labels found" in t or "missing labels" in t:
        return ("No labels found — the labels/ folder must sit next to images/ "
                "and match data.yaml.")
    if "does not exist" in t or "no such file" in t:
        return ("A path from data.yaml can't be found — re-export, or fix the "
                "'path:' line in data.yaml.")
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
