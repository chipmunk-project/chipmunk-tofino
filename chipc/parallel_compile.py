"""Parallel compiler"""
from pathlib import Path
import sys
import re

from chipc.compiler import Compiler
from chipc.utils import get_num_pkt_fields_and_state_groups


def main(argv):
    """Main program."""
    if len(argv) != 6:
        print("Usage: chipmunk_parallel" +
              " <program file> <alu file> <number of pipeline stages> " +
              "<number of stateless/stateful ALUs per stage> " +
              "<sketch_name (w/o file extension)> ")
        sys.exit(1)

    program_file = str(argv[1])
    alu_file = str(argv[2])
    num_pipeline_stages = int(argv[3])
    num_alus_per_stage = int(argv[4])
    sketch_name = str(argv[5])

    (num_fields_in_prog,
     num_state_groups) = get_num_pkt_fields_and_state_groups(
         Path(program_file).read_text())

    compiler = Compiler(program_file, alu_file, num_pipeline_stages, num_alus_per_stage, sketch_name, "serial")

    compiler.parallel_codegen()


def run_main():
    sys.exit(main(sys.argv))


if __name__ == "__main__":
    run_main()
