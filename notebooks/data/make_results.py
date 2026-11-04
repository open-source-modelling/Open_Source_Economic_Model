"""
Run OSEM on the notebook inputs and save its Results.csv in notebooks/data/Output, for
summary_charts.ipynb. Run it after changing a file in notebooks/data/Input:

    python notebooks/data/make_results.py
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

data_folder = Path(__file__).resolve().parent
repo_root = data_folder.parents[1]

# The module loggers write to the Logs folder of the working directory when they are imported
os.chdir(repo_root)
sys.path.insert(0, str(repo_root / "src"))

from osem.main import main  # noqa: E402

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as run_folder:
    # main reads ALM.ini from the working directory, and the notebook files name each other
    # relative to the repository root, so the run gets a copy of that layout
    run_data = Path(run_folder) / "notebooks" / "data"
    shutil.copytree(data_folder / "Input", run_data / "Input")
    (run_data / "Output").mkdir()
    shutil.copy(data_folder / "notebooks.ini", Path(run_folder) / "ALM.ini")

    os.chdir(run_folder)
    try:
        main()
    finally:
        os.chdir(repo_root)

    (data_folder / "Output").mkdir(exist_ok=True)
    shutil.copy(run_data / "Output" / "Results.csv", data_folder / "Output" / "Results.csv")

print(f"Saved {data_folder / 'Output' / 'Results.csv'}")
