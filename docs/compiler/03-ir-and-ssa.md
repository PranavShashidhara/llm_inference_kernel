# 3. Intermediate representations, SSA and types

This is the most important chapter. Take it slowly; the order of sections is
chosen so each term is explained before it's used.

An AST mirrors the *syntax* of the source. An **IR** mirrors the
*computation*, which is much easier to optimize and to lower toward the
machine.

Sections:
1. Three-address code
2. How to read IR code (notation)
3. Basic blocks and the CFG
4. SSA (the key idea), phi nodes and block arguments
5. The two graphs inside an IR
6. SSA vs. hardware registers and memory
7. SSA: advantages and disadvantages (and why not just use trees)
8. Structured vs. unstructured control flow
9. Types and values

---

## 1. Three-address code

Each instruction does **one** operation and names at most two inputs and one
output: three "addresses". Complex expressions are broken into steps, with
temporaries holding the in-between results.

```
a + b * c      becomes      t1 = b * c
                            t2 = a + t1
```

Why: every instruction is simple, so it's easy to analyze, rewrite, and later
map to a machine instruction. (Three-address code describes the *shape* of
instructions. SSA, below, is a separate rule about *naming*. Real IRs like
LLVM and MLIR have both.)

## 2. How to read IR code

You'll see this notation throughout these docs and in toy-mlir:

```mlir
%2 = toy.mul %0, %1 : tensor<2x3xf64>
```

| Piece | Meaning |
|---|---|
| `%2` | the **result**: a name for the value this instruction computes |
| `%0`, `%1` | **operands**: values computed by earlier instructions |
| `toy.mul` | the **operation**: `mul` from the `toy` dialect (a dialect is a namespace of ops) |
| `: tensor<2x3xf64>` | the **type** of the value |
| `^bb1:` or `^then:` | the name of a **basic block** (next section) |
| `// text` | a comment |

A name like `%2` is not a memory location. It's just a *name for a computed
result*.

## 3. Basic blocks and the CFG

### Basic block

A **basic block** is a straight-line run of instructions with
- **one way in**: execution only enters at the top (nobody jumps into the
  middle), and
- **one way out**: execution only leaves at the bottom through the last
  instruction, the **terminator** (a branch, conditional branch, or return).

Once a block starts, every instruction in it runs, in order, with no jumps in
between. That lets the compiler reason about the whole block as one unit.

**A block is a container of instructions**, not an instruction itself.

Example. This code:

```
x = a + b
if (x > 0)  y = 1
else        y = 2
z = y * 2
```

splits into four blocks, because every jump target starts a new block and
every jump ends one:

```
^entry:                      // block 1
  %x = add %a, %b
  %c = cmp gt %x, 0
  cond_br %c, ^then, ^else   // terminator: jump to then or else

^then:                       // block 2
  br ^after(1)               // terminator: jump to after, carrying y=1

^else:                       // block 3
  br ^after(2)               // terminator: jump to after, carrying y=2

^after(%y):                  // block 4. %y is a block argument (explained below)
  %z = mul %y, 2
  return %z
```

How to find blocks: start a new one at the function entry, at every jump
target, and right after every jump.

### CFG (Control Flow Graph)

The **CFG** is a map of the paths the program can take.
- **Nodes** = basic blocks
- **Edges** = possible jumps between them

```
   entry
   /   \
 then  else
   \   /
   after
```

A loop is a CFG with a **cycle** (an edge pointing back to an earlier
block):

```
[entry] -> [loop body] -> [exit]
              ^   |
              +---+
```

### Dominance

Block A **dominates** block B if *every* path from the entry to B passes
through A.

In the diagram above `entry` dominates every block. But `then` does **not**
dominate `after`, because you can also reach `after` via `else`.

Why it matters: a value defined in `then` can't be used in `after`, since on
the `else` path it was never defined. A value may only be used where its
definition **dominates** the use. This is why `%y` above is passed as a block
argument instead of being defined inside `then`.

## 4. SSA - Static Single Assignment

### The rule

Every value is assigned **exactly once**. If the source reassigns a
variable, the compiler gives each assignment a **new name**:

```
x = 1                 x1 = 1
x = x + 2      ==>    x2 = x1 + 2
y = x * 3             y1 = x2 * 3
```

Nothing is overwritten: `x1` still holds `1` after `x2` is computed. The
compiler generates SSA for you; nobody writes it by hand.

"**Static**" means once in the *code as written*, not once per execution. A
value defined inside a loop body gets a new runtime value on every
iteration, but there is only one *statement* that defines it.

### Terms you'll see from now on

- **Def (definition)**: the one place a value is created
  (`%1 = add %a, %b`).
- **Use**: any instruction that reads the value as an operand
  (`%2 = mul %1, 2` is a use of `%1`). Most instructions are both a def (of
  their result) and a use (of their operands).
- **Use-def link**: from a use, the pointer back to its def. "Where did this
  value come from?"
- **Def-use list**: from a def, the list of all instructions that use it.
  "Who reads this value?"

