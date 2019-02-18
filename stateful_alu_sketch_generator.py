from stateful_aluParser import stateful_aluParser
from stateful_aluVisitor import stateful_aluVisitor

# Visitor class to generate Sketch code from a stateful_alu specification in a .stateful_alu file
class StatefulAluSketchGenerator(stateful_aluVisitor):
  def __init__(self, stateful_alu_file, stateful_alu_name):
    self.stateful_alu_name = stateful_alu_name
    self.stateful_alu_file = stateful_alu_file
    self.mux3Count = 0
    self.mux2Count = 0
    self.relopCount = 0
    self.optCount = 0
    self.constCount = 0
    self.helperFunctionStrings = "\n\n\n"
    self.globalholes = dict()
    self.stateful_alu_args = dict()
    self.mainFunction = ""

  def add_hole(self, hole_name, hole_width):
    prefixed_hole = self.stateful_alu_name + "_" + hole_name
    assert(prefixed_hole + "_global" not in self.globalholes)
    self.globalholes[prefixed_hole + "_global"] = hole_width
    assert(hole_name not in self.stateful_alu_args)
    self.stateful_alu_args[hole_name] = hole_width

  def visitStateful_alu(self, ctx):
    self.mainFunction += "int " + self.stateful_alu_name + "("
    self.visit(ctx.getChild(0))
    self.mainFunction += ", "
    self.visit(ctx.getChild(1))
    self.mainFunction += ", %s) {\n int old_state = state_1;" # The %s is for hole arguments, which are added below.
    self.visit(ctx.getChild(2))
    self.mainFunction += "\n; return old_state;\n}"
    argument_string = ",".join(["int " + hole for hole in sorted(self.stateful_alu_args)])
    self.mainFunction = self.mainFunction%argument_string

  def visitState_var(self, ctx):
    self.mainFunction += ctx.getText()

  def visitPacket_field(self, ctx):
    self.mainFunction += ctx.getText()

  def visitState_vars(self, ctx):
    self.mainFunction +=  "ref int "
    self.visit(ctx.getChild(0))
    assert(ctx.getChildCount() == 1), "We currently only handle 1 packet field and 1 state variable in an atom."

  def visitPacket_fields(self, ctx):
    self.mainFunction += "int "
    self.visit(ctx.getChild(0))
    assert(ctx.getChildCount() == 1), "We currently only handle 1 packet field and 1 state variable in an atom."

  def visitMux2(self, ctx):
    self.mainFunction += self.stateful_alu_name + "_" + "Mux2_" + str(self.mux2Count) + "("
    self.visit(ctx.getChild(2))
    self.mainFunction += ","
    self.visit(ctx.getChild(4))
    self.mainFunction += "," + "Mux2_" + str(self.mux2Count) + ")"
    self.generateMux2()
    self.mux2Count += 1

  def visitMux3(self, ctx):
    self.mainFunction += self.stateful_alu_name + "_" + "Mux3_" + str(self.mux3Count) + "("
    self.visit(ctx.getChild(2))
    self.mainFunction += ","
    self.visit(ctx.getChild(4))
    self.mainFunction += ","
    self.visit(ctx.getChild(6))    
    self.mainFunction += "," + "Mux3_" + str(self.mux3Count) + ")"
    self.generateMux3()
    self.mux3Count += 1

  def visitOpt(self, ctx):
    self.mainFunction += self.stateful_alu_name + "_" + "Opt_" + str(self.optCount) + "("
    self.visitChildren(ctx)
    self.mainFunction += "," + "Opt_" + str(self.optCount) + ")"
    self.generateOpt()
    self.optCount += 1

  def visitRelOp(self, ctx):
    self.mainFunction += self.stateful_alu_name + "_" + "rel_op_" + str(self.relopCount) + "("
    self.visit(ctx.getChild(2))
    self.mainFunction += ","
    self.visit(ctx.getChild(4))
    self.mainFunction += "," + "rel_op_" + str(self.relopCount) + ")"
    self.generateRelOp()
    self.relopCount += 1

  def visitTrue(self, ctx):
    self.mainFunction += "true"

  def visitConstant(self, ctx):
    self.mainFunction += self.stateful_alu_name + "_" + "C_" + str(self.constCount) + "("
    self.mainFunction += "const_" + str(self.constCount) + ")"
    self.generateConstant()
    self.constCount += 1

  def visitUpdate(self, ctx):
    self.visit(ctx.getChild(0))
    self.mainFunction += " = "
    self.visit(ctx.getChild(2))

  def visitGuarded_update(self, ctx):
    self.mainFunction += "if("
    self.visit(ctx.getChild(0))
    self.mainFunction += ")"
    self.mainFunction += "{\n\t"
    self.visit(ctx.getChild(2))
    self.mainFunction += ";\n}"

  def visitExprWithOp(self, ctx):
    self.visit(ctx.getChild(0))
    self.mainFunction += ctx.getChild(1).getText()
    self.visit(ctx.getChild(2))

  def generateMux2(self):
    self.helperFunctionStrings += "int " + self.stateful_alu_name + "_" + "Mux2_" + str(self.mux2Count) +  """(int op1, int op2, int choice) {
    if (choice == 0) return op1;
    else if (choice == 1) return op2;
    else assert(false);
    } \n\n"""
    self.add_hole("Mux2_" + str(self.mux2Count), 2);

  def generateMux3(self):
    self.helperFunctionStrings += "int " + self.stateful_alu_name + "_" + "Mux3_" + str(self.mux3Count) + """(int op1, int op2, int op3, int choice) {
    if (choice == 0) return op1;
    else if (choice == 1) return op2;
    else if (choice == 2) return op3;
    else assert(false);
    } \n\n"""
    self.add_hole("Mux3_" + str(self.mux3Count), 2)

  def generateRelOp(self):
    self.helperFunctionStrings += "bit " + self.stateful_alu_name + "_" + "rel_op_" + str(self.relopCount) + """(int operand1, int operand2, int opcode) {
    if (opcode == 0) {
      return operand1 != operand2;
    } else if (opcode == 1) {
      return operand1 < operand2;
    } else if (opcode == 2) {
      return operand1 > operand2;
    } else {
      assert(opcode == 3);
      return operand1 == operand2;
    }
    } \n\n"""
    self.add_hole("rel_op_" + str(self.relopCount), 2)

  def generateConstant(self):
    self.helperFunctionStrings += "int " + self.stateful_alu_name + "_" + "C_" + str(self.constCount) + """(int const) {
    return const;
    }\n\n"""
    self.add_hole("const_" + str(self.constCount), 2)

  def generateOpt(self):
    self.helperFunctionStrings += "int " + self.stateful_alu_name + "_" + "Opt_" + str(self.optCount) + """(int op1, int enable) {
    if (enable != 0) return 0;
    return op1;
    } \n\n"""
    self.add_hole("Opt_" + str(self.optCount), 1)
