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

from pathlib import Path
import argparse
import logging
from typing import Iterable, Tuple, List, Optional

import numpy as np
from scipy.io import loadmat

ANS_LABELS = ["lambda", "lambda_dot", "pitch", "pitch_dot", "elevation", "elevation_dot"]


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
    """If 'ans' has the expected layout, return (t, states[6,N], labels)."""
    if "ans" not in data or not is_numeric_array(data["ans"]):
        return None, None, None
    A = np.asarray(data["ans"])
    if A.ndim != 2:
        return None, None, None

    # Accept (7, N) or (N, 7)
    if A.shape[0] == 7:
        t = A[0, :].ravel()
        states = A[1:7, :]
    elif A.shape[1] == 7:
        t = A[:, 0].ravel()
        states = A[:, 1:7].T  # make it (6, N)
    else:
        return None, None, None

    if t.size < 2 or not np.all(np.diff(t) > 0) or states.shape[1] != t.size:
        return None, None, None

    return t, states, ANS_LABELS[:]  # copy of labels


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
                out_file: Path, figsize: Tuple[float, float], dpi: int) -> None:
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    indices = [i for i in indices if 0 <= i < states.shape[0]]
    if not indices:
        indices = list(range(states.shape[0]))

    fig, ax = plt.subplots(figsize=figsize)
    for i in indices:
        ax.plot(t, states[i, :], linewidth=1.6, label=labels[i] if i < len(labels) else f"State {i+1}")
    ax.set_xlabel("time [s]")
    ax.set_ylabel("value")
    ax.set_title("States over time")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="upper left", fontsize="medium", ncols=1)
    fig.tight_layout()
    fig.savefig(out_file, dpi=dpi, format="png")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot selected states from .mat files here.")
    parser.add_argument("--states", default="all",
                        help='Which states to plot: "all", names (e.g. "pitch,elevation"), or 1-based indices "3,5".')
    parser.add_argument("--tmin", type=float, default=None, help="Min time (seconds) to include")
    parser.add_argument("--tmax", type=float, default=None, help="Max time (seconds) to include")
    parser.add_argument("--figsize", default="14,6", help="Figure size W,H in inches (default 14,6)")
    parser.add_argument("--dpi", type=int, default=150, help="PNG DPI (default 150)")
    args = parser.parse_args()

    try:
        w, h = (float(x) for x in args.figsize.split(","))
    except Exception:
        w, h = 14.0, 6.0
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

        # Try the lab 'ans' layout first
        t, Y, labels = load_ans_layout(data)
        suffix = "states"
        if t is None:
            # Fallback: search for a time vector and a 2D array with >=6 columns
            t, t_key = find_time_vector(data)
            if t is None:
                logging.info("Skipping %s (no time vector found).", mat_path.name)
                continue

            best_key = None
            best_arr = None
            # Prefer arrays where rows align with time length and have at least 6 columns
            for k, v in data.items():
                if k == t_key:
                    continue
                if not is_numeric_array(v):
                    continue
                a = np.asarray(v)
                if a.ndim != 2:
                    continue
                if a.shape[0] == t.size and a.shape[1] >= 6:
                    best_key, best_arr = k, a
                    break
                if a.shape[1] == t.size and a.shape[0] >= 6 and best_arr is None:
                    best_key, best_arr = k, a.T  # transpose to rows=time
            if best_arr is None:
                logging.info("Skipping %s (no 2D state-like variable with >=6 columns).", mat_path.name)
                continue

            # Use first 6 rows as states
            if best_arr.shape[1] != t.size:
                logging.info("Skipping %s (states/time length mismatch).", mat_path.name)
                continue
            Y = best_arr[:6, :]
            labels = [f"State {i+1}" for i in range(Y.shape[0])]
            suffix = best_key

        # Time crop
        t, Y = crop_time(t, Y, args.tmin, args.tmax)

        # Pick which states to plot
        indices = pick_state_indices(args.states, labels)

        out_file = out_dir / f"{mat_path.stem}__{suffix}.png"
        plot_states(t, Y, indices, labels, out_file, figsize, args.dpi)
        logging.info("Saved %s", out_file.name)
        saved += 1

    logging.info("Done. Saved %d file(s) to %s", saved, out_dir)


if __name__ == "__main__":
    main()