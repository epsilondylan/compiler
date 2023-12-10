from enum import Enum, auto, unique


# Kinds of instructions.
@unique
class InstrKind(Enum):
    # Labels.
    LABEL = auto()
    # Sequential instructions (unary operations, binary operations, etc).
    SEQ = auto()
    # Branching instructions.
    JMP = auto()
    # Branching with conditions.
    COND_JMP = auto()
    # Return instruction.
    RET = auto()
    CALL = auto()


# Kinds of unary operations.
@unique
class TacUnaryOp(Enum):
    NEG = auto()
    NOT = auto()
    SEQZ = auto()
    SNEZ = auto()

# Kinds of binary operations.
@unique
class TacBinaryOp(Enum):
    OR = auto()
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    REM = auto()
    EQU = auto()
    LEQ = auto()
    SLT = auto()
    NEQ = auto()
    SGT = auto()
    GEQ = auto()
    AND = auto()

# Kinds of branching with conditions.
@unique
class CondBranchOp(Enum):
    BEQ = auto()
    BNE = auto()
