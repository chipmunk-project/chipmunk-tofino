from jinja2 import Template, Environment, FileSystemLoader, StrictUndefined
import pickle
from pathlib import Path
import sys
from   sketch_generator import SketchGenerator
from   chipmunk_pickle import ChipmunkPickle
import re
import subprocess

# Use a regex to scan the program and extract the largest packet field index and largest state variable index
def get_num_pkt_fields_and_state_vars(program):
  pkt_fields = [int(x) for x in re.findall("state_and_packet.pkt_(\d+)", program)]
  state_vars = [int(x) for x in re.findall("state_and_packet.state_(\d+)", program)]
  return (max(pkt_fields) + 1, max(state_vars) + 1)

# Convention for indices:
# i : pipeline stage
# j : ALU within pipeline stage
# k : PHV container within pipeline stage
# l : packet field or state variable from program

if (len(sys.argv) < 7):
  print("Usage: python3 " + sys.argv[0] + " <program file> <instruction file> <number of pipeline stages> <number of stateless/stateful ALUs per stage> <codegen/optverify> <sketch_name (w/o file extension)>")
  sys.exit(1)
else:
  program_file         = str(sys.argv[1])
  (num_fields_in_prog, num_state_vars) = get_num_pkt_fields_and_state_vars(Path(program_file).read_text())
  instruction_file     = str(sys.argv[2])
  num_pipeline_stages  = int(sys.argv[3])
  num_alus_per_stage   = int(sys.argv[4])
  num_phv_containers   = num_alus_per_stage
  assert(num_fields_in_prog <= num_phv_containers)
  mode                 = str(sys.argv[5])
  assert((mode == "codegen") or (mode == "optverify"))
  sketch_name          = str(sys.argv[6])

# Initialize jinja2 environment for templates
env = Environment(loader = FileSystemLoader('./templates'), undefined = StrictUndefined)

# Create an object for sketch generation
sketch_generator = SketchGenerator(sketch_name = sketch_name, num_pipeline_stages = num_pipeline_stages, num_alus_per_stage = num_alus_per_stage, num_phv_containers = num_phv_containers, num_state_vars = num_state_vars, num_fields_in_prog = num_fields_in_prog, jinja2_env = env, instruction_file = instruction_file)

# Create operand muxes for stateful ALUs, output muxes, and stateless and stateful ALUs
stateful_operand_mux_definitions = sketch_generator.generate_stateful_operand_muxes()
output_mux_definitions           = sketch_generator.generate_output_muxes()
alu_definitions                  = sketch_generator.generate_alus()

# Create allocator to ensure each state var is assigned to exactly stateful ALU and vice versa.
sketch_generator.generate_state_allocator()

# Now fill the appropriate template holes using the components created using sketch_generator
if (mode == "codegen"):
  codegen_code = sketch_generator.generate_sketch(program_file = program_file,
                 alu_definitions = alu_definitions,
                 stateful_operand_mux_definitions = stateful_operand_mux_definitions, mode = mode,
                 output_mux_definitions = output_mux_definitions)

  # Create file and write sketch_harness into it.
  sketch_file = open(sketch_name + "_codegen.sk", "w")
  sketch_file.write(codegen_code)
  sketch_file.close()

  # Call sketch on it
  print("Total number of hole bits is", sketch_generator.total_hole_bits_)
  print("Sketch file is ", sketch_file.name)
  (ret_code, output) = subprocess.getstatusoutput("time sketch -V 12 --slv-seed=1 --slv-parallel --bnd-inbits=2 --bnd-int-range=50 " + sketch_file.name)
  if (ret_code != 0):
    errors_file = open(sketch_name + ".errors", "w")
    errors_file.write(output)
    errors_file.close()
    print("Sketch failed. Output left in " + errors_file.name)
    sys.exit(1)
  else:
    success_file = open(sketch_name + ".success", "w")
    for hole_name in sketch_generator.hole_names_:
      hits = re.findall("(" + hole_name + ")__" + "\w+ = (\d+)", output)
      assert(len(hits) == 1)
      assert(len(hits[0]) == 2)
      print("int ", hits[0][0], " = ", hits[0][1], ";")
    success_file.write(output)
    success_file.close()
    print("Sketch succeeded. Generated configuration is given above. Output left in " + success_file.name)
    sys.exit(0)

else:
  assert(mode == "optverify")
  optverify_code = sketch_generator.generate_sketch(program_file = program_file,
                   alu_definitions = alu_definitions,
                   stateful_operand_mux_definitions = stateful_operand_mux_definitions, mode = mode,
                   output_mux_definitions = output_mux_definitions)

  # Create file and write sketch_function into it
  sketch_file = open(sketch_name + "_optverify.sk", "w")
  sketch_file.write(optverify_code)
  sketch_file.close()
  print("Sketch file is ", sketch_file.name)

  # Put the rest (holes, hole arguments, constraints, etc.) into a .pickle file.
  pickle_file   = open(sketch_name + ".pickle", "wb")
  pickle.dump(ChipmunkPickle(holes = sketch_generator.holes_,
                             hole_arguments = sketch_generator.hole_arguments_,
                             constraints = sketch_generator.constraints_,
                             num_fields_in_prog = num_fields_in_prog,
                             num_state_vars = num_state_vars),
              pickle_file)
  pickle_file.close()
  print("Pickle file is ", pickle_file.name)

  print("Total number of hole bits is", sketch_generator.total_hole_bits_)
