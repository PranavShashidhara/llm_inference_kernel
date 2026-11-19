"""Exercise 3: dead code elimination (DCE).

Remove pure ops whose result is never used. Never remove ops with side
effects (print, ret).

Think: removing one op can make another one dead. Walk BACKWARDS over the
ops, keeping a set of 'live' values, so one pass is enough.
"""
from mini_ir import Function, PURE_OPS, SIDE_EFFECT_OPS


def dce(fn: Function) -> Function:
    raise NotImplementedError
