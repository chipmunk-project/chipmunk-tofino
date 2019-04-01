"""Chipmunk Compiler"""
from pathlib import Path
import sys
import re

from chipc.compiler import Compiler
from chipc.utils import get_hole_value_assignments


def main(argv):
    """Main program."""
    if len(argv) < 8:
        print("Usage: chipmunk <program file> <alu file> " +
              "<number of pipeline stages> " +
              "<number of stateless/stateful ALUs per stage> " +
              "<codegen/optverify> <sketch_name (w/o file extension)> " +
              "<parallel/serial>")
        exit(1)

    program_file = str(argv[1])
    alu_file = str(argv[2])
    num_pipeline_stages = int(argv[3])
    num_alus_per_stage = int(argv[4])
    mode = str(argv[5])
    assert mode in ["codegen", "optverify"]
    sketch_name = str(argv[6])
    parallel_or_serial = str(argv[7])
    assert parallel_or_serial in ["parallel", "serial"]

    compiler = Compiler(program_file, alu_file, num_pipeline_stages,
                        num_alus_per_stage, sketch_name, parallel_or_serial)

    # Now fill the appropriate template holes using the components created using
    # sketch_generator
    if mode == "codegen":
        (ret_code, output, _) = compiler.serial_codegen()

        if ret_code != 0:
            with open(compiler.sketch_name + ".errors", "w") as errors_file:
                errors_file.write(output)
                print("Sketch failed. Output left in " + errors_file.name)
            sys.exit(1)

        holes_to_values = get_hole_value_assignments(
            compiler.sketch_generator.hole_names_, output)

        for hole, value in holes_to_values.items():
            print("int ", hole, " = ", value, ";")

        with open(compiler.sketch_name + ".success", "w") as success_file:
            success_file.write(output)
            print("Sketch succeeded. Generated configuration is given " +
                  "above. Output left in " + success_file.name)
        sys.exit(0)
    else:
        compiler.optverify()


def run_main():
    sys.exit(main(sys.argv))


if __name__ == "__main__":
    run_main()
