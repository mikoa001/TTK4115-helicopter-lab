#!/usr/bin/env python3
"""Simple batch plotter for .mat files in lab1.

For each .mat file in the `lab1` folder, this script finds the first suitable
numeric variable (1D or 2D) and produces a PNG plot saved to `lab1/figs/`.
If a variable is 2D, each column is plotted. If multiple numeric variables
exist, you can choose one by name with --var; otherwise the first is used.

Usage (PowerShell):
    python plot_lab1.py           # saves PNGs for each .mat
    python plot_lab1.py --var x    # pick specific variable name if present
    python plot_lab1.py --all      # plot all numeric variables per file

Outputs:
    lab1/figs/<mat_stem>__<var>.png

Dependencies: numpy, scipy, matplotlib (see requirements.txt).
"""
from __future__ import annotations

import argparse
from pathlib import Path
import logging
from typing import Any, List

import numpy as np
import scipy.io


def is_numeric_array(obj: Any) -> bool:
    return isinstance(obj, np.ndarray) and np.issubdtype(obj.dtype, np.number) and obj.ndim in (1, 2)


def load_numeric_variables(mat_path: Path) -> List[str]:
    try:
        data = scipy.io.loadmat(str(mat_path))
    except Exception as e:
        logging.warning("Failed to load %s: %s", mat_path, e)
        return []
    keys = [k for k in data.keys() if not (k.startswith("__") and k.endswith("__"))]
    numeric = [k for k in keys if is_numeric_array(data[k])]
    return numeric


def plot_variable(mat_path: Path, var: str, out_dir: Path, figsize=(10, 5)) -> bool:
    import matplotlib
    matplotlib.use("Agg")  # ensure non-interactive
    import matplotlib.pyplot as plt

    try:
        data = scipy.io.loadmat(str(mat_path))
    except Exception as e:
        logging.error("Reload failed %s: %s", mat_path, e)
        return False
    arr = data.get(var)
    if arr is None or not is_numeric_array(arr):
        logging.debug("Variable %s not suitable in %s", var, mat_path.name)
        return False
    arr = np.array(arr)

    fig, ax = plt.subplots(figsize=figsize)
    try:
        if arr.ndim == 1 or (arr.ndim == 2 and 1 in arr.shape):
            y = arr.ravel()
            x = np.arange(y.shape[0])
            ax.plot(x, y, label=var)
        else:  # 2D
            nrows, ncols = arr.shape
            x = np.arange(nrows)
            for c in range(ncols):
                ax.plot(x, arr[:, c], label=f"{var}[ :, {c} ]")
            ax.legend(loc="best", fontsize="small")
        ax.set_title(f"{mat_path.name} — {var}")
        ax.set_xlabel("index")
        ax.set_ylabel(var)
        ax.grid(True, linestyle="--", alpha=0.4)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{mat_path.stem}__{var}.png"
        fig.savefig(out_file, dpi=150, format="png")
        logging.info("Saved %s", out_file)
        return True
    except Exception as e:
        logging.warning("Plot failed for %s:%s -> %s", mat_path.name, var, e)
        return False
    finally:
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Plot one or all numeric variables from .mat files in lab1")
    parser.add_argument("--folder", default="lab1", help="Folder containing .mat files (default: lab1)")
    parser.add_argument("--var", help="Specific variable name to plot if present")
    parser.add_argument("--all", action="store_true", help="Plot all numeric variables instead of just the first")
    parser.add_argument("--figsize", default="10,5", help="Figure size 'w,h' (default 10,5)")
    parser.add_argument("--verbose", "-v", action="count", default=0, help="Increase verbosity (-v, -vv)")
    args = parser.parse_args()

    level = logging.WARNING
    if args.verbose == 1:
        level = logging.INFO
    elif args.verbose >= 2:
        level = logging.DEBUG
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    folder = Path(args.folder)
    if not folder.is_dir():
        logging.error("Folder not found: %s", folder)
        return
    try:
        w, h = [float(x) for x in args.figsize.split(",")]
        figsize = (w, h)
    except Exception:
        logging.warning("Invalid figsize '%s', using default", args.figsize)
        figsize = (10, 5)

    mat_files = sorted(folder.glob("*.mat"))
    if not mat_files:
        logging.warning("No .mat files in %s", folder)
        return

    out_dir = folder / "figs"
    total_plots = 0
    for mat in mat_files:
        numeric_vars = load_numeric_variables(mat)
        if not numeric_vars:
            logging.info("No numeric variables in %s", mat.name)
            continue
        targets: List[str]
        if args.var:
            # Only plot specified variable if present
            targets = [v for v in numeric_vars if v == args.var]
            if not targets:
                logging.info("Variable %s not found in %s", args.var, mat.name)
                continue
        elif args.all:
            targets = numeric_vars
        else:
            targets = [numeric_vars[0]]

        for var in targets:
            if plot_variable(mat, var, out_dir, figsize=figsize):
                total_plots += 1

    logging.info("Completed. Plots saved: %d", total_plots)


if __name__ == "__main__":
    main()
