"""Run the MAX10-HTD benchmark experiments with the fixed classifier configurations.

The positive class is the Trojan-inserted design.  Every model is fitted on a
training partition and scored on the held-out partition; preprocessing is
fitted on the training partition only.

Experiments (numbered as in the evaluation protocol)
  E1  baseline detection with grouped cross-validation: 5 repetitions of
      5-fold cross-validation in which a host group (a Trojan-free design, its
      near duplicates and all their Trojan-inserted variants) never spans
      training and test data; E1b repeats it with design groups, which also
      merge a module with the larger designs that contain its sources
  E2  unseen host families: leave one functional family out (E2a) and leave
      one benchmark source out (E2b); for E2b, host groups that occur in the
      held-out source are removed from the training data
  E3  unseen Trojan categories: Trojan-inserted designs of one payload category
      are held out of training and form the positive test class; a control run
      keeps that category in the training folds (sources with published
      payload categories only)
  E4  structural against Quartus-derived features: each feature group alone,
      all Quartus report groups together and both structural groups together
  E5  feature-group ablation (all groups but one) and feature selection (the
      k features with the highest mutual information with the label in the
      training fold)
  E6  class balance of the training data: class weights, random undersampling
      of Trojan-inserted designs, random oversampling of Trojan-free designs
      (the natural distribution is E1)
  E7  sensitivity to circuit complexity: computed from the E1 predictions by
      scripts.analysis (no extra training)
  C1  interface control: E1 without the features that count top-level ports

Usage:
  python -m ml.training.run_experiments [--experiments E1,E2] [--models LR,RF] [--reps 5]

Writes experiments/predictions/<experiment>.csv and experiments/results/<experiment>_folds.csv.
"""
from __future__ import annotations

import argparse
import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_selection import mutual_info_classif

from ..evaluation.metrics import binary_metrics
from ..models import zoo
from ..preprocessing.transform import preprocessor

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "dataset"
OUT = REPO / "experiments"
ALL = list(zoo.MODELS) + list(zoo.BASELINES)
PORT_FEATURES = ["net_pi_bits", "net_po_bits", "net_pins", "fit_io_pins", "syn_io_pins"]
PAYLOADS = ["change-functionality", "denial-of-service", "leak-information"]
SELECT_K = (10, 25, 50)
# Repetitions of the grouped cross-validation per experiment; the feature-set experiments use
# two repetitions to bound the running time.
REPS = {"E1": 5, "E4": 2, "E5": 2, "E6": 5, "C1": 5}


def load():
    X = pd.read_csv(DATA / "features" / "features.csv", index_col="sample_id")
    meta = pd.read_csv(DATA / "metadata" / "samples.csv", index_col="sample_id").loc[X.index]
    cv = pd.read_csv(DATA / "splits" / "grouped_cv.csv", index_col="sample_id").loc[X.index]
    cvd = pd.read_csv(DATA / "splits" / "grouped_cv_design.csv", index_col="sample_id").loc[X.index]
    groups = json.loads((DATA / "features" / "feature_groups.json").read_text(encoding="utf-8"))
    return X, meta, cv, cvd, groups


def fit_score(name, Xtr, ytr, Xte, cfg, weights=None):
    """Fit one model on the training rows and return test scores and timings."""
    cols = ["fit_le"] if name == "Size" else list(Xtr.columns)
    pre = preprocessor().fit(Xtr[cols].to_numpy(dtype=float))
    A = pre.transform(Xtr[cols].to_numpy(dtype=float))
    B = pre.transform(Xte[cols].to_numpy(dtype=float))
    model = zoo.build(name, n_train=A.shape[0], p=A.shape[1], cfg=cfg)
    fit_kw = {}
    if weights is not None:
        step = model.steps[-1][0] if hasattr(model, "steps") else None
        fit_kw = {f"{step}__sample_weight" if step else "sample_weight": weights}
    t0 = time.perf_counter()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        model.fit(A, ytr, **fit_kw)
    t_fit = time.perf_counter() - t0
    t0 = time.perf_counter()
    s = zoo.scores(model, B)
    t_pred = time.perf_counter() - t0
    return s, t_fit, t_pred


def run_partition(models, X, y, train_idx, test_idx, cfg, tag: dict, weights=None, rows=None, folds=None):
    """Score every model on one train/test partition and append predictions and fold metrics."""
    for name in models:
        w = None
        if weights is not None and name not in ("KNN", "Dummy"):
            w = weights
        s, t_fit, t_pred = fit_score(name, X.iloc[train_idx], y[train_idx], X.iloc[test_idx], cfg, w)
        thr = zoo.threshold(name, cfg)
        for sid, yy, sc in zip(X.index[test_idx], y[test_idx], s):
            rows.append({**tag, "model": name, "sample_id": sid, "label": int(yy), "score": float(sc),
                         "pred": int(sc > thr) if thr == 0.0 else int(sc >= thr)})
        m = binary_metrics(y[test_idx], s, thr)
        folds.append({**tag, "model": name, "n_train": len(train_idx), "fit_seconds": t_fit,
                      "predict_seconds": t_pred, "predict_seconds_per_design": t_pred / max(1, len(test_idx)), **m})


