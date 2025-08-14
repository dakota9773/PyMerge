#bin/helpers.py

"""
Purpose:
- Provides helper functions for binning time-series data into fixed intervals and computing summary statistics.
- Used by bin/workers.py to perform the binning step in the analysis pipeline.
"""

import re
import numpy as np
import pandas as pd
from config import (TIME_COLUMN, SELECTED_COLUMNS, DELINEATING_COL)

def melt_activity_data(df: pd.DataFrame, status_callback) -> pd.DataFrame:
    """
    Purpose:
    - Unrolls activity columns (Act[0] to Act[5]) into individual minute-level records.
    - Groups by device before melting so each device's data is kept together.
    - Fills environmental columns across expanded rows.
    - Sorts output by device first, then time.
    - Optionally saves the melted DataFrame to disk.
    """
    if status_callback:
        status_callback("Melting data…")

    act_cols = [col for col in df.columns if re.match(r"Act\[\d+]", col)]
    df[TIME_COLUMN] = pd.to_datetime(df[TIME_COLUMN], errors="coerce", utc=True).dt.tz_convert(None)

    melted_rows = []

    # ✅ Group by device before expanding
    for device_id, device_df in df.groupby(DELINEATING_COL):
        for _, row in device_df.iterrows():
            base_time = row[TIME_COLUMN]
            for offset in range(len(act_cols)):
                new_row = {
                    DELINEATING_COL: device_id,
                    "Time": base_time - pd.Timedelta(minutes=offset),
                    "Act": row[f"Act[{offset}]"],
                    "T": row.get("T", None),
                    "Light": row.get("Light", None),
                    "Vbat": row.get("Vbat", None)
                }
                melted_rows.append(new_row)

    melted_df = pd.DataFrame(melted_rows)
    melted_df = melted_df.dropna(subset=["Act"])

    # ✅ Sort by device first, then time
    melted_df = melted_df.sort_values(by=[DELINEATING_COL, "Time"])

    return melted_df

def bin_data(df: pd.DataFrame, interval: str, status_callback) -> pd.DataFrame:
    """
    Purpose:
    - Floors timestamps into bins of length `interval` and computes summary statistics per subject and bin.
    - Uses config-defined aggregation rules to generate a new binned DataFrame.
    Args:
    - df (pd.DataFrame): Input DataFrame containing timestamped data.
    - interval (str): Binning interval (e.summary_df. "15 minutes", "1 hour", "1 day").
    Returns:
    - pd.DataFrame: Binned DataFrame with summary statistics and time-aligned bins.
    """

    match = re.search(r"(\d+)", interval)       #Parse numeric duration from input string (e.summary_df. "15 minutes")
    if not match:       #Validate that a numeric duration was found in the interval string
        raise ValueError(f"Invalid interval format: '{interval}'. Expected a number like '15 minutes'.")

    if status_callback:
        status_callback(f"Binning data…")


    duration_value = float(match.group(1))      #Convert matched number to float (e.g. "15" → 15.0)

    #Ensure all timestamps are naive and in local timezone
    df[TIME_COLUMN] = (
        pd.to_datetime(df[TIME_COLUMN], errors="coerce", utc=True)
        .dt.tz_convert(None)        # Convert timestamps to naive datetime (local time, no timezone info)
    )

    #Floor timestamps to bin intervals
    unit = (
        "D"   if "day"  in interval else
        "H"   if "hour" in interval else
        "min"
    )
    df["Bin"] = df[TIME_COLUMN].dt.floor(f"{int(duration_value)}{unit}")

    #Initialize summary containers
    summary = []

    #Loop over configured aggregation groups
    for idx, cfg in SELECTED_COLUMNS.items():
        name = cfg.get("name", f"Bin_{idx}")           #output column name
        cols = cfg.get("columns", [])                  #source columns to aggregate
        agg  = cfg.get("summarize", "mean")            #aggregation method

        def agg_func(subdf: pd.DataFrame) -> float:
            vals = subdf[cols].to_numpy().ravel()      #flatten all values
            vals = vals[~np.isnan(vals)]               #drop NaNs
            if vals.size == 0:
                return np.nan
            if agg == "sum":         return np.sum(vals)
            if agg == "max":         return np.max(vals)
            if agg == "min":         return np.min(vals)
            if agg == "act_percent": return np.mean(vals) * 50 + 50
            return np.mean(vals)

        summary_series = df.groupby([DELINEATING_COL, "Bin"]).apply(agg_func)
        summary_df = summary_series.reset_index()
        summary_df.rename(columns={0: name}, inplace=True)
        summary.append(summary_df)

    #Merge all computed summaries
    if not summary:
        out = df.copy()
    else:
        out = summary[0]
        for summary_df in summary[1:]:
            out = out.merge(summary_df, on=[DELINEATING_COL, "Bin"], how="left")

    out.rename(columns={"Bin": "Time"}, inplace=True) #Rename bin column to "Time" for clarity
    return out

def melt_then_bin(df: pd.DataFrame, interval: str, status_callback=None) -> pd.DataFrame:
    melted = melt_activity_data(df, status_callback)
    return bin_data(melted, interval, status_callback)