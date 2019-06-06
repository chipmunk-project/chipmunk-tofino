"""Repeated Solver"""
import argparse
import sys
from pathlib import Path

from chipc.compiler import Compiler
from chipc.utils import compilation_failure
from chipc.utils import compilation_success
from chipc.utils import get_num_pkt_fields
from chipc.utils import get_state_group_info


# Create hole_elimination_assert from hole_assignments
# hole_assignments is in the format {'hole_name':'hole_value'},
# i.e., {'sample1_stateless_alu_0_0_mux1_ctrl': '0'}
def generate_hole_elimination_assert(hole_assignments):
    # The ! is to ensure a hole combination isn't present.
    hole_elimination_string = '!'
    for hole, value in hole_assignments.items():
        hole_elimination_string += '(' + hole + ' == ' + value + ') && '
    hole_elimination_string += '1'
    return [hole_elimination_string]


def set_default_values(pkt_fields, state_vars, num_fields_in_prog,
                       state_group_info):
    """Check if all packet fields and state variables exist in counterexample
    dictionaries, pkt_fields and state_vars. If not, set those missing to 0
    since they don't really matter.
    """
    for i in range(int(num_fields_in_prog)):
        field_name = 'pkt_' + str(i)
        if field_name not in pkt_fields:
            print('Setting value 0 for', field_name)
            pkt_fields[field_name] = 0
    for group_idx, vs in state_group_info.items():
        for var_idx in vs:
            state_var_name = 'state_group_' + group_idx + '_state_' + var_idx
            if state_var_name not in state_vars:
                print('Setting value 0 for', state_var_name)
                state_vars[state_var_name] = 0
    return (pkt_fields, state_vars)


def generate_additional_testcases(hole_assignments, compiler,
                                  num_fields_in_prog, state_group_info, count,
                                  sol_verify_bit):
    """Creates multiple counterexamples from 2 bits
    to sol_verify_bit input ranges."""
    counter_example_definition = ''
    counter_example_assert = ''
    for bits in range(2, sol_verify_bit):
        print('Generating counterexamples of', str(bits), 'bits.')
        (cex_pkt_fields, cex_state_vars) = compiler.counter_example_generator(
            bits, hole_assignments, iter_cnt=count)

        # z3 was not able to find counterexamples for this input range.
        if len(cex_pkt_fields) == 0 and len(cex_state_vars) == 0:
            continue

        pkt_fields, state_vars = set_default_values(
            cex_pkt_fields, cex_state_vars, num_fields_in_prog,
            state_group_info)

        counter_example_definition += '|StateAndPacket| x_' + str(
            count) + '_' + str(bits) + ' = |StateAndPacket|(\n'
        for field_name, value in pkt_fields.items():
            counter_example_definition += field_name + ' = ' + str(
                value + 2**bits) + ',\n'

        for i, (state_var_name, value) in enumerate(state_vars.items()):
            counter_example_definition += state_var_name + ' = ' + str(
                value + 2**bits)
            if i < len(state_vars) - 1:
                counter_example_definition += ',\n'
            else:
                counter_example_definition += ');\n'

        counter_example_assert += 'assert (pipeline(' + 'x_' + str(
            count) + '_' + str(bits) + ')' + ' == ' + 'program(' + 'x_' + str(
                count) + '_' + str(bits) + '));\n'
    return counter_example_definition + counter_example_assert


def main(argv):
    parser = argparse.ArgumentParser(description='Iterative solver.')
    parser.add_argument(
        'program_file', help='Program specification in .sk file')
    parser.add_argument('stateful_alu_file', help='Stateful ALU file to use.')
    parser.add_argument(
        'stateless_alu_file', help='Stateless ALU file to use.')
    parser.add_argument(
        'num_pipeline_stages', type=int, help='Number of pipeline stages')
    parser.add_argument(
        'num_alus_per_stage',
        type=int,
        help='Number of stateless/stateful ALUs per stage')
    parser.add_argument(
        'max_input_bit',
        type=int,
        help='The maximum input value in bits')
    parser.add_argument(
        '--pkt-fields',
        type=int,
        nargs='+',
        help='Packet fields to check correctness')
    parser.add_argument(
        '-p',
        '--parallel',
        action='store_true',
        help='Whether to run multiple smaller sketches in parallel by\
              setting salu_config variables explicitly.')
    parser.add_argument(
        '--parallel-sketch',
        action='store_true',
        help='Whether sketch process internally uses parallelism')
    parser.add_argument(
        '--hole-elimination',
        action='store_true',
        help='If set, use hole elimination mode instead of counterexample '
        'generation mode.'
    )

    args = parser.parse_args(argv[1:])
    # Use program_content to store the program file text rather than using it
    # twice
    program_content = Path(args.program_file).read_text()
    num_fields_in_prog = get_num_pkt_fields(program_content)

    # Get the state vars information
    # TODO: add the max_input_bit into sketch_name
    state_group_info = get_state_group_info(program_content)
    sketch_name = args.program_file.split('/')[-1].split('.')[0] + \
        '_' + args.stateful_alu_file.split('/')[-1].split('.')[0] + \
        '_' + args.stateless_alu_file.split('/')[-1].split('.')[0] + \
        '_' + str(args.num_pipeline_stages) + \
        '_' + str(args.num_alus_per_stage)

    compiler = Compiler(args.program_file, args.stateful_alu_file,
                        args.stateless_alu_file,
                        args.num_pipeline_stages, args.num_alus_per_stage,
                        sketch_name, args.parallel_sketch, args.pkt_fields)

    # Repeatedly run synthesis at 2 bits and verification using all valid ints
    # until either verification succeeds or synthesis fails at 2 bits. Note
    # that the verification with all ints, might not work because sketch only
    # considers positive integers.
    # Synthesis is much faster at a smaller bit width, while verification needs
    # to run at a larger bit width for soundness.
    count = 1
    hole_elimination_assert = []
    additional_testcases = ''
    sol_verify_bit = args.max_input_bit
    while 1:
        print('Iteration #' + str(count))
        (synthesis_ret_code, output, hole_assignments) = \
            compiler.parallel_codegen(
                additional_constraints=hole_elimination_assert,
                additional_testcases=additional_testcases) \
            if args.parallel else \
            compiler.serial_codegen(
            iter_cnt=count,
            additional_constraints=hole_elimination_assert,
            additional_testcases=additional_testcases)

        if synthesis_ret_code == 0:
            print('Synthesis succeeded with 2 bits, proceeding to '
                  'verification.')
            verification_ret_code = compiler.sol_verify(
                hole_assignments, sol_verify_bit, iter_cnt=count)
            if verification_ret_code == 0:
                compilation_success(sketch_name, hole_assignments, output)
                return 0
            else:
                print('Verification failed. Trying again.')
                if args.hole_elimination:
                    hole_elimination_assert += \
                        generate_hole_elimination_assert(
                            hole_assignments)
                else:
                    additional_testcases += generate_additional_testcases(
                        hole_assignments, compiler, num_fields_in_prog,
                        state_group_info, count, sol_verify_bit)
                count = count + 1
                continue
        else:
            # Failed synthesis at 2 bits.
            compilation_failure(sketch_name, output)
            return 1


def run_main():
    sys.exit(main(sys.argv))


if __name__ == '__main__':
    run_main()
