# MAX10-HTD dataset description

## Sample unit

One row is one implementation: a design compiled with Quartus Prime 25.1 Lite for the MAX 10 device 10M50DAF484C7G with the fixed flow of `scripts/quartus/`. The label is the one given by the benchmark source (1 = Trojan-inserted, 0 = Trojan-free). Each Trojan-inserted implementation names the Trojan-free implementation of the same host in `clean_reference`.

## Size

- Implementations: 136 (108 Trojan-inserted, 28 Trojan-free); ratio 3.86 Trojan-inserted per Trojan-free implementation.
- Host groups: 27; functional families: 7.
- Features: 163 (netlist_structure 50, quartus_fitter 31, quartus_power 10, quartus_routing 7, quartus_synthesis 27, quartus_timing 17, rtl_structure 21).
- Catalog: 380 designs, 167 compiled (43.9%).

## Composition by source and family

| source | family | Trojan-free | Trojan-inserted |
|---|---|---|---|
| ghost | communication | 1 | 4 |
| ghost | cryptographic | 0 | 5 |
| ghost | memory | 1 | 4 |
| hayashi | clocking | 1 | 0 |
| hayashi | communication | 5 | 31 |
| hayashi | cryptographic | 3 | 8 |
| hayashi | debug | 1 | 0 |
| hayashi | interconnect | 1 | 0 |
| hayashi | memory | 1 | 0 |
| hayashi | processor | 9 | 44 |
| trusthub | cryptographic | 2 | 6 |
| trusthub | interconnect | 1 | 2 |
| trusthub | memory | 1 | 1 |
| trusthub | processor | 1 | 3 |

## Trojan categories reported by the sources

Payload (effect) categories of the Trojan-inserted implementations; one implementation can carry several. The RISC-V and Web3 release does not report categories per file.

| payload | implementations |
|---|---|
| change-functionality | 13 |
| change-functionality;denial-of-service | 2 |
| degrade-performance;denial-of-service | 1 |
| denial-of-service | 6 |
| leak-information | 3 |
| not-reported | 83 |

Trigger categories:

| trigger | implementations |
|---|---|
| not-reported | 83 |
| triggered-externally | 5 |
| triggered-internally | 20 |

## Missing values

58 features have missing values; 3.77% of all cells are missing. A missing value means that the quantity is undefined for the design (for example, no register-to-register path, or a combinational cycle for the logic depth), that the RTL features could not be computed (VHDL sources) or that the Quartus report does not give the value; `docs/feature_dictionary.md` lists the case for each feature. Per-feature fractions: `experiments/results/audit_missingness.csv`.

## Duplicates

- Identical feature rows: 7 rows in 3 sets; 0 sets mix labels and 0 span host groups.
- Near-duplicate Trojan-free designs merged into one host group: 1 pairs (`dataset/metadata/near_duplicates.csv`).

