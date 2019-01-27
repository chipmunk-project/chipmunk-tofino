from jinja2 import Template
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import sys

# Read contents of file_name into a string
def file_to_str(file_name):
  return Path(file_name).read_text()


def get_holes(hole_file):

if (len(sys.argv) < 4):
  print("Usage: " + sys.argv[0] + " sketch1_name sketch2_name transform_function ")
  sys.exit(1)
else:
  sketch1_name        = str(sys.argv[1])
  sketch1_function    = file_to_str(sketch1_name + ".sk")
  sketch1_holes       = file_to_str(sketch1_name + ".holes")
  sketch1_constraints = file_to_str(sketch1_name + ".constraints")
  sketch2_name        = str(sys.argv[2])
  sketch2_function    = file_to_str(sketch2_name + ".sk")
  sketch2_holes       = file_to_str(sketch2_name + ".holes")
  sketch2_constraints = file_to_str(sketch2_name + ".constraints")
  transform_function  = file_to_str(str(sys.argv[3]))
  env = Environment(loader=FileSystemLoader('./templates'))
  opt_verify_template = env.get_template("opt_verify.j2")
  hole1_arguments     =
  hole2_arguments     =

  opt_verifer         = opt_verify_template.render(sketch1_file_name = sketch1_name + ".sk",
                                                   sketch2_file_name = sketch2_name + ".sk",
                                                   hole1_arguments = ,
                                                   hole2_arguments = ,
                                                   sketch1_holes = ,
                                                   sketch1_asserts = ,
                                                   sketch2_holes = ,
                                                   sketch2_asserts = ,)


