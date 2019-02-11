import sys
from antlr4 import *
from instructionLexer import instructionLexer
from instructionParser import instructionParser
from chipmunk_alu_gen_visitor import ChipmunkAluGenVisitor
 
def main(argv):
    instruction_file = argv[1]
    input_stream = FileStream(instruction_file)
    lexer = instructionLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = instructionParser(stream)
    tree = parser.instruction()
    chipmunk_alu_gen_visitor = ChipmunkAluGenVisitor(instruction_file)
    chipmunk_alu_gen_visitor.visit(tree)
    for hole in chipmunk_alu_gen_visitor.globalholes:
      print("int ", hole, " = ", "??(" + str(chipmunk_alu_gen_visitor.globalholes[hole]) + ");\n")
    print(chipmunk_alu_gen_visitor.helperFunctionStrings)
    print(chipmunk_alu_gen_visitor.mainFunction)
    
if __name__ == '__main__':
    main(sys.argv)
