from jinja2 import Template, Environment, FileSystemLoader, StrictUndefined
from pathlib import Path
from chipmunk_pickle import ChipmunkPickle
import sys
import pickle
import subprocess


# Read contents of file_name into a string
def file_to_str(file_name):
    return Path(file_name).read_text()


if (len(sys.argv) < 4):
    print("Usage: " + sys.argv[0] +
          " sketch1_name sketch2_name transform_file")
    sys.exit(1)
else:
    sketch1_name = str(sys.argv[1])
    sketch2_name = str(sys.argv[2])
    transform_file = str(sys.argv[3])
    env = Environment(
        loader=FileSystemLoader('./templates'), undefined=StrictUndefined)
    assert (pickle.load(open(
        sketch1_name + ".pickle", "rb")).num_fields_in_prog_ == pickle.load(
            open(sketch2_name + ".pickle", "rb")).num_fields_in_prog_)
    assert (pickle.load(open(
        sketch1_name + ".pickle", "rb")).num_state_vars_ == pickle.load(
            open(sketch2_name + ".pickle", "rb")).num_state_vars_)
    num_fields_in_prog = pickle.load(open(sketch1_name + ".pickle",
                                          "rb")).num_fields_in_prog_
    num_state_vars = pickle.load(open(sketch1_name + ".pickle",
                                      "rb")).num_state_vars_
    opt_verify_template = env.get_template("opt_verify.j2")
    opt_verifier = opt_verify_template.render(
        sketch1_name=sketch1_name,
        sketch2_name=sketch2_name,
        sketch1_file_name=sketch1_name + "_optverify.sk",
        sketch2_file_name=sketch2_name + "_optverify.sk",
        hole1_arguments=pickle.load(open(sketch1_name + ".pickle",
                                         "rb")).hole_arguments_,
        hole2_arguments=pickle.load(open(sketch2_name + ".pickle",
                                         "rb")).hole_arguments_,
        sketch1_holes=pickle.load(open(sketch1_name + ".pickle", "rb")).holes_,
        sketch2_holes=pickle.load(open(sketch2_name + ".pickle", "rb")).holes_,
        sketch1_asserts=pickle.load(open(sketch1_name + ".pickle",
                                         "rb")).constraints_,
        sketch2_asserts=pickle.load(open(sketch2_name + ".pickle",
                                         "rb")).constraints_,
        num_fields_in_prog=num_fields_in_prog,
        num_state_vars=num_state_vars,
        transform_function=file_to_str(transform_file))
    print("Verifier file is ",
          sketch1_name + "_" + sketch2_name + "_verifier.sk")
    verifier_file = sketch1_name + "_" + sketch2_name + "_verifier.sk"
    verifier_file_handle = open(verifier_file, "w")
    verifier_file_handle.write(opt_verifier)
    verifier_file_handle.close()

    # Call sketch on it
    (ret_code,
     output) = subprocess.getstatusoutput("time sketch -V 12 " + verifier_file)
    if (ret_code != 0):
        errors_file = open(verifier_file + ".errors", "w")
        errors_file.write(output)
        errors_file.close()
        print("Verification failed. Output left in " + errors_file.name)
        sys.exit(1)
    else:
        success_file = open(verifier_file + ".success", "w")
        success_file.write(output)
        success_file.close()
        print("Verification succeeded. Output left in " + success_file.name)
        sys.exit(0)
