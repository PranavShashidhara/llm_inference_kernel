"""Exercise 4: common subexpression elimination (CSE).

If two pure ops have the same opcode, same operands (and same attr for
const), the second is redundant: replace its uses with the first result
and delete it.

Hint: dict keyed by (opcode, tuple(operands), attr) -> result name.
Use replace_all_uses from mini_ir. Because of SSA you need no check that
operands were 'reassigned in between'. That is the point.

Bonus: add and mul are commutative, so `add %a, %b` == `add %b, %a`.
Sort the operands in the key for those.
"""
from mini_ir import Function, PURE_OPS, replace_all_uses


def cse(fn: Function) -> Function:
    raise NotImplementedError