def save(name: str, rows: list, folds: list) -> None:
    (OUT / "predictions").mkdir(parents=True, exist_ok=True)
    (OUT / "results").mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT / "predictions" / f"{name}.csv", index=False, lineterminator="\n",
                              float_format="%.6g")
    pd.DataFrame(folds).to_csv(OUT / "results" / f"{name}_folds.csv", index=False, lineterminator="\n",
                               float_format="%.6g")


def grouped_cv(models, X, y, cv, cfg, reps, tag=None, select=None, weights_fn=None, resample=None):
    rows, folds = [], []
    tag = tag or {}
    for r in range(reps):
        f = cv[f"rep{r}"].to_numpy()
        for k in sorted(set(f)):
            tr, te = np.where(f != k)[0], np.where(f == k)[0]
            Xc = X
            if select is not None:
                Xc = X[select(X.iloc[tr], y[tr])]
            w = weights_fn(y[tr]) if weights_fn else None
            if resample is not None:
                tr = resample(tr, y, r, k)
                w = weights_fn(y[tr]) if weights_fn else None
            run_partition(models, Xc, y, tr, te, cfg, {**tag, "rep": r, "fold": int(k)}, w, rows, folds)
    return rows, folds


def holdout(models, X, y, key: pd.Series, cfg, groups: pd.Series, tag_name: str, exclude_shared=False):
    rows, folds = [], []
    for value in sorted(key.dropna().unique()):
        te = np.where(key.to_numpy() == value)[0]
        tr_mask = key.to_numpy() != value
        if exclude_shared:
            shared = set(groups.iloc[te])
            tr_mask &= ~groups.isin(shared).to_numpy()
        tr = np.where(tr_mask)[0]
        if len(set(y[tr])) < 2:
            continue
        run_partition(models, X, y, tr, te, cfg, {tag_name: value, "rep": 0, "fold": str(value)}, None, rows, folds)
    return rows, folds


def mutual_information_top(Xtr: pd.DataFrame, ytr, k: int, random_state: int) -> list[str]:
    """The k features with the highest mutual information with the label, estimated after preprocessing."""
    pre = preprocessor().fit(Xtr.to_numpy(dtype=float))
    names = pre.get_feature_names_out(list(Xtr.columns))
    mi = mutual_info_classif(pre.transform(Xtr.to_numpy(dtype=float)), ytr, random_state=random_state)
    return [n for n, _ in sorted(zip(names, mi), key=lambda t: -t[1]) if n in Xtr.columns][:k]


