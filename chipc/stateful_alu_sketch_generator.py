from collections import OrderedDict
from textwrap import dedent

from overrides import overrides

from chipc.aluParser import aluParser
from chipc.aluVisitor import aluVisitor


class StatefulALUSketchGenerator(aluVisitor):
    def __init__(self, alu_file, alu_name,
                 constant_arr_size):
        self.instruction_file = alu_file
        self.alu_name = alu_name
        self.constant_arr_size = constant_arr_size
        self.num_state_slots = 0
        self.num_packet_fields = 0
        self.mux6_count = 0
        self.mux3_count = 0
        self.mux2_count = 0
        self.relop_count = 0
        self.arithop_count = 0
        self.opt_count = 0
        self.constant_count = 0
        self.compute_alu_count = 0
        self.bitwise_op_count = 0
        self.helper_function_strings = '\n\n\n'
        self.alu_args = OrderedDict()
        self.global_holes = OrderedDict()
        self.main_function = ''

    # Copied From Taegyun's code
    def add_hole(self, hole_name, hole_width):
        prefixed_hole = self.alu_name + '_' + hole_name
        assert (prefixed_hole + '_global' not in self.global_holes)
        self.global_holes[prefixed_hole + '_global'] = hole_width
        assert (hole_name not in self.alu_args)
        self.alu_args[hole_name] = hole_width

    @overrides
    def visitAlu(self, ctx):
        self.add_hole('output_mux', 1)
        self.main_function += ('|StateGroup| ' + self.alu_name +
                               '(ref | StateGroup | state_group, ' +
                               'int output_mux, ')

        self.visit(ctx.getChild(0, aluParser.Packet_fieldsContext))

        self.visit(ctx.getChild(0, aluParser.State_varsContext))

        self.main_function += \
            ', %s) {\n |StateGroup| old_state_group = state_group;'

        assert(self.num_state_slots > 0)
        for slot in range(self.num_state_slots):
            self.main_function += '\nint state_' + str(
                slot) + ' = state_group.state_' + str(slot) + ';'

        self.visit(ctx.getChild(0, aluParser.Alu_bodyContext))
        for slot in range(self.num_state_slots):
            self.main_function += '\nstate_group.state_' + str(
                slot) + ' = state_' + str(slot) + ';'
        self.main_function += '\n\nif (output_mux == 1){\n' +\
                              'return old_state_group;\n}else{\n' +\
                              'return state_group;\n}\n\n}'
        argument_string = ','.join(
            ['int ' + hole for hole in sorted(self.alu_args)])
        self.main_function = self.main_function % argument_string

    @overrides
    def visitPacket_fields(self, ctx):
        self.main_function += 'int '
        self.main_function += ctx.getChild(
            0, aluParser.Packet_fieldContext).getText() + ','
        self.num_packet_fields = 1
        if (ctx.getChildCount() > 6):
            for i in range(5, ctx.getChildCount() - 1):
                self.visit(ctx.getChild(i))
                self.num_packet_fields += 1
        self.main_function = self.main_function[:-1]  # Trim out the last comma

    @overrides
    def visitPacket_field_with_comma(self, ctx):
        self.main_function += 'int '
        assert (ctx.getChild(0).getText() == ',')
        self.main_function += ctx.getChild(1).getText() + ','

    @overrides
    def visitVar(self, ctx):
        self.main_function += ctx.getText()

    @overrides
    def visitState_vars(self, ctx):
        self.num_state_slots = ctx.getChildCount() - 5

    @overrides
    def visitState_indicator(self, ctx):
        pass

    @overrides
    def visitReturn_statement(self, ctx):
        # Stateful ALU's dont have return statements
        assert(ctx.getChildCount() == 0)

    @overrides
    def visitAlu_body(self, ctx):
        if (ctx.getChildCount() == 1):  # simple update
            self.visit(ctx.getChild(0))
        else:  # if-elif-else update
            self.main_function += 'if ('
            self.visit(ctx.if_guard)
            self.main_function += ') {'
            self.visit(ctx.if_body)
            self.main_function += '}'

            # if there is an elif
            if (ctx.getChildCount() > 7
                    and ctx.getChild(7).getText() == 'elif'):
                self.main_function += 'else if ('
                self.visit(ctx.elif_guard)
                self.main_function += ') {'
                self.visit(ctx.elif_body)
                self.main_function += '}'

            # if there is an else
            if ((ctx.getChildCount() > 7
                 and ctx.getChild(7).getText() == 'else')
                    or (ctx.getChildCount() > 14
                        and ctx.getChild(14).getText() == 'else')):
                self.main_function += 'else {'
                self.visit(ctx.else_body)
                self.main_function += '}'

    @overrides
    def visitUpdates(self, ctx):
        self.visitChildren(ctx)

    @overrides
    def visitUpdate(self, ctx):
        assert ctx.getChild(ctx.getChildCount() - 1).getText() == ';', \
            'Every update must end with a semicolon.'

        self.visit(ctx.getChild(0, aluParser.State_varContext))
        self.main_function += ' = '
        self.visit(ctx.getChild(2))
        self.main_function += ';'

    @overrides
    def visitExprWithOp(self, ctx):
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ctx.getChild(1).getText()
        self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitState_var(self, ctx):
        self.main_function += ctx.getChild(0).getText()

    @overrides
    def visitMux6(self, ctx):
        self.main_function += self.alu_name + '_' + 'Mux6_' + str(
            self.mux6_count) + '('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(1, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(2, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(3, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(4, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(5, aluParser.ExprContext))
        self.main_function += ',' + 'Mux6_' + str(self.mux6_count) + ')'
        self.generateMux6()
        self.mux6_count += 1

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
            self.relop_count) + '('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(1, aluParser.ExprContext))
        self.main_function += ',' + 'rel_op_' + \
            str(self.relop_count) + ') == 1'
        self.generateRelOp()
        self.relop_count += 1

    @overrides
    def visitBitwiseOp(self, ctx):
        self.main_function += self.alu_name + '_' + 'bitwise_op_' + str(
            self.bitwise_op_count) + '('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(1, aluParser.ExprContext))
        self.main_function += ',' + 'bitwise_op_' + \
            str(self.bitwise_op_count) + ') == 1'
        self.generateBitwiseOp()
        self.bitwise_op_count += 1

    @overrides
    def visitArithOp(self, ctx):
        self.main_function += self.alu_name + '_' + 'arith_op_' + str(
            self.arithop_count) + '('
        self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += ','
        self.visit(ctx.getChild(1, aluParser.ExprContext))
        self.main_function += ',' + 'arith_op_' + str(self.arithop_count) + ')'
        self.generateArithOp()
        self.arithop_count += 1

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

    def generateMux6(self):
        function_str = """\
int {alu_name}_Mux6_{mux6_count}(int op1, int op2, int op3, int op5, int op6,
                                 int opcode) {{
    if (opcode == 0) return op1;
    else if (opcode == 1) return op2;
    else if (opcode == 2) return op3;
    else if (opcode == 3) return op4;
    else if (opcode == 4) return op5;
    else if (opcode == 5) return op6;
    else return 0;
}}
"""
        self.helper_function_strings += dedent(
            function_str.format(self.alu_name, str(self.mux6_count)))
        self.add_hole('Mux6_' + str(self.mux6_count), 3)

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
            'rel_op_' + str(self.relop_count) + \
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
        self.add_hole('rel_op_' + str(self.relop_count), 2)

    def generateBitwiseOp(self):
        function_str = """\
int {alu_name}_bitwise_op_{bitwise_op_count} (int op1, int op2, int opcode) {{
  if (opcode == 0) {
    return false;
  } else if (opcode == 1) {
    return ~(op1 | op 2);
  } else if (opcode == 2) {
    return (~op1) & op2;
  } else if (opcode == 3) {
    return ~op1;
  } else if (opcode == 4) {
    return op1 & (~op2);
  } else if (opcode == 5) {
    return ~op2;
  } else if (opcode == 6) {
    return op1 ^ op2;
  } else if (opcode == 7) {
    return ~(op1 & op2);
  } else if (opcode == 8) {
    return op1 & op2;
  } else if (opcode == 9) {
    return ~(op1 ^ op2);
  } else if (opcode == 10) {
    return op2;
  } else if (opcode == 11) {
    return (~op1) | op2;
  } else if (opcode == 12) {
    return op1;
  } else if (opcode == 13) {
    return op1 | (~op2);
  } else if (opcode == 14) {
    return op1 | op2;
  } else {
    return true;
  }
}}\n
"""
        self.helper_function_strings += dedent(
            function_str.format(
                alu_name=self.alu_name,
                bitwise_op_count=self.bitwise_op_count
            )
        )
        self.add_hole('bitwise_op_' + str(self.bitwise_op_count), 4)

    def generateArithOp(self):
        self.helper_function_strings += 'int ' + self.alu_name + '_' + \
            'arith_op_' + str(self.arithop_count) + \
            """(int operand1, int operand2, int opcode) {
    if (opcode == 0) {
      return operand1 + operand2;
    } else {
      return operand1 - operand2;
    }
    }\n\n"""
        self.add_hole('arith_op_' + str(self.arithop_count), 1)

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
    if (opcode == 0) {
        return op1 + op2;
    } else if (opcode == 1) {
      return op1 - op2;
    } else if (opcode == 2) {
      return op1 > op2 ? op2 : op1;
    } else if (opcode == 3) {
      return op1 > op2 ? op1 : op2;
    } else if (opcode == 4) {
      return op2 - op1;
    } else if (opcode == 5) {
      return 0;
    } else if (opcode == 6) {
      return ~(op1 | op 2);
    } else if (opcode == 7) {
      return (~op1) & op2;
    } else if (opcode == 8) {
      return ~op1;
    } else if (opcode == 9) {
      return op1 & (~op2);
    } else if (opcode == 10) {
      return ~op2;
    } else if (opcode == 11) {
      return op1 ^ op2;
    } else if (opcode == 12) {
      return ~(op1 & op2);
    } else if (opcode == 13) {
      return op1 & op2;
    } else if (opcode == 14) {
      return ~(op1 ^ op2);
    } else if (opcode == 15) {
      return op2;
    } else if (opcode == 16) {
      return (~op1) | op2;
    } else if (opcode == 17) {
      return op1;
    } else if (opcode == 18) {
      return op1 | (~op2);
    } else if (opcode == 19) {
      return op1 | op2;
    } else {
      return 1;
_   }
}}\n"""
        self.helper_function_strings += dedent(
            function_str.format(alu_name=self.alu_name,
                                compute_alu_count=str(self.compute_alu_count)))

        self.add_hole('compute_alu_' + str(self.compute_alu_count), 5)
