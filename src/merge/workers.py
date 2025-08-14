#merge/workers.py

"""
Purpose:
- Worker script that uses merge/helpers.py to merge dataframes into a single long-format dataset.
"""

import os
import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal
from merge.helpers import run_merge_script


class MergeWorker(QThread):
    """
    Purpose:
    - Background thread responsible for executing the merge logic.
    - Emits a DataFrame and output path on success, or an error message on failure.
    """

    finished = pyqtSignal(pd.DataFrame, str)  #Fired when merge completes successfully
    errored  = pyqtSignal(str)                       #Fired if merge fails
    status = pyqtSignal(str)             #Emits status messages to the GUI

    def __init__(self, folder: str, export_dir: str = None):
        """
        Purpose:
        - Initializes the worker with folder and export path.

        Args:
        - folder (str): Master directory to scan for subfolders containing .DAT files.
        - export_dir (str, optional): Directory to save final csv output. Defaults to <folder>/exports.
        """
        super().__init__()
        self.folder = folder
        self.export_dir = export_dir or os.path.join(self.folder, "exports") #Default export path is <folder>/exports if not provided
        os.makedirs(self.export_dir, exist_ok=True)

    def run(self):
        """
        Purpose:
        - Executes the merge logic in a background thread.
        - Saves the result to csv and emits success or error signals.
        """
        try:
            df = run_merge_script(self.folder, status_callback=self.status.emit) #Run the user-defined merge logic (returns a DataFrame)

            if df is None:
                raise RuntimeError("No data merged; check your data folder.")

            filename = "merged_data.csv" #Save final csv to exports folder
            out_path = os.path.join(self.export_dir, filename)
            df.to_csv(out_path, index=False)

            self.finished.emit(df, out_path) #Notify main thread of success

        except Exception as e:
            self.errored.emit(str(e)) #Bubble up error message to UI