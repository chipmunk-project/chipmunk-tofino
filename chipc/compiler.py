from pathlib import Path
from os import path
import pickle
import re
import subprocess
import sys
import itertools
import concurrent.futures
import signal, psutil, os

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from chipc.chipmunk_pickle import ChipmunkPickle
from chipc.sketch_generator import SketchGenerator
from chipc.utils import get_num_pkt_fields_and_state_groups
from chipc.utils import get_hole_value_assignments
from chipc.mode import Mode


def kill_child_processes(parent_pid, sig=signal.SIGTERM):
    try:
        parent = psutil.Process(parent_pid)
    except psutil.NoSuchProcess:
        return
    children = parent.children(recursive=True)
    for process in children:
        try:
            process.send_signal(sig)
            print("send_signal killed a child process", process)
        except psutil.NoSuchProcess as e:
            print("send_signal didn't have any effect because process didn't exist")
            print(e)

class Compiler:
    def __init__(self, program_file, alu_file, num_pipeline_stages,
                 num_alus_per_stage, sketch_name, parallel_or_serial,
                 pkt_fields_to_check=[]):
        self.program_file = program_file
        self.alu_file = alu_file
        self.num_pipeline_stages = num_pipeline_stages
        self.num_alus_per_stage = num_alus_per_stage
        self.sketch_name = sketch_name
        self.parallel_or_serial = parallel_or_serial

        (self.num_fields_in_prog,
         self.num_state_groups) = get_num_pkt_fields_and_state_groups(
             Path(program_file).read_text())

        assert self.num_fields_in_prog <= num_alus_per_stage, (
            "Number of fields in program %d is greater than number of "
            "alus per stage %d. Try increasing number of alus per stage." % (
                self.num_fields_in_prog, num_alus_per_stage))

        # Initialize jinja2 environment for templates
        self.jinja2_env = Environment(
            loader=FileSystemLoader(
                path.join(path.dirname(__file__), './templates')),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True)

        if not pkt_fields_to_check:
            pkt_fields_to_check = list(range(self.num_fields_in_prog))

        # Create an object for sketch generation
        self.sketch_generator = SketchGenerator(
            sketch_name=sketch_name,
            num_pipeline_stages=num_pipeline_stages,
            num_alus_per_stage=num_alus_per_stage,
            num_phv_containers=num_alus_per_stage,
            num_state_groups=self.num_state_groups,
            num_fields_in_prog=self.num_fields_in_prog,
            pkt_fields_to_check=pkt_fields_to_check,
            jinja2_env=self.jinja2_env,
            alu_file=alu_file)

    def single_codegen_run(self, compiler_input):
        additional_constraints = compiler_input[0]
        additional_testcases = compiler_input[1]
        sketch_file_name = compiler_input[2]

        """Codegeneration"""
        codegen_code = self.sketch_generator.generate_sketch(
            program_file=self.program_file,
            mode=Mode.CODEGEN,
            additional_constraints=additional_constraints,
            additional_testcases = additional_testcases)

        # Create file and write sketch_harness into it.
        with open(sketch_file_name, "w") as sketch_file:
            sketch_file.write(codegen_code)

        # Call sketch on it
        print("Total number of hole bits is",
              self.sketch_generator.total_hole_bits_)
        print("Sketch file is ", sketch_file_name)
        if self.parallel_or_serial == "parallel":
            (ret_code, output) = subprocess.getstatusoutput(
                "time sketch -V 12 --slv-seed=1 --slv-parallel " +
                "--bnd-inbits=2 " + sketch_file_name)
        else:
            (ret_code, output) = subprocess.getstatusoutput(
                "time sketch -V 12 --slv-seed=1 --bnd-inbits=2 " +
                sketch_file_name)
        if (ret_code == 0):
            holes_to_values = get_hole_value_assignments(self.sketch_generator.hole_names_, output)
        else:
            holes_to_values = dict()
        return (ret_code, output, holes_to_values)

    def serial_codegen(self, additional_constraints = [], additional_testcases = ""):
        return self.single_codegen_run((additional_constraints, additional_testcases, self.sketch_name + "_codegen.sk"))

    def parallel_codegen(self, additional_constraints = [], additional_testcases = ""):
        # For each state_group, pick a pipeline_stage exhaustively.
        # Note that some of these assignments might be infeasible, but that's OK. Sketch will reject these anyway.
        count = 0
        compiler_output = None
        compiler_inputs = []
        for assignment in itertools.product(
                list(range(self.num_pipeline_stages)), repeat=self.num_state_groups):
            constraint_list = additional_constraints.copy()
            count = count + 1
            print("Now in assignment # ", count, " assignment is ", assignment)
            for state_group in range(self.num_state_groups):
                assigned_stage = assignment[state_group]
                for stage in range(self.num_pipeline_stages):
                    if (stage == assigned_stage):
                        constraint_list += [
                            self.sketch_name + "_salu_config_" +
                            str(stage) + "_" + str(state_group) + " == 1"
                        ]
                    else:
                        constraint_list += [
                            self.sketch_name + "_salu_config_" +
                            str(stage) + "_" + str(state_group) + " == 0"
                        ]
            compiler_inputs += [(constraint_list, additional_testcases, self.sketch_name + "_" + str(count) + "_codegen.sk")]

        with concurrent.futures.ProcessPoolExecutor(max_workers=count) as executor:
            futures = []
            for compiler_input in compiler_inputs:
                futures.append(
                    executor.submit(self.single_codegen_run, compiler_input))

            for f in concurrent.futures.as_completed(futures):
                compiler_output = f.result()
                if (compiler_output[0] == 0):
                    print("Success")
                    # TODO: Figure out the right way to do this in the future.
                    executor.shutdown(wait=False)
                    kill_child_processes(os.getpid())
                    return compiler_output
                else:
                    print("One run failed, waiting for others.")
        return compiler_output

    def optverify(self):
        """Opt Verify"""
        optverify_code = self.sketch_generator.generate_sketch(
            program_file=self.program_file,
            mode=Mode.OPTVERIFY,
            additional_constraints=[])

        # Create file and write sketch_function into it
        with open(self.sketch_name + "_optverify.sk", "w") as sketch_file:
            sketch_file.write(optverify_code)
            print("Sketch file is ", sketch_file.name)

        # Put the rest (holes, hole arguments, constraints, etc.) into a .pickle
        # file.
        with open(self.sketch_name + ".pickle", "wb") as pickle_file:
            pickle.dump(
                ChipmunkPickle(
                    holes=self.sketch_generator.holes_,
                    hole_arguments=self.sketch_generator.hole_arguments_,
                    constraints=self.sketch_generator.constraints_,
                    num_fields_in_prog=self.num_fields_in_prog,
                    num_state_groups=self.num_state_groups,
                    num_state_slots=self.sketch_generator.num_state_slots_),
                pickle_file)
            print("Pickle file is ", pickle_file.name)

        print("Total number of hole bits is",
              self.sketch_generator.total_hole_bits_)

    def sol_verify(self, hole_assignments, num_input_bits):
        # Check that all holes are filled.
        for hole in self.sketch_generator.hole_names_:
            assert(hole in hole_assignments)

        # Generate and run sketch that verifies these holes on a large input range (num_input_bits)
        sol_verify_code = self.sketch_generator.generate_sketch(
            program_file=self.program_file,
            mode = Mode.SOL_VERIFY,
            hole_assignments=hole_assignments
        )
        with open(self.sketch_name + "_sol_verify.sk", "w") as sketch_file:
            sketch_file.write(sol_verify_code)
        (ret_code, output) = subprocess.getstatusoutput("sketch -V 12 --slv-seed=1 --bnd-inbits=" +
                             str(num_input_bits) + " " + self.sketch_name + "_sol_verify.sk")
        return ret_code

    def counter_example_generator(self, bits_val, hole_assignments):
        cex_code = self.sketch_generator.generate_sketch(
            program_file=self.program_file,
            mode=Mode.CEXGEN,
            hole_assignments = hole_assignments,
            input_offset = 2**bits_val)
        with open(self.sketch_name + "_cexgen.sk", "w") as sketch_file:
            sketch_file.write(cex_code)

        # Use --debug-cex mode and get counter examples.
        (ret_code, output) = subprocess.getstatusoutput(
            "sketch -V 3 --slv-seed=1 --debug-cex --bnd-inbits=" + str(bits_val) + " " + self.sketch_name + "_cexgen.sk")

        # Extract counterexample using regular expression.
        pkt_group = re.findall(
            r"input (pkt_\d+)\w+ has value \d+= \((\d+)\)",
            output)
        state_group = re.findall(
            r"input (state_group_\d+_state_\d+)\w+ has value \d+= \((\d+)\)",
            output)
        return (pkt_group, state_group)
