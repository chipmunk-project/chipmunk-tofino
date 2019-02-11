import sys
from antlr4 import *
from instructionLexer import instructionLexer
from instructionParser import instructionParser
from domino_alu_gen_visitor import DominoAluGenVisitor
 
def main(argv):
    instruction_file = argv[1]
    input_stream = FileStream(instruction_file)
    lexer = instructionLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = instructionParser(stream)
    tree = parser.instruction()
    domino_alu_gen_visitor = DominoAluGenVisitor(instruction_file)
    domino_alu_gen_visitor.visit(tree)
 
if __name__ == '__main__':
    main(sys.argv)
