"""Compare each Trojan-inserted implementation with its Trojan-free reference.

Two checks are made on the Quartus post-fit netlists, which are the
implementations the features describe.

1. Structural difference.  The netlists are compared with a fingerprint that
   ignores signal, instance and project names (cell types, parameter settings
   and connections).  Identical fingerprints mean that synthesis removed every
   trace of the inserted logic, so the implementation carries no Trojan.
   Trojan-free designs with identical post-fit netlists are represented by one
   of them (see representatives), which is the reference of the Trojan-inserted
   designs of all copies.

2. Dormant behavior.  Both netlists are simulated with Icarus Verilog on the
   same pseudo-random input sequence, and the outputs that both designs have
   are compared cycle by cycle.  Inputs that only one design has are held at
   0.  Reset-like inputs (names containing rst, reset, clr or clear) are
   asserted for the first two cycles and then released, active-low when the
   name ends in n, _l, b or _ni.  Identical outputs over the whole sequence are consistent
   with a Trojan that stays dormant under ordinary inputs; they do not show
   that a trigger can fire or that a payload works.  Differing outputs mean
   that the inserted logic changes visible behavior under ordinary inputs.

Usage:
  python -m scripts.verification.dormant [--cycles 1000] [--jobs 4] [--only S0001,...] [--force]

Writes dataset/metadata/verification.csv.
"""
from __future__ import annotations

import argparse
import csv
import random
import re
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..common import config
from ..common.util import derive_seed, read_json, run, sha256_file, sha256_text, write_json, write_text
from ..feature_extraction import netlist_features as nf
from .sim_shim import write_shim

SHIM = "fiftyfivenm_open_shim.v"
SIM_TIMEOUT = 900          # seconds per simulation; combinational loops can make a run oscillate
RESET_RE = re.compile(r"(rst|reset|clr|clear)", re.I)
ACTIVE_LOW_RE = re.compile(r"(_n|_l|n|b|_b|_ni)$", re.I)
NAME_PARAMS = ("init_file", "logical_ram_name")
SOURCE_ORDER = ("trusthub", "ghost", "hayashi")   # Trust-Hub first: the other two sources reuse its hosts


def top_module(text: str) -> str:
    end = text.find("endmodule")
    return text[: end if end >= 0 else len(text)]


def ports(vo: Path) -> dict[str, tuple[str, int]]:
    """Top-level ports of a post-fit netlist: name -> (direction, width)."""
    text = top_module(vo.read_text(encoding="utf-8", errors="replace"))
    out = {}
    for m in re.finditer(r"^\s*(input|output|inout)\s+(?:wire\s+)?(?:\[(\d+):(\d+)\]\s*)?([^;]+);", text, re.M):
        width = abs(int(m.group(2)) - int(m.group(3))) + 1 if m.group(2) else 1
        for name in m.group(4).split(","):
            name = name.strip()
            if name:
                out[name] = (m.group(1), width)
    return out


def structure_hash(vo: Path, rounds: int = 4) -> tuple[str, int]:
    """Name-independent fingerprint of a netlist and its cell count.

    Cells are labeled with their type and parameter settings, except the
    parameters that only hold names (the memory initialization file and the
    logical memory name, which contain the project name and the hierarchy
    path); the labels are refined for a few rounds with the labels of the cells
    that drive and read each port (Weisfeiler-Lehman refinement).  Netlists that
    differ only in signal, instance and project names receive the same
    fingerprint.
    """
    cells, _, _ = nf.parse(vo)
    cells = [c for c in cells if c["type"] not in nf.HIDDEN]
    driver = {}
    for i, c in enumerate(cells):
        for port in nf.OUTPUTS.get(c["type"], ()):
            for net in c["ports"].get(port, []):
                driver[net] = (i, port)
    outs = set(p for c in cells for p in nf.OUTPUTS.get(c["type"], ()))
    fanin = [[] for _ in cells]
    fanout = [[] for _ in cells]
    for j, c in enumerate(cells):
        for port, nets in c["ports"].items():
            if port in nf.OUTPUTS.get(c["type"], ()):
                continue
            for k, net in enumerate(nets):
                if net in driver:
                    i, dport = driver[net]
                    fanin[j].append((port, k, dport, i))
                    fanout[i].append((dport, port, k, j))
                elif net.lower() in nf.CONST:
                    fanin[j].append((port, k, net.lower(), -1))
    label = [sha256_text(c["type"] + "|" + ";".join(f"{a}={b}" for a, b in sorted(c["params"].items())
                                                    if a not in NAME_PARAMS))
             for c in cells]
    for _ in range(rounds):
        label = [sha256_text(label[j] + "|in:" + ",".join(sorted(f"{p}{k}<{d}{label[i] if i >= 0 else ''}"
                                                                 for p, k, d, i in fanin[j]))
                             + "|out:" + ",".join(sorted(f"{d}>{p}{k}{label[i]}" for d, p, k, i in fanout[j])))
                 for j in range(len(cells))]
    return sha256_text(",".join(sorted(label))), len(cells)


