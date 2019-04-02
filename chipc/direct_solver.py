"""Chipmunk Compiler"""
from pathlib import Path
import sys
import re

from chipc.compiler import Compiler
from chipc.utils import get_hole_value_assignments

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
    assert mode in ["parallel_codegen", "serial_codegen"]
    sketch_name = str(argv[6])
    parallel_or_serial = str(argv[7])
    assert parallel_or_serial in ["parallel", "serial"]

    compiler = Compiler(program_file, alu_file, num_pipeline_stages,
                        num_alus_per_stage, sketch_name, parallel_or_serial)

    if mode == "serial_codegen":
        (ret_code, output, hole_names) = compiler.serial_codegen()
    else:
        (ret_code, output, hole_names) = compiler.parallel_codegen()

    # print results
    if ret_code != 0:
        with open(sketch_name + ".errors", "w") as errors_file:
            errors_file.write(output)
            print("Sketch failed. Output left in " + errors_file.name)
        sys.exit(1)

    holes_to_values = get_hole_value_assignments(hole_names, output)

    for hole, value in holes_to_values.items():
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
