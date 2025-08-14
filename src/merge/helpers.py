#merge/helpers.py

"""
Purpose:
- Provides helper functions for merging datasets from subfolders into a single long-format DataFrame.
- Used by merge/workers.py to perform the actual data merge.
"""

import os
import glob
import pandas as pd
from typing import Optional


def run_merge_script(folder: str, status_callback=None) -> Optional[pd.DataFrame]:
    """
    Purpose:
    - Scans subdirectories of `folder`, loads all .CSV files into DataFrames,
    - adds a source label, and concatenates them into a single long-format DataFrame.
    - Returns None if nothing could be merged.
    Args:
    - folder (str): Path to the master directory containing subfolders of .CSV files.
    Returns:
    - Optional[pd.DataFrame]: Long-format DataFrame if merge succeeds, else None.
    """
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Folder not found: {folder}")

    subdirs = [
        sub_folder for sub_folder in os.listdir(folder)
        if os.path.isdir(os.path.join(folder, sub_folder)) and sub_folder != "exports"
    ]
    if not subdirs:
        return None

    total = len(subdirs)

    def process(sub: str, index: int) -> Optional[pd.DataFrame]:
        """
        Purpose:
        - Reads all .CSV files from a subdirectory and tags them with the subfolder name.
        - Fires status_callback after processing is complete.
        Args:
        - sub (str): Name of the subdirectory to process.
        - index (int): Position in the list for progress tracking.
        Returns:
        - Optional[pd.DataFrame]: DataFrame with 'Dataset' column added, or None if no files loaded.
        """
        path = os.path.join(folder, sub)
        dfs = []

        for fp in glob.glob(os.path.join(path, "*")):
            try:
                dfs.append(pd.read_csv(fp))
            except Exception as e:
                print(f"Error reading {fp}: {e}")

        if not dfs:
            return None

        df = pd.concat(dfs, ignore_index=True)
        df["Dataset"] = sub
        cols = ["Dataset"] + [c for c in df.columns if c != "Dataset"]

        if status_callback:
            status_callback(f"Processing folder {index + 1} of {total}…")

        return df[cols]

    parts = []
    for i, subs in enumerate(subdirs):
        dfr = process(subs, i)
        if dfr is not None:
            parts.append(dfr)

    return pd.concat(parts, ignore_index=True) if parts else None