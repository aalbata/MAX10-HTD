"""Compile the catalog designs with Quartus Prime for the MAX 10 10M50DAF484C7G.

Every design is compiled twice from the same sources.  The first pass runs
Analysis & Synthesis only and lists the top-level ports and the ports that
drive register clock inputs.  The second pass runs the full flow with every
port except the clock ports assigned as a virtual pin, so that designs with
more ports than the device has pins are implemented like an IP core inside a
larger design, and all designs are treated the same way.  Clocks receive a
20 ns constraint and input-to-output paths a 20 ns maximum delay.

For each design the script keeps the report panels, the timing-path summary,
the post-fit Verilog netlist and the stage reports in <out>/<sample>, then
deletes the Quartus databases.

Usage:
  python -m scripts.quartus.compile [--jobs N] [--only S0001,S0002] [--force] [--seed 1]
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from ..common import config
from ..common.util import read_json, sha256_file, write_json, write_text

HERE = Path(__file__).resolve().parent
RAW = config.BUILD / "raw"
KEEP = (".map.rpt", ".fit.rpt", ".sta.rpt", ".pow.rpt", ".asm.rpt", ".eda.rpt", ".flow.rpt",
        ".map.summary", ".fit.summary", ".sta.summary", ".pow.summary")
KIND = {".v": "VERILOG_FILE", ".sv": "SYSTEMVERILOG_FILE", ".vhd": "VHDL_FILE", ".vhdl": "VHDL_FILE"}
FLOW_TIMEOUT = 3600          # seconds per Quartus step (probe synthesis, full flow, report export)


def message_counts(rpt: Path) -> dict:
    """Error and warning totals that Quartus prints at the end of each stage report."""
    text = rpt.read_text(encoding="utf-8", errors="replace") if rpt.exists() else ""
    m = re.findall(r"was successful\. (\d+) errors?, (\d+) warnings?", text)
    if m:
        return {"errors": int(m[-1][0]), "warnings": int(m[-1][1]), "successful": True}
    m = re.findall(r"was unsuccessful\. (\d+) errors?, (\d+) warnings?", text)
    if m:
        return {"errors": int(m[-1][0]), "warnings": int(m[-1][1]), "successful": False}
    return {"errors": None, "warnings": None, "successful": False}


def first_errors(log: Path, n: int = 5) -> list[str]:
    if not log.exists():
        return []
    lines = [l.strip() for l in log.read_text(encoding="utf-8", errors="replace").splitlines()
             if l.strip().startswith("Error (")]
    return [l[:300] for l in lines[:n]]


INCLUDE_RE = re.compile(r'`include\s+"([^"]+)"')


def included_names(paths: list[Path]) -> set[str]:
    """Lower-case file names that some design file pulls in with an include directive."""
    out = set()
    for p in paths:
        if p.suffix.lower() in (".v", ".sv", ".h", ".vh", ".svh", ".inc"):
            for m in INCLUDE_RE.finditer(p.read_text(encoding="utf-8", errors="replace")):
                out.add(re.split(r"[/\\]", m.group(1))[-1].lower())
    return out


def prepare_sources(sample: dict, proj: Path) -> dict:
    """Copy the design files into <proj>/src and point include directives at the local copies.

    Files that another design file includes are copied but not added to the project, so that
    their modules are not declared twice.
    """
    src = proj / "src"
    src.mkdir(parents=True)
    names = [Path(f).name for f in sample["files"]]
    if len(set(n.lower() for n in names)) != len(names):
        raise RuntimeError("two design files share a file name")
    included = included_names([RAW / f for f in sample["files"]])
    rewrites = 0
    lines = []
    for f in sample["files"]:
        p = RAW / f
        dest = src / p.name
        if p.suffix.lower() in (".v", ".sv", ".h", ".vh", ".svh", ".inc"):
            text = p.read_text(encoding="utf-8", errors="replace")

            def local(m):
                nonlocal rewrites
                base = re.split(r"[/\\]", m.group(1))[-1]
                if base != m.group(1) and base.lower() in {n.lower() for n in names}:
                    rewrites += 1
                    return f'`include "{base}"'
                return m.group(0)
            text = INCLUDE_RE.sub(local, text)
            dest.write_text(text, encoding="utf-8", newline="\n")
        else:
            shutil.copyfile(p, dest)
        kind = KIND.get(p.suffix.lower())
        if kind and p.name.lower() not in included:
            lines.append(f"{kind}\tsrc/{p.name}")
    write_text(proj / "files.txt", "\n".join(lines) + "\n")
    return {"include_rewrites": rewrites}


def parse_ports(path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    ports, clocks = [], []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split("\t")
        if parts[0] == "port" and len(parts) == 3:
            ports.append((parts[1], parts[2]))
        elif parts[0] == "clock" and len(parts) == 3 and parts[2] == "port":
            clocks.append(parts[1])
    names = {p for p, _ in ports}
    return ports, sorted(set(c for c in clocks if c in names))


def tcl_names(names: list[str]) -> str:
    return "{" + " ".join(names) + "}"


def sdc_text(ports: list[tuple[str, str]], clocks: list[str]) -> str:
    period = f"{config.CLOCK_PERIOD_NS:.3f}"
    lines = [f"create_clock -name {{{c}}} -period {period} [get_ports {{{c}}}]" for c in clocks]
    lines += ["derive_pll_clocks", f"derive_clocks -period {period}", "derive_clock_uncertainty"]
    jtag = [p for p, _ in ports if p.startswith("altera_reserved_")]
    data_in = [p for p, d in ports if d in ("in", "inout") and p not in clocks and p not in jtag]
    data_out = [p for p, d in ports if d in ("out", "inout") and p not in jtag]
    if data_in and data_out:
        skip_in, skip_out = clocks + jtag, jtag
        src = f"[remove_from_collection [all_inputs] [get_ports {tcl_names(skip_in)}]]" if skip_in else "[all_inputs]"
        dst = f"[remove_from_collection [all_outputs] [get_ports {tcl_names(skip_out)}]]" if skip_out else "[all_outputs]"
        lines.append(f"set_max_delay -from {src} -to {dst} {config.COMB_MAX_DELAY_NS:.3f}")
        lines.append(f"set_min_delay -from {src} -to {dst} 0.000")
    return "\n".join(lines) + "\n"


def quartus(args: list[str], cwd: Path, log: Path) -> int:
    """Run a Quartus command; after FLOW_TIMEOUT seconds the whole process tree is stopped."""
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "w", encoding="utf-8", errors="replace", newline="\n") as fh:
        proc = subprocess.Popen(args, cwd=str(cwd), stdout=fh, stderr=subprocess.STDOUT, text=True)
        try:
            return proc.wait(timeout=FLOW_TIMEOUT)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
            else:
                proc.kill()
            proc.wait()
            fh.write(f"\nError (timeout): the step exceeded the time limit of {FLOW_TIMEOUT} s\n")
            return 124


def fitter_notes(proj: Path, project: str) -> list[str]:
    """Readable Fitter messages about placement and routing, taken from the Fitter message database."""
    f = proj / "db" / f"{project}.fit.qmsg"
    if not f.exists():
        return []
    text = f.read_bytes().decode("latin-1")
    msgs = re.findall(r"(?:Fitter|Router|Routing|The router)[A-Za-z ,\-()0-9%:.]{20,200}", text)
    keep = [m.strip() for m in msgs if "%1" not in m and re.search(r"placement|routing|congestion|interconnect", m, re.I)]
    out = []
    for m in keep:
        if m not in out:
            out.append(m)
    return out[-6:]


def compile_one(sample: dict, out_root: Path, seed: int = config.FITTER_SEED, force: bool = False) -> dict:
    sid = sample["sample_id"]
    out = out_root / sid
    status_file = out / "compile_status.json"
    if status_file.exists() and not force:
        return read_json(status_file)
    proj = config.BUILD / "quartus" / f"{sid}_s{seed}"
    shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir(parents=True)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    qbin = config.quartus_bin()
    status = {"sample_id": sid, "seed": seed, "top": sample["top"]}
    t0 = time.time()
    status.update(prepare_sources(sample, proj))
    write_text(proj / "probe.sdc", "")
    write_text(proj / "virtual.txt", "")

    # Pass 1: synthesis, port list and clock ports.
    hdlver = "VERILOG_2001"
    rc = quartus([str(qbin / "quartus_sh"), "-t", str(HERE / "flow.tcl"), "probe", sample["top"], "files.txt",
                  "probe.sdc", str(seed), "virtual.txt", "probe", hdlver], proj, proj / "probe.log")
    if rc != 0 and "Verilog HDL syntax error" in (proj / "probe.log").read_text(errors="replace"):
        hdlver = "SYSTEMVERILOG_2005"
        rc = quartus([str(qbin / "quartus_sh"), "-t", str(HERE / "flow.tcl"), "probe", sample["top"], "files.txt",
                      "probe.sdc", str(seed), "virtual.txt", "probe", hdlver], proj, proj / "probe.log")
    status["hdl_version"] = hdlver
    status["probe_exit"] = rc
    ok = rc == 0
    if ok:
        quartus([str(qbin / "quartus_sta"), "-t", str(HERE / "ports.tcl"), "probe", "ports.tsv"], proj,
                proj / "ports.log")
        ok = (proj / "ports.tsv").exists()
    if not ok:
        status["errors"] = first_errors(proj / "probe.log")
        status["failed_stage"] = "timeout" if rc == 124 else "synthesis"
    else:
        ports, clocks = parse_ports(proj / "ports.tsv")
        status["ports_in"] = sum(d == "in" for _, d in ports)
        status["ports_out"] = sum(d == "out" for _, d in ports)
        status["ports_inout"] = sum(d == "inout" for _, d in ports)
        status["clock_ports"] = clocks
        # JTAG pins that Quartus adds for on-chip debug blocks must stay device pins.
        virtual = [p for p, _ in ports if p not in clocks and not p.startswith("altera_reserved_")]
        write_text(proj / "virtual.txt", "\n".join(virtual) + "\n")
        write_text(proj / "design.sdc", sdc_text(ports, clocks))
        # Pass 2: full flow with virtual pins.
        rc = quartus([str(qbin / "quartus_sh"), "-t", str(HERE / "flow.tcl"), sid, sample["top"], "files.txt",
                      "design.sdc", str(seed), "virtual.txt", "full", hdlver], proj, proj / "flow.log")
        status["flow_exit"] = rc
        for stage in ("map", "fit", "sta", "asm", "pow", "eda"):
            status[stage] = message_counts(proj / f"{sid}.{stage}.rpt")
        if rc == 0:
            quartus([str(qbin / "quartus_sh"), "-t", str(HERE / "export_panels.tcl"), sid, "panels.tsv"], proj,
                    proj / "panels.log")
            quartus([str(qbin / "quartus_sta"), "-t", str(HERE / "timing_paths.tcl"), sid, "timing.tsv"], proj,
                    proj / "timing.log")
            vo = proj / "simulation" / "questa" / f"{sid}.vo"
            if vo.exists():
                shutil.copyfile(vo, out / "postfit.vo")
                status["netlist_sha256"] = sha256_file(out / "postfit.vo")
            for name in ("panels.tsv", "timing.tsv"):
                if (proj / name).exists():
                    shutil.copyfile(proj / name, out / name)
            for f in proj.iterdir():
                if f.name.endswith(KEEP):
                    shutil.copyfile(f, out / f.name)
        else:
            status["errors"] = first_errors(proj / "flow.log")
            status["failed_stage"] = {2: "synthesis", 3: "fitter", 4: "timing", 5: "assembler", 6: "power",
                                      7: "netlist", 124: "timeout"}.get(rc, "flow")
            if rc in (3, 124):
                status["fitter_notes"] = fitter_notes(proj, sid)
    for name in ("files.txt", "ports.tsv", "design.sdc", "virtual.txt", "probe.log", "flow.log"):
        if (proj / name).exists():
            shutil.copyfile(proj / name, out / name)
    status["flow_seconds"] = round(time.time() - t0, 1)
    status["ok"] = all((out / n).exists() for n in ("panels.tsv", "timing.tsv", "postfit.vo"))
    write_json(status_file, status)
    for d in ("db", "incremental_db", "simulation"):
        shutil.rmtree(proj / d, ignore_errors=True)
    return status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--only", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--seed", type=int, default=config.FITTER_SEED)
    ap.add_argument("--catalog", default=str(config.METADATA_DIR / "catalog.json"))
    ap.add_argument("--out", default="")
    ap.add_argument("--defer", default="", help="sample identifiers to schedule after all others")
    args = ap.parse_args()
    samples = read_json(Path(args.catalog))["samples"]
    if args.only:
        keep = set(args.only.split(","))
        samples = [s for s in samples if s["sample_id"] in keep]
    out_root = Path(args.out) if args.out else config.BUILD / ("compiled" if args.seed == config.FITTER_SEED
                                                               else f"compiled_seed{args.seed}")
    size = {s["sample_id"]: sum((RAW / f).stat().st_size for f in s["files"]) for s in samples}
    deferred = set(args.defer.split(",")) if args.defer else set()
    samples.sort(key=lambda s: (s["sample_id"] in deferred, size[s["sample_id"]]))
    done = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futs = {pool.submit(compile_one, s, out_root, args.seed, args.force): s["sample_id"] for s in samples}
        for f in as_completed(futs):
            try:
                st = f.result()
            except Exception as ex:
                st = {"sample_id": futs[f], "ok": False, "exception": str(ex)[:300]}
                write_json(out_root / futs[f] / "compile_status.json", st)
            done += 1
            print(f"[{done}/{len(samples)}] {st['sample_id']} ok={st['ok']} {st.get('flow_seconds')}s "
                  f"{st.get('failed_stage', '')}", flush=True)


if __name__ == "__main__":
    main()
