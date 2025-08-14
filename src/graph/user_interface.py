# graph/user_interface.py

"""
Purpose:
- Provides a GUI for selecting graph settings, rendering previews, and saving visualizations
- Includes panels for display and controls, and dialogs for dataset/column selection
"""

import os
import pandas as pd
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QProgressBar, QFileDialog, QMessageBox,
    QWidget, QComboBox, QListWidget, QListWidgetItem, QTabWidget,
    QDialog, QDialogButtonBox, QCheckBox
)
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt6.QtWebEngineWidgets import QWebEngineView
from numpy.ma.core import nonzero
from graph.workers import (GraphLoadWorker, PlotWorker,
                           SaveMultipleWorker, SaveMultiColumnWorker)

class DatasetSelectDialog(QDialog):
    """
    Purpose:
    - Dialog to select one or more datasets for export
    - Provides 'Select All' toggle and confirmation buttons
    """
    def __init__(self, parent, dataset_list: list[str]):
        super().__init__(parent)
        self.setWindowTitle("Select Datasets to Save")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        self.select_all = QCheckBox("Select All")
        self.select_all.setChecked(True)
        self.select_all.clicked.connect(self._toggle_all)
        layout.addWidget(self.select_all)

        self.checkboxes = []
        for name in dataset_list:
            cb = QCheckBox(name)
            cb.setChecked(True)
            self.checkboxes.append(cb)
            layout.addWidget(cb)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _toggle_all(self):
        checked = self.select_all.isChecked()
        for cb in self.checkboxes:
            cb.setChecked(checked)

    def get_selection(self) -> list[str]:
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]

class ColumnSelectDialog(QDialog):
    """
    Purpose:
    - Dialog to select one or more columns from a dataset
    - Provides 'Select All' toggle and confirmation buttons
    """
    def __init__(self, parent, column_list: list[str]):
        super().__init__(parent)
        self.setWindowTitle("Select Columns to Use")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        self.select_all = QCheckBox("Select All")
        self.select_all.setChecked(True)
        self.select_all.clicked.connect(self._toggle_all)
        layout.addWidget(self.select_all)

        self.checkboxes = []
        for name in column_list:
            cb = QCheckBox(name)
            cb.setChecked(True)
            self.checkboxes.append(cb)
            layout.addWidget(cb)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _toggle_all(self):
        checked = self.select_all.isChecked()
        for cb in self.checkboxes:
            cb.setChecked(checked)

    def get_selection(self) -> list[str]:
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]

