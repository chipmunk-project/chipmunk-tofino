# Helper functions to generate sketch code for synthesis
from jinja2 import Template
from pathlib import Path
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
def generate_stateless_alu(alu_name, potential_operands):
  operand_mux_template   = Template(Path("templates/mux.j2").read_text())
  stateless_alu_template = Template(Path("templates/stateless_alu.j2").read_text())
  stateless_alu = stateless_alu_template.render(potential_operands = potential_operands,
                                                arg_list = ["int " + x for x in potential_operands],
                                                alu_name = alu_name, opcode_hole = alu_name + "_opcode",
                                                immediate_operand_hole = alu_name + "_immediate",
                                                alu_mode_hole = alu_name + "_mode",
                                                mux1 = alu_name + "_mux1", mux2 = alu_name + "_mux2")
  mux_op_1 = generate_mux(len(potential_operands), alu_name + "_mux1")
  mux_op_2 = generate_mux(len(potential_operands), alu_name + "_mux2")
  generate_hole(alu_name + "_opcode", 1)
  generate_hole(alu_name + "_immediate", 2)
  generate_hole(alu_name + "_mode", 2)
  add_assert(alu_name + "_mux1_ctrl <= " + alu_name + "_mux2_ctrl") # symmetry breaking for commutativity
  # add_assert(alu_name +  "_opcode" + "< 2") # Comment out because assert is redundant
  add_assert(alu_name + "_mode" + "< 3")
  return mux_op_1 + mux_op_2 + stateless_alu

# Generate Sketch code for a simple stateful alu (+,-,*,/)
# Takes one state and one packet operand (or immediate operand) as inputs
# Updates the state in place and returns the old value of the state
def generate_stateful_alu(alu_name):
  stateful_alu = '''
int %s(ref int s, int y, %s, %s, %s) {
  int opcode = %s;
  int immediate_operand = %s;
  int alu_mode = %s;
  int old_val = s;
  if (opcode == 0) {
    s = s + (alu_mode == 0 ?  y : immediate_operand);
  } else {
    s = s - (alu_mode == 0 ?  y : immediate_operand);
  }
  return old_val;
}
'''%(alu_name,
     "int " + alu_name + "_opcode_local", "int " + alu_name + "_immediate_local", "int " + alu_name + "_mode_local",
     alu_name + "_opcode_local", alu_name + "_immediate_local", alu_name + "_mode_local")
  generate_hole(alu_name + "_opcode", 1)
  generate_hole(alu_name + "_immediate", 2)
  generate_hole(alu_name + "_mode", 1)
  # add_assert(alu_name +  "_opcode" + "< 2") # Comment out because assert is redundant.
  # add_assert(alu_name + "_mode" + "< 2")    # Comment out because assert is redundant.
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
  operand_mux_template   = Template(Path("templates/mux.j2").read_text())
  mux_code = operand_mux_template.render(mux_name = mux_name,
                                         operand_list = ["input" + str(i) for i in range(0, n)],
                                         arg_list = ["int input" + str(i) for i in range(0, n)],
                                         num_operands = n)
  generate_hole(mux_name + "_ctrl", num_bits)
  add_assert(mux_name + "_ctrl" + "<" + str(n))
  return mux_code
