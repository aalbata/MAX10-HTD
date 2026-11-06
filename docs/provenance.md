# Provenance of the MAX10-HTD designs

MAX10-HTD does not redistribute third-party hardware designs. Every design is downloaded from its original location by `python -m scripts.sources.fetch`, which checks the size and SHA-256 digest of each downloaded file against `dataset/metadata/source_archives.csv`. The features, labels and metadata in `dataset/` are measurements and annotations produced by this project.

## Sources

### Trust-Hub chip-level Trojan benchmarks

- Location: <https://trust-hub.org/#/benchmarks/chip-level-trojan>
- Reference: H. Salmani, M. Tehranipoor and R. Karri, ICCD 2013, doi:10.1109/ICCD.2013.6657085; B. Shakya et al., J. Hardw. Syst. Secur. 1(1), 2017, doi:10.1007/s41635-017-0001-6
- License: no license stated; copyright Trust-Hub; not redistributed
- Archives: 92 and the benchmark index benchmarks-trojan-chip.json (25,827,008 bytes), retrieved 2026-11-04
- Catalog designs: 8 Trojan-free and 58 Trojan-inserted (identical copies counted once)

### TRIT-TC and TRIT-TS (Trust-Hub)

- Location: <https://trust-hub.org/#/benchmarks/chip-level-trojan>
- Reference: J. Cruz, Y. Huang, P. Mishra and S. Bhunia, DATE 2018, doi:10.23919/DATE.2018.8342270
- License: no license stated; copyright Trust-Hub; not redistributed
- Archives: 2 (28,222,277 bytes), retrieved 2026-11-04
- Catalog designs: none (gate-level netlists for ASIC cell libraries; see the items not in the catalog)

### GHOST hardware Trojan benchmarks

- Location: <https://github.com/NMSU-PEARL/GHOST_benchmarks>
- Reference: M. O. Faruque, P. Jamieson, A. Patooghy and A.-H. A. Badawy, Electronics 14(23):4745, 2025, doi:10.3390/electronics14234745
- License: BSD-3-Clause (original work); upstream hosts Apache-2.0, MIT or BSD-3-Clause
- Archives: 1 (3,425,332 bytes), retrieved 2026-11-04
- Catalog designs: 3 Trojan-free and 14 Trojan-inserted (identical copies counted once)

### Hardware Trojan dataset of RISC-V and Web3

- Location: <https://doi.org/10.5281/zenodo.11035341>
- Reference: V. T. Hayashi and W. V. Ruggiero, Data 9(6):82, 2024, doi:10.3390/data9060082
- License: CC-BY-4.0
- Archives: 3 (349,459 bytes), retrieved 2026-11-04
- Catalog designs: 27 Trojan-free and 270 Trojan-inserted (identical copies counted once)

## What was changed in the third-party sources

- Files are copied without edits, except that absolute `include` paths are replaced by the file name of the included file, which is copied next to the design.
- GHOST: the annotated Trojan-inserted files (`*_A1.v`) are used, because comments do not affect synthesis and some comment-free copies (`*_cleaned.v`) fail to parse with Icarus Verilog although their annotated versions parse. The design unit is the module that received the Trojan.
- RISC-V and Web3: each Trojan-inserted module file is compiled with the unmodified golden files of the modules it instantiates.

## Pairing of Trojan-inserted and Trojan-free designs

Trust-Hub and GHOST distribute each Trojan-inserted design together with the Trojan-free version of its host. In the RISC-V and Web3 release, a Trojan-inserted file is paired with the golden module whose identifiers it shares most (Jaccard similarity, without comments, keywords and compiler directives). This is the module named in the file name except for the files below, which are modified versions of another golden module.

| Sample | File | Named host | Paired with |
|---|---|---|---|
| S0009 | MINER/virtual_wire_T0.v | virtual_wire | uart_tx_fifo |
| S0043 | MINER/virtual_wire_T7.v | virtual_wire | uart_tx_fifo |
| S0105 | MINER/virtual_wire_T1.v | virtual_wire | uart_tx_fifo |
| S0107 | MINER/virtual_wire_T9.v | virtual_wire | uart_tx_fifo |
| S0130 | MINER/virtual_wire_T5.v | virtual_wire | uart_tx_fifo |
| S0145 | MINER/virtual_wire_T6.v | virtual_wire | uart_tx_fifo |
| S0202 | MINER/virtual_wire_T2.v | virtual_wire | uart_tx_fifo |
| S0325 | MINER/virtual_wire_T8.v | virtual_wire | uart_tx_fifo |
| S0351 | MINER/virtual_wire_T4.v | virtual_wire | uart_tx_fifo |

