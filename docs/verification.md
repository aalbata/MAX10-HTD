# Verification

The labels are those of the benchmark sources. MAX10-HTD adds three checks of every Trojan-inserted implementation against the implementation of its Trojan-free reference (`scripts/verification/dormant.py`, results in `dataset/metadata/verification.csv`).

1. Interface: the top-level ports of the two designs are compared.
2. Structure: every post-fit netlist receives a fingerprint that ignores signal, instance and project names (cell types, parameter values and connections, refined over four rounds). A Trojan-inserted design with the fingerprint of a Trojan-free design is taken to carry no Trojan after synthesis and is excluded. Designs of the same class with identical fingerprints are kept once; of two Trojan-free designs with the same fingerprint, the copy from the source listed first (Trust-Hub, GHOST, RISC-V and Web3) is kept and is the reference of the Trojan-inserted designs of both.
3. Dormant behavior: both netlists are simulated with Icarus Verilog and the Quartus MAX 10 models on the same pseudo-random inputs for 1000 clock cycles; inputs that only one design has are held at 0 and reset-like inputs are asserted for two cycles. The common outputs are compared in every cycle.

What the checks do not show: identical outputs do not prove that a trigger can fire or that a payload works, and differing outputs do not identify the payload. Trigger activation and payloads are documented by the sources (GHOST reports testbench activation before and after synthesis); they were not re-verified. No design was programmed onto a physical board.

## Outcomes for the included Trojan-inserted implementations

- Pairs verified: 108
- Identical interface: 92; extra inputs: 15; extra outputs: 6
- Dormant-behavior outcomes: outputs differ 31, outputs identical 74, simulation timeout 3
- Median difference in post-fit cell count: 23 cells; 24 pairs differ by at most 10 cells
- Excluded because the netlist has the fingerprint of a Trojan-free design (inserted logic taken as removed by synthesis): 13
- Trojan-inserted designs left out because their netlist has the fingerprint of another Trojan-inserted design: 10
- Trojan-free designs left out because their netlist has the fingerprint of another Trojan-free design: 1

