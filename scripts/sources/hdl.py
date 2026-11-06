"""Light-weight scanning of Verilog and VHDL sources.

Used to choose the files and the top-level module of each benchmark design:
module definitions, module instantiations, include directives and VHDL
entity and component references are found with regular expressions after
comments are removed.  The scan does not elaborate the design; Quartus does
that during compilation and reports any file the scan missed.
"""
from __future__ import annotations

import re
from pathlib import Path

VERILOG_SUFFIXES = (".v", ".sv")
VHDL_SUFFIXES = (".vhd", ".vhdl")
INCLUDE_SUFFIXES = (".h", ".vh", ".svh", ".inc")

VERILOG_KEYWORDS = {
    "always", "and", "assign", "automatic", "begin", "buf", "bufif0", "bufif1", "case", "casex", "casez",
    "cmos", "deassign", "default", "defparam", "disable", "edge", "else", "end", "endcase", "endfunction",
    "endgenerate", "endmodule", "endprimitive", "endspecify", "endtable", "endtask", "event", "for", "force",
    "forever", "fork", "function", "generate", "genvar", "highz0", "highz1", "if", "ifnone", "initial",
    "inout", "input", "integer", "join", "large", "localparam", "macromodule", "medium", "module", "nand",
    "negedge", "nmos", "nor", "not", "notif0", "notif1", "or", "output", "parameter", "pmos", "posedge",
    "primitive", "pull0", "pull1", "pulldown", "pullup", "rcmos", "real", "realtime", "reg", "release",
    "repeat", "rnmos", "rpmos", "rtran", "rtranif0", "rtranif1", "scalared", "signed", "small", "specify",
    "specparam", "strong0", "strong1", "supply0", "supply1", "table", "task", "time", "tran", "tranif0",
    "tranif1", "tri", "tri0", "tri1", "triand", "trior", "trireg", "unsigned", "vectored", "wait", "wand",
    "weak0", "weak1", "while", "wire", "wor", "xnor", "xor", "logic", "bit", "byte", "int", "return",
    "always_ff", "always_comb", "always_latch", "unique", "priority", "typedef", "enum", "struct", "packed",
    "import", "export", "var", "const", "static", "void", "string", "else",
}


def strip_verilog_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def strip_vhdl_comments(text: str) -> str:
    return re.sub(r"--[^\n]*", "", text)


def read(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


MODULE_RE = re.compile(r"\b(?:module|macromodule)\s+(\\\S+|[A-Za-z_][\w$]*)")
INST_RE = re.compile(r"(?:^|[;\s)])([A-Za-z_][\w$]*)(?:\s+|\s*#\s*\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\)\s*)"
                     r"(\\\S+|[A-Za-z_][\w$]*)\s*(?:\[[^\]]*\]\s*)?\(", re.S)
INCLUDE_RE = re.compile(r'`include\s+"([^"]+)"')


def verilog_modules(text: str) -> dict[str, set[str]]:
    """Map each module defined in the text to the set of identifiers it instantiates."""
    text = strip_verilog_comments(text)
    out = {}
    for m in re.finditer(r"\b(?:module|macromodule)\s+(\\\S+|[A-Za-z_][\w$]*)(.*?)\bendmodule\b", text, re.S):
        body = m.group(2)
        insts = set()
        for i in INST_RE.finditer(body):
            name = i.group(1)
            if name not in VERILOG_KEYWORDS and i.group(2) not in VERILOG_KEYWORDS:
                insts.add(name)
        out[m.group(1)] = insts
    return out


def verilog_ports(text: str, module: str) -> int | None:
    """Number of names in the port list of a module, or None when the module is absent."""
    text = strip_verilog_comments(text)
    m = re.search(r"\bmodule\s+" + re.escape(module) + r"\s*(?:#\s*\((?:[^()]|\([^()]*\))*\)\s*)?\((.*?)\)\s*;",
                  text, re.S)
    if not m:
        return None
    return len([p for p in m.group(1).split(",") if p.strip()])


def includes(text: str) -> list[str]:
    return INCLUDE_RE.findall(strip_verilog_comments(text))


def vhdl_entities(text: str) -> set[str]:
    return {m.lower() for m in re.findall(r"\bentity\s+(\w+)\s+is\b", strip_vhdl_comments(text), re.I)}


def vhdl_references(text: str) -> set[str]:
    """Entity names referenced by component declarations or direct entity instantiation."""
    t = strip_vhdl_comments(text)
    refs = {m.lower() for m in re.findall(r"\bcomponent\s+(\w+)", t, re.I)}
    refs |= {m.lower() for m in re.findall(r"\bentity\s+\w+\.(\w+)", t, re.I)}
    return refs


def is_testbench_name(path: Path) -> bool:
    n = path.name.lower()
    return bool(re.match(r"(test|tb)[_\w]*\.(v|sv|vhd|vhdl)$", n) or re.search(r"(_tb|_test|tb)\.(v|sv|vhd|vhdl)$", n)
                or n.startswith("bench"))


def closure(top: str, files: list[Path]) -> tuple[list[Path], set[str]]:
    """Verilog files needed to elaborate `top` and the module names that no file defines."""
    defined: dict[str, Path] = {}
    insts: dict[str, set[str]] = {}
    for f in files:
        for mod, used in verilog_modules(read(f)).items():
            if mod not in defined:
                defined[mod] = f
                insts[mod] = used
    need, missing, seen = [], set(), set()
    stack = [top]
    while stack:
        mod = stack.pop()
        if mod in seen:
            continue
        seen.add(mod)
        if mod not in defined:
            missing.add(mod)
            continue
        if defined[mod] not in need:
            need.append(defined[mod])
        stack.extend(sorted(insts[mod]))
    return need, missing


def roots(files: list[Path]) -> list[str]:
    """Modules that no other module in the files instantiates (candidate top levels)."""
    mods: dict[str, set[str]] = {}
    for f in files:
        mods.update(verilog_modules(read(f)))
    used = set().union(*mods.values()) if mods else set()
    return sorted(m for m in mods if m not in used)
