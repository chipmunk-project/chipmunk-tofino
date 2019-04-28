"""Utilities for Chipmunk"""
from re import findall


def get_info_of_state_groups(program):
    """Returns the information of all state vars
    i.e state_and_packet.state_group_1_state_0
    we will get the information (1,0)
    """
    state_group_info = findall(
        r'state_and_packet.state_group_(\d+)_state_(\d+)', program)
    return state_group_info


def get_num_pkt_fields_and_state_groups(program):
    """Returns number of packet fields and state groups.
    Use a regex to scan the program and extract the largest packet field index
    and largest state variable index

    Args:
        program: The program to read

    Returns:
        A tuple of packet field numbers and state variables.
    """
    pkt_fields = [
        int(x) for x in findall(r'state_and_packet.pkt_(\d+)', program)
    ]
    state_groups = [
        int(x) for x in findall(r'state_and_packet.state_group_(\d+)', program)
    ]
    return (max(pkt_fields) + 1, max(state_groups) + 1)


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
        values = findall("" + name + "__" + r"\w+ = (\d+)", sketch)
        assert len(values) == 1, (
            "Unexpected number of assignment statements found for hole %s, "
            "with values %s" % (name, values))
        holes_to_values[name] = values[0]

    return holes_to_values
