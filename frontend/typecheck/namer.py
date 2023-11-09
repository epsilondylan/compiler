from typing import Protocol, TypeVar, cast

from frontend.ast.node import Node, NullType
from frontend.ast.tree import *
from frontend.ast.visitor import RecursiveVisitor, Visitor
from frontend.scope.globalscope import GlobalScope
from frontend.scope.scope import Scope, ScopeKind
from frontend.scope.scopestack import ScopeStack
from frontend.symbol.funcsymbol import FuncSymbol
from frontend.symbol.symbol import Symbol
from frontend.symbol.varsymbol import VarSymbol
from frontend.type.array import ArrayType
from frontend.type.type import DecafType
from utils.error import *
from utils.riscv import MAX_INT

"""
The namer phase: resolve all symbols defined in the abstract 
syntax tree and store them in symbol tables (i.e. scopes).
"""


class Namer(Visitor[ScopeStack, None]):
    def __init__(self) -> None:
        pass

    # Entry of this phase
    def transform(self, program: Program) -> Program:
        # Global scope. You don't have to consider it until Step 6.
        program.globalScope = GlobalScope
        ctx = ScopeStack(program.globalScope)

        program.accept(self, ctx)
        return program

    def visitProgram(self, program: Program, ctx :ScopeStack) -> None:
        # Check if the 'main' function is missing
        if not program.hasMainFunc():
            raise DecafNoMainFuncError

        for func in program.functions().values():
            func.accept(self, ctx)

    def visitFunction(self, func: Function, ctx :ScopeStack) -> None:
        func.body.accept(self, ctx)

    def visitBlock(self, block: Block, ctx :ScopeStack) -> None:
        with ctx.local(): 
          for child in block:
              child.accept(self, ctx)

    def visitReturn(self, stmt: Return, ctx :ScopeStack) -> None:
        stmt.expr.accept(self, ctx)

    """
    def visitFor(self, stmt: For, ctx :ScopeStack) -> None:

    1. Open a local scope for stmt.init.
    2. Visit stmt.init, stmt.cond, stmt.update.
    3. Open a loop in ctx (for validity checking of break/continue)
    4. Visit body of the loop.
    5. Close the loop and the local scope.
    """

    def visitIf(self, stmt: If, ctx :ScopeStack) -> None:
        stmt.cond.accept(self, ctx)
        stmt.then.accept(self, ctx)

        # check if the else branch exists
        if not stmt.otherwise is NULL:
            stmt.otherwise.accept(self, ctx)

    def visitWhile(self, stmt: While, ctx :ScopeStack) -> None:
        stmt.cond.accept(self, ctx)
        stmt.body.accept(self, ctx)

    def visitBreak(self, stmt: Break, ctx :ScopeStack) -> None:
        """
        You need to check if it is currently within the loop.
        To do this, you may need to check 'visitWhile'.

        if not in a loop:
            raise DecafBreakOutsideLoopError()
        """
        raise NotImplementedError

    """
    def visitContinue(self, stmt: Continue, ctx :ScopeStack) -> None:
    
    1. Refer to the implementation of visitBreak.
    """

    def visitDeclaration(self, decl: Declaration, ctx :ScopeStack) -> None:
        """
        1. Use ctx.lookup to find if a variable with the same name has been declared.
        2. If not, build a new VarSymbol, and put it into the current scope using ctx.declare.
        3. Set the 'symbol' attribute of decl.
        4. If there is an initial value, visit it.
        """
        
        if ctx.findConflict(decl.ident.value) is not None:
            symbol = ctx.findConflict(decl.ident.value)
            newvar = VarSymbol(decl.ident.value, decl.var_t.type)
            ctx.declare(newvar)
            decl.setattr('symbol', newvar)
        else:
            symbol = ctx.lookup(decl.ident.value)
            if(decl.getattr('symbol') is None):
                newvar = VarSymbol(decl.ident.value, decl.var_t.type)
                ctx.declare(newvar)
                decl.setattr('symbol', newvar)
        if symbol is None:
            newvar = VarSymbol(decl.ident.value, decl.var_t.type)
            ctx.declare(newvar)
            decl.setattr('symbol', newvar)
        if decl.init_expr is not NULL:
            decl.init_expr.accept(self, ctx)

    def visitAssignment(self, expr: Assignment, ctx :ScopeStack) -> None:
        if not isinstance(expr.lhs, Identifier):
            raise DecafSyntaxError('Invalid Assigment cause lhs of the expression is not a Idenfifier')
        self.visitBinary(expr, ctx)

    def visitUnary(self, expr: Unary, ctx :ScopeStack) -> None:
        expr.operand.accept(self, ctx)

    def visitBinary(self, expr: Binary, ctx :ScopeStack) -> None:
        expr.lhs.accept(self, ctx)
        expr.rhs.accept(self, ctx)

    def visitCondExpr(self, expr: ConditionExpression, ctx :ScopeStack) -> None:
        """
        1. Refer to the implementation of visitBinary.
        """
        raise NotImplementedError

    def visitIdentifier(self, ident: Identifier, ctx :ScopeStack) -> None:
        """
        1. Use ctx.lookup to find the symbol corresponding to ident.
        2. If it has not been declared, raise a DecafUndefinedVarError.
        3. Set the 'symbol' attribute of ident.
        """
        symbol = ctx.lookup(ident.value)
        if symbol is None:
            raise DecafUndefinedFuncError('Invalid behavior because identifier is not defined')
        ident.setattr('symbol',symbol)

    def visitIntLiteral(self, expr: IntLiteral, ctx :ScopeStack) -> None:
        value = expr.value
        if value > MAX_INT:
            raise DecafBadIntValueError(value)
