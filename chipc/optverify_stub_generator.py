"""Chipmunk Compiler"""
import argparse
import sys

from chipc.compiler import Compiler


def main(argv):
    """Main program."""
    parser = argparse.ArgumentParser(
        description="Stub generator for optimization verification.")
    parser.add_argument(
        "program_file", help="Program specification in .sk file")
    parser.add_argument("stateful_alu_file", help="Stateful ALU file to use.")
    parser.add_argument(
        "stateless_alu_file", help="Stateless ALU file to use.")
    parser.add_argument(
        "num_pipeline_stages", type=int, help="Number of pipeline stages")
    parser.add_argument(
        "num_alus_per_stage",
        type=int,
        help="Number of stateless/stateful ALUs per stage")
    parser.add_argument(
        "sketch_name",
        help="Name of sketch")

    args = parser.parse_args(argv[1:])
    compiler = Compiler(args.program_file, args.stateful_alu_file,
                        args.stateless_alu_file,
                        args.num_pipeline_stages, args.num_alus_per_stage,
                        args.sketch_name, "serial")
    compiler.optverify()


def run_main():
    sys.exit(main(sys.argv))


if __name__ == "__main__":
    run_main()
