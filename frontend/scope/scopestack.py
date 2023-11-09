from typing import Optional
from frontend.symbol.symbol import Symbol
from .scope import Scope,ScopeKind

class ScopeStack:
    defaultMaxScopeDepth = 256

    def __init__(
        self, globalscope: Scope, scopeDepth: int = defaultMaxScopeDepth
    ) -> None:
        self.globalscope = globalscope
        self.stack = [globalscope]
        self.scopeDepth = scopeDepth

        self.loopDepth = 0
        self.close_stack = []

    # To get the current scope (stack top).
    def currentScope(self) -> Scope:
        if not self.stack:
            return self.globalscope
        return self.stack[-1]

    # To open a new scope.
    def open(self, scope: Scope) -> None:
        if len(self.stack) < self.scopeDepth:
            self.stack.append(scope)
        else:
            raise ScopeStackOverflow

    # To close the current scope.
    def close(self) -> None:
        self.stack.pop()

    # To check if it is in the global scope.
    def isGlobalScope(self) -> bool:
        return self.currentScope().isGlobalScope()

    # To declare a new symbol in the current scope.
    def declare(self, symbol: Symbol) -> None:
        self.currentScope().declare(symbol)

    # To find if there is a name conflict in the current scope.
    def findConflict(self, name: str) -> Optional[Symbol]:
        if self.currentScope().containsKey(name):
            return self.currentScope().get(name)
        return None

    # To find the symbol via name from top to bottom.
    def lookup(self, name: str) -> Optional[Symbol]:
        stackSize = len(self.stack)
        for d in range(stackSize - 1, -1, -1):
            scope = self.stack[d]
            if scope.containsKey(name):
                return scope.get(name)
        return None

    # Maintaining the number of loops at current position (to check if a 'break' or 'continue' is valid).
    def openLoop(self) -> None:
        self.loopDepth += 1

    def closeLoop(self) -> None:
        self.loopDepth -= 1

    def inLoop(self) -> None:
        return self.loopDepth > 0

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_stack.pop()()

    def local(self):
        self.open(Scope(ScopeKind.LOCAL))
        self.close_stack += [self.close]
        return self

    def global_(self):
        self.open(Scope(ScopeKind.GLOBAL))
        self.close_stack += [self.close]
        return self

    def loop(self):
        self.openLoop()
        self.close_stack += [self.closeLoop]
        return self

    def __del__(self):
        csl = len(self.close_stack)
        assert csl == 0, f"Improper usage of context, remaining size {csl}"