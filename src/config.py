# config.py

# Which columns to roll up in each time bin, how to summarize, and output names
SELECTED_COLUMNS = {
    1: {
        "name": "Raw Score",
        "summarize": "mean",
        "columns": ["Act"]
    },
    2: {
        "name": "Percent Score",
        "summarize": "act_percent",
        "columns": ["Act"]
    },
    3: {
        "name": "Temperature",
        "summarize": "mean",
        "columns": ["T"]
    },
    4: {
        "name": "Light",
        "summarize": "mean",
        "columns": ["Light"]
    },
    5: {
        "name": "Battery Voltage",
        "summarize": "mean",
        "columns": ["Vbat"]
    }
}

# Name of the timestamp column in your DataFrames
TIME_COLUMN = "Time"

# Column that identifies each record’s “subject” or dataset
DELINEATING_COL = "Dataset"