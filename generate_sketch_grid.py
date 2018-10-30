import sys
import math

constant_generator = '''
generator int constant() {
  return ??(2);
}
'''

alu_generator = '''
generator int simple_alu(int x, int y) {
  int opcode = ??(2);
  if (opcode == 0) {
    return x + y;
  } else if (opcode == 1) {
    return x * y;
  } else if (opcode == 2) {
    return x - y;
  } else {
    assert(opcode == 3);
    return x / y;
  }
}
'''

# Sketch code for an n-to-1 selector
# Used for n-to-1 muxes and for compile-time configuration
# (e.g., assigning packet fields to containers in the packet header vector (PHV))
def generate_selector(n, selector_name):
  assert(n > 1)
  num_bits = math.ceil(math.log(n, 2))
  sketch_code = "generator int " + selector_name + "("
  for i in range(0, n):
    sketch_code += "int v" + str(i) + ","
  sketch_code = sketch_code[:-1] + ") {\n"

  sketch_code += "  int opcode = ??(" + str(num_bits) + ");\n"
  sketch_code += "  if (opcode == 0) { return v0; }\n"
  for i in range(1, n):
    sketch_code += "  else if (opcode == " + str(i) + ") { return v" + str(i) + "; } \n"
  sketch_code += "  else { assert(false); }\n"

  sketch_code += "}\n";
  return sketch_code

if (len(sys.argv) < 5):
  print("Usage: python3 " + sys.argv[0] + " <number of packet fields in program> <maximum number of fields in packet> < number of pipeline stages> <number of ALUs per stage> ")
  sys.exit(1)
else:
  num_fields_in_prog   = int(sys.argv[1])
  num_phv_containers   = int(sys.argv[2])
  num_pipeline_stages  = int(sys.argv[3])
  num_alus_per_stage   = int(sys.argv[4])

# Generate one mux to represent the register allocator
# i.e., for each of up to num_phv_containers phv containers, assign a packet field (out of num_fields_in_prog)
sketch_harness = generate_selector(num_fields_in_prog, "phv_allocator") + "\n"

# The code below represents a register de-allocator
# i.e., for each of up to num_fields_in_prog fields in the program, assign a container (out of num_phv_containers)
# TODO: It's optimistic to assume that a de-allocator exists.
# In general, we would expect the final value of a packet field
# to be available in the same PHV container that was allocated to the packet field,
# but this is a bit harder to model in Sketch, but we should fix it soon.
sketch_harness += generate_selector(num_phv_containers, "phv_deallocator") + "\n"

# Generate two muxes, one for inputs: num_phv_containers+1 to 1
# and one for outputs: num_alus_per_stage to 1
sketch_harness += generate_selector(num_phv_containers + 1, "operand_mux") + "\n"
sketch_harness += generate_selector(num_alus_per_stage, "output_mux") + "\n"

# Add sketch code for alu and constants
sketch_harness += alu_generator + "\n" + constant_generator + "\n"

# Function signature
sketch_harness += "harness void main("
for p in range(num_fields_in_prog):
  sketch_harness += "int pkt_" + str(p) + ", "
sketch_harness = sketch_harness[:-2] + ") {\n"

# Generate PHV allocator
sketch_harness += "\n  // PHV allocation\n"
for k in range(num_phv_containers):
  sketch_harness += "  int input_" +  "0"   + "_" + str(k) + " = "
  sketch_harness += " phv_allocator("
  for p in range(num_fields_in_prog):
    sketch_harness += "pkt_" + str(p) + ", "
  sketch_harness = sketch_harness[:-2] + ");\n"

# Generate pipeline stages
for i in range(num_pipeline_stages):
  sketch_harness += "\n  /********* Stage " + str(i) + " *******/\n"
  # set up inputs to each stage
  # we can have num_phv_containers fields in the inputs to each stage
  sketch_harness += "\n  // Inputs\n"
  if (i == 0):
    sketch_harness += "  // PHV allocation already handles setting of inputs for the first stage\n"
  else:
    for k in range(num_phv_containers):
      sketch_harness += "  int input_" + str(i) + "_" + str(k) + " = output_" + str(i-1) + "_" + str(k) + ";\n"

  # Two operands for each ALU in each stage
  sketch_harness += "\n  // Operands\n"
  for j in range(num_alus_per_stage):
    # First operand
    sketch_harness += "  int operand_" + str(i) + "_" + str(j) + "_a ="
    sketch_harness += " operand_mux("
    for k in range(num_phv_containers):
      sketch_harness += "input_" + str(i) + "_" + str(k) + ", "
    sketch_harness += "constant());\n"

    # Second operand
    sketch_harness += "  int operand_" + str(i) + "_" + str(j) + "_b ="
    sketch_harness += " operand_mux("
    for k in range(num_phv_containers):
      sketch_harness += "input_" + str(i) + "_" + str(k) + ", "
    sketch_harness += "constant());\n"

  # ALUs
  sketch_harness += "\n  // ALUs\n"
  for j in range(num_alus_per_stage):
    sketch_harness += "  int destination_" + str(i) + "_" + str(j) + "= simple_alu(operand_" + str(i) + "_" + str(j) + "_a, operand_" + str(i) + "_" + str(j) + "_b);\n"

  # Write outputs
  sketch_harness += "\n  // Outputs\n"
  for k in range(num_phv_containers):
    sketch_harness += "  int output_" + str(i) + "_" + str(k)
    sketch_harness  += "= output_mux("
    for j in range(num_alus_per_stage):
      sketch_harness += "destination_" + str(i) + "_" + str(j) + ", "
    sketch_harness = sketch_harness[:-2] + ");\n"

# Generate PHV de-allocator
sketch_harness += "\n  // PHV de-allocation\n"
for p in range(num_fields_in_prog):
  sketch_harness += "  pkt_" + str(p) + " = "
  sketch_harness += " phv_deallocator("
  for k in range(num_phv_containers):
    sketch_harness += "output_" + str(num_pipeline_stages - 1) + "_" + str(k) + ", "
  sketch_harness = sketch_harness[:-2] + ");\n"

sketch_harness += "}\n"
print(sketch_harness)
