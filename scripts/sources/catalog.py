"""Build the sample catalog of MAX10-HTD from the unpacked public benchmarks.

Each sample is one design: a set of HDL files, a top-level module, a label
taken from the benchmark source (Trojan-inserted or Trojan-free), and the
identifier of its Trojan-free reference.  In the release of Hayashi et al.,
a Trojan-inserted file is paired with the golden module whose identifiers it
shares most, which is the module named in its file name for all files except
most of the MINER files virtual_wire_T*.  Identical Trojan-free designs that several
archives ship are kept once.  Archives that cannot enter the
catalog are listed with the reason in dataset/metadata/excluded_items.csv.

Usage:
  python -m scripts.sources.catalog

Writes dataset/metadata/catalog.json, catalog.csv and excluded_items.csv.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

from ..common import config
from ..common.util import write_json
from . import hdl

RAW = config.BUILD / "raw"
ID_SEED = 20261104

FAMILIES = {
    "aes_128": "cryptographic", "uart": "communication", "mc8051": "processor", "pic16f84": "processor",
    "b19": "processor", "mem_ctrl": "memory", "wb_conmax": "interconnect", "sram": "memory",
    "fpgaminer_top": "cryptographic", "sha256_transform": "cryptographic", "sha256_functions": "cryptographic",
    "bip39": "cryptographic", "random": "cryptographic", "crypto_wallet2_top": "processor",
    "uart_comm": "communication", "uart_rx": "communication", "uart_tx": "communication",
    "uart_tx_fifo": "communication", "main_pll": "clocking", "virtual_wire": "debug",
    "ALU_RV32I": "processor", "Branch_CTLR": "processor", "CTLR_Unit_RV32I": "processor",
    "Data_Path_RV32I": "processor", "Immediate_Gen": "processor", "MUX_to_Reg_File": "processor",
    "PC": "processor", "Register_File": "processor", "RV32I_Top": "processor",
    "prepherial_datapath": "processor", "dsram": "memory", "isram": "memory", "P2S": "communication",
    "StP": "communication", "simpleBus": "interconnect",
}


def rel(p: Path) -> str:
    return p.relative_to(RAW).as_posix()


def content_key(files: list[Path]) -> str:
    """Digest of a file set that ignores whitespace, comments and file order."""
    h = hashlib.sha256()
    for f in sorted(files, key=lambda p: p.name.lower()):
        text = hdl.read(f)
        text = hdl.strip_vhdl_comments(text) if f.suffix.lower() in hdl.VHDL_SUFFIXES else hdl.strip_verilog_comments(text)
        text = re.sub(r'`include\s+"[^"]*?([^/"\\]+)"', r'`include "\1"', text)
        h.update(f.name.lower().encode() + b"\0" + re.sub(r"\s+", " ", text).strip().encode() + b"\0")
    return h.hexdigest()


def language(files: list[Path]) -> str:
    kinds = {"vhdl" if f.suffix.lower() in hdl.VHDL_SUFFIXES else "verilog"
             for f in files if f.suffix.lower() not in hdl.INCLUDE_SUFFIXES}
    return "mixed" if len(kinds) > 1 else kinds.pop()


def verilog_set(folder: Path, top: str) -> tuple[list[Path], set[str]]:
    files = [p for p in sorted(folder.glob("*")) if p.suffix.lower() in hdl.VERILOG_SUFFIXES
             and not hdl.is_testbench_name(p)]
    need, missing = hdl.closure(top, files)
    inc = []
    for f in need:
        for name in hdl.includes(hdl.read(f)):
            cand = folder / Path(name.replace("\\", "/")).name
            if cand.exists() and cand not in inc:
                inc.append(cand)
    return need + inc, missing


def vhdl_set(folder: Path) -> tuple[list[Path], set[str]]:
    """Non-testbench VHDL files of a folder, plus Verilog files for components no VHDL file defines."""
    out, ents, refs = [], set(), set()
    for p in sorted(folder.glob("*")):
        if p.suffix.lower() not in hdl.VHDL_SUFFIXES or hdl.is_testbench_name(p):
            continue
        text = hdl.read(p)
        e = hdl.vhdl_entities(text)
        if e and all(x.startswith(("tb_", "testbench")) or x.endswith("_tb") for x in e):
            continue
        out.append(p)
        ents |= e
        refs |= hdl.vhdl_references(text)
    missing = refs - ents
    vfiles = [p for p in sorted(folder.glob("*")) if p.suffix.lower() in hdl.VERILOG_SUFFIXES
              and not hdl.is_testbench_name(p)]
    vmods = {m.lower(): m for f in vfiles for m in hdl.verilog_modules(hdl.read(f))}
    for comp in sorted(missing & set(vmods)):
        need, _ = hdl.closure(vmods[comp], vfiles)
        out += [f for f in need if f not in out]
    return out, missing - set(vmods)


# ---------------------------------------------------------------- Trust-Hub

def trusthub_tags(entry: dict) -> dict:
    tags = {}
    for t in entry["tags"].split("::"):
        parts = t.split(":")
        if len(parts) >= 3:
            tags.setdefault(parts[1], []).append(":".join(parts[2:]))
    act = tags.get("activation-mechanism", [])
    if any(a.startswith("triggered:externally") for a in act):
        trigger = "triggered-externally"
    elif any(a.startswith("triggered:internally") for a in act):
        trigger = "triggered-internally"
    elif "always-on" in act:
        trigger = "always-on"
    else:
        trigger = "not-stated"
    effects = sorted(tags.get("effect", [])) or ["not-stated"]
    return {"trigger": trigger, "trigger_detail": ";".join(act) or "not-stated", "payload": ";".join(effects),
            "abstraction": ";".join(tags.get("abstraction-level", []))}


TRUSTHUB_RTL = {
    # host prefix: (design key, clean folder, infected folder, top of clean, top of infected, language)
    "AES": ("aes_128", "src/TjFree", "src/TjIn", "aes_128", None, "verilog"),
    "B19": ("b19", "src/TjFree", "src/TjIn", "b19", "b19", "vhdl"),
    "MC8051": ("mc8051", "src/TjFree", "src/TjIn", "mc8051_top", "mc8051_top", "vhdl"),
    "PIC16F84": ("pic16f84", "src/TjFree", "src/TjIn", "pic_16f84_core", "pic_16f84_core", "verilog"),
    "RS232": ("uart", "src/TjFree", "src/TjIn", "uart", "uart", "verilog"),
    "wb_conmax": ("wb_conmax", "src/TjFree", "src/TjIn", "wb_conmax_top", "wb_conmax_top", "verilog"),
    "memctrl": ("mem_ctrl", "rtl/verilog", "rtl/verilog_tj_In", "mc_top", "mc_top", "verilog"),
}


def trusthub(samples: list, excluded: list) -> None:
    cat = json.loads((RAW / "trusthub" / "archives" / "benchmarks-trojan-chip.json").read_text(encoding="utf-8"))
    rs232_clean = None
    pending_rs232 = []
    for e in sorted(cat, key=lambda e: e["name"]):
        name = e["name"]
        if name.startswith("TRIT-"):
            excluded.append(("trusthub", name, "gate-level netlists mapped to an ASIC standard-cell library whose "
                             "simulation models are not distributed with the benchmark"))
            continue
        tags = trusthub_tags(e)
        if len(e["links"]) != 1:
            excluded.append(("trusthub", name, "distributed as a multi-part archive of ASIC layout or gate-level "
                             "databases; not downloaded"))
            continue
        if tags["abstraction"] != "register-transfer":
            excluded.append(("trusthub", name, f"{tags['abstraction']}-level netlist mapped to an ASIC standard-cell "
                             "library whose simulation models are not distributed with the benchmark"))
            continue
        prefix = name.split("-")[0]
        if prefix == "BasicRSA":
            excluded.append(("trusthub", name, "archive contains no Trojan-free version of the design"))
            continue
        key, cdir, tdir, ctop, ttop, lang = TRUSTHUB_RTL[prefix]
        stem = e["links"][0].rsplit("/", 1)[-1].rsplit(".", 1)[0]
        root = RAW / "trusthub" / "x" / stem / stem
        if not root.exists():
            root = RAW / "trusthub" / "x" / stem
        tfolder = root / tdir
        if prefix == "AES" and not tfolder.exists() and (root / "src" / "TnIn").exists():
            tfolder = root / "src" / "TnIn"
        if prefix == "RS232" and not tfolder.exists():
            tfolder = root / "src"
        cfolder = root / cdir
        if lang == "vhdl":
            top_t = ttop
            tfiles, tmissing = vhdl_set(tfolder)
            cfiles, cmissing = vhdl_set(cfolder) if cfolder.exists() else (None, set())
        else:
            files_t = [p for p in tfolder.glob("*") if p.suffix.lower() in hdl.VERILOG_SUFFIXES
                       and not hdl.is_testbench_name(p)]
            top_t = ttop or hdl.roots(files_t)[0]
            tfiles, tmissing = verilog_set(tfolder, top_t)
            cfiles, cmissing = verilog_set(cfolder, ctop) if cfolder.exists() else (None, set())
        clean = None
        if cfiles:
            clean = {"source": "trusthub", "source_items": [name], "role": "clean", "label": 0, "design": key,
                     "top": ctop, "files": [rel(p) for p in cfiles], "language": language(cfiles),
                     "unresolved_modules": sorted(cmissing), "content_key": content_key(cfiles),
                     "source_verification": "Trojan-free version shipped in the benchmark archive"}
            samples.append(clean)
            if prefix == "RS232":
                rs232_clean = clean
        trojan = {"source": "trusthub", "source_items": [name], "role": "trojan", "label": 1, "design": key,
                  "top": top_t, "files": [rel(p) for p in tfiles], "language": language(tfiles),
                  "unresolved_modules": sorted(tmissing), "content_key": content_key(tfiles),
                  "trigger": tags["trigger"], "trigger_detail": tags["trigger_detail"], "payload": tags["payload"],
                  "source_verification": "label from the Trust-Hub catalog; no activation result published",
                  "clean_key": clean["content_key"] if clean else None}
        if prefix == "RS232" and clean is None:
            pending_rs232.append(trojan)
        samples.append(trojan)
    for t in pending_rs232:
        t["clean_key"] = rs232_clean["content_key"]
        t["clean_note"] = ("archive ships no Trojan-free version; paired with the Trojan-free RS232 design of "
                           "RS232-T2100 to RS232-T2400, which differs from the unmodified files of this archive "
                           "only in absolute include paths")


# -------------------------------------------------------------------- GHOST

def primary_module(path: Path) -> str | None:
    mods = list(hdl.verilog_modules(hdl.read(path)))
    if not mods:
        return None
    return path.stem if path.stem in mods else mods[0]



GHOST_EFFECT = {"0": "change-functionality", "1": "leak-information", "2": "denial-of-service"}
GHOST_MODEL = {"gpt-4": "GPT-4", "llama3-70b-8192": "LLaMA3-70B", "models_gemini-1.5-pro-latest": "Gemini-1.5-pro"}


def ghost_taxonomy(folder: Path) -> str:
    tax = next(iter(folder.glob("*taxonomy*.txt")), None)
    trigger = "not-stated"
    if tax:
        text = re.sub(r"\*", "", hdl.read(tax)).lower()
        m = re.search(r"activation mechanism:\s*([^\n]+)", text)
        if m:
            a = m.group(1)
            trigger = ("triggered-externally" if "extern" in a else "triggered-internally" if "intern" in a
                       else "always-on" if "always" in a else "not-stated")
    return trigger


def ghost(samples: list, excluded: list) -> None:
    base = next((RAW / "ghost" / "x").glob("*/GHOST_benchmarks-*"))
    for model in sorted(GHOST_MODEL):
        for hostdir in sorted((base / model).iterdir()):
            worked = hostdir / "worked"
            if not worked.is_dir():
                continue
            failed = hostdir / "X"
            if failed.is_dir():
                for f in sorted(failed.glob("*.v")):
                    if "_net" not in f.name:
                        excluded.append(("ghost", f"{model}/{hostdir.name}/X/{f.name}",
                                         "listed by GHOST as a failed generation attempt"))
            designs = sorted((d for d in worked.iterdir() if d.is_dir()),
                             key=lambda d: (not d.name.endswith("HT_free"), d.name))
            def rtl(d):
                return [p for p in sorted(d.glob("*.v")) if "_net" not in p.name and not hdl.is_testbench_name(p)
                        and not p.name.startswith(("tb", "test"))]
            # The design unit is the module that received the Trojan; its Trojan-free counterpart is
            # the module of the same name in the reference folder.
            target = None
            for d in designs:
                annotated = [p for p in rtl(d) if re.search(r"_A\d+\.v$", p.name)]
                if annotated:
                    target = primary_module(annotated[0])
                    break
            clean_key = None
            for d in designs:
                v = rtl(d)
                is_clean = d.name.endswith("HT_free")
                if is_clean:
                    files = v
                else:
                    cleaned = [p for p in v if "cleaned" in p.name]
                    annotated = [p for p in v if re.search(r"_A\d+\.v$", p.name)]
                    support = [p for p in v if p not in cleaned and p not in annotated]
                    files = annotated + support
                top = target if target else hdl.roots(files)[0]
                fset, missing = hdl.closure(top, files)
                item = f"{model}/{hostdir.name}/{d.name}"
                s = {"source": "ghost", "source_items": [item], "role": "clean" if is_clean else "trojan",
                     "label": 0 if is_clean else 1, "design": hostdir.name, "top": top,
                     "files": [rel(p) for p in fset], "language": "verilog", "unresolved_modules": sorted(missing),
                     "content_key": content_key(fset), "generator": GHOST_MODEL[model]}
                if is_clean:
                    s["source_verification"] = "reference design of the GHOST repository"
                    clean_key = s["content_key"]
                else:
                    m = re.search(r"[HT]T?(\d)(\d)(\d)$", d.name)
                    trigger = ghost_taxonomy(d)
                    s.update({"trigger": trigger, "trigger_detail": trigger,
                              "payload": GHOST_EFFECT.get(m.group(2), "not-stated") if m else "not-stated",
                              "source_verification": ("GHOST: dormant-mode and activation testbenches before and "
                                                      "after Yosys synthesis (folder 'worked')"),
                              "clean_key": clean_key})
                samples.append(s)


# ------------------------------------------------------------------ Hayashi

def identifiers(path: Path) -> set[str]:
    """Identifiers of a Verilog file, without comments, keywords and compiler directives."""
    text = hdl.strip_verilog_comments(hdl.read(path))
    return set(re.findall(r"(?<![`\w$])[A-Za-z_][\w$]*", text)) - hdl.VERILOG_KEYWORDS


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a or b else 1.0


def hayashi(samples: list, excluded: list) -> None:
    for design in ("WALLET", "MINER", "RISCV"):
        folder = RAW / "hayashi" / "x" / f"{design}_benchmarks_Verilog" / f"{design}_benchmarks_Verilog"
        golden = sorted(p for p in folder.glob("*.v") if not re.search(r"_T\d+$", p.stem))
        closures = {g: hdl.closure(primary_module(g), golden) for g in golden}
        keys = {g: content_key(closures[g][0]) for g in golden}
        names = {g: identifiers(g) for g in golden}
        for g in golden:
            gfiles, gmissing = closures[g]
            samples.append({"source": "hayashi", "source_items": [f"{design}/{g.name}"], "role": "clean",
                            "label": 0, "design": g.stem, "top": primary_module(g), "files": [rel(p) for p in gfiles],
                            "language": "verilog", "unresolved_modules": sorted(gmissing), "content_key": keys[g],
                            "source_verification": "golden module of the dataset"})
            for v in sorted(folder.glob(g.stem + "_T*.v"), key=lambda p: int(p.stem.rsplit("_T", 1)[1])):
                vmods = set(hdl.verilog_modules(hdl.read(v)))
                vtop = primary_module(v)
                if vtop is None:
                    excluded.append(("hayashi", f"{design}/{v.name}", "file defines no Verilog module"))
                    continue
                # The reference is the golden module whose identifiers the file shares most (Jaccard
                # similarity). It is the module named in the file name except for the MINER files
                # virtual_wire_T*, most of which are modified versions of the UART transmit FIFO.
                vnames = identifiers(v)
                host = max(golden, key=lambda p: (jaccard(vnames, names[p]), p == g))
                note = "" if host == g else (f"; paired with {host.stem}, of which it is a modified version, although "
                                             f"its file name refers to {g.stem}")
                others = [p for p in golden if p != host and not (set(hdl.verilog_modules(hdl.read(p))) & vmods)]
                tfiles, tmissing = hdl.closure(vtop, [v] + others)
                samples.append({"source": "hayashi", "source_items": [f"{design}/{v.name}"], "role": "trojan",
                                "label": 1, "design": host.stem, "top": vtop, "files": [rel(p) for p in tfiles],
                                "language": "verilog", "unresolved_modules": sorted(tmissing),
                                "content_key": content_key(tfiles), "trigger": "not-reported",
                                "trigger_detail": "not-reported", "payload": "not-reported",
                                "generator": "ChatGPT-4",
                                "source_verification": "label from the dataset; Verilator lint used by the authors"
                                                       + note,
                                "clean_key": keys[host]})


# ---------------------------------------------------------------- assembly

def merge_duplicates(samples: list, excluded: list) -> list:
    """Keep one sample per distinct design; merge provenance of identical copies."""
    out, seen = [], {}
    for s in samples:
        k = s["content_key"]
        if k in seen:
            first = seen[k]
            if first["label"] != s["label"]:
                for item in s["source_items"]:
                    excluded.append((s["source"], item, "Trojan-inserted file identical to its Trojan-free design "
                                     "after removing comments and white space"))
                continue
            first["source_items"] = sorted(set(first["source_items"]) | set(s["source_items"]))
            first.setdefault("also_in_sources", [])
            if s["source"] != first["source"] and s["source"] not in first["also_in_sources"]:
                first["also_in_sources"].append(s["source"])
            continue
        seen[k] = s
        out.append(s)
    return out


def main():
    samples, excluded = [], []
    trusthub(samples, excluded)
    ghost(samples, excluded)
    hayashi(samples, excluded)
    samples = merge_duplicates(samples, excluded)
    # Identifiers follow a pseudo-random order of the design contents, so that they carry no label
    # information; identifiers already issued in an earlier catalog are kept.
    previous = {}
    if (config.METADATA_DIR / "catalog.json").exists():
        old = json.loads((config.METADATA_DIR / "catalog.json").read_text(encoding="utf-8"))["samples"]
        previous = {s["content_key"]: s["sample_id"] for s in old}
    order = sorted(samples, key=lambda s: hashlib.sha256(f"{ID_SEED}:{s['content_key']}".encode()).hexdigest())
    ids = {s["content_key"]: previous[s["content_key"]] for s in samples if s["content_key"] in previous}
    issued = max((int(v[1:]) for v in previous.values()), default=0)
    for s in order:
        if s["content_key"] not in ids:
            issued += 1
            ids[s["content_key"]] = f"S{issued:04d}"
    for s in samples:
        s["sample_id"] = ids[s["content_key"]]
        ck = s.pop("clean_key", None)
        s["clean_reference"] = ids.get(ck) if ck else (s["sample_id"] if s["role"] == "clean" else None)
        s["family"] = FAMILIES.get(s["design"], "other")
    samples.sort(key=lambda s: s["sample_id"])
    write_json(config.METADATA_DIR / "catalog.json", {"samples": samples})
    cols = ["sample_id", "source", "role", "label", "design", "family", "top", "language", "clean_reference",
            "trigger", "payload", "source_items", "files"]
    with open(config.METADATA_DIR / "catalog.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(cols)
        for s in samples:
            w.writerow([";".join(s[c]) if isinstance(s.get(c), list) else s.get(c, "") for c in cols])
    with open(config.METADATA_DIR / "excluded_items.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["source", "item", "reason"])
        w.writerows(sorted(excluded))
    n1 = sum(s["label"] for s in samples)
    print(f"{len(samples)} samples ({n1} Trojan-inserted, {len(samples) - n1} Trojan-free); {len(excluded)} excluded items")


if __name__ == "__main__":
    main()
