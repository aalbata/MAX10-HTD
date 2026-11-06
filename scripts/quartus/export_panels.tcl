# Write every report panel of a compiled project to a tab-separated text file.
# Usage: quartus_sh -t export_panels.tcl <project> <output file>
load_package report
lassign $quartus(args) project outfile

project_open $project
load_report
set fh [open $outfile w]
fconfigure $fh -encoding utf-8
foreach panel [get_report_panel_names] {
  set nrows [get_number_of_rows -name $panel]
  puts $fh "#PANEL\t$panel\t$nrows"
  for {set r 0} {$r < $nrows} {incr r} {
    set cells {}
    foreach c [get_report_panel_row -name $panel -row $r] {
      lappend cells [string map [list "\t" " " "\n" " " "\r" " "] $c]
    }
    puts $fh [join $cells "\t"]
  }
}
close $fh
unload_report
project_close