def fingerprint(compiled: Path, sid: str) -> tuple[str, int]:
    """structure_hash of a compiled design, cached next to its netlist.

    The cache is keyed by the digest of the netlist and of the code that
    parses and fingerprints it.
    """
    d = compiled / sid
    key = "|".join([read_json(d / "compile_status.json").get("netlist_sha256", ""),
                    sha256_file(Path(__file__)), sha256_file(Path(nf.__file__))])
    cache = d / "structure_fingerprint.json"
    if cache.exists():
        old = read_json(cache)
        if old.get("key") == key:
            return old["fingerprint"], old["cells"]
    h, n = structure_hash(d / "postfit.vo")
    write_json(cache, {"key": key, "fingerprint": h, "cells": n})
    return h, n


def representatives(samples: dict, ok: set, compiled: Path) -> dict[str, str]:
    """Representative of every compiled Trojan-free design.

    Trojan-free designs whose post-fit netlists are identical up to names are
    one implementation; it is represented by the copy whose source comes first
    in SOURCE_ORDER, then by sample ID.
    """
    clean = sorted((s for s in samples.values() if s["label"] == 0 and s["sample_id"] in ok),
                   key=lambda s: (SOURCE_ORDER.index(s["source"]), s["sample_id"]))
    first, rep = {}, {}
    for s in clean:
        h = fingerprint(compiled, s["sample_id"])[0]
        rep[s["sample_id"]] = first.setdefault(h, s["sample_id"])
    return rep


def gate_libraries(scratch: Path) -> list[str]:
    lib = config.quartus_simlib()
    shim = scratch / SHIM
    if not shim.exists():
        write_shim(lib / "fiftyfivenm_atoms.v", shim)
    return [str(lib / "fiftyfivenm_atoms.v"), str(lib / "altera_primitives.v"), str(shim)]


def reset_value(name: str, cycle: int) -> int | None:
    if not RESET_RE.search(name):
        return None
    active = 0 if ACTIVE_LOW_RE.search(name) else 1
    return active if cycle < 2 else 1 - active


def testbench(module: str, pmap: dict, clocks: list[str], drive: list[tuple[str, int]], n: int) -> str:
    """Testbench that reads one input word per cycle and writes the outputs of every cycle."""
    win = max(1, sum(w for _, w in drive))
    outs = [(p, w) for p, (d, w) in sorted(pmap.items()) if d == "output"]
    lines = ["`timescale 1 ps / 1 ps", "module tb;"]
    for p, (d, w) in sorted(pmap.items()):
        rng = f"[{w - 1}:0] " if w > 1 else ""
        lines.append(f"  {'reg' if d == 'input' else 'wire'} {rng}\\{p} ;")
    conns = ", ".join(f".\\{p} (\\{p} )" for p in sorted(pmap))
    lines.append(f"  {module} dut ({conns});")
    lines.append(f"  reg [{win - 1}:0] stim [0:{n - 1}];")
    lines.append("  integer i, fo;")
    lines.append("  initial begin")
    lines.append('    $readmemh("stim.hex", stim);')
    lines.append('    fo = $fopen("trace.txt", "w");')
    for p, (d, w) in sorted(pmap.items()):
        if d == "input":
            lines.append(f"    \\{p} = 0;")
    lines.append(f"    for (i = 0; i < {n}; i = i + 1) begin")
    if drive:
        lines.append(f"      #{config.SIM_APPLY_PS} {{{', '.join(chr(92) + p + ' ' for p, _ in drive)}}} = stim[i];")
    else:
        lines.append(f"      #{config.SIM_APPLY_PS};")
    half = config.SIM_PERIOD_PS // 2
    lines.append(f"      #{half - config.SIM_APPLY_PS};")
    for c in clocks:
        lines.append(f"      \\{c} = 1'b1;")
    lines.append(f"      #{config.SIM_SAMPLE_PS - half};")
    if outs:
        lines.append(f'      $fwrite(fo, "%b\\n", {{{", ".join(chr(92) + p + " " for p, _ in outs)}}});')
    lines.append(f"      #{config.SIM_PERIOD_PS - config.SIM_SAMPLE_PS};")
    for c in clocks:
        lines.append(f"      \\{c} = 1'b0;")
    lines.append("    end")
    lines.append("    $fclose(fo);")
    lines.append("    $finish;")
    lines.append("  end")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


