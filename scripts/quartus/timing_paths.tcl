# Report the longest and shortest path delays of four path classes and the clock
# frequency limit for the slow 1200 mV 85 C timing model.
# Usage: quartus_sta -t timing_paths.tcl <project> <output file>
package require ::quartus::sta
lassign $quartus(args) project outfile

project_open $project
create_timing_netlist
read_sdc
update_timing_netlist
set_operating_conditions -model slow -temperature 85 -voltage 1200
update_timing_netlist

set fh [open $outfile w]
puts $fh "fmax\t[get_clock_fmax_info]"
foreach {cls from to} {in2out all_inputs all_outputs in2reg all_inputs all_registers reg2reg all_registers all_registers reg2out all_registers all_outputs} {
  set fc [$from]
  set tc [$to]
  if {[get_collection_size $fc] == 0 || [get_collection_size $tc] == 0} {
    puts $fh "$cls\tnone"
    continue
  }
  set found 0
  foreach_in_collection p [get_path -from $fc -to $tc -npaths 1 -nworst 1] {
    set found 1
    puts $fh "$cls\tmax\t[get_path_info $p -data_delay]\t[get_path_info $p -num_logic_levels]"
  }
  foreach_in_collection p [get_path -from $fc -to $tc -npaths 1 -nworst 1 -min_path] {
    puts $fh "$cls\tmin\t[get_path_info $p -data_delay]\t[get_path_info $p -num_logic_levels]"
  }
  if {!$found} { puts $fh "$cls\tnopath" }
}
foreach kind {setup hold} {
  set r [report_timing -$kind -npaths 1 -nworst 1 -panel_name "${kind}_worst" -quiet]
  puts $fh "worst_$kind\t[lindex $r 0]\t[lindex $r 1]"
}
close $fh
delete_timing_netlist
project_close
