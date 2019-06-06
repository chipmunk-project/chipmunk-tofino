import concurrent.futures as cf
import itertools
import os
import pickle
import signal
from os import path
from pathlib import Path

import psutil
from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import StrictUndefined

from chipc import sketch_utils
from chipc import z3_utils
from chipc.chipmunk_pickle import ChipmunkPickle
from chipc.mode import Mode
from chipc.sketch_generator import SketchGenerator
from chipc.utils import get_hole_value_assignments
from chipc.utils import get_num_pkt_fields
from chipc.utils import get_state_group_info


def kill_child_processes(parent_pid, sig=signal.SIGTERM):
    try:
        parent = psutil.Process(parent_pid)
    except psutil.NoSuchProcess:
        return
    children = parent.children(recursive=True)
    for process in children:
        try:
            process.send_signal(sig)
            print('send_signal killed a child process', process)
        except psutil.NoSuchProcess as e:
            print("send_signal didn't have any effect because process didn't"
                  'exist')
            print(e)


class Compiler:
    def __init__(self, program_file, stateful_alu_file, stateless_alu_file,
                 num_pipeline_stages, num_alus_per_stage, sketch_name,
                 parallel_sketch, pkt_fields_to_check=[]):
        self.program_file = program_file
        self.stateful_alu_file = stateful_alu_file
        self.stateless_alu_file = stateless_alu_file
        self.num_pipeline_stages = num_pipeline_stages
        self.num_alus_per_stage = num_alus_per_stage
        self.sketch_name = sketch_name
        self.parallel_sketch = parallel_sketch

        program_content = Path(program_file).read_text()
        self.num_fields_in_prog = get_num_pkt_fields(program_content)
        self.num_state_groups = len(get_state_group_info(program_content))

        assert self.num_fields_in_prog <= num_alus_per_stage, (
            'Number of fields in program %d is greater than number of '
            'alus per stage %d. Try increasing number of alus per stage.' % (
                self.num_fields_in_prog, num_alus_per_stage))

        # Initialize jinja2 environment for templates
        self.jinja2_env = Environment(
            loader=FileSystemLoader(
                [path.join(path.dirname(__file__), './templates'),
                 path.join(os.getcwd(),
                           stateless_alu_file[:stateless_alu_file.rfind('/')]),
                 '.', '/']),
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
            stateful_alu_file=stateful_alu_file,
            stateless_alu_file=stateless_alu_file)

    def single_codegen_run(self, compiler_input):
        additional_constraints = compiler_input[0]
        additional_testcases = compiler_input[1]
        sketch_file_name = compiler_input[2]

        """Codegeneration"""
        codegen_code = self.sketch_generator.generate_sketch(
            program_file=self.program_file,
            mode=Mode.CODEGEN,
            additional_constraints=additional_constraints,
            additional_testcases=additional_testcases)

        # Create file and write sketch_harness into it.
        with open(sketch_file_name, 'w') as sketch_file:
            sketch_file.write(codegen_code)

        # Call sketch on it
        print('Total number of hole bits is',
              self.sketch_generator.total_hole_bits_)
        print('Sketch file is', sketch_file_name)
        assert (self.parallel_sketch in [True, False])
        (ret_code, output) = sketch_utils.synthesize(
            sketch_file_name,
            bnd_inbits=2,
            slv_seed=1,
            slv_parallel=self.parallel_sketch)

        # Store sketch output
        with open(sketch_file_name[:sketch_file_name.find('.sk')] +
                  '_output.txt', 'w') as output_file:
            output_file.write(output)
        if (ret_code == 0):
            holes_to_values = get_hole_value_assignments(
                self.sketch_generator.hole_names_, output)
        else:
            holes_to_values = dict()
        return (ret_code, output, holes_to_values)

    def serial_codegen(self, iter_cnt=1, additional_constraints=[],
                       additional_testcases=''):
        return self.single_codegen_run((additional_constraints,
                                        additional_testcases,
                                        self.sketch_name +
                                        '_codegen_iteration_' +
                                        str(iter_cnt) + '.sk'))

    def parallel_codegen(self,
                         additional_constraints=[],
                         additional_testcases=''):
        # For each state_group, pick a pipeline_stage exhaustively.
        # Note that some of these assignments might be infeasible, but that's
        # OK. Sketch will reject these anyway.
        count = 0
        compiler_output = None
        compiler_inputs = []
        for assignment in itertools.product(list(
            range(self.num_pipeline_stages)),
                repeat=self.num_state_groups):
            constraint_list = additional_constraints.copy()
            count = count + 1
            print('Now in assignment # ', count, ' assignment is ', assignment)
            for state_group in range(self.num_state_groups):
                assigned_stage = assignment[state_group]
                for stage in range(self.num_pipeline_stages):
                    if (stage == assigned_stage):
                        constraint_list += [
                            self.sketch_name + '_salu_config_' +
                            str(stage) + '_' + str(state_group) + ' == 1'
                        ]
                    else:
                        constraint_list += [
                            self.sketch_name + '_salu_config_' +
                            str(stage) + '_' + str(state_group) + ' == 0'
                        ]
            compiler_inputs += [
                (constraint_list, additional_testcases,
                 self.sketch_name + '_' + str(count) + '_codegen.sk')
            ]

        with cf.ProcessPoolExecutor(max_workers=count) as executor:
            futures = []
            for compiler_input in compiler_inputs:
                futures.append(
                    executor.submit(self.single_codegen_run, compiler_input))

            for f in cf.as_completed(futures):
                compiler_output = f.result()
                if (compiler_output[0] == 0):
                    print('Success')
                    # TODO: Figure out the right way to do this in the future.
                    executor.shutdown(wait=False)
                    kill_child_processes(os.getpid())
                    return compiler_output
                else:
                    print('One run failed, waiting for others.')
        return compiler_output

    def optverify(self):
        """Opt Verify"""
        optverify_code = self.sketch_generator.generate_sketch(
            program_file=self.program_file,
            mode=Mode.OPTVERIFY,
            additional_constraints=[])

        # Create file and write sketch_function into it
        with open(self.sketch_name + '_optverify.sk', 'w') as sketch_file:
            sketch_file.write(optverify_code)
            print('Sketch file is', sketch_file.name)

        # Put the rest (holes, hole arguments, constraints, etc.) into a
        # .pickle file.
        with open(self.sketch_name + '.pickle', 'wb') as pickle_file:
            pickle.dump(
                ChipmunkPickle(
                    holes=self.sketch_generator.holes_,
                    hole_arguments=self.sketch_generator.hole_arguments_,
                    constraints=self.sketch_generator.constraints_,
                    num_fields_in_prog=self.num_fields_in_prog,
                    num_state_groups=self.num_state_groups,
                    num_state_slots=self.sketch_generator.num_state_slots_),
                pickle_file)
            print('Pickle file is ', pickle_file.name)

        print('Total number of hole bits is',
              self.sketch_generator.total_hole_bits_)

    def sol_verify(self, hole_assignments, sol_verify_bit, iter_cnt=1):
        """Verify hole value assignments with z3"""
        # Check that all holes are filled.
        for hole in self.sketch_generator.hole_names_:
            assert (hole in hole_assignments)

        # Generate and run sketch that verifies these holes on a large input
        # range (num_input_bits)
        sol_verify_code = self.sketch_generator.generate_sketch(
            program_file=self.program_file,
            mode=Mode.SOL_VERIFY,
            hole_assignments=hole_assignments)

        sol_verify_basename = self.sketch_name + \
            '_sol_verify_iteration_' + str(iter_cnt)
        sketch_filename = sol_verify_basename + '.sk'
        smt2_filename = sol_verify_basename + '.smt2'
        Path(sketch_filename).write_text(sol_verify_code)
        sketch_utils.generate_smt2_formula(
            sketch_filename, smt2_filename, sol_verify_bit)

        if z3_utils.simple_check(smt2_filename):
            return 0
        return -1

    def counter_example_generator(self, bits_val,
                                  hole_assignments, iter_cnt=1):
        cex_code = self.sketch_generator.generate_sketch(
            program_file=self.program_file,
            mode=Mode.CEXGEN,
            hole_assignments=hole_assignments,
            input_offset=2**bits_val)

        cex_basename = self.sketch_name + '_cexgen_iteration_' + \
            str(iter_cnt) + '_bits_' + str(bits_val)
        sketch_filename = cex_basename + '.sk'
        smt2_filename = cex_basename + '.smt2'
        Path(sketch_filename).write_text(cex_code)

        # We only need following sketch call's side-effect, corresponding .smt2
        # file for the sketch.
        sketch_utils.generate_smt2_formula(
            sketch_filename, smt2_filename, bits_val)

        return z3_utils.generate_counter_examples(smt2_filename)
