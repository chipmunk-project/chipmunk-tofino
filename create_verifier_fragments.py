import sys

if (len(sys.argv) < 5):
  print("Usage: ", sys.argv[0], " <program file> <number of pipeline stages> <number of alus per stage> <transform function>")
  exit(1)
else:
  program_file = sys.argv[1]
  num_pipeline_stages = int(sys.argv[2])
  num_alus_per_stage  = int(sys.argv[3])
  transform_function  = syst.argv[4]

  # Generate predicates from list of asserts.

  # Generate predicates from hole ranges in global holes.

  # Generate sketch functions by converting holes into function arguments and also converting harness inputs into function arguments.
 
