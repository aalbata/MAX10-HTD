"""Figures of the MAX10-HTD paper and documentation, drawn from the released result files.

Usage:
  python -m scripts.analysis.figures

Writes figures/*.pdf (vector) and figures/*.png (for inspection).
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FuncFormatter, MaxNLocator, NullLocator
import numpy as np
import pandas as pd

from ..common import config

FIG = config.REPO / "figures"
RES = config.REPO / "experiments" / "results"
WIDTH = 3.45                      # IEEE single-column width in inches
FREE, TROJAN, THIRD = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#d9d8d4"
MODEL_ORDER = ["LR", "DT", "RF", "SVM", "KNN", "XGB", "MLP", "ET", "AB", "GNB", "LightGBM"]
SOURCE_NAME = {"trusthub": "Trust-Hub", "ghost": "GHOST", "hayashi": "RISC-V and Web3"}
GROUP_NAME = {"quartus_synthesis": "Synthesis", "quartus_fitter": "Fitter", "quartus_routing": "Routing",
              "quartus_timing": "Timing", "quartus_power": "Power", "netlist_structure": "Netlist",
              "rtl_structure": "RTL", "quartus_reports": "All Quartus reports", "structural": "Netlist + RTL"}


def style():
    plt.rcParams.update({
        "font.family": "serif", "font.serif": ["Times New Roman", "Times", "STIXGeneral"],
        "mathtext.fontset": "stix", "font.size": 7, "axes.titlesize": 7, "axes.labelsize": 7,
        "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6.5,
        "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0.5,
        "xtick.major.size": 2.5, "ytick.major.size": 2.5, "lines.linewidth": 0.8,
        "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
        "text.color": INK, "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": 300,
        "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    })


def save(fig, name):
    FIG.mkdir(exist_ok=True)
    meta = {"Title": None, "Author": None, "Subject": None, "Keywords": None, "CreationDate": None}
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight", pad_inches=0.02, metadata=meta)
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight", pad_inches=0.02, dpi=300)
    plt.close(fig)


def composition(meta: pd.DataFrame):
    tab = meta.groupby(["family", "label"]).size().unstack(fill_value=0)
    tab = tab.reindex(tab.sum(axis=1).sort_values().index)
    fig, ax = plt.subplots(figsize=(WIDTH, 0.28 * len(tab) + 0.45))
    y = np.arange(len(tab))
    free, tro = tab.get(0, 0).to_numpy(), tab.get(1, 0).to_numpy()
    ax.barh(y, free, color=FREE, height=0.62, label="Trojan-free", edgecolor="white", linewidth=0.6)
    ax.barh(y, tro, left=free, color=TROJAN, height=0.62, label="Trojan-inserted", edgecolor="white",
            linewidth=0.6)
    for yi, a, b in zip(y, free, tro):
        ax.text(a + b + max(tab.sum(axis=1)) * 0.01, yi, f"{a} / {b}", va="center", fontsize=6.5, color=MUTED)
    ax.set_yticks(y, [f.capitalize() for f in tab.index])
    ax.set_xlabel("Implementations (Trojan-free / Trojan-inserted)")
    ax.set_xlim(0, max(tab.sum(axis=1)) * 1.18)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(axis="x", color=GRID, linewidth=0.4)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", ncol=1, handlelength=1.0)
    save(fig, "fig_composition")


def footprint(meta: pd.DataFrame, X: pd.DataFrame):
    tro = meta[meta["label"] == 1]
    cols = [("fit_le", "Logic elements"), ("fit_registers", "Registers"), ("pow_core_dynamic_mw", "Core dynamic power")]
    fig, axes = plt.subplots(len(cols), 1, figsize=(WIDTH, 2.7), sharex=True)
    sources = [s for s in ("trusthub", "ghost", "hayashi") if s in set(tro["source"])]
    colors = {"trusthub": FREE, "ghost": TROJAN, "hayashi": THIRD}
    rng = np.random.default_rng(0)
    change = {}
    for col, _ in cols:
        for src in sources:
            sub = tro[tro["source"] == src]
            ref = X.loc[sub["clean_reference"], col].to_numpy(dtype=float)
            val = X.loc[sub.index, col].to_numpy(dtype=float)
            rel = 100.0 * (val - ref) / np.where(ref == 0, np.nan, ref)
            change[col, src] = rel[np.isfinite(rel)]
    every = np.concatenate(list(change.values()))
    for ax, (col, title) in zip(axes, cols):
        for i, src in enumerate(sources):
            rel = change[col, src]
            ax.scatter(rel, i + rng.uniform(-0.18, 0.18, len(rel)), s=4, color=colors[src], alpha=0.75,
                       linewidths=0)
            if len(rel):
                ax.plot([np.median(rel)] * 2, [i - 0.32, i + 0.32], color=INK, linewidth=0.9)
        ax.axvline(0, color=MUTED, linewidth=0.5, linestyle=":")
        ax.set_title(title, pad=2, loc="left")
        ax.set_yticks(range(len(sources)), [SOURCE_NAME[s] for s in sources])
        ax.set_ylim(-0.6, len(sources) - 0.4)
        ax.grid(axis="x", color=GRID, linewidth=0.4)
        ax.set_axisbelow(True)
    ax = axes[-1]
    ax.set_xscale("symlog", linthresh=1.0)
    ax.set_xlim(min(-150.0, 1.5 * every.min()), max(150.0, 1.5 * every.max()))
    ax.xaxis.set_major_locator(FixedLocator([t for t in (-100, -10, -1, 0, 1, 10, 100, 1000, 10000)
                                             if 1.5 * every.min() <= t <= 1.5 * every.max() or abs(t) <= 100]))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:g}".replace("-", "−")))
    ax.set_xlabel("Change from the Trojan-free reference (%)")
    fig.subplots_adjust(hspace=0.5)
    save(fig, "fig_footprint")


def e1_models():
    ci = pd.read_csv(RES / "summary_E1_bootstrap.csv").set_index("model")
    tab = pd.read_csv(RES / "summary_E1.csv").set_index("model")
    models = [m for m in MODEL_ORDER if m in ci.index]
    order = sorted(models, key=lambda m: ci.loc[m, "roc_auc"])
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.0), sharey=True)
    y = np.arange(len(order))
    for ax, key, title, ref in ((axes[0], "roc_auc", "ROC AUC", 0.5),
                                (axes[1], "balanced_accuracy", "Balanced accuracy", 0.5)):
        v = ci.loc[order, key].to_numpy()
        lo, hi = ci.loc[order, f"{key}_lo"].to_numpy(), ci.loc[order, f"{key}_hi"].to_numpy()
        ax.errorbar(v, y, xerr=[v - lo, hi - v], fmt="o", ms=2.8, color=FREE, ecolor=FREE, elinewidth=0.7,
                    capsize=1.2)
        ax.axvline(ref, color=MUTED, linewidth=0.5, linestyle=":")
        if "Size" in tab.index:
            s = ci.loc["Size", key] if "Size" in ci.index else tab.loc["Size", f"{key}_mean"]
            ax.axvline(s, color=TROJAN, linewidth=0.7, linestyle="--")
        ax.set_title(title, pad=3)
        ax.set_xlim(0.3, 1.0)
        ax.grid(axis="x", color=GRID, linewidth=0.4)
        ax.set_axisbelow(True)
    axes[0].set_yticks(y, order)
    fig.subplots_adjust(wspace=0.08)
    save(fig, "fig_e1_models")


def feature_groups():
    tab = pd.read_csv(RES / "summary_E4_feature_groups.csv")
    tab["set"] = tab["feature_set"].str.replace("only:", "", regex=False)
    pivot = tab.pivot(index="model", columns="set", values="roc_auc_mean")
    cols = [c for c in ["quartus_synthesis", "quartus_fitter", "quartus_routing", "quartus_timing", "quartus_power",
                        "quartus_reports", "netlist_structure", "rtl_structure", "structural"] if c in pivot.columns]
    rows = [m for m in MODEL_ORDER if m in pivot.index]
    data = pivot.loc[rows, cols].to_numpy()
    fig, ax = plt.subplots(figsize=(WIDTH, 2.35))
    im = ax.imshow(data, cmap="Blues", vmin=0.4, vmax=1.0, aspect="auto")
    for i in range(len(rows)):
        for j in range(len(cols)):
            if np.isfinite(data[i, j]):
                ax.text(j, i, f"{data[i, j]:.2f}", ha="center", va="center", fontsize=5.5,
                        color="white" if data[i, j] > 0.8 else INK)
    ax.set_xticks(range(len(cols)), [GROUP_NAME[c] for c in cols], rotation=40, ha="right")
    ax.set_yticks(range(len(rows)), rows)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cb.set_label("ROC AUC", fontsize=6.5)
    cb.ax.tick_params(labelsize=6, length=2)
    cb.outline.set_linewidth(0.4)
    save(fig, "fig_feature_groups")


def seed_variation():
    f = RES / "seed_variance_groups.csv"
    if not f.exists():
        return
    g = pd.read_csv(f).set_index("group")
    order = [k for k in GROUP_NAME if k in g.index]
    frac = (g.loc[order, "varying_features"] / g.loc[order, "features"]).to_numpy()
    fig, ax = plt.subplots(figsize=(WIDTH, 1.45))
    x = np.arange(len(order))
    ax.bar(x, 100 * frac, color=FREE, width=0.62)
    for xi, v, n in zip(x, frac, g.loc[order, "features"]):
        ax.text(xi, 100 * v + 2, f"{100 * v:.0f}%", ha="center", fontsize=6, color=MUTED)
    ax.set_xticks(x, [GROUP_NAME[k] for k in order])
    ax.set_ylabel("Features that change\nwith the fitter seed (%)")
    ax.set_ylim(0, 112)
    ax.grid(axis="y", color=GRID, linewidth=0.4)
    ax.set_axisbelow(True)
    save(fig, "fig_seed_variation")


def main():
    style()
    meta = pd.read_csv(config.METADATA_DIR / "samples.csv", index_col="sample_id")
    X = pd.read_csv(config.DATASET_DIR / "features" / "features.csv", index_col="sample_id")
    composition(meta)
    footprint(meta, X)
    if (RES / "summary_E1_bootstrap.csv").exists():
        e1_models()
    if (RES / "summary_E4_feature_groups.csv").exists():
        feature_groups()
    seed_variation()
    print("wrote", sorted(p.name for p in FIG.glob("*.pdf")))


if __name__ == "__main__":
    main()
