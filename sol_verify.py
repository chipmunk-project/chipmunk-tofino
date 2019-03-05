"""Solution Verifier"""


import sys
import subprocess
from pathlib import Path

if (len(sys.argv) != 3):
    print("Usage: python3 " + sys.argv[0] +
          " <original sketch file> <hole value file>")
    sys.exit(1)

original_sketch_file = str(sys.argv[1])
hole_value_file = str(sys.argv[2])

original_sketch_file_string = Path(original_sketch_file).read_text()
hole_value_file_string = Path(hole_value_file).read_text()

# Remove the hole definition in original_sketch_file.
original_sketch_file_string = original_sketch_file_string[
    original_sketch_file_string.rfind('??'):]
original_sketch_file_string = original_sketch_file_string[
    original_sketch_file_string.find(';') + 1:]

# Remove the redundant code in hole_value_file.
begin_pos = hole_value_file_string.find('int')
end_pos = hole_value_file_string.rfind(';')
hole_value_file_string = hole_value_file_string[begin_pos:end_pos + 1]

sketch_file_with_hole_value = hole_value_file_string + original_sketch_file_string

# Create file and write sketch_harness into it.
sketch_file_name = original_sketch_file[0:original_sketch_file.find('.')] + \
        "_with_hole_value.sk"
with open(sketch_file_name, "w") as sketch_file:
    sketch_file.write(sketch_file_with_hole_value)

# Call sketch on it.
(ret_code, output) = subprocess.getstatusoutput("sketch --bnd-inbits=10 " +
                                                sketch_file_name)
if (ret_code != 0):
    print("Sketch failed.")
    sys.exit(1)
else:
    print("Sketch succeeded.")
    sys.exit(0)
