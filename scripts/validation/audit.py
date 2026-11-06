"""Dataset audit of MAX10-HTD: composition, compilation and verification outcomes,
missing values, duplicates, near duplicates and associations between the label
and simple design properties.

Usage:
  python -m scripts.validation.audit

Writes experiments/results/dataset_audit.json and the CSV tables
experiments/results/audit_*.csv.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr

from ..common import config

OUT = config.REPO / "experiments" / "results"
PORT_FEATURES = ["net_pi_bits", "net_po_bits"]


def compile_table() -> pd.DataFrame:
    ct = pd.read_csv(config.METADATA_DIR / "compilation.csv", keep_default_na=False)
    ct["ok"] = ct["compiled"].astype(int) == 1
    return ct


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = json.loads((config.METADATA_DIR / "catalog.json").read_text(encoding="utf-8"))["samples"]
    meta = pd.read_csv(config.METADATA_DIR / "samples.csv", index_col="sample_id")
    X = pd.read_csv(config.DATASET_DIR / "features" / "features.csv", index_col="sample_id").loc[meta.index]
    ver = pd.read_csv(config.METADATA_DIR / "verification.csv", index_col="sample_id")
    excl = pd.read_csv(config.METADATA_DIR / "exclusions.csv")
    groups = json.loads((config.DATASET_DIR / "features" / "feature_groups.json").read_text(encoding="utf-8"))
    y = meta["label"]
    audit = {}

    # Composition.
    comp = meta.groupby(["source", "family", "label"]).size().unstack("label", fill_value=0)
    comp.columns = [f"label_{c}" for c in comp.columns]
    comp.to_csv(OUT / "audit_composition.csv", lineterminator="\n")
    audit["samples"] = int(len(meta))
    audit["trojan_inserted"] = int(y.sum())
    audit["trojan_free"] = int((1 - y).sum())
    audit["imbalance_ratio"] = float(y.sum() / (1 - y).sum())
    audit["host_groups"] = int(meta["host_group"].nunique())
    audit["families"] = int(meta["family"].nunique())
    audit["sources"] = meta.groupby("source")["label"].agg(["size", "sum"]).rename(
        columns={"size": "samples", "sum": "trojan_inserted"}).to_dict(orient="index")
    audit["designs_per_family"] = meta.groupby("family")["design"].nunique().to_dict()
    audit["host_groups_per_family"] = meta.groupby("family")["host_group"].nunique().to_dict()
    audit["features"] = int(X.shape[1])
    audit["features_per_group"] = {g: len(c) for g, c in groups.items()}
    tro = meta[meta["label"] == 1]
    audit["payload_categories"] = tro["payload"].fillna("not-reported").value_counts().to_dict()
    audit["trigger_categories"] = tro["trigger"].fillna("not-reported").value_counts().to_dict()

    # Compilation.
    ct = compile_table()
    ct.to_csv(OUT / "audit_compilation.csv", index=False, lineterminator="\n")
    audit["catalog_designs"] = int(len(ct))
    audit["compiled"] = int(ct["ok"].sum())
    audit["compile_rate"] = float(ct["ok"].mean())
    audit["compile_by_source"] = ct.groupby(["source", "role"])["ok"].agg(["size", "sum"]).rename(
        columns={"size": "designs", "sum": "compiled"}).reset_index().to_dict(orient="records")
    audit["failed_stage"] = ct.loc[~ct["ok"], "failed_stage"].value_counts().to_dict()
    audit["exclusion_reasons"] = excl["reason"].value_counts().to_dict()

    # Verification of the included Trojan-inserted designs.
    v = ver.loc[ver.index.intersection(tro.index)]
    audit["verification"] = {
        "pairs": int(len(v)),
        "interface_identical": int(v["interface_identical"].sum()),
        "pairs_with_extra_inputs": int((v["extra_inputs"] > 0).sum()),
        "pairs_with_extra_outputs": int((v["extra_outputs"] > 0).sum()),
        "dormant_check": v["dormant_check"].value_counts().to_dict(),
        "residual_cells_median": float((v["cells_trojan"] - v["cells_clean"]).median()),
        "residual_cells_le_10": int(((v["cells_trojan"] - v["cells_clean"]).abs() <= 10).sum()),
    }
    reason = excl["reason"]
    audit["removed_by_synthesis"] = int(reason.str.startswith("post-fit netlist identical to a Trojan-free").sum())
    audit["identical_trojan_inserted_kept_once"] = int(
        reason.str.startswith("post-fit netlist identical to another Trojan-inserted").sum())
    audit["identical_trojan_free_kept_once"] = int(
        reason.str.startswith("post-fit netlist identical to another Trojan-free").sum())

    # Missing values.
    miss = X.isna().mean()
    miss_tab = pd.DataFrame({"missing_fraction": miss, "missing_trojan_free": X[y == 0].isna().mean(),
                             "missing_trojan_inserted": X[y == 1].isna().mean()})
    miss_tab.to_csv(OUT / "audit_missingness.csv", lineterminator="\n", float_format="%.4f")
    audit["features_with_missing"] = int((miss > 0).sum())
    audit["missing_cells_fraction"] = float(X.isna().to_numpy().mean())

    # Duplicates.
    filled = X.fillna(-1e30).round(9)
    dup = filled.duplicated(keep=False)
    dup_groups = filled[dup].groupby(list(filled.columns)).groups
    cross_label = 0
    cross_group = 0
    for idx in dup_groups.values():
        idx = list(idx)
        if meta.loc[idx, "label"].nunique() > 1:
            cross_label += 1
        if meta.loc[idx, "host_group"].nunique() > 1:
            cross_group += 1
    audit["duplicate_feature_rows"] = int(dup.sum())
    audit["duplicate_sets"] = int(len(dup_groups))
    audit["duplicate_sets_mixed_labels"] = int(cross_label)
    audit["duplicate_sets_across_host_groups"] = int(cross_group)
    nd = pd.read_csv(config.METADATA_DIR / "near_duplicates.csv")
    audit["near_duplicate_clean_pairs"] = int(len(nd))

    # Associations between the label and simple properties.
    assoc = []
    for col in ["fit_le", "fit_registers", "net_lcells", "pow_total_mw", "sta_fmax_mhz"] + PORT_FEATURES:
        a, b = X.loc[y == 1, col].dropna(), X.loc[y == 0, col].dropna()
        u = mannwhitneyu(a, b) if len(a) and len(b) else None
        assoc.append({"feature": col, "median_trojan_inserted": float(a.median()), "median_trojan_free": float(b.median()),
                      "auc_univariate": float(u.statistic / (len(a) * len(b))) if u else np.nan,
                      "mannwhitney_p": float(u.pvalue) if u else np.nan})
    pd.DataFrame(assoc).to_csv(OUT / "audit_label_associations.csv", index=False, lineterminator="\n",
                               float_format="%.4g")

    # Paired differences within host groups (Trojan-inserted minus its reference).
    paired = []
    for sid, row in tro.iterrows():
        ref = row["clean_reference"]
        if ref in X.index:
            paired.append(X.loc[sid] - X.loc[ref])
    pdiff = pd.DataFrame(paired)
    pd.DataFrame({"median_difference": pdiff.median(), "fraction_positive": (pdiff > 0).mean(),
                  "fraction_zero": (pdiff == 0).mean(), "fraction_negative": (pdiff < 0).mean()}).to_csv(
        OUT / "audit_paired_differences.csv", lineterminator="\n", float_format="%.4g")

    # Feature correlation with design size.
    size = np.log1p(X["fit_le"])
    corr = {}
    for c in X.columns:
        col = X[c]
        ok = col.notna()
        if ok.sum() > 10 and col[ok].nunique() > 1:
            corr[c] = float(spearmanr(size[ok], col[ok]).statistic)
    pd.Series(corr, name="spearman_with_log_le").to_csv(OUT / "audit_size_correlation.csv", lineterminator="\n",
                                                        float_format="%.4f")
    audit["features_strongly_size_correlated"] = int(sum(abs(v) >= 0.8 for v in corr.values()))

    X.describe().T.to_csv(OUT / "audit_feature_summary.csv", lineterminator="\n", float_format="%.6g")
    with open(OUT / "dataset_audit.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(audit, fh, indent=1, sort_keys=True, default=lambda o: o.item() if hasattr(o, "item") else str(o))
        fh.write("\n")
    print(json.dumps({k: audit[k] for k in ("samples", "trojan_inserted", "trojan_free", "host_groups", "families",
                                            "compile_rate", "duplicate_feature_rows")}, indent=1))


if __name__ == "__main__":
    main()
