#!/usr/bin/env python3
"""Plot states from every .mat file next to this script.

- Detects lab "ans" layout:
    shape (7, N) or (N, 7); first row/col is time, next six are states:
    [lambda, lambda_dot, pitch, pitch_dot, elevation, elevation_dot]
- Falls back to a generic 2D array with >=6 columns and a detected time vector.
- Plots a selectable subset of the six states (default: all six).
- Supports time cropping via --tmin/--tmax.
- Saves one PNG per .mat to ./figs using a non-interactive backend.

Examples (PowerShell):
  python lab2\plot.py                         # all six states, full time
  python lab2\plot.py --states pitch,elevation
  python lab2\plot.py --states 3,5            # 1-based indices
  python lab2\plot.py --tmax 60               # crop to first 60 seconds
  python lab2\plot.py --tmin 10 --tmax 40
"""
from __future__ import annotations

from email import parser
from pathlib import Path
import argparse
import logging
from typing import Iterable, Tuple, List, Optional

import numpy as np
from scipy.io import loadmat

ANS_LABELS = ["pitch", "pitch_dot", "elevation", "elevation_dot", "lambda_dot"]


def is_numeric_array(obj) -> bool:
    return hasattr(obj, "dtype") and hasattr(obj, "ndim")


def find_time_vector(data: dict) -> tuple[Optional[np.ndarray], Optional[str]]:
    """Return (time_vector, key) if a likely time vector exists, else (None, None)."""
    candidates = ["t", "time", "Time", "timestamp"]
    for k in candidates:
        if k in data:
            arr = data[k]
            if is_numeric_array(arr):
                a = np.asarray(arr)
                if a.ndim == 1 or (a.ndim == 2 and 1 in a.shape):
                    v = a.ravel()
                    if v.size >= 2 and np.all(np.diff(v) > 0):
                        return v, k
    return None, None


def load_ans_layout(data: dict) -> tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[List[str]]]:
    """If 'ans' has expected layout (time + 5 or 6 states), return (t, states[ns,N], labels)."""
    if "ans" not in data or not is_numeric_array(data["ans"]):
        return None, None, None
    A = np.asarray(data["ans"])
    if A.ndim != 2:
        return None, None, None

    # Accept time + 5 states (shape 6, N) or time + 6 states (shape 7, N)
    if A.shape[0] in (6, 7):
        t = A[0, :].ravel()
        states = A[1:, :]
    elif A.shape[1] in (6, 7):
        t = A[:, 0].ravel()
        states = A[:, 1:7] if A.shape[1] >= 7 else A[:, 1:6]  # time + 5 or 6 states
        states = states.T  # make (ns, N)
    else:
        return None, None, None

    # Sanity checks
    if t.size < 2 or not np.all(np.diff(t) > 0) or states.shape[1] != t.size:
        return None, None, None

    nstates = states.shape[0]
    labels = ANS_LABELS[:nstates] if nstates <= len(ANS_LABELS) else [f"State {i+1}" for i in range(nstates)]
    return t, states, labels

# New: detect a matrix where first row/col is time (monotone), remaining rows/cols are states
def detect_embedded_time_matrix(data: dict) -> tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[List[str]], Optional[str]]:
    for k, v in data.items():
        if not is_numeric_array(v):
            continue
        a = np.asarray(v)
        if a.ndim != 2:
            continue

        # First row is time
        if a.shape[1] >= 2 and np.all(np.diff(a[0, :].ravel()) > 0):
            t = a[0, :].ravel()
            Y = a[1:, :]
            if Y.shape[1] == t.size and Y.shape[0] >= 1:
                nstates = Y.shape[0]
                labels = ANS_LABELS[:nstates] if nstates <= len(ANS_LABELS) else [f"State {i+1}" for i in range(nstates)]
                return t, Y, labels, k

        # First column is time
        if a.shape[0] >= 2 and np.all(np.diff(a[:, 0].ravel()) > 0):
            t = a[:, 0].ravel()
            Y = a[:, 1:].T  # rows = states
            if Y.shape[1] == t.size and Y.shape[0] >= 1:
                nstates = Y.shape[0]
                labels = ANS_LABELS[:nstates] if nstates <= len(ANS_LABELS) else [f"State {i+1}" for i in range(nstates)]
                return t, Y, labels, k
    return None, None, None, None

def pick_state_indices(spec: str, labels: List[str]) -> List[int]:
    """Parse --states spec into zero-based indices using provided labels list.

    spec can be:
      - "all"
      - comma-separated names (e.g., "pitch,elevation")
      - comma-separated 1-based indices (e.g., "3,5")
    """
    if spec.strip().lower() == "all":
        return list(range(len(labels)))

    # Try names first
    parts = [p.strip().lower() for p in spec.split(",") if p.strip()]
    idx: List[int] = []
    label_to_i = {lbl.lower(): i for i, lbl in enumerate(labels)}
    name_hits = 0
    for p in parts:
        if p in label_to_i:
            idx.append(label_to_i[p])
            name_hits += 1

    if name_hits == len(parts) and name_hits > 0:
        # all parts matched names
        return sorted(set(idx))

    # Fallback to 1-based indices
    idx = []
    for p in parts:
        if p.isdigit():
            i1 = int(p)
            if 1 <= i1 <= len(labels):
                idx.append(i1 - 1)
    if idx:
        return sorted(set(idx))

    # Default to all if nothing valid
    return list(range(len(labels)))


