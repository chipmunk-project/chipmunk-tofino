"""Utilities for Chipmunk"""
from collections import defaultdict
from pathlib import Path
from re import findall


def get_state_group_info(program):
    """Returns a dictionary from state group indices to set of state variables
    indices.
    For state_group_0_state_1, the dict will have an entry {0: set(1)}"""

    state_group_info = defaultdict(set)
    for i, j in findall(
            r'state_and_packet.state_group_(\d+)_state_(\d+)', program):
        state_group_info[i].add(j)

    return state_group_info


def get_num_pkt_fields(program):
    """Returns number of packet fields in the program.
    If this returns n, packet field indices are from 0 to n-1.
    """
    pkt_fields = set()
    for x in findall(r'state_and_packet.pkt_(\d+)', program):
        pkt_fields.add(int(x))

    return len(pkt_fields)


def get_hole_dicts(sketch):
    """Returns a dictionary from hole names to hole bit sizes given a sketch.
    """
    return {
        name: bits
        for name, bits in findall(r'(\w+)= \?\?\((\d+)\);', sketch)
    }


def get_hole_value_assignments(hole_names, sketch):
    """Returns a dictionary from hole names to hole value assignments given a
    list of hole names and a completed sketch.
    """

    holes_to_values = {}

    for name in hole_names:
        values = findall('' + name + '__' + r'\w+ = (\d+)', sketch)
        assert len(values) == 1, (
            'Unexpected number of assignment statements found for hole %s, '
            'with values %s' % (name, values))
        holes_to_values[name] = values[0]

    return holes_to_values


def compilation_success(sketch_name, hole_assignments, output):
    print('Compilation succeeded. Hole value assignments are following:')
    for hole, value in hole_assignments.items():
        print('int', hole, '=', value)
    p = Path(sketch_name + '.success')
    p.write_text(output)
    print('Output left in', p.name)


def compilation_failure(sketch_name, output):
    print('Compilation failed.')
    p = Path(sketch_name + '.errors')
    p.write_text(output)
    print('Output left in', p.name)
