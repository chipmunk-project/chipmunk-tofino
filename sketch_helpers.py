# Helper functions to generate sketch code for synthesis
import math
import sys

# Write all holes to a single hole string for ease of debugging
def generate_hole(hole_name, hole_bit_width):
  generate_hole.hole_names += [hole_name]
  generate_hole.hole_preamble += "int " + hole_name + "= ??(" + str(hole_bit_width) + ");\n"
  generate_hole.total_hole_bits += hole_bit_width
generate_hole.total_hole_bits = 0
generate_hole.hole_names = []
generate_hole.hole_preamble = ""

# Generate holes corresponding to immediate operands for instruction units
def generate_immediate_operand(immediate_operand_name):
  generate_hole(immediate_operand_name, 2);

# Generate Sketch code for a simple stateless alu (+,-,*,/) 
def generate_stateless_alu(alu_name):
  stateless_alu = '''
int %s(int x, int y) {
  assert(y != 0);
  int opcode = %s;
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
'''%(alu_name, alu_name + "_opcode")
  generate_hole(alu_name + "_opcode", 2)
  return stateless_alu

# Generate Sketch code for a simple stateful alu (+,-,*,/)
# Takes one state and one packet operand (or immediate operand) as inputs
# Updates the state in place and returns the old value of the state
def generate_stateful_alu(alu_name):
  stateful_alu = '''
int %s(ref int s, int y) {
  assert(y != 0);
  int opcode = %s;
  int old_val = s;
  if (opcode == 0) {
    s = s + y;
  } else if (opcode == 1) {
    s = s * y;
  } else if (opcode == 2) {
    s = s - y;
  } else {
    assert(opcode == 3);
    s = s / y;
  }
  return old_val;
}
'''%(alu_name, alu_name + "_opcode")
  generate_hole(alu_name + "_opcode", 2)
  return stateful_alu

def generate_stateful_config(num_pipeline_stages, num_alus_per_stage, num_state_vars):
  stateful_config ="\n// One bit indicator variable for each combination of pipeline stage and state variable\n"
  stateful_config += "// Note that some stateful ALUs can have more than one slot (not dealt with yet)\n"
  #TODO: Deal with the above case.
  stateful_config += "// See beginning of file for actual holes.\n"
  for i in range(num_pipeline_stages):
    for l in range(num_state_vars):
      generate_hole("salu_config_" + str(i) + "_" + str(l), 1)
  return stateful_config

def generate_state_allocator(num_pipeline_stages, num_alus_per_stage, num_state_vars):
  state_allocator = "\n  // Any stage has at most num_alus_per_stage variables assigned to it (sum over l)\n"
  for i in range(num_pipeline_stages):
    state_allocator += "  assert(("
    for l in range(num_state_vars):
      state_allocator += "salu_config_" + str(i) + "_" + str(l) + " + "
    state_allocator = state_allocator[:-2] + ") <= " + str(num_alus_per_stage) + ");\n"

  state_allocator += "\n  // Any stateful variable is assigned to at most one stage (sum over i)\n"
  for l in range(num_state_vars):
    state_allocator += "  assert(("
    for i in range(num_pipeline_stages):
      state_allocator += "salu_config_" + str(i) + "_" + str(l) + " + "
    state_allocator = state_allocator[:-2] + ") <= 1);\n"

  return state_allocator

# Sketch code for an n-to-1 mux
def generate_mux(n, mux_name):
  assert(n > 1)
  num_bits = math.ceil(math.log(n, 2))
  mux_code = "int " + mux_name + "("
  for i in range(0, n):
    mux_code += "int v" + str(i) + ","
  mux_code = mux_code[:-1] + ") {\n"

  mux_code += "  int mux_ctrl = " + mux_name + "_ctrl;\n"
  mux_code += "  if (mux_ctrl == 0) { return v0; }\n"
  for i in range(1, n):
    mux_code += "  else if (mux_ctrl == " + str(i) + ") { return v" + str(i) + "; } \n"
  mux_code += "  else { assert(false); }\n"

  mux_code += "}\n";
  generate_hole(mux_name + "_ctrl", num_bits)
  return mux_code
