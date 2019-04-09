"""Repeated Solver"""
from pathlib import Path
import re
import subprocess
import sys
import argparse

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
    parser = argparse.ArgumentParser(description="Iterative solver.")
    parser.add_argument(
        "program_file", help="Program specification in .sk file")
    parser.add_argument("alu_file", help="ALU file to use.")
    parser.add_argument(
        "num_pipeline_stages", type=int, help="Number of pipeline stages")
    parser.add_argument(
        "num_alus_per_stage",
        type=int,
        help="Number of stateless/stateful ALUs per stage")
    parser.add_argument(
        "--pkt-fields",
        type=int,
        nargs='+',
        help="Packet fields to check correctness")
    parser.add_argument(
        "-p",
        "--parallel",
        action="store_const",
        const="parallel_codegen",
        default="serial_codegen",
        help="Whether to run multiple sketches in parallel.")
    parser.add_argument(
        "--parallel-sketch",
        action="store_true",
        help="Whether sketch process uses parallelism")
    parser.add_argument(
        "--hole-elimination",
        action="store_const",
        const="hole_elimination_mode",
        default="cex_mode",
        help="Whether to iterate by eliminating holes or using counterexamples") 

    args = parser.parse_args(argv[1:])
    (num_fields_in_prog, num_state_groups) = get_num_pkt_fields_and_state_groups(
        Path(args.program_file).read_text())

    sketch_name = args.program_file.split('/')[-1].split('.')[0] + "_" + args.alu_file.split('/')[-1].split('.')[0] + \
                  "_" + str(args.num_pipeline_stages) + "_" + str(args.num_alus_per_stage)
    compiler = Compiler(args.program_file, args.alu_file,
                        args.num_pipeline_stages, args.num_alus_per_stage,
                        sketch_name, args.parallel_sketch, args.pkt_fields)

    # Repeatedly run synthesis at 2 bits and verification at 10 bits until either
    # verification succeeds at 10 bits or synthesis fails at 2 bits. Synthesis is
    # much faster at a smaller bit width, while verification needs to run at a larger
    # bit width for soundness.
    count = 1
    hole_elimination_assert = []
    additional_testcases = ""
    while 1:
        if args.hole_elimination == "hole_elimination_mode":
            (synthesis_ret_code, output, hole_assignments) = \
                compiler.serial_codegen(additional_constraints = hole_elimination_assert) \
                if args.parallel == "serial_codegen" else \
                compiler.parallel_codegen(additional_constraints = hole_elimination_assert)

            hole_elimination_assert = generate_hole_elimination_assert(hole_assignments)
        else:
            assert(args.hole_elimination == "cex_mode")
            (synthesis_ret_code, output, hole_assignments) = \
                compiler.serial_codegen(additional_testcases = additional_testcases) \
                if args.parallel == "serial_codegen" else \
                compiler.parallel_codegen(additional_testcases = additional_testcases)
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
