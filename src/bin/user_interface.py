# bin/user_interface.py

"""
Purpose:
- Provides a GUI panel for binning a long-format DataFrame into user-specified intervals.
- Allows user to select a file, define time bounds, and configure binning parameters.
- Emits the final binned file path for downstream use.
Works with:
- bin/workers.py
- bin/helpers.py
"""

import os
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QSizePolicy,
    QCheckBox, QDateEdit, QTimeEdit, QButtonGroup, QRadioButton, QSpinBox,
    QFileDialog, QMessageBox, QProgressBar
)
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from bin.workers import BinningWorker

class BinningPanel(QGroupBox):
    """
    Purpose:
    - GUI panel for configuring and executing binning on a merged dataset.
    - Allows user to select a file, define start/end bounds, and choose binning interval.
    - Emits the final binned file path to downstream components (e.g. graphing).
    """

    binned_filepath = pyqtSignal(str)  #Fired when binning completes successfully; emits final file path

    def __init__(self, parent=None):
        """
        Purpose:
        - Initializes the binning panel UI and internal state.
        Args:
        - parent (QWidget, optional): Parent widget for layout hierarchy.
        """
        super().__init__("2) Configure Binning", parent)
        self.bin_file = None  #Path to selected file for binning
        self.binning_worker = None  #Worker thread for binning process
        self.loader = None  #Optional graph loader (used downstream)
        self._build_ui()  #Construct UI elements
        self._toggle_entries()  #Set initial enabled/disabled state for time controls

    def _build_ui(self):
        """
        Purpose:
        - Constructs the full binning panel layout.
        - Includes file selection, time range controls, binning interval configuration, and submit/progress widgets.
        """
        layout = QVBoxLayout(self)

        h_file = QHBoxLayout()
        self.bin_file_lbl = QLabel("No file selected", self) #set bin label and show no file loaded
        self.bin_file_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        btn_browse = QPushButton("Browse…", self) #browse button
        btn_browse.clicked.connect(self._bin_file_browse) #wire to function for browsing
        h_file.addWidget(self.bin_file_lbl)
        h_file.addWidget(btn_browse)
        layout.addLayout(h_file)

        self.bounded_cb = QCheckBox("Time already trimmed", self) #Toggle for need to set start/end times
        self.bounded_cb.stateChanged.connect(self._toggle_entries) #wire to function
        layout.addWidget(self.bounded_cb)

        # Start/End controls
        h_se = QHBoxLayout()
        layout.addLayout(h_se)

        #Start group
        self.start_gb = QGroupBox("Start", self)
        v_start = QVBoxLayout(self.start_gb)
        self.start_date = QDateEdit(parent=self.start_gb)
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())
        v_start.addWidget(self.start_date)
        self.start_time = QTimeEdit(parent=self.start_gb)
        self.start_time.setDisplayFormat("hh:mm")
        self.start_time.setTime(self.start_time.time().fromString("00:00", "hh:mm"))
        v_start.addWidget(self.start_time)
        self.start_am = QRadioButton("AM", self.start_gb)
        self.start_pm = QRadioButton("PM", self.start_gb)
        self.start_am.setChecked(True)
        grp1 = QButtonGroup(self.start_gb)
        grp1.addButton(self.start_am)
        grp1.addButton(self.start_pm)
        h1 = QHBoxLayout()
        h1.addWidget(self.start_am)
        h1.addWidget(self.start_pm)
        v_start.addLayout(h1)
        h_se.addWidget(self.start_gb)

        #End group
        self.end_gb = QGroupBox("End", self)
        v_end = QVBoxLayout(self.end_gb)
        self.end_date = QDateEdit(parent=self.end_gb)
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        v_end.addWidget(self.end_date)
        self.end_time = QTimeEdit(parent=self.end_gb)
        self.end_time.setDisplayFormat("hh:mm")
        self.end_time.setTime(self.end_time.time().fromString("00:00", "hh:mm"))
        v_end.addWidget(self.end_time)
        self.end_am = QRadioButton("AM", self.end_gb)
        self.end_pm = QRadioButton("PM", self.end_gb)
        self.end_am.setChecked(True)
        grp2 = QButtonGroup(self.end_gb)
        grp2.addButton(self.end_am)
        grp2.addButton(self.end_pm)
        h2 = QHBoxLayout()
        h2.addWidget(self.end_am)
        h2.addWidget(self.end_pm)
        v_end.addLayout(h2)
        h_se.addWidget(self.end_gb)

        #Binterval
        bin_box = QGroupBox("Binning Interval", self)
        h_bin = QHBoxLayout(bin_box)
        self.bin_val = QSpinBox(bin_box)
        self.bin_val.setRange(1, 1000)
        self.bin_val.setValue(15)
        h_bin.addWidget(self.bin_val)
        self.rb_min = QRadioButton("minutes", bin_box)
        self.rb_hr  = QRadioButton("hours",   bin_box)
        self.rb_day = QRadioButton("days",    bin_box)
        self.rb_min.setChecked(True)
        units = QButtonGroup(bin_box)
        for rb in (self.rb_min, self.rb_hr, self.rb_day):
            units.addButton(rb)
            h_bin.addWidget(rb)
        layout.addWidget(bin_box)

        #Submit + spinner
        self.btn_bin = QPushButton("Submit", self) #submit button
        self.btn_bin.setEnabled(False) #disable at start (until file is loaded)
        self.btn_bin.clicked.connect(self._bin_start)
        layout.addWidget(self.btn_bin)

        h_progress = QHBoxLayout()
        self.bin_progress = QProgressBar(self)
        self.bin_progress.setRange(0, 0)
        self.bin_progress.setVisible(False)
        self.bin_progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.status_lbl = QLabel("", self)
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        h_progress.addWidget(self.bin_progress)
        h_progress.addWidget(self.status_lbl)
        layout.addLayout(h_progress)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

    def _toggle_entries(self):
        """
        Purpose:
        - Enables or disables the start/end time controls based on whether time trimming is selected.
        """
        enable = not self.bounded_cb.isChecked()
        for widget in (
                self.start_date, self.start_time,
                self.start_am,   self.start_pm,
                self.end_date,   self.end_time,
                self.end_am,     self.end_pm
        ):
            widget.setEnabled(enable)

    def set_bin_file(self, path: str):
        """
        Purpose:
        - Sets the file path for binning, updates the UI label, and enables the submit button.
        """
        self.bin_file = path #Load path
        fm = QFontMetrics(self.bin_file_lbl.font())
        elided = fm.elidedText(path, Qt.TextElideMode.ElideMiddle, self.bin_file_lbl.width() - 20)
        self.bin_file_lbl.setText(elided) #Show text for filepath and elide longer paths
        self.btn_bin.setEnabled(True) #Enable button once dataset is loaded

    def _bin_file_browse(self):
        """
        Purpose:
        - Opens a file dialog for selecting a merged dataset to bin.
        - Updates the file label and enables the submit button.
        """
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select merged file",
            "",
            "Data Files (*.csv *.xlsx *.xls);;All Files (*)"
        )
        if not path:
            return

        self.bin_file = path #set path
        fm = QFontMetrics(self.bin_file_lbl.font())
        elided = fm.elidedText(path, Qt.TextElideMode.ElideMiddle, self.bin_file_lbl.width() - 20)
        self.bin_file_lbl.setText(elided) #Show text for filepath and elide longer paths
        self.btn_bin.setEnabled(True) #Enable button once dataset is loaded

    def _bin_start(self):
        """
        Purpose:
        - Initializes and starts the binning worker with user-defined parameters.
        - Hides the submit button and shows the progress bar.
        """
        if not self.bin_file: #Ensure file exists
            QMessageBox.warning(self, "No File", "Please select a merged file first.")
            return

        self.btn_bin.hide() #hide button
        self.bin_progress.show() #show progress

        unit = (
            "minutes" if self.rb_min.isChecked() else
            "hours"   if self.rb_hr.isChecked()  else
            "days"
        )
        interval = f"{self.bin_val.value()} {unit}" #set interval using integer and units

        self.binning_worker = BinningWorker( #set bin worker
            file_path=self.bin_file,
            interval=interval,
            already_trimmed=self.bounded_cb.isChecked(),
            start_date=self.start_date.date(),
            start_time=self.start_time.time(),
            start_pm=self.start_pm.isChecked(),
            end_date=self.end_date.date(),
            end_time=self.end_time.time(),
            end_pm=self.end_pm.isChecked()
        )
        self.binning_worker.finished.connect( #set up worker done function
            lambda out_df: self._bin_done(out_df, interval)
        )
        self.binning_worker.errored.connect(self._bin_error)  #set up worker error function
        self.binning_worker.status.connect(self._on_status_update)
        self.binning_worker.start()

    def _bin_done(self, out_df, interval):
        """
        Purpose:
        - Handles successful completion of the binning worker.
        - Saves the output to Excel, emits the file path, and shows a success message.
        """
        self.bin_progress.hide() #hide progress bar
        self.btn_bin.show() #reshow button
        self.status_lbl.clear()

        try:
            export_dir = os.path.dirname(self.bin_file)
            os.makedirs(export_dir, exist_ok=True)
            file_name = f"binned_{interval.replace(' ', '_')}.csv" #generate file name
            display_path = os.path.normpath(os.path.join(export_dir, file_name)) #generate filepath
            out_df.to_csv(display_path, index=False) #Save filepath
            self.binned_filepath.emit(display_path)

            QMessageBox.information(
                self, "Binning Complete",
                f"Binned into {interval} ({len(out_df)} rows).\nSaved to:\n{display_path}"
            )
        except Exception as e:
            print(f"[BinningPanel._bin_done] export/UI error: {e}")
            return

    def _bin_error(self, msg):
        """
        Purpose:
        - Handles errors emitted by the binning worker.
        - Restores UI state and displays an error message to the user.
        """
        self.bin_progress.hide() #hide progress
        self.btn_bin.show() #show button
        self.status_lbl.clear()
        QMessageBox.critical(self, "Binning Error", msg) #show error

    def _on_status_update(self, status):
        self.status_lbl.setText(status)