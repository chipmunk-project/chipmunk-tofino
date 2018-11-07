import sys
import math
import sketch_helpers
# TODO: Fix this. Need a more seamless way of specifying the spec.
import spec_program

# Convention for indices:
# i : pipeline stage
# j : ALU within pipeline stage
# k : PHV container within pipeline stage
# l : packet field or state variable from program

if (len(sys.argv) < 5):
  print("Usage: python3 " + sys.argv[0] + " <number of packet fields in program> <number of state variables in program> <number of pipeline stages> <number of stateless/stateful ALUs per stage> ")
  sys.exit(1)
else:
  num_fields_in_prog   = int(sys.argv[1])
  num_state_vars       = int(sys.argv[2])
  num_pipeline_stages  = int(sys.argv[3])
  num_alus_per_stage   = int(sys.argv[4])
  num_phv_containers   = 2 * num_alus_per_stage

# Generate one mux for inputs: num_phv_containers+1 to 1. The +1 is to support constant/immediate operands.
sketch_harness =  "\n// Operand muxes for each ALU in each stage\n"
sketch_harness += "// Total of num_pipeline_stages*num_alus_per_stage*3 (num_phv_containers + 1)-to-1 muxes\n"
for i in range(num_pipeline_stages):
  for j in range(num_alus_per_stage):
    sketch_harness += sketch_helpers.generate_mux(num_phv_containers + 1, "stateless_operand_mux_a_" + str(i) + "_" + str(j)) + "\n"
    sketch_harness += sketch_helpers.generate_mux(num_phv_containers + 1, "stateless_operand_mux_b_" + str(i) + "_" + str(j)) + "\n"
    sketch_harness += sketch_helpers.generate_mux(num_phv_containers + 1, "stateful_operand_mux_" + str(i) + "_" + str(j)) + "\n"

# Generate sketch code for alus and immediate operands in each stage
sketch_harness += "\n// Sketch definition for ALUs and immediate operands\n"
for i in range(num_pipeline_stages):
  for j in range(num_alus_per_stage):
    sketch_harness += "" + \
                  sketch_helpers.generate_stateless_alu("stateless_alu_" + str(i) + "_" + str(j)) + "\n" + \
                  sketch_helpers.generate_stateful_alu("stateful_alu_" + str(i) + "_" + str(j)) + "\n" + \
                  sketch_helpers.generate_immediate_operand("stateless_immediate_" + str(i) + "_" + str(j) + "_a") + "\n" + \
                  sketch_helpers.generate_immediate_operand("stateless_immediate_" + str(i) + "_" + str(j) + "_b") + "\n" + \
                  sketch_helpers.generate_immediate_operand("stateful_immediate_" + str(i) + "_" + str(j)) + "\n"

# Add sketch code for StateAndPacket data type
# This is a struct consisting of all packet and state variables
sketch_harness += "\n// Data type for holding result from spec and implementation\n"
sketch_harness += "struct StateAndPacket {\n"
for p in range(num_fields_in_prog):
  sketch_harness += "  int pkt_" + str(p) + ";\n"
for s in range(num_state_vars):
  sketch_harness += "  int state_" + str(s) + ";\n"
sketch_harness += "}\n"

# Generate PHV configuration holes
sketch_harness += "\n// Sketch holes corresponding to PHV configuration indicator variables\n"
sketch_harness += sketch_helpers.generate_phv_config(num_phv_containers, num_fields_in_prog)

# Generate stateful ALU configuraton holes
sketch_harness += "\n// Sketch holes corresponding to stateful configuration indicator variables\n"
sketch_harness += sketch_helpers.generate_stateful_config(num_pipeline_stages, num_alus_per_stage, num_state_vars)

# Add code for dummy spec program
sketch_harness += "\n// Dummy spec program; TODO: Pass this on cmdline\n"
sketch_harness += spec_program.spec_program

# Function signature that includes both packet fields and state variables
# belonging to this particular packet transaction
sketch_harness += "|StateAndPacket| pipeline(|StateAndPacket| state_and_packet) implements program {\n"

# Generate PHV containers
sketch_harness += "\n  // One variable for each container in the PHV\n"
sketch_harness += "  // This will be allocated to a packet field from the program using indicator variables.\n"
for k in range(num_phv_containers):
  sketch_harness += "  int input_" +  "0"   + "_" + str(k) + ";\n"

# Generate PHV allocator
sketch_harness += sketch_helpers.generate_phv_allocator(num_phv_containers, num_fields_in_prog)

# Generate stateful operands
sketch_harness += "\n  // One variable for each stateful ALU's state operand\n"
sketch_harness += "  // This will be allocated to a state variable from the program using indicator variables.\n"
for i in range(num_pipeline_stages):
  for j in range(num_alus_per_stage):
    sketch_harness += "  int state_operand_salu_" + str(i) + "_" + str(j) + ";\n"

# Generate state allocator
sketch_harness += sketch_helpers.generate_state_allocator(num_pipeline_stages, num_alus_per_stage, num_state_vars)