## Items not in the catalog

| Source | Item | Reason |
|---|---|---|
| ghost | gpt-4/aes_128/X/Xaes_128_HT4_gpt-4_A1.v | listed by GHOST as a failed generation attempt |
| ghost | gpt-4/aes_128/X/Xaes_128_HT4_gpt-4_A1_tb.v | listed by GHOST as a failed generation attempt |
| ghost | gpt-4/sram/X/Xsram_HT4_gpt-4_A1.v | listed by GHOST as a failed generation attempt |
| ghost | gpt-4/sram/X/sram_HT4_gpt-4_A1_tb.v | listed by GHOST as a failed generation attempt |
| ghost | gpt-4/uart/X/Xuart_rx_HT3_gpt-4_A1.v | listed by GHOST as a failed generation attempt |
| ghost | gpt-4/uart/X/Xuart_rx_HT3_gpt-4_A1_tb.v | listed by GHOST as a failed generation attempt |
| ghost | gpt-4/uart/X/Xuart_rx_HT4_gpt-4_A1.v | listed by GHOST as a failed generation attempt |
| ghost | gpt-4/uart/X/uart_rx_HT4_gpt-4_A1_tb.v | listed by GHOST as a failed generation attempt |
| ghost | llama3-70b-8192/sram/X/sram_HT1_llama3-70b-8192_A1.v | listed by GHOST as a failed generation attempt |
| ghost | llama3-70b-8192/sram/X/sram_HT1_llama3-70b-8192_A1_tb.v | listed by GHOST as a failed generation attempt |
| ghost | llama3-70b-8192/sram/X/sram_HT2_llama3-70b-8192_A1.v | listed by GHOST as a failed generation attempt |
| ghost | llama3-70b-8192/sram/X/sram_HT2_llama3-70b-8192_A1_tb.v | listed by GHOST as a failed generation attempt |
| ghost | llama3-70b-8192/sram/X/sram_HT4_llama3-70b-8192_A1.v | listed by GHOST as a failed generation attempt |
| ghost | llama3-70b-8192/sram/X/sram_HT4_llama3-70b-8192_A1_tb.v | listed by GHOST as a failed generation attempt |
| ghost | models_gemini-1.5-pro-latest/aes_128/X/aes_128_HT1_models_gemini-1.5-pro-latest_A1.v | listed by GHOST as a failed generation attempt |
| ghost | models_gemini-1.5-pro-latest/aes_128/X/aes_128_HT1_models_gemini-1.5-pro-latest_A1_tb.v | listed by GHOST as a failed generation attempt |
| ghost | models_gemini-1.5-pro-latest/aes_128/X/aes_128_HT4_models_gemini-1.5-pro-latest_A1.v | listed by GHOST as a failed generation attempt |
| ghost | models_gemini-1.5-pro-latest/aes_128/X/aes_128_HT4_models_gemini-1.5-pro-latest_A1_tb.v | listed by GHOST as a failed generation attempt |
| ghost | models_gemini-1.5-pro-latest/sram/X/sram_HT1_models_gemini-1.5-pro-latest_A1.v | listed by GHOST as a failed generation attempt |
| ghost | models_gemini-1.5-pro-latest/sram/X/sram_HT1_models_gemini-1.5-pro-latest_A1_tb.v | listed by GHOST as a failed generation attempt |
| ghost | models_gemini-1.5-pro-latest/sram/X/sram_HT2_models_gemini-1.5-pro-latest_A1.v | listed by GHOST as a failed generation attempt |
| ghost | models_gemini-1.5-pro-latest/sram/X/sram_HT2_models_gemini-1.5-pro-latest_A1_tb.v | listed by GHOST as a failed generation attempt |
| ghost | models_gemini-1.5-pro-latest/sram/X/sram_HT4_models_gemini-1.5-pro-latest_A1.v | listed by GHOST as a failed generation attempt |
| ghost | models_gemini-1.5-pro-latest/sram/X/sram_HT4_models_gemini-1.5-pro-latest_A1_tb.v | listed by GHOST as a failed generation attempt |
| ghost | models_gemini-1.5-pro-latest/uart/X/uart_rx_HT2_models_gemini-1.5-pro-latest_A1.v | listed by GHOST as a failed generation attempt |
| ghost | models_gemini-1.5-pro-latest/uart/X/uart_rx_HT2_models_gemini-1.5-pro-latest_A1_tb.v | listed by GHOST as a failed generation attempt |
| ghost | models_gemini-1.5-pro-latest/uart/X/uart_rx_HT4_models_gemini-1.5-pro-latest_A1.v | listed by GHOST as a failed generation attempt |
| ghost | models_gemini-1.5-pro-latest/uart/X/uart_rx_HT4_models_gemini-1.5-pro-latest_A1_tb.v | listed by GHOST as a failed generation attempt |
| trusthub | AES-T2200 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | B15-T100 | layout-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | B15-T200 | layout-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | B15-T300 | layout-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | B15-T400 | layout-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | B19-T100 | distributed as a multi-part archive of ASIC layout or gate-level databases; not downloaded |
| trusthub | B19-T200 | distributed as a multi-part archive of ASIC layout or gate-level databases; not downloaded |
| trusthub | BasicRSA-T100 | archive contains no Trojan-free version of the design |
| trusthub | BasicRSA-T200 | archive contains no Trojan-free version of the design |
| trusthub | BasicRSA-T300 | archive contains no Trojan-free version of the design |
| trusthub | BasicRSA-T400 | archive contains no Trojan-free version of the design |
| trusthub | EthernetMAC10GE-T100 | distributed as a multi-part archive of ASIC layout or gate-level databases; not downloaded |
| trusthub | EthernetMAC10GE-T200 | distributed as a multi-part archive of ASIC layout or gate-level databases; not downloaded |
| trusthub | EthernetMAC10GE-T300 | distributed as a multi-part archive of ASIC layout or gate-level databases; not downloaded |
| trusthub | EthernetMAC10GE-T400 | distributed as a multi-part archive of ASIC layout or gate-level databases; not downloaded |
| trusthub | EthernetMAC10GE-T500 | distributed as a multi-part archive of ASIC layout or gate-level databases; not downloaded |
| trusthub | EthernetMAC10GE-T600 | distributed as a multi-part archive of ASIC layout or gate-level databases; not downloaded |
| trusthub | EthernetMAC10GE-T700 | distributed as a multi-part archive of ASIC layout or gate-level databases; not downloaded |
| trusthub | EthernetMAC10GE-T710 | distributed as a multi-part archive of ASIC layout or gate-level databases; not downloaded |
| trusthub | EthernetMAC10GE-T720 | distributed as a multi-part archive of ASIC layout or gate-level databases; not downloaded |
| trusthub | EthernetMAC10GE-T730 | distributed as a multi-part archive of ASIC layout or gate-level databases; not downloaded |
| trusthub | MultPyramid-T100 | layout-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | MultPyramid-T200 | layout-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | RS232-T1000 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | RS232-T1100 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | RS232-T1200 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | RS232-T1300 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | RS232-T1400 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | RS232-T1500 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | RS232-T1600 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | RS232-T1700 | layout-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | RS232-T1800 | layout-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | RS232-T1900 | layout-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | RS232-T2000 | layout-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | TRIT-TC | gate-level netlists mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | TRIT-TS | gate-level netlists mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | s15850-T100 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | s35932-T100 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | s35932-T200 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | s35932-T300 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | s38417-T100 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | s38417-T200 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | s38417-T300 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | s38584-T100 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | s38584-T200 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | s38584-T300 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | vga_lcd-T100 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |
| trusthub | wb_conmax-T100 | gate-level netlist mapped to an ASIC standard-cell library whose simulation models are not distributed with the benchmark |

