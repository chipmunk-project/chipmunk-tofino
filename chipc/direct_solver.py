"""Chipmunk Compiler"""
import argparse
import sys

from chipc.compiler import Compiler


def main(argv):
    """Main program."""
    parser = argparse.ArgumentParser(description="Direct solver.")
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

    args = parser.parse_args(argv[1:])

    sketch_name = args.program_file.split('/')[-1].split('.')[0] + \
        "_" + args.alu_file.split('/')[-1].split('.')[0] + \
        "_" + str(args.num_pipeline_stages) + \
        "_" + str(args.num_alus_per_stage)
    compiler = Compiler(args.program_file, args.alu_file,
                        args.num_pipeline_stages, args.num_alus_per_stage,
                        sketch_name, args.parallel_sketch, args.pkt_fields)

    if args.parallel == "serial_codegen":
        (ret_code, output, hole_assignments) = compiler.serial_codegen()
    else:
        (ret_code, output, hole_assignments) = compiler.parallel_codegen()

    # print results
    if ret_code != 0:
        with open(sketch_name + ".errors", "w") as errors_file:
            errors_file.write(output)
            print("Sketch failed. Output left in " + errors_file.name)
        sys.exit(1)
    else:
        for hole, value in hole_assignments.items():
            print("int ", hole, " = ", value, ";")

        with open(sketch_name + ".success", "w") as success_file:
            success_file.write(output)
            print("Sketch succeeded. Generated configuration is given " +
                  "above. Output left in " + success_file.name)
        sys.exit(0)


def run_main():
    sys.exit(main(sys.argv))


if __name__ == "__main__":
    run_main()
