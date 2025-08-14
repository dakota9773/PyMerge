# graph/helpers.py

"""
Purpose:
- Provides plotting utilities for multi-series visualizations using Plotly.
- Supports single-dataset multi-column plots and cross-dataset comparisons.
- Used for generating annotated subplots and normalized visual summaries.
"""

import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def sing_sub_plot(df, x_axis, y_axes, title_text):
    """
    Purpose:
    - Generates annotated subplots for each column in `y_axes` against `x_axis`.
    - Includes an optional combined subplot with normalized series (0–1 scale).
    - Intended for exploring column-wise trends within a single dataset.
    Args:
    - df (pd.DataFrame): Source dataset containing all columns to visualize.
    - x_axis (str): Column to use as x-axis (usually timestamps or measurements).
    - y_axes (list[str]): Columns to plot individually and in normalized combination.
    - title_text (str): Title to display above the entire figure.
    Returns:
    - go.Figure: Fully styled Plotly figure with internal filename for export.
    """
    df = df.copy()
    for col in y_axes:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    n = len(y_axes)
    has_combined = n > 1
    total_rows = n + (1 if has_combined else 0)

    fig = make_subplots(
        rows=total_rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05
    )

    base_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    cmap = {col: base_colors[i % len(base_colors)]
            for i, col in enumerate(y_axes)}

    # 1) individual subplots
    for i, col in enumerate(y_axes, start=1):
        fig.add_trace(
            go.Scatter(
                x=df[x_axis], y=df[col],
                mode='lines', name=col,
                line=dict(color=cmap[col]),
                legendgroup=col
            ),
            row=i, col=1
        )
        fig.update_yaxes(
            type='linear', tickformat=".2f",
            automargin=True, title_standoff=30,
            row=i, col=1
        )

    # 2) combined normalized subplot (only if >1 series)
    if has_combined:
        norm_df = pd.DataFrame({x_axis: df[x_axis]})
        for col in y_axes:
            mn, mx = df[col].min(), df[col].max()
            if mx > mn:
                norm_df[col] = (df[col] - mn) / (mx - mn)
            else:
                norm_df[col] = 0

        for col in y_axes:
            fig.add_trace(
                go.Scatter(
                    x=norm_df[x_axis], y=norm_df[col],
                    mode='lines', name=col,
                    line=dict(color=cmap[col]),
                    legendgroup=col,
                    showlegend=False
                ),
                row=total_rows, col=1
            )
        fig.update_yaxes(
            title="Normalized (0–1)",
            automargin=True, row=total_rows, col=1
        )

    # 3) x-ticks on every row
    for i in range(1, total_rows + 1):
        fig.update_xaxes(showticklabels=True, row=i, col=1)

    # 4) annotations
    annotations = []
    for i, col in enumerate(y_axes, start=1):
        yref = "y domain" if i == 1 else f"y{i} domain"
        annotations.append(dict(
            xref="paper", yref=yref,
            x=-0.10, y=0.5, xanchor="right",
            text=col, showarrow=False,
            textangle=-90,
            font=dict(family="Arial", size=18, color="black")
        ))
    if has_combined:
        yref = f"y{total_rows} domain"
        annotations.append(dict(
            xref="paper", yref=yref,
            x=-0.10, y=0.5, xanchor="right",
            text="Combined", showarrow=False,
            textangle=-90,
            font=dict(family="Arial", size=18, color="black")
        ))

    # 5) layout
    fig.update_layout(
        title=dict(text=title_text, x=0.5, font=dict(size=16)),
        width=1000,
        height=200 * total_rows,
        margin=dict(l=200, r=20, t=50, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Arial", size=12, color="#1a2a3a"),
        annotations=annotations,
        showlegend=True,
        legend=dict(
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#cccccc", borderwidth=1
        )
    )

    safe = lambda s: s.replace(" ", "_").replace("/", "_")
    y_part = "_".join(safe(col) for col in y_axes)
    fig._filename = f"{safe(title_text)}_{safe(x_axis)}_{y_part}.html"
    return fig

def mult_sub_plot(df, x_axis, column, selected_ds):
    """
    Purpose:
    - Plots the same `column` across multiple datasets in separate subplots.
    - Adds an optional combined subplot of raw values from all datasets.
    - Used for cross-dataset comparisons of a single metric.
    Args:
    - df (pd.DataFrame): Long-format DataFrame with a 'Dataset' column.
    - x_axis (str): Column to use as x-axis (e.g. 'Time', 'Sample', etc.).
    - column (str): Target column to visualize across datasets.
    - selected_ds (list[str]): List of dataset labels to include (from 'Dataset' column).
    Returns:
    - go.Figure: Annotated Plotly figure ready for export or embedding.
    """
    df = df.copy()
    df[column] = pd.to_numeric(df[column], errors='coerce')

    n = len(selected_ds)
    has_combined = n > 1
    total_rows = n + (1 if has_combined else 0)

    fig = make_subplots(
        rows=total_rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05
    )

    base_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    cmap = {ds: base_colors[i % len(base_colors)]
            for i, ds in enumerate(selected_ds)}

    # individual subject plots
    for i, ds in enumerate(selected_ds, start=1):
        sub = df[df['Dataset'] == ds]
        fig.add_trace(
            go.Scatter(
                x=sub[x_axis], y=sub[column],
                mode='lines', name=ds,
                line=dict(color=cmap[ds]),
                legendgroup=ds
            ),
            row=i, col=1
        )
        fig.update_yaxes(
            type='linear', tickformat=".2f",
            automargin=True, row=i, col=1
        )

    # combined subplot at bottom (raw values)
    if has_combined:
        for ds in selected_ds:
            sub = df[df['Dataset'] == ds]
            fig.add_trace(
                go.Scatter(
                    x=sub[x_axis], y=sub[column],
                    mode='lines', name=ds,
                    line=dict(color=cmap[ds]),
                    legendgroup=ds,
                    showlegend=False
                ),
                row=total_rows, col=1
            )
        fig.update_yaxes(
            type='linear', tickformat=".2f",
            automargin=True, row=total_rows, col=1
        )

    # show x-ticks on every row
    for i in range(1, total_rows + 1):
        fig.update_xaxes(showticklabels=True, row=i, col=1)

    # annotations
    annotations = []
    for i, ds in enumerate(selected_ds, start=1):
        yref = "y domain" if i == 1 else f"y{i} domain"
        annotations.append(dict(
            xref="paper", yref=yref,
            x=-0.10, y=0.5, xanchor="right",
            text=ds, showarrow=False,
            textangle=-90,
            font=dict(family="Arial", size=18, color="black")
        ))
    if has_combined:
        yref = f"y{total_rows} domain"
        annotations.append(dict(
            xref="paper", yref=yref,
            x=-0.10, y=0.5, xanchor="right",
            text="Combined", showarrow=False,
            textangle=-90,
            font=dict(family="Arial", size=18, color="black")
        ))

    fig.update_layout(
        title=dict(text=f"{column} Across Datasets", x=0.5, font=dict(size=16)),
        width=1000,
        height=200 * total_rows,
        margin=dict(l=200, r=20, t=50, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Arial", size=12, color="#1a2a3a"),
        annotations=annotations,
        showlegend=True,
        legend=dict(
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#cccccc", borderwidth=1
        )
    )

    safe = lambda s: s.replace(" ", "_").replace("/", "_")
    fig._filename = f"{safe(column)}_across_{safe('_'.join(selected_ds))}.html"
    return fig

def wrap_html(inner: str) -> str:
    """
    Purpose:
    - Wraps a raw HTML snippet in a scrollable, horizontally centered HTML shell.
    - Useful for embedding Plotly figures or other interactive fragments.
    Args:
    - inner (str): HTML content to embed within the scroll container.
    Returns:
    - str: Complete HTML document string with styles for full-height scroll.
    """
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
  <style>
    html, body {{
        height: 100%;
        margin: 0;
        padding: 0;
    }}
    #scroll-container {{
        width: 100%;
        height: 100%;
        overflow: auto;
        text-align: center;  /* ⬅️ this is what centers your content */
    }}
    #scroll-container > * {{
        display: inline-block;  /* ⬅️ keeps block elements centered within text-align */
        text-align: left;       /* optional: keeps internal layout left-aligned */
    }}
  </style>
</head><body>
  <div id="scroll-container">
    {inner}
  </div>
</body></html>"""