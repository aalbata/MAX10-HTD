"""Assemble the MAX10-HTD benchmark tables from the compiled and verified designs.

Inclusion rules
  * The design compiled through the full Quartus flow.
  * One row per distinct implementation: designs whose post-fit netlists are
    identical up to names are kept once.  For Trojan-free designs the copy
    chosen by verification.dormant.representatives is kept and becomes the
    reference of the Trojan-inserted designs of all copies.
  * A Trojan-inserted design is included only when its Trojan-free reference
    also compiled and its post-fit netlist differs from that of every
    Trojan-free design (an identical netlist means that synthesis removed the
    inserted logic).

Host groups
  Each Trojan-free design starts its own host group and every Trojan-inserted
  design joins the group of its reference.  Trojan-free designs whose sources
  are near duplicates (Jaccard similarity of 5-token shingles of at least 0.8
  after removing comments) are merged into one group, so that near-identical
  designs never fall on both sides of a split.

Writes
  dataset/features/features.csv    predictive features of the included designs
  dataset/labels/labels.csv        sample_id, label (1 = Trojan-inserted)
  dataset/metadata/samples.csv     metadata that is not used for prediction
  dataset/metadata/exclusions.csv  designs left out, with the reason
  dataset/splits/*.csv             fixed partitions used by the experiments

Usage:
  python -m scripts.validation.assemble
"""
from __future__ import annotations

import csv
import json
import re
from itertools import combinations

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from ..common import config
from ..sources import hdl
from ..verification.dormant import fingerprint, representatives

RAW = config.BUILD / "raw"
SIMILAR = 0.8
REPEATS = 5
FOLDS = 5
SPLIT_SEED = 20261104


def shingles(files: list[str], k: int = 5) -> set:
    toks = []
    for f in sorted(files):
        p = RAW / f
        text = hdl.read(p)
        text = hdl.strip_vhdl_comments(text) if p.suffix.lower() in hdl.VHDL_SUFFIXES else hdl.strip_verilog_comments(text)
        toks += re.findall(r"[A-Za-z_][\w$]*|\d+'[bBhHdDoO][0-9a-fA-FxXzZ_]+|\d+|\S", text)
    return {tuple(toks[i:i + k]) for i in range(max(0, len(toks) - k + 1))}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a or b else 1.0


def log_flags(sid: str) -> dict:
    """Counts of Quartus warnings about combinational loops and inferred latches (metadata only)."""
    f = config.BUILD / "compiled" / sid / "flow.log"
    text = f.read_text(encoding="utf-8", errors="replace") if f.exists() else ""
    return {"combinational_loop_warnings": len(re.findall(r"Warning \(332125\)", text)),
            "latch_warnings": len(re.findall(r"Warning \(10240\)", text))}


def status(sid: str) -> dict:
    f = config.BUILD / "compiled" / sid / "compile_status.json"
    return json.loads(f.read_text()) if f.exists() else {}