def stimulus(seed: int, drive: list[tuple[str, int]], n: int) -> list[str]:
    rng = random.Random(seed)
    width = max(1, sum(w for _, w in drive))
    rows = []
    for k in range(n):
        word = 0
        for name, w in drive:
            r = reset_value(name, k)
            v = r if r is not None and w == 1 else rng.getrandbits(w)
            word = (word << w) | v
        rows.append(f"{word:0{(width + 3) // 4}x}")
    return rows


def simulate(vo: Path, module: str, pmap: dict, clocks: list[str], stim_names: list[tuple[str, int]],
             stim_rows: list[str], work: Path, libs: list[str]) -> list[str] | None:
    work.mkdir(parents=True, exist_ok=True)
    drive = [(p, w) for p, w in stim_names if p in pmap and pmap[p][0] == "input" and p not in clocks]
    # The stimulus word holds every common input; columns for inputs this design lacks are dropped.
    idx, pos = {}, 0
    for p, w in stim_names:
        idx[p] = (pos, w)
        pos += w
    total = pos
    rows = []
    for r in stim_rows:
        bits = bin(int(r, 16))[2:].zfill(total)[-total:] if total else ""
        rows.append("".join(bits[idx[p][0]: idx[p][0] + w] for p, w in drive) or "0")
    write_text(work / "stim.hex", "\n".join(f"{int(b, 2):x}" for b in rows) + "\n")
    write_text(work / "tb.v", testbench(module, pmap, clocks, drive, len(rows)))
    env = config.oss_env()
    rc = run([config.tool("iverilog"), "-g2005", "-o", "sim.vvp", "-s", "tb", "tb.v", str(vo)] + libs,
             cwd=work, log=work / "compile.log", env=env, timeout=3600)
    if rc != 0:
        return None
    try:
        rc = run([config.tool("vvp"), "-n", "sim.vvp"], cwd=work, log=work / "run.log", env=env,
                 timeout=SIM_TIMEOUT)
    except subprocess.TimeoutExpired:
        return "timeout"
    if rc != 0 or not (work / "trace.txt").exists():
        return None
    return (work / "trace.txt").read_text().split()


def structure(compiled: Path, tid: str, cid: str) -> dict:
    (ht, nt), (hc, nc) = fingerprint(compiled, tid), fingerprint(compiled, cid)
    return {"structure_identical": int(ht == hc), "cells_trojan": nt, "cells_clean": nc}


def compare(pair: tuple[dict, dict], compiled: Path, n: int, libs: list[str]) -> dict:
    t, c = pair
    tvo, cvo = compiled / t["sample_id"] / "postfit.vo", compiled / c["sample_id"] / "postfit.vo"
    row = {"sample_id": t["sample_id"], "clean_reference": c["sample_id"]}
    tp, cp = ports(tvo), ports(cvo)
    tin = {p for p, (d, _) in tp.items() if d == "input"}
    cin = {p for p, (d, _) in cp.items() if d == "input"}
    tout = {p for p, (d, _) in tp.items() if d == "output"}
    cout = {p for p, (d, _) in cp.items() if d == "output"}
    row["extra_inputs"] = len(tin - cin)
    row["extra_outputs"] = len(tout - cout)
    row["missing_inputs"] = len(cin - tin)
    row["missing_outputs"] = len(cout - tout)
    width_change = sum(1 for p in tp.keys() & cp.keys() if tp[p] != cp[p])
    row["interface_identical"] = int(tp == cp)
    row["width_changes"] = width_change
    row.update(structure(compiled, t["sample_id"], c["sample_id"]))
    clocks = sorted(set(read_json(compiled / t["sample_id"] / "compile_status.json").get("clock_ports", [])) |
                    set(read_json(compiled / c["sample_id"] / "compile_status.json").get("clock_ports", [])))
    common_in = sorted(p for p in tin & cin if p not in clocks and tp[p] == cp[p])
    stim_names = [(p, tp[p][1]) for p in common_in]
    common_out = sorted(p for p in tout & cout if tp[p] == cp[p])
    row["compared_outputs"] = len(common_out)
    row["cycles"] = n
    if not common_out:
        row["dormant_check"] = "no common outputs"
        return row
    seed = derive_seed(config.GENERATOR_SEED, "dormant", c["sample_id"])
    rows = stimulus(seed, stim_names, n)
    work = config.BUILD / "verify" / t["sample_id"]
    tr = simulate(tvo, top_name(tvo), tp, [k for k in clocks if k in tp], stim_names, rows, work / "trojan", libs)
    cr = simulate(cvo, top_name(cvo), cp, [k for k in clocks if k in cp], stim_names, rows, work / "clean", libs)
    if tr == "timeout" or cr == "timeout":
        row["dormant_check"] = "simulation timeout"
        return row
    if tr is None or cr is None:
        row["dormant_check"] = "simulation failed"
        return row
    order_t = [p for p, (d, _) in sorted(tp.items()) if d == "output"]
    order_c = [p for p, (d, _) in sorted(cp.items()) if d == "output"]
    first_diff, unknown, diff_cycles = None, 0, 0
    for k, (a, b) in enumerate(zip(tr, cr)):
        va, vb = split(a, order_t, tp), split(b, order_c, cp)
        differ = False
        for p in common_out:
            x, y = va[p], vb[p]
            if "x" in x or "z" in x or "x" in y or "z" in y:
                unknown += 1
                continue
            if x != y:
                differ = True
        if differ:
            diff_cycles += 1
            if first_diff is None:
                first_diff = k
    row["differing_cycles"] = diff_cycles
    row["first_difference_cycle"] = "" if first_diff is None else first_diff
    row["unknown_output_samples"] = unknown
    row["dormant_check"] = "outputs identical" if diff_cycles == 0 else "outputs differ"
    return row


