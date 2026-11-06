"""Classification metrics with the Trojan-inserted class as the positive class."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score, matthews_corrcoef, roc_auc_score


def _ratio(a: float, b: float) -> float:
    return a / b if b else float("nan")


def binary_metrics(y: np.ndarray, score: np.ndarray, thr: float) -> dict:
    """Threshold metrics at `thr` and ranking metrics from the continuous scores."""
    y = np.asarray(y).astype(int)
    score = np.asarray(score, dtype=float)
    pred = (score > thr).astype(int) if thr == 0.0 else (score >= thr).astype(int)
    tp = int(((pred == 1) & (y == 1)).sum())
    tn = int(((pred == 0) & (y == 0)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    n = len(y)
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    specificity = _ratio(tn, tn + fp)
    both = len(set(y.tolist())) == 2
    return {
        "n": n, "positives": int(y.sum()), "negatives": int(n - y.sum()), "prevalence": _ratio(int(y.sum()), n),
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "accuracy": _ratio(tp + tn, n),
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": _ratio(2 * tp, 2 * tp + fp + fn),
        "fpr": _ratio(fp, fp + tn),
        "fnr": _ratio(fn, fn + tp),
        "balanced_accuracy": np.nanmean([recall, specificity]) if both else float("nan"),
        "mcc": matthews_corrcoef(y, pred) if both else float("nan"),
        "pr_auc": average_precision_score(y, score) if both else float("nan"),
        "pr_auc_clean": average_precision_score(1 - y, -score) if both else float("nan"),
        "roc_auc": roc_auc_score(y, score) if both else float("nan"),
    }
