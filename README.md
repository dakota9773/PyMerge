# PyMerge

## Purpose

**PyMerge** is a standalone Windows application for merging, binning, and graphing data from the [MCCI Catena 4430 Animal Activity Sensor](https://github.com/mcci-catena/Catena4430_Sensor). It is designed for users with minimal programming experience and can be used alongside more advanced analysis software.
## System Compatibility & Setup
PyMerge is distributed as a standalone executable for Windows 10 or 11 (64-bit). No installation or Python setup is required.

To launch:
1. Download `PyMerge.exe`
2. Double-click to run
## Installation
No external installation required. Simply download and run `PyMerge.exe`.
## File Structure
The PyMerge repository includes both the standalone executable and development resources:
- `PyMerge.exe`: Ready-to-run executable
- `examples/`: Sample input and output files
- `src/`: Python source code for development
- `tests/`:  Python Validation scripts
- `.idea/`, `.venv/`: Development environment metadata (can be ignored by end users)
- `README.md`: This file
- `LICENSE`: Licensing terms for reuse and citation
## Code Overview
PyMerge operates in three sequential modules: **Merge**, **Bin**, and **Graph**.
### Merge
- User selects a parent directory containing subfolders of CSV-style files.
- The software scans each subfolder (excluding `/exports`) and merges all readable files into a single long-format `pandas` DataFrame.
- A `Dataset` column is added to track subfolder origin.
- Output is saved to `/directory/exports/merged_data.csv`; the `exports` folder is created if missing.
### Bin
- Users select a merged file if it isn't uploaded from a previous merge and define a binning interval.
- Activity columns (`Act[0]`–`Act[5]`) are expanded into minute-level records.
- Other variables (`T`, `Light`, `Vbat`) are preserved.
- Data is grouped by `Dataset` and floored to time intervals, then aggregated using preset rules.
- Activity is scaled to percent via a weighted formula.
- Output is saved to `/directory/exports/binned_interval.csv`.
### Graph
- Two workflows: **Single Dataset** and **Multiple Dataset**.
- Users select datasets and columns to visualize.
- Interactive Plotly graphs are generated and previewed in the GUI.
- Outputs are saved as HTML:
  - `/directory/exports/dataset_columns.html` for single-dataset graphs
  - `/directory/exports/column_datasets.html` for multi-dataset comparisons
## Example Data
Sample input and output files are available in the `examples/` folder to demonstrate expected input formats and results.
## License
To be determined after meeting with the group.
## More information
Some browsers will flag the executable file (PyMerge.exe) as unsafe because it is not widely used or known. Please follow your browser's directions for marking the download as safe. 