def top_name(vo: Path) -> str:
    m = re.search(r"^\s*module\s+(\\\S+|\w+)", vo.read_text(encoding="utf-8", errors="replace"), re.M)
    return m.group(1)


def split(word: str, order: list[str], pmap: dict) -> dict[str, str]:
    out, pos = {}, 0
    for p in order:
        w = pmap[p][1]
        out[p] = word[pos: pos + w].lower()
        pos += w
    return out


FIELDS = ["sample_id", "clean_reference", "interface_identical", "extra_inputs", "extra_outputs", "missing_inputs",
          "missing_outputs", "width_changes", "structure_identical", "cells_trojan", "cells_clean",
          "compared_outputs", "cycles", "dormant_check", "differing_cycles", "first_difference_cycle",
          "unknown_output_samples"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=1000)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--only", default="")
    ap.add_argument("--compiled", default=str(config.BUILD / "compiled"))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    compiled = Path(args.compiled)
    samples = {s["sample_id"]: s for s in read_json(config.METADATA_DIR / "catalog.json")["samples"]}

    def ok(sid):
        f = compiled / sid / "compile_status.json"
        return f.exists() and read_json(f).get("ok")
    compiled_ok = {sid for sid in samples if ok(sid)}
    rep = representatives(samples, compiled_ok, compiled)
    pairs = [(s, samples[rep[s["clean_reference"]]]) for s in samples.values()
             if s["label"] == 1 and s.get("clean_reference") and s["sample_id"] in compiled_ok
             and s["clean_reference"] in compiled_ok]
    if args.only:
        keep = set(args.only.split(","))
        pairs = [p for p in pairs if p[0]["sample_id"] in keep]
    (config.BUILD / "verify").mkdir(parents=True, exist_ok=True)
    libs = gate_libraries(config.BUILD / "verify")
    def cached(pair):
        """Result of one pair.  The simulation result is reused when both netlists are unchanged
        since the last run; the structural comparison is always recomputed."""
        t, c = pair
        key = "|".join([read_json(compiled / t["sample_id"] / "compile_status.json").get("netlist_sha256", ""),
                        read_json(compiled / c["sample_id"] / "compile_status.json").get("netlist_sha256", ""),
                        str(args.cycles)])
        f = config.BUILD / "verify" / t["sample_id"] / "result.json"
        if f.exists() and not args.force:
            old = read_json(f)
            if old.get("key") == key:
                row = old["row"]
                row.update(structure(compiled, t["sample_id"], c["sample_id"]))
                return row
        row = compare(pair, compiled, args.cycles, libs)
        write_json(f, {"key": key, "row": row})
        return row
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        rows = list(pool.map(cached, pairs))
    rows.sort(key=lambda r: r["sample_id"])
    with open(config.METADATA_DIR / "verification.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    print(Counter(r.get("dormant_check") for r in rows), "structure identical:",
          sum(r["structure_identical"] for r in rows))


if __name__ == "__main__":
    main()
