"""Exercise 6: combine the passes.

Write `optimize(fn)` that runs constant_fold, simplify, cse, dce in a loop
until the function stops changing. Think about why order matters, and
find an input where running them in the wrong order leaves dead code behind.
"""
from mini_ir import Function


def optimize(fn: Function) -> Function:
    raise NotImplementedError