# Generate pipeline stages
for i in range(num_pipeline_stages):
  sketch_harness += "\n  /********* Stage " + str(i) + " *******/\n"
  # set up inputs to each stage
  # we can have num_phv_containers fields in the inputs to each stage
  sketch_harness += "\n  // Inputs\n"
  if (i == 0):
    # Read packet fields into PHV
    sketch_harness += "  // Read each PHV container from appropriate packet field based on PHV allocation\n"
    for k in range(num_phv_containers):
      for l in range(num_fields_in_prog):
        if (l == 0):
          sketch_harness += "  if (phv_" + str(k) + "_" + str(l) + " == 1) { input_0_" + str(k) + " = state_and_packet.pkt_" + str(l) + ";}\n"
        else:
          sketch_harness += "  else if (phv_" + str(k) + "_" + str(l) + " == 1) { input_0_" + str(k) + " = state_and_packet.pkt_" + str(l) + ";}\n"

  else:
    # Read previous stage's outputs into this one.
    sketch_harness += "  // Input of this stage is the output of the previous one\n"
    for k in range(num_phv_containers):
      sketch_harness += "  int input_" + str(i) + "_" + str(k) + " = output_" + str(i-1) + "_" + str(k) + ";\n"

  # Two operands for each stateless ALU in each stage
  sketch_harness += "\n  // Stateless operands\n"
  for j in range(num_alus_per_stage):
    # First operand
    sketch_harness += "  int operand_" + str(i) + "_" + str(j) + "_a ="
    sketch_harness += " stateless_operand_mux_a_" + str(i) + "_" + str(j) + "("
    for k in range(num_phv_containers):
      sketch_harness += "input_" + str(i) + "_" + str(k) + ", "
    sketch_harness += "stateless_immediate_" + str(i) + "_" + str(j) + "_a());\n"

    # Second operand
    sketch_harness += "  int operand_" + str(i) + "_" + str(j) + "_b ="
    sketch_harness += " stateless_operand_mux_b_" + str(i) + "_" + str(j) + "("
    for k in range(num_phv_containers):
      sketch_harness += "input_" + str(i) + "_" + str(k) + ", "
    sketch_harness += "stateless_immediate_" + str(i) + "_" + str(j) + "_b());\n"

  # Stateless ALUs
  sketch_harness += "\n  // Stateless ALUs\n"
  for j in range(num_alus_per_stage):
    sketch_harness += "  int destination_" + str(i) + "_" + str(j) + "= stateless_alu_" + str(i) + "_" + str(j) + "(operand_" + str(i) + "_" + str(j) + "_a, operand_" + str(i) + "_" + str(j) + "_b);\n"

  # One packet operand for each stateful ALU in each stage
  sketch_harness += "\n  // Stateful operands\n"
  for j in range(num_alus_per_stage):
    sketch_harness += "  int packet_operand_salu" + str(i) + "_" + str(j) + " ="
    sketch_harness += " stateful_operand_mux_" + str(i) + "_" + str(j) + "("
    for k in range(num_phv_containers):
      sketch_harness += "input_" + str(i) + "_" + str(k) + ", "
    sketch_harness += "stateful_immediate_" + str(i) + "_" + str(j) + "());\n"

  # Read state
  sketch_harness += "\n  // Read stateful ALU slots from allocated state variables\n"
  for j in range(num_alus_per_stage):
    for l in range(num_state_vars):
      if (l == 0):
        sketch_harness += "  if (salu_" + str(i) + "_" + str(j) + "_" + str(l) + " == 1) { state_operand_salu_" + str(i) + "_" + str(j) + " = state_and_packet.state_" + str(l) + ";}\n"
      else:
        sketch_harness += "  else if (salu_" + str(i) + "_" + str(j) + "_" + str(l) + " == 1) { state_operand_salu_" + str(i) + "_" + str(j) + " = state_and_packet.state_" + str(l) + ";}\n"

  # Stateful ALUs
  sketch_harness += "\n  // Stateful ALUs\n"
  for j in range(num_alus_per_stage):
    sketch_harness += "  int old_state_" + str(i) + "_" + str(j) + "= stateful_alu_" + str(i) + "_" + str(j) + "(state_operand_salu_" + str(i) + "_" + str(j) + ", packet_operand_salu" + str(i) + "_" + str(j) + ");\n"

  # Write packet outputs
  sketch_harness += "\n  // Outputs\n"
  assert(num_phv_containers == 2 * num_alus_per_stage)
  for k in range(num_phv_containers):
    sketch_harness += "  int output_" + str(i) + "_" + str(k)
    if (k < num_alus_per_stage):
      sketch_harness += "destination_" + str(i) + "_" + str(k) + ";\n"
    else:
      sketch_harness += "old_state_" + str(i) + "_" + str(k-num_alus_per_stage) + ";\n"

  # Write state
  for k in range(num_state_vars):
    sketch_harness += "\n  // Write state_" + str(k) + "\n"
    for j in range(num_alus_per_stage):
      if (j == 0):
        sketch_harness += "  if (salu_" + str(i) + "_" + str(j) + "_" + str(k) + " == 1) { state_and_packet.state_" + str(k) + " = " + "state_operand_salu_" + str(i) + "_" + str(j) + ";}\n"
      else:
        sketch_harness += "  else if (salu_" + str(i) + "_" + str(j) + "_" + str(k) + " == 1) { state_and_packet.state_" + str(k) + " = " + "state_operand_salu_" + str(i) + "_" + str(j) + ";}\n"

# Write back PHV containers into packet fields
for l in range(num_fields_in_prog):
  sketch_harness += "\n  // Write pkt_" + str(l) + "\n"
  for k in range(num_phv_containers):
    if (k == 0):
      sketch_harness += "  if (phv_" + str(k) + "_" + str(l) + " == 1) { state_and_packet.pkt_" + str(l) + " = " + "output_" + str(num_pipeline_stages - 1) + "_" + str(k) + ";}\n"
    else:
      sketch_harness += "  else if (phv_" + str(k) + "_" + str(l) + " == 1) { state_and_packet.pkt_" + str(l) + " = " + "output_" + str(num_pipeline_stages - 1) + "_" + str(k) + ";}\n"

# Return updated packet and state
sketch_harness += "\n  // Return updated packet fields and state variables\n"
sketch_harness += "  return state_and_packet;\n"
sketch_harness += "}\n"

print(sketch_harness)
print("Total number of holes is ", sketch_helpers.generate_hole_function.num_holes, file = sys.stderr)
