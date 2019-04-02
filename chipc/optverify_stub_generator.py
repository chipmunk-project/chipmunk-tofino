"""Chipmunk Compiler"""
from pathlib import Path
import sys
import re

from chipc.compiler import Compiler
from chipc.utils import get_hole_value_assignments

def main(argv):
    """Main program."""
    if len(argv) < 6:
        print("Usage: optverify_stub_generator <program file> <alu file> " +
              "<number of pipeline stages> " +
              "<number of stateless/stateful ALUs per stage> " +
              "<sketch_name (w/o file extension)> ")
        sys.exit(1)

    program_file = str(argv[1])
    alu_file = str(argv[2])
    num_pipeline_stages = int(argv[3])
    num_alus_per_stage = int(argv[4])
    sketch_name = str(argv[5])
    compiler = Compiler(program_file, alu_file, num_pipeline_stages,
                        num_alus_per_stage, sketch_name, "serial")
    compiler.optverify()


def run_main():
    sys.exit(main(sys.argv))


if __name__ == "__main__":
    run_main()
