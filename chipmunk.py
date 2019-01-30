from jinja2 import Template, Environment, FileSystemLoader, StrictUndefined
import pickle
from pathlib import Path
import sys
from   sketch_helpers import SketchGenerator
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

if (len(sys.argv) < 6):
  print("Usage: python3 " + sys.argv[0] + " <program file> <number of pipeline stages> <number of stateless/stateful ALUs per stage> <codegen/optverify> <sketch_name (w/o file extension)>")
  sys.exit(1)
else:
  program_file         = str(sys.argv[1])
  (num_fields_in_prog, num_state_vars) = get_num_pkt_fields_and_state_vars(Path(program_file).read_text())
  num_pipeline_stages  = int(sys.argv[2])
  num_alus_per_stage   = int(sys.argv[3])
  num_phv_containers   = num_alus_per_stage
  assert(num_fields_in_prog <= num_phv_containers)
  mode                 = str(sys.argv[4])
  assert((mode == "codegen") or (mode == "optverify"))
  sketch_name          = str(sys.argv[5])

# Create an object for sketch generation
sketch_generator = SketchGenerator(sketch_name = sketch_name)

operand_mux_definitions = ""
output_mux_definitions  = ""
alu_definitions         = ""
# Generate one mux for inputs: num_phv_containers+1 to 1. The +1 is to support constant/immediate operands.
for i in range(num_pipeline_stages):
  for l in range(num_state_vars):
    operand_mux_definitions += sketch_generator.generate_mux(num_phv_containers, "stateful_operand_mux_" + str(i) + "_" + str(l)) + "\n"

# Output mux for stateful ALUs
for i in range(num_pipeline_stages):
  for k in range(num_phv_containers):
    # Note: We are generating a mux that takes as input all virtual stateful ALUs + corresponding stateless ALU
    # The number of virtual stateful ALUs is more or less than the physical stateful ALUs because it equals the
    # number of state variables in the program_file, but this doesn't affect correctness
    # because we enforce that the total number of active virtual stateful ALUs is within the physical limit.
    # It also doesn't affect the correctness of modeling the output mux because the virtual output mux setting can be
    # translated into the physical output mux setting during post processing.
    output_mux_definitions += sketch_generator.generate_mux(num_state_vars + 1, "output_mux_phv_" + str(i) + "_" + str(k)) + "\n"

# Generate sketch code for alus and immediate operands in each stage
for i in range(num_pipeline_stages):
  for j in range(num_alus_per_stage):
    alu_definitions += sketch_generator.generate_stateless_alu("stateless_alu_" + str(i) + "_" + str(j), ["input" + str(k) for k in range(0, num_phv_containers)]) + "\n"
  for l in range(num_state_vars):
    alu_definitions += sketch_generator.generate_stateful_alu("stateful_alu_" + str(i) + "_" + str(l)) + "\n"

# Ensures each state var is assigned to exactly stateful ALU and vice versa.
sketch_generator.generate_state_allocator(num_pipeline_stages, num_alus_per_stage, num_state_vars)

# Create sketch_file_as_string
env = Environment(loader = FileSystemLoader('./templates'), undefined = StrictUndefined)

if (mode == "codegen"):
  code_gen_template = env.get_template("code_generator.j2")
  code_generator = code_gen_template.render(mode = "codegen",
                                            sketch_name = sketch_name,
                                            program_file = program_file,
                                            num_pipeline_stages = num_pipeline_stages,
                                            num_alus_per_stage = num_alus_per_stage,
                                            num_phv_containers = num_phv_containers,
                                            hole_definitions = sketch_generator.hole_preamble_,
                                            operand_mux_definitions = operand_mux_definitions,
                                            output_mux_definitions = output_mux_definitions,
                                            alu_definitions = alu_definitions,
                                            num_fields_in_prog = num_fields_in_prog,
                                            num_state_vars = num_state_vars,
                                            spec_as_sketch = Path(program_file).read_text(),
                                            all_assertions = sketch_generator.asserts_)

  # Create file and write sketch_harness into it.
  sketch_file = open(sketch_name + "_codegen.sk", "w")
  sketch_file.write(code_generator)
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
  sketch_function_template = env.get_template("sketch_functions.j2")
  sketch_function = sketch_function_template.render(mode = "optverify",
                                                    program_file = program_file,
                                                    num_pipeline_stages = num_pipeline_stages,
                                                    num_alus_per_stage = num_alus_per_stage,
                                                    num_phv_containers = num_phv_containers,
                                                    operand_mux_definitions = operand_mux_definitions,
                                                    output_mux_definitions = output_mux_definitions,
                                                    alu_definitions = alu_definitions,
                                                    num_fields_in_prog = num_fields_in_prog,
                                                    num_state_vars = num_state_vars,
                                                    hole_arguments = sketch_generator.hole_arguments_,
                                                    sketch_name = sketch_name)
  # Create file and write sketch_function into it
  sketch_file = open(sketch_name + "_optverify.sk", "w")
  sketch_file.write(sketch_function)
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
