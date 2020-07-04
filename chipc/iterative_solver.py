"""Repeated Solver"""
import argparse
import sys
from pathlib import Path

from ordered_set import OrderedSet

from chipc.compiler import Compiler
from chipc.utils import compilation_failure
from chipc.utils import compilation_success
from chipc.utils import get_num_pkt_fields
from chipc.utils import get_state_group_info


def print_set(constant_set):
    ret_str = 'Final constant set is: '
    for i in range(len(constant_set) - 1):
        ret_str += constant_set[i] + ','
    ret_str += constant_set[len(constant_set) - 1]
    print(ret_str)


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
                                    state_group_info, count,
                                    output_packet_fields,
                                    state_group_to_check, group_size):
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

    if output_packet_fields is None and state_group_to_check is None:
        counterexample_asserts += 'assert (pipeline(' + 'x_' + str(
            count) + ')' + ' == ' + 'program(' + 'x_' + str(
                count) + '));\n'
    elif output_packet_fields is not None and state_group_to_check is None:
        # If our spec only cares about specific packet fields,
        # the counterexample generated should also care about
        # the same packet fields
        # For example, we only care about pkt_0 then the counterexample
        # assert should be assert(pipeline(x_1).pkt_0 == program(x_1).pkt_0)

        # Same case for stateful_groups except we should care about the size
        # of state group
        # For example, we only care about the state_group_0 with the size
        # of this group to be 2, then the counterexample assert should be
        # assert(pipeline(x_1).state_group_0_state_0 ==
        # program(x_1).state_group_0_state_0)
        # assert(pipeline(x_1).state_group_0_state_1 ==
        # program(x_1).state_group_0_state_1)
        for i in range(len(output_packet_fields)):
            counterexample_asserts += 'assert (pipeline(' + 'x_' + str(
                count) + ').pkt_' + str(output_packet_fields[i]) + \
                ' == ' + 'program(' + 'x_' + str(
                count) + ').pkt_' + str(output_packet_fields[i]) + ');\n'
    elif output_packet_fields is not None and state_group_to_check is not None:
        # counterexample for packet fields
        for i in range(len(output_packet_fields)):
            counterexample_asserts += 'assert (pipeline(' + 'x_' + str(
                count) + ').pkt_' + str(output_packet_fields[i]) + \
                ' == ' + 'program(' + 'x_' + str(
                count) + ').pkt_' + str(output_packet_fields[i]) + ');\n'
        # counterexample for stateful groups
        for i in range(len(state_group_to_check)):
            for j in range(group_size):
                counterexample_asserts += 'assert (pipeline(' + 'x_' + str(
                    count) + ').state_group_' + \
                    str(state_group_to_check[i]) + \
                    '_state_' + str(j) + ' == ' + 'program(' + 'x_' + str(
                    count) + ').state_group_' + \
                    str(state_group_to_check[i]) + '_state_' + str(j) + ');\n'
    else:
        assert output_packet_fields is None
        assert state_group_to_check is not None
        for i in range(len(state_group_to_check)):
            for j in range(group_size):
                counterexample_asserts += 'assert (pipeline(' + 'x_' + str(
                    count) + ').state_group_' + \
                    str(state_group_to_check[i]) + \
                    '_state_' + str(j) + ' == ' + 'program(' + 'x_' + str(
                    count) + ').state_group_' + str(state_group_to_check[i]) +\
                    '_state_' + str(j) + ');\n'

    return counterexample_defs + counterexample_asserts