```
%1 = add %a, %b      <- def of %1
%2 = mul %1, 2       <- use of %1 (use-def: points back to the add)
%3 = sub %1, %2      <- another use of %1
toy.print %1         <- another use of %1

def-use list of %1 = { mul, sub, print }
def-use list of %3 = { }                  <- empty
```

- **Side effect**: any observable action other than producing a result:
  writing memory, printing, possibly crashing.
- **Pure**: no side effects *and* the result depends only on the operands.
  Pure ops can be deleted if unused, merged if duplicated, and moved freely.
- **Dead code**: a pure op whose result has no uses. **DCE** deletes it.
  (Details in [04-optimizations.md](04-optimizations.md).)
- **CSE**: if two ops compute the same thing from the same inputs, keep one.
  (Also in [04](04-optimizations.md).)

### Why SSA helps: "use-def is trivial"

Every value has exactly one def, so a use-def link is **a plain pointer**:
no analysis needed to answer "where did this come from?".

Without SSA:

```
x = 1
if (c) x = 2
y = x + 5      // which x? 1 or 2? depends on the path taken
```

The compiler must run a separate **reaching-definitions analysis** to find
which assignments can reach that use. With SSA the question disappears,
because each name has exactly one definition.

### The merge problem: phi nodes

SSA has one difficulty: when control flow **merges**, which version of the
variable applies?

```
if (c) x1 = 1
else   x2 = 2
use(x?)           // x1 or x2?
```

The answer is a **phi node**: a special instruction at the top of the merge
block that picks the value according to which path was taken.

```
        entry
        /   \
     then   else
   x1 = 1   x2 = 2
        \   /
   after: x3 = phi(x1 from then, x2 from else)
          use(x3)
```

### MLIR's version: block arguments

MLIR has no phi instruction. Instead a block declares **parameters** and each
branch passes values to them, like a function call:

```
^then:  br ^after(%x1)          // passes x1
^else:  br ^after(%x2)          // passes x2
^after(%x3):                    // %x3 is a block argument
  use(%x3)
```

Same power as a phi, cleaner to manipulate.

### Loops are not overwriting

A loop counter looks like overwriting but isn't:

```
^loop(%i: i64):            // %i is defined once, here, as a block argument
  %next = add %i, 1        // a new name, not an overwrite
  br ^loop(%next)          // passes %next in as %i of the next iteration
```

`%i` holds different values on different iterations, but no statement ever
*writes* to `%i`. It's rebound by the block argument each time the block is
entered.

## 5. The two graphs inside an IR

An SSA IR is really **two graphs** layered together. They have different
kinds of nodes, and mixing them up is a common source of confusion.

| | **CFG** (control-flow graph) | **Data-flow graph** (use-def graph) |
|---|---|---|
| Nodes | **basic blocks** (containers of instructions) | **instructions / values** |
| Edges | jumps: "this block can run after that block" | operands: "this value feeds that instruction" |
| Can have cycles? | yes (loops) | within straight-line code, no (it's a DAG) |
| Answers | which code can run after which | where each value comes from |

```
CFG (nodes = blocks)               Data-flow graph (nodes = instructions)

   entry                           x1 = 1      x2 = 2
   /   \                               \       /
 then  else                           x3 = phi(x1, x2)
   \   /                                   |
   after                                y = x3 * 2
```

- A **normal instruction** (like `add`) is a node with a fixed set of input
  edges.
- A **phi** (or block argument) is a node in the data-flow graph with
  **multiple possible incoming edges**: one per path that can reach the
  block. It's the *merging* node.
- A **block** is not an instruction; it's a node in the *other* graph (the
  CFG). The phi sits at the top of the block, and the phi's incoming entries
  match the block's predecessors in the CFG. That's how the two graphs link.

The use-def links *are* the data-flow graph's edges. You don't build a
separate structure: each operand is a pointer to the defining instruction, so
the IR already is the graph.

Rough progression of structures through the compiler: **tree** (AST) ->
**DAG** (data-flow within a block: a value can have several users) ->
**general graph** (CFG, with loops).

## 6. SSA vs. hardware registers and memory

### SSA values vs. registers

SSA values behave like **virtual registers**:
- unlimited in number (every new result gets a new name),
- written once, then only read,
- not tied to any hardware.

Real CPU registers are the opposite: a small fixed number (16 general-purpose
on x86-64) and **mutable** (`rax` is overwritten constantly).

The backend bridges the gap with **register allocation**: it maps the
unlimited SSA values onto the few physical registers. Two values whose
lifetimes don't overlap can share one register. If more values are alive at
once than there are registers, some are **spilled** to the stack. Phi nodes
and block arguments are removed here (**SSA destruction**), becoming plain
`mov`s:

```
SSA IR                      After register allocation
%a = load ...               mov rax, [..]
%b = add %a, 1              add rax, 1      // %a is dead, so rax is reused for %b
%c = mul %b, 2              imul rax, 2     // reused again for %c
```

