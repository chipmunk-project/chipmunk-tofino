import math
import re

from overrides import overrides

from chipc.aluParser import aluParser
from chipc.aluVisitor import aluVisitor


class TofinoStatelessAluVisitor(aluVisitor):
    def __init__(self, alu_filename, alu_name, constant_arr, hole_assignments):
        self.alu_filename = alu_filename
        self.alu_name = alu_name
        self.constant_arr = constant_arr
        self.hole_assignments = hole_assignments
        # self.stateless_alu_name = stateless_alu_name
        # self.stateless_alu_filename = stateless_alu_filename
        # self.alu_name = alu_name
        # self.potential_operands = potential_operands
        # self.generate_stateless_mux = generate_stateless_mux
        # self.constant_arr_size = constant_arr_size
        # self.mux3_count = 0
        # self.mux2_count = 0
        # self.rel_cop_count = 0
        # self.arith_op_count = 0
        # self.opt_count = 0
        # self.const_count = 0
        # self.helper_function_strings = '\n\n\n'
        # self.global_holes = OrderedDict()
        # self.stateless_alu_args = OrderedDict()
        # self.main_function = ''
        # self.num_packet_fields = 0
        # self.packet_fields = []
        self.opcode_bits = self.find_opcode_bits()
        self.template_args = {}

    # def add_hole(self, hole_name, hole_width):
    #     # immediate_operand forced down to immediate
    #     # for global name.
    #     if 'immediate_operand' in hole_name:
    #         prefixed_hole = self.stateless_alu_name + '_' + \
    #             hole_name[:hole_name.index('_')]
    #         # Set num_bits for immediate
    #         hole_width = self.constant_arr_size
    #     else:
    #         prefixed_hole = self.stateless_alu_name + '_' + hole_name
    #     assert (prefixed_hole not in self.global_holes)
    #     try:
    #         assert prefixed_hole not in self.global_holes, prefixed_hole + \
    #             ' already in global holes'
    #     except AssertionError:
    #         raise
    #     self.global_holes[prefixed_hole] = hole_width

    #     assert (hole_name not in self.stateless_alu_args)
    #     self.stateless_alu_args[hole_name+'_hole_local'] = hole_width

    # Calculates number of bits to set opcode hole to
    def find_opcode_bits(self):
        with open(self.alu_filename) as f:
            first_line = f.readline()
            prog = re.compile(r'// Max value of opcode is (\d+)')
            result = int(prog.match(first_line).groups(0)[0])
            return math.ceil(math.log2(result))

    # # Generates the mux ctrl paremeters
    # def write_mux_inputs(self):
    #     mux_index = 1
    #     for i in range((self.num_packet_fields)):
    #         self.main_function += '\tint ' + 'mux' + str(mux_index) + \
    #             '_ctrl_hole_local,'
    #         mux_index += 1
    #     self.main_function = self.main_function[:-1]

    # # Reassigns hole variable parameters to inputs specified
    # # in ALU file
    # def write_temp_hole_vars(self):
    #     for arg in self.stateless_alu_args:
    #         temp_var = arg[:arg.index('_hole_local')]
    #         # Follow the format like this
    #         # int opcode = opcode_hole_local;
    #         # int immediate_operand = \
    #         # constant_vector[immediate_operand_hole_local];
    #         if 'immediate_operand' in temp_var:
    #             self.main_function += '\tint ' + temp_var + \
    #                 ' = ' + 'constant_vector[' + arg + '];\n'
    #         else:
    #             self.main_function += '\tint ' + temp_var + ' = ' + arg + \
    # ';\n'

    # # Generates code that calls muxes from within stateless ALU
    # def write_mux_call(self):
    #     mux_index = 1
    #     mux_input_str = ''
    #     for operand in self.potential_operands:
    #         mux_input_str += operand+','
    #     for p in self.packet_fields:
    #         mux_ctrl = 'mux' + str(mux_index) + '_ctrl_hole_local'
    #         self.main_function += '\tint ' + p + ' = ' + \
    #             self.stateless_alu_name + '_' + 'mux' + \
    #             str(mux_index) + '(' + mux_input_str + \
    #             mux_ctrl + ');\n'
    #         full_name = self.alu_name + '_' + 'mux' + str(mux_index)
    #         self.helper_function_strings += \
    #             self.generate_stateless_mux(
    #                 len(self.potential_operands), full_name)

    #         mux_index += 1

    @overrides
    def visitAlu(self, ctx):
        expr = self.visit(ctx.getChild(0, aluParser.Alu_bodyContext))

        self.template_args['expr'] = expr

        # self.visit(ctx.getChild(0, aluParser.State_indicatorContext))
        # self.visit(ctx.getChild(0, aluParser.State_varsContext))

        # self.main_function += 'int ' + self.stateless_alu_name + '('
        # # Takes in all phv_containers as parameters
        # for p in self.potential_operands:
        #     self.main_function += 'int ' + p + ','
        # # Records packet fields being used (results from the muxes)
        # self.visit(ctx.getChild(0, aluParser.Packet_fieldsContext))

        # # Adds hole variables to parameters
        # self.visit(ctx.getChild(0, aluParser.Hole_varsContext))
        # self.write_mux_inputs()
        # self.main_function += ' %s){\n'
        # self.write_temp_hole_vars()
        # self.write_mux_call()
        # self.visit(ctx.getChild(0, aluParser.Alu_bodyContext))
        # self.main_function += '\n}'

        # # For additional hole variables (relops, opts, etc)
        # argument_string = ''
        # if len(self.stateless_alu_args) > 2:

        #     argument_string = ',' + ','.join(
        #         ['int ' + hole for hole in sorted(self.stateless_alu_args)])

        # self.main_function = self.main_function % argument_string

        # if self.main_function[-1] == ',':
        #     self.main_function = self.main_function[:-1]

    @overrides
    def visitAlu_body(self, ctx):
        return self.visit(ctx.getChild(0))

    @overrides
    def visitCondition_block(self, ctx):
        # We only expect opcode == \d+ for the expression context
        comparison_expr_ctx = ctx.getChild(0, aluParser.ExprContext)
        opcode_expr_ctx = comparison_expr_ctx.getChild(0,
                                                       aluParser.ExprContext)
        constant_expr_ctx = comparison_expr_ctx.getChild(
            1, aluParser.ExprContext)

        opcode_expr = self.visit(opcode_expr_ctx)
        constant_expr = self.visit(constant_expr_ctx)
        if int(opcode_expr) == int(constant_expr):
            ret_val = self.visit(ctx.getChild(0, aluParser.Alu_bodyContext))
            return ret_val

        return None

    @overrides
    def visitStmtIfElseIfElse(self, ctx):
        # Loop through all the boolean condition and body for 'if' and
        # 'if else', and check whether the condition is satisfied. If so,
        condition_blocks = ctx.condition_block()
        expr_to_return = None
        for block in condition_blocks:
            expr_to_return = self.visit(block)
            if expr_to_return is not None:
                return expr_to_return

        # Now, simply visit the else_body clause and return.
        assert ctx.else_body is not None
        expr_to_return = self.visit(ctx.else_body)

        return expr_to_return

    @overrides
    def visitReturn_statement(self, ctx):
        # Simply return the expression.
        return self.visit(ctx.getChild(0, aluParser.ExprContext))

    @overrides
    def visitVar(self, ctx):
        var_name = ctx.getText()
        # Handle constant propagation for immediate_operand hole
        if var_name == 'immediate_operand' or var_name == 'opcode':
            hole_name = self.alu_name + '_' + var_name
            return str(self.hole_assignments[hole_name])

        return var_name

    @overrides
    def visitExprWithOp(self, ctx):
        return self.visit(ctx.getChild(0, aluParser.ExprContext)) + \
            ctx.getChild(1).getText() + \
            self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitExprWithParen(self, ctx):
        return ctx.getChild(0).getText() + self.visit(
            ctx.getChild(1)) + ctx.getChild(2).getText()

    @overrides
    def visitNum(self, ctx):
        return ctx.getText()

    @overrides
    def visitEquals(self, ctx):
        return self.visit(ctx.getChild(0, aluParser.ExprContext)) + \
            ctx.getChild(1).getText() + \
            self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitGreater(self, ctx):
        return self.visit(ctx.getChild(0, aluParser.ExprContext)) + \
            ctx.getChild(1).getText() + \
            self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitGreaterEqual(self, ctx):
        return self.visit(ctx.getChild(0, aluParser.ExprContext)) + \
            ctx.getChild(1).getText() + \
            self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitLess(self, ctx):
        return self.visit(ctx.getChild(0, aluParser.ExprContext)) + \
            ctx.getChild(1).getText() + \
            self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitLessEqual(self, ctx):
        return self.visit(ctx.getChild(0, aluParser.ExprContext)) + \
            ctx.getChild(1).getText() + \
            self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitNotEqual(self, ctx):
        return self.visit(ctx.getChild(0, aluParser.ExprContext)) + \
            ctx.getChild(1).getText() + \
            self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitAnd(self, ctx):
        return self.visit(ctx.getChild(0, aluParser.ExprContext)) + \
            ctx.getChild(1).getText() + \
            self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitOr(self, ctx):
        return self.visit(ctx.getChild(0, aluParser.ExprContext)) + \
            ctx.getChild(1).getText() + \
            self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitTernary(self, ctx):
        return self.visit(ctx.getChild(0, aluParser.ExprContext)) + \
            ctx.getChild(1).getText() + \
            self.visit(ctx.getChild(1, aluParser.ExprContext)) + \
            ctx.getChild(3).getText() + \
            self.visit(ctx.getChild(2, aluParser.ExprContext))
