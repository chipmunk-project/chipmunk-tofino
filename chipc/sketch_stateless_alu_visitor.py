import math
import re
from collections import OrderedDict

from overrides import overrides

from chipc.aluParser import aluParser
from chipc.aluVisitor import aluVisitor


class SketchStatelessAluVisitor (aluVisitor):
    def __init__(self, alu_filename, alu_name, potential_operands,
                 generate_stateless_mux, constant_arr_size):
        # TODO: alu_filename is need to open the alu template file and get the
        # maximum possible value of opcode as specified in there. However, this
        # can also be handled by the parser and visitor. Remove this argument
        # by doing so.
        # NOTE: alu_name is stateless_alu prefixed and postfixed with the
        # original spec name and pipeline stage, and alu number within that
        # stage. See find_opcode_bis()
        self.alu_filename = alu_filename
        self.alu_name = alu_name
        self.potential_operands = potential_operands
        self.generate_stateless_mux = generate_stateless_mux
        self.constant_arr_size = constant_arr_size
        self.helper_function_strings = '\n\n\n'
        self.global_holes = OrderedDict()
        self.stateless_alu_args = OrderedDict()
        self.main_function = ''
        self.packet_fields = []

        self.opcode_bits = self.find_opcode_bits()

    def add_hole(self, hole_name, hole_width):
        prefixed_hole = self.alu_name + '_' + hole_name

        if 'immediate_operand' in hole_name:
            hole_width = self.constant_arr_size
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
        with open(self.alu_filename) as f:
            first_line = f.readline()
            prog = re.compile(r'// Max value of opcode is (\d+)')
            result = int(prog.match(first_line).groups(0)[0])
            # FIXME: When the result is a power of 2, i.e. 2^n, this returns n
            # instead of n + 1.
            return math.ceil(math.log2(result))

    # Generates the mux ctrl paremeters
    def write_mux_inputs(self):
        for mux_index in range(len(self.packet_fields)):
            self.main_function += ', '
            self.main_function += 'int ' + 'operand_mux_' + str(mux_index) + \
                '_ctrl_hole_local'

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
        mux_index = 0
        mux_input_str = ''
        for operand in self.potential_operands:
            mux_input_str += operand+','
        for i, p in enumerate(self.packet_fields):
            assert(i == mux_index)
            mux_ctrl = 'operand_mux_' + str(mux_index) + '_ctrl_hole_local'
            self.main_function += '\tint ' + p + ' = ' + \
                self.alu_name + '_operand_mux_' + \
                str(mux_index) + '(' + mux_input_str + \
                mux_ctrl + ');\n'
            full_name = self.alu_name + '_operand_mux_' + str(mux_index)
            self.helper_function_strings += \
                self.generate_stateless_mux(
                    len(self.potential_operands), full_name)

            mux_index += 1

    @overrides
    def visitAlu(self, ctx):
        self.visit(ctx.getChild(0, aluParser.State_indicatorContext))
        self.visit(ctx.getChild(0, aluParser.State_var_defContext))

        self.main_function += 'int ' + self.alu_name + '('
        # Takes in all phv_containers as parameters
        for p in self.potential_operands:
            self.main_function += 'int ' + p + ','
        # Records packet fields being used (results from the muxes)
        self.visit(ctx.getChild(0, aluParser.Packet_field_defContext))

        # Adds hole variables to parameters
        self.visit(ctx.getChild(0, aluParser.Hole_defContext))
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
    def visitHole_def(self, ctx):
        self.visit(ctx.getChild(0, aluParser.Hole_seqContext))

    @overrides
    def visitHole_seq(self, ctx):
        if ctx.getChildCount() > 0:
            self.visitChildren(ctx)

    @overrides
    def visitSingleHoleVar(self, ctx):
        self.visitChildren(ctx)

    @overrides
    def visitMultipleHoleVars(self, ctx):
        self.visit(ctx.getChild(0, aluParser.Hole_varContext))
        self.main_function += ', '
        self.visit(ctx.getChild(0, aluParser.Hole_varsContext))

    @overrides
    def visitHole_var(self, ctx):
        var_name = ctx.getText()

        num_bits = 2
        if var_name == 'opcode':
            num_bits = self.opcode_bits
        self.add_hole(var_name, num_bits)
        self.main_function += 'int ' + var_name + '_hole_local'

    @overrides
    def visitPacket_field_def(self, ctx):
        self.visit(ctx.getChild(0, aluParser.Packet_field_seqContext))

    @overrides
    def visitPacket_field_seq(self, ctx):
        if ctx.getChildCount() > 0:
            self.visitChildren(ctx)

    @overrides
    def visitSinglePacketField(self, ctx):
        self.visitChildren(ctx)

    @overrides
    def visitMultiplePacketFields(self, ctx):
        self.visit(ctx.getChild(0, aluParser.Packet_fieldContext))
        self.visit(ctx.getChild(0, aluParser.Packet_fieldsContext))

    @overrides
    def visitPacket_field(self, ctx):
        packet_field_name = ctx.getText()
        self.packet_fields.append(packet_field_name)

    @overrides
    def visitVar(self, ctx):
        self.main_function += ctx.getText()

    @overrides
    def visitCondition_block(self, ctx):
        self.main_function += ' ('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ')\n {'
        self.visit(ctx.getChild(0, aluParser.Alu_bodyContext))
        self.main_function += '\n}\n'

    @overrides
    def visitStmtIfElseIfElse(self, ctx):
        condition_blocks = ctx.condition_block()

        for i, block in enumerate(condition_blocks):
            if i != 0:
                self.main_function += 'else '
            self.main_function += 'if'
            self.visit(block)

        if ctx.else_body is not None:
            self.main_function += 'else {\n'
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