SSA is a property of the **IR** that makes analysis and optimization easy.
The hardware doesn't care about it. The backend removes it at the very end.

### Memory is not SSA

SSA applies to **values** (`%0`, `%1`, ...). **Memory** can be overwritten
freely:

```mlir
affine.store %a, %buf[0]
affine.store %b, %buf[0]    // overwrites the first store
```

`%buf` is a single SSA value (a pointer). The *contents* behind it are
mutable. This is why **tensors** (immutable values, SSA-friendly) are easier
to optimize than **memrefs** (mutable buffers), and why the conversion between
them (**bufferization**) happens late.

## 7. SSA: advantages and disadvantages

### Is SSA required? What about just using trees?

SSA isn't strictly required; many compilers work without it. But trees break
down in three places:

1. **Shared values.** If `t = a * b` is used twice, a tree must duplicate
   the subtree. Once a node has two parents it's a **DAG**, not a tree. SSA
   is that DAG written as a list of instructions.
2. **Control flow.** A tree has no cycles, but a loop is a cycle. You need a
   CFG, and then values flow across blocks, which brings back the "which
   assignment reaches this use?" problem. Phi / block arguments solve it.
3. **Mutation.** With repeated `x = x + 1`, a tree can't say which `x` each
   node refers to without extra analysis.

### Doing SSA early doesn't make later passes harder

SSA is built **once**, early (by the frontend, or by LLVM's `mem2reg` pass
that promotes stack slots to SSA values). After that every pass **maintains**
SSA as it rewrites. In MLIR, `replaceAllUsesWith`, the verifier and the
pattern driver enforce this. Only the very end (register allocation) leaves
SSA.

How a frontend creates SSA:
- **Direct construction**: keep a map "source variable -> current SSA value".
  `x = x + 1` creates a new value and updates the map. At merges, insert a
  phi / block argument.
- **Memory first, then promote** (LLVM): the frontend emits plain stack
  slots (`alloca`/`load`/`store`), which are easy to generate, then `mem2reg`
  converts them to SSA values and inserts the phis.

### Advantages
- **Use-def is trivial**: one pointer hop, no reaching-definitions analysis.
- **Def-use lists** make "replace all uses" and "is this dead?" cheap, which
  is what CSE, DCE and constant propagation need.
- **Sparse analyses**: facts attach to values, not to every program point, so
  analyses run faster.
- **Fewer bugs**: a value never changes, so there's no "was it modified in
  between?".
- **Linear and uniform**: passes just iterate over operations.

### Disadvantages
- **Merges need phi / block arguments**, which complicate building and
  rewriting control flow (loops especially).
- **Only covers values, not memory**: arrays, pointers and globals still use
  load/store and need **alias analysis** (figuring out whether two pointers
  can refer to the same memory).
- **Bookkeeping cost**: every rewrite must keep def-use lists correct and
  keep every def dominating its uses.
- **Must be undone in the backend**: phis become `mov`s. Done badly, this adds
  extra copies.
- **Awkward for humans to write**: you don't; the compiler generates it.

## 8. Structured vs. unstructured control flow

- **Unstructured** (LLVM): a CFG of blocks connected by branches. Very
  general, but the shape of the original loop is lost.
- **Structured** (higher-level IRs): loops and ifs stay as constructs with
  nested bodies (`for`, `if`).

```mlir
affine.for %i = 0 to 10 {        // structured: still clearly "a loop over 0..10"
  ...
}
```

Structured form keeps information that is painful to recover from a CFG
(e.g. "this is a loop over i in [0, N)"), which is precisely what enables loop
tiling, fusion and vectorization. MLIR supports both, via **regions**
(see [06-mlir-concepts.md](06-mlir-concepts.md)).

## 9. Types and values

- **Scalar types**: `i1`, `i32`, `i64` (integers by bit width), `f16`, `f32`,
  `f64` (floats).
- **Aggregate types**: tensors, vectors, structs, pointers/memrefs.
- **Shape**: the dimensions of a tensor, e.g. `2x3`. May be static (`2x3`),
  dynamic (`?x3`, size unknown at compile time) or unranked (`*`, rank
  unknown).
- **Tensor vs. buffer** (important for ML compilers):
  - *tensor*: an immutable **value**. SSA-friendly, has no memory address,
    cannot alias. Great for optimization.
  - *memref / buffer*: a **mutable region of memory**. Needed for real code
    generation. Converting tensors to buffers is called **bufferization**.

## Key takeaways

- A **basic block** = straight-line instructions, one way in, one way out. A
  **CFG** = blocks (nodes) + jumps (edges).
- **SSA** = every value is defined exactly once; reassignment makes a new
  name. Nothing is overwritten.
- **Use-def / def-use** are the pointers between a value's definition and its
  uses. They are the edges of the data-flow graph and make optimization cheap.
- **Phi / block arguments** pick a value at a control-flow merge. They live in
  the data-flow graph; blocks live in the CFG.
- SSA values are like **virtual registers**; the backend maps them to real
  registers. **Memory** is not SSA.
