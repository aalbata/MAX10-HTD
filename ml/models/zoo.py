"""Classifiers of the MAX10-HTD reference baselines with their fixed configurations.

The configurations are read from ml/configs/model_hyperparameters.yaml.  Values
that depend on the training fold (the number of training rows and of feature
columns) are evaluated when a model is built for a fold.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import yaml
from lightgbm import LGBMClassifier
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import AdaBoostClassifier, BaggingClassifier, ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

CONFIG = Path(__file__).resolve().parents[1] / "configs" / "model_hyperparameters.yaml"
MODELS = ("LR", "DT", "RF", "SVM", "KNN", "XGB", "MLP", "ET", "AB", "GNB", "LightGBM")
BASELINES = ("Dummy", "Size")


def load_config(path: Path = CONFIG) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class KknnOptimalWeights:
    """Rank weights of the kknn 'optimal' kernel for k neighbors and d features.

    w_i = (1/k) (1 + d/2 - d / (2 k^(2/d)) (i^(1+2/d) - (i-1)^(1+2/d))), i = 1..k,
    as computed by the kknn function optKernel; the nearest neighbor comes first.
    """

    def __init__(self, n_features: int):
        self.n_features = n_features

    def __call__(self, dist: np.ndarray) -> np.ndarray:
        k = dist.shape[1]
        d = float(self.n_features)
        i = np.arange(1, k + 1, dtype=float)
        w = (1 + d / 2 - d / (2 * k ** (2 / d)) * (i ** (1 + 2 / d) - (i - 1) ** (1 + 2 / d))) / k
        return np.tile(w, (dist.shape[0], 1))


def build(name: str, n_train: int, p: int, cfg: dict | None = None):
    """Untrained estimator for one training fold with n_train rows and p feature columns."""
    cfg = cfg or load_config()
    seed, n_jobs = cfg["random_state"], cfg["n_jobs"]
    if name == "LR":
        m = cfg["models"]["LR"]["params"]
        est = LogisticRegression(l1_ratio=m["l1_ratio"], C=1.0 / (0.004 * n_train), solver=m["solver"],
                                 max_iter=m["max_iter"], random_state=seed)
        return make_pipeline(StandardScaler(), est)
    if name == "DT":
        return DecisionTreeClassifier(**cfg["models"]["DT"]["params"], random_state=seed)
    if name == "RF":
        m = dict(cfg["models"]["RF"]["params"])
        m.pop("estimator")
        tree = DecisionTreeClassifier(criterion="gini", max_features=min(p, math.ceil(0.257 * p)))
        return BaggingClassifier(estimator=tree, **m, random_state=seed, n_jobs=n_jobs)
    if name == "SVM":
        return make_pipeline(StandardScaler(), SVC(**cfg["models"]["SVM"]["params"]))
    if name == "KNN":
        m = cfg["models"]["KNN"]["params"]
        k = min(m["n_neighbors"], n_train)
        return make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=k, metric=m["metric"], p=m["p"],
                                                                    weights=KknnOptimalWeights(p)))
    if name == "XGB":
        return XGBClassifier(**cfg["models"]["XGB"]["params"], random_state=seed, n_jobs=n_jobs)
    if name == "MLP":
        return make_pipeline(StandardScaler(), MLPClassifier(random_state=seed))
    if name == "ET":
        return ExtraTreesClassifier(random_state=seed, n_jobs=n_jobs)
    if name == "AB":
        return AdaBoostClassifier(random_state=seed)
    if name == "GNB":
        return GaussianNB()
    if name == "LightGBM":
        return LGBMClassifier(**cfg["models"]["LightGBM"]["params"], n_jobs=n_jobs, random_state=seed)
    if name == "Dummy":
        return DummyClassifier(strategy="most_frequent")
    if name == "Size":
        return make_pipeline(StandardScaler(), LogisticRegression())
    raise KeyError(name)


def scores(model, X: np.ndarray) -> np.ndarray:
    """Continuous score for the positive class (Trojan-inserted); larger means more likely Trojan."""
    if hasattr(model, "predict_proba"):
        try:
            return model.predict_proba(X)[:, 1]
        except AttributeError:
            pass
    return model.decision_function(X)


def threshold(name: str, cfg: dict | None = None) -> float:
    """Decision threshold on the score: 0 for decision functions, 0.5 for probabilities."""
    cfg = cfg or load_config()
    return 0.0 if cfg["models"].get(name, {}).get("score") == "decision_function" else 0.5
