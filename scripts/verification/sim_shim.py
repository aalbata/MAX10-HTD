"""Open simulation models for the encrypted MAX 10 atom wrappers.

The Quartus MAX 10 library (fiftyfivenm_atoms.v) implements a few wrappers,
including the I/O buffers and the hidden flash and ADC blocks, through modules
that are distributed only in encrypted form for one commercial simulator.  This
script reads the plain-text wrappers from the local Quartus installation and
writes a replacement for each encrypted module: input and output buffers pass
data through (with output enable and open-drain handling), and the remaining
blocks drive their outputs low.  None of these blocks implements design logic,
so the logic cells and registers are still simulated by the original models.
No Quartus source text is redistributed; the file is generated locally.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def write_shim(atoms: Path, out: Path) -> int:
    src = atoms.read_text(encoding="latin-1")
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"//[^\n]*", "", src)
    mods = re.findall(r"\bmodule\s+(\w+)\s*(#\s*\(.*?\))?\s*\((.*?)\);(.*?)\bendmodule", src, re.S)
    blocks = ["`timescale 1 ps/1 ps"]
    for name, _hdr, ports, body in mods:
        m = re.search(r"\b(%s_encrypted)\b" % re.escape(name), body)
        if not m:
            continue
        params = re.findall(r"\bparameter\s+(?:\w+\s+)?(\w+)\s*=\s*([^;]+);", body)
        decls = re.findall(r"^\s*(input|output|inout)\s*(\[[^\]]+\])?\s*([\w\s,]+);", body, re.M)
        names = [x.strip() for x in ports.replace("\n", " ").split(",") if x.strip()]
        lines = [f"module {m.group(1)} ({', '.join(names)});"]
        lines += [f"  parameter {pn} = {pv.strip()};" for pn, pv in params]
        outs = []
        for direction, width, group in decls:
            for sig in [s.strip() for s in group.split(",") if s.strip()]:
                lines.append(f"  {direction} {width or ''} {sig};")
                if direction == "output":
                    outs.append(sig)
        if name.endswith("io_ibuf"):
            lines.append("  assign o = i;")
        elif name.endswith("io_obuf"):
            lines.append("  assign o = (open_drain_output == \"true\") ? "
                         "((oe && !i) ? 1'b0 : 1'bz) : (oe ? i : 1'bz);")
            lines.append("  assign obar = ~o;")
        else:
            lines += [f"  assign {sig} = 0;" for sig in outs]
        lines.append("endmodule")
        blocks.append("\n".join(lines))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n\n".join(blocks) + "\n", encoding="ascii")
    return len(blocks) - 1


if __name__ == "__main__":
    n = write_shim(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"wrote {n} replacement modules")
