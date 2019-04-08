"""Repeated Solver"""
from pathlib import Path
import re
import subprocess
import sys

from chipc.compiler import Compiler
from chipc.utils import get_num_pkt_fields_and_state_groups, get_hole_value_assignments

# Create hole_elimination_assert from hole_assignments
# hole_assignments is in the format {'hole_name':'hole_value'},
# i.e., {'sample1_stateless_alu_0_0_mux1_ctrl': '0'}
def generate_hole_elimination_assert(hole_assignments):
    hole_elimination_string = "!" # The ! is to ensure a hole combination isn't present.
    for hole, value in hole_assignments.items():
        hole_elimination_string += "(" + hole + " == " + value + ") && "
    hole_elimination_string += "1"
    return [hole_elimination_string]

# Create multiple counterexamples in the range from 2 bits to 10 bits.
def generate_additional_testcases(hole_assignments, compiler, num_fields_in_prog, num_state_groups, count):
    counter_example_definition = ""
    counter_example_assert = ""
    for bits in range(2, 10):
        (pkt_group, state_group) = compiler.counter_example_generator(bits, hole_assignments)

        # Check if all packet fields are included in pkt_group as part
        # of the counterexample.
        # If not, set those packet fields to a default (0) since they
        # don't matter for the counterexample.
        for i in range(int(num_fields_in_prog)):
            if ("pkt_" + str(i) in [
                    regex_match[0] for regex_match in pkt_group
            ]):
                continue
            else:
                pkt_group.append(("pkt_" + str(i), str(0)))

        # Check if all state vars are included in state_group as part
        # of the counterexample. If not, set those state vars to
        # default (0) since they don't matter for the counterexample.
        for i in range(int(num_state_groups)):
            if ("state_group_0_state_" + str(i) in [
                    regex_match[0] for regex_match in state_group
            ]):
                continue
            else:
                state_group.append(("state_group_0_state_" + str(i),
                                    str(0)))
        counter_example_definition += "|StateAndPacket| x_" + str(
            count) + "_" + str(bits) + " = |StateAndPacket|(\n"
        for group in pkt_group:
            counter_example_definition += group[0] + " = " + str(
                int(group[1]) + 2**bits) + ',\n'
        for i, group in enumerate(state_group):
            counter_example_definition += group[0] + " = " + str(
                int(group[1]) + 2**bits)
            if i < len(state_group) - 1:
                counter_example_definition += ',\n'
            else:
                counter_example_definition += ");\n"
        counter_example_assert += "assert (pipeline(" + "x_" + str(
            count) + "_" + str(
                bits) + ")" + " == " + "program(" + "x_" + str(
                    count) + "_" + str(bits) + "));\n"
    return counter_example_definition + counter_example_assert

def main(argv):
    if len(argv) != 8:
        print("Usage: iterative_solver " +
              " <program file> <alu file> <number of pipeline stages> " +
              "<number of stateless/stateful ALUs per stage> " +
              "<sketch_name (w/o file extension)> <parallel/serial> " +
              "<cex_mode/hole_elimination_mode>")
        return 1

    program_file = str(argv[1])
    (num_fields_in_prog,
     num_state_groups) = get_num_pkt_fields_and_state_groups(
         Path(program_file).read_text())
    alu_file = str(argv[2])
    num_pipeline_stages = int(argv[3])
    num_alus_per_stage = int(argv[4])
    sketch_name = str(argv[5])
    parallel_or_serial = str(argv[6])
    mode = str(argv[7])
    assert mode in ["cex_mode", "hole_elimination_mode"], "Unknown mode " + mode

    # First try to compile with default number (2) of bits.
    compiler = Compiler(program_file, alu_file, num_pipeline_stages,
                        num_alus_per_stage, sketch_name, parallel_or_serial)

    # Repeatedly run synthesis at 2 bits and verification at 10 bits until either
    # verification succeeds at 10 bits or synthesis fails at 2 bits. Synthesis is
    # much faster at a smaller bit width, while verification needs to run at a larger
    # bit width for soundness.
    count = 1
    hole_elimination_assert = []
    additional_testcases = ""
    while 1:
        if mode == "hole_elimination_mode":
            (synthesis_ret_code, output, hole_assignments) = compiler.serial_codegen(
                additional_constraints = hole_elimination_assert)
            hole_elimination_assert = generate_hole_elimination_assert(hole_assignments)
        else:
            assert(mode == "cex_mode")
            (synthesis_ret_code, output, hole_assignments) = \
                compiler.serial_codegen(additional_testcases = additional_testcases)
            additional_testcases    = generate_additional_testcases(hole_assignments, compiler,
                num_fields_in_prog, num_state_groups, count)

        print("Iteration #" + str(count))
        if synthesis_ret_code == 0:
            print("Synthesis succeeded with 2 bits, proceeding to 10-bit verification.")
            verification_ret_code = compiler.sol_verify(hole_assignments, num_input_bits = 10)
            if verification_ret_code == 0:
                print("SUCCESS: Verification succeeded at 10 bits.")
                return 0
            else:
                print("Verification failed at 10 bits. Trying again.")
                count = count + 1
                continue
        else:
            # Failed synthesis at 2 bits.
            print("FAILURE: Failed synthesis at 2 bits.")
            return 1


def run_main():
    sys.exit(main(sys.argv))


if __name__ == "__main__":
    run_main()
