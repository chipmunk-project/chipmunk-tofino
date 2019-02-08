from instructionParser import instructionParser
from instructionVisitor import instructionVisitor
class ChipmunkAluGenVisitor(instructionVisitor):
  def __init__(self, instruction_file):
    self.instruction_file = instruction_file
    self.mux3Count = 0
    self.mux2Count = 0
    self.relopCount = 0
    self.optCount = 0
    self.constCount = 0
    self.helperFunctionStrings = "\n\n\n"
    self.globalholes = ""
    self.mainFunction = ""


  def visitInstruction(self, ctx):
    self.mainFunction += "int atom("
    self.visit(ctx.getChild(0))
    self.mainFunction += ", "
    self.visit(ctx.getChild(1))
    self.mainFunction += ") {\n int old_state = state_1;"
    self.visit(ctx.getChild(2))
    self.mainFunction += "\n; return old_state;\n}"


  def visitState_var(self, ctx):
     self.mainFunction += ctx.getText()


  def visitState_vars(self, ctx):
    self.mainFunction +=  "ref int "
    self.visit(ctx.getChild(0))
    self.mainFunction += ','
    self.mainFunction += "ref int "
    self.visit(ctx.getChild(1))

  def visitPacket_field(self, ctx):
     self.mainFunction += ctx.getText()

  def visitPacket_fields(self, ctx):
    self.mainFunction += "int "
    self.visit(ctx.getChild(0))
    self.mainFunction += ','
    self.mainFunction += "int "
    self.visit(ctx.getChild(1))

  def visitState_vars(self, ctx):
    self.mainFunction +=  "ref int "
    self.visit(ctx.getChild(0))
    self.mainFunction += ','
    self.mainFunction += "ref int "
    self.visit(ctx.getChild(1))




  def visitMux2(self, ctx):
    self.mainFunction += "Mux2_" + str(self.mux2Count) + "("
    self.visit(ctx.getChild(2))
    self.mainFunction += ","
    self.visit(ctx.getChild(4))
    self.mainFunction += ")"
    self.generate2Mux()
    self.mux2Count += 1



  def visitMux3(self, ctx):
    self.mainFunction += "Mux3_" + str(self.mux3Count) + "("
    self.visit(ctx.getChild(2))
    self.mainFunction += ","
    self.visit(ctx.getChild(4))
    self.mainFunction += ","
    self.visit(ctx.getChild(6))    
    self.mainFunction += ")"
    self.generate3Mux()
    self.mux3Count += 1


  def visitOpt(self, ctx):
    self.mainFunction += "Opt_" + str(self.optCount) + "("
    self.visitChildren(ctx)
    self.mainFunction += ")"
    self.generateOpt()
    self.optCount += 1
   


  def visitRelOp(self, ctx):
    self.mainFunction += "rel_op_" + str(self.relopCount) + "("
    self.visit(ctx.getChild(2))
    self.mainFunction += ","
    self.visit(ctx.getChild(4))
    self.mainFunction += ")"
    self.generateRelOp()
    self.relopCount += 1


  def visitConstant(self, ctx):
    self.mainFunction += "C_" + str(self.constCount) + "("
    self.mainFunction += ")"
    self.generateConstant()
    self.constCount += 1

  def visitPacketField(self, ctx):
    self.mainFunction += ctx.getText()
    self.visitChildren(ctx)
  


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

  def generate2Mux(self):
    self.helperFunctionStrings += """int Mux2_""" + str(self.mux2Count) +  """(int op1, int op2) {
    int choice = Mux2_""" + str(self.mux2Count) +  "_hole;" """
    if (choice == 0) return op1;
    else if (choice == 1) return op2;
    } \n\n"""

    self.globalholes += "int Mux2_" + str(self.mux2Count) + "_hole = ??(2);\n" 

  def generate3Mux(self):
    self.helperFunctionStrings += """int Mux3_""" + str(self.mux3Count) + """(int op1, int op2, int op3) {
    int choice = Mux3_""" + str(self.mux3Count) +  "_hole;" """
    if (choice == 0) return op1;
    else if (choice == 1) return op2;
    else if (choice == 2) return op3;
    else assert(false);
    } \n\n"""

    self.globalholes += "int Mux3_" + str(self.mux3Count) + "_hole = ??(2);\n"  
      

  def generateRelOp(self):
    self.helperFunctionStrings += """bit rel_op_""" + str(self.relopCount) + """(int operand1, int operand2) {
    int opcode = rel_op_""" + str(self.relopCount) + """_hole;
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

    self.globalholes += "int rel_op_" + str(self.relopCount) + "_hole = ??(2);\n" 

  def generateConstant(self):
    self.helperFunctionStrings += """int C_""" + str(self.constCount) + """() {
    return const_""" + str(self.constCount) + """_hole;
    }\n\n"""

    self.globalholes += "int const_" + str(self.constCount) + "_hole = ??(2);\n" 

  def generateOpt(self):
    self.helperFunctionStrings += """int Opt_""" + str(self.optCount) + """(int op1) {
    bit enable = opt_""" + str(self.optCount) + "_hole;""" + """
    if (! enable) return 0;
    return op1;
    } \n\n"""
    
    self.globalholes += "int opt_" + str(self.optCount) + "_hole = ??(1);\n"
