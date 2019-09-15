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

    def generate_stateless_alus(self):
        stateless_alus = [[dict()] * self.num_alus_per_stage_
                          for _ in range(self.num_pipeline_stages_)]
        for i in range(self.num_pipeline_stages_):
            for j in range(self.num_alus_per_stage_):
                hole_prefix = self.sketch_name_ + '_stateless_alu_' + \
                    str(i) + '_' + str(j)
                stateless_alus[i][j]['enable'] = self.hole_assignments_.pop(
                    hole_prefix + '_demux_ctrl')
                stateless_alus[i][j]['opcode'] = self.hole_assignments_.pop(
                    hole_prefix + '_opcode')
                stateless_alus[i][j]['result'] = 'ipv4.pkt_' + str(j)
                stateless_alus[i][j]['operand0'] = 'ipv4.pkt_' + str(
                    self.hole_assignments_.pop(hole_prefix +
                                               '_operand_mux_0_ctrl'))
                stateless_alus[i][j]['operand1'] = 'ipv4.pkt_' + str(
                    self.hole_assignments_.pop(hole_prefix +
                                               '_operand_mux_1_ctrl'))

        return stateless_alus

    def generate_stateful_alus(self):
        stateful_alus = [[{}] * self.num_state_groups_
                         for _ in range(self.num_pipeline_stages_)]
        for i in range(self.num_pipeline_stages_):
            for j in range(self.num_state_groups_):
                stateful_alu_template_dict = self.generate_stateful_alu(
                    'stateful_alu_' + str(i) + '_' + str(j))
                stateful_alu_template_dict['alu_name'] = 'salu_' + str(
                    i) + '_' + str(j)
                stateful_alu_template_dict['reg_name'] = 'reg_' + str(j)

                stateful_alus[i][j] = stateful_alu_template_dict

        return stateful_alus

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

        self.hole_assignments_ = tofino_stateful_alu_visitor.hole_assignments

        return tofino_stateful_alu_visitor.template_args

    def generate_salu_configs(self):
        salu_configs = [[0] * self.num_state_groups_
                        for _ in range(self.num_pipeline_stages_)]
        for i in range(self.num_pipeline_stages_):
            for j in range(self.num_state_groups_):
                hole_name = self.sketch_name_ + '_salu_config_' + str(
                    i) + '_' + str(j)
                hole_value = self.hole_assignments_.pop(hole_name)
                salu_configs[i][j] = hole_value

        return salu_configs

    def run(self):
        stateful_alus = self.generate_stateful_alus()
        stateless_alus = self.generate_stateless_alus()
        salu_configs = self.generate_salu_configs()

        template = self.jinja2_env_.get_template('tofino_p4.j2')

        p4_code = template.render(
            sketch_name=self.sketch_name_,
            num_pipeline_stages=self.num_pipeline_stages_,
            num_state_groups=self.num_state_groups_,
            num_alus_per_stage=self.num_alus_per_stage_,
            stateful_alus=stateful_alus,
            stateless_alus=stateless_alus,
            salu_configs=salu_configs
        )

        print("List of holes that we haven't used to generate p4 code")
        for hole, value in sorted(self.hole_assignments_.items()):
            print('int', hole, '=', value)

        p4_filename = self.sketch_name_ + '.p4'
        Path(p4_filename).write_text(p4_code)
        print('Compilation to p4 done. Output left at', p4_filename)
