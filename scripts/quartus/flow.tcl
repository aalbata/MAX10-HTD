# Create a Quartus Prime project for one design and run synthesis only (probe)
# or the full compilation flow (full).
# Usage: quartus_sh -t flow.tcl <project> <top> <file list> <sdc file> <seed> <virtual pin list> <mode> <hdl version>
#   file list         lines "<assignment name><tab><path>", for example "VERILOG_FILE<tab>src/uart.v"
#   virtual pin list  one top-level port name per line; each becomes a virtual pin (full mode)
#   mode              probe: Analysis & Synthesis only; full: synthesis, fitter, timing, assembler,
#                     power analysis and the simulation netlist writer
#   hdl version       VERILOG_2001 or SYSTEMVERILOG_2005
load_package flow
lassign $quartus(args) project top filelist sdcfile seed vpins mode hdlver

proc read_lines {path} {
  set fh [open $path r]
  set lines [split [string trimright [read $fh] "\n"] "\n"]
  close $fh
  return $lines
}

project_new $project -overwrite
set_global_assignment -name FAMILY "MAX 10"
set_global_assignment -name DEVICE 10M50DAF484C7G
# Single uncompressed image with memory initialization: HDL-initialized ROM and RAM can use M9K blocks.
set_global_assignment -name INTERNAL_FLASH_UPDATE_MODE "SINGLE IMAGE WITH ERAM"
set_global_assignment -name TOP_LEVEL_ENTITY $top
set_global_assignment -name SEARCH_PATH src
set_global_assignment -name VERILOG_INPUT_VERSION $hdlver
foreach line [read_lines $filelist] {
  if {$line eq ""} continue
  lassign [split $line "\t"] kind path
  set_global_assignment -name $kind $path
}
set_global_assignment -name SDC_FILE $sdcfile
set_global_assignment -name NUM_PARALLEL_PROCESSORS 1
set_global_assignment -name SEED $seed
set_global_assignment -name EDA_SIMULATION_TOOL "Questa Altera FPGA (Verilog)"
set_global_assignment -name EDA_OUTPUT_DATA_FORMAT "VERILOG HDL" -section_id eda_simulation
if {$mode eq "full" && [file exists $vpins]} {
  foreach p [read_lines $vpins] {
    if {$p ne ""} { set_instance_assignment -name VIRTUAL_PIN ON -to $p }
  }
}
export_assignments

if {[catch {execute_module -tool map} err]} { project_close; exit 2 }
if {$mode eq "full"} {
  if {[catch {execute_module -tool fit} err]} { project_close; exit 3 }
  if {[catch {execute_module -tool sta} err]} { project_close; exit 4 }
  if {[catch {execute_module -tool asm} err]} { project_close; exit 5 }
  if {[catch {execute_module -tool pow} err]} { project_close; exit 6 }
  if {[catch {execute_module -tool eda} err]} { project_close; exit 7 }
}
project_close