class GraphSettingsPanel(QGroupBox):
    """
    Purpose:
     - Provide UI for graph setup via single-dataset and multi-dataset tabs
     - Collect user selections for datasets and columns
     - Trigger background PlotWorker for selected graphing mode
     - Emit plotReady with figure, HTML content, mode, and metadata
     - Optionally emit filedataReady with tabular data for export
    """

    plotReady = pyqtSignal(object, str, str, object)
    filedataReady = pyqtSignal(list, list, object, str)

    def __init__(self, parent=None):
        """
        Purpose:
        - Initializes the graph settings panel with state variables and child widgets.
        - Builds the user interface for single-dataset and multi-dataset plotting.
        - Prepares layout but defers file load and plot execution to user interactions.
        Args:
        - parent: Optional parent widget anchor (main window or layout).
        """
        super().__init__("3) Graph Settings", parent)
        self.graphing_dataframe = None
        self.loader = None
        self._plot_worker = None
        self.current_fig = None
        self.last_plot_type = None
        self._last_cols = None
        self._last_datasets = None
        self.graph_file = None
        self._build_ui()

    def _build_ui(self):
        """
        Purpose:
        - Constructs tabbed UI layout for single-dataset and multi-dataset plotting flows.
        - Includes input file selection, dataset/column pickers, progress indicators, and plot triggers.
        - Shared file selection controls update both tabs and funnel into the same load pipeline.
        """
        layout = QVBoxLayout(self)
        tabs = QTabWidget(self)
        layout.addWidget(tabs)

        # --- Tab 1: Single dataset ---
        tab1 = QWidget(self)
        dl = QVBoxLayout(tab1)

        dl.addWidget(QLabel("Select file for graph data:", tab1))
        h1 = QHBoxLayout()
        self.graph_file_lbl = QLabel("No file selected", tab1)
        self.graph_file_lbl.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        btn_browse_1 = QPushButton("Browse…", tab1)
        btn_browse_1.clicked.connect(self.graph_file_browse)
        h1.addWidget(self.graph_file_lbl)
        h1.addWidget(btn_browse_1)
        dl.addLayout(h1)

        self.graph_progress = QProgressBar(tab1)
        self.graph_progress.setRange(0, 0)
        self.graph_progress.setVisible(False)
        dl.addWidget(self.graph_progress)

        dl.addWidget(QLabel("Select Dataset:", tab1))
        self.dataset_combo = QComboBox(tab1)
        self.dataset_combo.setEnabled(False)
        dl.addWidget(self.dataset_combo)

        dl.addWidget(QLabel("Pick one or more columns to graph:", tab1))
        self.columns_list = QListWidget(tab1)
        self.columns_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        dl.addWidget(self.columns_list)

        self.plot_btn_1 = QPushButton("Submit", tab1)
        self.plot_btn_1.setEnabled(False) #disable at start (until file is loaded)
        self.plot_btn_1.clicked.connect(self.plot_sing_sub)
        dl.addWidget(self.plot_btn_1)

        self.plot1_progress = QProgressBar(tab1)
        self.plot1_progress.setRange(0, 0)
        self.plot1_progress.setVisible(False)
        dl.addWidget(self.plot1_progress)

        tabs.addTab(tab1, "Single dataset")

        # --- Tab 2: Multi dataset ---
        tab2 = QWidget(self)
        tl = QVBoxLayout(tab2)

        tl.addWidget(QLabel("Select file for graph data:", tab2))
        h2 = QHBoxLayout()
        self.graph_file2_lbl = QLabel("No file selected", tab2)
        self.graph_file2_lbl.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        btn_browse_2 = QPushButton("Browse…", tab2)
        btn_browse_2.clicked.connect(self.graph_file_browse)
        h2.addWidget(self.graph_file2_lbl)
        h2.addWidget(btn_browse_2)
        tl.addLayout(h2)

        self.graph2_progress = QProgressBar(tab2)
        self.graph2_progress.setRange(0, 0)
        self.graph2_progress.setVisible(False)
        tl.addWidget(self.graph2_progress)

        tl.addWidget(QLabel("Select Column to Plot:", tab2))
        self.column2_combo = QComboBox(tab2)
        self.column2_combo.setEnabled(False)
        tl.addWidget(self.column2_combo)

        tl.addWidget(QLabel("Pick one or more datasets to graph:", tab2))
        self.dataset2_list = QListWidget(tab2)
        self.dataset2_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        tl.addWidget(self.dataset2_list)

        self.plot_btn_2 = QPushButton("Submit", tab2)
        self.plot_btn_2.setEnabled(False) #disable at start (until file is loaded)
        self.plot_btn_2.clicked.connect(self.plot_mult_sub)
        tl.addWidget(self.plot_btn_2)

        self.plot2_progress = QProgressBar(tab2)
        self.plot2_progress.setRange(0, 0)
        self.plot2_progress.setVisible(False)
        tl.addWidget(self.plot2_progress)

        tabs.addTab(tab2, "Comparing Multiple Subjects")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

    def set_graph_file(self, path: str):
        """
        Purpose:
        - Sets the graph file path manually (via signal or external method call).
        - Updates both file labels, loads the file, and populates plot controls.
        - Emits filedataReady signal once data and metadata are available.
        Args:
        - path (str): Path to the file to use for plotting.
        """
        self.graph_file = path
        export_dir = os.path.dirname(self.graph_file)

        # Update labels with elided path
        fm = QFontMetrics(self.graph_file_lbl.font())
        w = self.graph_file_lbl.width() - 20
        elided = fm.elidedText(path, Qt.TextElideMode.ElideMiddle, w)
        self.graph_file_lbl.setText(elided)
        self.graph_file2_lbl.setText(elided)

        # Load the file
        try:
            df = pd.read_csv(path)
        except Exception as e:
            QMessageBox.critical(self, "Load Error", str(e))
            return

        # Populate UI widgets
        self.graphing_dataframe = df
        datasets = sorted(df["Dataset"].astype(str).unique())
        columns = [c for c in df.columns if c not in ("Time", "Dataset")]

        self.dataset_combo.clear()
        self.dataset_combo.addItems(datasets)
        self.dataset_combo.setEnabled(True)

        self.columns_list.clear()
        for col in columns:
            item = QListWidgetItem(col)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.columns_list.addItem(item)

        self.column2_combo.clear()
        self.column2_combo.addItems(columns)
        self.column2_combo.setEnabled(True)

        self.dataset2_list.clear()
        for ds in datasets:
            item = QListWidgetItem(ds)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.dataset2_list.addItem(item)

        # Emit signal
        self.filedataReady.emit(datasets, columns, df, export_dir)
        self.plot_btn_1.setEnabled(True) #enable buttons
        self.plot_btn_2.setEnabled(True)

    @pyqtSlot()
    def graph_file_browse(self):
        """
        Purpose:
        - Opens a file dialog for selecting the graph data file.
        - Updates file labels, shows progress, and starts GraphLoadWorker.
        - On success or error, flow continues to corresponding slot.
        """
        path, _ = QFileDialog.getOpenFileName(
            self, "Select File", "", "Data Files (*.csv *.xlsx *.xls);;All Files (*)"
        )
        if not path:
            return
        self.graph_file = path

        fm = QFontMetrics(self.graph_file_lbl.font())
        w = self.graph_file_lbl.width() - 20
        elided = fm.elidedText(path, Qt.TextElideMode.ElideMiddle, w)
        self.graph_file_lbl.setText(elided)
        self.graph_file2_lbl.setText(elided)

        self.graph_progress.setVisible(True)
        self.graph2_progress.setVisible(True)
        self.graph_file_lbl.parentWidget().findChild(QPushButton).setVisible(False)

        self.loader = GraphLoadWorker(path)
        self.loader.finished.connect(self.graph_file_loaded)
        self.loader.errored.connect(self.graph_file_load_error)
        self.loader.start()

    @pyqtSlot(object)
    def graph_file_loaded(self, df: pd.DataFrame):
        """
        Purpose:
        - Called when GraphLoadWorker finishes successfully.
        - Populates dataset and column controls in both tabs.
        - Emits filedataReady signal to notify downstream graph display logic.
        Args:
        - df (pd.DataFrame): Loaded DataFrame from graph file.
        """
        self.graph_progress.setVisible(False)
        self.graph2_progress.setVisible(False)
        self.graph_file_lbl.parentWidget().findChild(QPushButton).setVisible(True)

        self.graphing_dataframe = df
        datasets = sorted(df["Dataset"].astype(str).unique())
        columns = [c for c in df.columns if c not in ("Time", "Dataset")]

        self.dataset_combo.clear()
        self.dataset_combo.addItems(datasets)
        self.dataset_combo.setEnabled(True)

        self.columns_list.clear()
        for col in columns:
            item = QListWidgetItem(col)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.columns_list.addItem(item)

        self.column2_combo.clear()
        self.column2_combo.addItems(columns)
        self.column2_combo.setEnabled(True)

        self.dataset2_list.clear()
        for ds in datasets:
            item = QListWidgetItem(ds)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.dataset2_list.addItem(item)

        export_dir = os.path.dirname(self.graph_file)
        self.filedataReady.emit(datasets, columns, df, export_dir)
        self.plot_btn_1.setEnabled(True) #enable buttons
        self.plot_btn_2.setEnabled(True)

    @pyqtSlot(str)
    def graph_file_load_error(self, msg: str):
        """
        Purpose:
        - Handles error during graph file loading.
        - Restores UI to usable state and displays error dialog.
        Args:
        - msg (str): Error message returned from worker.
        """
        self.graph_progress.setVisible(False)
        self.graph2_progress.setVisible(False)
        self.graph_file_lbl.parentWidget().findChild(QPushButton).setVisible(True)
        QMessageBox.critical(self, "Load Error", msg)

    @pyqtSlot()
    def plot_sing_sub(self):
        """
        Purpose:
        - Collects the selected dataset and column(s) from the single-dataset tab.
        - Validates input and spawns a background PlotWorker with mode 'single'.
        - Disables UI controls and shows progress until plotting is complete.
        """
        ds = self.dataset_combo.currentText()

        cols = [
            self.columns_list.item(i).text()
            for i in range(self.columns_list.count())
            if self.columns_list.item(i).checkState() == Qt.CheckState.Checked
        ]

        if not cols:
            QMessageBox.warning(self, "No Selection", "Pick at least one series.")
            return
        self._last_cols = cols

        self.plot1_progress.setVisible(True)
        self.plot_btn_1.setVisible(False)

        worker = PlotWorker("single", ds, cols, self.graphing_dataframe)
        worker.finished.connect(self.on_plot_sing_done)
        worker.errored.connect(self.on_plot_error)
        worker.start()
        self._plot_worker = worker

    @pyqtSlot()
    def plot_mult_sub(self):
        """
        Purpose:
        - Collects the selected column and dataset(s) from the multi-dataset tab.
        - Validates input and spawns a background PlotWorker with mode 'multi'.
        - Disables UI controls and shows progress until plotting is complete.
        """
        col = self.column2_combo.currentText()

        datasets = [
            self.dataset2_list.item(i).text()
            for i in range(self.dataset2_list.count())
            if self.dataset2_list.item(i).checkState() == Qt.CheckState.Checked
        ]

        if not datasets:
            QMessageBox.warning(self, "No Selection", "Pick at least one dataset.")
            return
        self._last_datasets = datasets

        self.plot2_progress.setVisible(True)
        self.plot_btn_2.setVisible(False)

        worker = PlotWorker("multi", col, datasets, self.graphing_dataframe)
        worker.finished.connect(self.on_plot_mult_done)
        worker.errored.connect(self.on_plot_error)
        worker.start()
        self._plot_worker = worker

    @pyqtSlot(object, str)
    def on_plot_sing_done(self, fig, html):
        """
        Purpose:
        - Receives figure and HTML output from PlotWorker (single-dataset mode).
        - Stores result internally and emits plotReady signal for display.
        - Restores UI controls after successful plot.
        Args:
        - fig: Generated Plotly figure object.
        - html: HTML string to render inside the web view.
        """
        self.current_fig = fig
        self.last_plot_type = "single"
        cols = self._last_cols
        self.plotReady.emit(fig, html, "single", cols)
        self.plot1_progress.setVisible(False)
        self.plot_btn_1.setVisible(True)

    @pyqtSlot(object, str)
    def on_plot_mult_done(self, fig, html):
        """
        Purpose:
        - Receives figure and HTML output from PlotWorker (multi-dataset mode).
        - Stores result internally and emits plotReady signal for display.
        - Restores UI controls after successful plot.
        Args:
        - fig: Generated Plotly figure object.
        - html: HTML string to render inside the web view.
        """
        self.current_fig = fig
        self.last_plot_type = "multi"
        datasets = self._last_datasets  # Ensure this is set in plot_mult_sub
        self.plotReady.emit(fig, html, "multi", datasets)

        self.plot2_progress.setVisible(False)
        self.plot_btn_2.setVisible(True)

    @pyqtSlot(str)
    def on_plot_error(self, msg: str):
        """
        Purpose:
        - Handles any error emitted by a PlotWorker.
        - Re-enables both plot buttons and hides progress indicators.
        - Displays an error dialog with the provided message.
        Args:
        - msg (str): Error message string from worker.
        """
        QMessageBox.critical(self, "Plot Error", msg)
        self.plot1_progress.setVisible(False)
        self.plot_btn_1.setVisible(True)
        self.plot2_progress.setVisible(False)
        self.plot_btn_2.setVisible(True)

