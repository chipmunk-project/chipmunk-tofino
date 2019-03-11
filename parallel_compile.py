"""Parallel compiler"""
from pathlib import Path
import sys
import re
import itertools
import concurrent.futures
import signal, psutil, os

from compiler import Compiler
from utils import get_num_pkt_fields_and_state_groups


def kill_child_processes(parent_pid, sig=signal.SIGTERM):
    try:
        parent = psutil.Process(parent_pid)
    except psutil.NoSuchProcess:
        return
    children = parent.children(recursive=True)
    for process in children:
        process.send_signal(sig)


def single_compiler_run(compiler_input):
    return compiler_input[0].codegen(compiler_input[1])


def main(argv):
    """Main program."""
    if len(argv) != 6:
        print("Usage: python3 " + argv[0] +
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

    # For each state_group, pick a pipeline_stage exhaustively.
    # Note that some of these assignments might be infeasible, but that's OK. Sketch will reject these anyway.
    count = 0
    compiler_output = None
    compiler_inputs = []
    for assignment in itertools.product(
            list(range(num_pipeline_stages)), repeat=num_state_groups):
        additional_asserts = []
        count = count + 1
        print("Now in assignment # ", count, " assignment is ", assignment)
        for state_group in range(num_state_groups):
            assigned_stage = assignment[state_group]
            for stage in range(num_pipeline_stages):
                if (stage == assigned_stage):
                    additional_asserts += [
                        sketch_name + "_" + str(count) + "_salu_config_" +
                        str(stage) + "_" + str(state_group) + " == 1"
                    ]
                else:
                    additional_asserts += [
                        sketch_name + "_" + str(count) + "_salu_config_" +
                        str(stage) + "_" + str(state_group) + " == 0"
                    ]
        compiler_inputs += [(Compiler(
            program_file, alu_file, num_pipeline_stages, num_alus_per_stage,
            sketch_name + "_" + str(count), "serial"), additional_asserts)]

    with concurrent.futures.ProcessPoolExecutor(max_workers=count) as executor:
        futures = []
        for compiler_input in compiler_inputs:
            futures.append(
                executor.submit(single_compiler_run, compiler_input))

        for f in concurrent.futures.as_completed(futures):
            compiler_output = f.result()
            if (compiler_output[0] == 0):
                print("Success")
                for hole_name in compiler_output[2]:
                    hits = re.findall("(" + hole_name + ")__" + r"\w+ = (\d+)",
                                      compiler_output[1])
                    assert len(hits) == 1
                    assert len(hits[0]) == 2
                    print("int ", hits[0][0], " = ", hits[0][1], ";")
                with open(sketch_name + ".success", "w") as success_file:
                    success_file.write(compiler_output[1])
                    print("Sketch succeeded. Generated configuration is given "
                          + "above. Output left in " + success_file.name)
                # TODO: Figure out the right way to do this in the future.
                executor.shutdown(wait=False)
                kill_child_processes(os.getpid())
                sys.exit(0)

            else:
                print("One run failed, waiting for others.")

    # If all runs failed
    with open(sketch_name + ".errors", "w") as errors_file:
        errors_file.write(compiler_output[1])
        print("Sketch failed. Output left in " + errors_file.name)
    sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)
