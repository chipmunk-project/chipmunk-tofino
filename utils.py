"""Utilities for Chipmunk"""

from re import findall


def get_num_pkt_fields_and_state_vars(program):
    """Returns number of packet fields and state variables.
    Use a regex to scan the program and extract the largest packet field index
    and largest state variable index

    Args:
        program: The program to read

    Returns:
        A tuple of packet field numbers and state variables.
    """
    pkt_fields = len(findall(r'\/\/ state_and_packet.pkt_(\d+) =', program))
    state_vars = len(findall(r'\/\/ state_and_packet.state_(\d+) =', program))

    return (pkt_fields, state_vars)
