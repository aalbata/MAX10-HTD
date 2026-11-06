"""Feature preprocessing fitted on the training fold only.

1. Signed logarithm x -> sign(x) log(1 + |x|).  Most features are counts,
   delays or powers with long right tails; the transform is monotonic, so it
   leaves tree-based models unchanged and makes distances and linear terms less
   dominated by the largest designs.
2. Median imputation with the training-fold medians, plus one indicator column
   for every feature that has missing values in the training fold.  A missing
   value means that the quantity does not exist for the design (for example no
   register-to-register path); the indicator keeps that information.
3. Removal of columns that are constant in the training fold.
"""
from __future__ import annotations

import numpy as np
from sklearn.feature_selection import VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer


def signed_log1p(x):
    return np.sign(x) * np.log1p(np.abs(x))


def preprocessor() -> Pipeline:
    return Pipeline([
        ("log", FunctionTransformer(signed_log1p, feature_names_out="one-to-one")),
        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
        ("constant", VarianceThreshold(0.0)),
    ])
