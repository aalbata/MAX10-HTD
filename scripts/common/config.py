"""Paths, tool locations and fixed implementation settings for MAX10-HTD.

Tool locations are read from environment variables so that the scripts run on
any machine with the same tools installed:

QUARTUS_ROOTDIR   Quartus Prime installation (set by the Quartus installer),
                  for example C:/altera_lite/25.1std/quartus
OSS_CAD_SUITE     root of a YosysHQ OSS CAD Suite installation that provides
                  Icarus Verilog and Yosys (optional if both are on PATH)
MAX10HTD_BUILD    scratch directory for downloads, simulation and compilation
                  runs (default: <repository>/build)
SEVEN_ZIP         7-Zip executable for unpacking benchmark archives
                  (optional if 7z is on PATH)
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BUILD = Path(os.environ.get("MAX10HTD_BUILD", REPO / "build"))

RTL_DIR = REPO / "rtl"
DATASET_DIR = REPO / "dataset"
METADATA_DIR = DATASET_DIR / "metadata"

# Target device and implementation settings shared by every design.
FAMILY = "MAX 10"
DEVICE = "10M50DAF484C7G"
CONFIGURATION_MODE = "SINGLE IMAGE WITH ERAM"   # single uncompressed image with memory initialization
CLOCK_PERIOD_NS = 20.0          # 50 MHz, the board oscillator frequency
COMB_MAX_DELAY_NS = 20.0        # input-to-output budget for combinational designs
FITTER_SEED = 1
GENERATOR_SEED = 20261104       # master seed of the dataset generator

# Simulation timing (picoseconds within one 20 ns cycle).
SIM_PERIOD_PS = 20000
SIM_APPLY_PS = 2000             # inputs change 2 ns after the rising edge
SIM_SAMPLE_PS = 18000           # outputs are sampled 2 ns before the next edge


def quartus_bin() -> Path:
    root = os.environ.get("QUARTUS_ROOTDIR")
    if not root:
        raise RuntimeError("QUARTUS_ROOTDIR is not set; point it at the Quartus 'quartus' folder")
    return Path(root) / "bin64"


def quartus_simlib() -> Path:
    root = os.environ.get("QUARTUS_ROOTDIR")
    if not root:
        raise RuntimeError("QUARTUS_ROOTDIR is not set")
    return Path(root) / "eda" / "sim_lib"


def oss_env() -> dict:
    """Environment for running Icarus Verilog and Yosys from the OSS CAD Suite."""
    env = dict(os.environ)
    suite = os.environ.get("OSS_CAD_SUITE")
    if suite:
        extra = os.pathsep.join([str(Path(suite) / "bin"), str(Path(suite) / "lib")])
        env["PATH"] = extra + os.pathsep + env.get("PATH", "")
    return env


def archiver() -> str:
    """7-Zip executable used to unpack ZIP and RAR benchmark archives (env SEVEN_ZIP or PATH)."""
    found = os.environ.get("SEVEN_ZIP") or shutil.which("7z") or shutil.which("7za")
    if not found:
        raise RuntimeError("7-Zip not found; set SEVEN_ZIP or add 7z to PATH")
    return found


def tool(name: str) -> str:
    """Absolute path of an OSS CAD Suite tool (iverilog, vvp, yosys)."""
    suite = os.environ.get("OSS_CAD_SUITE")
    if suite:
        cand = Path(suite) / "bin" / (name + ".exe")
        if cand.exists():
            return str(cand)
        cand = Path(suite) / "bin" / name
        if cand.exists():
            return str(cand)
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"{name} not found; set OSS_CAD_SUITE or add it to PATH")
    return found
