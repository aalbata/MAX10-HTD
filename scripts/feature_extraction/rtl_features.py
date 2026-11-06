"""Source-level structural features computed with Yosys from Verilog RTL.

The design is elaborated with `proc; flatten; opt_clean -purge`, which keeps
word-level operators (adders, comparators, multiplexers, registers) as
inferred from the source rather than mapping them to device cells.  Features
are counts of operator classes, register bits, and comparisons in which one
operand is a constant.  Designs written in VHDL are not supported by the
Yosys build used here; their RTL features are recorded as missing.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from ..common import config
from ..common.util import run

NAN = float("nan")

GROUPS = {
    "arith": {"$add", "$sub", "$neg", "$div", "$mod", "$divfloor", "$modfloor", "$pow", "$alu", "$macc"},
    "mul": {"$mul"},
    "cmp_eq": {"$eq", "$ne", "$eqx", "$nex"},
    "cmp_rel": {"$lt", "$le", "$gt", "$ge"},
    "logic_bit": {"$and", "$or", "$xor", "$xnor", "$not"},
    "logic_bool": {"$logic_and", "$logic_or", "$logic_not"},
    "reduce": {"$reduce_and", "$reduce_or", "$reduce_xor", "$reduce_xnor", "$reduce_bool"},
    "shift": {"$shl", "$shr", "$sshl", "$sshr", "$shift", "$shiftx"},
    "mux": {"$mux", "$bmux", "$demux", "$bwmux"},
    "pmux": {"$pmux"},
    "ff": {"$dff", "$adff", "$sdff", "$dffe", "$adffe", "$sdffe", "$sdffce", "$dffsr", "$dffsre", "$aldff",
           "$aldffe", "$ff"},
    "latch": {"$dlatch", "$adlatch", "$dlatchsr", "$sr"},
    "mem": {"$mem", "$mem_v2", "$memrd", "$memrd_v2", "$memwr", "$memwr_v2", "$meminit", "$meminit_v2"},
}

FEATURES = {
    "rtl_cells": ("count", "Word-level cells after elaboration"),
    "rtl_wires": ("count", "Named and internal wires"),
    "rtl_wire_bits": ("bits", "Total wire bits"),
    **{f"rtl_{g}": ("count", f"Word-level cells of class {g}") for g in GROUPS},
    "rtl_ff_bits": ("bits", "Register bits (sum of register widths)"),
    "rtl_const_cmp": ("count", "Equality comparisons with one fully constant operand"),
    "rtl_const_cmp_bits_max": ("bits", "Widest equality comparison against a constant"),
    "rtl_const_cmp_bits_sum": ("bits", "Total width of equality comparisons against constants"),
    "rtl_other": ("count", "Cells outside the listed classes"),
}


def _const_operand(bits) -> bool:
    return bool(bits) and all(isinstance(b, str) for b in bits)


def extract(sources: list[Path], top: str, workdir: Path, include_dir: Path | None = None,
            systemverilog: bool = False) -> dict:
    f = {k: NAN for k in FEATURES}
    if any(Path(s).suffix.lower() in (".vhd", ".vhdl") for s in sources):
        return f
    workdir.mkdir(parents=True, exist_ok=True)
    opts = "-DSYNTHESIS" + (" -sv" if systemverilog else "") + (f" -I{Path(include_dir).as_posix()}" if include_dir else "")
    # Files that another source includes are read through the include directive only.
    included = set()
    for s in sources:
        if Path(s).exists():
            for m in re.finditer(r'`include\s+"([^"]+)"', Path(s).read_text(encoding="utf-8", errors="replace")):
                included.add(re.split(r"[/\\]", m.group(1))[-1].lower())
    reads = "; ".join(f"read_verilog {opts} {Path(s).as_posix()}" for s in sources
                      if Path(s).suffix.lower() in (".v", ".sv") and Path(s).name.lower() not in included)
    script = (f"{reads}; hierarchy -top {top}; proc; flatten; opt_clean -purge; "
              f"tee -q -o stat.json stat -json; write_json netlist.json")
    rc = run([config.tool("yosys"), "-q", "-p", script], cwd=workdir, log=workdir / "yosys.log",
             env=config.oss_env(), timeout=1800)
    if rc != 0 or not (workdir / "netlist.json").exists():
        return f
    nl = json.loads((workdir / "netlist.json").read_text())
    mod = nl["modules"].get(top) or next(iter(nl["modules"].values()))
    cells = mod.get("cells", {})
    types = Counter(c["type"] for c in cells.values())
    f["rtl_cells"] = float(sum(types.values()))
    nets = mod.get("netnames", {})
    f["rtl_wires"] = float(len(nets))
    f["rtl_wire_bits"] = float(sum(len(n.get("bits", [])) for n in nets.values()))
    known = set()
    for g, members in GROUPS.items():
        f[f"rtl_{g}"] = float(sum(types[t] for t in members))
        known |= members
    f["rtl_other"] = float(sum(v for t, v in types.items() if t not in known))
    ff_bits = 0
    cmp_widths = []
    for c in cells.values():
        t = c["type"]
        if t in GROUPS["ff"] or t in GROUPS["latch"]:
            ff_bits += int(str(c.get("parameters", {}).get("WIDTH", "1")), 2) if set(
                str(c.get("parameters", {}).get("WIDTH", "1"))) <= {"0", "1"} else 1
        if t in ("$eq", "$ne"):
            a = c["connections"].get("A", [])
            b = c["connections"].get("B", [])
            if _const_operand(a) != _const_operand(b):
                cmp_widths.append(len(b) if _const_operand(b) else len(a))
    f["rtl_ff_bits"] = float(ff_bits)
    f["rtl_const_cmp"] = float(len(cmp_widths))
    f["rtl_const_cmp_bits_max"] = float(max(cmp_widths, default=0))
    f["rtl_const_cmp_bits_sum"] = float(sum(cmp_widths))
    assert set(f) == set(FEATURES)
    return f
