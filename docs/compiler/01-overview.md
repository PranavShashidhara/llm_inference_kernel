# 1. What a compiler is

**Read this first.** If you only remember one thing from this whole folder:

> A compiler translates a program from one form to another, in several small
> steps, without changing what the program means.

Everything else (IR, SSA, passes, dialects, lowering) is a detail of *how* it
does those small steps.

---

## The idea

You write code in a language humans like (Python-like, C-like, Toy). The
machine only runs low-level instructions (`add rax, rbx`). A compiler is the
program that bridges the two.

It doesn't do it in one jump. It does it in stages, like translating a book
from English to Japanese by first writing a neutral outline, tidying the
outline, and only then writing the Japanese:

```
source code --> [ frontend ] --> IR --> [ middle-end ] --> better IR --> [ backend ] --> machine code
 (text)          (understand)    (neutral    (improve)                      (target the     (what the
                                  outline)                                   hardware)       CPU/GPU runs)
```

**IR** = *Intermediate Representation*: the neutral "outline" form that the
compiler works on in the middle. It is neither the source language nor
machine code.

## The three phases

| Phase | Job | Input -> Output | Knows about the source language? | Knows about the hardware? |
|---|---|---|---|---|
| **Frontend** | Understand the program | text -> IR | **yes** | no |
| **Middle-end** | Make the IR better (faster, smaller) | IR -> better IR | no | no |
| **Backend** | Produce code for one specific target | IR -> machine code | no | **yes** |

- **Frontend**: reads source text, checks it, and builds the IR. The only
  phase that knows the source syntax.
- **Middle-end**: the optimizer. Rewrites the IR to do the same thing with
  less work. It is **active** (it does the optimization work), and it knows
  *neither* the source language *nor* the hardware.
- **Backend**: maps the IR onto a specific target: x86 CPU, ARM CPU, NVIDIA
  GPU (PTX), etc.

## Why have an IR at all?

The IR is the **contract between the phases**. Frontends only need to
produce it; backends only need to consume it.

With N source languages and M hardware targets:
- without a shared IR you need **N x M** compilers,
- with a shared IR you need **N frontends + M backends**.

Optimizations like "delete code whose result is never used" are written once
on the IR and then benefit every language and every target. This is the
**LLVM** idea. **MLIR** (what toy-mlir is about) generalizes it: instead of
one IR it lets you define *several* IRs at different levels and convert
between them step by step. See [06-mlir-concepts.md](06-mlir-concepts.md).

A caveat: optimizations that need hardware knowledge (tile sizes, vector
width, shared memory) happen near or inside the backend, not in the
hardware-independent middle-end.

## Compiled vs. interpreted, AOT vs. JIT

- **Compiler**: translates the whole program before it runs.
- **Interpreter**: executes the source (or a simple IR) directly, step by
  step. Slower, but no translation step.
- **AOT (ahead-of-time)**: compile first, producing a binary you run later.
- **JIT (just-in-time)**: compile in memory right when the program starts (or
  while it runs) and execute immediately. The Toy tutorial's `-emit=jit` does
  this.

## How the data changes shape through the pipeline

Early stages work on a **tree**, later stages on **graphs** (a graph is a set
of nodes connected by edges):

```
source text      ->  tokens  ->  AST (tree)  ->  IR (graphs)  ->  machine code
characters           words       sentence         what really       what the CPU
                                 structure        gets computed     runs
```

- **Tree (AST)** mirrors the *structure of the text*.
- **Graphs (IR)** mirror the *structure of the computation*: which values
  feed which operations, and which blocks of code can run after which. See
  [03-ir-and-ssa.md](03-ir-and-ssa.md).

## Where to go next

Continue to [02-frontend.md](02-frontend.md), or go back to the
[README](README.md) for the reading order.
