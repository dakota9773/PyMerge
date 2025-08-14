# graph/workers.py

"""
Purpose:
- Defines background worker threads for loading data and generating Plotly visualizations.
- Handles single-dataset plotting, multi-dataset comparisons, and batch saving of graphs.
- Uses PyQt6 threads to avoid blocking the GUI during heavy operations.
"""

import os, time
import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal
from graph.helpers import sing_sub_plot, mult_sub_plot, wrap_html

class GraphLoadWorker(QThread):
    """
    Purpose:
    - Loads an Excel spreadsheet from a given path on a separate thread.
    - Emits the resulting DataFrame or an error message to the GUI.
    Args:
    - path (str): File path to the Excel document to load.
    Signals:
    - finished (pd.DataFrame): Emitted when the file is successfully loaded.
    - errored (str): Emitted with error message if file load fails.
    """
    finished = pyqtSignal(pd.DataFrame)
    errored  = pyqtSignal(str)

    def __init__(self, path: str):
        super().__init__()
        self.path = path

    def run(self):
        try:
            df = pd.read_csv(self.path, na_filter=False)
            print(df.dtypes)
            self.finished.emit(df)
        except Exception as e:
            self.errored.emit(str(e))

class PlotWorker(QThread):
    """
    Purpose:
    - Generates a Plotly graph from a DataFrame based on user selection.
    - Handles both 'single' (multi-column within one dataset) and 'multi' (one column across datasets) modes.
    - Emits both the figure and wrapped HTML output for display or export.
    Args:
    - mode (str): Either 'single' or 'multi', determines plotting logic.
    - key (str): Dataset name (if 'single') or column name (if 'multi').
    - items (list[str]): List of columns or datasets depending on mode.
    - df (pd.DataFrame): Source DataFrame containing data to plot.
    Signals:
    - finished (tuple): Emits (go.Figure, wrapped HTML string) upon success.
    - errored (str): Emits error message if plotting fails.
    """
    finished = pyqtSignal(object, str)   # emits (fig, wrapped_html)
    errored  = pyqtSignal(str)

    def __init__(self, mode: str, key: str, items: list[str], df):
        super().__init__()
        self.mode = mode
        self._df  = df.copy()

        if mode == "single":
            self.dataset = key              # name of the single dataset
            self.y_axes  = items            # list[str] of columns to plot
        else:
            self.column   = key             # the column to plot on Y-axis
            self.datasets = items           # list[str] of dataset names

    def run(self):
        try:
            # give the UI spinner a moment
            time.sleep(0.5)

            if self.mode == "single":
                sub = self._df[self._df["Dataset"] == self.dataset]
                x_axis = "Time" if "Time" in sub.columns else sub.columns[0]
                fig = sing_sub_plot(sub, x_axis, self.y_axes, title_text=self.dataset)

            else:  # multi‐subject
                # we can pass the full DataFrame to the helper; it'll filter per‐ds internally
                x_axis = "Time" if "Time" in self._df.columns else self._df.columns[0]
                fig = mult_sub_plot(self._df, x_axis, self.column, self.datasets)

            # wrap into full HTML page
            inner = fig.to_html(include_plotlyjs="cdn", full_html=False)
            html  = wrap_html(inner)

            # hand back to GUI thread
            self.finished.emit(fig, html)

        except Exception as e:
            self.errored.emit(str(e))

class SaveMultipleWorker(QThread):
    """
    Purpose:
    - Saves individual multi-column plots for each selected dataset.
    - Uses `sing_sub_plot()` from graph/helpers.py to generate each figure.
    - Writes each plot as a standalone HTML file with auto-sizing applied.
    Args:
    - datasets (list[str]): List of dataset labels to plot individually.
    - y_axes (list[str]): Columns to visualize for each dataset.
    - df (pd.DataFrame): Full dataset to slice per subject.
    - out_dir (str): Directory to save HTML output files.
    Signals:
    - finished (tuple): Emits ([saved file paths], output directory) on success.
    - errored (str): Emits error message on failure.
    """
    # emits (list_of_paths, output_dir)
    finished = pyqtSignal(list, str)
    errored  = pyqtSignal(str)

    def __init__(self, datasets: list[str], y_axes: list[str], df, out_dir: str):
        super().__init__()
        self.datasets = datasets
        self.y_axes   = y_axes
        self._df      = df.copy()
        self.out_dir  = out_dir

    def run(self):
        import time, os

        try:
            time.sleep(0.5)
            saved = []

            for ds in self.datasets:
                # 1) filter down
                sub = self._df[self._df["Dataset"] == ds]
                # 2) pick X-axis
                x_axis = "Time" if "Time" in sub.columns else sub.columns[0]

                # 3) build figure (this also sets fig._filename)
                fig = sing_sub_plot(sub, x_axis, self.y_axes, title_text=ds)

                # 4) auto-size & margin
                fig.update_layout(
                    autosize=True,
                    height=200 * len(self.y_axes) + 100,
                    margin=dict(l=200, r=20, t=40, b=40)
                )

                # 5) write out HTML using the same name sing_sub_plot created
                default_name = getattr(fig, "_filename", f"{ds}.html")
                out_path     = os.path.join(self.out_dir, default_name)
                fig.write_html(out_path, include_plotlyjs="cdn", full_html=True)
                saved.append(out_path)

            self.finished.emit(saved, self.out_dir)

        except Exception as e:
            self.errored.emit(str(e))

class SaveMultiColumnWorker(QThread):
    """
    Purpose:
    - Saves cross-dataset plots for each selected column.
    - Uses `mult_sub_plot()` to show how each column varies across datasets.
    - Wraps each figure in a scrollable HTML shell and writes to disk.
    Args:
    - datasets (list[str]): List of datasets to include in each subplot.
    - columns (list[str]): Columns to plot one at a time.
    - df (pd.DataFrame): Full dataset, assumed to contain all columns and 'Dataset' tag.
    - out_dir (str): Directory to save the resulting HTML files.
    Signals:
    - finished (tuple): Emits ([saved file paths], output directory) on success.
    - errored (str): Emits error string on failure.
    """
    finished = pyqtSignal(list, str)   # (saved_paths, out_dir)
    errored  = pyqtSignal(str)

    def __init__(self,
                 datasets: list[str],  # list of dataset names
                 columns:  list[str],  # list of columns to plot
                 df,                   # full DataFrame loaded via graph_file_loaded
                 out_dir:  str):
        super().__init__()
        self.datasets = datasets
        self.columns  = columns
        self._df      = df.copy()
        self.out_dir  = out_dir

    def run(self):
        saved = []
        try:
            time.sleep(0.2)

            # pick X-axis just once
            x_axis = "Time" if "Time" in self._df.columns else self._df.columns[0]

            for col in self.columns:
                fig = mult_sub_plot(
                    self._df,
                    x_axis=x_axis,
                    column=col,
                    selected_ds=self.datasets
                )

                # auto-size & wrap
                fig.update_layout(
                    autosize=True,
                    width=1000,
                    height=200 * (len(self.datasets) + 1) + 100,
                    margin=dict(l=200, r=20, t=50, b=40)
                )
                inner = fig.to_html(include_plotlyjs="cdn", full_html=False)
                html  = wrap_html(inner)

                # get filename that mult_sub_plot set on fig
                filename = getattr(fig, "_filename", f"{col}.html")
                out_path = os.path.join(self.out_dir, filename)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(html)

                saved.append(out_path)

            self.finished.emit(saved, self.out_dir)

        except Exception as e:
            self.errored.emit(str(e))