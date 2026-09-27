#!/usr/bin/env python3
"""Rebuild Figure 1 from frozen aggregate values."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parents[1] / "results" / "figures" / "Figure1_HeldOutPredictiveEvidence.png"
green, grey = "#2e7d32", "#8a8a8a"
fig, axes = plt.subplots(1, 2, figsize=(10, 4.6))
fig.suptitle("Held-Out Predictive Evidence -- 6-Month Value-Growth Model", fontsize=15, fontweight="bold", y=1.03)
fig.text(0.5, 0.965, "HELD-OUT TEST RESULT  (n = 1,345 valuation events, never used during development)", ha="center", fontsize=11, color=green, fontweight="bold")
x = [0, 1]
for ax, vals, title, ylabel, ylim in [
    (axes[0], [0.339, 0.3094], "Prediction Error", "MAE (log-return, lower is better)", (0, 0.42)),
    (axes[1], [0.569, 0.5916], "Rank Correlation", "Spearman correlation", (0, 0.72)),
]:
    ax.bar(x, vals, color=[grey, green], width=0.6)
    ax.set_xticks(x, ["VALIDATION\n(development)", "TEST\n(held-out)"], fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_ylim(*ylim)
    ax.set_title(title, fontsize=12)
    offset = 0.012 if title == "Prediction Error" else 0.018
    for xi, value in zip(x, vals):
        ax.text(xi, value + offset, f"{value:.4f}", ha="center", fontsize=12, fontweight="bold")
fig.text(0.5, -0.03, "Accuracy on unseen, later-period valuation events matches or exceeds development-set accuracy.", ha="center", fontsize=10.5, style="italic", color="#444")
fig.tight_layout(rect=[0, 0.02, 1, 0.90])
fig.savefig(OUT, dpi=200, bbox_inches="tight")
plt.close(fig)
print(OUT)