def main(argv):
    parser = argparse.ArgumentParser(description='Iterative solver.')
    parser.add_argument(
        'spec_filename', help='Program specification in .sk file')
    parser.add_argument('stateful_alu_filename',
                        help='Stateful ALU file to use.')
    parser.add_argument(
        'stateless_alu_filename', help='Stateless ALU file to use.')
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
              and the format will be like 0,1,2,3\
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
        '--state-groups',
        type=int,
        nargs='+',
        help='State groups to check correctness')
    parser.add_argument(
        '--input-packet',
        type=int,
        nargs='+',
        help='This is intended to provide user with choice\
                to pick up the packet fields that will \
                influence the packet fields/states we\
                want to check correctness for to feed into chipmunk.\
                For example, in example_specs/blue_decrease.sk, \
                packet field pkt_1 only depends on pkt_0, \
                so we can specify --input-packet=0 when we \
                set - -pkt-fields=1.')
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
    parser.add_argument(
        '--target-tofino',
        action='store_true',
        help='If set, use the push mode instead of pull mode to update PHVs\
              from stateful ALUs.'
    )

    args = parser.parse_args(argv[1:])
    # Use program_content to store the program file text rather than using it
    # twice
    program_content = Path(args.spec_filename).read_text()
    num_fields_in_prog = get_num_pkt_fields(program_content)

    # Get the state vars information
    # TODO: add the max_input_bit into sketch_name
    state_group_info = get_state_group_info(program_content)

    # record the number of state groups in the program
    # which is equal to the num of stateful ALU per stage
    # if no member in args.state_groups and args.pkt_fields
    # or equal to 0 if only members in args.pkt_fields
    # or equal to the size of args.state_groups
    if not args.state_groups and not args.pkt_fields:
        state_group_num = len(get_state_group_info(program_content))
    elif not args.state_groups and args.pkt_fields:
        state_group_num = 0
    else:
        state_group_num = len(args.state_groups)

    sketch_name = args.spec_filename.split('/')[-1].split('.')[0] + \
        '_' + args.stateful_alu_filename.split('/')[-1].split('.')[0] + \
        '_' + args.stateless_alu_filename.split('/')[-1].split('.')[0] + \
        '_' + str(args.num_pipeline_stages) + \
        '_' + str(args.num_alus_per_stage)

    # Get how many members in each state group
    # state_group_info is OrderedDict which stores the num of state group and
    # the how many stateful vars in each state group
    # state_group_info[item] specifies the
    # num of stateful vars in each state group
    # In our example, each state group has the same size, so we only pick up
    # one of them to get the group size
    # For example,
    # if state_group_info = OrderedDict([('0', OrderedSet(['0', '1']))])
    # state_group_info[item] = OrderedSet(['0', '1'])
    # group_size = 2
    for item in state_group_info:
        group_size = len(state_group_info[item])
        break

    # Use OrderedSet here for deterministic compilation results. We can also
    # use built-in dict() for Python versions 3.6 and later, as it's inherently
    # ordered.
    constant_set = OrderedSet(args.constant_set.split(','))

    compiler = Compiler(args.spec_filename, args.stateful_alu_filename,
                        args.stateless_alu_filename,
                        args.num_pipeline_stages, args.num_alus_per_stage,
                        sketch_name, args.parallel_sketch,
                        constant_set, group_size,
                        args.synthesized_allocation,
                        args.pkt_fields, args.state_groups,
                        args.input_packet, args.target_tofino)
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
            if args.target_tofino:
                compiler.compile_to_tofino(hole_assignments)
            print_set(constant_set)
            print('Using', args.num_alus_per_stage, 'stateless ALUs per stage')
            print('Using', state_group_num, 'stateful ALUs per stage')
            print('Synthesis succeeded with ' + str(args.num_pipeline_stages) +
                  ' stages and ' +
                  str(state_group_num + args.num_alus_per_stage) +
                  ' ALUs per stage')
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

            # compiler.constant_set will be in the form "0,1,2,3"

            # Get the value of counterexample and add them into constant_set
            for _, value in pkt_fields.items():
                value_str = str(value)
                constant_set.add(value_str)
            for _, value in state_vars.items():
                value_str = str(value)
                constant_set.add(value_str)

            # Print the updated constant_array just for debugging
            print('updated constant array', constant_set)

            # Add constant set to compiler for next synthesis.
            compiler.update_constants_for_synthesis(constant_set)

            pkt_fields, state_vars = set_default_values(
                pkt_fields, state_vars, num_fields_in_prog, state_group_info
            )

            additional_testcases += generate_counterexample_asserts(
                pkt_fields, state_vars, num_fields_in_prog, state_group_info,
                count, args.pkt_fields, args.state_groups, group_size)

        count += 1


def run_main():
    sys.exit(main(sys.argv))


if __name__ == '__main__':
    run_main()
