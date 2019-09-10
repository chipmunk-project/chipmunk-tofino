import math
import re
from collections import OrderedDict

from overrides import overrides

from chipc.aluParser import aluParser
from chipc.aluVisitor import aluVisitor


class StatelessAluSketchGenerator (aluVisitor):
    def __init__(self, stateless_alu_file, stateless_alu_name,
                 alu_name,
                 potential_operands,
                 generate_stateless_mux,
                 constant_arr_size):
        self.stateless_alu_name = stateless_alu_name
        self.stateless_alu_file = stateless_alu_file
        self.alu_name = alu_name
        self.potential_operands = potential_operands
        self.generate_stateless_mux = generate_stateless_mux
        self.constant_arr_size = constant_arr_size
        self.mux3_count = 0
        self.mux2_count = 0
        self.rel_cop_count = 0
        self.arith_op_count = 0
        self.opt_count = 0
        self.const_count = 0
        self.helper_function_strings = '\n\n\n'
        self.global_holes = OrderedDict()
        self.stateless_alu_args = OrderedDict()
        self.main_function = ''
        self.num_packet_fields = 0
        self.packet_fields = []

    def add_hole(self, hole_name, hole_width):
        # immediate_operand forced down to immediate
        # for global name.
        if 'immediate_operand' in hole_name:
            prefixed_hole = self.stateless_alu_name + '_' + \
                hole_name[:hole_name.index('_')]
            # Set num_bits for immediate
            hole_width = self.constant_arr_size
        else:
            prefixed_hole = self.stateless_alu_name + '_' + hole_name
        assert (prefixed_hole not in self.global_holes)
        try:
            assert prefixed_hole not in self.global_holes, prefixed_hole + \
                ' already in global holes'
        except AssertionError:
            raise
        self.global_holes[prefixed_hole] = hole_width

        assert (hole_name not in self.stateless_alu_args)
        self.stateless_alu_args[hole_name+'_hole_local'] = hole_width

    # Calculates number of bits to set opcode hole to
    def find_opcode_bits(self):
        with open(self.stateless_alu_file) as f:
            first_line = f.readline()
            prog = re.compile(r'// Max value of opcode is (\d+)')
            result = int(prog.match(first_line).groups(0)[0])
            return math.ceil(math.log2(result))

    # Generates the mux ctrl paremeters
    def write_mux_inputs(self):
        mux_index = 1
        for i in range((self.num_packet_fields)):
            self.main_function += '\tint ' + 'mux' + str(mux_index) + \
                '_ctrl_hole_local,'
            mux_index += 1
        self.main_function = self.main_function[:-1]

    # Reassigns hole variable parameters to inputs specified
    # in ALU file
    def write_temp_hole_vars(self):
        for arg in self.stateless_alu_args:
            temp_var = arg[:arg.index('_hole_local')]
            # Follow the format like this
            # int opcode = opcode_hole_local;
            # int immediate_operand = \
            # constant_vector[immediate_operand_hole_local];
            if 'immediate_operand' in temp_var:
                self.main_function += '\tint ' + temp_var + \
                    ' = ' + 'constant_vector[' + arg + '];\n'
            else:
                self.main_function += '\tint ' + temp_var + ' = ' + arg + ';\n'

    # Generates code that calls muxes from within stateless ALU
    def write_mux_call(self):
        mux_index = 1
        mux_input_str = ''
        for operand in self.potential_operands:
            mux_input_str += operand+','
        for p in self.packet_fields:
            mux_ctrl = 'mux' + str(mux_index) + '_ctrl_hole_local'
            self.main_function += '\tint ' + p + ' = ' + \
                self.stateless_alu_name + '_' + 'mux' + \
                str(mux_index) + '(' + mux_input_str + \
                mux_ctrl + ');\n'
            full_name = self.alu_name + '_' + 'mux' + str(mux_index)
            self.helper_function_strings += \
                self.generate_stateless_mux(
                    len(self.potential_operands), full_name)

            mux_index += 1

    @overrides
    def visitAlu(self, ctx):

        self.visit(ctx.getChild(0, aluParser.State_indicatorContext))
        self.visit(ctx.getChild(0, aluParser.State_varsContext))

        self.main_function += 'int ' + self.stateless_alu_name + '('
        # Takes in all phv_containers as parameters
        for p in self.potential_operands:
            self.main_function += 'int ' + p + ','
        # Records packet fields being used (results from the muxes)
        self.visit(ctx.getChild(0, aluParser.Packet_fieldsContext))

        # Adds hole variables to parameters
        self.visit(ctx.getChild(0, aluParser.Hole_varsContext))
        self.write_mux_inputs()
        self.main_function += ' %s){\n'
        self.write_temp_hole_vars()
        self.write_mux_call()
        self.visit(ctx.getChild(0, aluParser.Alu_bodyContext))
        self.main_function += '\n}'

        # For additional hole variables (relops, opts, etc)
        argument_string = ''
        if len(self.stateless_alu_args) > 2:

            argument_string = ',' + ','.join(
                ['int ' + hole for hole in sorted(self.stateless_alu_args)])

        self.main_function = self.main_function % argument_string

        if self.main_function[-1] == ',':
            self.main_function = self.main_function[:-1]

    @overrides
    def visitState_indicator(self, ctx):
        try:
            assert ctx.getChildCount() == 3, 'Error: invalid state' + \
                ' indicator argument provided for type. Insert + \
                ''\'stateful\' or \'stateless\''

            assert ctx.getChild(2).getText() == 'stateless', 'Error:  ' + \
                'type is declared as ' + ctx.getChild(2).getText() + \
                ' and not \'stateless\' for stateless ALU '

        except AssertionError:
            raise

    @overrides
    def visitState_vars(self, ctx):
        try:
            assert ctx.getChildCount() == 5, 'Error: ' + \
                'state variables given to stateless ALU'
        except AssertionError:
            raise

    @overrides
    def visitState_var_with_comma(self, ctx):
        pass

    # TODO: Fix comma and int problem, line 230
    @overrides
    def visitHole_vars(self, ctx):
        # Empty set of hole vars
        if (ctx.getChildCount() == 5):
            return

        num_bits = 2
        if 'opcode' in ctx.getChild(4).getText():
            num_bits = self.find_opcode_bits()
        self.add_hole(ctx.getChild(4).getText(), num_bits)
        self.main_function += 'int ' + ctx.getChild(4).getText() + (
            '_hole_local,')
        if (ctx.getChildCount() > 5):
            for i in range(5, ctx.getChildCount()-1):
                self.visit(ctx.getChild(i))
                if 'opcode' in ctx.getChild(i).getText():
                    num_bits = self.find_opcode_bits()
                self.add_hole(ctx.getChild(i).getText()[1:].strip(), (
                    num_bits))

                self.main_function += 'int ' + \
                    ctx.getChild(i).getText()[1:].strip() + \
                    '_hole_local,'

    def visitHole_var_with_comma(self, ctx):
        assert (ctx.getChild(0).getText() == ',')

    @overrides
    def visitPacket_fields(self, ctx):
        # Empty set of packet fields
        if (ctx.getChildCount() == 5):
            return
        self.packet_fields.append(ctx.getChild(4).getText())
        self.num_packet_fields += 1
        if (ctx.getChildCount() > 5):
            for i in range(5, ctx.getChildCount()-1):
                self.packet_fields.append(ctx.getChild(i).getText()[1:])
                self.num_packet_fields += 1

    @overrides
    def visitPacket_field_with_comma(self, ctx):
        assert (ctx.getChild(0).getText() == ',')
        self.main_function += 'int '+ctx.getChild(1).getText() + ','

    @overrides
    def visitVar(self, ctx):
        self.main_function += ctx.getText()

    @overrides
    def visitStmtIfElseIfElse(self, ctx):
        self.main_function += '\tif ('
        self.visit(ctx.if_guard)
        self.main_function += ') {\n'

        self.visit(ctx.if_body)
        self.main_function += '\n}\n'
        elif_index = 7
        while (ctx.getChildCount() > elif_index and
                ctx.getChild(elif_index).getText() == 'elif'):

            self.main_function += '\telse if ('
            self.visit(ctx.getChild(elif_index+2))
            self.main_function += ') {\n'
            self.visit(ctx.getChild(elif_index+5))

            self.main_function += '\n}\n'
            elif_index += 7

        # if there is an else
        if (ctx.getChildCount() > elif_index and
                ctx.getChild(elif_index).getText() == 'else'):
            self.main_function += '\telse {\n'
            self.visit(ctx.else_body)
            self.main_function += '\n}\n'

    @overrides
    def visitStmtUpdateExpr(self, ctx):
        assert ctx.getChild(ctx.getChildCount() - 1).getText() == ';', \
            'Every update must end with a semicolon.'
        self.visit(ctx.getChild(0, aluParser.State_varContext))
        self.main_function += ' = '
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ';'

    @overrides
    def visitStmtUpdateTempInt(self, ctx):
        assert ctx.getChild(ctx.getChildCount() - 1).getText() == ';', \
            'Every update must end with a semicolon.'
        self.main_function += ctx.getChild(0).getText()
        self.visit(ctx.getChild(0, aluParser.Temp_varContext))
        self.main_function += '='
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ';'

    @overrides
    def visitStmtUpdateTempBit(self, ctx):
        assert ctx.getChild(ctx.getChildCount() - 1).getText() == ';', \
            'Every update must end with a semicolon.'
        self.main_function += ctx.getChild(0).getText()
        self.visit(ctx.getChild(0, aluParser.Temp_varContext))
        self.main_function += '='
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ';'

    @overrides
    def visitReturn_statement(self, ctx):
        self.main_function += '\t\treturn '
        self.visit(ctx.getChild(1))
        self.main_function += ';'

    @overrides
    def visitEquals(self, ctx):
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += '=='
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitGreater(self, ctx):
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += '>'
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitGreaterEqual(self, ctx):
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += '>='
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitLess(self, ctx):
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += '<'
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitLessEqual(self, ctx):
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += '<='
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitOr(self, ctx):
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += '||'
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitAnd(self, ctx):
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += '&&'
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitNotEqual(self, ctx):
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += '!='
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitNum(self, ctx):
        self.main_function += ctx.getText()

    @overrides
    def visitTernary(self, ctx):
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += '?'
        self.visit(ctx.getChild(1, aluParser.ExprContext))
        self.main_function += ':'
        self.visit(ctx.getChild(2, aluParser.ExprContext))

    @overrides
    def visitTrue(self, ctx):
        self.main_function += 'true'

    @overrides
    def visitExprWithParen(self, ctx):
        self.main_function += ctx.getChild(0).getText()
        self.visit(ctx.getChild(1))

        self.main_function += ctx.getChild(2).getText()

    @overrides
    def visitExprWithOp(self, ctx):
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ctx.getChild(1).getText()
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitMux2(self, ctx):
        assert False, 'Unexpected keyword Mux2 in stateless ALU.'

    @overrides
    def visitMux3(self, ctx):
        assert False, 'Unexpected keyword Mux3 in stateless ALU.'

    @overrides
    def visitMux3WithNum(self, ctx):
        assert False, 'Unexpected keyword Mux3 in stateless ALU.'

    @overrides
    def visitOpt(self, ctx):
        assert False, 'Unexpected keyword Opt in stateless ALU.'

    @overrides
    def visitRelOp(self, ctx):
        assert False, 'Unexpected keyword rel_op in stateless ALU.'

    @overrides
    def visitArithOp(self, ctx):
        assert False, 'Unexpected keyword arith_op in stateless ALU.'

    @overrides
    def visitConstant(self, ctx):
        assert False, 'Unexpected keyword C() in stateless ALU.'