def crop_time(t: np.ndarray, Y: np.ndarray, tmin: Optional[float], tmax: Optional[float]) -> tuple[np.ndarray, np.ndarray]:
    """Return time-cropped (t, Y). Y has shape (nstates, N)."""
    mask = np.ones_like(t, dtype=bool)
    if tmin is not None:
        mask &= (t >= float(tmin))
    if tmax is not None:
        mask &= (t <= float(tmax))
    if mask.sum() >= 2:
        return t[mask], Y[:, mask]
    return t, Y


def plot_states(t: np.ndarray, states: np.ndarray, indices: Iterable[int], labels: List[str],
                out_file: Path, figsize: Tuple[float, float], dpi: int,
                y_min: Optional[float] = None, y_max: Optional[float] = None) -> None:
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    indices = [i for i in indices if 0 <= i < states.shape[0]]
    if not indices:
        indices = list(range(states.shape[0]))

    fig, ax = plt.subplots(figsize=figsize)
    for i in indices:
        ax.plot(t, states[i, :], linewidth=1.6, label=labels[i] if i < len(labels) else f"State {i+1}")
    ax.set_xlabel("time [s]", fontsize="large")
    ax.set_ylabel("angle [rad]", fontsize="large")
    #ax.set_title("States over time")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="upper left", fontsize="large", ncols=1)
    # Apply y-limits if provided
    if y_min is not None or y_max is not None:
        cur_ymin, cur_ymax = ax.get_ylim()
        ax.set_ylim(y_min if y_min is not None else cur_ymin,
                    y_max if y_max is not None else cur_ymax)
    fig.tight_layout()
    fig.savefig(out_file, dpi=dpi, format="png")
    plt.close(fig)

def main() -> None:
    parser = argparse.ArgumentParser(description="Plot selected states from .mat files here.")
    parser.add_argument("--states", default="all",
                        help='Which states to plot: "all", names (e.g. "pitch,elevation"), or 1-based indices "3,5".')
    parser.add_argument("--tmin", type=float, default=None, help="Min time (seconds) to include")
    parser.add_argument("--tmax", type=float, default=None, help="Max time (seconds) to include")
    parser.add_argument("--figsize", default="8,7", help="Figure size W,H in inches (default 8,7)")
    parser.add_argument("--dpi", type=int, default=150, help="PNG DPI (default 150)")
    parser.add_argument("--ymax", type=float, default=None, help="Max y-value (upper axis limit)")
    parser.add_argument("--ymin", type=float, default=None, help="Min y-value (lower axis limit)")
    parser.add_argument("--yabs", type=float, default=None, help="Symmetric y-limits [-yabs, +yabs] (overrides --ymin/--ymax)")
    args = parser.parse_args()

    try:
        w, h = (float(x) for x in args.figsize.split(","))
    except Exception:
        w, h = 8.0, 8.0
    figsize = (w, h)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    script_dir = Path(__file__).parent.resolve()
    out_dir = script_dir / "figs"
    out_dir.mkdir(parents=True, exist_ok=True)

    mat_files = sorted(script_dir.glob("*.mat"))
    if not mat_files:
        logging.warning("No .mat files found in %s", script_dir)
        return

    saved = 0
    for mat_path in mat_files:
        logging.info("Processing %s", mat_path.name)
        try:
            data = loadmat(str(mat_path), squeeze_me=True)
        except Exception as e:
            logging.warning("Failed to load %s: %s", mat_path.name, e)
            continue

        # Try the lab 'ans' layout first (now supports 5 or 6 states)
        t, Y, labels = load_ans_layout(data)
        suffix = "states"
        if t is None:
            # Fallback 1: separate time vector + a 2D matrix
            t, t_key = find_time_vector(data)
            best_key = None
            best_arr = None
            if t is not None:
                for k, v in data.items():
                    if k == t_key or not is_numeric_array(v):
                        continue
                    a = np.asarray(v)
                    if a.ndim != 2:
                        continue
                    if a.shape[0] == t.size and a.shape[1] >= 1:
                        best_key, best_arr = k, a
                        break
                    if a.shape[1] == t.size and a.shape[0] >= 1 and best_arr is None:
                        best_key, best_arr = k, a.T  # rows=time
                if best_arr is not None and best_arr.shape[1] == t.size:
                    Y = best_arr
                    labels = ANS_LABELS[:Y.shape[0]] if Y.shape[0] <= len(ANS_LABELS) else [f"State {i+1}" for i in range(Y.shape[0])]
                    suffix = best_key
                else:
                    t = None  # force next fallback

            # Fallback 2: embedded time in first row/col of a 2D array
            if t is None:
                t, Y, labels, key = detect_embedded_time_matrix(data)
                if t is not None:
                    suffix = key

            if t is None:
                logging.info("Skipping %s (no time vector found).", mat_path.name)
                continue

        # Time crop and plotting unchanged
        t, Y = crop_time(t, Y, args.tmin, args.tmax)
        indices = pick_state_indices(args.states, labels)
        out_file = out_dir / f"{mat_path.stem}__{suffix}.png"
        # Resolve y-limits
        if args.yabs is not None:
            y_min, y_max = -abs(args.yabs), abs(args.yabs)
        else:
            y_min, y_max = args.ymin, args.ymax
        plot_states(t, Y, indices, labels, out_file, figsize, args.dpi, y_min=y_min, y_max=y_max)
        logging.info("Saved %s", out_file.name)


if __name__ == "__main__":
    main()