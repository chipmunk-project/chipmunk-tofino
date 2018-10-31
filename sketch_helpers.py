# Helper functions to generate sketch code for synthesis
import math

constant_generator = '''
generator int constant() {
  return ??(2);
}
'''

stateless_alu_generator = '''
generator int stateless_alu(int x, int y) {
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

stateful_alu_generator = '''
generator int stateful_alu(ref int s, int y) {
  int opcode = ??(2);
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
'''

def generate_state_allocator(num_pipeline_stages, num_alus_per_stage, num_state_vars):
  state_allocator ="\n  // One bit indicator variable for each combination of stateful ALU slot and state variable\n"
  state_allocator += "  // Note that some stateful ALUs can have more than one slot\n" #TODO: Deal with this case.
  for i in range(num_pipeline_stages):
    for j in range(num_alus_per_stage):
      for l in range(num_state_vars):
        state_allocator += "  bit salu_" + str(i) + "_" + str(j) + "_" + str(l) + " = ??(1);\n"

  state_allocator += "\n  // Any stateful slot has at most one variable assigned to it (sum over l)\n"
  for i in range(num_pipeline_stages):
    for j in range(num_alus_per_stage):
      state_allocator += "  assert(("
      for l in range(num_state_vars):
        state_allocator += "salu_" + str(i) + "_" + str(j) + "_" + str(l) + " + "
      state_allocator = state_allocator[:-2] + ") <= 1);\n"

  state_allocator += "\n  // Any stateful variable is assigned to at most one slot (sum over i and j)\n"
  for l in range(num_state_vars):
    state_allocator += "  assert(("
    for i in range(num_pipeline_stages):
      for j in range(num_alus_per_stage):
        state_allocator += "salu_" + str(i) + "_" + str(j) + "_" + str(l) + " + "
    state_allocator = state_allocator[:-2] + ") <= 1);\n"

  return state_allocator

def generate_phv_allocator(num_phv_containers, num_fields_in_prog):
  phv_allocator ="\n  // One bit indicator variable for each combination of PHV container and packet field\n"
  for k in range(num_phv_containers):
    for l in range(num_fields_in_prog):
      phv_allocator += "  bit phv_" + str(k) + "_" + str(l) + " = ??(1);\n"

  phv_allocator += "\n  // Any container has at most one variable assigned to it (sum over l)\n"
  for k in range(num_phv_containers):
    phv_allocator += "  assert(("
    for l in range(num_fields_in_prog):
      phv_allocator += "phv_" + str(k) + "_" + str(l) + " + "
    phv_allocator = phv_allocator[:-2] + ") <= 1);\n"

  phv_allocator += "\n  // Any packet field is assigned to at most one container (sum over i)\n"
  for l in range(num_fields_in_prog):
    phv_allocator += "  assert(("
    for k in range(num_phv_containers):
      phv_allocator += "phv_" + str(k) + "_" + str(l) + " + "
    phv_allocator = phv_allocator[:-2] + ") <= 1);\n"

  return phv_allocator

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
