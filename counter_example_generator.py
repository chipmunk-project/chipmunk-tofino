"""counter_example_generator"""

import subprocess
from pathlib import Path
import re


# This program is to return the counterexample within [bits_val,bits_val+1] bits
def counter_example_generator(bits_val, filename, num_fields_in_prog,
                              num_state_vars):

    #add some content to the filename first
    original_sketch_file_string = Path(filename).read_text()
    for i in range(num_fields_in_prog):
        to_be_replaced = 'pkt_' + str(i) + ' = ' + 'pkt_' + str(i)
        original_sketch_file_string = original_sketch_file_string.replace(
            to_be_replaced, to_be_replaced + " + " + str(2**bits_val))
    for i in range(num_fields_in_prog):
        to_be_replaced = 'state_' + str(i) + ' = ' + 'state_' + str(i)
        original_sketch_file_string = original_sketch_file_string.replace(
            to_be_replaced, to_be_replaced + " + " + str(2**bits_val))
    with open("/tmp/counter_example_" + str(bits_val), "w") as result_file:
        result_file.write(original_sketch_file_string)

    #run the sketch first
    (ret_code, output
     ) = subprocess.getstatusoutput("sketch --bnd-inbits=" + str(bits_val) +
                                    " --bnd-int-range=50 " + result_file.name)
    #run the counterexample then
    if (ret_code == 0):
        return ""
    else:
        (ret_code, output) = subprocess.getstatusoutput(
            "sketch -V 3 --debug-cex --bnd-inbits=" + str(bits_val) +
            " --bnd-int-range=50 " + result_file.name)
        return output
