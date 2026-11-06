"""Reproduce the MAX10-HTD results.

Fast path (default, CPU only, Python packages of requirements.txt): from the
released tables in dataset/, rerun the dataset audit, the experiments, the
result summaries, the seed-variance analysis, the figures and the README.

    python reproduce.py
    python reproduce.py --experiments E1,E2      # a subset of the experiments

Full path: rebuild the released tables from the original archives first.  It
needs Quartus Prime 25.1 Lite (QUARTUS_ROOTDIR), the OSS CAD Suite with Yosys
and Icarus Verilog (OSS_CAD_SUITE), 7-Zip (SEVEN_ZIP or on PATH) and several
hours of compilation.

    python reproduce.py --full
"""
from __future__ import annotations

import argparse
import subprocess
import sys

from scripts.common import config

PY = sys.executable


def step(args: list[str]) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--experiments", default="E1,E2,E3,E4,E5,E6,C1")
    ap.add_argument("--jobs", default="4")
    args = ap.parse_args()
    if args.full:
        step([PY, "-m", "scripts.sources.fetch"])
        step([PY, "-m", "scripts.sources.catalog"])
        step([PY, "-m", "scripts.quartus.compile", "--jobs", args.jobs])
        step([PY, "-m", "scripts.verification.dormant", "--jobs", args.jobs])
        step([PY, "-m", "scripts.feature_extraction.build_features", "--jobs", args.jobs])
        step([PY, "-m", "scripts.validation.assemble"])
        ids = open("dataset/metadata/seed_study.csv", encoding="utf-8").read().split()[1:]
        for seed in ("2", "3"):
            step([PY, "-m", "scripts.quartus.compile", "--seed", seed, "--jobs", args.jobs, "--only", ",".join(ids)])
            step([PY, "-m", "scripts.feature_extraction.build_features", "--compiled",
                  str(config.BUILD / f"compiled_seed{seed}"), "--only", ",".join(ids), "--out",
                  f"dataset/features/seed_study/features_seed{seed}.csv"])
    step([PY, "-m", "scripts.validation.audit"])
    step([PY, "-m", "ml.training.run_experiments", "--experiments", args.experiments])
    step([PY, "-m", "scripts.analysis.summarize"])
    step([PY, "-m", "scripts.analysis.seed_variance", "analyze"])
    step([PY, "-m", "scripts.analysis.figures"])
    step([PY, "-m", "scripts.analysis.readme"])


if __name__ == "__main__":
    main()
