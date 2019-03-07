"""Chipmunk Compiler"""
from pathlib import Path
import sys
import re

from compiler import Compiler
from utils import get_num_pkt_fields_and_state_vars

def main(argv):
    """Main program."""
    if len(argv) < 8:
        print("Usage: python3 " + argv[0] +
              " <program file> <alu file> <number of pipeline stages> " +
              "<number of stateless/stateful ALUs per stage> " +
              "<codegen/optverify> <sketch_name (w/o file extension)> " +
              "<parallel/serial>")
        exit(1)

    program_file = str(argv[1])
    (num_fields_in_prog, num_state_vars) = get_num_pkt_fields_and_state_vars(
        Path(program_file).read_text())
    alu_file = str(argv[2])
    num_pipeline_stages = int(argv[3])
    num_alus_per_stage = int(argv[4])
    num_phv_containers = num_alus_per_stage
    assert num_fields_in_prog <= num_phv_containers
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
        (ret_code, output) = compiler.codegen()

        if ret_code != 0:
            with open(compiler.sketch_name + ".errors", "w") as errors_file:
                errors_file.write(output)
                print("Sketch failed. Output left in " + errors_file.name)
            sys.exit(1)

        for hole_name in compiler.sketch_generator.hole_names_:
            hits = re.findall("(" + hole_name + ")__" + r"\w+ = (\d+)", output)
            assert len(hits) == 1
            assert len(hits[0]) == 2
            print("int ", hits[0][0], " = ", hits[0][1], ";")
        with open(compiler.sketch_name + ".success", "w") as success_file:
            success_file.write(output)
            print("Sketch succeeded. Generated configuration is given " +
                  "above. Output left in " + success_file.name)
        sys.exit(0)
    else:
        compiler.optverify()

if __name__ == "__main__":
    main(sys.argv)
