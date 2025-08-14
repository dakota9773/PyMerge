#bin/workers.py

"""
Purpose:
- Worker script that uses bin/helpers.py to bin a long-format dataset into user-specified intervals.
- Optionally trims the dataset by start/end time range.
Works with:
- bin/user_interface.py
- bin/helpers.py
"""

import os
import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal, QDate, QTime
from bin.helpers import melt_then_bin
from config import (TIME_COLUMN, SELECTED_COLUMNS)


class BinningWorker(QThread):
    """
    Purpose:
    - Background thread responsible for executing the binning logic.
    - Emits the final binned DataFrame on success, or an error message on failure.
    """

    finished = pyqtSignal(pd.DataFrame)  #Fired when binning completes successfully
    errored  = pyqtSignal(str)           #Fired if binning fails
    status = pyqtSignal(str)             #Emits status messages to the GUI

    def __init__(self, file_path: str, interval: str, already_trimmed: bool,
                 start_date: QDate, start_time: QTime, start_pm: bool,
                 end_date: QDate, end_time: QTime, end_pm: bool):
        """
        Purpose:
        - Initializes the binning worker with user-specified parameters.
        Args:
        - file_path (str): Path to the long-format csv file.
        - interval (str): Binning interval string (e.g. "15 minutes", "1 hour").
        - already_trimmed (bool): Whether to trim the dataset by start/end time.
        - start_date/start_time (QDate/QTime): User-selected start datetime.
        - start_pm (bool): Whether start time is in PM.
        - end_date/end_time (QDate/QTime): User-selected end datetime.
        - end_pm (bool): Whether end time is in PM.
        """
        super().__init__()
        self.file_path  = file_path
        self.interval   = interval
        self.already_trimmed    = already_trimmed
        self.start_date = start_date
        self.start_time = start_time
        self.start_pm   = start_pm
        self.end_date   = end_date
        self.end_time   = end_time
        self.end_pm     = end_pm
        self.status_callback = self.status.emit

    def run(self):
        """
        Purpose:
        - Loads the dataset and optionally trims it by user-defined time bounds.
        - Executes binning logic using bin/helpers.py.
        - Emits the final binned DataFrame or an error message.
        """
        try:
            self.status_callback("Reading Data…")
            df = pd.read_csv(self.file_path) #Load input dataset

            #Ensure timestamps are naive (no timezone info)
            df[TIME_COLUMN] = (
                pd.to_datetime(df[TIME_COLUMN], errors="coerce", utc=True)
                .dt.tz_convert(None)
            )

            if not self.already_trimmed: #Trim dataset by start/end time if bounding is enabled
                import datetime as dt

                start_hour = (self.start_time.hour() % 12) + (12 if self.start_pm else 0) #Construct start datetime (convert 12hr to 24hr if needed)
                start_dt = dt.datetime(
                    self.start_date.year(),
                    self.start_date.month(),
                    self.start_date.day(),
                    start_hour,
                    self.start_time.minute()
                )

                end_hour = (self.end_time.hour() % 12) + (12 if self.end_pm else 0)#Construct end datetime (convert 12hr to 24hr if needed)
                end_dt = dt.datetime(
                    self.end_date.year(),
                    self.end_date.month(),
                    self.end_date.day(),
                    end_hour,
                    self.end_time.minute()
                )

                #Filter rows within the user-defined time range
                df = df.loc[
                    (df[TIME_COLUMN] >= start_dt) &
                    (df[TIME_COLUMN] <= end_dt)
                    ]

            binned_df = melt_then_bin(df, self.interval, status_callback=self.status.emit) #Execute binning logic using helper
            self.finished.emit(binned_df)  #Emit result to UI

        except Exception as error:
            self.errored.emit(str(error))  #Emit error message to UI