"""Structural and testability features of a Quartus post-fit Verilog netlist (.vo).

The netlist lists MAX 10 atoms: logic cells (fiftyfivenm_lcell_comb, a 4-input
LUT with a carry output), registers (dffeas), I/O buffers, clock-control
blocks and, when used, memory and multiplier blocks.  The parser builds a
signal graph from the port connections and computes, without using any signal
name:

* cell counts, LUT input usage and a coarse classification of LUT functions,
* fan-out statistics, logic depth and carry-chain length,
* connectivity (weakly connected components, strongly connected components
  formed through registers),
* COP signal probabilities under independent inputs with probability 0.5,
* combinational SCOAP controllability (CC0, CC1) and observability (CO), with
  register outputs treated as pseudo-primary inputs and register inputs as
  pseudo-primary outputs.

LUT semantics follow the Quartus simulation model of fiftyfivenm_lcell_comb:
combout = mask[{d, c', b, a}], where c' is datac or cin according to
sum_lutc_input, and cout = mask[{0, cin, b, a}].
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np

NAN = float("nan")
INF = 10 ** 6
LUT_IN = ("dataa", "datab", "datac", "datad")
HIDDEN = {"fiftyfivenm_unvm", "fiftyfivenm_adcblock"}
OUTPUTS = {
    "fiftyfivenm_lcell_comb": ("combout", "cout"),
    "dffeas": ("q",),
    "fiftyfivenm_io_ibuf": ("o",),
    "fiftyfivenm_io_obuf": ("o", "obar"),
    "fiftyfivenm_clkctrl": ("outclk",),
    "fiftyfivenm_ram_block": ("portadataout", "portbdataout"),
    "fiftyfivenm_mac_mult": ("dataout",),
    "fiftyfivenm_mac_out": ("dataout",),
    "fiftyfivenm_pll": ("clk", "locked", "fbout", "phasedone", "clkbad", "activeclock", "scandataout",
                        "scandone", "vcooverrange", "vcounderrange"),
}
DFF_SINKS = ("d", "ena", "sclr", "sload", "asdata", "clrn", "prn", "aload")
CONST = {"gnd": 0, "vcc": 1}
GLOBAL_TIES = {"devclrn", "devpor", "devoe", "unknown"}
KEYWORDS = {"module", "input", "output", "inout", "wire", "reg", "assign", "defparam", "tri1", "tri0",
            "initial", "always", "endmodule", "primitive", "specify", "timescale"}

INST = re.compile(r"^[ \t]*(\w+)[ \t]+(\\\S+|\w+)[ \t]*\(", re.M)
PORT = re.compile(r"\.(\w+)\s*\(")
DEFPARAM = re.compile(r"^\s*defparam\s+(\\\S+|\w+)\s*\.(\w+)\s*=\s*(.*?);\s*$", re.M)
DECL = re.compile(r"^\s*(input|output)\s*(\[(\d+):(\d+)\])?\s*([^;]+);", re.M)

FEATURES = {
    "net_pi_bits": ("count", "Primary input bits of the top-level module"),
    "net_po_bits": ("count", "Primary output bits of the top-level module"),
    "net_lcells": ("count", "Logic cells (4-input LUT with carry) in the post-fit netlist"),
    "net_lcells_arith": ("count", "Logic cells that use the carry input or drive a carry output"),
    "net_dffs": ("count", "Registers (dffeas)"),
    "net_ram_blocks": ("count", "Embedded memory blocks"),
    "net_mac_blocks": ("count", "Embedded multiplier blocks (mult and output stages)"),
    "net_clock_nets": ("count", "Distinct nets that drive register clock pins"),
    "net_signals": ("count", "Distinct driven signals excluding clock nets"),
    "net_pins": ("count", "Signal-to-cell input connections excluding clock nets"),
    "net_lut_k0": ("count", "Logic cells whose LUT uses no data input"),
    "net_lut_k1": ("count", "Logic cells whose LUT uses 1 data input"),
    "net_lut_k2": ("count", "Logic cells whose LUT uses 2 data inputs"),
    "net_lut_k3": ("count", "Logic cells whose LUT uses 3 data inputs"),
    "net_lut_k4": ("count", "Logic cells whose LUT uses 4 data inputs"),
    "net_fanin_mean": ("count", "Mean number of used LUT data inputs per logic cell"),
    "net_fn_and_frac": ("fraction", "Normal-mode LUTs (2+ inputs) whose output is 1 for exactly one input combination"),
    "net_fn_or_frac": ("fraction", "Normal-mode LUTs (2+ inputs) whose output is 0 for exactly one input combination"),
    "net_fn_xor_frac": ("fraction", "Normal-mode LUTs (2+ inputs) computing parity or its complement"),
    "net_fn_buf_frac": ("fraction", "Normal-mode LUTs with one used input (buffer or inverter)"),
    "net_fn_other_frac": ("fraction", "Normal-mode LUTs with any other function"),
    "net_fanout_mean": ("count", "Mean fan-out of driven signals (clock nets excluded)"),
    "net_fanout_std": ("count", "Standard deviation of signal fan-out"),
    "net_fanout_max": ("count", "Maximum signal fan-out"),
    "net_fanout_p90": ("count", "90th percentile of signal fan-out"),
    "net_fanout_ge8_frac": ("fraction", "Signals with fan-out of at least 8"),
    "net_depth_max": ("levels", "Longest chain of logic-cell outputs between sequential or I/O boundaries"),
    "net_depth_mean": ("levels", "Mean logic depth at register inputs and primary outputs"),
    "net_depth_nocarry_max": ("levels", "Longest logic chain counting carry links as zero levels"),
    "net_carry_chain_max": ("cells", "Longest chain of carry-out to carry-in links"),
    "net_carry_chains": ("count", "Carry chains of two or more cells"),
    "net_wcc": ("count", "Weakly connected components of the cell graph"),
    "net_wcc_largest_frac": ("fraction", "Share of cells in the largest weakly connected component"),
    "net_scc_count": ("count", "Strongly connected components with more than one cell (feedback through registers)"),
    "net_scc_frac": ("fraction", "Share of cells inside such feedback components"),
    "net_sp_lt_1e2_frac": ("fraction", "Logic-cell outputs with COP probability of the rarer value below 0.01"),
    "net_sp_lt_1e3_frac": ("fraction", "Logic-cell outputs with COP probability of the rarer value below 0.001"),
    "net_sp_lt_1e4_frac": ("fraction", "Logic-cell outputs with COP probability of the rarer value below 0.0001"),
    "net_sp_lt_1e2": ("count", "Logic-cell outputs with COP probability of the rarer value below 0.01"),
    "net_sp_min_log10": ("log10", "Base-10 logarithm of the smallest COP rare-value probability (floored at -12)"),
    "net_sp_entropy_mean": ("bits", "Mean binary entropy of logic-cell output probabilities"),
    "net_cc0_max": ("SCOAP", "Maximum finite combinational 0-controllability"),
    "net_cc1_max": ("SCOAP", "Maximum finite combinational 1-controllability"),
    "net_cc1_p90": ("SCOAP", "90th percentile of combinational 1-controllability"),
    "net_cc_mean": ("SCOAP", "Mean of CC0 and CC1 over logic-cell outputs"),
    "net_co_max": ("SCOAP", "Maximum finite combinational observability"),
    "net_co_p90": ("SCOAP", "90th percentile of combinational observability"),
    "net_co_mean": ("SCOAP", "Mean combinational observability over logic-cell outputs"),
    "net_cc_hard_frac": ("fraction", "Logic-cell outputs with CC0 or CC1 of at least 20"),
    "net_co_hard_frac": ("fraction", "Logic-cell outputs with CO of at least 20"),
}


def _unescape(tok: str) -> str:
    tok = tok.strip()
    return tok[1:].strip() if tok.startswith("\\") else tok


def _split_concat(value: str) -> list[str]:
    value = value.strip()
    if not (value.startswith("{") and value.endswith("}")):
        return [value]
    inner, items, cur, i = value[1:-1], [], "", 0
    while i < len(inner):
        c = inner[i]
        if c == "\\":
            j = i
            while j < len(inner) and inner[j] not in " \t\n":
                j += 1
            cur += inner[i:j]
            i = j
            continue
        if c == ",":
            items.append(cur)
            cur = ""
        else:
            cur += c
        i += 1
    items.append(cur)
    return [x.strip() for x in items if x.strip()]


def _is_const(tok: str) -> bool:
    return tok in CONST or tok in GLOBAL_TIES or bool(re.fullmatch(r"\d+'[bhdo][0-9a-fA-FxXzZ_]+", tok)) or tok == ""


def _scan_ports(text: str, i: int):
    """Parse '.port(value), ...' from text[i:] up to the closing ')' of the instance."""
    ports, n = {}, len(text)
    while i < n:
        c = text[i]
        if c == "\\":
            while i < n and text[i] not in " \t\n":
                i += 1
            continue
        if c == ".":
            m = PORT.match(text, i)
            if m:
                i = m.end()
                start, depth = i, 1
                while i < n and depth:
                    ch = text[i]
                    if ch == "\\":
                        while i < n and text[i] not in " \t\n":
                            i += 1
                        continue
                    if ch == "(":
                        depth += 1
                    elif ch == ")":
                        depth -= 1
                    i += 1
                ports[m.group(1)] = text[start:i - 1]
                continue
        if c == ")":
            return ports, i + 1
        i += 1
    return ports, n


def parse(path: Path):
    text = Path(path).read_text(encoding="latin-1")
    text = re.sub(r"//[^\n]*", "", text)
    params = defaultdict(dict)
    for inst, key, val in DEFPARAM.findall(text):
        params[_unescape(inst)][key] = val.strip().strip('"')
    cells = []
    for m in INST.finditer(text):
        ctype, inst = m.group(1), m.group(2)
        if ctype in KEYWORDS:
            continue
        ports, _ = _scan_ports(text, m.end())
        conns = {p: [_unescape(t) for t in _split_concat(v)] for p, v in ports.items()}
        name = _unescape(inst)
        cells.append({"type": ctype, "name": name, "ports": conns, "params": params.get(name, {})})
    pi = po = 0
    end = text.find("endmodule")
    top = text[:end] if end >= 0 else text
    body = top[top.find(");") + 2:] if ");" in top else top
    for d, rng, hi, lo, names in DECL.findall(body):
        if names.strip().startswith("\\") or "~" in names:
            continue
        width = abs(int(hi) - int(lo)) + 1 if rng else 1
        count = len([x for x in names.split(",") if x.strip()])
        if d == "input":
            pi += width * count
        else:
            po += width * count
    return cells, pi, po


def _lut_prob(mask: int, probs) -> float:
    total = 0.0
    for m in range(16):
        if (mask >> m) & 1:
            p = 1.0
            for k in range(4):
                p *= probs[k] if (m >> k) & 1 else 1.0 - probs[k]
            total += p
    return total


def _lut_cc(mask: int, cc0, cc1):
    best = [INF, INF]
    for m in range(16):
        v = (mask >> m) & 1
        cost = 1
        for k in range(4):
            cost += cc1[k] if (m >> k) & 1 else cc0[k]
        best[v] = min(best[v], cost)
    return min(best[0], INF), min(best[1], INF)


def _lut_obs(mask: int, cc0, cc1, k: int) -> int:
    best = INF
    for m in range(16):
        if (m >> k) & 1:
            continue
        if ((mask >> m) & 1) == ((mask >> (m | (1 << k))) & 1):
            continue
        cost = 1
        for j in range(4):
            if j != k:
                cost += cc1[j] if (m >> j) & 1 else cc0[j]
        best = min(best, cost)
    return best


def _reduced_function(mask: int, consts: dict):
    """Truth table of a 4-input mask over its non-constant inputs (constants substituted)."""
    free = [k for k in range(4) if k not in consts]
    table = []
    for idx in range(1 << len(free)):
        m = 0
        for j, k in enumerate(free):
            if (idx >> j) & 1:
                m |= 1 << k
        for k, v in consts.items():
            if v:
                m |= 1 << k
        table.append((mask >> m) & 1)
    return free, table


def _classify(table, nfree) -> str:
    ones = sum(table)
    size = len(table)
    if nfree == 1:
        return "buf"
    if nfree == 0 or ones in (0, size):
        return "const"
    if ones == 1:
        return "and"
    if ones == size - 1:
        return "or"
    parity = [bin(i).count("1") & 1 for i in range(size)]
    if table == parity or table == [1 - x for x in parity]:
        return "xor"
    return "other"


def extract(path: Path) -> dict:
    cells, pi_bits, po_bits = parse(path)
    cells = [c for c in cells if c["type"] not in HIDDEN]
    driver = {}
    for idx, c in enumerate(cells):
        for port in OUTPUTS.get(c["type"], ()):
            for net in c["ports"].get(port, []):
                if net and not _is_const(net):
                    driver[net] = (idx, port)
    clock_nets = set()
    for c in cells:
        if c["type"] in ("dffeas", "fiftyfivenm_ram_block", "fiftyfivenm_mac_mult", "fiftyfivenm_mac_out"):
            for port in ("clk", "clk0", "clk1", "portaclk", "portbclk"):
                clock_nets.update(n for n in c["ports"].get(port, []) if not _is_const(n))
    for c in cells:
        if c["type"] == "fiftyfivenm_clkctrl" and any(n in clock_nets for n in c["ports"].get("outclk", [])):
            clock_nets.update(n for n in c["ports"].get("inclk", []) if not _is_const(n))

    sinks = defaultdict(list)
    for idx, c in enumerate(cells):
        outs = OUTPUTS.get(c["type"], ())
        for port, nets in c["ports"].items():
            if port in outs or port in ("clk", "clk0", "clk1", "portaclk", "portbclk"):
                continue
            for net in nets:
                if net and not _is_const(net) and net not in clock_nets:
                    sinks[net].append((idx, port))

    f = {k: NAN for k in FEATURES}
    lc = [i for i, c in enumerate(cells) if c["type"] == "fiftyfivenm_lcell_comb"]
    f["net_pi_bits"], f["net_po_bits"] = float(pi_bits), float(po_bits)
    f["net_lcells"] = float(len(lc))
    f["net_dffs"] = float(sum(c["type"] == "dffeas" for c in cells))
    f["net_ram_blocks"] = float(sum(c["type"] == "fiftyfivenm_ram_block" for c in cells))
    f["net_mac_blocks"] = float(sum(c["type"] in ("fiftyfivenm_mac_mult", "fiftyfivenm_mac_out") for c in cells))

    # Signal identifiers: (cell index, output port); undriven nets become sources.
    def sig_of(net):
        return driver.get(net, ("src", net))

    def is_used(net):
        return net and not _is_const(net)

    lut_info = {}
    arith = 0
    kcount = [0] * 5
    fn_counts = defaultdict(int)
    for i in lc:
        c = cells[i]
        mask = int(re.sub(r"^\d+'h", "", c["params"].get("lut_mask", "0")) or "0", 16)
        use_cin = c["params"].get("sum_lutc_input", "datac") == "cin"
        ins = []
        consts = {}
        for k, port in enumerate(LUT_IN):
            net = c["ports"].get(port, [""])[0] if c["ports"].get(port) else ""
            if k == 2 and use_cin:
                net = c["ports"].get("cin", [""])[0] if c["ports"].get("cin") else ""
            if is_used(net):
                ins.append(net)
            else:
                ins.append(None)
                consts[k] = CONST.get(net, 0)
        cin = c["ports"].get("cin", [""])[0] if c["ports"].get("cin") else ""
        cout_used = bool(c["ports"].get("cout") and c["ports"]["cout"][0])
        if (use_cin and is_used(cin)) or cout_used:
            arith += 1
        used = sum(1 for x in ins if x is not None)
        kcount[used] += 1
        if not use_cin and not cout_used:
            free, table = _reduced_function(mask, consts)
            fn_counts[_classify(table, len(free))] += 1
        lut_info[i] = {"mask": mask, "ins": ins, "consts": consts, "cin": cin if is_used(cin) else None,
                       "cout_used": cout_used}
    f["net_lcells_arith"] = float(arith)
    for k in range(5):
        f[f"net_lut_k{k}"] = float(kcount[k])
    f["net_fanin_mean"] = float(np.mean([sum(x is not None for x in v["ins"]) for v in lut_info.values()])) if lut_info else 0.0
    nfn = sum(v for k, v in fn_counts.items() if k != "const")
    for key in ("and", "or", "xor", "buf", "other"):
        f[f"net_fn_{key}_frac"] = fn_counts[key] / nfn if nfn else 0.0

    # Fan-out over driven, non-clock signals.
    fo = [len(sinks.get(net, [])) for net in driver if net not in clock_nets]
    f["net_clock_nets"] = float(len(clock_nets))
    f["net_signals"] = float(len(fo))
    f["net_pins"] = float(sum(len(v) for v in sinks.values()))
    if fo:
        arr = np.array(fo, dtype=float)
        f["net_fanout_mean"], f["net_fanout_std"] = float(arr.mean()), float(arr.std())
        f["net_fanout_max"], f["net_fanout_p90"] = float(arr.max()), float(np.percentile(arr, 90))
        f["net_fanout_ge8_frac"] = float((arr >= 8).mean())

    # Signal graph of logic-cell outputs for depth, probability and SCOAP.
    G = nx.DiGraph()
    carry_edges = []
    for i, info in lut_info.items():
        out_c, out_y = (i, "combout"), (i, "cout")
        G.add_node(out_c)
        for net in info["ins"]:
            if net is not None:
                G.add_edge(sig_of(net), out_c)
        if info["cout_used"]:
            G.add_node(out_y)
            for k in (0, 1):
                if info["ins"][k] is not None:
                    G.add_edge(sig_of(info["ins"][k]), out_y)
            if info["cin"] is not None:
                G.add_edge(sig_of(info["cin"]), out_y)
        if info["cin"] is not None:
            src = sig_of(info["cin"])
            if src[0] != "src" and src[1] == "cout":
                carry_edges.append((src[0], i))
    lut_nodes = [n for n in G.nodes if n[0] != "src" and n[0] in lut_info
                 and (n[1] == "cout" or any(x is not None for x in lut_info[n[0]]["ins"]))]
    try:
        order = list(nx.topological_sort(G))
    except nx.NetworkXUnfeasible:
        order = None

    endpoints = set()
    for i, c in enumerate(cells):
        if c["type"] == "dffeas":
            for port in DFF_SINKS:
                for net in c["ports"].get(port, []):
                    if is_used(net) and net not in clock_nets:
                        endpoints.add(sig_of(net))
        elif c["type"] not in ("fiftyfivenm_lcell_comb", "fiftyfivenm_clkctrl"):
            outs = OUTPUTS.get(c["type"], ())
            for port, nets in c["ports"].items():
                if port in outs:
                    continue
                for net in nets:
                    if is_used(net) and net not in clock_nets:
                        endpoints.add(sig_of(net))

    if order is not None and lut_nodes:
        depth, depth_nc = {}, {}
        for n in order:
            preds = list(G.predecessors(n))
            if n[0] == "src" or n[0] not in lut_info:
                depth[n] = depth_nc[n] = 0
                continue
            depth[n] = 1 + max((depth[p] for p in preds), default=0)
            is_carry_link = n[1] == "cout"
            depth_nc[n] = (0 if is_carry_link else 1) + max((depth_nc[p] for p in preds), default=0)
        f["net_depth_max"] = float(max(depth[n] for n in lut_nodes))
        f["net_depth_nocarry_max"] = float(max(depth_nc[n] for n in lut_nodes))
        ep = [depth.get(e, 0) for e in endpoints if e in depth]
        f["net_depth_mean"] = float(np.mean(ep)) if ep else 0.0

        # COP probabilities: register outputs are iterated to a fixed point.
        prob = {}
        dff_list = [i for i, c in enumerate(cells) if c["type"] == "dffeas"]
        qsig = {}
        for i in dff_list:
            for net in cells[i]["ports"].get("q", []):
                if is_used(net):
                    qsig[i] = (i, "q")
        for n in G.nodes:
            if n[0] == "src" or n not in lut_nodes:
                prob[n] = 0.5

        def pin_prob(net):
            if net is None or not is_used(net):
                return float(CONST.get(net, 0)) if net else 0.0
            return prob.get(sig_of(net), 0.5)

        for _ in range(12):
            for n in order:
                if n[0] == "src" or n[0] not in lut_info:
                    continue
                info = lut_info[n[0]]
                ps = [prob.get(sig_of(x), 0.5) if x is not None else float(info["consts"].get(k, 0))
                      for k, x in enumerate(info["ins"])]
                if n[1] == "cout":
                    pc = prob.get(sig_of(info["cin"]), 0.5) if info["cin"] is not None else 0.0
                    prob[n] = _lut_prob(info["mask"] & 0xFF, [ps[0], ps[1], pc, 0.0])
                else:
                    prob[n] = _lut_prob(info["mask"], ps)
            changed = 0.0
            for i, s in qsig.items():
                c = cells[i]

                def pp(port, default):
                    nets = c["ports"].get(port, [])
                    if not nets or not nets[0]:
                        return default
                    return pin_prob(nets[0]) if is_used(nets[0]) else float(CONST.get(nets[0], default))
                p_d, p_sl, p_sc, p_as = pp("d", 0.0), pp("sload", 0.0), pp("sclr", 0.0), pp("asdata", 0.0)
                new = (1 - p_sc) * (p_sl * p_as + (1 - p_sl) * p_d)
                changed = max(changed, abs(new - prob.get(s, 0.5)))
                prob[s] = new
            if changed < 1e-6:
                break
        rare = np.array([min(prob[n], 1 - prob[n]) for n in lut_nodes])
        f["net_sp_lt_1e2"] = float((rare < 1e-2).sum())
        f["net_sp_lt_1e2_frac"] = float((rare < 1e-2).mean())
        f["net_sp_lt_1e3_frac"] = float((rare < 1e-3).mean())
        f["net_sp_lt_1e4_frac"] = float((rare < 1e-4).mean())
        nz = rare[rare > 0]
        f["net_sp_min_log10"] = float(max(-12.0, math.log10(nz.min()))) if nz.size else -12.0
        pr = np.clip(np.array([prob[n] for n in lut_nodes]), 1e-12, 1 - 1e-12)
        f["net_sp_entropy_mean"] = float(np.mean(-(pr * np.log2(pr) + (1 - pr) * np.log2(1 - pr))))

        # SCOAP controllability (forward) and observability (backward).
        cc0, cc1 = {}, {}

        def pin_cc(x, k, info):
            if x is None:
                v = info["consts"].get(k, 0)
                return (0, INF) if v == 0 else (INF, 0)
            s = sig_of(x)
            return cc0.get(s, 1), cc1.get(s, 1)

        for n in order:
            if n[0] == "src" or n[0] not in lut_info:
                cc0[n], cc1[n] = 1, 1
                continue
            info = lut_info[n[0]]
            pins = [pin_cc(x, k, info) for k, x in enumerate(info["ins"])]
            if n[1] == "cout":
                cin_cc = (cc0.get(sig_of(info["cin"]), 1), cc1.get(sig_of(info["cin"]), 1)) if info["cin"] else (0, INF)
                pins = [pins[0], pins[1], cin_cc, (0, INF)]
                mask = info["mask"] & 0xFF
            else:
                mask = info["mask"]
            cc0[n], cc1[n] = _lut_cc(mask, [p[0] for p in pins], [p[1] for p in pins])
        co = defaultdict(lambda: INF)
        for e in endpoints:
            co[e] = 0
        for i, c in enumerate(cells):
            if c["type"] == "fiftyfivenm_io_obuf":
                for net in c["ports"].get("i", []):
                    if is_used(net):
                        co[sig_of(net)] = 0
        for n in reversed(order):
            if n[0] == "src" or n[0] not in lut_info or co[n] >= INF:
                continue
            info = lut_info[n[0]]
            if n[1] == "cout":
                srcs = [info["ins"][0], info["ins"][1], info["cin"], None]
                mask = info["mask"] & 0xFF
                pins = [pin_cc(srcs[0], 0, info), pin_cc(srcs[1], 1, info),
                        (cc0.get(sig_of(info["cin"]), 1), cc1.get(sig_of(info["cin"]), 1)) if info["cin"] else (0, INF),
                        (0, INF)]
            else:
                srcs = info["ins"]
                mask = info["mask"]
                pins = [pin_cc(x, k, info) for k, x in enumerate(srcs)]
            c0, c1 = [p[0] for p in pins], [p[1] for p in pins]
            for k, x in enumerate(srcs):
                if x is None:
                    continue
                s = sig_of(x)
                co[s] = min(co[s], co[n] + _lut_obs(mask, c0, c1, k))
        cc0v = np.array([cc0[n] for n in lut_nodes if cc0[n] < INF], dtype=float)
        cc1v = np.array([cc1[n] for n in lut_nodes if cc1[n] < INF], dtype=float)
        cov = np.array([co[n] for n in lut_nodes if co[n] < INF], dtype=float)
        if cc0v.size:
            f["net_cc0_max"] = float(cc0v.max())
        if cc1v.size:
            f["net_cc1_max"], f["net_cc1_p90"] = float(cc1v.max()), float(np.percentile(cc1v, 90))
        both = np.concatenate([cc0v, cc1v])
        f["net_cc_mean"] = float(both.mean()) if both.size else NAN
        if cov.size:
            f["net_co_max"], f["net_co_p90"], f["net_co_mean"] = float(cov.max()), float(np.percentile(cov, 90)), float(cov.mean())
        hard = [max(cc0[n], cc1[n]) >= 20 for n in lut_nodes]
        f["net_cc_hard_frac"] = float(np.mean(hard))
        f["net_co_hard_frac"] = float(np.mean([co[n] >= 20 for n in lut_nodes]))
    else:
        # A combinational cycle leaves the logic depth undefined; a netlist without logic cells has depth 0.
        for k in ("net_depth_max", "net_depth_nocarry_max", "net_depth_mean"):
            f[k] = NAN if order is None else 0.0

    # Carry chains.
    nxt = {a: b for a, b in carry_edges}
    starts = set(nxt) - set(nxt.values())
    lengths = []
    for s in starts:
        n, length = s, 1
        while n in nxt and length < 100000:
            n, length = nxt[n], length + 1
        lengths.append(length)
    f["net_carry_chain_max"] = float(max(lengths, default=0))
    f["net_carry_chains"] = float(sum(1 for x in lengths if x >= 2))

    # Cell-level connectivity.
    C = nx.DiGraph()
    logic_cells = [i for i, c in enumerate(cells) if c["type"] != "fiftyfivenm_clkctrl"]
    C.add_nodes_from(logic_cells)
    for net, lst in sinks.items():
        d = driver.get(net)
        if d is None:
            continue
        for j, _p in lst:
            if d[0] in C and j in C and d[0] != j:
                C.add_edge(d[0], j)
    if C.number_of_nodes():
        comps = list(nx.weakly_connected_components(C))
        f["net_wcc"] = float(len(comps))
        f["net_wcc_largest_frac"] = float(max(len(c) for c in comps) / C.number_of_nodes())
        scc = [s for s in nx.strongly_connected_components(C) if len(s) > 1]
        f["net_scc_count"] = float(len(scc))
        f["net_scc_frac"] = float(sum(len(s) for s in scc) / C.number_of_nodes())
    assert set(f) == set(FEATURES)
    return f
