# List the top-level ports of a synthesized design and the ports that act as clocks.
# A port is a clock when the Timing Analyzer's clock derivation places a clock on it,
# that is, when it drives the clock input of at least one register.
# Usage: quartus_sta -t ports.tcl <project> <output file>
package require ::quartus::sta
lassign $quartus(args) project outfile

project_open $project
create_timing_netlist -post_map
derive_clocks -period 20.000
update_timing_netlist

set fh [open $outfile w]
foreach_in_collection p [get_ports *] {
  set dir out
  if {[get_port_info -is_inout_port $p]} {
    set dir inout
  } elseif {[get_port_info -is_input_port $p]} {
    set dir in
  }
  puts $fh "port\t[get_port_info -name $p]\t$dir"
}
foreach_in_collection c [all_clocks] {
  foreach_in_collection n [get_clock_info -targets $c] {
    puts $fh "clock\t[get_node_info -name $n]\t[get_node_info -type $n]"
  }
}
close $fh
delete_timing_netlist
project_close
