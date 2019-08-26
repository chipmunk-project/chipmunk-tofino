from enum import Enum


class Mode(Enum):
    SOL_VERIFY = 2  # Deprecated, no longer in use.
    CODEGEN = 3
    VERIFY = 4

    def is_SOL_VERIFY(self):
        return self.name == 'SOL_VERIFY'

    def is_CODEGEN(self):
        return self.name == 'CODEGEN'

    def is_VERIFY(self):
        return self.name == 'VERIFY'
