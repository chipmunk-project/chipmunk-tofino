from pathlib import Path
from os import path
import pickle
import subprocess
import sys
import argparse

from jinja2 import Environment, FileSystemLoader, StrictUndefined

PICKLE_EXT = ".pickle"


def read_file(filename):
    return Path(filename).read_text()


def optverify(sketch1_name, sketch2_name, transform_file):
    env = Environment(
        loader=FileSystemLoader(
            path.join(path.dirname(__file__), './templates')),
        undefined=StrictUndefined)

    with open(sketch1_name + PICKLE_EXT, "rb") as pickle_file:
        pickle1 = pickle.load(pickle_file)

    with open(sketch2_name + PICKLE_EXT, "rb") as pickle_file:
        pickle2 = pickle.load(pickle_file)

    assert (
        pickle1.num_fields_in_prog_ == pickle2.num_fields_in_prog_
    ), "Two sketches have different number of packet fields, %d != %d" % (
        pickle1.num_fields_in_prog_, pickle2.num_fields_in_prog_)
    assert (
        pickle1.num_state_groups_ == pickle2.num_state_groups_
    ), "Two sketches have different number of state groups, %d != %d" % (
        pickle1.num_state_groups_, pickle2.num_state_groups_)

    num_fields_in_prog = pickle1.num_fields_in_prog_
    num_state_groups = pickle1.num_state_groups_
    num_state_slots = pickle1.num_state_slots_

    opt_verify_template = env.get_template("opt_verify.j2")
    opt_verifier = opt_verify_template.render(
        sketch1_name=sketch1_name,
        sketch2_name=sketch2_name,
        sketch1_file_name=sketch1_name + "_optverify.sk",
        sketch2_file_name=sketch2_name + "_optverify.sk",
        hole1_arguments=pickle1.hole_arguments_,
        hole2_arguments=pickle2.hole_arguments_,
        sketch1_holes=pickle1.holes_,
        sketch2_holes=pickle2.holes_,
        sketch1_asserts=pickle1.constraints_,
        sketch2_asserts=pickle2.constraints_,
        num_fields_in_prog=num_fields_in_prog,
        num_state_groups=num_state_groups,
        transform_function=read_file(transform_file),
        num_state_slots=num_state_slots)
    print("Verifier file is ",
          sketch1_name + "_" + sketch2_name + "_verifier.sk")
    verifier_file = sketch1_name + "_" + sketch2_name + "_verifier.sk"
    verifier_file_handle = open(verifier_file, "w")
    verifier_file_handle.write(opt_verifier)
    verifier_file_handle.close()

    # Call sketch on it
    (ret_code,
     output) = subprocess.getstatusoutput("time sketch -V 12 " + verifier_file)
    if ret_code != 0:
        errors_file = open(verifier_file + ".errors", "w")
        errors_file.write(output)
        errors_file.close()
        print("Verification failed. Output left in " + errors_file.name)
        return 1
    else:
        success_file = open(verifier_file + ".success", "w")
        success_file.write(output)
        success_file.close()
        print("Verification succeeded. Output left in " + success_file.name)
        return 0


def main(argv):
    """Main routine for optimization verifier."""
    parser = argparse.ArgumentParser(description="Sketch generator for optimization verification.")
    parser.add_argument(
        "sketch1",
        help="Name of first sketch")
    parser.add_argument(
        "sketch2",
        help="Name of second sketch")
    parser.add_argument(
        "transform_file", help="Transform file to assist in optimization verification")

    args = parser.parse_args(argv[1:])
    sys.exit(optverify(args.sketch1, args.sketch2, args.transform_file))

def run_main():
    sys.exit(main(sys.argv))


if __name__ == "__main__":
    run_main()
