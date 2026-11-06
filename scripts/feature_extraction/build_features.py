"""Assemble the feature table and the feature dictionary.

Usage:
  python -m scripts.feature_extraction.build_features [--compiled DIR] [--jobs N] [--only IDS] [--out CSV]
                                                      [--dictionary-only]

Reads dataset/metadata/catalog.json and, for every sample that compiled, the
Quartus outputs in <compiled>/<sample_id>/ and the design sources prepared by
the compile step.  Writes
  <build>/features_all.csv             one row per compiled sample, predictive features only
                                       (scripts.validation.assemble selects the benchmark rows)
  dataset/features/feature_groups.json feature names per group
  docs/feature_dictionary.md           name, group, unit, source and definition
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from ..common import config
from ..common.util import sha256_file
from . import netlist_features, quartus_features, rtl_features

GROUP_OF_PREFIX = {
    "syn_": "quartus_synthesis",
    "fit_": "quartus_fitter",
    "rte_": "quartus_routing",
    "sta_": "quartus_timing",
    "pow_": "quartus_power",
    "net_": "netlist_structure",
    "rtl_": "rtl_structure",
}
GROUP_TEXT = {
    "quartus_synthesis": "Analysis & Synthesis reports (resource estimates, register and multiplexer statistics, LUT depth)",
    "quartus_fitter": "Fitter reports (placed resource usage, LAB statistics, control signals, fan-out)",
    "quartus_routing": "Fitter routing usage by interconnect type",
    "quartus_timing": "Timing Analyzer, slow 1200 mV 85 C model, 20 ns constraint",
    "quartus_power": "Power Analyzer with default settings (12.5 % toggle rate for input pins, vectorless estimation of internal nodes); virtual input pins carry no switching activity, so the dynamic estimate reflects the clock network, clocked registers and memories, and logic that switches without input activity",
    "netlist_structure": "Post-fit Verilog netlist: cell counts, fan-out, depth, connectivity, COP and SCOAP testability",
    "rtl_structure": "Yosys word-level elaboration of the Verilog source",
}
MISSING = {
    "sta_fmax_mhz": "no clock or no register-to-register path",
    "sta_in2out_max_ns": "no combinational path from an input to an output",
    "sta_in2reg_max_ns": "no path from an input to a register",
    "sta_reg2reg_max_ns": "no register-to-register path",
    "sta_reg2out_max_ns": "no path from a register to an output",
    "sta_setup_slack_ns": "no constrained path",
    "sta_hold_slack_ns": "no constrained path",
    "sta_mc_setup_slack_ns": "no constrained path",
    "sta_mc_hold_slack_ns": "no constrained path",
    "syn_le_est": "not reported when synthesis leaves no logic element",
    "fit_lab_avg_inputs": "not reported when the Fitter writes no LAB Distinct Inputs panel",
    "net_depth_max": "combinational cycle through logic cells",
    "net_depth_mean": "combinational cycle through logic cells",
    "net_depth_nocarry_max": "combinational cycle through logic cells",
}
TESTABILITY_MISSING = "combinational cycle through logic cells, or no logic cell with inputs"
RTL_MISSING = "VHDL design (Yosys reads Verilog only)"


def all_features() -> dict:
    out = {}
    for name, (unit, source, text) in quartus_features.FEATURES.items():
        out[name] = (unit, "Quartus report: " + source, text)
    for name, (unit, text) in netlist_features.FEATURES.items():
        out[name] = (unit, "Post-fit netlist (quartus_eda)", text)
    for name, (unit, text) in rtl_features.FEATURES.items():
        out[name] = (unit, "Yosys RTL elaboration", text)
    return out


def group_of(name: str) -> str:
    for prefix, group in GROUP_OF_PREFIX.items():
        if name.startswith(prefix):
            return group
    raise KeyError(name)


def write_dictionary(path: Path) -> None:
    feats = all_features()
    lines = ["# MAX10-HTD feature dictionary", "",
             "Every feature is a design-level number computed from one compiled design. "
             "Missing values (empty cells in features.csv) mean that the quantity is undefined for the design or "
             "that the vendor report does not give it; the last column lists the cases.", "",
             "## Feature groups", ""]
    for g, text in GROUP_TEXT.items():
        n = sum(group_of(k) == g for k in feats)
        lines.append(f"- `{g}` ({n} features): {text}")
    lines += ["", "## Features", "",
              "| Feature | Group | Unit | Extraction source | Definition | Missing when |",
              "|---|---|---|---|---|---|"]
    for name, (unit, source, text) in feats.items():
        miss = MISSING.get(name, MISSING.get(name.replace("_min_ns", "_max_ns").replace("_levels", "_max_ns"), ""))
        if name.startswith(("net_sp_", "net_cc", "net_co")):
            miss = TESTABILITY_MISSING
        elif name.startswith("rtl_"):
            miss = RTL_MISSING
        lines.append(f"| `{name}` | {group_of(name)} | {unit} | {source} | {text} | {miss} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def sample_row(sample: dict, compiled: Path) -> dict | None:
    """Feature row of one compiled design, or None when the compilation did not succeed."""
    sid = sample["sample_id"]
    d = compiled / sid
    status = json.loads((d / "compile_status.json").read_text()) if (d / "compile_status.json").exists() else {}
    if not status.get("ok"):
        return None
    # Cached rows are reused while the netlist, the reports and the extractor code are unchanged.
    key = "|".join([status.get("netlist_sha256", ""), sha256_file(d / "panels.tsv"), sha256_file(d / "timing.tsv"),
                    *(sha256_file(Path(m.__file__)) for m in (quartus_features, netlist_features, rtl_features))])
    cache = d / "features.json"
    if cache.exists():
        old = json.loads(cache.read_text())
        if old.get("key") == key:
            return old["row"]
    row = {"sample_id": sid}
    row.update(quartus_features.extract(d))
    row.update(netlist_features.extract(d / "postfit.vo"))
    src = config.BUILD / "quartus" / f"{sid}_s{status.get('seed', config.FITTER_SEED)}" / "src"
    files = [src / Path(f).name for f in sample["files"]]
    row.update(rtl_features.extract(files, sample["top"], config.BUILD / "yosys" / f"{sid}_s{status.get('seed', 1)}",
                                    include_dir=src, systemverilog=status.get("hdl_version") == "SYSTEMVERILOG_2005"))
    cache.write_text(json.dumps({"key": key, "row": row}, allow_nan=True))
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--compiled", default=str(config.BUILD / "compiled"))
    ap.add_argument("--dictionary-only", action="store_true")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default=str(config.BUILD / "features_all.csv"))
    args = ap.parse_args()
    write_dictionary(config.REPO / "docs" / "feature_dictionary.md")
    feats = all_features()
    groups = {}
    for name in feats:
        groups.setdefault(group_of(name), []).append(name)
    out_dir = config.DATASET_DIR / "features"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "feature_groups.json").write_text(json.dumps(groups, indent=1) + "\n", encoding="utf-8")
    if args.dictionary_only:
        return
    compiled = Path(args.compiled)
    samples = json.loads((config.METADATA_DIR / "catalog.json").read_text(encoding="utf-8"))["samples"]
    if args.only:
        keep = set(args.only.split(","))
        samples = [s for s in samples if s["sample_id"] in keep]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        rows = [r for r in pool.map(sample_row, samples, [compiled] * len(samples)) if r is not None]
    rows.sort(key=lambda r: r["sample_id"])
    names = ["sample_id"] + list(feats)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(names)
        for r in rows:
            w.writerow([r["sample_id"]] + ["" if (isinstance(r[n], float) and math.isnan(r[n])) else
                                           (f"{r[n]:.6g}" if isinstance(r[n], float) else r[n]) for n in names[1:]])
    print(f"wrote {len(rows)} rows x {len(feats)} features")


if __name__ == "__main__":
    main()
