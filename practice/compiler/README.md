# Compiler practice

Goal: move from reading (`docs/compiler/`) to doing. Do them in order.

| # | Where | What | Time |
|---|-------|------|------|
| 1 | `paper/ex1_ssa_by_hand.md` | SSA, phi/block args, CSE legality on paper | 30 min |
| 2 | `exercises/ex2_constant_folding.py` | constant folding | 30 min |
| 3 | `exercises/ex3_dce.py` | dead code elimination (backward walk) | 30 min |
| 4 | `exercises/ex4_cse.py` | CSE with hash keys + commutativity | 45 min |
| 5 | `exercises/ex5_peephole.py` | pattern rewriting to fixpoint (MLIR's core idea) | 1 h |
| 6 | `exercises/ex6_pipeline.py` | pass ordering | 30 min |
| 7 | `exercises/ex7_dominance_bonus.md` | CFGs, dominance, why CSE needs it | 1-2 h |
| 8 | `mlir/` | run real `mlir-opt` passes, read matching C++ | 1-2 h |

## How to work
    cd practice/compiler
    python3 -m unittest tests.test_exercises -v            # all
    python3 -m unittest tests.test_exercises.T4 -v         # one exercise

- `mini_ir/ir.py` is a tiny SSA IR (parser, printer, interpreter). Read it
  first (~100 lines). `run()` lets you check an optimization kept behavior.
- Print IR before and after each pass while debugging.
- Rules: implement each pass yourself; don't peek at an LLM's answer
  until your tests pass. Then compare with how MLIR does it.

## After these
1. MLIR Toy tutorial, chapters 1-4 (typed in by hand).
2. Rewrite ex4/ex5 as C++ MLIR patterns.
3. Read `mlir/lib/Transforms/CSE.cpp` and `Canonicalizer.cpp`.
