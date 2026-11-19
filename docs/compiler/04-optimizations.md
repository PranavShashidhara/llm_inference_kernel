# 4. Middle-end: analyses and optimizations

The middle-end takes the IR and rewrites it so it does the **same thing with
less work**. It is built out of many small, independent steps called
**passes**.

Prerequisite: [03-ir-and-ssa.md](03-ir-and-ssa.md) (def, use, pure, side
effect). The key facts used below:

- A **use** is an instruction that reads a value; a **def** creates it.
- A **def-use list** is every use of a value.
- A **pure** op has no side effects and its result depends only on its
  operands.

## The big picture (start here)

An optimization is a rewrite that keeps the program's **behavior the same**
but does **less work**. Every optimization asks two questions:

1. **Can I spot a wasteful pattern?** A duplicate computation, an unused
   result, something I could compute early.
2. **Is it safe to change?** Would anyone be able to tell the difference?

The second question is why **pure** matters so much. A pure op only computes a
value, so it can be deleted, merged or moved freely. An op with a side effect
(`print`, `store`) is observable, so it must be left alone.

### One running example

```
x = a + b
y = a + b
z = x * 1
w = y * 100        // never used later
print(z)
```

Each optimization fixes one specific waste:

| Step | What it notices | Result |
|---|---|---|
| **CSE** | `a + b` is computed twice | `y` reuses `x` (uses of `y` now point to `x`) |
| **Canonicalization** | `x * 1` is just `x` | `z` becomes `x` |
| **Constant folding** | nothing here (`2 + 3` would become `5`) | |
| **DCE** | `w` is never used and `*` has no side effects | `w` is deleted |

Result:

```
x = a + b
print(x)
```

Five lines became two with the same output. Try it yourself on paper first,
then run `practice/compiler/mlir/05_pipeline.mlir` through
`mlir-opt --canonicalize --cse` and compare.

### The optimizations in plain words

- **Constant folding**: inputs known now? Compute at compile time, not on
  every run.
- **DCE**: nobody uses the result and there is no side effect? Delete it.
- **CSE**: same computation twice? Do it once and reuse the answer.
- **Canonicalization**: rewrite to a standard simple form (`x + 0` -> `x`)
  so other passes have fewer cases.
- **Inlining**: copy a function body into the caller. The real win is that
  the compiler can now optimize across the old function boundary.
- **LICM**: a value that doesn't change inside a loop is computed once before
  it.
- **Loop tiling / unrolling / fusion**: restructure loops for cache and
  speed. Very important for ML kernels.
- **DSE**: DCE for memory. A write overwritten before anyone reads it is
  useless.

The detailed sections below cover each one.

## Passes, analyses and transforms

- An **analysis** computes facts about the IR (which values are constants,
  which blocks dominate which). It does **not** change the IR.
- A **transform** rewrites the IR.
- Both are packaged as **passes**. A **pass manager** runs a list of them in
  order: a **pass pipeline**.

Passes **cooperate**: one pass creates opportunities for the next. In the
Toy example:

```
inlining -> constant folding -> CSE -> DCE
(exposes)    (makes things      (merges    (removes what
              identical)         duplicates) is left over)
```

## Overview

| Optimization | Idea |
|---|---|
| Constant folding | `2 + 3` -> `5` at compile time |
| Constant propagation | replace uses of a known constant |
| Dead code elimination (DCE) | delete pure ops whose results are never used |
| Dead store elimination (DSE) | delete a store that is overwritten before being read |
| CSE (common subexpression elimination) | compute identical expressions once |
| Inlining | replace a call with the callee's body |
| Loop-invariant code motion (LICM) | move computation that doesn't change out of a loop |
| Loop unrolling / tiling / fusion | improve locality, reduce overhead |
| Canonicalization | rewrite to a standard form (`x + 0` -> `x`) |
| Shape inference | work out tensor shapes by propagating known ones |

Each one is explained below.

## Why side effects matter for every optimization

Whether an optimization is safe depends on whether it can change what the
program does. Deleting or merging an op is only safe if the op is **pure**:

- A **side effect** is any observable action besides producing a result:
  writing memory (`store`), printing, possibly crashing.
- Two identical `load`s might return different values if a `store` happens
  between them, so they're **not** pure and can't be merged.
- Ops like `toy.add` and `toy.transpose` are declared `Pure`, so the
  optimizer may freely delete, merge and move them.

## Dead code elimination (DCE)

**Delete instructions whose results are never used, provided deleting them
cannot change what the program does.**

An op is **dead** when both are true:
1. **No uses**: its def-use list is empty (nobody reads the result).
2. **No side effects**: it is pure, so removing it changes nothing
   observable.

```
%1 = toy.transpose(%0)
%2 = toy.mul %1, %1        // def-use list of %2 is empty, mul is pure -> dead
toy.print %1
```

After DCE:

```
%1 = toy.transpose(%0)
toy.print %1
```

Why both conditions:
- *No uses* alone isn't enough: `toy.print` and `store` have no used result
  but deleting them changes the output or memory.
- *Pure* alone isn't enough: a pure op whose result **is** used obviously
  can't be deleted.

**It cascades.** Deleting one op can make others dead, so the pass repeats
until nothing more can be removed:

```
%1 = toy.transpose(%0)     // used only by %2
%2 = toy.mul %1, %1        // unused -> delete
```

Once `%2` is gone, `%1` has no users, so it's dead too, and so is whatever
fed `%1`.

How it works (SSA makes this cheap):
1. Look at an op.
2. If it's pure and its def-use list is empty, erase it.
3. Its operands lose one use each, so check their defining ops next.

