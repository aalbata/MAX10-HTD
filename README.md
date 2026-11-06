# MAX10-HTD

MAX10-HTD is a benchmark of FPGA implementations of public hardware Trojan designs. Every design was compiled with Quartus Prime for the Altera MAX 10 device 10M50DAF484C7G with one fixed flow, and each implementation is described by features measured from the Quartus reports, from the post-fit netlist and from the RTL source. Each Trojan-inserted implementation is linked to the implementation of its Trojan-free reference and was compared with it structurally and in simulation.

The hardware designs come from Trust-Hub, the GHOST benchmarks and the RISC-V and Web3 Trojan dataset; they are not redistributed here. `scripts/sources/fetch.py` downloads them from their original locations and checks every archive against `dataset/metadata/source_archives.csv`. The implementations, features, verification results, partitions and reference results are produced by this project. See `docs/provenance.md`.

## Contents

- 136 implementations: 108 Trojan-inserted and 28 Trojan-free, in 27 host groups and 7 functional families.
- 163 features in 7 groups (`docs/feature_dictionary.md`).
- Catalog of 380 designs, of which 167 compiled; every excluded design is listed with its reason in `dataset/metadata/exclusions.csv`.

| Source | Trojan-free | Trojan-inserted |
|---|---:|---:|
| GHOST | 2 | 13 |
| RISC-V and Web3 (Zenodo 11035341) | 21 | 83 |
| Trust-Hub chip-level RTL | 5 | 12 |

| Family | Trojan-free | Trojan-inserted |
|---|---:|---:|
| clocking | 1 | 0 |
| communication | 6 | 35 |
| cryptographic | 5 | 19 |
| debug | 1 | 0 |
| interconnect | 2 | 2 |
| memory | 3 | 5 |
| processor | 10 | 47 |

## Measurement conditions

- Device MAX 10 10M50DAF484C7G, Quartus Prime 25.1std.0 Lite Edition, fitter seed 1, configuration mode "single uncompressed image with memory initialization" so that HDL-initialized ROM and RAM can use M9K blocks.
- Every top-level port except the clock ports is a virtual pin, as for an IP core compiled in its own project; clock ports are device pins. Clocks: 20 ns; input-to-output paths: 20 ns maximum delay.
- Timing: slow 1200 mV 85 C model. `sta_fmax_mhz` is the unrestricted Fmax of the slowest clock; paths through virtual pins are Quartus estimates of the core delay.
- Power: Power Analyzer defaults (12.5 % toggle rate for input pins, vectorless estimation of internal nodes). Virtual input pins carry no switching activity, so dynamic power reflects the clock network, clocked registers and memories, and logic that switches without input activity (for example free-running counters). These are estimates, not measurements.
- Placement-dependent features (fitter, routing, timing, power) vary with the fitter seed; `experiments/results/seed_variance_*.csv` quantifies this for a subset compiled with seeds 1 to 3.

## Layout

| Path | Content |
|---|---|
| `dataset/features/features.csv` | one row per implementation, predictive features only |
| `dataset/labels/labels.csv` | `label` 1 = Trojan-inserted, 0 = Trojan-free |
| `dataset/metadata/samples.csv` | source, design, family, host group, reference, Trojan category, verification results (not for prediction) |
| `dataset/metadata/catalog.json` | every cataloged design with its files and top-level module |
| `dataset/metadata/verification.csv` | interface, structure and dormant-behavior comparison of each pair |
| `dataset/metadata/exclusions.csv`, `excluded_items.csv` | designs and archive items left out, with reasons |
| `dataset/splits/` | fixed partitions: grouped cross-validation and holdout keys |
| `dataset/checksums/SHA256SUMS` | digests of every released data file |
| `scripts/` | fetching, cataloging, Quartus automation, feature extraction, verification, assembly |
| `ml/` | classifiers, fixed hyperparameters and their sources, preprocessing, metrics, experiments |
| `experiments/` | saved predictions and result tables |
| `docs/` | dataset description, feature dictionary, verification, provenance, reproduction |

## Reference results

Grouped cross-validation (E1): five repetitions of five-fold cross-validation in which a host design and all its variants are always on the same side of the split. Values are the mean ± standard deviation over the repetitions of metrics computed on the pooled out-of-fold predictions. The positive class is Trojan-inserted; the threshold is 0.5 on predicted probabilities (0 on the SVM decision function).

