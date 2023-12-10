from typing import Any, Optional, Union, List, Tuple

from frontend.ast.tree import Declaration, NULL
from .tacfunc import TACFunc


# A TAC program consists of several TAC functions.
class TACProg:
    def __init__(self, funcs: list[TACFunc], globals: List[Declaration]) -> None:
        self.funcs = funcs
        self.globals = globals

    def printTo(self) -> None:
        for decl in self.globals:
            if decl.init_expr is not NULL:
                print(f"GLOBAL {decl.ident.value} = {decl.init_expr}")
            else:
                print(f"GLOBAL {decl.ident.value}")

        for func in self.funcs:
            func.printTo()