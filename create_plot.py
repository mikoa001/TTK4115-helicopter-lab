#!/usr/bin/env python3
"""Plot .mat files from the lab1 folder.

This script scans a folder for .mat files, loads numeric arrays and creates
PNG plots for each sensible variable. By default it saves plots under
`<input_folder>/figs/`.

Features:
- Handles MATLAB v5 .mat files via scipy.io.loadmat
- Plots 1D arrays and 2D arrays (each column as a series)
- Skips non-numeric or >2D variables
- CLI options for input folder, output folder, showing plots and saving

Example:
    python create_plot.py --input lab1 --output lab1/figs --save

"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

import numpy as np
import scipy.io


def find_mat_files(folder: Path):
    return sorted(folder.glob("*.mat"))


def is_numeric_array(obj: Any) -> bool:
    return isinstance(obj, (np.ndarray,)) and np.issubdtype(obj.dtype, np.number)


def process_mat_file(mat_path: Path, out_dir: Path, save: bool, show: bool, figsize=(12, 6)):
    logging.info("Processing %s", mat_path)
    try:
        data = scipy.io.loadmat(str(mat_path))
    except Exception as e:
        logging.warning("Failed to load %s: %s", mat_path, e)
        return 0

    # omit MATLAB meta keys
    keys = [k for k in data.keys() if not (k.startswith("__") and k.endswith("__"))]
    if not keys:
        logging.info("No user variables found in %s", mat_path)
        return

    # pyplot should be available; backend must already be configured in main()
    import matplotlib.pyplot as plt

    saved = 0
    for key in keys:
        val = data[key]
        if not is_numeric_array(val):
            logging.debug("Skipping non-numeric variable %s", key)
            continue

        # flatten length-1 dimensions, but keep 2D arrays
        arr = np.array(val)
        if arr.ndim == 0:
            logging.debug("Skipping scalar %s", key)
            continue

        fig, ax = plt.subplots(figsize=figsize)
        try:
            if arr.ndim == 1 or (arr.ndim == 2 and 1 in arr.shape):
                y = arr.ravel()
                x = np.arange(y.shape[0])
                ax.plot(x, y, label=key)
                ax.set_xlabel("index")
                ax.set_ylabel(key)
            elif arr.ndim == 2:
                # plot each column as a series
                nrows, ncols = arr.shape
                x = np.arange(nrows)
                for col in range(ncols):
                    ax.plot(x, arr[:, col], label=f"{key}[ :, {col} ]")
                ax.set_xlabel("index")
                ax.set_ylabel(key)
                ax.legend(loc="best", fontsize="small")
            else:
                logging.debug("Skipping %s: ndim=%d >2", key, arr.ndim)
                plt.close(fig)
                continue

            ax.set_title(f"{mat_path.name} — {key}")
            ax.grid(True, linestyle="--", alpha=0.5)

            out_file = out_dir / f"{mat_path.stem}__{key}.png"
            if save:
                out_dir.mkdir(parents=True, exist_ok=True)
                # force PNG output to avoid environment defaulting to PDF
                fig.savefig(str(out_file), dpi=150, format="png")
                logging.info("Saved plot: %s", out_file)
                saved += 1

            if show:
                plt.show()
            plt.close(fig)
        except Exception as e:
            logging.warning("Failed plotting variable %s from %s: %s", key, mat_path, e)
            plt.close(fig)
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot .mat files from a folder")
    parser.add_argument("--input", "-i", default="lab1", help="Input folder containing .mat files")
    parser.add_argument("--output", "-o", default=None, help="Output folder for plots (default: <input>/figs)")
    parser.add_argument("--save", action="store_true", help="Save plots to files (default: False)")
    parser.add_argument("--show", action="store_true", help="Show plots interactively (default: False)")
    parser.add_argument("--figsize", default="12,6", help="Figure size as 'width,height' in inches (default: 12,6)")
    parser.add_argument("--verbose", "-v", action="count", default=0, help="Increase logging verbosity")

    args = parser.parse_args()

    level = logging.WARNING
    if args.verbose == 1:
        level = logging.INFO
    elif args.verbose >= 2:
        level = logging.DEBUG
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    input_folder = Path(args.input)
    if not input_folder.exists() or not input_folder.is_dir():
        logging.error("Input folder does not exist: %s", input_folder)
        return

    out_dir = Path(args.output) if args.output else input_folder / "figs"

    mat_files = find_mat_files(input_folder)
    if not mat_files:
        logging.warning("No .mat files found in %s", input_folder)
        return

    # configure matplotlib backend once (must be before any pyplot import)
    import matplotlib
    if not args.show:
        matplotlib.use("Agg")

    # parse figsize argument (string like '12,6')
    try:
        w, h = [float(s) for s in args.figsize.split(",")]
        figsize = (w, h)
    except Exception:
        figsize = (12, 6)

    total_saved = 0
    for m in mat_files:
        saved = process_mat_file(m, out_dir, save=args.save, show=args.show, figsize=figsize)
        total_saved += int(saved or 0)

    logging.info("Total plots saved: %d", total_saved)


if __name__ == "__main__":
    main()
