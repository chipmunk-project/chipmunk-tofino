"""Chipmunk Compiler"""
from pathlib import Path
import argparse
import sys
import re

from chipc.compiler import Compiler
from chipc.utils import get_hole_value_assignments


def main(argv):
    """Main program."""
    parser = argparse.ArgumentParser(description="Chipmunk compiler.")
    parser.add_argument(
        "program_file", help="Program specification in .sk file")
    parser.add_argument("alu_file", help="ALU file to use.")
    parser.add_argument(
        "num_pipeline_stages", type=int, help="Number of pipeline stages")
    parser.add_argument(
        "num_alus_per_stage",
        type=int,
        help="Number of stateless/stateful ALUs per stage")
    parser.add_argument(
        "sketch_name", help="Output sketch filename without extension")
    parser.add_argument(
        "--pkt-fields",
        type=int,
        nargs='+',
        help="Packet fields to check correctness")
    parser.add_argument(
        "-p",
        "--parallel",
        action="store_const",
        const="parallel_codegen",
        default="serial_codegen",
        help="Whether to run multiple sketches in parallel.")
    parser.add_argument(
        "--parallel-sketch",
        action="store_true",
        help="Whether sketch process uses parallelism")

    args = parser.parse_args()

    compiler = Compiler(args.program_file, args.alu_file,
                        args.num_pipeline_stages, args.num_alus_per_stage,
                        args.sketch_name, args.parallel_sketch, args.pkt_fields)

    if args.parallel == "serial_codegen":
        (ret_code, output, hole_names) = compiler.serial_codegen()
    else:
        (ret_code, output, hole_names) = compiler.parallel_codegen()

    # print results
    if ret_code != 0:
        with open(args.sketch_name + ".errors", "w") as errors_file:
            errors_file.write(output)
            print("Sketch failed. Output left in " + errors_file.name)
        sys.exit(1)

    holes_to_values = get_hole_value_assignments(hole_names, output)

    for hole, value in holes_to_values.items():
        print("int ", hole, " = ", value, ";")

    with open(args.sketch_name + ".success", "w") as success_file:
        success_file.write(output)
        print("Sketch succeeded. Generated configuration is given " +
              "above. Output left in " + success_file.name)
    sys.exit(0)


def run_main():
    sys.exit(main(sys.argv))


if __name__ == "__main__":
    run_main()
