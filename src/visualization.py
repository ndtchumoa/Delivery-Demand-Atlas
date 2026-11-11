"""Plot helpers shared by the notebooks.

Complexity: plotting cost is linear in the number of plotted points.
"""
from typing import Sequence

import matplotlib.pyplot as plt
import pandas as pd

from . import config

DATE = config.DEMAND_DATE_COLUMN


def saveFigure(name: str) -> None:
    """Save the current figure to outputs/figures/<name>.png and show it."""
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(config.FIGURES_DIR / f"{name}.png", dpi=150)
    plt.show()


def plotActualVsPredicted(predictions: pd.DataFrame, seriesIds: Sequence[str], model: str, split: str = "test") -> None:
    """Actual and predicted daily demand of selected series for one model and split."""
    sub = predictions[(predictions.model == model) & (predictions.split == split)]
    fig, axes = plt.subplots(len(seriesIds), 1, figsize=(10, 2.6 * len(seriesIds)), sharex=True)
    for ax, sid in zip(axes if len(seriesIds) > 1 else [axes], seriesIds):
        one = sub[sub.series_id == sid].sort_values(DATE)
        ax.plot(one[DATE], one.demand, marker="o", ms=3, lw=1, label="actual")
        ax.plot(one[DATE], one.prediction, marker="s", ms=3, lw=1, label=model)
        ax.set_ylabel(sid)
        ax.legend(loc="upper right", fontsize=8)
    fig.autofmt_xdate()
