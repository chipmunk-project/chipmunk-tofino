import math
import re
from collections import OrderedDict
from textwrap import dedent

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
        self.mux3Count = 0
        self.mux2Count = 0
        self.relopCount = 0
        self.arithopCount = 0
        self.optCount = 0
        self.constCount = 0
        self.helperFunctionStrings = '\n\n\n'
        self.globalholes = OrderedDict()
        self.stateless_alu_args = OrderedDict()
        self.mainFunction = ''
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
        assert (prefixed_hole not in self.globalholes)
        try:
            assert prefixed_hole not in self.globalholes, prefixed_hole + \
                ' already in global holes'
        except AssertionError:
            raise
        self.globalholes[prefixed_hole] = hole_width

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
            self.mainFunction += '\tint ' + 'mux' + str(mux_index) + \
                '_ctrl_hole_local,'
            mux_index += 1
        self.mainFunction = self.mainFunction[:-1]

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
                self.mainFunction += '\tint ' + temp_var + \
                    ' = ' + 'constant_vector[' + arg + '];\n'
            else:
                self.mainFunction += '\tint ' + temp_var + ' = ' + arg + ';\n'

    # Generates code that calls muxes from within stateless ALU
    def write_mux_call(self):
        mux_index = 1
        mux_input_str = ''
        for operand in self.potential_operands:
            mux_input_str += operand+','
        for p in self.packet_fields:
            mux_ctrl = 'mux' + str(mux_index) + '_ctrl_hole_local'
            self.mainFunction += '\tint ' + p + ' = ' + \
                self.stateless_alu_name + '_' + 'mux' + \
                str(mux_index) + '(' + mux_input_str + \
                mux_ctrl + ');\n'
            full_name = self.alu_name + '_' + 'mux' + str(mux_index)
            self.helperFunctionStrings += \
                self.generate_stateless_mux(
                    len(self.potential_operands), full_name)

            mux_index += 1

    @overrides
    def visitAlu(self, ctx):

        self.visit(ctx.getChild(0, aluParser.State_indicatorContext))
        self.visit(ctx.getChild(0, aluParser.State_varsContext))

        self.mainFunction += 'int ' + self.stateless_alu_name + '('
        # Takes in all phv_containers as parameters
        for p in self.potential_operands:
            self.mainFunction += 'int ' + p + ','
        # Records packet fields being used (results from the muxes)
        self.visit(ctx.getChild(0, aluParser.Packet_fieldsContext))

        # Adds hole variables to parameters
        self.visit(ctx.getChild(0, aluParser.Hole_varsContext))
        self.write_mux_inputs()
        self.mainFunction += ' %s){\n'
        self.write_temp_hole_vars()
        self.write_mux_call()
        self.visit(ctx.getChild(0, aluParser.Alu_bodyContext))
        self.mainFunction += '\n}'

        # For additional hole variables (relops, opts, etc)
        argument_string = ''
        if len(self.stateless_alu_args) > 2:

            argument_string = ',' + ','.join(
                ['int ' + hole for hole in sorted(self.stateless_alu_args)])

        self.mainFunction = self.mainFunction % argument_string

        if self.mainFunction[-1] == ',':
            self.mainFunction = self.mainFunction[:-1]

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
        self.mainFunction += 'int ' + ctx.getChild(4).getText() + (
            '_hole_local,')
        if (ctx.getChildCount() > 5):
            for i in range(5, ctx.getChildCount()-1):
                self.visit(ctx.getChild(i))
                if 'opcode' in ctx.getChild(i).getText():
                    num_bits = self.find_opcode_bits()
                self.add_hole(ctx.getChild(i).getText()[1:].strip(), (
                    num_bits))

                self.mainFunction += 'int ' + \
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
        self.mainFunction += 'int '+ctx.getChild(1).getText() + ','

    @overrides
    def visitVar(self, ctx):
        self.mainFunction += ctx.getText()

    @overrides
    def visitStmtIfElseIfElse(self, ctx):
        self.mainFunction += 'if ('
        self.visit(ctx.if_guard)
        self.mainFunction += ') {'
        self.visit(ctx.if_body)
        self.mainFunction += '}'

        # if there is an elif
        if (ctx.getChildCount() > 7
                and ctx.getChild(7).getText() == 'elif'):
            self.mainFunction += 'else if ('
            self.visit(ctx.elif_guard)
            self.mainFunction += ') {'
            self.visit(ctx.elif_body)
            self.mainFunction += '}'

        # if there is an else
        if ((ctx.getChildCount() > 7
                and ctx.getChild(7).getText() == 'else')
                or (ctx.getChildCount() > 14
                    and ctx.getChild(14).getText() == 'else')):
            self.mainFunction += 'else {'
            self.visit(ctx.else_body)
            self.mainFunction += '}'

    @overrides
    def visitStmtUpdateExpr(self, ctx):
        assert ctx.getChild(ctx.getChildCount() - 1).getText() == ';', \
            'Every update must end with a semicolon.'
        self.visit(ctx.getChild(0, aluParser.State_varContext))
        self.mainFunction += ' = '
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.mainFunction += ';'

    @overrides
    def visitStmtUpdateGuard(self, ctx):
        assert ctx.getChild(ctx.getChildCount() - 1).getText() == ';', \
            'Every update must end with a semicolon.'
        self.visit(ctx.getChild(0, aluParser.State_varContext))
        self.mainFunction += ' = '
        self.visit(ctx.getChild(0, aluParser.GuardContext))
        self.mainFunction += ';'

    @overrides
    def visitStmtUpdateTempInt(self, ctx):
        assert ctx.getChild(ctx.getChildCount() - 1).getText() == ';', \
            'Every update must end with a semicolon.'
        self.mainFunction += ctx.getChild(0).getText()
        self.visit(ctx.getChild(0, aluParser.Temp_varContext))
        self.mainFunction += '='
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.mainFunction += ';'

    @overrides
    def visitStmtUpdateTempBit(self, ctx):
        assert ctx.getChild(ctx.getChildCount() - 1).getText() == ';', \
            'Every update must end with a semicolon.'
        self.mainFunction += ctx.getChild(0).getText()
        self.visit(ctx.getChild(0, aluParser.Temp_varContext))
        self.mainFunction += '='
        self.visit(ctx.getChild(0, aluParser.GuardContext))
        self.mainFunction += ';'

    @overrides
    def visitNested(self, ctx):
        self.visit(ctx.getChild(0))
        self.mainFunction += ctx.getChild(1).getText()
        self.visit(ctx.getChild(2))

    @overrides
    def visitMux2(self, ctx):
        self.mainFunction += self.stateless_alu_name + '_' + 'Mux2_' + str(
            self.mux2Count) + '('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.mainFunction += ','
        self.visit(ctx.getChild(1, aluParser.ExprContext))
        self.mainFunction += ',' + 'Mux2_' + str(self.mux2Count) + ')'
        self.generateMux2()
        self.mux2Count += 1

    @overrides
    def visitMux3(self, ctx):
        self.mainFunction += self.stateless_alu_name + '_' + 'Mux3_' + str(
            self.mux3Count) + '('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.mainFunction += ','
        self.visit(ctx.getChild(1, aluParser.ExprContext))
        self.mainFunction += ','
        self.visit(ctx.getChild(2, aluParser.ExprContext))
        self.mainFunction += ',' + 'Mux3_' + str(self.mux3Count) + ')'
        self.generateMux3()
        self.mux3Count += 1

    @overrides
    def visitReturn_statement(self, ctx):
        self.mainFunction += '\t\treturn '
        self.visit(ctx.getChild(1))
        self.mainFunction += ';'

    @overrides
    def visitMux3WithNum(self, ctx):
        self.mainFunction += self.stateless_alu_name + '_Mux3_' + str(
            self.mux3Count) + '('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.mainFunction += ','
        self.visit(ctx.getChild(1, aluParser.ExprContext))
        self.mainFunction += ',' + 'Mux3_' + str(self.mux3Count) + ')'
        # Here it's the child with index 6. The grammar parse for this
        # expression as whole is following, NUM '(' expr ',' expr ',' NUM ')'
        # Where NUM is not considered as an expr. Consider parsing NUM as expr
        # so we could simply do ctx.getChild(2, aluParser.ExprContext)
        # below.
        self.generateMux3WithNum(ctx.getChild(6).getText())
        self.mux3Count += 1

    @overrides
    def visitOpt(self, ctx):
        self.mainFunction += self.stateless_alu_name + '_' + 'Opt_' + str(
            self.optCount) + '('
        self.visitChildren(ctx)
        self.mainFunction += ',' + 'Opt_' + str(self.optCount) + ')'
        self.generateOpt()
        self.optCount += 1

    @overrides
    def visitRelOp(self, ctx):
        self.mainFunction += self.stateless_alu_name + '_' + 'rel_op_' + str(
            self.relopCount) + '('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.mainFunction += ','
        self.visit(ctx.getChild(1, aluParser.ExprContext))
        self.mainFunction += ',' + 'rel_op_' + str(self.relopCount) + ') == 1'
        self.generateRelOp()
        self.relopCount += 1

    @overrides
    def visitEquals(self, ctx):

        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.mainFunction += '=='
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitGreater(self, ctx):

        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.mainFunction += '>'
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitGreaterEqual(self, ctx):

        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.mainFunction += '>='
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitLess(self, ctx):

        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.mainFunction += '<'
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitLessEqual(self, ctx):

        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.mainFunction += '<='
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitOr(self, ctx):

        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.mainFunction += '||'
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitAnd(self, ctx):

        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.mainFunction += '&&'
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitNotEqual(self, ctx):

        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.mainFunction += '!='
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitValue(self, ctx):
        self.mainFunction += ctx.getText()

    @overrides
    def visitArithOp(self, ctx):
        self.mainFunction += self.stateless_alu_name + '_' + 'arith_op_' + str(
            self.arithopCount) + '('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.mainFunction += ','
        self.visit(ctx.getChild(1, aluParser.ExprContext))
        self.mainFunction += ',' + 'arith_op_' + str(self.arithopCount) + ')'
        self.generateArithOp()
        self.arithopCount += 1

    @overrides
    def visitTrue(self, ctx):
        self.mainFunction += 'true'

    @overrides
    def visitConstant(self, ctx):
        self.mainFunction += self.stateless_alu_name + '_' + 'C_' + str(
            self.constCount) + '('
        self.mainFunction += 'const_' + str(self.constCount) + ')'
        self.generateConstant()
        self.constCount += 1

    @overrides
    def visitParen(self, ctx):
        self.mainFunction += '('
        self.visit(ctx.getChild(1))
        self.mainFunction += ')'

    @overrides
    def visitExprWithParen(self, ctx):
        self.mainFunction += ctx.getChild(0).getText()
        self.visit(ctx.getChild(1))

        self.mainFunction += ctx.getChild(2).getText()

    @overrides
    def visitExprWithOp(self, ctx):
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.mainFunction += ctx.getChild(1).getText()
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    def generateMux2(self):
        self.helperFunctionStrings += 'int ' + self.stateless_alu_name + \
            '_' + 'Mux2_' + str(self.mux2Count) + \
            """(int op1, int op2, int choice) {
    if (choice == 0) return op1;
    else return op2;
    } \n\n"""
        self.add_hole('Mux2_' + str(self.mux2Count), 1)

    def generateMux3(self):
        self.helperFunctionStrings += 'int ' + self.stateless_alu_name + \
            '_' + 'Mux3_' + str(self.mux3Count) + \
            """(int op1, int op2, int op3, int choice) {
    if (choice == 0) return op1;
    else if (choice == 1) return op2;
    else return op3;
    } \n\n"""
        self.add_hole('Mux3_' + str(self.mux3Count), 2)

    def generateMux3WithNum(self, num):
        # NOTE: To escape curly brace, use double curly brace.
        function_str = """\
            int {0}_Mux3_{1}(int op1, int op2, int choice) {{
                if (choice == 0) return op1;
                else if (choice == 1) return op2;
                else return {2};
            }}\n
        """
        self.helperFunctionStrings += dedent(
            function_str.format(self.stateless_alu_name, str(self.mux3Count),
                                num))
        # Add two bit width hole, to express 3 possible values for choice
        # in the above code.
        self.add_hole('Mux3_' + str(self.mux3Count), 2)

    def generateRelOp(self):
        self.helperFunctionStrings += 'int ' + self.stateless_alu_name + \
            '_' + 'rel_op_' + str(self.relopCount) + \
            """(int operand1, int operand2, int opcode) {
    if (opcode == 0) {
      return (operand1 != operand2) ? 1 : 0;
    } else if (opcode == 1) {
      return (operand1 < operand2) ? 1 : 0;
    } else if (opcode == 2) {
      return (operand1 > operand2) ? 1 : 0;
    } else {
      return (operand1 == operand2) ? 1 : 0;
    }
    } \n\n"""
        self.add_hole('rel_op_' + str(self.relopCount), 2)

    def generateArithOp(self):
        self.helperFunctionStrings += 'int ' + self.stateless_alu_name + \
            '_' + 'arith_op_' + str(self.arithopCount) + \
            """(int operand1, int operand2, int opcode) {
    if (opcode == 0) {
      return operand1 + operand2;
    } else {
      return operand1 - operand2;
    }
    }\n\n"""
        self.add_hole('arith_op_' + str(self.arithopCount), 1)

    def generateConstant(self):
        self.helperFunctionStrings += 'int ' + self.stateless_alu_name + \
            '_' + 'C_' + str(self.constCount) + """(int const) {
    return constant_vector[const];
    }\n\n"""
        self.add_hole('const_' + str(self.constCount), self.constant_arr_size)

    def generateOpt(self):
        self.helperFunctionStrings += 'int ' + self.stateless_alu_name + \
            '_' + 'Opt_' + str(self.optCount) + """(int op1, int enable) {
    if (enable != 0) return 0;
    return op1;
    } \n\n"""
        self.add_hole('Opt_' + str(self.optCount), 1)
