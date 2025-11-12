# create_plot.py

This repository contains a small script to load MATLAB `.mat` files from the `lab1/` folder and create plots for numeric variables.

Usage
-----

1. Install dependencies (PowerShell):

```powershell
python -m pip install -r requirements.txt
```

2. Run the script from the repository root:

```powershell
# save plots to lab1/figs
python create_plot.py --input lab1 --save

# show plots interactively (will open windows)
python create_plot.py --input lab1 --show

# increase verbosity
python create_plot.py --input lab1 --save -v
```

Behavior
--------
- Scans the specified input folder for `*.mat` files.
- Loads variables using `scipy.io.loadmat`.
- Plots 1D arrays or each column of 2D numeric arrays.
- Saves PNG files to `<input>/figs/` by default when `--save` is used.

Notes
-----
- The script is intentionally conservative: it skips non-numeric and higher-than-2D variables.
- If `scipy` or `matplotlib` aren't installed, install them using the `requirements.txt` above.
# TTK4115-helicopter-lab