## Archive manifest

| Source | Archive | Bytes | SHA-256 |
|---|---|---|---|
| ghost | GHOST_benchmarks-078cec60f163.zip | 3,425,332 | `d9b020674f8a3997cf719ebc80d827afc1e10e2cae04a0cfac1696c9b9d18b04` |
| hayashi | MINER_benchmarks_Verilog.zip | 142,356 | `5af80142cbf26ce7df5102ace85af6ccd0d5bf2bf807831745cd42dd4d1f1b98` |
| hayashi | RISCV_benchmarks_Verilog.zip | 147,690 | `f6db6fe4fae492cb55665e8668e8f88bae2639b3784d631963b51ff4a902b5f6` |
| hayashi | WALLET_benchmarks_Verilog.zip | 59,413 | `f24a0ba6cbfe4a2408cc77922aa6f304820dbe5de5b1a2f9cbca6f8ffab42a06` |
| trit | TRIT-TC.zip | 14,504,224 | `7c858e7f409beed8c5d44096dd5b8591feb78cb5e4215ea5ab9b82ee3445074c` |
| trit | TRIT-TS.zip | 13,718,053 | `1367027867d8861bc9e20af62a89f2bf54d64f80ebe058a5ec07930a45cc3408` |
| trusthub | AES-T100.zip | 78,935 | `a1df16f8da6deab0ea0611a7c5fdd8d1fd6da0f90c0197eb68c64a09af868caf` |
| trusthub | AES-T1000.zip | 79,895 | `79d287ebc2b4e36364f4df0b781052ba10bca7f2ccdb434cb4e3a4c418e82beb` |
| trusthub | AES-T1100.zip | 80,034 | `1e36e864d2ff2b198d53daefdd4bb5e4a43439b41f82879f4160c72a5d221503` |
| trusthub | AES-T1200.zip | 80,195 | `bb101fb9eaa45c6d2ec67ef0349aa0e1bc29b9ba238a6ec5406766f72da1166e` |
| trusthub | AES-T1300.zip | 80,151 | `41acc514dd04f75e09b019056fff74197d3cd27e675453ac6edf394b14d6b832` |
| trusthub | AES-T1400.zip | 80,213 | `82a18773e171c18532f3211ba212ebce8f3b4885804e6e40c35e117a4bd96c9a` |
| trusthub | AES-T1500.zip | 79,803 | `2b1ae1ad175b1b6423a9a34b4d594aa5cea6b6637f92dd0b7d19af9ea2f80021` |
| trusthub | AES-T1600.zip | 81,726 | `0d2690775f6eae18f84454ef1845253e26adeba0e6be7241d54ba7a756d21aee` |
| trusthub | AES-T1700.zip | 82,198 | `d234889a6321f008676fe999ecab9bc3dbee31f538168f106781feeafe588bcf` |
| trusthub | AES-T1800.zip | 79,949 | `5ec9d26872a7d1f2583db993fb9350c26fb3f7d26d1e7265b7546e91c4b997b1` |
| trusthub | AES-T1900.zip | 79,030 | `946e89729a6a3a0cbdcdd2721a3163b93aaba3274f49e40cf04a1563599ef6c2` |
| trusthub | AES-T200.zip | 79,171 | `54d049d5ea25858409ac89a175845bd358b565a59821e86752ff35eb0e31e9c1` |
| trusthub | AES-T2000.zip | 78,766 | `f52ef26dcd356ba148f14d6b171299ab313238f291273c0207d610aac73cd72f` |
| trusthub | AES-T2100.zip | 78,913 | `da82c0d351a47a8d50d2606ea1b08cfc02fb6bf002b9e06c181829759211dbe4` |
| trusthub | AES-T2200.zip | 3,452,574 | `4b6b5b014c953718706d02cc4a3063b34083a620fd310c53443417d44486874d` |
| trusthub | AES-T2300.zip | 19,146 | `128398a360172d597f16da70986f6270e3d96a32ae277a616d1b412f9fa6d61c` |
| trusthub | AES-T2400.zip | 19,161 | `1b493b5927180781f9c8a0c1d4f640d3fa656e100d040e7da29b6100081470d2` |
| trusthub | AES-T2500.zip | 19,233 | `56cfd69e1200bca16a768a53a976a2be92099a377acb096b9994a22904d4b640` |
| trusthub | AES-T2600.zip | 19,356 | `3f11731a2e4258ce202554881e7e7811877862e3f70faa387bf3a58512ddf4a8` |
| trusthub | AES-T2700.zip | 19,421 | `a8f1cac0554a753d08c4e34fccf25c9bdeba20592328f9b081a2881e22a1268a` |
| trusthub | AES-T2800.zip | 19,561 | `b9bb94e2118fd3a9a6432083ce12311a5388bc87457a589d1f32ec86003e6b8c` |
| trusthub | AES-T300.zip | 78,160 | `2b90831df665e994b5b68b361bf14911a779fe031ea09fde0061ff3c69bd7f23` |
| trusthub | AES-T400.zip | 80,239 | `d3c9f71755b775d54001558eb7e2ca3b5506e34d3ce5a20fcbf267558e1c8cab` |
| trusthub | AES-T500.zip | 78,838 | `011056cacb658ffb62e773c5a31d603a06908561205092908e5154304fe46f42` |
| trusthub | AES-T600.zip | 77,903 | `b0205aa3ba48038fdb17b19b5fb11b7d82af26cde70cf877d4686f05640eab48` |
| trusthub | AES-T700.zip | 79,836 | `a8ae2606ce74077eaeadfd89ebdd282e182b34b0c6eee4daf6b26d356b0967c4` |
| trusthub | AES-T800.zip | 79,464 | `5317bbb5b8d8b2447558d8623c7b9837dad2d899f911f5c3f8329faf1f61c16c` |
| trusthub | AES-T900.zip | 79,588 | `aa92ef0a919ac5f57b7f4435bc3f05d08a5502ac63e05f7d6d1a97c0071314e9` |
| trusthub | BasicRSA-T100.rar | 67,451 | `a270ea279bec95698d95987aeee9cf0ab193ba527d899c831cf339a33631f57d` |
| trusthub | BasicRSA-T200.rar | 65,710 | `872601b330323d1fd08b984c9c276065c5956457f5c088804c8a51599ea22b52` |
| trusthub | BasicRSA-T300.rar | 70,732 | `be3603f94a2db1b30cd53733369697ce9f26e87af3c326ab12a1adce871c09ce` |
| trusthub | BasicRSA-T400.rar | 70,267 | `44d8b49fefdd94e1f183ab6ccdd06ca88d52c425c2b7b4865b9fff5241189055` |
| trusthub | MC8051-T200.rar | 551,341 | `05a0182927744232ff30cf055893e92cecd4427e350ae3dd1cd10397115efcd5` |
| trusthub | MC8051-T300.rar | 564,253 | `5d4484d5210d007ec8b4e15cc9e1772d1f625cf4eb37ed560042d60d0b1ad492` |
| trusthub | MC8051-T400.rar | 509,585 | `a2d03f4124dbda095b9f0b9dfdd3aeb303d94048b3c9f95c06b36affc919760e` |
| trusthub | MC8051-T500.rar | 467,277 | `a06dba0f86f68ad9f1313b05ca8f22b06b79cd69022c727ed6d0bb5461cf3cdc` |
| trusthub | MC8051-T600.rar | 543,056 | `110b5b63354ef0fc1be07a3ff456cf17e2c736bf000b60de69b584c995f2471d` |
| trusthub | MC8051-T700.rar | 571,366 | `0fb02de057d6776a6d48ef978e2c877a74493d85fe0ea2fe7cdf434c82e46f2e` |
| trusthub | MC8051-T800.rar | 636,820 | `063eb2a57ffa8f1c70b778ee2b4924318a57796ca1bfcf5cec7707a5eaf61dfc` |
| trusthub | MultPyramid-T100.rar | 263,440 | `80d690e381998c7c5c4b07c817f1df2afa27cd48020eac218cba5f5dbe280c18` |
| trusthub | MultPyramid-T200.rar | 263,440 | `96f9782ffb8a1b220490388dbb6ca18e462589038ec2b8d54bfa5283dfcbb0d3` |
| trusthub | PIC16F84-T100.rar | 92,344 | `a5898490092c7362ce61326289cfd70598c85b7dc0ac84d638487e847e1bb122` |
| trusthub | PIC16F84-T200.rar | 93,090 | `d9c7bdb880fb14e326445f71e50db5ace7debb693aedd02c5821b9eaedf82685` |
| trusthub | PIC16F84-T300.rar | 93,894 | `e63ff51c2c3adb28893a7b81cd54b843c7f843ff964cfa09707086e75da4cfeb` |
| trusthub | PIC16F84-T400.rar | 93,828 | `b2f5398183689a6540870ea1b1e1431cdb9751e54e75b61380aef439d173d256` |
| trusthub | RS232-T100.zip | 60,243 | `136df3ac02e5b612734b406897e32c4d14ab8b7f36cfda7a766bb02905f12915` |
| trusthub | RS232-T1000.zip | 108,593 | `4da6721fc7eb3b04f26ff5a8ec82464387c6fe663bd6815c0d48bf3480927eb2` |
| trusthub | RS232-T1100.zip | 109,682 | `59ecbf4e8cd2ce9bbc91753cb96d58a0684b16df1418745220eff81e76170c6b` |
| trusthub | RS232-T1200.zip | 109,402 | `44616ab4b775a4427b5bb408d21dbf87765d78e4fcfd8d2724d518ee27db46e5` |
| trusthub | RS232-T1300.zip | 108,246 | `d9f5da8f25006c65c8b535d004ce256f2ea688b3ab9806f4021b104ed7209b0d` |
| trusthub | RS232-T1400.zip | 109,779 | `bab8048c114195b65474b3fb81160b28c2c315042f3e02867377a1a6d8cbb9b9` |
| trusthub | RS232-T1500.zip | 110,554 | `2dd50914736e063af22942fed9d5ac3b2de0bc69e08a20d2977f76aea680fd96` |
| trusthub | RS232-T1600.zip | 110,150 | `f4a6ad248ab0cb63eef2a9d0f9aa2fea592afe012ffc2896d273fc759155f35a` |
| trusthub | RS232-T1700.zip | 141,803 | `683039829e288e9286262f9c738627acb6a20ded4db5368c130e0c735661965d` |
| trusthub | RS232-T1800.zip | 138,965 | `51130222cbcd7b7f5d2a9eceb780b9a138944051da791c423e5f532071c5a135` |
| trusthub | RS232-T1900.zip | 143,153 | `f420252b0a7f63b9a7511e37f30259cfde4075a49df496c30084fbe5d61d800d` |
| trusthub | RS232-T200.zip | 60,712 | `b71ad77944b4f4e7df929c5611272a868497b505cadd672baf6af2292085daf4` |
| trusthub | RS232-T2000.zip | 143,229 | `da743271a176930e595598bc9479d7e00270707003d7eea6e5799d2dcbda40f7` |
| trusthub | RS232-T2100.zip | 9,793 | `df09e8000967c9916e1ab4f208313e24acee0865487add8ffa5da3edadb38705` |
| trusthub | RS232-T2200.zip | 9,795 | `220c56a77f3cc7d93e7728c1295af9cd27ab62f2e8f11da40c7c65bbda35f1fa` |
| trusthub | RS232-T2300.zip | 9,816 | `522d40aa0b0ab077dd4e56199e0a8f15f04818e5f19f8ffdd0ee0cb831b66ecf` |
| trusthub | RS232-T2400.zip | 9,882 | `5239d6197585197a366059125a06ee5f33f8782ee07e5b528830fa2d858aaa9c` |
| trusthub | RS232-T300.zip | 61,387 | `3f86d5d22b2779369ddb75bb4c53ad4aa4c2779d5f6e237e34979f75d245ece2` |
| trusthub | RS232-T400.zip | 60,998 | `27ff92bcb4ff23dcdb718f76a94d52de0e6f61274b5132d7d13ae91894cfe96d` |
| trusthub | RS232-T500.zip | 61,745 | `bd33ac68bab69d98841fe934f64a87231f8c9410455bd5bfb88e77563f61f35f` |
| trusthub | RS232-T600.zip | 61,842 | `05f3e87903e00e402ddf106cef687018ae89cb5b2375c786422e71124937c310` |
| trusthub | RS232-T700.zip | 62,118 | `e6ce5b5c08c697f48b2178bab3d87258c577ba68830a97db78e9a9a959cb2dd5` |
| trusthub | RS232-T800.zip | 61,823 | `024049efdde3d987598f899b5531efdebdfe2c2d2b1bf663ee7000742e6f44e2` |
| trusthub | RS232-T900.zip | 62,017 | `e0ed112cc4c0c63202517ba1088e898a9b9da9ace311377851a81f2057fb3a17` |
| trusthub | RS232-T901.zip | 62,144 | `4d66d0d4a5dabb427d4c1e05d93682f07a2a080577cbec483ed5c1e91c8ef83d` |
| trusthub | b15-T100.zip | 2,038,290 | `719f849b46f50ee3e2d5adac460448d81f7b21b671a0e1931aac0da896102ef6` |
| trusthub | b15-T200.zip | 2,039,343 | `79e6d61bdd7a3d49ecb2ce8bbd58693ea3307b88aeb79a2ab422f7bf74533a76` |
| trusthub | b15-T300.zip | 1,857,552 | `8f1ef4d7404718cb085cb88d8f9c7eb02ea6fac2a16fd80258affc4616deff38` |
| trusthub | b15-T400.zip | 2,037,638 | `86bf2ed42399950264eb84493a01c9a12ebff2c6b30b5693e5d4e3202bd28299` |
| trusthub | b19-T300.rar | 68,307 | `c36d617c32d2bcd6c4bac7a9a5a5cdca89f0d6c72593f6e27b37ac45a4e26814` |
| trusthub | b19-T400.rar | 68,572 | `009069327c7c2fe93b9d9333ea30c2c6cde5ecfb2ecb19127bf4b06a38fc79d0` |
| trusthub | b19-T500.rar | 67,858 | `0be545a6fcdfd4bfef5fc157dc54f239c624eba13329ddf11b2d3470b3327ca2` |
| trusthub | benchmarks-trojan-chip.json | 120,303 | `b882bccd99220c820fd647ee590e512eb35eabed813c6b21696a34709483558c` |
| trusthub | memctrl-T100.zip | 876,083 | `fc8282b11defed0c8f8668b15084b7992394813d2a05189c69575d6ed2a722d6` |
| trusthub | s15850-T100.rar | 132,172 | `cb035f3f0d13d4186537d92eaedd82a5258493009060f5fe873581ab8ddb4dfd` |
| trusthub | s35932-T100.rar | 177,699 | `a15607a5c493f2dd6c7a164c22a3b06aa77b2624a98ca54c8519df22cf4ffcd7` |
| trusthub | s35932-T200.rar | 176,950 | `ba25d9a2a7eeb175b2ec6dda91f600a54bdcb746d821c947c750ac62a822b384` |
| trusthub | s35932-T300.rar | 178,770 | `7891a5495d0d450d053468dd32b24db5578bb9e3e460165e709a991c57b980d1` |
| trusthub | s38417-T100.rar | 219,484 | `0808df39ec78669b9a3c410a235757eabf011163628ff6efa4c30854b92eccf9` |
| trusthub | s38417-T200.rar | 219,596 | `a8ac9ad25045bfe1629349d4bb9789d52de13643d01f50142765a140711932c3` |
| trusthub | s38417-T300.rar | 218,753 | `124b29eccc57595c1a42c3a1a65b0c155a9a4ee4a7a9cbd9a91902637ba89d96` |
| trusthub | s38584-T100.rar | 268,562 | `7354aae09403d6feae731a2bd7689b81d14438599a6269423955c5af3335d7da` |
| trusthub | s38584-T200.rar | 269,734 | `3f1effab305b6979d83f28767579c7725318e68022e6195699355db91f0bd658` |
| trusthub | s38584-T300.rar | 275,321 | `a94dcbabe2c52747ddefc906c5a07f941b580171a93b97d1986097eb17b07617` |
| trusthub | vga_lcd-T100.zip | 1,462,966 | `65416c8b0a6ef32c0b89384088a6f27546be40787a5868dbc6cde5dab31bf384` |
| trusthub | wb_conmax-T100.rar | 572,737 | `07e65dc8623e0cc0d678c3acf7e9b501373f2c2dfe947cd328ab5e6e1174d4f7` |
| trusthub | wb_conmax-T200.rar | 116,217 | `e7a0d6c01eb77780f2b4daceb32afbe5f02732f2e455e1069c132b3695374f54` |
| trusthub | wb_conmax-T300.rar | 116,877 | `876c7880592b6a26828d953708210bb0f12f9ce2d5c0c58ad1821e737b4aa953` |
