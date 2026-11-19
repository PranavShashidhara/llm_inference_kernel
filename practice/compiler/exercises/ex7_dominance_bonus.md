# Exercise 7 (bonus, paper + code): going beyond one block

The mini IR has one block, so CSE is trivially "global". Real IR has a CFG.

1. Draw a CFG: entry -> (then | else) -> merge. Put `%x = add %a, %b` in
   entry and again in `merge`. Can the second be replaced by the first? Why?
2. Now put the add in `then` and again in `merge`. Can it be replaced? Why not?
3. Compute the dominator sets for each block in your diagram by hand.
4. State the rule: CSE of op B by op A is legal iff ______ .
5. (code) Extend `ir.py` with a `br`/`cond_br` and blocks, then compute
   dominators with the iterative algorithm
   `dom(n) = {n} ∪ ⋂ dom(pred)` until fixpoint.
