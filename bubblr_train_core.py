# -*- coding: utf-8 -*-
"""Pure (GUI-free) training helpers for BubblR Model Trainer.

Kept separate from the PyQt5 app so the exact command/script the GUI runs can be
unit-tested and reused without importing Qt."""

import re


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
        "    r = m.train(**kw)\n"
        "    print('BUBBLR_DONE', getattr(r, 'save_dir', ''))\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    multiprocessing.freeze_support()\n"
        "    _run()\n")


def train_config(model, data, epochs, imgsz, batch, device, project, name):
    """Assemble the JSON config the training script consumes."""
    return {"model": model, "data": data, "epochs": int(epochs),
            "imgsz": int(imgsz), "batch": int(batch), "device": device or "",
            "project": project, "name": name}


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
