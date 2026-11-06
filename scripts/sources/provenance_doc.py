"""Write docs/provenance.md from the archive manifest and the sample catalog.

Usage:
  python -m scripts.sources.provenance_doc
"""
from __future__ import annotations

import csv
import json
from collections import Counter

from ..common import config

SOURCES = {
    "trusthub": ("Trust-Hub chip-level Trojan benchmarks", "https://trust-hub.org/#/benchmarks/chip-level-trojan",
                 "H. Salmani, M. Tehranipoor and R. Karri, ICCD 2013, doi:10.1109/ICCD.2013.6657085; "
                 "B. Shakya et al., J. Hardw. Syst. Secur. 1(1), 2017, doi:10.1007/s41635-017-0001-6"),
    "trit": ("TRIT-TC and TRIT-TS (Trust-Hub)", "https://trust-hub.org/#/benchmarks/chip-level-trojan",
             "J. Cruz, Y. Huang, P. Mishra and S. Bhunia, DATE 2018, doi:10.23919/DATE.2018.8342270"),
    "ghost": ("GHOST hardware Trojan benchmarks", "https://github.com/NMSU-PEARL/GHOST_benchmarks",
              "M. O. Faruque, P. Jamieson, A. Patooghy and A.-H. A. Badawy, Electronics 14(23):4745, 2025, "
              "doi:10.3390/electronics14234745"),
    "hayashi": ("Hardware Trojan dataset of RISC-V and Web3", "https://doi.org/10.5281/zenodo.11035341",
                "V. T. Hayashi and W. V. Ruggiero, Data 9(6):82, 2024, doi:10.3390/data9060082"),
}


def main():
    with open(config.METADATA_DIR / "source_archives.csv", encoding="utf-8", newline="") as fh:
        arch = list(csv.DictReader(fh))
    cat = json.loads((config.METADATA_DIR / "catalog.json").read_text(encoding="utf-8"))["samples"]
    with open(config.METADATA_DIR / "excluded_items.csv", encoding="utf-8", newline="") as fh:
        excl = list(csv.DictReader(fh))
    n = Counter((s["source"], s["role"]) for s in cat)
    lines = ["# Provenance of the MAX10-HTD designs", "",
             "MAX10-HTD does not redistribute third-party hardware designs. Every design is downloaded from "
             "its original location by `python -m scripts.sources.fetch`, which checks the size and SHA-256 "
             "digest of each downloaded file against `dataset/metadata/source_archives.csv`. The features, labels "
             "and metadata in `dataset/` are measurements and annotations produced by this project.", "",
             "## Sources", ""]
    for key, (name, url, cite) in SOURCES.items():
        rows = [a for a in arch if a["source"] == key]
        if not rows:
            continue
        lic = rows[0]["license"]
        archives = [a for a in rows if not a["archive"].endswith(".json")]
        index = [a for a in rows if a["archive"].endswith(".json")]
        files = f"- Archives: {len(archives)}" + (f" and the benchmark index {index[0]['archive']}" if index else "")
        designs = (f"{n[(key, 'clean')]} Trojan-free and {n[(key, 'trojan')]} Trojan-inserted (identical copies "
                   "counted once)" if n[(key, 'clean')] + n[(key, 'trojan')] else
                   "none (gate-level netlists for ASIC cell libraries; see the items not in the catalog)")
        lines += [f"### {name}", "", f"- Location: <{url}>", f"- Reference: {cite}", f"- License: {lic}",
                  f"{files} ({sum(int(a['bytes']) for a in rows):,} bytes), retrieved "
                  f"{min(a['retrieved'] for a in rows)}",
                  f"- Catalog designs: {designs}", ""]
    lines += ["## What was changed in the third-party sources", "",
              "- Files are copied without edits, except that absolute `include` paths are replaced by the "
              "file name of the included file, which is copied next to the design.",
              "- GHOST: the annotated Trojan-inserted files (`*_A1.v`) are used, because comments do not affect "
              "synthesis and some comment-free copies (`*_cleaned.v`) fail to parse with Icarus Verilog although "
              "their annotated versions parse. The design unit is the module that received the Trojan.",
              "- RISC-V and Web3: each Trojan-inserted module file is compiled with the unmodified golden "
              "files of the modules it instantiates.", "",
              "## Pairing of Trojan-inserted and Trojan-free designs", "",
              "Trust-Hub and GHOST distribute each Trojan-inserted design together with the Trojan-free version "
              "of its host. In the RISC-V and Web3 release, a Trojan-inserted file is paired with the golden module "
              "whose identifiers it shares most (Jaccard similarity, without comments, keywords and compiler "
              "directives). This is the module named in the file name except for the files below, which are "
              "modified versions of another golden module.", "",
              "| Sample | File | Named host | Paired with |", "|---|---|---|---|"]
    for s in sorted(cat, key=lambda s: s["sample_id"]):
        note = s.get("source_verification", "")
        if "paired with" in note:
            named = note.rsplit("refers to ", 1)[1]
            lines.append(f"| {s['sample_id']} | {', '.join(s['source_items'])} | {named} | {s['design']} |")
    lines += ["", "## Items not in the catalog", "", "| Source | Item | Reason |", "|---|---|---|"]
    for e in excl:
        lines.append(f"| {e['source']} | {e['item']} | {e['reason']} |")
    lines += ["", "## Archive manifest", "", "| Source | Archive | Bytes | SHA-256 |", "|---|---|---|---|"]
    for a in sorted(arch, key=lambda a: (a["source"], a["archive"])):
        lines.append(f"| {a['source']} | {a['archive']} | {int(a['bytes']):,} | `{a['sha256']}` |")
    (config.REPO / "docs").mkdir(exist_ok=True)
    (config.REPO / "docs" / "provenance.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("wrote docs/provenance.md")


if __name__ == "__main__":
    main()
