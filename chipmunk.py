"""Chipmunk Compiler"""
from pathlib import Path
import sys

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
        return compiler.codegen()

    compiler.optverify()

if __name__ == "__main__":
    main(sys.argv)
