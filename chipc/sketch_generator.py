import math
from pathlib import Path

from antlr4 import CommonTokenStream
from antlr4 import FileStream

from chipc.aluLexer import aluLexer
from chipc.aluParser import aluParser
from chipc.mode import Mode
from chipc.stateful_alu_sketch_generator import StatefulALUSketchGenerator
from chipc.stateless_alu_sketch_generator import StatelessAluSketchGenerator


class Hole:
    def __init__(self, hole_name, max_value):
        self.name = hole_name
        self.max = max_value


def add_prefix_suffix(text, prefix_string, suffix_string):
    return prefix_string + str(text) + suffix_string


# Sketch Generator class
class SketchGenerator:
    def __init__(self, sketch_name, num_phv_containers, num_state_groups,
                 num_alus_per_stage, num_pipeline_stages, num_fields_in_prog,
                 pkt_fields_to_check, jinja2_env, stateful_alu_file,
                 stateless_alu_file, synthesized_allocation):
        self.sketch_name_ = sketch_name
        self.total_hole_bits_ = 0
        self.hole_names_ = []
        self.hole_preamble_ = ''
        self.hole_arguments_ = []
        self.holes_ = []
        self.asserts_ = ''
        self.constraints_ = []
        self.num_phv_containers_ = num_phv_containers
        self.num_pipeline_stages_ = num_pipeline_stages
        self.num_state_groups_ = num_state_groups
        self.num_alus_per_stage_ = num_alus_per_stage
        self.num_fields_in_prog_ = num_fields_in_prog
        self.pkt_fields_to_check_ = pkt_fields_to_check
        self.jinja2_env_ = jinja2_env
        self.jinja2_env_.filters['add_prefix_suffix'] = add_prefix_suffix
        self.stateful_alu_file_ = stateful_alu_file
        self.stateless_alu_file_ = stateless_alu_file
        self.num_operands_to_stateful_alu_ = 0
        self.num_state_slots_ = 0
        self.synthesized_allocation_ = synthesized_allocation

    def reset_holes_and_asserts(self):
        self.total_hole_bits_ = 0
        self.hole_names_ = []
        self.hole_preamble_ = ''
        self.hole_arguments_ = []
        self.holes_ = []
        self.asserts_ = ''
        self.constraints_ = []

    # Write all holes to a single hole string for ease of debugging
    def add_hole(self, hole_name, hole_bit_width):
        assert (hole_bit_width >= 0)
        self.hole_names_ += [hole_name]
        self.hole_preamble_ += 'int ' + hole_name + '= ??(' + str(
            hole_bit_width) + ');\n'
        self.total_hole_bits_ += hole_bit_width
        self.hole_arguments_ += ['int ' + hole_name]
        self.holes_ += [Hole(hole_name, 2**hole_bit_width - 1)]

    # Write several holes from a dictionary (new_holes) into self.holes_
    def add_holes(self, new_holes):
        for hole in sorted(new_holes):
            self.add_hole(hole, new_holes[hole])

    def add_assert(self, assert_predicate):
        self.asserts_ += 'assert(' + assert_predicate + ');\n'
        self.constraints_ += [assert_predicate]

    # Generate Sketch code for a simple stateless alu (+,-,*,/)
    def generate_stateless_alu(self, alu_name, potential_operands):
        # Grab the stateless alu file name by using
        input_stream = FileStream(self.stateless_alu_file_)
        lexer = aluLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = aluParser(stream)
        tree = parser.alu()

        stateless_alu_sketch_generator = \
            StatelessAluSketchGenerator(
                self.stateless_alu_file_, self.sketch_name_ + '_' +
                alu_name, alu_name, potential_operands, self.generate_mux)
        stateless_alu_sketch_generator.visit(tree)
        self.add_holes(stateless_alu_sketch_generator.globalholes)
        self.stateless_alu_hole_arguments_ = [
            x for x in sorted(
                stateless_alu_sketch_generator.stateless_alu_args
            )]
