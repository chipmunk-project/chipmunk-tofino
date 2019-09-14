from os import path
from pathlib import Path

from antlr4 import CommonTokenStream
from antlr4 import FileStream
from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import StrictUndefined

from chipc.aluLexer import aluLexer
from chipc.aluParser import aluParser
from chipc.tofino_stateful_alu_visitor import TofinoStatefulAluVisitor


class TofinoCodeGenerator:
    def __init__(self, sketch_name, num_alus_per_stage, num_pipeline_stages,
                 num_state_groups, constant_arr, stateful_alu_filename,
                 stateless_alu_filename, hole_assignments):
        self.sketch_name_ = sketch_name
        self.num_pipeline_stages_ = num_pipeline_stages
        self.num_alus_per_stage_ = num_alus_per_stage
        self.num_state_groups_ = num_state_groups
        self.constant_arr_ = constant_arr
        self.hole_assignments_ = hole_assignments
        self.stateful_alu_filename_ = stateful_alu_filename
        self.stateless_alu_filename_ = stateless_alu_filename

        self.jinja2_env_ = Environment(loader=FileSystemLoader(
            [path.join(path.dirname(__file__), './templates')]),
            undefined=StrictUndefined)

    def generate_alus(self):
        stateful_alus = [[{}] * self.num_state_groups_
                         for i in range(self.num_pipeline_stages_)]
        stateless_alus = [[0] * self.num_alus_per_stage_
                          for i in range(self.num_pipeline_stages_)]
        for i in range(self.num_pipeline_stages_):
            for j in range(self.num_alus_per_stage_):
                stateless_alus[i][j] = self.hole_assignments_[
                    self.sketch_name_ + '_stateless_alu_' +
                    str(i) + '_' + str(j) + '_opcode'
                ]
            for l in range(self.num_state_groups_):
                stateful_alu_template_dict = self.generate_stateful_alu(
                    'stateful_alu_' + str(i) + '_' + str(l))
                stateful_alu_template_dict['alu_name'] = 'salu_' + str(
                    i) + '_' + str(l)
                stateful_alu_template_dict['reg_name'] = 'reg_' + str(
                    i) + '_' + str(l)

                stateful_alus[i][l] = stateful_alu_template_dict

        return stateful_alus, stateless_alus

    def generate_stateful_alu(self, alu_name):
        input_stream = FileStream(self.stateful_alu_filename_)
        lexer = aluLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = aluParser(stream)
        tree = parser.alu()

        tofino_stateful_alu_visitor = TofinoStatefulAluVisitor(
            self.sketch_name_ + '_' + alu_name, self.constant_arr_,
            self.hole_assignments_)
        tofino_stateful_alu_visitor.visit(tree)

        return tofino_stateful_alu_visitor.template_args

    def run(self):
        stateful_alus, stateless_alus = self.generate_alus()

        template = self.jinja2_env_.get_template('tofino_p4.j2')

        p4_code = template.render(
            sketch_name=self.sketch_name_,
            num_pipeline_stages=self.num_pipeline_stages_,
            num_state_groups=self.num_state_groups_,
            num_alus_per_stage=self.num_alus_per_stage_,
            stateful_alus=stateful_alus,
            stateless_alus=stateless_alus
        )

        Path(self.sketch_name_ + '.p4').write_text(p4_code)
