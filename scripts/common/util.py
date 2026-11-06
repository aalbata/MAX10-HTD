"""Small helpers shared by the fetching, compilation, verification and extraction scripts."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


def derive_seed(*parts) -> int:
    """Deterministic 32-bit seed derived from the master seed and string parts."""
    text = "/".join(str(p) for p in parts)
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:4], "big")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=1, sort_keys=True)
        fh.write("\n")


def read_json(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def run(cmd, cwd: Path, log: Path | None = None, env=None, timeout: int = 3600) -> int:
    """Run a command, optionally saving combined stdout and stderr to a log file."""
    proc = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True,
                          errors="replace", timeout=timeout)
    if log is not None:
        write_text(log, (proc.stdout or "") + (proc.stderr or ""))
    return proc.returncode

