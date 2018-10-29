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

def generate_n_to_1_mux(n, prefix):
  assert(n > 1)
  num_bits = math.ceil(math.log(n, 2))
  sketch_code = "generator int " + prefix + "mux"+ str(n) + "("
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

max_fields_in_packet = int(sys.argv[1])
num_pipeline_stages  = int(sys.argv[2])
num_alus_per_stage   = int(sys.argv[3])

# Generate two muxes, one for inputs: max_fields_in_packet+1 to 1
# and one for outputs: num_alus_per_stage to 1
sketch_harness = generate_n_to_1_mux(max_fields_in_packet + 1, "i") + "\n"
sketch_harness += generate_n_to_1_mux(num_alus_per_stage, "o") + "\n"

# Add sketch code for alu and constants
sketch_harness += alu_generator + "\n" + constant_generator + "\n"

# Function signature
# TODO: The function signature needs to be fixed
# because the number of packet fields may not be
# related to max_fields_in_packet
sketch_harness += "harness void main("
for i in range(max_fields_in_packet):
  sketch_harness += "int pkt_" + str(i) + ", "
sketch_harness = sketch_harness[:-2] + ") {\n"

# Generate pipeline stages
for i in range(num_pipeline_stages):
  sketch_harness += "\n  /********* Stage " + str(i) + " *******/\n"
  # set up inputs to each stage
  # we can have max_fields_in_packet fields in the inputs to each stage
  sketch_harness += "\n  // Inputs\n"
  if (i == 0):
    for k in range(max_fields_in_packet):
      sketch_harness += "  int input_" +  "0"   + "_" + str(k) + " = pkt_" + str(k) + ";\n"
      # TODO for now we are assigning input_0_k = pkt_k; In general, this should be programmable.
  else:
    for k in range(max_fields_in_packet):
      sketch_harness += "  int input_" + str(i) + "_" + str(k) + " = output_" + str(i-1) + "_" + str(k) + ";\n"

  # Two operands for each ALU in each stage
  sketch_harness += "\n  // Operands\n"
  for j in range(num_alus_per_stage):
    # First operand
    sketch_harness += "  int operand_" + str(i) + "_" + str(j) + "_a ="
    sketch_harness += "imux" + str(max_fields_in_packet + 1) + "("
    for k in range(max_fields_in_packet):
      sketch_harness += "input_" + str(i) + "_" + str(k) + ", "
    sketch_harness += "constant());\n"

    # Second operand
    sketch_harness += "  int operand_" + str(i) + "_" + str(j) + "_b ="
    sketch_harness += "imux" + str(max_fields_in_packet + 1) + "("
    for k in range(max_fields_in_packet):
      sketch_harness += "input_" + str(i) + "_" + str(k) + ", "
    sketch_harness += "constant());\n"

  # ALUs
  sketch_harness += "\n  // ALUs\n"
  for j in range(num_alus_per_stage):
    sketch_harness += "  int destination_" + str(i) + "_" + str(j) + "= simple_alu(operand_" + str(i) + "_" + str(j) + "_a, operand_" + str(i) + "_" + str(j) + "_b);\n"

  # Write outputs
  sketch_harness += "\n  // Outputs\n"
  for k in range(max_fields_in_packet):
    sketch_harness += "  int output_" + str(i) + "_" + str(k)
    sketch_harness  += "= omux" + str(num_alus_per_stage) + "("
    for j in range(num_alus_per_stage):
      sketch_harness += "destination_" + str(i) + "_" + str(j) + ", "
    sketch_harness = sketch_harness[:-2] + ");\n"

sketch_harness += "}\n"
print(sketch_harness)