def balanced_weights(y):
    n, n1 = len(y), int(y.sum())
    w1, w0 = n / (2.0 * n1), n / (2.0 * (n - n1))
    return np.where(y == 1, w1, w0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiments", default="E1,E2,E3,E4,E5,E6,C1")
    ap.add_argument("--models", default=",".join(ALL))
    ap.add_argument("--reps", type=int, default=0, help="override the repetitions of every experiment")
    args = ap.parse_args()
    cfg = zoo.load_config()
    X, meta, cv, cvd, groups = load()
    y = meta["label"].to_numpy().astype(int)
    models = args.models.split(",")
    chosen = set(args.experiments.split(","))

    def reps(name):
        return args.reps or REPS[name]
    (OUT / "configs").mkdir(parents=True, exist_ok=True)
    (OUT / "configs" / "experiments.json").write_text(json.dumps({
        "positive_class": "Trojan-inserted (label 1)",
        "models": models, "repetitions": {k: reps(k) for k in REPS}, "folds": 5,
        "partitions": {"E1": "dataset/splits/grouped_cv.csv", "E1b": "dataset/splits/grouped_cv_design.csv",
                       "E2a": "family in dataset/metadata/samples.csv", "E2b": "source in dataset/metadata/samples.csv",
                       "E3": "rep0 of dataset/splits/grouped_cv.csv, sources trusthub and ghost"},
        "payload_categories": PAYLOADS, "selection_k": list(SELECT_K), "port_count_features": PORT_FEATURES,
        "preprocessing": "signed log1p, training-median imputation with missing indicators, constant columns removed",
        "thresholds": "0.5 on probabilities, 0 on the SVM decision function",
        "hyperparameters": "ml/configs/model_hyperparameters.yaml"}, indent=1) + "\n", encoding="utf-8")
    # The two baselines do not depend on the feature set; they are run where all features are used.
    learners = [m for m in models if m not in zoo.BASELINES]

    if "E1" in chosen:
        save("E1_grouped_cv", *grouped_cv(models, X, y, cv, cfg, reps("E1")))
        save("E1b_design_grouped_cv", *grouped_cv(models, X, y, cvd, cfg, reps("E1")))

    if "E2" in chosen:
        save("E2a_family_holdout", *holdout(models, X, y, meta["family"], cfg, meta["host_group"], "family"))
        save("E2b_source_holdout", *holdout(models, X, y, meta["source"], cfg, meta["host_group"], "source",
                                           exclude_shared=True))

    if "E3" in chosen:
        rows, folds = [], []
        known = meta["source"].isin(["trusthub", "ghost"]).to_numpy()
        pay = meta["payload"].fillna("").astype(str)
        f0 = cv["rep0"].to_numpy()
        for p in PAYLOADS:
            has = pay.str.contains(p, regex=False).to_numpy() & (y == 1)
            for k in sorted(set(f0)):
                # Test: Trojan-free designs of fold k and Trojan-inserted designs of category p in fold k.
                # Training (unseen): designs outside fold k with known categories, without category p.
                # Training (seen_control): the same designs with category p kept.
                te = np.where(known & (f0 == k) & ((y == 0) | has))[0]
                if len(te) == 0 or not has[te].any():
                    continue
                for variant, tr in (("unseen", np.where(known & (f0 != k) & ~has)[0]),
                                    ("seen_control", np.where(known & (f0 != k))[0])):
                    if len(set(y[tr])) < 2:
                        continue
                    run_partition(models, X, y, tr, te, cfg, {"payload": p, "variant": variant, "rep": 0,
                                                              "fold": int(k)}, None, rows, folds)
        save("E3_unseen_payload", rows, folds)

    if "E4" in chosen:
        rows, folds = [], []
        sets = {f"only:{g}": cols for g, cols in groups.items()}
        sets["only:quartus_reports"] = [c for g, cols in groups.items() if g.startswith("quartus_") for c in cols]
        sets["only:structural"] = groups["netlist_structure"] + groups["rtl_structure"]
        for label, cols in sets.items():
            r_, f_ = grouped_cv(learners, X[cols], y, cv, cfg, reps("E4"), tag={"feature_set": label})
            rows += r_
            folds += f_
        save("E4_feature_groups", rows, folds)

    if "E5" in chosen:
        rows, folds = [], []
        for g, gcols in groups.items():
            cols = [c for c in X.columns if c not in gcols]
            r_, f_ = grouped_cv(learners, X[cols], y, cv, cfg, reps("E5"), tag={"feature_set": f"without:{g}"})
            rows += r_
            folds += f_

        def top_k(k):
            def select(Xtr, ytr):
                return mutual_information_top(Xtr, ytr, k, cfg["random_state"])
            return select
        for k in SELECT_K:
            r_, f_ = grouped_cv(learners, X, y, cv, cfg, reps("E5"), tag={"feature_set": f"mutual_information_top{k}"},
                                select=top_k(k))
            rows += r_
            folds += f_
        save("E5_ablation_selection", rows, folds)

    if "E6" in chosen:
        rows, folds = [], []
        rng_seed = cfg["random_state"]

        def under(tr, yy, r, k):
            rng = np.random.default_rng(rng_seed + 100 * r + k)
            pos, neg = tr[yy[tr] == 1], tr[yy[tr] == 0]
            return np.sort(np.concatenate([neg, rng.choice(pos, size=min(len(pos), len(neg)), replace=False)]))

        def over(tr, yy, r, k):
            rng = np.random.default_rng(rng_seed + 100 * r + k)
            pos, neg = tr[yy[tr] == 1], tr[yy[tr] == 0]
            extra = rng.choice(neg, size=max(0, len(pos) - len(neg)), replace=True)
            return np.sort(np.concatenate([tr, extra]))
        for label, kw in (("class_weights", {"weights_fn": balanced_weights}),
                          ("undersample_trojan", {"resample": under}),
                          ("oversample_clean", {"resample": over})):
            r_, f_ = grouped_cv(learners, X, y, cv, cfg, reps("E6"), tag={"balance": label}, **kw)
            rows += r_
            folds += f_
        save("E6_class_balance", rows, folds)

    if "C1" in chosen:
        cols = [c for c in X.columns if c not in PORT_FEATURES]
        save("C1_without_port_counts", *grouped_cv(learners, X[cols], y, cv, cfg, reps("C1"),
                                                   tag={"feature_set": "without_port_counts"}))


if __name__ == "__main__":
    main()
