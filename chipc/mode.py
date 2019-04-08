from enum import Enum
class Mode(Enum):
    OPTVERIFY  = 1
    SOL_VERIFY = 2
    CODEGEN    = 3
    CEXGEN     = 4
    def is_OPTVERIFY(self):
        return self.name == 'OPTVERIFY'
    def is_SOL_VERIFY(self):
        return self.name == 'SOL_VERIFY'
    def is_CODEGEN(self):
        return self.name == 'CODEGEN'
    def is_CEXGEN(self):
        return self.name == 'CEXGEN'
