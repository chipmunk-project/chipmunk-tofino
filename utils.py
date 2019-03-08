"""Utilities for Chipmunk"""

from re import findall


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

def get_hole_dicts(sketch_file):
    """Returns a dictionary from hole names to hole bit sizes given a sketch
    file.
    """
    return {
        name: bits
        for name, bits in findall(r'(\w+)= \?\?\((\d+)\);', sketch_file)
    }
