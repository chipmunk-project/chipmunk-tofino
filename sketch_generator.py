# Helper functions to generate sketch code for synthesis
from jinja2 import Template
import math
import sys
from pathlib import Path
from stateful_aluLexer import stateful_aluLexer
from stateful_aluParser import stateful_aluParser
from stateful_alu_sketch_generator import StatefulAluSketchGenerator
from antlr4 import *


class Hole:
    def __init__(self, hole_name, max_value):
        self.name = hole_name
        self.max = max_value


def add_prefix_suffix(text, prefix_string, suffix_string):
    return prefix_string + str(text) + suffix_string


# Sketch Generator class
class SketchGenerator:
    def __init__(self, sketch_name, num_phv_containers, num_state_vars,
                 num_alus_per_stage, num_pipeline_stages, num_fields_in_prog,
                 jinja2_env, alu_file):
        self.sketch_name_ = sketch_name
        self.total_hole_bits_ = 0
        self.hole_names_ = []
        self.hole_preamble_ = ""
        self.hole_arguments_ = []
        self.holes_ = []
        self.asserts_ = ""
        self.constraints_ = []
        self.num_phv_containers_ = num_phv_containers
        self.num_pipeline_stages_ = num_pipeline_stages
        self.num_state_vars_ = num_state_vars
        self.num_alus_per_stage_ = num_alus_per_stage
        self.num_fields_in_prog_ = num_fields_in_prog
        self.jinja2_env_ = jinja2_env
        self.jinja2_env_.filters["add_prefix_suffix"] = add_prefix_suffix
        self.alu_file_ = alu_file
        self.num_operands_to_stateful_alu_ = 0

    # Write all holes to a single hole string for ease of debugging
    def add_hole(self, hole_name, hole_bit_width):
        assert (hole_bit_width >= 0)
        self.hole_names_ += [hole_name]
        self.hole_preamble_ += "int " + hole_name + "= ??(" + str(
            hole_bit_width) + ");\n"
        self.total_hole_bits_ += hole_bit_width
        self.hole_arguments_ += ["int " + hole_name]
        self.holes_ += [Hole(hole_name, 2**hole_bit_width - 1)]

    # Write several holes from a dictionary (new_holes) into self.holes_
    def add_holes(self, new_holes):
        for hole in sorted(new_holes):
            self.add_hole(hole, new_holes[hole])

    def add_assert(self, assert_predicate):
        self.asserts_ += "assert(" + assert_predicate + ");\n"
        self.constraints_ += [assert_predicate]

    # Generate Sketch code for a simple stateless alu (+,-,*,/)
    def generate_stateless_alu(self, alu_name, potential_operands):
        operand_mux_template = self.jinja2_env_.get_template("mux.j2")
        stateless_alu_template = self.jinja2_env_.get_template(
            "stateless_alu.j2")
        stateless_alu = stateless_alu_template.render(
            potential_operands=potential_operands,
            arg_list=["int " + x for x in potential_operands],
            alu_name=self.sketch_name_ + "_" + alu_name,
            mux1=self.sketch_name_ + "_" + alu_name + "_mux1",
            mux2=self.sketch_name_ + "_" + alu_name + "_mux2")
        mux_op_1 = self.generate_mux(
            len(potential_operands), alu_name + "_mux1")
        mux_op_2 = self.generate_mux(
            len(potential_operands), alu_name + "_mux2")
        self.add_hole(self.sketch_name_ + "_" + alu_name + "_opcode", 3)
        self.add_hole(self.sketch_name_ + "_" + alu_name + "_immediate", 2)
        self.add_hole(self.sketch_name_ + "_" + alu_name + "_mode", 2)
        self.add_assert(
            "(" + self.sketch_name_ + "_" + alu_name + "_opcode == 1)" + "|| ("
            + self.sketch_name_ + "_" + alu_name + "_mux1_ctrl <= " +
            self.sketch_name_ + "_" + alu_name +
            "_mux2_ctrl)")  # symmetry breaking for commutativity
        return mux_op_1 + mux_op_2 + stateless_alu

    # Generate Sketch code for a simple stateful alu (+,-,*,/)
    # Takes one state and one packet operand (or immediate operand) as inputs
    # Updates the state in place and returns the old value of the state
    def generate_stateful_alu(self, alu_name):
        input_stream = FileStream(self.alu_file_)
        lexer = stateful_aluLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = stateful_aluParser(stream)
        tree = parser.stateful_alu()
        stateful_alu_sketch_generator = StatefulAluSketchGenerator(
            self.alu_file_, self.sketch_name_ + "_" + alu_name)
        stateful_alu_sketch_generator.visit(tree)
        self.add_holes(stateful_alu_sketch_generator.globalholes)
        self.stateful_alu_hole_arguments_ = [
            x for x in sorted(stateful_alu_sketch_generator.stateful_alu_args)
        ]
        self.num_operands_to_stateful_alu_ = stateful_alu_sketch_generator.num_packet_fields
        return stateful_alu_sketch_generator.helperFunctionStrings + stateful_alu_sketch_generator.mainFunction

    def generate_state_allocator(self):
        for i in range(self.num_pipeline_stages_):
            for l in range(self.num_state_vars_):
                self.add_hole(
                    self.sketch_name_ + "_" + "salu_config_" + str(i) + "_" +
                    str(l), 1)

        for i in range(self.num_pipeline_stages_):
            assert_predicate = "("
            for l in range(self.num_state_vars_):
                assert_predicate += self.sketch_name_ + "_" + "salu_config_" + str(
                    i) + "_" + str(l) + " + "
            assert_predicate += "0) <= " + str(self.num_alus_per_stage_)
            self.add_assert(assert_predicate)

        for l in range(self.num_state_vars_):
            assert_predicate = "("
            for i in range(self.num_pipeline_stages_):
                assert_predicate += self.sketch_name_ + "_" + "salu_config_" + str(
                    i) + "_" + str(l) + " + "
            assert_predicate += "0) <= 1"
            self.add_assert(assert_predicate)

    # Sketch code for an n-to-1 mux
    def generate_mux(self, n, mux_name):
        assert (n >= 1)
        num_bits = math.ceil(math.log(n, 2))
        operand_mux_template = self.jinja2_env_.get_template("mux.j2")
        mux_code = operand_mux_template.render(
            mux_name=self.sketch_name_ + "_" + mux_name,
            operand_list=["input" + str(i) for i in range(0, n)],
            arg_list=["int input" + str(i) for i in range(0, n)],
            num_operands=n)
        self.add_hole(self.sketch_name_ + "_" + mux_name + "_ctrl", num_bits)
        return mux_code

    # Stateful operand muxes (stateless ones are part of generate_stateless_alu)
    def generate_stateful_operand_muxes(self):
        ret = ""
        # Generate one mux for inputs: num_phv_containers+1 to 1. The +1 is to
        # support constant/immediate operands.
        assert (self.num_operands_to_stateful_alu_ > 0)
        for i in range(self.num_pipeline_stages_):
            for l in range(self.num_state_vars_):
                for k in range(self.num_operands_to_stateful_alu_):
                    ret += self.generate_mux(
                        self.num_phv_containers_, "stateful_operand_mux_" +
                        str(i) + "_" + str(l) + "_" + str(k)) + "\n"
        return ret

    # Output muxes to pick between stateful ALUs and stateless ALU
    def generate_output_muxes(self):
        # Note: We are generating a mux that takes as input all virtual stateful
        # ALUs + corresponding stateless ALU The number of virtual stateful ALUs
        # is more or less than the physical stateful ALUs because it equals the
        # number of state variables in the program_file, but this doesn't affect
        # correctness because we enforce that the total number of active virtual
        # stateful ALUs is within the physical limit.  It also doesn't affect
        # the correctness of modeling the output mux because the virtual output
        # mux setting can be translated into the physical output mux setting
        # during post processing.
        ret = ""
        for i in range(self.num_pipeline_stages_):
            for k in range(self.num_phv_containers_):
                ret += self.generate_mux(
                    self.num_state_vars_ + 1,
                    "output_mux_phv_" + str(i) + "_" + str(k)) + "\n"
        return ret

    def generate_alus(self):
        # Generate sketch code for alus and immediate operands in each stage
        ret = ""
        for i in range(self.num_pipeline_stages_):
            for j in range(self.num_alus_per_stage_):
                ret += self.generate_stateless_alu(
                    "stateless_alu_" + str(i) + "_" + str(j), [
                        "input" + str(k)
                        for k in range(0, self.num_phv_containers_)
                    ]) + "\n"
            for l in range(self.num_state_vars_):
                ret += self.generate_stateful_alu("stateful_alu_" + str(i) +
                                                  "_" + str(l)) + "\n"
        return ret

    def generate_sketch(self, program_file, alu_definitions,
                        output_mux_definitions,
                        stateful_operand_mux_definitions, mode):
        template = (self.jinja2_env_.get_template("code_generator.j2")
                    if mode == "codegen" else
                    self.jinja2_env_.get_template("sketch_functions.j2"))
        return template.render(
            mode=mode,
            sketch_name=self.sketch_name_,
            program_file=program_file,
            num_pipeline_stages=self.num_pipeline_stages_,
            num_alus_per_stage=self.num_alus_per_stage_,
            num_phv_containers=self.num_phv_containers_,
            hole_definitions=self.hole_preamble_,
            stateful_operand_mux_definitions=stateful_operand_mux_definitions,
            output_mux_definitions=output_mux_definitions,
            alu_definitions=alu_definitions,
            num_fields_in_prog=self.num_fields_in_prog_,
            num_state_vars=self.num_state_vars_,
            spec_as_sketch=Path(program_file).read_text(),
            all_assertions=self.asserts_,
            hole_arguments=self.hole_arguments_,
            stateful_alu_hole_arguments=self.stateful_alu_hole_arguments_,
            num_operands_to_stateful_alu=self.num_operands_to_stateful_alu_)
