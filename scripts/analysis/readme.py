"""Write README.md from the dataset tables and the experiment summaries.

Usage:
  python -m scripts.analysis.readme
"""
from __future__ import annotations

import json

import pandas as pd

from ..common import config

RES = config.REPO / "experiments" / "results"
MODEL_ORDER = ["LR", "DT", "RF", "SVM", "KNN", "XGB", "MLP", "ET", "AB", "GNB", "LightGBM", "Dummy", "Size"]


def fmt(m, s):
    return f"{m:.3f} ± {s:.3f}" if pd.notna(s) else f"{m:.3f}"


def main():
    audit = json.loads((RES / "dataset_audit.json").read_text(encoding="utf-8"))
    meta = pd.read_csv(config.METADATA_DIR / "samples.csv")
    e1 = pd.read_csv(RES / "summary_E1.csv").set_index("model").reindex(MODEL_ORDER).dropna(how="all")
    comp = meta.groupby(["source", "label"]).size().unstack(fill_value=0)
    fam = meta.groupby(["family", "label"]).size().unstack(fill_value=0)
    names = {"trusthub": "Trust-Hub chip-level RTL", "ghost": "GHOST", "hayashi": "RISC-V and Web3 (Zenodo 11035341)"}

    lines = [
        "# MAX10-HTD",
        "",
        "MAX10-HTD is a benchmark of FPGA implementations of public hardware Trojan designs. Every design was "
        "compiled with Quartus Prime for the Altera MAX 10 device 10M50DAF484C7G with one fixed flow, and each "
        "implementation is described by features measured from the Quartus reports, from the post-fit netlist "
        "and from the RTL source. Each Trojan-inserted implementation is linked to the implementation of its "
        "Trojan-free reference and was compared with it structurally and in simulation.",
        "",
        "The hardware designs come from Trust-Hub, the GHOST benchmarks and the RISC-V and Web3 Trojan dataset; "
        "they are not redistributed here. `scripts/sources/fetch.py` downloads them from their original "
        "locations and checks every archive against `dataset/metadata/source_archives.csv`. The "
        "implementations, features, verification results, partitions and reference results are produced by "
        "this project. See `docs/provenance.md`.",
        "",
        "## Contents",
        "",
        f"- {audit['samples']} implementations: {audit['trojan_inserted']} Trojan-inserted and "
        f"{audit['trojan_free']} Trojan-free, in {audit['host_groups']} host groups and {audit['families']} "
        f"functional families.",
        f"- {audit['features']} features in {len(audit['features_per_group'])} groups "
        "(`docs/feature_dictionary.md`).",
        f"- Catalog of {audit['catalog_designs']} designs, of which {audit['compiled']} compiled; every "
        "excluded design is listed with its reason in `dataset/metadata/exclusions.csv`.",
        "",
        "| Source | Trojan-free | Trojan-inserted |",
        "|---|---:|---:|",
    ]
    for src, row in comp.iterrows():
        lines.append(f"| {names.get(src, src)} | {row.get(0, 0)} | {row.get(1, 0)} |")
    lines += ["", "| Family | Trojan-free | Trojan-inserted |", "|---|---:|---:|"]
    for f, row in fam.iterrows():
        lines.append(f"| {f} | {row.get(0, 0)} | {row.get(1, 0)} |")
    lines += [
        "",
        "## Measurement conditions",
        "",
        "- Device MAX 10 10M50DAF484C7G, Quartus Prime 25.1std.0 Lite Edition, fitter seed 1, configuration mode "
        "\"single uncompressed image with memory initialization\" so that HDL-initialized ROM and RAM can use M9K "
        "blocks.",
        "- Every top-level port except the clock ports is a virtual pin, as for an IP core compiled in its own "
        "project; clock ports are device pins. Clocks: 20 ns; input-to-output paths: 20 ns maximum delay.",
        "- Timing: slow 1200 mV 85 C model. `sta_fmax_mhz` is the unrestricted Fmax of the slowest clock; paths "
        "through virtual pins are Quartus estimates of the core delay.",
        "- Power: Power Analyzer defaults (12.5 % toggle rate for input pins, vectorless estimation of internal "
        "nodes). Virtual input pins carry no switching activity, so dynamic power reflects the clock network, "
        "clocked registers and memories, and logic that switches without input activity (for example free-running "
        "counters). These are estimates, not measurements.",
        "- Placement-dependent features (fitter, routing, timing, power) vary with the fitter seed; "
        "`experiments/results/seed_variance_*.csv` quantifies this for a subset compiled with seeds 1 to 3.",
        "",
        "## Layout",
        "",
        "| Path | Content |",
        "|---|---|",
        "| `dataset/features/features.csv` | one row per implementation, predictive features only |",
        "| `dataset/labels/labels.csv` | `label` 1 = Trojan-inserted, 0 = Trojan-free |",
        "| `dataset/metadata/samples.csv` | source, design, family, host group, reference, Trojan category, "
        "verification results (not for prediction) |",
        "| `dataset/metadata/catalog.json` | every cataloged design with its files and top-level module |",
        "| `dataset/metadata/verification.csv` | interface, structure and dormant-behavior comparison of each pair |",
        "| `dataset/metadata/exclusions.csv`, `excluded_items.csv` | designs and archive items left out, with reasons |",
        "| `dataset/splits/` | fixed partitions: grouped cross-validation and holdout keys |",
        "| `dataset/checksums/SHA256SUMS` | digests of every released data file |",
        "| `scripts/` | fetching, cataloging, Quartus automation, feature extraction, verification, assembly |",
        "| `ml/` | classifiers, fixed hyperparameters and their sources, preprocessing, metrics, experiments |",
        "| `experiments/` | saved predictions and result tables |",
        "| `docs/` | dataset description, feature dictionary, verification, provenance, reproduction |",
        "",
        "## Reference results",
        "",
        "Grouped cross-validation (E1): five repetitions of five-fold cross-validation in which a host design and "
        "all its variants are always on the same side of the split. Values are the mean ± standard deviation over "
        "the repetitions of metrics computed on the pooled out-of-fold predictions. The positive class is "
        "Trojan-inserted; the threshold is 0.5 on predicted probabilities (0 on the SVM decision function).",
        "",
        "| Model | Balanced accuracy | Recall | Specificity | Precision | ROC AUC | PR AUC (Trojan) | PR AUC (Trojan-free) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for m, r in e1.iterrows():
        lines.append(f"| {m} | {fmt(r.balanced_accuracy_mean, r.balanced_accuracy_std)} | "
                     f"{fmt(r.recall_mean, r.recall_std)} | {fmt(r.specificity_mean, r.specificity_std)} | "
                     f"{fmt(r.precision_mean, r.precision_std)} | {fmt(r.roc_auc_mean, r.roc_auc_std)} | "
                     f"{fmt(r.pr_auc_mean, r.pr_auc_std)} | {fmt(r.pr_auc_clean_mean, r.pr_auc_clean_std)} |")
    lines += [
        "",
        "Column definitions: balanced accuracy is the mean of recall and specificity; recall is the fraction of "
        "Trojan-inserted designs predicted as Trojan-inserted; specificity is the fraction of Trojan-free designs "
        "predicted as Trojan-free; precision is the fraction of designs predicted as Trojan-inserted that are; "
        "ROC AUC is the area under the receiver operating characteristic curve; PR AUC (Trojan) is the average "
        "precision for the Trojan-inserted class and PR AUC (Trojan-free) the average precision for the "
        "Trojan-free class. Dummy predicts the majority class; Size is logistic regression on the logarithm of "
        "the number of logic elements.",
        "",
        "## Reproduction",
        "",
        "Fast path from the shipped tables (Python 3.12, CPU only):",
        "",
        "```",
        "pip install -r requirements.txt",
        "python reproduce.py",
        "```",
        "",
        "Full path from the original archives, with Quartus Prime 25.1 Lite, the OSS CAD Suite (Yosys, Icarus "
        "Verilog) and 7-Zip: see `docs/reproduction.md`.",
        "",
        "## License and citation",
        "",
        "Code: MIT license (`LICENSE`). Data produced by this project (features, labels, metadata, partitions, "
        "results): CC BY 4.0 (`LICENSE-DATA`). Third-party designs keep their own terms and are not included. "
        "Citation metadata: `CITATION.cff`.",
        "",
    ]
    (config.REPO / "README.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("wrote README.md")


if __name__ == "__main__":
    main()
