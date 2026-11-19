"""Exercise 2: constant folding.

If an op's operands are all constants, compute it at compile time and
replace the op with a `const`.

    %a = const 2            %a = const 2
    %b = const 3     ->     %b = const 3
    %c = add %a, %b         %c = const 5

Hint: keep a dict {value_name: int} of known constants while walking ops.
Note that folding can enable more folding (a chain), and one forward pass
handles that because SSA defs always come before uses.
"""
from mini_ir import Function, Op


def constant_fold(fn: Function) -> Function:
    raise NotImplementedError
