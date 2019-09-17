from collections import OrderedDict
from textwrap import dedent

from overrides import overrides

from chipc.aluParser import aluParser
from chipc.aluVisitor import aluVisitor


class SketchStatefulAluVisitor(aluVisitor):
    def __init__(self, alu_name, constant_arr_size):
        self.alu_name = alu_name
        self.constant_arr_size = constant_arr_size
        self.mux5_count = 0
        self.mux4_count = 0
        self.mux3_count = 0
        self.mux2_count = 0
        self.rel_op_count = 0
        self.arith_op_count = 0
        self.opt_count = 0
        self.constant_count = 0
        self.compute_alu_count = 0
        self.bool_op_count = 0
        self.helper_function_strings = '\n\n\n'
        self.alu_args = OrderedDict()
        self.global_holes = OrderedDict()
        self.main_function = ''
        self.packet_fields = []
        self.state_vars = []

    # Copied From Taegyun's code
    def add_hole(self, hole_name, hole_width):
        prefixed_hole = self.alu_name + '_' + hole_name
        assert (prefixed_hole + '_global' not in self.global_holes)
        self.global_holes[prefixed_hole + '_global'] = hole_width
        assert (hole_name not in self.alu_args)
        self.alu_args[hole_name] = hole_width

    @overrides
    def visitAlu(self, ctx):
        self.main_function += ('int ' + self.alu_name +
                               '(ref | StateGroup | state_group, ')

        self.visit(ctx.getChild(0, aluParser.Packet_field_defContext))

        self.visit(ctx.getChild(0, aluParser.State_var_defContext))

        self.main_function += \
            ', %s) {\n'

        assert len(self.state_vars) > 0
        for idx, state_var in enumerate(self.state_vars):
            self.main_function += '\nint ' + state_var + \
                ' = state_group.state_' + str(idx) + ';'

        self.visit(ctx.getChild(0, aluParser.Alu_bodyContext))
        self.main_function += '\n\n}'
        argument_string = ','.join(
            ['int ' + hole for hole in sorted(self.alu_args)])
        self.main_function = self.main_function % argument_string

    @overrides
    def visitState_var_def(self, ctx):
        self.visitChildren(ctx)

    @overrides
    def visitState_var_seq(self, ctx):
        if ctx.getChildCount() > 0:
            self.visitChildren(ctx)

    @overrides
    def visitSingleStateVar(self, ctx):
        self.visit(ctx.getChild(0, aluParser.State_varContext))

    @overrides
    def visitMultipleStateVars(self, ctx):
        self.visitChildren(ctx)

    @overrides
    def visitState_var(self, ctx):
        state_var_name = ctx.getText()
        self.state_vars.append(state_var_name)

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
        self.main_function += ', '
        self.visit(ctx.getChild(0, aluParser.Packet_fieldsContext))

    @overrides
    def visitPacket_field(self, ctx):
        packet_field_name = ctx.getText()
        self.main_function += 'int '
        self.main_function += packet_field_name
        self.packet_fields.append(packet_field_name)

    @overrides
    def visitVariable(self, ctx):
        self.main_function += ctx.getText()

    @overrides
    def visitNum(self, ctx):
        self.main_function += ctx.getText()

    @overrides
    def visitTemp_var(self, ctx):
        self.main_function += ctx.getText()

    @overrides
    def visitState_indicator(self, ctx):
        pass

    @overrides
    def visitReturn_statement(self, ctx):
        for idx, state_var in enumerate(self.state_vars):
            self.main_function += '\nstate_group.state_' + str(
                idx) + ' = ' + state_var + ';'

        self.main_function += 'return '
        self.visit(ctx.getChild(1))
        self.main_function += ';'

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
    def visitAnd(self, ctx):
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ' && '
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    # TODO: Implement (!A) && B, we only support A && (!B), and !B && A.
    @overrides
    def visitNOT(self, ctx):
        self.main_function += ' !'
        self.visit(ctx.getChild(0, aluParser.ExprContext))

    @overrides
    def visitOr(self, ctx):
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ' || '
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitStmtUpdateExpr(self, ctx):
        assert ctx.getChild(ctx.getChildCount() - 1).getText() == ';', \
            'Every update must end with a semicolon.'
        self.visit(ctx.getChild(0, aluParser.VariableContext))
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
    def visitAssertFalse(self, ctx):
        self.main_function += ctx.getChild(0).getText()

    @overrides
    def visitExprWithOp(self, ctx):
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ctx.getChild(1).getText()
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitExprWithParen(self, ctx):
        self.main_function += '('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ')'

    @overrides
    def visitMux5(self, ctx):
        self.main_function += self.alu_name + '_' + 'Mux5_' + str(
            self.mux5_count) + '('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(1, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(2, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(3, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(4, aluParser.ExprContext))
        self.main_function += ',' + 'Mux5_' + str(self.mux5_count) + ')'
        self.generateMux5()
        self.mux5_count += 1

    @overrides
    def visitMux4(self, ctx):
        self.main_function += self.alu_name + '_' + 'Mux4_' + str(
            self.mux4_count) + '('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(1, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(2, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(3, aluParser.ExprContext))
        self.main_function += ',' + 'Mux4_' + str(self.mux4_count) + ')'
        self.generateMux4()
        self.mux4_count += 1

    @overrides
    def visitMux3(self, ctx):
        self.main_function += self.alu_name + '_' + 'Mux3_' + str(
            self.mux3_count) + '('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(1, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(2, aluParser.ExprContext))
        self.main_function += ',' + 'Mux3_' + str(self.mux3_count) + ')'
        self.generateMux3()
        self.mux3_count += 1

    @overrides
    def visitMux3WithNum(self, ctx):
        self.main_function += self.alu_name + '_Mux3_' + str(
            self.mux3_count) + '('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(1, aluParser.ExprContext))
        self.main_function += ',' + 'Mux3_' + str(self.mux3_count) + ')'
        # Here it's the child with index 6. The grammar parse for this
        # expression as whole is following, NUM '(' expr ',' expr ',' NUM ')'
        # Where NUM is not considered as an expr. Consider parsing NUM as expr
        # so we could simply do ctx.getChild(2, stateful_aluParser.ExprContext)
        # below.
        self.generateMux3WithNum(ctx.getChild(6).getText())
        self.mux3_count += 1

    @overrides
    def visitMux2(self, ctx):
        self.main_function += self.alu_name + '_' + 'Mux2_' + str(
            self.mux2_count) + '('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(1, aluParser.ExprContext))
        self.main_function += ',' + 'Mux2_' + str(self.mux2_count) + ')'
        self.generateMux2()
        self.mux2_count += 1

    @overrides
    def visitRelOp(self, ctx):
        self.main_function += self.alu_name + '_' + 'rel_op_' + str(
            self.rel_op_count) + '('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(1, aluParser.ExprContext))
        self.main_function += ',' + 'rel_op_' + \
            str(self.rel_op_count) + ') == 1'
        self.generateRelOp()
        self.rel_op_count += 1

    @overrides
    def visitBoolOp(self, ctx):
        self.main_function += self.alu_name + '_' + 'bool_op_' + str(
            self.bool_op_count) + '('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(1, aluParser.ExprContext))
        self.main_function += ',' + 'bool_op_' + \
            str(self.bool_op_count) + ') == 1'
        self.generateBoolOp()
        self.bool_op_count += 1

    @overrides
    def visitArithOp(self, ctx):
        self.main_function += self.alu_name + '_' + 'arith_op_' + str(
            self.arith_op_count) + '('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(1, aluParser.ExprContext))
        self.main_function += ',' + 'arith_op_' + \
            str(self.arith_op_count) + ')'
        self.generateArithOp()
        self.arith_op_count += 1

    @overrides
    def visitOpt(self, ctx):
        self.main_function += self.alu_name + '_' + 'Opt_' + str(
            self.opt_count) + '('
        self.visitChildren(ctx)
        self.main_function += ',' + 'Opt_' + str(self.opt_count) + ')'
        self.generateOpt()
        self.opt_count += 1

    @overrides
    def visitConstant(self, ctx):
        self.main_function += self.alu_name + '_' + 'C_' + str(
            self.constant_count) + '('
        self.main_function += 'const_' + str(self.constant_count) + ')'
        self.generateConstant()
        self.constant_count += 1

    @overrides
    def visitComputeAlu(self, ctx):
        self.main_function += self.alu_name + '_' + 'compute_alu_' + str(
            self.compute_alu_count) + '('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(1, aluParser.ExprContext))
        self.main_function += ',' + 'compute_alu_' + \
            str(self.compute_alu_count) + ')'
        self.generateComputeAlu()
        self.compute_alu_count += 1

    def generateMux5(self):
        function_str = """\
int {alu_name}_Mux5_{mux5_count}(int op1, int op2, int op3, int op4, int op5,
                                 int opcode) {{
    if (opcode == 0) return op1;
    else if (opcode == 1) return op2;
    else if (opcode == 2) return op3;
    else if (opcode == 3) return op4;
    else return op5;
}}
"""
        self.helper_function_strings += dedent(
            function_str.format(
                alu_name=self.alu_name,
                mux5_count=str(self.mux5_count)))
        self.add_hole('Mux5_' + str(self.mux5_count), 3)

    def generateMux4(self):
        function_str = """\
int {alu_name}_Mux4_{mux4_count}(int op1, int op2, int op3, int op4,
                                 int opcode) {{
    if (opcode == 0) return op1;
    else if (opcode == 1) return op2;
    else if (opcode == 2) return op3;
    else return op4;
}}
"""
        self.helper_function_strings += dedent(
            function_str.format(
                alu_name=self.alu_name,
                mux4_count=str(self.mux4_count)))
        self.add_hole('Mux4_' + str(self.mux4_count), 2)

    def generateMux3(self):
        self.helper_function_strings += 'int ' + self.alu_name + '_' + \
            'Mux3_' + str(self.mux3_count) + \
            """(int op1, int op2, int op3, int choice) {
    if (choice == 0) return op1;
    else if (choice == 1) return op2;
    else return op3;
    } \n\n"""
        self.add_hole('Mux3_' + str(self.mux3_count), 2)

    def generateMux3WithNum(self, num):
        # NOTE: To escape curly brace, use double curly brace.
        function_str = """\
            int {0}_Mux3_{1}(int op1, int op2, int choice) {{
                if (choice == 0) return op1;
                else if (choice == 1) return op2;
                else return {2};
            }}\n
        """
        self.helper_function_strings += dedent(
            function_str.format(self.alu_name, str(self.mux3_count),
                                num))
        # Add two bit width hole, to express 3 possible values for choice in
        # the above code.
        self.add_hole('Mux3_' + str(self.mux3_count), 2)

    def generateMux2(self):
        self.helper_function_strings += 'int ' + self.alu_name + '_' + \
            'Mux2_' + str(self.mux2_count) + \
            """(int op1, int op2, int choice) {
    if (choice == 0) return op1;
    else return op2;
    } \n\n"""
        self.add_hole('Mux2_' + str(self.mux2_count), 1)
    # TODO: return the member of the vector

    def generateConstant(self):
        self.helper_function_strings += 'int ' + self.alu_name + '_' + \
            'C_' + str(self.constant_count) + """(int const) {
    return constant_vector[const];
    }\n\n"""
        self.add_hole('const_' + str(self.constant_count),
                      self.constant_arr_size)

    def generateRelOp(self):
        self.helper_function_strings += 'int ' + self.alu_name + '_' + \
            'rel_op_' + str(self.rel_op_count) + \
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
        self.add_hole('rel_op_' + str(self.rel_op_count), 2)

    def generateBoolOp(self):
        function_str = """\
bit {alu_name}_bool_op_{bool_op_count} (bit op1, bit op2, int opcode) {{
  if (opcode == 0) {{
    return false;
  }} else if (opcode == 1) {{
    return ~(op1 || op2);
  }} else if (opcode == 2) {{
    return (~op1) && op2;
  }} else if (opcode == 3) {{
    return ~op1;
  }} else if (opcode == 4) {{
    return op1 && (~op2);
  }} else if (opcode == 5) {{
    return ~op2;
  }} else if (opcode == 7) {{
    return ~(op1 && op2);
  }} else if (opcode == 8) {{
    return op1 && op2;
  }} else if (opcode == 10) {{
    return op2;
  }} else if (opcode == 11) {{
    return (~op1) || op2;
  }} else if (opcode == 12) {{
    return op1;
  }} else if (opcode == 13) {{
    return op1 || (~op2);
  }} else if (opcode == 14) {{
    return op1 || op2;
  }} else {{
    return true;
  }}
}}\n
"""
        self.helper_function_strings += dedent(
            function_str.format(
                alu_name=self.alu_name,
                bool_op_count=self.bool_op_count
            )
        )
        self.add_hole('bool_op_' + str(self.bool_op_count), 4)

    def generateArithOp(self):
        self.helper_function_strings += 'int ' + self.alu_name + '_' + \
            'arith_op_' + str(self.arith_op_count) + \
            """(int operand1, int operand2, int opcode) {
    if (opcode == 0) {
      return operand1 + operand2;
    } else {
      return operand1 - operand2;
    }
    }\n\n"""
        self.add_hole('arith_op_' + str(self.arith_op_count), 1)

    def generateOpt(self):
        self.helper_function_strings += 'int ' + self.alu_name + '_' + \
            'Opt_' + str(self.opt_count) + """(int op1, int enable) {
    if (enable != 0) return 0;
    return op1;
    } \n\n"""
        self.add_hole('Opt_' + str(self.opt_count), 1)

    def generateComputeAlu(self):
        function_str = """\
int {alu_name}_compute_alu_{compute_alu_count}(int op1, int op2, int opcode) {{
    if (opcode == 0) {{
        return op1 + op2;
    }} else if (opcode == 1) {{
      return op1 - op2;
    }} else if (opcode == 2) {{
      return op2 - op1;
    }} else if (opcode == 3) {{
      return op2;
    }} else if (opcode == 4) {{
      return op1;
    }} else if (opcode == 5) {{
      return 0;
    }} else {{
      return 1;
    }}
}}\n"""
        self.helper_function_strings += dedent(
            function_str.format(alu_name=self.alu_name,
                                compute_alu_count=str(self.compute_alu_count)))

        self.add_hole('compute_alu_' + str(self.compute_alu_count), 5)