def main():
    samples = json.loads((config.METADATA_DIR / "catalog.json").read_text(encoding="utf-8"))["samples"]
    by_id = {s["sample_id"]: s for s in samples}
    ver = pd.read_csv(config.METADATA_DIR / "verification.csv", dtype={"first_difference_cycle": str})
    ver = ver.set_index("sample_id")
    feats = pd.read_csv(config.BUILD / "features_all.csv").set_index("sample_id")
    st = {sid: status(sid) for sid in by_id}

    compiled = config.BUILD / "compiled"
    ok = {sid for sid in by_id if st[sid].get("ok")}
    rep = representatives(by_id, ok, compiled)
    fp = {sid: fingerprint(compiled, sid)[0] for sid in ok}
    clean_of = {fp[sid]: r for sid, r in rep.items()}

    included, excluded = [], []
    for s in samples:
        sid = s["sample_id"]
        if not st[sid]:
            excluded.append((sid, s["source"], s["role"], "not compiled", ""))
            continue
        if not st[sid].get("ok"):
            stage = st[sid].get("failed_stage", "flow")
            first = (st[sid].get("errors") or [""])[0]
            excluded.append((sid, s["source"], s["role"], f"compilation failed ({stage})", first[:200]))
            continue
        if sid not in feats.index:
            excluded.append((sid, s["source"], s["role"], "feature extraction failed", ""))
            continue
        if s["label"] == 0 and rep[sid] != sid:
            excluded.append((sid, s["source"], s["role"], "post-fit netlist identical to another Trojan-free "
                             "design of the benchmark", rep[sid]))
            continue
        if s["label"] == 1:
            ref = s.get("clean_reference")
            if not ref or ref not in ok:
                excluded.append((sid, s["source"], s["role"], "Trojan-free reference did not compile", ref or ""))
                continue
            if fp[sid] in clean_of:
                excluded.append((sid, s["source"], s["role"], "post-fit netlist identical to a Trojan-free "
                                 "design (inserted logic removed by synthesis)", clean_of[fp[sid]]))
                continue
            if sid not in ver.index:
                excluded.append((sid, s["source"], s["role"], "not verified", ref))
                continue
            s = {**s, "clean_reference": rep[ref]}
        included.append(s)

    # The kept Trojan-free copy carries the provenance of all its copies.
    kept = {s["sample_id"]: s for s in included}
    for s in samples:
        if s["label"] == 0 and s["sample_id"] in rep and rep[s["sample_id"]] != s["sample_id"]:
            k = kept[rep[s["sample_id"]]]
            k["source_items"] = sorted(set(k["source_items"]) | set(s["source_items"]))

    # Trojan-inserted designs with identical post-fit netlists are kept once, with the provenance
    # of all copies.
    first_of = {}
    unique = []
    for s in sorted(included, key=lambda s: s["sample_id"]):
        if s["label"] == 1 and fp[s["sample_id"]] in first_of:
            keep = first_of[fp[s["sample_id"]]]
            keep["source_items"] = sorted(set(keep["source_items"]) | set(s["source_items"]))
            excluded.append((s["sample_id"], s["source"], s["role"], "post-fit netlist identical to another "
                             "Trojan-inserted design of the benchmark", keep["sample_id"]))
            continue
        if s["label"] == 1:
            first_of[fp[s["sample_id"]]] = s
        unique.append(s)
    included = unique

    # Host groups with near-duplicate merging of the Trojan-free designs.
    clean = [s for s in included if s["label"] == 0]
    sh = {s["sample_id"]: shingles(s["files"]) for s in clean}
    parent = {s["sample_id"]: s["sample_id"] for s in clean}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    pairs = []
    for a, b in combinations(sorted(sh), 2):
        j = jaccard(sh[a], sh[b])
        if j >= SIMILAR:
            pairs.append((a, b, j))
            parent[find(a)] = find(b)
    roots = sorted({find(x) for x in parent})
    gid = {r: f"G{i + 1:02d}" for i, r in enumerate(roots)}
    host_group = {sid: gid[find(sid)] for sid in parent}
    for s in included:
        if s["label"] == 1:
            host_group[s["sample_id"]] = host_group[s["clean_reference"]]

    # Design groups, a stricter grouping: host groups are also merged when the sources of one
    # Trojan-free design are contained in those of another (containment of at least 0.8, measured
    # on the smaller shingle set), for example a module and the core that instantiates it.
    dparent = {g: g for g in set(host_group.values())}

    def dfind(x):
        while dparent[x] != x:
            dparent[x] = dparent[dparent[x]]
            x = dparent[x]
        return x
    for a, b in combinations(sorted(sh), 2):
        small = min(len(sh[a]), len(sh[b]))
        if small and len(sh[a] & sh[b]) / small >= SIMILAR:
            dparent[dfind(host_group[a])] = dfind(host_group[b])
    droots = sorted({dfind(g) for g in dparent})
    did = {r: f"D{i + 1:02d}" for i, r in enumerate(droots)}
    design_group = {sid: did[dfind(g)] for sid, g in host_group.items()}

    rows = []
    for s in included:
        sid = s["sample_id"]
        v = ver.loc[sid] if (s["label"] == 1 and sid in ver.index) else None
        rows.append({
            "sample_id": sid, "label": s["label"], "role": s["role"], "source": s["source"],
            "design": s["design"], "family": s["family"], "host_group": host_group[sid],
            "design_group": design_group[sid],
            "clean_reference": s.get("clean_reference") or "", "top": s["top"], "language": s["language"],
            "trigger": s.get("trigger", ""), "payload": s.get("payload", ""),
            "generator": s.get("generator", ""), "source_items": ";".join(s["source_items"]),
            "source_verification": s.get("source_verification", ""),
            "compile_seconds": st[sid].get("flow_seconds"), "hdl_version": st[sid].get("hdl_version"),
            "clock_ports": len(st[sid].get("clock_ports", [])),
            **log_flags(sid),
            "interface_identical": "" if v is None else int(v["interface_identical"]),
            "extra_inputs": "" if v is None else int(v["extra_inputs"]),
            "extra_outputs": "" if v is None else int(v["extra_outputs"]),
            "dormant_check": "" if v is None else v["dormant_check"],
            "differing_cycles": "" if v is None or pd.isna(v.get("differing_cycles")) else int(v["differing_cycles"]),
        })
    meta = pd.DataFrame(rows).sort_values("sample_id")
    comp = []
    for s in samples:
        sid = s["sample_id"]
        comp.append({"sample_id": sid, "source": s["source"], "role": s["role"], "design": s["design"],
                     "compiled": int(bool(st[sid].get("ok"))),
                     "failed_stage": st[sid].get("failed_stage", "") if st[sid] else "not compiled",
                     "first_error": (st[sid].get("errors") or [""])[0][:200] if st[sid] else "",
                     "flow_seconds": st[sid].get("flow_seconds", ""), "hdl_version": st[sid].get("hdl_version", ""),
                     "ports_in": st[sid].get("ports_in", ""), "ports_out": st[sid].get("ports_out", ""),
                     "clock_ports": ";".join(st[sid].get("clock_ports", []))})
    pd.DataFrame(comp).sort_values("sample_id").to_csv(config.METADATA_DIR / "compilation.csv", index=False,
                                                        lineterminator="\n")
    (config.DATASET_DIR / "labels").mkdir(parents=True, exist_ok=True)
    (config.DATASET_DIR / "splits").mkdir(parents=True, exist_ok=True)
    meta.to_csv(config.METADATA_DIR / "samples.csv", index=False, lineterminator="\n")
    meta[["sample_id", "label"]].to_csv(config.DATASET_DIR / "labels" / "labels.csv", index=False,
                                         lineterminator="\n")
    feats.loc[meta["sample_id"]].to_csv(config.DATASET_DIR / "features" / "features.csv", lineterminator="\n")
    with open(config.METADATA_DIR / "exclusions.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["sample_id", "source", "role", "reason", "detail"])
        w.writerows(sorted(excluded))
    with open(config.METADATA_DIR / "near_duplicates.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["sample_a", "sample_b", "jaccard"])
        w.writerows((a, b, f"{j:.3f}") for a, b, j in pairs)

    # Fixed partitions.
    y = meta["label"].to_numpy()
    groups = meta["host_group"].to_numpy()
    cv = pd.DataFrame({"sample_id": meta["sample_id"]})
    for r in range(REPEATS):
        fold = np.full(len(meta), -1)
        skf = StratifiedGroupKFold(n_splits=FOLDS, shuffle=True, random_state=SPLIT_SEED + r)
        for k, (_, te) in enumerate(skf.split(np.zeros(len(y)), y, groups)):
            fold[te] = k
        cv[f"rep{r}"] = fold
    cv.to_csv(config.DATASET_DIR / "splits" / "grouped_cv.csv", index=False, lineterminator="\n")
    dgroups = meta["design_group"].to_numpy()
    cvd = pd.DataFrame({"sample_id": meta["sample_id"]})
    for r in range(REPEATS):
        fold = np.full(len(meta), -1)
        skf = StratifiedGroupKFold(n_splits=FOLDS, shuffle=True, random_state=SPLIT_SEED + r)
        for k, (_, te) in enumerate(skf.split(np.zeros(len(y)), y, dgroups)):
            fold[te] = k
        cvd[f"rep{r}"] = fold
    cvd.to_csv(config.DATASET_DIR / "splits" / "grouped_cv_design.csv", index=False, lineterminator="\n")
    meta[["sample_id", "host_group", "design_group", "family", "source", "payload"]].to_csv(
        config.DATASET_DIR / "splits" / "holdout_keys.csv", index=False, lineterminator="\n")
    print(f"included {len(meta)} ({int(y.sum())} Trojan-inserted, {int(len(y) - y.sum())} Trojan-free) "
          f"in {meta['host_group'].nunique()} host groups and {meta['family'].nunique()} families; "
          f"excluded {len(excluded)}; near-duplicate pairs {len(pairs)}")


if __name__ == "__main__":
    main()
