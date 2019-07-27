"""Repeated Solver"""
import argparse
import sys
from pathlib import Path

from chipc.compiler import Compiler
from chipc.utils import compilation_failure
from chipc.utils import compilation_success
from chipc.utils import get_num_pkt_fields
from chipc.utils import get_state_group_info


def generate_hole_elimination_assert(hole_assignments):
    """Given hole value assignments, {'n_0: 'v_0', 'n_1': 'v_1', ... }, which
    failed to verify for larger input bit ranges, generates a single element
    string list representing the negation of holes all equal to the values.
    This is then passed to sketch file to avoid this specific combination of
    hole value assignments."""
    if len(hole_assignments) == 0:
        return []

    # The ! is to ensure a hole combination isn't present.
    hole_elimination_string = '!('
    # To make it easier to test, sort the hole value assignments using the hole
    # names.
    for idx, (hole, value) in enumerate(
            sorted(hole_assignments.items(), key=lambda x: x[0])):
        hole_elimination_string += '(' + hole + ' == ' + value + ')'
        if idx != len(hole_assignments) - 1:
            hole_elimination_string += ' && '
    hole_elimination_string += ')'
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


def generate_counterexample_asserts(pkt_fields, state_vars, num_fields_in_prog,
                                    state_group_info, count):
    counterexample_defs = ''
    counterexample_asserts = ''

    counterexample_defs += '|StateAndPacket| x_' + str(
        count) + ' = |StateAndPacket|(\n'
    for field_name, value in pkt_fields.items():
        counterexample_defs += field_name + ' = ' + str(
            value) + ',\n'

    for i, (state_var_name, value) in enumerate(state_vars.items()):
        counterexample_defs += state_var_name + ' = ' + str(
            value)
        if i < len(state_vars) - 1:
            counterexample_defs += ',\n'
        else:
            counterexample_defs += ');\n'

    counterexample_asserts += 'assert (pipeline(' + 'x_' + str(
        count) + ')' + ' == ' + 'program(' + 'x_' + str(
            count) + '));\n'
    return counterexample_defs + counterexample_asserts


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
        'constant_set',
        type=str,
        help='The content in the constant_set\
              and the format will be like {0,1,2,3}\
              and we will calculate the number of\
              comma to get the size of it')
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
        help='If set, add addtional assert statements to sketch, so that we \
              would not see the same combination of hole value assignments.'
    )
    parser.add_argument(
        '--synthesized-allocation',
        action='store_true',
        help='If set let sketch allocate state variables otherwise \
              use canonical allocation, i.e, first state variable assigned \
              to first phv container.'
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
                        sketch_name, args.parallel_sketch,
                        args.constant_set,
                        args.synthesized_allocation, args.pkt_fields)

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

        if synthesis_ret_code != 0:
            compilation_failure(sketch_name, output)
            return 1

        print('Synthesis succeeded with 2 bits, proceeding to verification.')
        pkt_fields, state_vars = compiler.verify(
            hole_assignments, sol_verify_bit, iter_cnt=count
        )

        if len(pkt_fields) == 0 and len(state_vars) == 0:
            compilation_success(sketch_name, hole_assignments, output)
            return 0

        print('Verification failed.')

        # NOTE(taegyunkim): There is no harm in using both hole elimination
        # asserts and counterexamples. We want to compare using only hole
        # elimination asserts and only counterexamples.
        if args.hole_elimination:
            hole_elimination_assert += generate_hole_elimination_assert(
                hole_assignments)
            print(hole_elimination_assert)
        else:
            print('Use returned counterexamples', pkt_fields, state_vars)

            pkt_fields, state_vars = set_default_values(
                pkt_fields, state_vars, num_fields_in_prog, state_group_info
            )

            additional_testcases += generate_counterexample_asserts(
                pkt_fields, state_vars, num_fields_in_prog, state_group_info,
                count)

        count += 1


def run_main():
    sys.exit(main(sys.argv))


if __name__ == '__main__':
    run_main()
