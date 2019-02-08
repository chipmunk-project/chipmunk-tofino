from instructionVisitor import instructionVisitor
from instructionParser import instructionParser
class DominoAluGenVisitor(instructionVisitor):
  def __init__(self, instruction_file):
    self.instruction_file = instruction_file

  def visitGuarded_updates(self, ctx):
    print("include \"muxes.sk\";")
    print("include \"rel_ops.sk\";")
    print("include \"constants.sk\";")
    print("StateResult ", self.instruction_file.strip(".instruction"), "(",
          "int state_1, int state_2, int pkt_1, int pkt_2, int pkt_3, int pkt_4, int pkt_5 ) {")
    self.visitChildren(ctx)
    print("StateResult ret = new StateResult();")
    print("ret.result_state_1 = state_1;")
    print("ret.result_state_2 = state_2;")
    print("return ret;}")

  def visitGuarded_update(self, ctx):
    assert(ctx.getChildCount() == 3)
    assert(ctx.getChild(1).getText() == ":")
    print("if (" + ctx.getChild(0).getText() + ") {" + ctx.getChild(2).getText() + "; }")
