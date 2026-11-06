"""Features derived from Quartus Prime compilation reports and timing paths.

Inputs per design (written by scripts/quartus/compile.py):
  panels.tsv  every report panel exported with the ::quartus::report Tcl package
  timing.tsv  longest and shortest path delays per path class, Fmax and worst slacks
              for the slow 1200 mV 85 C timing model

All values are design-level numbers.  Names of design signals that appear in
some panels (for example the maximum fan-out node) are never used as features.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

NAN = float("nan")

# name: (unit, source, description)
FEATURES = {
    # Analysis & Synthesis
    "syn_le_est": ("count", "Analysis & Synthesis Resource Usage Summary", "Estimated total logic elements after synthesis"),
    "syn_comb_functions": ("count", "Analysis & Synthesis Resource Usage Summary", "Total combinational functions"),
    "syn_lut4": ("count", "Analysis & Synthesis Resource Usage Summary", "Combinational functions with 4 LUT inputs"),
    "syn_lut3": ("count", "Analysis & Synthesis Resource Usage Summary", "Combinational functions with 3 LUT inputs"),
    "syn_lut_le2": ("count", "Analysis & Synthesis Resource Usage Summary", "Combinational functions with 2 or fewer LUT inputs"),
    "syn_le_normal": ("count", "Analysis & Synthesis Resource Usage Summary", "Logic elements in normal mode"),
    "syn_le_arith": ("count", "Analysis & Synthesis Resource Usage Summary", "Logic elements in arithmetic (carry-chain) mode"),
    "syn_registers": ("count", "Analysis & Synthesis Resource Usage Summary", "Total registers"),
    "syn_io_registers": ("count", "Analysis & Synthesis Resource Usage Summary", "Registers packed into I/O elements"),
    "syn_io_pins": ("count", "Analysis & Synthesis Resource Usage Summary", "I/O pins"),
    "syn_mult9": ("count", "Analysis & Synthesis Resource Usage Summary", "Embedded multiplier 9-bit elements"),
    "syn_mem_bits": ("bits", "Analysis & Synthesis Summary", "Total memory bits"),
    "syn_max_fanout": ("count", "Analysis & Synthesis Resource Usage Summary", "Maximum fan-out of any node"),
    "syn_total_fanout": ("count", "Analysis & Synthesis Resource Usage Summary", "Sum of fan-outs over all nodes"),
    "syn_avg_fanout": ("ratio", "Analysis & Synthesis Resource Usage Summary", "Average fan-out"),
    "syn_reg_sclr": ("count", "General Register Statistics", "Registers using synchronous clear"),
    "syn_reg_sload": ("count", "General Register Statistics", "Registers using synchronous load"),
    "syn_reg_aclr": ("count", "General Register Statistics", "Registers using asynchronous clear"),
    "syn_reg_aload": ("count", "General Register Statistics", "Registers using asynchronous load"),
    "syn_reg_ena": ("count", "General Register Statistics", "Registers using clock enable"),
    "syn_reg_preset": ("count", "General Register Statistics", "Registers using preset"),
    "syn_mux_groups": ("count", "Multiplexer Restructuring Statistics", "Multiplexer groups listed by the restructuring report"),
    "syn_mux_bits": ("bits", "Multiplexer Restructuring Statistics", "Total bus width of listed multiplexers"),
    "syn_mux_max_inputs": ("count", "Multiplexer Restructuring Statistics", "Largest number of multiplexer data inputs"),
    "syn_mux_baseline_le": ("count", "Multiplexer Restructuring Statistics", "Baseline area of listed multiplexers"),
    "syn_max_lut_depth": ("levels", "Post-Synthesis Netlist Statistics", "Maximum LUT depth"),
    "syn_avg_lut_depth": ("levels", "Post-Synthesis Netlist Statistics", "Average LUT depth"),
    # Fitter
    "fit_le": ("count", "Fitter Resource Usage Summary", "Total logic elements after fitting"),
    "fit_le_comb_only": ("count", "Fitter Resource Usage Summary", "Logic elements: combinational with no register"),
    "fit_le_reg_only": ("count", "Fitter Resource Usage Summary", "Logic elements: register only"),
    "fit_le_comb_reg": ("count", "Fitter Resource Usage Summary", "Logic elements: combinational with a register"),
    "fit_lut4": ("count", "Fitter Resource Usage Summary", "Logic elements using 4 LUT inputs"),
    "fit_lut3": ("count", "Fitter Resource Usage Summary", "Logic elements using 3 LUT inputs"),
    "fit_lut_le2": ("count", "Fitter Resource Usage Summary", "Logic elements using 2 or fewer LUT inputs"),
    "fit_le_normal": ("count", "Fitter Resource Usage Summary", "Logic elements in normal mode"),
    "fit_le_arith": ("count", "Fitter Resource Usage Summary", "Logic elements in arithmetic mode"),
    "fit_registers": ("count", "Fitter Resource Usage Summary", "Total registers"),
    "fit_labs": ("count", "Fitter Resource Usage Summary", "Logic array blocks partially or completely used"),
    "fit_io_pins": ("count", "Fitter Resource Usage Summary", "I/O pins"),
    "fit_m9k": ("count", "Fitter Resource Usage Summary", "M9K memory blocks"),
    "fit_mem_bits": ("bits", "Fitter Resource Usage Summary", "Total block memory bits"),
    "fit_mult9": ("count", "Fitter Resource Usage Summary", "Embedded multiplier 9-bit elements"),
    "fit_pll": ("count", "Fitter Resource Usage Summary", "PLLs"),
    "fit_global_signals": ("count", "Fitter Resource Usage Summary", "Signals routed on global networks"),
    "fit_ic_avg_pct": ("percent", "Fitter Resource Usage Summary", "Average interconnect usage (total)"),
    "fit_ic_peak_pct": ("percent", "Fitter Resource Usage Summary", "Peak interconnect usage (total)"),
    "fit_max_fanout": ("count", "Fitter Resource Usage Summary", "Maximum fan-out"),
    "fit_max_nonglobal_fanout": ("count", "Fitter Resource Usage Summary", "Highest non-global fan-out"),
    "fit_total_fanout": ("count", "Fitter Resource Usage Summary", "Total fan-out"),
    "fit_avg_fanout": ("ratio", "Fitter Resource Usage Summary", "Average fan-out"),
    "fit_lab_avg_le": ("count", "LAB Logic Elements", "Average logic elements per used LAB"),
    "fit_lab_avg_inputs": ("count", "LAB Distinct Inputs", "Average distinct inputs per used LAB"),
    "fit_lab_avg_sourced": ("count", "LAB Signals Sourced", "Average signals sourced per used LAB"),
    "fit_lab_avg_sourced_out": ("count", "LAB Signals Sourced Out", "Average signals leaving each used LAB"),
    "fit_ctrl_signals": ("count", "Control Signals", "Distinct register control signals"),
    "fit_ctrl_clock_enable": ("count", "Control Signals", "Control signals used as clock enables"),
    "fit_ctrl_sync": ("count", "Control Signals", "Control signals used as synchronous clear or load"),
    "fit_ctrl_async": ("count", "Control Signals", "Control signals used as asynchronous clear or load"),
    # Routing
    "rte_block": ("count", "Routing Usage Summary", "Block interconnects used"),
    "rte_c4": ("count", "Routing Usage Summary", "C4 column interconnects used"),
    "rte_c16": ("count", "Routing Usage Summary", "C16 column interconnects used"),
    "rte_r4": ("count", "Routing Usage Summary", "R4 row interconnects used"),
    "rte_r24": ("count", "Routing Usage Summary", "R24 row interconnects used"),
    "rte_direct": ("count", "Routing Usage Summary", "Direct links used"),
    "rte_local": ("count", "Routing Usage Summary", "Local interconnects used"),
    # Timing (slow 1200 mV 85 C model unless stated)
    "sta_fmax_mhz": ("MHz", "timing_paths.tcl get_clock_fmax_info", "Maximum clock frequency of the slowest clock from register-to-register paths, before the device restriction on clock period and I/O toggle rate; missing for designs without such a path"),
    "sta_setup_slack_ns": ("ns", "timing_paths.tcl report_timing", "Worst setup slack against the 20 ns constraint"),
    "sta_hold_slack_ns": ("ns", "timing_paths.tcl report_timing", "Worst hold slack"),
    "sta_mc_setup_slack_ns": ("ns", "Multicorner Timing Analysis Summary", "Worst setup slack over the three timing corners"),
    "sta_mc_hold_slack_ns": ("ns", "Multicorner Timing Analysis Summary", "Worst hold slack over the three timing corners"),
}
for _cls, _txt in (("in2out", "input to output"), ("in2reg", "input to register"),
                   ("reg2reg", "register to register"), ("reg2out", "register to output")):
    FEATURES[f"sta_{_cls}_max_ns"] = ("ns", "timing_paths.tcl get_path", f"Longest {_txt} data delay; missing when no such path exists")
    FEATURES[f"sta_{_cls}_min_ns"] = ("ns", "timing_paths.tcl get_path -min_path", f"Shortest {_txt} data delay; missing when no such path exists")
    FEATURES[f"sta_{_cls}_levels"] = ("levels", "timing_paths.tcl get_path", f"Logic levels on the longest {_txt} path; missing when no such path exists")
FEATURES.update({
    # Power (vectorless estimate, default toggle rate 12.5 %)
    "pow_total_mw": ("mW", "Power Analyzer Summary", "Total thermal power, vectorless estimate"),
    "pow_core_dynamic_mw": ("mW", "Power Analyzer Summary", "Core dynamic thermal power, vectorless estimate"),
    "pow_core_static_mw": ("mW", "Power Analyzer Summary", "Core static thermal power"),
    "pow_io_mw": ("mW", "Power Analyzer Summary", "I/O thermal power, vectorless estimate"),
    "pow_comb_mw": ("mW", "Thermal Power Dissipation by Block Type", "Combinational cell power"),
    "pow_reg_mw": ("mW", "Thermal Power Dissipation by Block Type", "Register cell power"),
    "pow_clock_mw": ("mW", "Thermal Power Dissipation by Block Type", "Clock control block power"),
    "pow_comb_toggle": ("Mtransitions/s", "Thermal Power Dissipation by Block Type", "Average toggle rate of combinational cells"),
    "pow_reg_toggle": ("Mtransitions/s", "Thermal Power Dissipation by Block Type", "Average toggle rate of register cells"),
    "pow_vcc_dynamic_ma": ("mA", "Current Drawn from Voltage Supplies Summary", "Dynamic current drawn from the VCC core supply"),
})


def read_panels(path: Path) -> dict:
    panels, cur = {}, None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("#PANEL\t"):
                cur = line.split("\t")[1]
                panels[cur] = []
            elif cur is not None:
                panels[cur].append(line.split("\t"))
    return panels


def num(text) -> float:
    """First number in a report cell such as '13 / 49,760 ( < 1 % )' or '100.68 mW'."""
    if text is None:
        return NAN
    m = re.search(r"-?\d[\d,]*\.?\d*", str(text))
    return float(m.group(0).replace(",", "")) if m else NAN


def find_panel(panels: dict, suffix: str):
    for name, rows in panels.items():
        if name.endswith(suffix):
            return rows
    return None


def keyed_rows(rows) -> dict:
    """Map 'parent/child' labels of a two-column resource panel to their value cells."""
    out, parent = {}, ""
    for r in rows or []:
        if not r or not r[0].strip():
            continue
        label = r[0]
        value = r[1] if len(r) > 1 else ""
        stripped = label.strip()
        if stripped.startswith("--"):
            out[f"{parent}/{stripped.lstrip('- ').strip()}"] = value
        else:
            parent = stripped.rstrip("*: ").strip()
            out[parent] = value
    return out


def header_average(rows) -> float:
    if not rows:
        return NAN
    m = re.search(r"Average\s*=\s*([\d.]+)", rows[0][0])
    return float(m.group(1)) if m else NAN


def parse_timing(path: Path) -> dict:
    out = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            key = parts[0]
            if key == "fmax":
                m = re.findall(r"\{?(\S+)\s+([\d.]+)\s+([\d.]+)", parts[1]) if len(parts) > 1 else []
                # Unrestricted Fmax of the slowest clock (the second number is the restricted Fmax).
                out["fmax"] = min(float(x[1]) for x in m) if m else NAN
            elif key.startswith("worst_"):
                # report_timing returns the number of paths and the worst slack; without a path there is no slack.
                out[key] = num(parts[2]) if len(parts) > 2 and num(parts[1]) > 0 else NAN
            elif len(parts) >= 4 and parts[1] in ("max", "min"):
                out[f"{key}_{parts[1]}"] = float(parts[2])
                if parts[1] == "max":
                    out[f"{key}_levels"] = float(parts[3])
    return out


def extract(compiled_dir: Path) -> dict:
    panels = read_panels(compiled_dir / "panels.tsv")
    f = {k: NAN for k in FEATURES}

    syn = keyed_rows(find_panel(panels, "Analysis & Synthesis Resource Usage Summary"))
    f["syn_le_est"] = num(syn.get("Estimated Total logic elements"))
    f["syn_comb_functions"] = num(syn.get("Total combinational functions"))
    f["syn_lut4"] = num(syn.get("Logic element usage by number of LUT inputs/4 input functions"))
    f["syn_lut3"] = num(syn.get("Logic element usage by number of LUT inputs/3 input functions"))
    f["syn_lut_le2"] = num(syn.get("Logic element usage by number of LUT inputs/<=2 input functions"))
    f["syn_le_normal"] = num(syn.get("Logic elements by mode/normal mode"))
    f["syn_le_arith"] = num(syn.get("Logic elements by mode/arithmetic mode"))
    f["syn_registers"] = num(syn.get("Total registers"))
    f["syn_io_registers"] = num(syn.get("Total registers/I/O registers"))
    f["syn_io_pins"] = num(syn.get("I/O pins"))
    f["syn_mult9"] = num(syn.get("Embedded Multiplier 9-bit elements"))
    f["syn_max_fanout"] = num(syn.get("Maximum fan-out"))
    f["syn_total_fanout"] = num(syn.get("Total fan-out"))
    f["syn_avg_fanout"] = num(syn.get("Average fan-out"))
    summ = keyed_rows(find_panel(panels, "Analysis & Synthesis||Analysis & Synthesis Summary"))
    f["syn_mem_bits"] = num(summ.get("Total memory bits"))

    reg = keyed_rows(find_panel(panels, "General Register Statistics"))
    for key, label in (("sclr", "Synchronous Clear"), ("sload", "Synchronous Load"), ("aclr", "Asynchronous Clear"),
                       ("aload", "Asynchronous Load"), ("ena", "Clock Enable"), ("preset", "Preset")):
        f[f"syn_reg_{key}"] = num(reg.get(f"Number of registers using {label}", 0))

    mux = None
    for name, rows in panels.items():
        if "Multiplexer Restructuring Statistics" in name:
            mux = rows
    if mux is not None:
        body = [r for r in mux[1:] if len(r) >= 3 and ":" in r[0]]
        f["syn_mux_groups"] = float(len(body))
        f["syn_mux_bits"] = float(sum(num(r[1]) for r in body))
        f["syn_mux_max_inputs"] = float(max([num(r[0].split(":")[0]) for r in body], default=0))
        f["syn_mux_baseline_le"] = float(sum(num(r[2]) for r in body))
    else:
        for k in ("syn_mux_groups", "syn_mux_bits", "syn_mux_max_inputs", "syn_mux_baseline_le"):
            f[k] = 0.0

    pss = find_panel(panels, "Post-Synthesis Netlist Statistics for Top Partition") or []
    for r in pss:
        lab = r[0].strip() if r else ""
        if lab == "Max LUT depth":
            f["syn_max_lut_depth"] = num(r[1])
        elif lab == "Average LUT depth":
            f["syn_avg_lut_depth"] = num(r[1])

    fit = keyed_rows(find_panel(panels, "Fitter Resource Usage Summary"))
    f["fit_le"] = num(fit.get("Total logic elements"))
    f["fit_le_comb_only"] = num(fit.get("Total logic elements/Combinational with no register"))
    f["fit_le_reg_only"] = num(fit.get("Total logic elements/Register only"))
    f["fit_le_comb_reg"] = num(fit.get("Total logic elements/Combinational with a register"))
    f["fit_lut4"] = num(fit.get("Logic element usage by number of LUT inputs/4 input functions"))
    f["fit_lut3"] = num(fit.get("Logic element usage by number of LUT inputs/3 input functions"))
    f["fit_lut_le2"] = num(fit.get("Logic element usage by number of LUT inputs/<=2 input functions"))
    f["fit_le_normal"] = num(fit.get("Logic elements by mode/normal mode"))
    f["fit_le_arith"] = num(fit.get("Logic elements by mode/arithmetic mode"))
    f["fit_registers"] = num(fit.get("Total registers"))
    f["fit_labs"] = num(fit.get("Total LABs:  partially or completely used", fit.get("Total LABs")))
    f["fit_io_pins"] = num(fit.get("I/O pins"))
    f["fit_m9k"] = num(fit.get("M9Ks"))
    f["fit_mem_bits"] = num(fit.get("Total block memory bits"))
    f["fit_mult9"] = num(fit.get("Embedded Multiplier 9-bit elements"))
    f["fit_pll"] = num(fit.get("PLLs"))
    f["fit_global_signals"] = num(fit.get("Global signals"))
    f["fit_ic_avg_pct"] = num(fit.get("Average interconnect usage (total/H/V)"))
    f["fit_ic_peak_pct"] = num(fit.get("Peak interconnect usage (total/H/V)"))
    f["fit_max_fanout"] = num(fit.get("Maximum fan-out"))
    f["fit_max_nonglobal_fanout"] = num(fit.get("Highest non-global fan-out"))
    f["fit_total_fanout"] = num(fit.get("Total fan-out"))
    f["fit_avg_fanout"] = num(fit.get("Average fan-out"))
    f["fit_lab_avg_le"] = header_average(find_panel(panels, "LAB Logic Elements"))
    f["fit_lab_avg_inputs"] = header_average(find_panel(panels, "LAB Distinct Inputs"))
    f["fit_lab_avg_sourced"] = header_average(find_panel(panels, "LAB Signals Sourced"))
    f["fit_lab_avg_sourced_out"] = header_average(find_panel(panels, "LAB Signals Sourced Out"))

    ctrl = find_panel(panels, "Control Signals") or []
    usage = [r[3].strip().lower() for r in ctrl[1:] if len(r) > 3]
    f["fit_ctrl_signals"] = float(len(usage))
    f["fit_ctrl_clock_enable"] = float(sum("clock enable" in u for u in usage))
    f["fit_ctrl_sync"] = float(sum(u.startswith("sync") for u in usage))
    f["fit_ctrl_async"] = float(sum(u.startswith("async") for u in usage))

    rte = keyed_rows(find_panel(panels, "Routing Usage Summary"))
    for key, label in (("block", "Block interconnects"), ("c4", "C4 interconnects"), ("c16", "C16 interconnects"),
                       ("r4", "R4 interconnects"), ("r24", "R24 interconnects"), ("direct", "Direct links"),
                       ("local", "Local interconnects")):
        f[f"rte_{key}"] = num(rte.get(label))

    tim = parse_timing(compiled_dir / "timing.tsv")
    f["sta_fmax_mhz"] = tim.get("fmax", NAN)
    f["sta_setup_slack_ns"] = tim.get("worst_setup", NAN)
    f["sta_hold_slack_ns"] = tim.get("worst_hold", NAN)
    for cls in ("in2out", "in2reg", "reg2reg", "reg2out"):
        f[f"sta_{cls}_max_ns"] = tim.get(f"{cls}_max", NAN)
        f[f"sta_{cls}_min_ns"] = tim.get(f"{cls}_min", NAN)
        f[f"sta_{cls}_levels"] = tim.get(f"{cls}_levels", NAN)
    mc = find_panel(panels, "Multicorner Timing Analysis Summary") or []
    for r in mc:
        if r and r[0].strip() == "Worst-case Slack":
            f["sta_mc_setup_slack_ns"] = num(r[1])
            f["sta_mc_hold_slack_ns"] = num(r[2])

    pw = keyed_rows(find_panel(panels, "Power Analyzer||Power Analyzer Summary"))
    f["pow_total_mw"] = num(pw.get("Total Thermal Power Dissipation"))
    f["pow_core_dynamic_mw"] = num(pw.get("Core Dynamic Thermal Power Dissipation"))
    f["pow_core_static_mw"] = num(pw.get("Core Static Thermal Power Dissipation"))
    f["pow_io_mw"] = num(pw.get("I/O Thermal Power Dissipation"))
    blocks = find_panel(panels, "Thermal Power Dissipation by Block Type") or []
    for r in blocks[1:]:
        if len(r) < 6:
            continue
        kind = r[0].strip().lower()
        if kind.startswith("combinational"):
            f["pow_comb_mw"], f["pow_comb_toggle"] = num(r[1]), num(r[5])
        elif kind.startswith("register"):
            f["pow_reg_mw"], f["pow_reg_toggle"] = num(r[1]), num(r[5])
        elif kind.startswith("clock control"):
            f["pow_clock_mw"] = num(r[1])
    for k in ("pow_comb_mw", "pow_reg_mw", "pow_clock_mw", "pow_comb_toggle", "pow_reg_toggle"):
        if math.isnan(f[k]):
            f[k] = 0.0
    cur = find_panel(panels, "Current Drawn from Voltage Supplies Summary") or []
    for r in cur:
        if r and r[0].strip() == "VCC" and len(r) > 2:
            f["pow_vcc_dynamic_ma"] = num(r[2])
    assert set(f) == set(FEATURES)
    return f


def metadata(compiled_dir: Path) -> dict:
    """Compilation facts recorded alongside, but never used as, predictive features."""
    panels = read_panels(compiled_dir / "panels.tsv")
    pw = keyed_rows(find_panel(panels, "Power Analyzer||Power Analyzer Summary"))
    flow = keyed_rows(find_panel(panels, "Flow Summary"))
    return {"power_confidence": pw.get("Power Estimation Confidence", ""),
            "quartus_version": flow.get("Quartus Prime Version", ""),
            "device": flow.get("Device", ""),
            "flow_status": flow.get("Flow Status", "")}