#        self.num_operands_to_stateless_alu_ = (
#            stateless_alu_sketch_generator.num_packet_fields)

        self.num_stateless_muxes_ = \
            stateless_alu_sketch_generator.num_packet_fields
        self.add_assert(
            '(' + self.sketch_name_ + '_' + alu_name + '_opcode == 1)' + '|| ('
            + self.sketch_name_ + '_' + alu_name + '_mux1_ctrl <= ' +
            self.sketch_name_ + '_' + alu_name +
            '_mux2_ctrl)')

        return (stateless_alu_sketch_generator.helperFunctionStrings +
                stateless_alu_sketch_generator.mainFunction)

    # Generate Sketch code for a simple stateful alu (+,-,*,/)
    # Takes one state and one packet operand (or immediate operand) as inputs
    # Updates the state in place and returns the old value of the state
    def generate_stateful_alu(self, alu_name):
        input_stream = FileStream(self.stateful_alu_file_)
        lexer = aluLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = aluParser(stream)
        tree = parser.alu()
        stateful_alu_sketch_generator = StatefulALUSketchGenerator(
            self.stateful_alu_file_, self.sketch_name_ + '_' + alu_name)
        stateful_alu_sketch_generator.visit(tree)
        self.add_holes(stateful_alu_sketch_generator.global_holes)
        self.stateful_alu_hole_arguments_ = [
            x for x in sorted(stateful_alu_sketch_generator.alu_args)
        ]
        self.num_operands_to_stateful_alu_ = (
            stateful_alu_sketch_generator.num_packet_fields)
        self.num_state_slots_ = stateful_alu_sketch_generator.num_state_slots

        return (stateful_alu_sketch_generator.helper_function_strings +
                stateful_alu_sketch_generator.main_function)

    def generate_pkt_field_allocator(self):
        for j in range(self.num_phv_containers_):
            for k in range(self.num_fields_in_prog_):
                self.add_hole(
                    'phv_config_' + str(k) + '_' +
                    str(j), 1)
        # add assert for phv_config
        # assert sum(field) phv_config_{field}_{container} <= 1
        for j in range(self.num_phv_containers_):
            assert_predicate = '('
            for k in range(self.num_fields_in_prog_):
                assert_predicate += ' phv_config_' + \
                    str(k) + '_' + str(j) + '+'
            assert_predicate += '0) <= 1'
            self.add_assert(assert_predicate)
        # assert sum(container) phv_config_{field}_{container} == 1
        for k in range(self.num_fields_in_prog_):
            assert_predicate = '('
            for j in range(self.num_phv_containers_):
                assert_predicate += ' phv_config_' + \
                    str(k) + '_' + str(j) + '+'
            assert_predicate += '0) == 1'
            self.add_assert(assert_predicate)

    def generate_state_allocator(self):
        for i in range(self.num_pipeline_stages_):
            for l in range(self.num_state_groups_):
                self.add_hole(
                    self.sketch_name_ + '_' + 'salu_config_' + str(i) + '_' +
                    str(l), 1)

        for i in range(self.num_pipeline_stages_):
            assert_predicate = '('
            for l in range(self.num_state_groups_):
                assert_predicate += self.sketch_name_ + '_' + \
                    'salu_config_' + str(i) + '_' + str(l) + ' + '
            assert_predicate += '0) <= ' + str(self.num_alus_per_stage_)
            self.add_assert(assert_predicate)

        for l in range(self.num_state_groups_):
            assert_predicate = '('
            for i in range(self.num_pipeline_stages_):
                assert_predicate += self.sketch_name_ + '_' + \
                    'salu_config_' + str(i) + '_' + str(l) + ' + '
            assert_predicate += '0) <= 1'
            self.add_assert(assert_predicate)

    # Sketch code for an n-to-1 mux
    def generate_mux(self, n, mux_name):
        assert (n >= 1)
        num_bits = math.ceil(math.log(n, 2))
        operand_mux_template = self.jinja2_env_.get_template('mux.j2')
        mux_code = operand_mux_template.render(
            mux_name=self.sketch_name_ + '_' + mux_name,
            operand_list=['input' + str(i) for i in range(0, n)],
            arg_list=['int input' + str(i) for i in range(0, n)],
            num_operands=n)
        self.add_hole(self.sketch_name_ + '_' + mux_name + '_ctrl', num_bits)
        return mux_code

    # Stateful operand muxes, stateless ones are part of generate_stateless_alu
    def generate_stateful_operand_muxes(self):
        ret = ''
        # Generate one mux for inputs: num_phv_containers+1 to 1. The +1 is to
        # support constant/immediate operands.
        assert (self.num_operands_to_stateful_alu_ > 0)
        for i in range(self.num_pipeline_stages_):
            for l in range(self.num_state_groups_):
                for k in range(self.num_operands_to_stateful_alu_):
                    ret += self.generate_mux(
                        self.num_phv_containers_, 'stateful_operand_mux_' +
                        str(i) + '_' + str(l) + '_' + str(k)) + '\n'
        return ret

    # Output muxes to pick between stateful ALUs and stateless ALU
    def generate_output_muxes(self):
        # Note: We are generating a mux that takes as input all virtual
        # stateful ALUs + corresponding stateless ALU The number of virtual
        # stateful ALUs is more or less than the physical stateful ALUs because
        # it equals the number of state variables in the program_file, but this
        # doesn't affect correctness because we enforce that the total number
        # of active virtual stateful ALUs is within the physical limit. It also
        # doesn't affect the correctness of modeling the output mux because the
        # virtual output mux setting can be translated into the physical output
        # mux setting during post processing.
        ret = ''
        for i in range(self.num_pipeline_stages_):
            for k in range(self.num_phv_containers_):
                ret += self.generate_mux(
                    self.num_state_groups_ * self.num_state_slots_ + 1,
                    'output_mux_phv_' + str(i) + '_' + str(k)) + '\n'
        return ret

    def generate_alus(self):
        # Generate sketch code for alus and immediate operands in each stage
        ret = ''
        for i in range(self.num_pipeline_stages_):
            for j in range(self.num_alus_per_stage_):
                ret += self.generate_stateless_alu(
                    'stateless_alu_' + str(i) + '_' + str(j), [
                        'input' + str(k)
                        for k in range(0, self.num_phv_containers_)
                    ]) + '\n'
            for l in range(self.num_state_groups_):
                ret += self.generate_stateful_alu('stateful_alu_' + str(i) +
                                                  '_' + str(l)) + '\n'
        return ret

    def generate_sketch(self, program_file, mode, additional_constraints=[],
                        hole_assignments=dict(), additional_testcases=''):
        self.reset_holes_and_asserts()
        if mode == Mode.CODEGEN or mode == Mode.SOL_VERIFY or \
                mode == Mode.VERIFY:
            # TODO: Need better name for j2 file.
            if (self.synthesized_allocation_):
                template = self.jinja2_env_.get_template(
                    'code_generator_synthesized_allocation.j2')
            else:
                template = self.jinja2_env_.get_template('code_generator.j2')
        else:
            assert(mode == Mode.OPTVERIFY), 'Found mode ' + mode
            # TODO: Need better name for j2 file.
            if (self.synthesized_allocation_):
                template = self.jinja2_env_.get_template(
                    'sketch_functions_synthesized_allocation.j2')
            else:
                template = self.jinja2_env_.get_template('sketch_functions.j2')

        # Create stateless and stateful ALUs, operand muxes for stateful ALUs,
        # and output muxes.
        alu_definitions = self.generate_alus()
        stateful_operand_mux_definitions = (
            self.generate_stateful_operand_muxes())
        output_mux_definitions = self.generate_output_muxes()

        # Create allocator to ensure each state var is assigned to exactly
        # stateful ALU and vice versa.
        self.generate_state_allocator()
        if (self.synthesized_allocation_):
            self.generate_pkt_field_allocator()

        return template.render(
            mode=mode,
            sketch_name=self.sketch_name_,
            program_file=program_file,
            num_pipeline_stages=self.num_pipeline_stages_,
            num_alus_per_stage=self.num_alus_per_stage_,
            num_phv_containers=self.num_phv_containers_,
            hole_definitions=self.hole_preamble_,
            stateful_operand_mux_definitions=stateful_operand_mux_definitions,
            num_stateless_muxes=self.num_stateless_muxes_,
            output_mux_definitions=output_mux_definitions,
            alu_definitions=alu_definitions,
            num_fields_in_prog=self.num_fields_in_prog_,
            pkt_fields_to_check=self.pkt_fields_to_check_,
            num_state_groups=self.num_state_groups_,
            spec_as_sketch=Path(program_file).read_text(),
            all_assertions=self.asserts_,
            hole_arguments=self.hole_arguments_,
            stateful_alu_hole_arguments=self.stateful_alu_hole_arguments_,
            num_operands_to_stateful_alu=self.num_operands_to_stateful_alu_,
            num_state_slots=self.num_state_slots_,
            additional_constraints='\n'.join(
                ['assert(' + str(x) + ');' for x in additional_constraints]),
            hole_assignments='\n'.join(
                ['int ' + str(hole) + ' = ' + str(value) + ';'
                    for hole, value in hole_assignments.items()]),
            additional_testcases=additional_testcases)
