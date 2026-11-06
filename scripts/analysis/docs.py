"""Write docs/dataset_description.md, docs/verification.md and docs/reproduction.md from the result files.

Usage:
  python -m scripts.analysis.docs
"""
from __future__ import annotations

import json

import pandas as pd

from ..common import config

RES = config.REPO / "experiments" / "results"
DOCS = config.REPO / "docs"


def table(df: pd.DataFrame) -> list[str]:
    cols = list(df.columns)
    out = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return out


def dataset_description(audit: dict, meta: pd.DataFrame, comp: pd.DataFrame) -> None:
    lines = ["# MAX10-HTD dataset description", "",
             "## Sample unit", "",
             "One row is one implementation: a design compiled with Quartus Prime 25.1 Lite for the MAX 10 "
             "device 10M50DAF484C7G with the fixed flow of `scripts/quartus/`. The label is the one given by the "
             "benchmark source (1 = Trojan-inserted, 0 = Trojan-free). Each Trojan-inserted implementation names "
             "the Trojan-free implementation of the same host in `clean_reference`.", "",
             "## Size", "",
             f"- Implementations: {audit['samples']} ({audit['trojan_inserted']} Trojan-inserted, "
             f"{audit['trojan_free']} Trojan-free); ratio {audit['imbalance_ratio']:.2f} Trojan-inserted per "
             "Trojan-free implementation.",
             f"- Host groups: {audit['host_groups']}; functional families: {audit['families']}.",
             f"- Features: {audit['features']} ({', '.join(f'{k} {v}' for k, v in audit['features_per_group'].items())}).",
             f"- Catalog: {audit['catalog_designs']} designs, {audit['compiled']} compiled "
             f"({100 * audit['compile_rate']:.1f}%).", "",
             "## Composition by source and family", ""]
    lines += table(comp.reset_index())
    lines += ["", "## Trojan categories reported by the sources", "",
              "Payload (effect) categories of the Trojan-inserted implementations; one implementation can carry "
              "several. The RISC-V and Web3 release does not report categories per file.", ""]
    lines += table(pd.DataFrame(sorted(audit["payload_categories"].items()), columns=["payload", "implementations"]))
    lines += ["", "Trigger categories:", ""]
    lines += table(pd.DataFrame(sorted(audit["trigger_categories"].items()), columns=["trigger", "implementations"]))
    lines += ["", "## Missing values", "",
              f"{audit['features_with_missing']} features have missing values; {100 * audit['missing_cells_fraction']:.2f}% "
              "of all cells are missing. A missing value means that the quantity is undefined for the design (for "
              "example, no register-to-register path, or a combinational cycle for the logic depth), that the RTL "
              "features could not be computed (VHDL sources) or that the Quartus report does not give the value; "
              "`docs/feature_dictionary.md` lists the case for each feature. Per-feature fractions: "
              "`experiments/results/audit_missingness.csv`.", "",
              "## Duplicates", "",
              f"- Identical feature rows: {audit['duplicate_feature_rows']} rows in {audit['duplicate_sets']} sets; "
              f"{audit['duplicate_sets_mixed_labels']} sets mix labels and {audit['duplicate_sets_across_host_groups']} "
              "span host groups.",
              f"- Near-duplicate Trojan-free designs merged into one host group: {audit['near_duplicate_clean_pairs']} pairs "
              "(`dataset/metadata/near_duplicates.csv`).", ""]
    DOCS.joinpath("dataset_description.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def verification(audit: dict) -> None:
    v = audit["verification"]
    lines = ["# Verification", "",
             "The labels are those of the benchmark sources. MAX10-HTD adds three checks of every Trojan-inserted "
             "implementation against the implementation of its Trojan-free reference "
             "(`scripts/verification/dormant.py`, results in `dataset/metadata/verification.csv`).", "",
             "1. Interface: the top-level ports of the two designs are compared.",
             "2. Structure: every post-fit netlist receives a fingerprint that ignores signal, instance and "
             "project names (cell types, parameter values and connections, refined over four rounds). A "
             "Trojan-inserted design with the fingerprint of a Trojan-free design is taken to carry no Trojan after "
             "synthesis and is excluded. Designs of the same class with identical fingerprints are kept once; of "
             "two Trojan-free designs with the same fingerprint, the copy from the source listed first (Trust-Hub, GHOST, RISC-V "
             "and Web3) is kept and is the reference of the Trojan-inserted designs of both.",
             "3. Dormant behavior: both netlists are simulated with Icarus Verilog and the Quartus MAX 10 models on "
             "the same pseudo-random inputs for 1000 clock cycles; inputs that only one design has are held at 0 and "
             "reset-like inputs are asserted for two cycles. The common outputs are compared in every cycle.", "",
             "What the checks do not show: identical outputs do not prove that a trigger can fire or that a payload "
             "works, and differing outputs do not identify the payload. Trigger activation and payloads are "
             "documented by the sources (GHOST reports testbench activation before and after synthesis); they "
             "were not re-verified. No design was programmed onto a physical board.", "",
             "## Outcomes for the included Trojan-inserted implementations", "",
             f"- Pairs verified: {v['pairs']}",
             f"- Identical interface: {v['interface_identical']}; extra inputs: {v['pairs_with_extra_inputs']}; extra "
             f"outputs: {v['pairs_with_extra_outputs']}",
             "- Dormant-behavior outcomes: " + ", ".join(f"{k} {n}" for k, n in sorted(v["dormant_check"].items())),
             f"- Median difference in post-fit cell count: {v['residual_cells_median']:.0f} cells; "
             f"{v['residual_cells_le_10']} pairs differ by at most 10 cells",
             "- Excluded because the netlist has the fingerprint of a Trojan-free design (inserted logic taken as "
             f"removed by synthesis): {audit['removed_by_synthesis']}",
             "- Trojan-inserted designs left out because their netlist has the fingerprint of another Trojan-inserted "
             f"design: {audit['identical_trojan_inserted_kept_once']}",
             "- Trojan-free designs left out because their netlist has the fingerprint of another Trojan-free design: "
             f"{audit['identical_trojan_free_kept_once']}", ""]
    DOCS.joinpath("verification.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def reproduction() -> None:
    lines = ["# Reproduction", "",
             "## Fast path (released tables, CPU only)", "",
             "Python 3.12 with the packages of `requirements.txt`:", "", "```",
             "pip install -r requirements.txt", "python reproduce.py", "```", "",
             "This reruns the audit, all experiments (about one hour on the laptop processor listed below), the "
             "summaries, the seed analysis, the figures and the README from `dataset/`. "
             "`python reproduce.py --experiments E1` runs one experiment.", "",
             "## Full path (from the original archives)", "",
             "Tools: Quartus Prime 25.1std Lite with MAX 10 device support (set `QUARTUS_ROOTDIR` to its `quartus` "
             "folder), the YosysHQ OSS CAD Suite for Yosys and Icarus Verilog (set `OSS_CAD_SUITE`), and 7-Zip "
             "(set `SEVEN_ZIP` or put `7z` on PATH). `MAX10HTD_BUILD` selects the scratch folder (default `build/`).",
             "", "```", "python reproduce.py --full", "```", "",
             "Steps: download and digest check of the archives (`scripts.sources.fetch`), catalog "
             "(`scripts.sources.catalog`), two-pass Quartus compilation (`scripts.quartus.compile`), pair "
             "verification (`scripts.verification.dormant`), feature extraction "
             "(`scripts.feature_extraction.build_features`), assembly (`scripts.validation.assemble`), the seed "
             "study compilations, then the fast path. Compiling all designs takes several hours; the flow time of "
             "every design is listed in `dataset/metadata/compilation.csv`.", "",
             "## Environment of the released results", "",
             "Windows 11 Enterprise, Intel Core Ultra 7 155U (12 cores, 14 threads), Python 3.12.10, Quartus Prime "
             "25.1std.0 Build 1129 Lite Edition, Yosys 0.70+309 and Icarus Verilog 14.0 (development snapshot "
             "s20260301) from the OSS CAD Suite of 2026-11-03, 7-Zip 26.02.", ""]
    DOCS.joinpath("reproduction.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main():
    audit = json.loads((RES / "dataset_audit.json").read_text(encoding="utf-8"))
    meta = pd.read_csv(config.METADATA_DIR / "samples.csv")
    comp = meta.assign(label=meta["label"].map({0: "Trojan-free", 1: "Trojan-inserted"})).groupby(
        ["source", "family", "label"]).size().unstack(fill_value=0)
    dataset_description(audit, meta, comp)
    verification(audit)
    reproduction()
    print("wrote docs")


if __name__ == "__main__":
    main()