Where dead code comes from: rarely from the programmer, usually from other
passes:
- **Inlining**: the unused `c` in the [worked example](07-worked-example.md).
- **Constant folding**: the old, folded ops are left unused.
- **CSE**: after two ops are merged, the duplicate has no uses.

That's why DCE runs *after* those passes. In MLIR, trivially dead ops are
removed by `canonicalize`; the `symbol-dce` pass removes unused functions.

## Dead store elimination (DSE)

The **memory** version of DCE: delete a `store` whose value is overwritten
before anyone reads it.

```
store %a, %buf[0]             // dead: overwritten below, never read in between
store %b, %buf[0]
```

DCE can't do this, because a store has a side effect. DSE needs **alias
analysis** (proving nothing else reads or points to that location in
between).

## Constant folding

Compute an operation **at compile time** when all its inputs are known
constants.

```
%0 = arith.constant 2 : i32
%1 = arith.constant 3 : i32
%2 = arith.addi %0, %1        ->     %2 = arith.constant 5 : i32
```

It cascades: once `%2` is a constant, ops that use it may fold too. That
chain is called **constant propagation**.

It also works on dialect ops: a `toy.reshape` of a constant becomes a
constant of the new shape. In MLIR this is each op's `fold()` hook.

## CSE (common subexpression elimination)

If the same computation appears more than once, do it once and reuse the
result.

```
y = (a * b) + 1
z = (a * b) * 2           // a*b is a "common subexpression"

        |  CSE
        v
t = a * b
y = t + 1
z = t * 2
```

In the IR:

```
%1 = toy.transpose(%0)
%2 = toy.transpose(%0)        // same op, same operand as %1
%3 = toy.mul %1, %2
        |  CSE
        v
%1 = toy.transpose(%0)
%3 = toy.mul %1, %1           // uses of %2 repointed to %1; %2 is now dead
```

Two ops are "the same" when:
1. They have the same **op type** (`transpose`).
2. They have the same **operands**. In SSA, the same name means the same
   value, since values never change.
3. They have the same **attributes** (constant settings on the op).
4. The op is **pure**.

**One more condition: dominance.** The first copy must always run before the
second (it must **dominate** it, see [03](03-ir-and-ssa.md)). If the first
`a * b` is only computed in the `then` branch and the second is after the
merge, you can't reuse it, because the `else` path never computed it.

The leftover duplicate is then removed by DCE.

## Inlining

Replace a call with the body of the function being called.

```
toy.func @square(%x) { %r = toy.mul %x, %x ; toy.return %r }
%y = toy.generic_call @square(%a)
        |  inline
        v
%y = toy.mul %a, %a
```

Benefits: removes call overhead, and, more importantly, **exposes more
optimization**. After inlining the callee's ops sit next to the caller's, so
constant folding, CSE and shape inference can see across the old function
boundary. Cost: code size grows.

In MLIR the dialect must implement the inliner interface
(`DialectInlinerInterface`) and its call ops must implement
`CallOpInterface`.

## Loop optimizations (names you'll meet)

- **Loop-invariant code motion (LICM)**: if something computed inside a
  loop doesn't change between iterations, compute it once before the loop.
- **Loop unrolling**: repeat the loop body several times per iteration to
  reduce branch overhead.
- **Loop tiling**: split a big loop into blocks that fit in cache.
- **Loop fusion**: merge two loops over the same range into one (removes
  intermediate buffers).

These work best on structured loops (`affine.for`), which is why MLIR keeps
loops high-level for as long as possible.

## Shape inference

Tensors have **shapes** (`2x3`). In Toy, functions are written without
shapes, so the compiler **propagates** known shapes forward: `transpose` of
`2x3` is `3x2`; `mul` of two `3x2` is `3x2`. Unknown shapes
(`tensor<*xf64>`) become known ones. Static shapes are what later make loop
bounds known at compile time.

## Pattern rewriting and canonicalization

Many optimizations are: "if you see this subgraph, replace it with that one."

```
match:    transpose(transpose(x))
rewrite:  x
```

- A **pattern** = a match + a rewrite.
- A **driver** applies patterns repeatedly until nothing changes (a **fixed
  point**).
- **Canonicalization** = rewriting into a standard form so later passes need
  fewer special cases (`x + 0` -> `x`; `reshape(reshape(x))` ->
  `reshape(x)`).

MLIR has this built in (`RewritePattern`, `OpRewritePattern`, declarative
**DRR** rules). The `canonicalize` pass collects every op's folding hook and
patterns, plus trivial DCE, and runs them to a fixed point.

Key requirement: every rewrite must preserve the program's meaning, which is
why ops declare whether they have side effects.

## Where it gets hard

- **Side effects and memory.** Two `load`s of the same address may return
  different values if a `store` sits between them. Safe optimization there
  needs **alias analysis**: can these two pointers refer to the same memory?
- **Control flow.** CSE across branches needs the first computation to
  **dominate** the second (see CSE above and [03](03-ir-and-ssa.md)).
- **Pass order.** CSE doesn't delete the duplicate, it only redirects its
  uses, leaving it unused for DCE to remove. That's why DCE runs late and why
  real compilers loop the pipeline until nothing changes.

## Key takeaways

- Optimizations are small **passes**; they set each other up.
- **DCE** deletes unused pure ops. **CSE** merges duplicates. **Folding**
  computes constants early. **Inlining** exposes more to optimize.
- All of these are cheap **because of SSA**: use-def and def-use links answer
  "who uses this?" and "is this the same?" immediately.
- All of them need to know which ops are **pure**.
