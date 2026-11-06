"""Summary tables of the MAX10-HTD experiments.

Metrics are computed from the saved out-of-partition predictions.  For the
cross-validated experiments, the predictions of all folds of one repetition
are pooled (every design is predicted once per repetition) and the metrics of
the repetitions are averaged; the spread is the standard deviation over the
repetitions.  For E1, 95% confidence intervals of the repetition means come
from a cluster bootstrap over host groups.

Usage:
  python -m scripts.analysis.summarize

Writes experiments/results/summary_*.csv and experiments/results/summary.json.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from ..common import config
from ml.evaluation.metrics import binary_metrics
from ml.models import zoo
from ml.training.run_experiments import mutual_information_top

RES = config.REPO / "experiments" / "results"
PRED = config.REPO / "experiments" / "predictions"
KEYS = ["accuracy", "precision", "recall", "specificity", "f1", "fpr", "fnr", "balanced_accuracy", "mcc",
        "pr_auc", "pr_auc_clean", "roc_auc"]
BOOT = 2000
SEED = 20261104


def pooled(df: pd.DataFrame, by: list[str], cfg: dict) -> pd.DataFrame:
    rows = []
    for key, g in df.groupby(by, sort=False):
        key = key if isinstance(key, tuple) else (key,)
        m = binary_metrics(g["label"].to_numpy(), g["score"].to_numpy(), zoo.threshold(dict(zip(by, key))["model"], cfg))
        rows.append({**dict(zip(by, key)), **m})
    return pd.DataFrame(rows)


def mean_std(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    agg = df.groupby(by, sort=False)[KEYS + ["tp", "tn", "fp", "fn", "n"]].agg(["mean", "std"])
    agg.columns = [f"{a}_{b}" for a, b in agg.columns]
    return agg.reset_index()


def timing(folds: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    return folds.groupby(by, sort=False)[["fit_seconds", "predict_seconds_per_design"]].mean().reset_index()


def bootstrap(df: pd.DataFrame, meta: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Repetition means of five metrics with 95% intervals from a cluster bootstrap over host groups.

    Each resample draws host groups with replacement, recomputes the metric of every repetition on the
    drawn designs and averages over the repetitions; all models are evaluated on the same resamples.
    """
    rng = np.random.default_rng(SEED)
    keys = ("pr_auc", "roc_auc", "balanced_accuracy", "recall", "specificity")
    ids = np.array(sorted(df["sample_id"].unique()))
    group = meta.loc[ids, "host_group"].to_numpy()
    names = np.unique(group)
    members = {k: np.where(group == k)[0] for k in names}
    draws = [np.concatenate([members[k] for k in rng.choice(names, size=len(names), replace=True)])
             for _ in range(BOOT)]
    rows = []
    for model, g in df.groupby("model", sort=False):
        thr = zoo.threshold(model, cfg)
        reps = [r.set_index("sample_id").loc[ids, ["label", "score"]].to_numpy() for _, r in g.groupby("rep")]
        point = {k: float(np.mean([binary_metrics(a[:, 0], a[:, 1], thr)[k] for a in reps])) for k in keys}
        stats = {k: [] for k in keys}
        for idx in draws:
            m = [binary_metrics(a[idx, 0], a[idx, 1], thr) for a in reps]
            if np.isnan(m[0]["roc_auc"]):
                continue
            for k in keys:
                stats[k].append(np.mean([x[k] for x in m]))
        row = {"model": model}
        for k in keys:
            row[k] = point[k]
            row[f"{k}_lo"] = float(np.nanpercentile(stats[k], 2.5))
            row[f"{k}_hi"] = float(np.nanpercentile(stats[k], 97.5))
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    cfg = zoo.load_config()
    meta = pd.read_csv(config.METADATA_DIR / "samples.csv", index_col="sample_id")
    X = pd.read_csv(config.DATASET_DIR / "features" / "features.csv", index_col="sample_id")
    out = {}

    def load(name):
        p, f = PRED / f"{name}.csv", RES / f"{name}_folds.csv"
        if not p.exists() or p.stat().st_size < 10:
            return None, None
        return pd.read_csv(p), pd.read_csv(f)

    e1, f1 = load("E1_grouped_cv")
    if e1 is not None:
        per_rep = pooled(e1, ["model", "rep"], cfg)
        tab = mean_std(per_rep, ["model"]).merge(timing(f1, ["model"]), on="model")
        tab.to_csv(RES / "summary_E1.csv", index=False, lineterminator="\n", float_format="%.4f")
        ci = bootstrap(e1, meta, cfg)
        ci.to_csv(RES / "summary_E1_bootstrap.csv", index=False, lineterminator="\n", float_format="%.4f")
        out["E1"] = tab.set_index("model").to_dict(orient="index")
        out["E1_bootstrap"] = ci.set_index("model").to_dict(orient="index")
        # By benchmark source and by functional family, from the same predictions.
        e1m = e1.join(meta[["source", "family", "interface_identical", "host_group"]], on="sample_id")
        by_src = mean_std(pooled(e1m, ["model", "source", "rep"], cfg), ["model", "source"])
        by_src.to_csv(RES / "summary_E1_by_source.csv", index=False, lineterminator="\n", float_format="%.4f")
        # Interface-preserving subset: Trojan-free designs and Trojan-inserted designs whose
        # top-level interface equals that of their reference.
        keep = (e1m["label"] == 0) | (e1m["interface_identical"] == 1)
        sub = mean_std(pooled(e1m[keep], ["model", "rep"], cfg), ["model"])
        sub.to_csv(RES / "summary_E1_interface_identical.csv", index=False, lineterminator="\n", float_format="%.4f")
        out["E1_interface_identical"] = sub.set_index("model").to_dict(orient="index")
        # E7: sensitivity to circuit complexity (terciles of the number of logic elements).
        size = X.loc[e1m["sample_id"], "fit_le"].to_numpy()
        cuts = np.quantile(X["fit_le"], [1 / 3, 2 / 3])
        e1m["size_bin"] = np.where(size <= cuts[0], "small", np.where(size <= cuts[1], "medium", "large"))
        e7 = mean_std(pooled(e1m, ["model", "size_bin", "rep"], cfg), ["model", "size_bin"])
        e7.to_csv(RES / "summary_E7_complexity.csv", index=False, lineterminator="\n", float_format="%.4f")
        out["E7_cuts_le"] = [float(c) for c in cuts]
        out["E7"] = {f"{r.model}|{r.size_bin}": {k: getattr(r, f"{k}_mean") for k in ("recall", "specificity", "n")}
                     for r in e7.itertuples()}

    e1b, f1b = load("E1b_design_grouped_cv")
    if e1b is not None:
        tab = mean_std(pooled(e1b, ["model", "rep"], cfg), ["model"]).merge(timing(f1b, ["model"]), on="model")
        tab.to_csv(RES / "summary_E1b.csv", index=False, lineterminator="\n", float_format="%.4f")
        out["E1b"] = tab.set_index("model").to_dict(orient="index")

    for name, by in (("E2a_family_holdout", "family"), ("E2b_source_holdout", "source")):
        e, f = load(name)
        if e is None:
            continue
        overall = pooled(e, ["model"], cfg).merge(timing(f, ["model"]), on="model")
        overall.to_csv(RES / f"summary_{name}.csv", index=False, lineterminator="\n", float_format="%.4f")
        part = pooled(e, ["model", by], cfg)
        part.to_csv(RES / f"summary_{name}_by_{by}.csv", index=False, lineterminator="\n", float_format="%.4f")
        out[name] = overall.set_index("model").to_dict(orient="index")

    e3, _ = load("E3_unseen_payload")
    if e3 is not None:
        tab = pooled(e3, ["model", "payload", "variant"], cfg)
        tab.to_csv(RES / "summary_E3.csv", index=False, lineterminator="\n", float_format="%.4f")
        out["E3"] = {f"{r.model}|{r.payload}|{r.variant}": {"recall": r.recall, "specificity": r.specificity,
                                                             "positives": r.positives, "negatives": r.negatives}
                     for r in tab.itertuples()}

    for name, key in (("E4_feature_groups", "feature_set"), ("E5_ablation_selection", "feature_set"),
                      ("E6_class_balance", "balance"), ("C1_without_port_counts", "feature_set")):
        e, f = load(name)
        if e is None:
            continue
        tab = mean_std(pooled(e, ["model", key, "rep"], cfg), ["model", key]).merge(timing(f, ["model", key]),
                                                                                  on=["model", key])
        tab.to_csv(RES / f"summary_{name}.csv", index=False, lineterminator="\n", float_format="%.4f")
        out[name] = {f"{r['model']}|{r[key]}": {k: r[f"{k}_mean"] for k in KEYS} for _, r in tab.iterrows()}

    # Features chosen by the ten-feature mutual-information selection of E5, counted over its training folds.
    e5, _ = load("E5_ablation_selection")
    if e5 is not None:
        groups = json.loads((config.DATASET_DIR / "features" / "feature_groups.json").read_text(encoding="utf-8"))
        group_of = {c: g for g, cols in groups.items() for c in cols}
        cv = pd.read_csv(config.DATASET_DIR / "splits" / "grouped_cv.csv", index_col="sample_id").loc[X.index]
        y = meta.loc[X.index, "label"].to_numpy().astype(int)
        counts, n_folds = {}, 0
        for r in sorted(e5["rep"].unique()):
            f = cv[f"rep{r}"].to_numpy()
            for k in sorted(set(f)):
                tr = np.where(f != k)[0]
                n_folds += 1
                for name in mutual_information_top(X.iloc[tr], y[tr], 10, cfg["random_state"]):
                    counts[name] = counts.get(name, 0) + 1
        sel = pd.DataFrame([{"feature": n, "group": group_of[n], "folds_selected": c, "folds": n_folds,
                             "median_trojan_inserted": X.loc[y == 1, n].median(),
                             "median_trojan_free": X.loc[y == 0, n].median(),
                             "missing_fraction": X[n].isna().mean()} for n, c in counts.items()])
        sel = sel.sort_values(["folds_selected", "feature"], ascending=[False, True])
        sel.to_csv(RES / "summary_E5_selected_features.csv", index=False, lineterminator="\n", float_format="%.4f")
        out["E5_selected_features"] = sel.set_index("feature")["folds_selected"].to_dict()

    with open(RES / "summary.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, sort_keys=True, default=float)
        fh.write("\n")
    print("wrote", sorted(p.name for p in RES.glob("summary_*.csv")))


if __name__ == "__main__":
    main()
