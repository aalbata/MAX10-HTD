# MAX10-HTD feature dictionary

Every feature is a design-level number computed from one compiled design. Missing values (empty cells in features.csv) mean that the quantity is undefined for the design or that the vendor report does not give it; the last column lists the cases.

## Feature groups

- `quartus_synthesis` (27 features): Analysis & Synthesis reports (resource estimates, register and multiplexer statistics, LUT depth)
- `quartus_fitter` (31 features): Fitter reports (placed resource usage, LAB statistics, control signals, fan-out)
- `quartus_routing` (7 features): Fitter routing usage by interconnect type
- `quartus_timing` (17 features): Timing Analyzer, slow 1200 mV 85 C model, 20 ns constraint
- `quartus_power` (10 features): Power Analyzer with default settings (12.5 % toggle rate for input pins, vectorless estimation of internal nodes); virtual input pins carry no switching activity, so the dynamic estimate reflects the clock network, clocked registers and memories, and logic that switches without input activity
- `netlist_structure` (50 features): Post-fit Verilog netlist: cell counts, fan-out, depth, connectivity, COP and SCOAP testability
- `rtl_structure` (21 features): Yosys word-level elaboration of the Verilog source

## Features

| Feature | Group | Unit | Extraction source | Definition | Missing when |
|---|---|---|---|---|---|
| `syn_le_est` | quartus_synthesis | count | Quartus report: Analysis & Synthesis Resource Usage Summary | Estimated total logic elements after synthesis | not reported when synthesis leaves no logic element |
| `syn_comb_functions` | quartus_synthesis | count | Quartus report: Analysis & Synthesis Resource Usage Summary | Total combinational functions |  |
| `syn_lut4` | quartus_synthesis | count | Quartus report: Analysis & Synthesis Resource Usage Summary | Combinational functions with 4 LUT inputs |  |
| `syn_lut3` | quartus_synthesis | count | Quartus report: Analysis & Synthesis Resource Usage Summary | Combinational functions with 3 LUT inputs |  |
| `syn_lut_le2` | quartus_synthesis | count | Quartus report: Analysis & Synthesis Resource Usage Summary | Combinational functions with 2 or fewer LUT inputs |  |
| `syn_le_normal` | quartus_synthesis | count | Quartus report: Analysis & Synthesis Resource Usage Summary | Logic elements in normal mode |  |
| `syn_le_arith` | quartus_synthesis | count | Quartus report: Analysis & Synthesis Resource Usage Summary | Logic elements in arithmetic (carry-chain) mode |  |
| `syn_registers` | quartus_synthesis | count | Quartus report: Analysis & Synthesis Resource Usage Summary | Total registers |  |
| `syn_io_registers` | quartus_synthesis | count | Quartus report: Analysis & Synthesis Resource Usage Summary | Registers packed into I/O elements |  |
| `syn_io_pins` | quartus_synthesis | count | Quartus report: Analysis & Synthesis Resource Usage Summary | I/O pins |  |
| `syn_mult9` | quartus_synthesis | count | Quartus report: Analysis & Synthesis Resource Usage Summary | Embedded multiplier 9-bit elements |  |
| `syn_mem_bits` | quartus_synthesis | bits | Quartus report: Analysis & Synthesis Summary | Total memory bits |  |
| `syn_max_fanout` | quartus_synthesis | count | Quartus report: Analysis & Synthesis Resource Usage Summary | Maximum fan-out of any node |  |
| `syn_total_fanout` | quartus_synthesis | count | Quartus report: Analysis & Synthesis Resource Usage Summary | Sum of fan-outs over all nodes |  |
| `syn_avg_fanout` | quartus_synthesis | ratio | Quartus report: Analysis & Synthesis Resource Usage Summary | Average fan-out |  |
| `syn_reg_sclr` | quartus_synthesis | count | Quartus report: General Register Statistics | Registers using synchronous clear |  |
| `syn_reg_sload` | quartus_synthesis | count | Quartus report: General Register Statistics | Registers using synchronous load |  |
| `syn_reg_aclr` | quartus_synthesis | count | Quartus report: General Register Statistics | Registers using asynchronous clear |  |
| `syn_reg_aload` | quartus_synthesis | count | Quartus report: General Register Statistics | Registers using asynchronous load |  |
| `syn_reg_ena` | quartus_synthesis | count | Quartus report: General Register Statistics | Registers using clock enable |  |
| `syn_reg_preset` | quartus_synthesis | count | Quartus report: General Register Statistics | Registers using preset |  |
| `syn_mux_groups` | quartus_synthesis | count | Quartus report: Multiplexer Restructuring Statistics | Multiplexer groups listed by the restructuring report |  |
| `syn_mux_bits` | quartus_synthesis | bits | Quartus report: Multiplexer Restructuring Statistics | Total bus width of listed multiplexers |  |
| `syn_mux_max_inputs` | quartus_synthesis | count | Quartus report: Multiplexer Restructuring Statistics | Largest number of multiplexer data inputs |  |
| `syn_mux_baseline_le` | quartus_synthesis | count | Quartus report: Multiplexer Restructuring Statistics | Baseline area of listed multiplexers |  |
| `syn_max_lut_depth` | quartus_synthesis | levels | Quartus report: Post-Synthesis Netlist Statistics | Maximum LUT depth |  |
| `syn_avg_lut_depth` | quartus_synthesis | levels | Quartus report: Post-Synthesis Netlist Statistics | Average LUT depth |  |
| `fit_le` | quartus_fitter | count | Quartus report: Fitter Resource Usage Summary | Total logic elements after fitting |  |
| `fit_le_comb_only` | quartus_fitter | count | Quartus report: Fitter Resource Usage Summary | Logic elements: combinational with no register |  |
| `fit_le_reg_only` | quartus_fitter | count | Quartus report: Fitter Resource Usage Summary | Logic elements: register only |  |
| `fit_le_comb_reg` | quartus_fitter | count | Quartus report: Fitter Resource Usage Summary | Logic elements: combinational with a register |  |
| `fit_lut4` | quartus_fitter | count | Quartus report: Fitter Resource Usage Summary | Logic elements using 4 LUT inputs |  |
| `fit_lut3` | quartus_fitter | count | Quartus report: Fitter Resource Usage Summary | Logic elements using 3 LUT inputs |  |
| `fit_lut_le2` | quartus_fitter | count | Quartus report: Fitter Resource Usage Summary | Logic elements using 2 or fewer LUT inputs |  |
| `fit_le_normal` | quartus_fitter | count | Quartus report: Fitter Resource Usage Summary | Logic elements in normal mode |  |
| `fit_le_arith` | quartus_fitter | count | Quartus report: Fitter Resource Usage Summary | Logic elements in arithmetic mode |  |
| `fit_registers` | quartus_fitter | count | Quartus report: Fitter Resource Usage Summary | Total registers |  |
| `fit_labs` | quartus_fitter | count | Quartus report: Fitter Resource Usage Summary | Logic array blocks partially or completely used |  |
| `fit_io_pins` | quartus_fitter | count | Quartus report: Fitter Resource Usage Summary | I/O pins |  |
| `fit_m9k` | quartus_fitter | count | Quartus report: Fitter Resource Usage Summary | M9K memory blocks |  |
| `fit_mem_bits` | quartus_fitter | bits | Quartus report: Fitter Resource Usage Summary | Total block memory bits |  |
| `fit_mult9` | quartus_fitter | count | Quartus report: Fitter Resource Usage Summary | Embedded multiplier 9-bit elements |  |
| `fit_pll` | quartus_fitter | count | Quartus report: Fitter Resource Usage Summary | PLLs |  |
| `fit_global_signals` | quartus_fitter | count | Quartus report: Fitter Resource Usage Summary | Signals routed on global networks |  |
| `fit_ic_avg_pct` | quartus_fitter | percent | Quartus report: Fitter Resource Usage Summary | Average interconnect usage (total) |  |
| `fit_ic_peak_pct` | quartus_fitter | percent | Quartus report: Fitter Resource Usage Summary | Peak interconnect usage (total) |  |
| `fit_max_fanout` | quartus_fitter | count | Quartus report: Fitter Resource Usage Summary | Maximum fan-out |  |
| `fit_max_nonglobal_fanout` | quartus_fitter | count | Quartus report: Fitter Resource Usage Summary | Highest non-global fan-out |  |
| `fit_total_fanout` | quartus_fitter | count | Quartus report: Fitter Resource Usage Summary | Total fan-out |  |
| `fit_avg_fanout` | quartus_fitter | ratio | Quartus report: Fitter Resource Usage Summary | Average fan-out |  |
| `fit_lab_avg_le` | quartus_fitter | count | Quartus report: LAB Logic Elements | Average logic elements per used LAB |  |
| `fit_lab_avg_inputs` | quartus_fitter | count | Quartus report: LAB Distinct Inputs | Average distinct inputs per used LAB | not reported when the Fitter writes no LAB Distinct Inputs panel |
| `fit_lab_avg_sourced` | quartus_fitter | count | Quartus report: LAB Signals Sourced | Average signals sourced per used LAB |  |
| `fit_lab_avg_sourced_out` | quartus_fitter | count | Quartus report: LAB Signals Sourced Out | Average signals leaving each used LAB |  |
| `fit_ctrl_signals` | quartus_fitter | count | Quartus report: Control Signals | Distinct register control signals |  |
| `fit_ctrl_clock_enable` | quartus_fitter | count | Quartus report: Control Signals | Control signals used as clock enables |  |
| `fit_ctrl_sync` | quartus_fitter | count | Quartus report: Control Signals | Control signals used as synchronous clear or load |  |
| `fit_ctrl_async` | quartus_fitter | count | Quartus report: Control Signals | Control signals used as asynchronous clear or load |  |
| `rte_block` | quartus_routing | count | Quartus report: Routing Usage Summary | Block interconnects used |  |
| `rte_c4` | quartus_routing | count | Quartus report: Routing Usage Summary | C4 column interconnects used |  |
| `rte_c16` | quartus_routing | count | Quartus report: Routing Usage Summary | C16 column interconnects used |  |
| `rte_r4` | quartus_routing | count | Quartus report: Routing Usage Summary | R4 row interconnects used |  |
| `rte_r24` | quartus_routing | count | Quartus report: Routing Usage Summary | R24 row interconnects used |  |
| `rte_direct` | quartus_routing | count | Quartus report: Routing Usage Summary | Direct links used |  |
| `rte_local` | quartus_routing | count | Quartus report: Routing Usage Summary | Local interconnects used |  |
| `sta_fmax_mhz` | quartus_timing | MHz | Quartus report: timing_paths.tcl get_clock_fmax_info | Maximum clock frequency of the slowest clock from register-to-register paths, before the device restriction on clock period and I/O toggle rate; missing for designs without such a path | no clock or no register-to-register path |
| `sta_setup_slack_ns` | quartus_timing | ns | Quartus report: timing_paths.tcl report_timing | Worst setup slack against the 20 ns constraint | no constrained path |
| `sta_hold_slack_ns` | quartus_timing | ns | Quartus report: timing_paths.tcl report_timing | Worst hold slack | no constrained path |
| `sta_mc_setup_slack_ns` | quartus_timing | ns | Quartus report: Multicorner Timing Analysis Summary | Worst setup slack over the three timing corners | no constrained path |
| `sta_mc_hold_slack_ns` | quartus_timing | ns | Quartus report: Multicorner Timing Analysis Summary | Worst hold slack over the three timing corners | no constrained path |
| `sta_in2out_max_ns` | quartus_timing | ns | Quartus report: timing_paths.tcl get_path | Longest input to output data delay; missing when no such path exists | no combinational path from an input to an output |
| `sta_in2out_min_ns` | quartus_timing | ns | Quartus report: timing_paths.tcl get_path -min_path | Shortest input to output data delay; missing when no such path exists | no combinational path from an input to an output |
| `sta_in2out_levels` | quartus_timing | levels | Quartus report: timing_paths.tcl get_path | Logic levels on the longest input to output path; missing when no such path exists | no combinational path from an input to an output |
| `sta_in2reg_max_ns` | quartus_timing | ns | Quartus report: timing_paths.tcl get_path | Longest input to register data delay; missing when no such path exists | no path from an input to a register |
| `sta_in2reg_min_ns` | quartus_timing | ns | Quartus report: timing_paths.tcl get_path -min_path | Shortest input to register data delay; missing when no such path exists | no path from an input to a register |
| `sta_in2reg_levels` | quartus_timing | levels | Quartus report: timing_paths.tcl get_path | Logic levels on the longest input to register path; missing when no such path exists | no path from an input to a register |
| `sta_reg2reg_max_ns` | quartus_timing | ns | Quartus report: timing_paths.tcl get_path | Longest register to register data delay; missing when no such path exists | no register-to-register path |
| `sta_reg2reg_min_ns` | quartus_timing | ns | Quartus report: timing_paths.tcl get_path -min_path | Shortest register to register data delay; missing when no such path exists | no register-to-register path |
| `sta_reg2reg_levels` | quartus_timing | levels | Quartus report: timing_paths.tcl get_path | Logic levels on the longest register to register path; missing when no such path exists | no register-to-register path |
| `sta_reg2out_max_ns` | quartus_timing | ns | Quartus report: timing_paths.tcl get_path | Longest register to output data delay; missing when no such path exists | no path from a register to an output |
| `sta_reg2out_min_ns` | quartus_timing | ns | Quartus report: timing_paths.tcl get_path -min_path | Shortest register to output data delay; missing when no such path exists | no path from a register to an output |
| `sta_reg2out_levels` | quartus_timing | levels | Quartus report: timing_paths.tcl get_path | Logic levels on the longest register to output path; missing when no such path exists | no path from a register to an output |
| `pow_total_mw` | quartus_power | mW | Quartus report: Power Analyzer Summary | Total thermal power, vectorless estimate |  |
| `pow_core_dynamic_mw` | quartus_power | mW | Quartus report: Power Analyzer Summary | Core dynamic thermal power, vectorless estimate |  |
| `pow_core_static_mw` | quartus_power | mW | Quartus report: Power Analyzer Summary | Core static thermal power |  |
| `pow_io_mw` | quartus_power | mW | Quartus report: Power Analyzer Summary | I/O thermal power, vectorless estimate |  |
| `pow_comb_mw` | quartus_power | mW | Quartus report: Thermal Power Dissipation by Block Type | Combinational cell power |  |
| `pow_reg_mw` | quartus_power | mW | Quartus report: Thermal Power Dissipation by Block Type | Register cell power |  |
| `pow_clock_mw` | quartus_power | mW | Quartus report: Thermal Power Dissipation by Block Type | Clock control block power |  |
| `pow_comb_toggle` | quartus_power | Mtransitions/s | Quartus report: Thermal Power Dissipation by Block Type | Average toggle rate of combinational cells |  |
| `pow_reg_toggle` | quartus_power | Mtransitions/s | Quartus report: Thermal Power Dissipation by Block Type | Average toggle rate of register cells |  |
| `pow_vcc_dynamic_ma` | quartus_power | mA | Quartus report: Current Drawn from Voltage Supplies Summary | Dynamic current drawn from the VCC core supply |  |
| `net_pi_bits` | netlist_structure | count | Post-fit netlist (quartus_eda) | Primary input bits of the top-level module |  |
| `net_po_bits` | netlist_structure | count | Post-fit netlist (quartus_eda) | Primary output bits of the top-level module |  |
| `net_lcells` | netlist_structure | count | Post-fit netlist (quartus_eda) | Logic cells (4-input LUT with carry) in the post-fit netlist |  |
| `net_lcells_arith` | netlist_structure | count | Post-fit netlist (quartus_eda) | Logic cells that use the carry input or drive a carry output |  |
| `net_dffs` | netlist_structure | count | Post-fit netlist (quartus_eda) | Registers (dffeas) |  |
| `net_ram_blocks` | netlist_structure | count | Post-fit netlist (quartus_eda) | Embedded memory blocks |  |
| `net_mac_blocks` | netlist_structure | count | Post-fit netlist (quartus_eda) | Embedded multiplier blocks (mult and output stages) |  |
| `net_clock_nets` | netlist_structure | count | Post-fit netlist (quartus_eda) | Distinct nets that drive register clock pins |  |
| `net_signals` | netlist_structure | count | Post-fit netlist (quartus_eda) | Distinct driven signals excluding clock nets |  |
| `net_pins` | netlist_structure | count | Post-fit netlist (quartus_eda) | Signal-to-cell input connections excluding clock nets |  |
| `net_lut_k0` | netlist_structure | count | Post-fit netlist (quartus_eda) | Logic cells whose LUT uses no data input |  |
| `net_lut_k1` | netlist_structure | count | Post-fit netlist (quartus_eda) | Logic cells whose LUT uses 1 data input |  |
| `net_lut_k2` | netlist_structure | count | Post-fit netlist (quartus_eda) | Logic cells whose LUT uses 2 data inputs |  |
| `net_lut_k3` | netlist_structure | count | Post-fit netlist (quartus_eda) | Logic cells whose LUT uses 3 data inputs |  |
| `net_lut_k4` | netlist_structure | count | Post-fit netlist (quartus_eda) | Logic cells whose LUT uses 4 data inputs |  |
| `net_fanin_mean` | netlist_structure | count | Post-fit netlist (quartus_eda) | Mean number of used LUT data inputs per logic cell |  |
| `net_fn_and_frac` | netlist_structure | fraction | Post-fit netlist (quartus_eda) | Normal-mode LUTs (2+ inputs) whose output is 1 for exactly one input combination |  |
| `net_fn_or_frac` | netlist_structure | fraction | Post-fit netlist (quartus_eda) | Normal-mode LUTs (2+ inputs) whose output is 0 for exactly one input combination |  |
| `net_fn_xor_frac` | netlist_structure | fraction | Post-fit netlist (quartus_eda) | Normal-mode LUTs (2+ inputs) computing parity or its complement |  |
| `net_fn_buf_frac` | netlist_structure | fraction | Post-fit netlist (quartus_eda) | Normal-mode LUTs with one used input (buffer or inverter) |  |
| `net_fn_other_frac` | netlist_structure | fraction | Post-fit netlist (quartus_eda) | Normal-mode LUTs with any other function |  |
| `net_fanout_mean` | netlist_structure | count | Post-fit netlist (quartus_eda) | Mean fan-out of driven signals (clock nets excluded) |  |
| `net_fanout_std` | netlist_structure | count | Post-fit netlist (quartus_eda) | Standard deviation of signal fan-out |  |
| `net_fanout_max` | netlist_structure | count | Post-fit netlist (quartus_eda) | Maximum signal fan-out |  |
| `net_fanout_p90` | netlist_structure | count | Post-fit netlist (quartus_eda) | 90th percentile of signal fan-out |  |
| `net_fanout_ge8_frac` | netlist_structure | fraction | Post-fit netlist (quartus_eda) | Signals with fan-out of at least 8 |  |
| `net_depth_max` | netlist_structure | levels | Post-fit netlist (quartus_eda) | Longest chain of logic-cell outputs between sequential or I/O boundaries | combinational cycle through logic cells |
| `net_depth_mean` | netlist_structure | levels | Post-fit netlist (quartus_eda) | Mean logic depth at register inputs and primary outputs | combinational cycle through logic cells |
| `net_depth_nocarry_max` | netlist_structure | levels | Post-fit netlist (quartus_eda) | Longest logic chain counting carry links as zero levels | combinational cycle through logic cells |
| `net_carry_chain_max` | netlist_structure | cells | Post-fit netlist (quartus_eda) | Longest chain of carry-out to carry-in links |  |
| `net_carry_chains` | netlist_structure | count | Post-fit netlist (quartus_eda) | Carry chains of two or more cells |  |
| `net_wcc` | netlist_structure | count | Post-fit netlist (quartus_eda) | Weakly connected components of the cell graph |  |
| `net_wcc_largest_frac` | netlist_structure | fraction | Post-fit netlist (quartus_eda) | Share of cells in the largest weakly connected component |  |
| `net_scc_count` | netlist_structure | count | Post-fit netlist (quartus_eda) | Strongly connected components with more than one cell (feedback through registers) |  |
| `net_scc_frac` | netlist_structure | fraction | Post-fit netlist (quartus_eda) | Share of cells inside such feedback components |  |
| `net_sp_lt_1e2_frac` | netlist_structure | fraction | Post-fit netlist (quartus_eda) | Logic-cell outputs with COP probability of the rarer value below 0.01 | combinational cycle through logic cells, or no logic cell with inputs |
| `net_sp_lt_1e3_frac` | netlist_structure | fraction | Post-fit netlist (quartus_eda) | Logic-cell outputs with COP probability of the rarer value below 0.001 | combinational cycle through logic cells, or no logic cell with inputs |
| `net_sp_lt_1e4_frac` | netlist_structure | fraction | Post-fit netlist (quartus_eda) | Logic-cell outputs with COP probability of the rarer value below 0.0001 | combinational cycle through logic cells, or no logic cell with inputs |
| `net_sp_lt_1e2` | netlist_structure | count | Post-fit netlist (quartus_eda) | Logic-cell outputs with COP probability of the rarer value below 0.01 | combinational cycle through logic cells, or no logic cell with inputs |
| `net_sp_min_log10` | netlist_structure | log10 | Post-fit netlist (quartus_eda) | Base-10 logarithm of the smallest COP rare-value probability (floored at -12) | combinational cycle through logic cells, or no logic cell with inputs |
| `net_sp_entropy_mean` | netlist_structure | bits | Post-fit netlist (quartus_eda) | Mean binary entropy of logic-cell output probabilities | combinational cycle through logic cells, or no logic cell with inputs |
| `net_cc0_max` | netlist_structure | SCOAP | Post-fit netlist (quartus_eda) | Maximum finite combinational 0-controllability | combinational cycle through logic cells, or no logic cell with inputs |
| `net_cc1_max` | netlist_structure | SCOAP | Post-fit netlist (quartus_eda) | Maximum finite combinational 1-controllability | combinational cycle through logic cells, or no logic cell with inputs |
| `net_cc1_p90` | netlist_structure | SCOAP | Post-fit netlist (quartus_eda) | 90th percentile of combinational 1-controllability | combinational cycle through logic cells, or no logic cell with inputs |
| `net_cc_mean` | netlist_structure | SCOAP | Post-fit netlist (quartus_eda) | Mean of CC0 and CC1 over logic-cell outputs | combinational cycle through logic cells, or no logic cell with inputs |
| `net_co_max` | netlist_structure | SCOAP | Post-fit netlist (quartus_eda) | Maximum finite combinational observability | combinational cycle through logic cells, or no logic cell with inputs |
| `net_co_p90` | netlist_structure | SCOAP | Post-fit netlist (quartus_eda) | 90th percentile of combinational observability | combinational cycle through logic cells, or no logic cell with inputs |
| `net_co_mean` | netlist_structure | SCOAP | Post-fit netlist (quartus_eda) | Mean combinational observability over logic-cell outputs | combinational cycle through logic cells, or no logic cell with inputs |
| `net_cc_hard_frac` | netlist_structure | fraction | Post-fit netlist (quartus_eda) | Logic-cell outputs with CC0 or CC1 of at least 20 | combinational cycle through logic cells, or no logic cell with inputs |
| `net_co_hard_frac` | netlist_structure | fraction | Post-fit netlist (quartus_eda) | Logic-cell outputs with CO of at least 20 | combinational cycle through logic cells, or no logic cell with inputs |
| `rtl_cells` | rtl_structure | count | Yosys RTL elaboration | Word-level cells after elaboration | VHDL design (Yosys reads Verilog only) |
| `rtl_wires` | rtl_structure | count | Yosys RTL elaboration | Named and internal wires | VHDL design (Yosys reads Verilog only) |
| `rtl_wire_bits` | rtl_structure | bits | Yosys RTL elaboration | Total wire bits | VHDL design (Yosys reads Verilog only) |
| `rtl_arith` | rtl_structure | count | Yosys RTL elaboration | Word-level cells of class arith | VHDL design (Yosys reads Verilog only) |
| `rtl_mul` | rtl_structure | count | Yosys RTL elaboration | Word-level cells of class mul | VHDL design (Yosys reads Verilog only) |
| `rtl_cmp_eq` | rtl_structure | count | Yosys RTL elaboration | Word-level cells of class cmp_eq | VHDL design (Yosys reads Verilog only) |
| `rtl_cmp_rel` | rtl_structure | count | Yosys RTL elaboration | Word-level cells of class cmp_rel | VHDL design (Yosys reads Verilog only) |
| `rtl_logic_bit` | rtl_structure | count | Yosys RTL elaboration | Word-level cells of class logic_bit | VHDL design (Yosys reads Verilog only) |
| `rtl_logic_bool` | rtl_structure | count | Yosys RTL elaboration | Word-level cells of class logic_bool | VHDL design (Yosys reads Verilog only) |
| `rtl_reduce` | rtl_structure | count | Yosys RTL elaboration | Word-level cells of class reduce | VHDL design (Yosys reads Verilog only) |
| `rtl_shift` | rtl_structure | count | Yosys RTL elaboration | Word-level cells of class shift | VHDL design (Yosys reads Verilog only) |
| `rtl_mux` | rtl_structure | count | Yosys RTL elaboration | Word-level cells of class mux | VHDL design (Yosys reads Verilog only) |
| `rtl_pmux` | rtl_structure | count | Yosys RTL elaboration | Word-level cells of class pmux | VHDL design (Yosys reads Verilog only) |
| `rtl_ff` | rtl_structure | count | Yosys RTL elaboration | Word-level cells of class ff | VHDL design (Yosys reads Verilog only) |
| `rtl_latch` | rtl_structure | count | Yosys RTL elaboration | Word-level cells of class latch | VHDL design (Yosys reads Verilog only) |
| `rtl_mem` | rtl_structure | count | Yosys RTL elaboration | Word-level cells of class mem | VHDL design (Yosys reads Verilog only) |
| `rtl_ff_bits` | rtl_structure | bits | Yosys RTL elaboration | Register bits (sum of register widths) | VHDL design (Yosys reads Verilog only) |
| `rtl_const_cmp` | rtl_structure | count | Yosys RTL elaboration | Equality comparisons with one fully constant operand | VHDL design (Yosys reads Verilog only) |
| `rtl_const_cmp_bits_max` | rtl_structure | bits | Yosys RTL elaboration | Widest equality comparison against a constant | VHDL design (Yosys reads Verilog only) |
| `rtl_const_cmp_bits_sum` | rtl_structure | bits | Yosys RTL elaboration | Total width of equality comparisons against constants | VHDL design (Yosys reads Verilog only) |
| `rtl_other` | rtl_structure | count | Yosys RTL elaboration | Cells outside the listed classes | VHDL design (Yosys reads Verilog only) |
