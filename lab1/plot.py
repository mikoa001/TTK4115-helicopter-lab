"""Plot PNGs for every .mat file next to this script.

Why your old version failed: relative paths are resolved against the current
working directory, not the script location. This version resolves paths
relative to the script and saves PNGs without GUI windows.
"""
from pathlib import Path
import logging

import numpy as np
from scipy.io import loadmat

# Select which named states to plot when labels are known (from 'ans' layout)
SELECTED_LABELS = {"pitch", "elevation"}
ANS_LABELS = ["lambda", "lambda_dot", "pitch", "pitch_dot", "elevation", "elevation_dot"]

def is_numeric_array(obj) -> bool:
    return hasattr(obj, "dtype") and hasattr(obj, "ndim") and obj.ndim in (1, 2)


def find_time_vector(data: dict) -> tuple[np.ndarray | None, str | None]:
    """Return (time_vector, key) if a likely time vector exists, else (None, None)."""
    candidates = ["t", "time", "Time", "timestamp"]
    for k in candidates:
        if k in data:
            arr = data[k]
            if is_numeric_array(arr):
                a = np.asarray(arr)
                if a.ndim == 1 or (a.ndim == 2 and 1 in a.shape):
                    return a.ravel(), k
    return None, None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    script_dir = Path(__file__).parent.resolve()
    mat_files = sorted(script_dir.glob("*.mat"))
    if not mat_files:
        logging.warning("No .mat files found in %s", script_dir)
        return

    # Use a non-interactive backend and import pyplot
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir = script_dir / "figs"
    out_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    for mat_path in mat_files:
        logging.info("Processing %s", mat_path.name)
        try:
            data = loadmat(str(mat_path))
        except Exception as e:
            logging.warning("Failed to load %s: %s", mat_path.name, e)
            continue

        # Prefer the common lab format: 'ans' with first row as time and next 6 rows as states
        if 'ans' in data and is_numeric_array(data['ans']):
            A = np.asarray(data['ans'])
            if A.ndim == 2 and A.shape[0] >= 7:
                t = A[0, :].ravel()
                # verify time is monotone increasing
                if t.size > 1 and np.all(np.diff(t) > 0):
                    states = A[1:7, :]
                    import matplotlib.pyplot as plt
                    fig, ax = plt.subplots(figsize=(14, 6))
                    labels = ANS_LABELS
                    # plot only selected labels (default: pitch, elevation)
                    sel_indices = [i for i, lbl in enumerate(labels) if lbl in SELECTED_LABELS]
                    if not sel_indices:
                        sel_indices = [2, 4]  # fallback to pitch (2) and elevation (4)
                    for i in sel_indices:
                        ax.plot(t, states[i, :], linewidth=1.5, label=labels[i])
                    ax.set_title("States over time")
                    ax.set_xlabel("time [s]")
                    ax.set_ylabel("value")
                    ax.grid(True, linestyle="--", alpha=0.6)
                    ax.legend(loc="upper left", fontsize="medium")
                    fig.tight_layout()
                    out_file = out_dir / f"{mat_path.stem}__states.png"
                    fig.savefig(out_file, dpi=150, format="png")
                    logging.info("Saved %s", out_file.name)
                    total += 1
                    plt.close(fig)
                    # Done with this file
                    continue

        # Filter out MATLAB metadata keys (fallback path)
        keys = [k for k in data.keys() if not (k.startswith("__") and k.endswith("__"))]
        if not keys:
            logging.info("No user variables in %s", mat_path.name)
            continue

        # Find time vector if present
        t, t_key = find_time_vector(data)
        len_t = t.shape[0] if t is not None else None

        # Find a 2D numeric array with at least 6 columns to represent states
        best_key = None
        best_arr = None
        best_rows_time_aligned = False
        for k in keys:
            if t_key and k == t_key:
                continue
            arr = data[k]
            if not is_numeric_array(arr):
                continue
            a = np.asarray(arr)
            if a.ndim != 2:
                continue
            nrows, ncols = a.shape
            # Prefer arrays aligned by rows with time and at least 6 columns
            if len_t is not None and nrows == len_t and ncols >= 6:
                best_key = k
                best_arr = a
                best_rows_time_aligned = True
                break
            # Otherwise remember a candidate with >=6 columns
            if best_arr is None and ncols >= 6:
                best_key = k
                best_arr = a

        if best_arr is None:
            logging.info("No 2D state-like variable (>=6 columns) found in %s", mat_path.name)
            continue

        # If time aligns with columns, transpose so rows are time samples
        if (not best_rows_time_aligned) and (len_t is not None) and best_arr.shape[1] == len_t:
            best_arr = best_arr.T
            best_rows_time_aligned = True

        nrows, ncols = best_arr.shape
        x_data = t if (t is not None and best_rows_time_aligned and len_t == nrows) else np.arange(nrows)

        '''
        # Plot first 6 states on one axis as a fallback
        nstates = min(6, ncols)
        import matplotlib.pyplot as plt  # already set Agg
        fig, ax = plt.subplots(figsize=(14, 6))
        for i in range(nstates):
            ax.plot(x_data, best_arr[:, i], linewidth=1.5, label=f"State {i+1}")
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.set_xlabel(t_key if (t is not None and best_rows_time_aligned) else "index")
        ax.set_ylabel("value")
        ax.set_title(f"{mat_path.name} — {best_key}")
        ax.legend(loc="upper left")
        fig.tight_layout()

        out_file = out_dir / f"{mat_path.stem}__{best_key}__states.png"
        fig.savefig(out_file, dpi=150, format="png")
        logging.info("Saved %s", out_file.name)
        total += 1
        plt.close(fig)
        '''
        # Plot only pitch and elevation as a fallback (assumes columns 3 and 5 if available)
        nrows, ncols = best_arr.shape
        x_data = t if (t is not None and best_rows_time_aligned and len_t == nrows) else np.arange(nrows)

        import matplotlib.pyplot as plt  # already set Agg
        fig, ax = plt.subplots(figsize=(14, 6))
        if ncols >= 5:
            col_idxs = [2, 4]  # likely pitch, elevation in lab convention
            col_labels = ["pitch", "elevation"]
        else:
            col_idxs = list(range(min(2, ncols)))
            col_labels = [f"State {i+1}" for i in col_idxs]

        for idx, lbl in zip(col_idxs, col_labels):
            ax.plot(x_data, best_arr[:, idx], linewidth=1.5, label=lbl)

        ax.grid(True, linestyle="--", alpha=0.6)
        ax.set_xlabel(t_key if (t is not None and best_rows_time_aligned) else "index")
        ax.set_ylabel("value")
        ax.set_title(f"{mat_path.name} — {best_key}")
        ax.legend(loc="upper left")
        fig.tight_layout()

        out_file = out_dir / f"{mat_path.stem}__{best_key}__pitch_elev.png"
        fig.savefig(out_file, dpi=150, format="png")
        logging.info("Saved %s", out_file.name)
        total += 1
        plt.close(fig) 
               
    logging.info("Done. Total plots saved: %d", total)


if __name__ == "__main__":
    main()