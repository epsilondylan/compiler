from frontend.ast.node import T, Optional
from frontend.ast.tree import T, Call, Function, Optional
from frontend.ast import node
from frontend.ast.tree import *
from frontend.ast.visitor import T, Visitor
from frontend.symbol.varsymbol import VarSymbol
from frontend.type.array import ArrayType
from utils.label.funclabel import *
from utils.label.label import Label, LabelKind
from utils.label.blocklabel import BlockLabel
from utils.label.funclabel import FuncLabel
from utils.tac import tacop
from utils.tac.temp import Temp
from utils.tac.tacinstr import *
from utils.tac.tacfunc import TACFunc
from utils.tac.tacprog import TACProg
from utils.tac.tacvisitor import TACVisitor


"""
The TAC generation phase: translate the abstract syntax tree into three-address code.
"""


class LabelManager:
    """
    A global label manager (just a counter).
    We use this to create unique (block) labels accross functions.
    """

    def __init__(self):
        self.labels = {}
        self.funcs = []
        self.nextTempLabelId = 1

    def putFuncLabel(self, name: str) -> None:
        self.labels[name] = FuncLabel(name)

    def getFuncLabel(self, name: str) -> FuncLabel:
        return self.labels[name]
    
    def freshLabel(self) -> BlockLabel:
        self.nextTempLabelId += 1
        return BlockLabel(str(self.nextTempLabelId))


class TACFuncEmitter(TACVisitor):
    """
    Translates a minidecaf (AST) function into low-level TAC function.
    """

    def __init__(
        self, entry: FuncLabel, numArgs: int, labelManager: LabelManager,
    ) -> None:
        self.labelManager = labelManager
        self.func = TACFunc(entry, numArgs)
        self.visitLabel(entry)
        self.nextTempId = 0
        self.continueLabelStack = []
        self.breakLabelStack = []

    # To get a fresh new temporary variable.
    def freshTemp(self) -> Temp:
        temp = Temp(self.nextTempId)
        self.nextTempId += 1
        return temp

    # To get a fresh new label (for jumping and branching, etc).
    def freshLabel(self) -> Label:
        return self.labelManager.freshLabel()
    
    # To count how many temporary variables have been used.
    def getUsedTemp(self) -> int:
        return self.nextTempId
    
    
    # In fact, the following methods can be named 'appendXXX' rather than 'visitXXX'.
    # E.g., by calling 'visitAssignment', you add an assignment instruction at the end of current function.
    def visitAssignment(self, dst: Temp, src: Temp) -> Temp:
        self.func.add(Assign(dst, src))
        return src

    def visitLoad(self, value: Union[int, str]) -> Temp:
        temp = self.freshTemp()
        self.func.add(LoadImm4(temp, value))
        return temp

    def visitUnary(self, op: UnaryOp, operand: Temp) -> Temp:
        temp = self.freshTemp()
        self.func.add(Unary(op, temp, operand))
        return temp

    def visitUnarySelf(self, op: UnaryOp, operand: Temp) -> None:
        self.func.add(Unary(op, operand, operand))

    def visitBinary(self, op: BinaryOp, lhs: Temp, rhs: Temp) -> Temp:
        temp = self.freshTemp()
        self.func.add(Binary(op, temp, lhs, rhs))
        return temp

    def visitBinarySelf(self, op: BinaryOp, lhs: Temp, rhs: Temp) -> None:
        self.func.add(Binary(op, lhs, lhs, rhs))

    def visitBranch(self, target: Label) -> None:
        self.func.add(Branch(target))

    def visitCondBranch(self, op: CondBranchOp, cond: Temp, target: Label) -> None:
        self.func.add(CondBranch(op, cond, target))

    def visitReturn(self, value: Optional[Temp]) -> None:
        self.func.add(Return(value))

    def visitLabel(self, label: Label) -> None:
        self.func.add(Mark(label))

    def visitMemo(self, content: str) -> None:
        self.func.add(Memo(content))

    def visitRaw(self, instr: TACInstr) -> None:
        self.func.add(instr)

    def visitEnd(self) -> TACFunc:
        if (len(self.func.instrSeq) == 0) or (not self.func.instrSeq[-1].isReturn()):
            self.func.add(Return(None))
        self.func.tempUsed = self.getUsedTemp()
        return self.func
    
    def visitCall(self, func_label: Label, mid: Temp, parameterList: List[Temp]) -> None:
        self.func.add(Call(func_label, mid, parameterList))

    # To open a new loop (for break/continue statements)
    def openLoop(self, breakLabel: Label, continueLabel: Label) -> None:
        self.breakLabelStack.append(breakLabel)
        self.continueLabelStack.append(continueLabel)

    # To close the current loop.
    def closeLoop(self) -> None:
        self.breakLabelStack.pop()
        self.continueLabelStack.pop()

    # To get the label for 'break' in the current loop.
    def getBreakLabel(self) -> Label:
        return self.breakLabelStack[-1]

    # To get the label for 'continue' in the current loop.
    def getContinueLabel(self) -> Label:
        return self.continueLabelStack[-1]


