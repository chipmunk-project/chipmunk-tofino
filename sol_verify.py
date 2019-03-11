"""Solution Verifier"""

import subprocess


def sol_verify(original_sketch_file, hole_value_file):
    original_sketch_file_string = open(str(original_sketch_file), "r").read()
    hole_value_file_string = open(str(hole_value_file), "r").read()

    #remove the hole definition in original_sketch_file
    original_sketch_file_string = original_sketch_file_string[
        original_sketch_file_string.rfind('??'):]
    original_sketch_file_string = original_sketch_file_string[
        original_sketch_file_string.find(';') + 1:]

    #remove the redundant code in hole_value_file
    begin_pos = hole_value_file_string.find('int')
    end_pos = hole_value_file_string.rfind(';')
    hole_value_file_string = hole_value_file_string[begin_pos:end_pos + 1]

    sketch_file_with_hole_value = hole_value_file_string + original_sketch_file_string

    # Create file and write sketch_harness into it.
    sketch_file = open(
        original_sketch_file[0:original_sketch_file.find('.')] +
        "_with_hole_value.sk", "w")
    sketch_file.write(sketch_file_with_hole_value)
    sketch_file.close()

    # Call sketch on it
    (ret_code, _) = subprocess.getstatusoutput("sketch --bnd-inbits=10 " +
                                               sketch_file.name)
    return ret_code
