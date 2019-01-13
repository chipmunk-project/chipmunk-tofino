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

def add_assert(assert_predicate):
  add_assert.asserts += "assert(" + assert_predicate + ");\n"
add_assert.asserts = ""

# Generate Sketch code for a simple stateless alu (+,-,*,/) 
def generate_stateless_alu(alu_name):
  stateless_alu = '''
int %s(|MuxSelection| x, |MuxSelection| y) {
  int opcode = %s;
  int immediate_operand = %s;
  if (opcode == 0) {
    assert(x.index <= y.index);
    return {| x.value + y.value | x.value + immediate_operand | immediate_operand |};
  } else {
    assert(opcode == 1); /* Redundant assert */
    return {| x.value - y.value | immediate_operand - y.value | x.value - immediate_operand |};
  }
}
'''%(alu_name, alu_name + "_opcode", alu_name + "_immediate")
  generate_hole(alu_name + "_opcode", 1)
  generate_hole(alu_name + "_immediate", 2)
  add_assert(alu_name +  "_opcode" + "< 2")
  return stateless_alu

# Generate Sketch code for a simple stateful alu (+,-,*,/)
# Takes one state and one packet operand (or immediate operand) as inputs
# Updates the state in place and returns the old value of the state
def generate_stateful_alu(alu_name):
  stateful_alu = '''
int %s(ref int s, |MuxSelection| y) {
  int opcode = %s;
  int immediate_operand = %s;
  int old_val = s;
  if (opcode == 0) {
    s = s + {| y.value | immediate_operand |};
  } else {
    assert(opcode == 1); /* Redundant assert */
    s = s - {| y.value | immediate_operand |};
  }
  return old_val;
}
'''%(alu_name, alu_name + "_opcode", alu_name + "_immediate")
  generate_hole(alu_name + "_opcode", 1)
  generate_hole(alu_name + "_immediate", 2)
  add_assert(alu_name +  "_opcode" + "< 2")
  return stateful_alu

def generate_state_allocator(num_pipeline_stages, num_alus_per_stage, num_state_vars):
  for i in range(num_pipeline_stages):
    for l in range(num_state_vars):
      generate_hole("salu_config_" + str(i) + "_" + str(l), 1)

  for i in range(num_pipeline_stages):
    assert_predicate = "("
    for l in range(num_state_vars):
      assert_predicate += "salu_config_" + str(i) + "_" + str(l) + " + "
    assert_predicate += "0) <= " + str(num_alus_per_stage)
    add_assert(assert_predicate)

  for l in range(num_state_vars):
    assert_predicate = "("
    for i in range(num_pipeline_stages):
      assert_predicate += "salu_config_" + str(i) + "_" + str(l) + " + "
    assert_predicate += "0) <= 1"
    add_assert(assert_predicate)

# Sketch code for an n-to-1 mux
def generate_mux(n, mux_name):
  assert(n > 1)
  num_bits = math.ceil(math.log(n, 2))
  mux_code = "|MuxSelection| " + mux_name + "("
  for i in range(0, n):
    mux_code += "int v" + str(i) + ","
  mux_code = mux_code[:-1] + ") {\n"
  mux_code += "  int mux_ctrl = " + mux_name + "_ctrl;\n"
  mux_code += "  if (mux_ctrl == 0) { return |MuxSelection|(value=v0, index=0); }\n"
  for i in range(1, n):
    mux_code += "  else if (mux_ctrl == " + str(i) + ") { return |MuxSelection|(value=v" + str(i) + ",index=" + str(i) + "); } \n"
  mux_code += "  else { assert(false); /* Redundant assert */ }\n"

  mux_code += "}\n";
  generate_hole(mux_name + "_ctrl", num_bits)
  add_assert(mux_name + "_ctrl" + "<" + str(n))
  return mux_code
