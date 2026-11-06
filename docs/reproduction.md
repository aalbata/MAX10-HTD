# Reproduction

## Fast path (released tables, CPU only)

Python 3.12 with the packages of `requirements.txt`:

```
pip install -r requirements.txt
python reproduce.py
```

This reruns the audit, all experiments (about one hour on the laptop processor listed below), the summaries, the seed analysis, the figures and the README from `dataset/`. `python reproduce.py --experiments E1` runs one experiment.

## Full path (from the original archives)

Tools: Quartus Prime 25.1std Lite with MAX 10 device support (set `QUARTUS_ROOTDIR` to its `quartus` folder), the YosysHQ OSS CAD Suite for Yosys and Icarus Verilog (set `OSS_CAD_SUITE`), and 7-Zip (set `SEVEN_ZIP` or put `7z` on PATH). `MAX10HTD_BUILD` selects the scratch folder (default `build/`).

```
python reproduce.py --full
```

Steps: download and digest check of the archives (`scripts.sources.fetch`), catalog (`scripts.sources.catalog`), two-pass Quartus compilation (`scripts.quartus.compile`), pair verification (`scripts.verification.dormant`), feature extraction (`scripts.feature_extraction.build_features`), assembly (`scripts.validation.assemble`), the seed study compilations, then the fast path. Compiling all designs takes several hours; the flow time of every design is listed in `dataset/metadata/compilation.csv`.

## Environment of the released results

Windows 11 Enterprise, Intel Core Ultra 7 155U (12 cores, 14 threads), Python 3.12.10, Quartus Prime 25.1std.0 Build 1129 Lite Edition, Yosys 0.70+309 and Icarus Verilog 14.0 (development snapshot s20260301) from the OSS CAD Suite of 2026-11-03, 7-Zip 26.02.

