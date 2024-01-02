from typing import Any, Optional, Union, List, Tuple

from frontend.ast.tree import Declaration, NULL
from .tacfunc import TACFunc


# A TAC program consists of several TAC functions.
class TACProg:
    def __init__(self, funcs: list[TACFunc]) -> None:
        self.funcs = funcs
        
    def printTo(self) -> None:
        for func in self.funcs:
            func.printTo()