| Model | Balanced accuracy | Recall | Specificity | Precision | ROC AUC | PR AUC (Trojan) | PR AUC (Trojan-free) |
|---|---|---|---|---|---|---|---|
| LR | 0.683 ± 0.043 | 0.730 ± 0.042 | 0.636 ± 0.085 | 0.886 ± 0.023 | 0.694 ± 0.019 | 0.862 ± 0.008 | 0.366 ± 0.021 |
| DT | 0.668 ± 0.039 | 0.822 ± 0.070 | 0.514 ± 0.125 | 0.869 ± 0.021 | 0.761 ± 0.035 | 0.914 ± 0.011 | 0.423 ± 0.085 |
| RF | 0.667 ± 0.023 | 0.741 ± 0.015 | 0.593 ± 0.041 | 0.875 ± 0.011 | 0.722 ± 0.040 | 0.914 ± 0.016 | 0.411 ± 0.053 |
| SVM | 0.625 ± 0.017 | 0.550 ± 0.025 | 0.700 ± 0.032 | 0.876 ± 0.011 | 0.665 ± 0.013 | 0.878 ± 0.010 | 0.415 ± 0.017 |
| KNN | 0.500 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 0.794 ± 0.000 | 0.713 ± 0.025 | 0.896 ± 0.014 | 0.392 ± 0.033 |
| XGB | 0.697 ± 0.020 | 0.807 ± 0.028 | 0.586 ± 0.032 | 0.883 ± 0.008 | 0.769 ± 0.025 | 0.930 ± 0.009 | 0.441 ± 0.049 |
| MLP | 0.639 ± 0.025 | 0.635 ± 0.028 | 0.643 ± 0.044 | 0.873 ± 0.014 | 0.642 ± 0.031 | 0.838 ± 0.015 | 0.387 ± 0.056 |
| ET | 0.679 ± 0.031 | 0.737 ± 0.038 | 0.621 ± 0.054 | 0.883 ± 0.015 | 0.754 ± 0.029 | 0.918 ± 0.014 | 0.515 ± 0.038 |
| AB | 0.685 ± 0.030 | 0.791 ± 0.068 | 0.579 ± 0.047 | 0.878 ± 0.010 | 0.727 ± 0.019 | 0.899 ± 0.009 | 0.431 ± 0.042 |
| GNB | 0.554 ± 0.034 | 0.722 ± 0.080 | 0.386 ± 0.069 | 0.819 ± 0.016 | 0.555 ± 0.049 | 0.816 ± 0.019 | 0.238 ± 0.026 |
| LightGBM | 0.694 ± 0.043 | 0.744 ± 0.042 | 0.643 ± 0.098 | 0.890 ± 0.024 | 0.759 ± 0.029 | 0.926 ± 0.008 | 0.447 ± 0.089 |
| Dummy | 0.500 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 0.794 ± 0.000 | 0.500 ± 0.000 | 0.794 ± 0.000 | 0.206 ± 0.000 |
| Size | 0.500 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 | 0.794 ± 0.000 | 0.385 ± 0.036 | 0.733 ± 0.017 | 0.196 ± 0.025 |

Column definitions: balanced accuracy is the mean of recall and specificity; recall is the fraction of Trojan-inserted designs predicted as Trojan-inserted; specificity is the fraction of Trojan-free designs predicted as Trojan-free; precision is the fraction of designs predicted as Trojan-inserted that are; ROC AUC is the area under the receiver operating characteristic curve; PR AUC (Trojan) is the average precision for the Trojan-inserted class and PR AUC (Trojan-free) the average precision for the Trojan-free class. Dummy predicts the majority class; Size is logistic regression on the logarithm of the number of logic elements.

## Reproduction

Fast path from the shipped tables (Python 3.12, CPU only):

```
pip install -r requirements.txt
python reproduce.py
```

Full path from the original archives, with Quartus Prime 25.1 Lite, the OSS CAD Suite (Yosys, Icarus Verilog) and 7-Zip: see `docs/reproduction.md`.

## License and citation

Code: MIT license (`LICENSE`). Data produced by this project (features, labels, metadata, partitions, results): CC BY 4.0 (`LICENSE-DATA`). Third-party designs keep their own terms and are not included. Citation metadata: `CITATION.cff`.
