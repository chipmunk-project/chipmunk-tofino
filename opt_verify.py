from jinja2 import Template, Environment, FileSystemLoader, StrictUndefined
from pathlib import Path
import sys
import pickle

# Read contents of file_name into a string
def file_to_str(file_name):
  return Path(file_name).read_text()

if (len(sys.argv) < 6):
  print("Usage: " + sys.argv[0] + " sketch1_name sketch2_name transform_function num_fields_in_prog num_state_vars")
  sys.exit(1)
else:
  sketch1_name        = str(sys.argv[1])
  sketch2_name        = str(sys.argv[2])
  transform_function  = str(sys.argv[3]) # TODO: Fill this up.
  num_fields_in_prog  = int(sys.argv[4])
  num_state_vars      = int(sys.argv[5])
  env = Environment(loader = FileSystemLoader('./templates'), undefined = StrictUndefined)
  opt_verify_template = env.get_template("opt_verify.j2")
  opt_verifer         = opt_verify_template.render(sketch1_name = sketch1_name,
                                                   sketch2_name = sketch2_name,
                                                   sketch1_file_name = sketch1_name + ".sk",
                                                   sketch2_file_name = sketch2_name + ".sk",
                                                   hole1_arguments = pickle.load(open(sketch1_name + ".holes", "rb"))[1],
                                                   hole2_arguments = pickle.load(open(sketch2_name + ".holes", "rb"))[1],
                                                   sketch1_holes = pickle.load(open(sketch1_name + ".holes", "rb"))[0],
                                                   sketch2_holes = pickle.load(open(sketch2_name + ".holes", "rb"))[0],
                                                   sketch1_asserts = pickle.load(open(sketch1_name + ".constraints", "rb")),
                                                   sketch2_asserts = pickle.load(open(sketch2_name + ".constraints", "rb")),
                                                   num_fields_in_prog = num_fields_in_prog,
                                                   num_state_vars  = num_state_vars,
                                                   transform_function = transform_function)
  print(opt_verifer)
