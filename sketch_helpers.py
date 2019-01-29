# Helper functions to generate sketch code for synthesis
from jinja2 import Template
from pathlib import Path
import math
import sys

class Hole:
  def __init__(self, hole_name, max_value):
    self.name = hole_name
    self.max  = max_value

# Read contents of file_name into a string
def file_to_str(file_name):
  return Path(file_name).read_text()

# Sketch Generator class
class SketchGenerator:
  def __init__(self, sketch_name):
    self.sketch_name_ = sketch_name
    self.total_hole_bits_ = 0
    self.hole_names_ = []
    self.hole_preamble_ = ""
    self.hole_arguments_ = []
    self.holes_ = []
    self.asserts_ = ""
    self.constraints_ = []

  # Write all holes to a single hole string for ease of debugging
  def generate_hole(self, hole_name, hole_bit_width):
    self.hole_names_ += [hole_name]
    self.hole_preamble_ += "int " + hole_name + "= ??(" + str(hole_bit_width) + ");\n"
    self.total_hole_bits_ += hole_bit_width
    self.hole_arguments_ += ["int " + hole_name]
    self.holes_ += [Hole(hole_name, 2**hole_bit_width)]
  
  def add_assert(self, assert_predicate):
    self.asserts_ += "assert(" + assert_predicate + ");\n"
    self.constraints_ += [assert_predicate]

  # Generate Sketch code for a simple stateless alu (+,-,*,/) 
  def generate_stateless_alu(self, alu_name, potential_operands):
    operand_mux_template   = Template(Path("templates/mux.j2").read_text())
    stateless_alu_template = Template(Path("templates/stateless_alu.j2").read_text())
    stateless_alu = stateless_alu_template.render(potential_operands = potential_operands,
                                                  arg_list = ["int " + x for x in potential_operands],
                                                  alu_name = alu_name, opcode_hole = alu_name + "_opcode",
                                                  immediate_operand_hole = alu_name + "_immediate",
                                                  alu_mode_hole = alu_name + "_mode",
                                                  mux1 = alu_name + "_mux1", mux2 = alu_name + "_mux2")
    mux_op_1 = self.generate_mux(len(potential_operands), alu_name + "_mux1")
    mux_op_2 = self.generate_mux(len(potential_operands), alu_name + "_mux2")
    self.generate_hole(alu_name + "_opcode", 1)
    self.generate_hole(alu_name + "_immediate", 2)
    self.generate_hole(alu_name + "_mode", 2)
    self.add_assert(alu_name + "_mux1_ctrl <= " + alu_name + "_mux2_ctrl") # symmetry breaking for commutativity
    # add_assert(alu_name +  "_opcode" + "< 2") # Comment out because assert is redundant
    self.add_assert(alu_name + "_mode" + " < 3")
    return mux_op_1 + mux_op_2 + stateless_alu
  
  # Generate Sketch code for a simple stateful alu (+,-,*,/)
  # Takes one state and one packet operand (or immediate operand) as inputs
  # Updates the state in place and returns the old value of the state
  def generate_stateful_alu(self, alu_name):
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
    self.generate_hole(alu_name + "_opcode", 1)
    self.generate_hole(alu_name + "_immediate", 2)
    self.generate_hole(alu_name + "_mode", 1)
    # add_assert(alu_name +  "_opcode" + "< 2") # Comment out because assert is redundant.
    # add_assert(alu_name + "_mode" + "< 2")    # Comment out because assert is redundant.
    return stateful_alu
  
  def generate_state_allocator(self, num_pipeline_stages, num_alus_per_stage, num_state_vars):
    for i in range(num_pipeline_stages):
      for l in range(num_state_vars):
        self.generate_hole("salu_config_" + str(i) + "_" + str(l), 1)
  
    for i in range(num_pipeline_stages):
      assert_predicate = "("
      for l in range(num_state_vars):
        assert_predicate += "salu_config_" + str(i) + "_" + str(l) + " + "
      assert_predicate += "0) <= " + str(num_alus_per_stage)
      self.add_assert(assert_predicate)
  
    for l in range(num_state_vars):
      assert_predicate = "("
      for i in range(num_pipeline_stages):
        assert_predicate += "salu_config_" + str(i) + "_" + str(l) + " + "
      assert_predicate += "0) <= 1"
      self.add_assert(assert_predicate)
  
  # Sketch code for an n-to-1 mux
  def generate_mux(self, n, mux_name):
    assert(n > 1)
    num_bits = math.ceil(math.log(n, 2))
    operand_mux_template   = Template(Path("templates/mux.j2").read_text())
    mux_code = operand_mux_template.render(mux_name = mux_name,
                                           operand_list = ["input" + str(i) for i in range(0, n)],
                                           arg_list = ["int input" + str(i) for i in range(0, n)],
                                           num_operands = n)
    self.generate_hole(mux_name + "_ctrl", num_bits)
    self.add_assert(mux_name + "_ctrl" + " < " + str(n))
    return mux_code
