from overrides import overrides

from chipc.aluParser import aluParser
from chipc.aluVisitor import aluVisitor


class TofinoStatefulAluVisitor(aluVisitor):
    def __init__(self, alu_filename, constant_arr, hole_assignments):
        self.alu_filename = alu_filename
        self.num_state_slots = 0
        self.num_packet_fields = 0
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
        self.main_function = ''
        self.hole_assignments = hole_assignments
        self.constant_arr = constant_arr
        self.template_keywords = set([
            'condition_hi',
            'condition_lo',
            'update_lo_1_predicate',
            'update_lo_1_value',
            'update_lo_2_predicate',
            'update_lo_2_value',
            'update_hi_1_predicate',
            'update_hi_1_value',
            'update_hi_2_predicate',
            'update_hi_2_value',
            'output_value',
        ])
        self.template_args = {}

    def get_full_hole_name(self, hole_name):
        return self.alu_filename + '_' + hole_name + '_global'

    @overrides
    def visitAlu(self, ctx):
        self.main_function += (
            'int ' + self.alu_filename + '(ref | StateGroup | state_group, ')

        self.visit(ctx.getChild(0, aluParser.Packet_fieldsContext))

        self.visit(ctx.getChild(0, aluParser.State_varsContext))

        self.main_function += \
            ') {\n'

        assert (self.num_state_slots > 0)
        for slot in range(self.num_state_slots):
            self.main_function += '\nint state_' + str(
                slot) + ' = state_group.state_' + str(slot) + ';'

        self.visit(ctx.getChild(0, aluParser.Alu_bodyContext))
        self.main_function += '\n\n}'

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
        return ctx.getText()

    @overrides
    def visitNum(self, ctx):
        return ctx.getText()

    @overrides
    def visitTemp_var(self, ctx):
        return ctx.getText()

    @overrides
    def visitState_vars(self, ctx):
        self.num_state_slots = ctx.getChildCount() - 5

    @overrides
    def visitState_indicator(self, ctx):
        pass

    @overrides
    def visitReturn_statement(self, ctx):
        for slot in range(self.num_state_slots):
            self.main_function += '\nstate_group.state_' + str(
                slot) + ' = state_' + str(slot) + ';'

        self.main_function += 'return '
        self.main_function += self.visit(ctx.getChild(1))
        self.main_function += ';'

    @overrides
    def visitCondition_block(self, ctx):
        self.main_function += ' ('
        self.main_function += self.visit(ctx.getChild(0,
                                                      aluParser.ExprContext))
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
        return self.visit(ctx.getChild(0, aluParser.ExprContext)) + \
            ' && ' + \
            self.visit(ctx.getChild(1, aluParser.ExprContext))

    # TODO: Implement (!A) && B, we only support A && (!B), and !B && A.
    @overrides
    def visitNOT(self, ctx):
        return ' !' + self.visit(ctx.getChild(0, aluParser.ExprContext))

    @overrides
    def visitOr(self, ctx):
        return self.visit(ctx.getChild(0, aluParser.ExprContext)) + \
            ' || ' + self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitStmtUpdateExpr(self, ctx):
        assert ctx.getChild(ctx.getChildCount() - 1).getText() == ';', \
            'Every update must end with a semicolon.'
        self.main_function += self.visit(
            ctx.getChild(0, aluParser.State_varContext))
        self.main_function += ' = '
        self.main_function += self.visit(ctx.getChild(0,
                                                      aluParser.ExprContext))
        self.main_function += ';'

    @overrides
    def visitStmtUpdateTempInt(self, ctx):
        assert ctx.getChild(ctx.getChildCount() - 1).getText() == ';', \
            'Every update must end with a semicolon.'
        self.main_function += ctx.getChild(0).getText()
        var_name = self.visit(
            ctx.getChild(0, aluParser.Temp_varContext))
        self.main_function += var_name
        self.main_function += '='
        expr = self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += expr
        self.main_function += ';'

        if var_name in self.template_keywords:
            self.template_args[var_name + '_expr'] = expr

    @overrides
    def visitStmtUpdateTempBit(self, ctx):
        assert ctx.getChild(ctx.getChildCount() - 1).getText() == ';', \
            'Every update must end with a semicolon.'
        self.main_function += ctx.getChild(0).getText()
        var_name = self.visit(
            ctx.getChild(0, aluParser.Temp_varContext))
        self.main_function += var_name
        self.main_function += '='
        expr = self.visit(ctx.getChild(0, aluParser.ExprContext))
        self.main_function += expr
        self.main_function += ';'

        if var_name in self.template_keywords:
            self.template_args[var_name + '_expr'] = expr

    @overrides
    def visitAssertFalse(self, ctx):
        self.main_function += ctx.getChild(0).getText()

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
    def visitEquals(self, ctx):
        return self.visit(ctx.getChild(0, aluParser.ExprContext)) + \
            ctx.getChild(1).getText() + \
            self.visit(ctx.getChild(1, aluParser.ExprContext))

    @overrides
    def visitState_var(self, ctx):
        return ctx.getChild(0).getText()

    @overrides
    def visitMux5(self, ctx):
        op1 = self.visit(ctx.getChild(0, aluParser.ExprContext))
        op2 = self.visit(ctx.getChild(1, aluParser.ExprContext))
        op3 = self.visit(ctx.getChild(2, aluParser.ExprContext))
        op4 = self.visit(ctx.getChild(3, aluParser.ExprContext))
        op5 = self.visit(ctx.getChild(4, aluParser.ExprContext))

        opcode = self.hole_assignments[self.get_full_hole_name(
            'Mux5_' + str(self.mux5_count))]

        self.mux5_count += 1

        return self.generateMux5(op1, op2, op3, op4, op5, opcode)

    @overrides
    def visitMux4(self, ctx):
        op1 = self.visit(ctx.getChild(0, aluParser.ExprContext))
        op2 = self.visit(ctx.getChild(1, aluParser.ExprContext))
        op3 = self.visit(ctx.getChild(2, aluParser.ExprContext))
        op4 = self.visit(ctx.getChild(3, aluParser.ExprContext))

        opcode = self.hole_assignments[self.get_full_hole_name(
            'Mux4_' + str(self.mux4_count))]

        self.mux4_count += 1

        return self.generateMux4(op1, op2, op3, op4, opcode)

    @overrides
    def visitMux3(self, ctx):
        op1 = self.visit(ctx.getChild(0, aluParser.ExprContext))
        op2 = self.visit(ctx.getChild(1, aluParser.ExprContext))
        op3 = self.visit(ctx.getChild(2, aluParser.ExprContext))

        opcode = self.hole_assignments[self.get_full_hole_name(
            'Mux3_' + str(self.mux3_count))]

        self.mux3_count += 1

        return self.generateMux3(op1, op2, op3, opcode)

    @overrides
    def visitMux3WithNum(self, ctx):
        op1 = self.visit(ctx.getChild(0, aluParser.ExprContext))
        op2 = self.visit(ctx.getChild(1, aluParser.ExprContext))
        op3 = ctx.getChild(6).getText()

        opcode = self.hole_assignments[self.get_full_hole_name(
            'Mux3_' + str(self.mux3_count))]

        self.mux3_count += 1

        return self.generateMux3(op1, op2, op3, opcode)

    @overrides
    def visitMux2(self, ctx):
        op1 = self.visit(ctx.getChild(0, aluParser.ExprContext))
        op2 = self.visit(ctx.getChild(1, aluParser.ExprContext))

        opcode = self.hole_assignments[self.get_full_hole_name(
            'Mux2_' + str(self.mux2_count))]

        self.mux2_count += 1

        return self.generateMux2(op1, op2, opcode)

    @overrides
    def visitRelOp(self, ctx):
        op1 = self.visit(ctx.getChild(0, aluParser.ExprContext))
        op2 = self.visit(ctx.getChild(1, aluParser.ExprContext))

        opcode = self.hole_assignments[self.get_full_hole_name(
            'rel_op_' + str(self.rel_op_count))]

        self.rel_op_count += 1

        return self.generateRelOp(op1, op2, opcode)

    @overrides
    def visitBoolOp(self, ctx):
        op1 = self.visit(ctx.getChild(0, aluParser.ExprContext))
        op2 = self.visit(ctx.getChild(1, aluParser.ExprContext))

        opcode = self.hole_assignments[self.get_full_hole_name(
            'bool_op_' + str(self.bool_op_count))]

        self.bool_op_count += 1

        return self.generateBoolOp(op1, op2, opcode)

    @overrides
    def visitArithOp(self, ctx):
        op1 = self.visit(ctx.getChild(0, aluParser.ExprContext))
        op2 = self.visit(ctx.getChild(1, aluParser.ExprContext))

        opcode = self.hole_assignments[self.get_full_hole_name(
            'arith_op_' + str(self.arith_op_count))]

        self.arith_op_count += 1

        return self.generateArithOp(op1, op2, opcode)

    @overrides
    def visitOpt(self, ctx):
        op = self.visit(ctx.getChild(0, aluParser.ExprContext))

        opcode = self.hole_assignments[self.get_full_hole_name(
            'Opt_' + str(self.arith_op_count))]
        self.opt_count += 1

        return self.generateOpt(op, opcode)

    @overrides
    def visitConstant(self, ctx):
        opcode = self.hole_assignments[self.get_full_hole_name(
            'const_' + str(self.constant_count))]

        self.constant_count += 1

        return self.generateConstant(opcode)

    @overrides
    def visitComputeAlu(self, ctx):
        op1 = self.visit(ctx.getChild(0, aluParser.ExprContext))
        op2 = self.visit(ctx.getChild(1, aluParser.ExprContext))

        opcode = self.hole_assignments[self.get_full_hole_name(
            'compute_alu_' + str(self.compute_alu_count))]

        self.compute_alu_count += 1

        return self.generateComputeAlu(op1, op2, opcode)

    def generateMux5(self, op1, op2, op3, op4, op5, opcode):
        if opcode == 0:
            return op1
        elif opcode == 1:
            return op2
        elif opcode == 2:
            return op3
        elif opcode == 4:
            return op4
        else:
            return op5

    def generateMux4(self, op1, op2, op3, op4, opcode):
        if opcode == 0:
            return op1
        elif opcode == 1:
            return op2
        elif opcode == 2:
            return op3
        else:
            return op4

    def generateMux3(self, op1, op2, op3, opcode):
        if opcode == 0:
            return op1
        elif opcode == 1:
            return op2
        else:
            return op3

    def generateMux2(self, op1, op2, opcode):
        if opcode == 0:
            return op1
        else:
            return op2

    def generateConstant(self, opcode):
        return self.constant_arr[opcode]

    def generateRelOp(self, op1, op2, opcode):
        if opcode == 0:
            template_str = '({op1}) != ({op2})'
        elif opcode == 1:
            template_str = '({op1}) < ({op2})'
        elif opcode == 2:
            template_str = '({op1}) > ({op2})'
        else:
            template_str = '({op1}) == ({op2})'

        return template_str.format(op1=op1, op2=op2)

    def generateBoolOp(self, op1, op2, opcode):
        if opcode == 0:
            template_str = 'false'
        elif opcode == 1:
            template_str = '~(({op1}) || ({op2}))'
        elif opcode == 2:
            template_str = '(~({op1})) && ({op2})'
        elif opcode == 3:
            template_str = '~({op1})'
        elif opcode == 4:
            template_str = '({op1}) && (~({op2}))'
        elif opcode == 5:
            template_str = '~({op2})'
        elif opcode == 6:
            template_str = '({op1}) ^ ({op2})'
        elif opcode == 7:
            template_str = '~(({op1}) && ({op2}))'
        elif opcode == 8:
            template_str = '({op1}) && ({op2})'
        elif opcode == 9:
            template_str = '~(({op1}) ^ ({op2}))'
        elif opcode == 10:
            template_str = '({op2})'
        elif opcode == 11:
            template_str = '(~({op1})) || ({op2})'
        elif opcode == 12:
            template_str = '({op1})'
        elif opcode == 13:
            template_str = '({op1}) || (~({op2}))'
        elif opcode == 14:
            template_str = '({op1}) || ({op2})'
        else:
            template_str = 'true'

        return template_str.format(op1=op1, op2=op2)

    def generateArithOp(self, op1, op2, opcode):
        if op1 == '0':
            if opcode == 0:
                template_str = '({op2})'
            else:
                template_str = '(-({op2}))'
        else:
            if opcode == 0:
                template_str = '({op1}) + ({op2})'
            else:
                template_str = '({op1}) - ({op2})'

        return template_str.format(op1=op1, op2=op2)

    def generateOpt(self, op, enable):
        if enable != 0:
            return '0'
        else:
            return op

    def generateComputeAlu(self, op1, op2, opcode):
        if opcode == 0:
            template_str = '({op1}) + ({op2})'
        elif opcode == 1:
            template_str = '({op1}) - ({op2})'
        elif opcode == 2:
            template_str = '({op1}) > ({op2}) ? ({op2}) : ({op1})'
        elif opcode == 3:
            template_str = '({op1}) > ({op2}) ? ({op1}) : ({op2})'
        elif opcode == 4:
            template_str = '({op2}) - ({op1})'
        elif opcode == 5:
            template_str = '({op2})'
        elif opcode == 6:
            template_str = '({op1})'
        elif opcode == 7:
            template_str = '0'
        else:
            template_str = '1'

        return template_str.format(op1=op1, op2=op2)
