"""Chipmunk Compiler"""
from pathlib import Path
import sys
import re

from chipc.compiler import Compiler

def main(argv):
    """Main program."""
    if len(argv) < 8:
        print("Usage: direct_solver <program file> <alu file> " +
              "<number of pipeline stages> " +
              "<number of stateless/stateful ALUs per stage> " +
              "<parallel_codegen/serial_codegen/optverify> <sketch_name (w/o file extension)> " +
              "<parallel/serial>")
        exit(1)

    program_file = str(argv[1])
    alu_file = str(argv[2])
    num_pipeline_stages = int(argv[3])
    num_alus_per_stage = int(argv[4])
    mode = str(argv[5])
    assert mode in ["parallel_codegen", "serial_codegen", "optverify"]
    sketch_name = str(argv[6])
    parallel_or_serial = str(argv[7])
    assert parallel_or_serial in ["parallel", "serial"]

    compiler = Compiler(program_file, alu_file, num_pipeline_stages,
                        num_alus_per_stage, sketch_name, parallel_or_serial)

    # Now fill the appropriate template holes using the components created using
    # sketch_generator
    if mode == "serial_codegen" or mode == "parallel_codegen":
        if mode == "serial_codegen":
            sys.exit(compiler.serial_codegen())
        else:
            compiler.parallel_codegen()
    else:
        compiler.optverify()


def run_main():
    sys.exit(main(sys.argv))


if __name__ == "__main__":
    run_main()
