"""Variation of the features across Quartus fitter seeds.

The benchmark compiles every design with fitter seed 1.  This study compiles a
subset again with seeds 2 and 3: every Trojan-free design of the benchmark
and, for each of them that has Trojan-inserted variants in the benchmark, the
variant with the smallest sample identifier.  Synthesis and RTL features do not depend on the fitter seed;
placement, routing, timing and power features can.

Usage:
  python -m scripts.analysis.seed_variance select     # writes dataset/metadata/seed_study.csv
  python -m scripts.quartus.compile --seed 2 --only <ids>   (likewise for seed 3)
  python -m scripts.feature_extraction.build_features --compiled <build>/compiled_seed2 --only <ids> \\
      --out dataset/features/seed_study/features_seed2.csv      (likewise for seed 3)
  python -m scripts.analysis.seed_variance analyze    # writes experiments/results/seed_variance_*.csv
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from ..common import config

SEEDS = (1, 2, 3)
RES = config.REPO / "experiments" / "results"
SEED_DIR = config.DATASET_DIR / "features" / "seed_study"


def select() -> None:
    meta = pd.read_csv(config.METADATA_DIR / "samples.csv")
    clean = meta[meta["label"] == 0]
    tro = meta[meta["label"] == 1].sort_values("sample_id")
    picks = list(clean["sample_id"])
    for ref in clean["sample_id"]:
        v = tro[tro["clean_reference"] == ref]
        if len(v):
            picks.append(v["sample_id"].iloc[0])
    pd.DataFrame({"sample_id": sorted(picks)}).to_csv(config.METADATA_DIR / "seed_study.csv", index=False,
                                                       lineterminator="\n")
    print(",".join(sorted(picks)))


def analyze() -> None:
    ids = pd.read_csv(config.METADATA_DIR / "seed_study.csv")["sample_id"].tolist()
    frames = {1: pd.read_csv(config.DATASET_DIR / "features" / "features.csv", index_col="sample_id").loc[ids]}
    for s in SEEDS[1:]:
        frames[s] = pd.read_csv(SEED_DIR / f"features_seed{s}.csv", index_col="sample_id").reindex(ids)
    groups = json.loads((config.DATASET_DIR / "features" / "feature_groups.json").read_text(encoding="utf-8"))
    group_of = {c: g for g, cols in groups.items() for c in cols}
    cube = np.stack([frames[s].to_numpy(dtype=float) for s in SEEDS])      # seeds x designs x features
    cols = list(frames[1].columns)
    rows = []
    for j, c in enumerate(cols):
        v = cube[:, :, j]
        ok = ~np.isnan(v).any(axis=0)
        if not ok.any():
            continue
        v = v[:, ok]
        spread = v.max(axis=0) - v.min(axis=0)
        scale = np.abs(v.mean(axis=0))
        rel = np.where(scale > 0, spread / np.where(scale > 0, scale, 1), 0.0)
        rows.append({"feature": c, "group": group_of.get(c, ""), "designs": int(ok.sum()),
                     "fraction_varying": float((spread > 0).mean()),
                     "median_relative_range": float(np.median(rel)), "p90_relative_range": float(np.quantile(rel, 0.9))})
    feat = pd.DataFrame(rows)
    feat.to_csv(RES / "seed_variance_features.csv", index=False, lineterminator="\n", float_format="%.5f")
    grp = feat.groupby("group").agg(features=("feature", "size"), varying_features=("fraction_varying",
                                                                                    lambda x: int((x > 0).sum())),
                                    median_relative_range=("median_relative_range", "median"))
    grp.to_csv(RES / "seed_variance_groups.csv", lineterminator="\n", float_format="%.5f")
    # Stability of the paired difference: does the sign of (Trojan-inserted - reference) stay the
    # same when both designs are compiled with the same seed, for every seed?
    meta = pd.read_csv(config.METADATA_DIR / "samples.csv", index_col="sample_id")
    pairs = [(t, meta.loc[t, "clean_reference"]) for t in ids if meta.loc[t, "label"] == 1]
    pos = {sid: i for i, sid in enumerate(ids)}
    srows = []
    for j, c in enumerate(cols):
        signs = []
        for t, r in pairs:
            d = cube[:, pos[t], j] - cube[:, pos[r], j]
            if np.isnan(d).any():
                continue
            signs.append(len(set(np.sign(d))) == 1)
        if signs:
            srows.append({"feature": c, "group": group_of.get(c, ""), "pairs": len(signs),
                          "sign_stable_fraction": float(np.mean(signs))})
    pd.DataFrame(srows).to_csv(RES / "seed_variance_pair_sign.csv", index=False, lineterminator="\n",
                               float_format="%.4f")
    print(grp.to_string())


if __name__ == "__main__":
    {"select": select, "analyze": analyze}[sys.argv[1]]()