class Handler:
    def __init__(self, funcs: List[Function]) -> None:
        self.funcs = []
        self.labelManager = LabelManager()
        for func in funcs:
            self.funcs.append(func)
            self.labelManager.getFuncLabel(func.ident.value)

    def visitMainFunc(self) -> TACFuncEmitter:
        entry = MAIN_LABEL
        return TACFuncEmitter(entry, 0, self.ctx)

    def visitFunc(self, name: str, numArgs: int) -> TACFuncEmitter:
        entry = self.labelManager.getFuncLabel(name)
        return TACFuncEmitter(entry, numArgs, self.labelManager)

    def visitEnd(self) -> TACProg:
        return TACProg(self.labelManager.funcs)

class TACGen(Visitor[TACFuncEmitter, None]):
    def __init__(self) -> None:
        pass

    # Entry of this phase
    def transform(self, program: Program) -> TACProg:
        handler = Handler(program.functions().values())
        for funcName, astFunc in program.functions().items():
            if astFunc.body is NULL:
                continue
            argnum = len(astFunc.parameterList)
            emitter = handler.visitFunc(FuncLabel(funcName), argnum)
            astFunc.accept(self, emitter)
            emitter.visitEnd()
        return handler.visitEnd()

    def visitBlock(self, block: Block, mv: TACFuncEmitter) -> None:
        for child in block:
            child.accept(self, mv)

    def visitReturn(self, stmt: Return, mv: TACFuncEmitter) -> None:
        stmt.expr.accept(self, mv)
        mv.visitReturn(stmt.expr.getattr("val"))

    def visitBreak(self, stmt: Break, mv: TACFuncEmitter) -> None:
        mv.visitBranch(mv.getBreakLabel())

    def visitIdentifier(self, ident: Identifier, mv: TACFuncEmitter) -> None:
        """
        1. Set the 'val' attribute of ident as the temp variable of the 'symbol' attribute of ident.
        """
        ident.setattr('val',ident.getattr('symbol').temp)

    def visitDeclaration(self, decl: Declaration, mv: TACFuncEmitter) -> None:
        """
        1. Get the 'symbol' attribute of decl.
        2. Use mv.freshTemp to get a new temp variable for this symbol.
        3. If the declaration has an initial value, use mv.visitAssignment to set it.
        """
        sym: VarSymbol = decl.getattr('symbol')
        temp = mv.freshTemp()
        sym.temp = temp
        if decl.init_expr is not NULL:
            decl.init_expr.accept(self, mv)
            mv.visitAssignment(temp, decl.init_expr.getattr('val'))

    def visitAssignment(self, expr: Assignment, mv: TACFuncEmitter) -> None:
        """
        1. Visit the right hand side of expr, and get the temp variable of left hand side.
        2. Use mv.visitAssignment to emit an assignment instruction.
        3. Set the 'val' attribute of expr as the value of assignment instruction.
        """
        expr.rhs.accept(self, mv)
        expr.lhs.accept(self, mv)
        expr.setattr('val',mv.visitAssignment(expr.lhs.getattr('val'),expr.rhs.getattr('val')))

    def visitIf(self, stmt: If, mv: TACFuncEmitter) -> None:
        stmt.cond.accept(self, mv)
        if stmt.otherwise is NULL:
            skipLabel = mv.freshLabel()
            mv.visitCondBranch(
                tacop.CondBranchOp.BEQ, stmt.cond.getattr("val"), skipLabel
            )
            stmt.then.accept(self, mv)
            mv.visitLabel(skipLabel)
        else:
            skipLabel = mv.freshLabel()
            exitLabel = mv.freshLabel()
            mv.visitCondBranch(
                tacop.CondBranchOp.BEQ, stmt.cond.getattr("val"), skipLabel
            )
            stmt.then.accept(self, mv)
            mv.visitBranch(exitLabel)
            mv.visitLabel(skipLabel)
            stmt.otherwise.accept(self, mv)
            mv.visitLabel(exitLabel)

    def visitWhile(self, stmt: While, mv: TACFuncEmitter) -> None:
        beginLabel = mv.freshLabel()
        loopLabel = mv.freshLabel()
        breakLabel = mv.freshLabel()
        mv.openLoop(breakLabel, loopLabel)

        mv.visitLabel(beginLabel)
        stmt.cond.accept(self, mv)
        mv.visitCondBranch(tacop.CondBranchOp.BEQ, stmt.cond.getattr("val"), breakLabel)

        stmt.body.accept(self, mv)
        mv.visitLabel(loopLabel)
        mv.visitBranch(beginLabel)
        mv.visitLabel(breakLabel)
        mv.closeLoop()
    
    def visitContinue(self, stmt: Continue, mv: TACFuncEmitter) -> None:
        mv.visitBranch(mv.getContinueLabel())

    def visitFor(self, stmt: For, mv: TACFuncEmitter) -> None:
        """
        _T1 = 0
        _T0 = _T1                 # int i = 0;
        _L1:                          # begin label
        _T2 = 5
        _T3 = LT _T0, _T2
        BEQZ _T3, _L3              # i < 5;
        _L2:                          # loop label
        _T4 = 1
        _T5 = ADD _T0, _T4
        _T0 = _T5                 # i = i + 1;
        JUMP _L1
        _L3:                          # break label
        """
        beginLabel = mv.freshLabel()
        loopLabel = mv.freshLabel()
        breakLabel = mv.freshLabel()
        stmt.init.accept(self, mv)
        mv.openLoop(breakLabel, loopLabel)
        mv.visitLabel(beginLabel)
        stmt.cond.accept(self, mv)
        if stmt.cond.getattr("val") is not None:
            mv.visitCondBranch(tacop.CondBranchOp.BEQ, stmt.cond.getattr("val"), breakLabel)
        stmt.body.accept(self, mv)
        mv.visitLabel(loopLabel)
        stmt.update.accept(self, mv)
        mv.visitBranch(beginLabel)
        mv.visitLabel(breakLabel)
        mv.closeLoop()

    def visitUnary(self, expr: Unary, mv: TACFuncEmitter) -> None:
        expr.operand.accept(self, mv)

        op = {
            node.UnaryOp.Neg: tacop.TacUnaryOp.NEG,
            node.UnaryOp.BitNot: tacop.TacUnaryOp.NOT,
            node.UnaryOp.LogicNot: tacop.TacUnaryOp.SEQZ,
            
            # You can add unary operations here.
        }[expr.op]
        expr.setattr("val", mv.visitUnary(op, expr.operand.getattr("val")))

    def visitBinary(self, expr: Binary, mv: TACFuncEmitter) -> None:
        expr.lhs.accept(self, mv)
        expr.rhs.accept(self, mv)

        op = {
            node.BinaryOp.Add: tacop.TacBinaryOp.ADD,
            node.BinaryOp.Sub : tacop.TacBinaryOp.SUB,
            node.BinaryOp.LogicOr: tacop.TacBinaryOp.OR,
            node.BinaryOp.LogicAnd :tacop.TacBinaryOp.AND,
            node.BinaryOp.Div : tacop.TacBinaryOp.DIV,
            node.BinaryOp.Mul : tacop.TacBinaryOp.MUL,
            node.BinaryOp.Mod : tacop.TacBinaryOp.REM,
            node.BinaryOp.LE : tacop.TacBinaryOp.LEQ,
            node.BinaryOp.NE : tacop.TacBinaryOp.NEQ,
            node.BinaryOp.EQ : tacop.TacBinaryOp.EQU,
            node.BinaryOp.LT : tacop.TacBinaryOp.SLT,
            node.BinaryOp.GE : tacop.TacBinaryOp.GEQ,
            node.BinaryOp.GT : tacop.TacBinaryOp.SGT,
            # You can add binary operations here.
        }[expr.op]
        expr.setattr(
            "val", mv.visitBinary(op, expr.lhs.getattr("val"), expr.rhs.getattr("val"))
        )
  
    def visitFunction(self, func: Function, mv: TACFuncEmitter) -> None:
        for param in func.parameterList:
            param.accept(self, mv)
        func.body.accept(self, mv)
    
    def visitCall(self, call: Call, mv: TACFuncEmitter) -> None:
        param_temp = []
        for arg in call.argument_list:
            arg.accept(self, mv)
            if not (arg.getattr('val')):
                raise SyntaxError('Error in arg fetching!')
            param_temp.append(arg.getattr('val'))
        ret = mv.freshTemp()
        call.setattr('val', ret)
        func_label = mv.labelManager.getFuncLabel(call.ident.value)
        mv.visitCall(func_label, ret, param_temp)
    
    def visitParameter(self, that: Parameter, mv: TACFuncEmitter) -> None:
        temp = self.visitDeclaration(that, mv)
        mv.func.addTempArgs(temp)

    def visitCondExpr(self, expr: ConditionExpression, mv: TACFuncEmitter) -> None:
        expr.cond.accept(self, mv)
        skipLabel = mv.freshLabel()
        exitLabel = mv.freshLabel()
        tempValue = mv.freshTemp()
        mv.visitCondBranch(tacop.CondBranchOp.BEQ, expr.cond.getattr("val"), skipLabel)
        expr.then.accept(self, mv)
        mv.visitAssignment(tempValue, expr.then.getattr("val"))
        mv.visitBranch(exitLabel)
        mv.visitLabel(skipLabel)
        expr.otherwise.accept(self, mv)
        mv.visitAssignment(tempValue, expr.otherwise.getattr("val"))
        mv.visitLabel(exitLabel)
        expr.setattr('val', tempValue)

    def visitIntLiteral(self, expr: IntLiteral, mv: TACFuncEmitter) -> None:
        expr.setattr("val", mv.visitLoad(expr.value))
   