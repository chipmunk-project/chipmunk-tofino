import sys
import subprocess

if (len(sys.argv) != 3):
  print("Usage: python3 " + sys.argv[0] + " <original sketch file> <hole value file>")
  sys.exit(1)
else:
  original_sketch_file = str(sys.argv[1])
  hole_value_file      = str(sys.argv[2])

original_sketch_file_string    = open(str(sys.argv[1]),"r").read()
hole_value_file_string         = open(str(sys.argv[2]),"r").read()

#remove the hole definition in original_sketch_file
original_sketch_file_string = original_sketch_file_string[original_sketch_file_string.rfind('??'):]
original_sketch_file_string = original_sketch_file_string[original_sketch_file_string.find(';')+1:]

#remove the redundant code in hole_value_file
begin_pos = hole_value_file_string.find('int')
end_pos = hole_value_file_string.rfind(';')
hole_value_file_string = hole_value_file_string[begin_pos:end_pos+1]

sketch_file_with_hole_value = hole_value_file_string + original_sketch_file_string

# Create file and write sketch_harness into it.
sketch_file = open(original_sketch_file[0:original_sketch_file.find('.')] + "_with_hole_value.sk", "w")
sketch_file.write(sketch_file_with_hole_value)
sketch_file.close()

# Call sketch on it
(ret_code, output) = subprocess.getstatusoutput("time sketch -V 12 --slv-seed=1 --slv-parallel --bnd-inbits=2 --bnd-int-range=50 " + sketch_file.name)
if (ret_code != 0):
  print("Sketch failed.")
  sys.exit(1)
else:
  print("Sketch succeeded.")
  sys.exit(0)
