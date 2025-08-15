#merge/user_interface.py

"""
Purpose:
- Provides a GUI panel for merging text (or .DAT) files into a long-format DataFrame.
- Allows users to select a folder, trigger a background merge, and view results.
"""

import os
from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
    QFileDialog, QSizePolicy, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from merge.workers import MergeWorker

class MergePanel(QGroupBox):
    """
    Purpose:
     - Select a master folder containing sub-folders of text (or .DAT) files
     - Trigger a background merge process
     - Save and report results to /exports and send emit the filepath
    """
    merged_filepath = pyqtSignal(str) #Prepare emit string for sending final filepath to bin
    def __init__(self, parent=None):
        """
        Purpose:
        - Initialize the merge panel and build the UI.
        Args:
        - parent (QWidget, optional): Parent widget for the panel. Defaults to None.
        """
        super().__init__("1) Merge text (or .DAT) Files", parent)
        self.folder = None
        self.dataframe = None
        self.worker = None
        self._build_ui()
    def _build_ui(self):
        """
        Purpose:
        - Construct the user interface layout and widgets.
        """
        layout = QVBoxLayout(self)
        #Directions
        layout.addWidget(QLabel(
            "Select master folder containing sub-folders",
            self
        ))

        #Folder chooser
        h_folder = QHBoxLayout()
        self.folder_lbl = QLabel("No folder selected", self)
        self.folder_lbl.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )
        btn_browse = QPushButton("Browse…", self)
        btn_browse.clicked.connect(self._on_browse)
        h_folder.addWidget(self.folder_lbl)
        h_folder.addWidget(btn_browse)
        layout.addLayout(h_folder)

        #Merge button
        self.btn_merge = QPushButton("Submit", self)
        self.btn_merge.setEnabled(False) #Disable until folder path is loaded
        self.btn_merge.clicked.connect(self._on_merge)
        layout.addWidget(self.btn_merge)

        #Merge progress so user knows process is occurring
        h_progress = QHBoxLayout()
        self.merge_progress = QProgressBar(self)
        self.merge_progress.setRange(0, 0)
        self.merge_progress.setVisible(False)
        self.status_lbl = QLabel("", self)
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        h_progress.addWidget(self.merge_progress)
        h_progress.addWidget(self.status_lbl)
        layout.addLayout(h_progress)

    def _on_browse(self):
        """
        Purpose:
        - Open a dialog to select the master folder.
        - Update UI and enable merge button if folder is selected.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select master folder")
        if not folder:
            return

        self.folder = folder
        self.folder_lbl.setText(os.path.normpath(folder))
        self.btn_merge.setEnabled(True) #Enable merge button now that folder is loaded

    def _on_merge(self):
        """
        Purpose:
        - Start the merge worker and show progress bar.
        - Connect worker signals to appropriate handlers.
        """
        self.btn_merge.hide() #Hide button
        self.merge_progress.show() #Show progress so user sees the program is working
        export_dir = os.path.join(self.folder, "exports")
        os.makedirs(export_dir, exist_ok=True) #Make exports folder
        self.worker = MergeWorker(self.folder) #set worker and done/error functions
        self.worker.finished.connect(self._on_done)
        self.worker.errored.connect(self._on_error)
        self.worker.status.connect(self._on_status_update)
        self.worker.start() #kick off worker

    def _on_done(self, dataframe, out_path):
        """
        Purpose:
        - Called when worker finishes successfully.
        - Restores UI state, emits filepath, and shows completion message.
        Args:
        - dataframe (pd.DataFrame): The merged dataset.
        - out_path (str): File path where the Excel file was saved.
        """
        self.merge_progress.hide()
        self.btn_merge.show()
        self.status_lbl.clear()
        self.dataframe = dataframe

        display_path = os.path.normpath(out_path)
        self.merged_filepath.emit(display_path) #Emit the filepath for use in binning functionality

        QMessageBox.information(
            self,
            "Merge Complete",
            f"Merged {len(dataframe)} rows.\nSaved to:\n{display_path}"
        )

    def _on_error(self, msg):
        """
        Purpose:
        - Called when worker emits an error.
        - Restores UI state and shows a critical message box.
        Args:
        - msg (str): Error message returned from worker.
        """
        self.merge_progress.hide() #Hide progress
        self.btn_merge.show() #show button
        self.status_lbl.clear()
        QMessageBox.critical(self, "Merge Error", msg) #display returned error message from worker

    def _on_status_update(self, status):
        self.status_lbl.setText(status)