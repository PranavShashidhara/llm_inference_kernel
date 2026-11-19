"""Exercise 5: pattern rewriting (the core idea of MLIR passes).

Implement these algebraic simplifications as separate small patterns:

    x * 1  -> x          x + 0 -> x          x - 0 -> x
    x * 0  -> const 0    x - x -> const 0

Structure it like MLIR: a list of pattern functions, each takes (op,
consts) and returns either None (no match) or a replacement. A driver
applies patterns until nothing changes (a fixpoint).

When a pattern replaces `%r = mul %x, %one` by `%x`, you must rewrite
all uses of %r to %x (replace_all_uses) and erase the op.
"""
from mini_ir import Function, Op, replace_all_uses


def simplify(fn: Function) -> Function:
    raise NotImplementedError
