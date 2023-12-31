from typing import Optional
from frontend.symbol.symbol import Symbol
from .scope import Scope,ScopeKind
default_capacity = 1024
class ScopeStack:
    def __init__(self, globalscope: Scope, capacity: int = default_capacity ) -> None:
        self.stack = [globalscope]
        self.innerstack = []
        self.globalscope = globalscope
        self.stack_capacity = capacity
        self.repeat = 0
        self.loopnum = 0
    
    def get_current_scope(self) -> Scope:
        if not self.stack:
            return self.globalscope
        else:
            return self.stack[-1]
        
    def open(self,scope:Scope) -> None:
        if(len(self.stack)<self.stack_capacity):
             self.stack.append(scope)
        else:
            raise OverflowError
        
    def close(self) -> None:
        if(len(self.stack)>=0):
             self.stack.pop()
        else:
            raise RuntimeError
        
    
    def lookup(self, name: str) -> Optional[Symbol]:
        for i in range(len(self.stack)):
            looking_scope = self.stack[len(self.stack)-1-i]
            if (looking_scope.containsKey(name)):
                return looking_scope.get(name)
        return None
    
    def openLoop(self) -> None:
        self.loopnum += 1

    def closeLoop(self) -> None:
        self.loopnum -= 1

    def inLoop(self) -> None:
        return self.loopnum > 0
    
    def loop(self):
        self.openLoop()
        self.innerstack += [self.closeLoop]
        return self

    # To declare a symbol.
    def declare(self, symbol: Symbol) -> None:
        self.get_current_scope().declare(symbol)

    # To check if this is a global scope.
    def isGlobalScope(self) -> bool:
        if(self.stack is not None):
          if (len(self.stack) == 1):
              return True
        return False
    
    def findConflict(self, name: str) -> Optional[Symbol]:
        if self.get_current_scope().containsKey(name):
            self.repeat += 1
            if(self.repeat>=2):
                raise AttributeError("Cannot redefine!")
            return self.get_current_scope().get(name)
        return None
    
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.innerstack.pop()()

    def local(self):
        self.open(Scope(ScopeKind.LOCAL))
        self.innerstack.append(self.close)
        return self

    def global_(self):
        self.open(Scope(ScopeKind.GLOBAL))
        self.innerstack.append(self.close)
        return self
    