class GraphDisplayPanel(QGroupBox):
    """
    Purpose:
    - Provides a UI panel for viewing interactive Plotly graphs inside the app.
    - Includes buttons for saving the current graph or batch-generating graphs based on last plot type.
    - Handles dataset/column selection dialogs and dispatches background save workers.
    Attributes:
    - current_fig (go.Figure): Last plotted figure.
    - last_plot_type (str): 'single' or 'multi', used to determine save logic.
    - graphing_dataframe (pd.DataFrame): Full DataFrame currently used for graphing.
    - cols (list[str]): Column list used if last plot type was 'single'.
    - datasets (list[str]): Dataset list used if last plot type was 'multi'.
    - _save_worker (QThread): Active background thread for saving graphs.
   """

    def __init__(self, parent=None):
        """
        Purpose:
        - Initializes the Graph Display panel with buttons, view area, and internal state.
        - Immediately builds the UI structure and resets graph-related attributes.
        Args:
        - parent: Optional parent widget (usually main window or layout anchor).
        """
        super().__init__("Graph Display", parent)
        self.current_fig = None
        self.last_plot_type = None
        self._save_worker = None
        self.cols = None
        self.datasets = None
        self.graphing_dataframe = None
        self._dataset_names = None
        self._column_names = None
        self.export_dir = None
        self._build_ui()

    def _build_ui(self):
        """
        Purpose:
        - Constructs the layout for the display panel, including:
          - Graph rendering area (QWebEngineView).
          - Button row for saving current or multiple graphs.
        - Connects button signals to their respective slots.
        """
        layout = QVBoxLayout(self)

        self.web_view = QWebEngineView(self)
        self.web_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        layout.addWidget(self.web_view)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.save_sing_btn = QPushButton("Save Example Graph", self)
        self.save_sing_btn.setFixedSize(200, 24)
        self.save_sing_btn.clicked.connect(self.on_save_ex)
        btn_layout.addWidget(self.save_sing_btn)

        self.save_mult_btn = QPushButton("Save multiple graphs", self)
        self.save_mult_btn.setFixedSize(200, 24)
        self.save_mult_btn.clicked.connect(self.save_based_on_last_plot)
        btn_layout.addWidget(self.save_mult_btn)

        layout.addLayout(btn_layout)

    @pyqtSlot(object, str, str, object)
    def update_plot(self, fig, html, mode, graph_list):
        """
        Purpose:
        - Receives a newly generated Plotly figure and HTML for display.
        - Sets internal tracking variables to inform future save logic.
        Args:
        - fig: Plotly figure object to store and optionally save later.
        - html: Raw HTML string to display in the web view.
        - mode (str): Either 'single' or 'multi'; used to set save logic.
        - graph_list (list[str]): Column or dataset list depending on mode.
        """
        self.current_fig = fig
        self.last_plot_type = mode
        self.web_view.setHtml(html)
        if mode == "single":
            self.cols = graph_list
            self.datasets = None
        else:
            self.cols = None
            self.datasets = graph_list

    @pyqtSlot(list, list, object, str)
    def receive_file_data(self, dataset_list: list[str], column_list: list[str], df: pd.DataFrame, export_dir: str):
        """
        Purpose:
        - Stores the dataset names, column names, and full DataFrame for graphing and export.
        - Called after a graph file is loaded.
        Args:
        - dataset_list: List of dataset identifiers found in file.
        - column_list: List of column headers available for graphing.
        - df: Full DataFrame loaded from the file.
        """
        self._dataset_names = dataset_list
        self._column_names = column_list
        self.graphing_dataframe = df
        self.export_dir = export_dir

    @pyqtSlot()
    def on_save_ex(self):
        fig = self.current_fig
        if not fig:
            QMessageBox.warning(self, "No Graph", "Load & plot first.")
            return

        default_name = getattr(fig, "_filename", "plot.html")
        export_dir = self.export_dir
        if not export_dir:
            QMessageBox.critical(self, "Save Error", "No export directory set.")
            return

        path = os.path.join(export_dir, default_name)
        if not path.lower().endswith(".html"):
            path += ".html"

        try:
            fig.write_html(path)
            # Normalize for display purposes
            display_path = path.replace("\\", "/")
            QMessageBox.information(self, "Saved", f"Saved to:\n{display_path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    @pyqtSlot(list)
    def on_save_mult(self, selection: list[str]):
        """
        Purpose:
        - Dispatches background worker to save multiple graphs depending on current plot mode.
        - Uses selection from dialog (either datasets or columns).
        - Validates required state and launches worker accordingly.
        Args:
        - selection: List of user-selected datasets or columns to export.
        """
        mode = getattr(self, "last_plot_type", None)
        if mode == "single":
            out_dir = self.export_dir
            if not out_dir:
                return

            cols = self.cols or []
            if not cols:
                QMessageBox.critical(self, "Save Error", "Missing Y-axes list. Save aborted.")
                return

            self._save_worker = SaveMultipleWorker(
                datasets=selection,
                y_axes=cols,
                df=self.graphing_dataframe,
                out_dir=out_dir
            )
            self._save_worker.finished.connect(self.on_save_mult_done)
            self._save_worker.errored.connect(self.on_save_error)
            self._save_worker.start()

        if mode == "multi":
            out_dir = self.export_dir
            if not out_dir:
                return

            datasets = self.datasets or []
            if not datasets:
                QMessageBox.critical(self, "Save Error", "Missing Datasets list. Save aborted.")
                return

            self._save_worker = SaveMultiColumnWorker(
                datasets=datasets,
                columns=selection,
                df=self.graphing_dataframe,
                out_dir=out_dir
            )
            self._save_worker.finished.connect(self.on_save_mult_done)
            self._save_worker.errored.connect(self.on_save_error)
            self._save_worker.start()

    @pyqtSlot(list, str)
    def on_save_mult_done(self, saved_paths: list[str], out_dir: str):
        """
        Purpose:
        - Called when background save worker finishes.
        - Displays confirmation dialog with number of files saved.
        Args:
        - saved_paths: List of saved file paths.
        - out_dir: Folder where files were written.
        """
        QMessageBox.information(
            self, "Save Complete", f"Written {len(saved_paths)} files to:\n{out_dir}"
        )

    @pyqtSlot(str)
    def on_save_error(self, msg: str):
        """
        Purpose:
        - Displays an error message when background save worker fails.
        Args:
        - msg: Error message string from worker.
        """
        QMessageBox.critical(self, "Save Error", msg)

    @pyqtSlot()
    def save_based_on_last_plot(self):
        """
        Purpose:
        - Determines which selection dialog to launch based on last plot type.
        - Calls `dataset_list_gen()` or `col_list_gen()` accordingly.
        """
        mode = getattr(self, "last_plot_type", None)

        if mode == "single":
            self.dataset_list_gen()
        elif mode == "multi":
            self.col_list_gen()
        else:
            QMessageBox.warning(self, "Nothing to Save", "No plot has been generated yet.")

    @pyqtSlot()
    def dataset_list_gen(self):
        """
        Purpose:
        - Launches dialog for user to select which datasets to export.
        - Passes result to `on_save_mult()` if selection was made.
        - Shows warning if no datasets are available.
        """
        ds_names = getattr(self, "_dataset_names", None)
        if not ds_names:
            QMessageBox.warning(self, "No Data", "No datasets available. Load a file first.")
            return

        dlg = DatasetSelectDialog(self, ds_names)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            sel = dlg.get_selection()
            if sel:
                self.on_save_mult(sel)
            else:
                QMessageBox.information(self, "Nothing Selected", "No datasets selected.")

    @pyqtSlot()
    def col_list_gen(self):
        """
        Purpose:
        - Launches dialog for user to select which columns to export across datasets.
        - Passes result to `on_save_mult()` if selection was made.
        - Shows warning if no columns are available.
        """
        col_names = getattr(self, "_column_names", None)

        if not col_names:
            QMessageBox.warning(self, "No Data", "No columns available. Load a file first.")
            return

        dlg = ColumnSelectDialog(self, col_names)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            sel = dlg.get_selection()

            if sel:
                self.on_save_mult(sel)
            else:
                QMessageBox.information(self, "Nothing Selected", "No datasets selected.")