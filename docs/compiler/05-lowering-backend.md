# 5. Lowering and the backend

## Lowering

**Lowering** means translating from a higher-level IR to a **lower-level**
one: closer to the hardware, further from the source language.

- **High-level IR** (`toy.transpose`): says *what* to compute. Abstract; keeps
  the programmer's intent.
- **Low-level IR** (loops, loads, stores): says *how* to compute it. Memory
  and control flow are explicit.

Lowering replaces each high-level op with ops at the lower level that do the
same thing:

```
toy.transpose(%a)          ->     affine.for %i ... affine.for %j ...
                                    load a[j][i]; store t[i][j]
```

The reverse is **raising**, which is hard because lowering discards the
original intent (recognizing a matmul from three nested loops is much harder
than lowering a matmul to loops).

Not every pipeline step is a lowering:
- **Lowering**: changes the level of abstraction.
- **Optimization**: rewrites within the same level (inlining, CSE, DCE). The
  IR stays at the same level.
- **Frontend steps**: text -> structure. Usually called parsing/generation,
  not lowering.

### The Toy pipeline

```
Toy language
  v  (parse)
AST
  v  (IR generation)
Toy dialect              high-level: matrix transpose, matmul, tensors
  v  (inline, shape inference, canonicalize)
Toy dialect              specialized
  v  (lower to affine)
Affine + Arith + MemRef  loops over memory, explicit
  v  (lower to LLVM)
LLVM dialect
  v  (translate)
LLVM IR  ->  machine code (JIT or object file)
```

### The dialects you meet while lowering

Each level in the diagram above is a **dialect** (a named set of ops, see
[06](06-mlir-concepts.md)). In order from high to low:

| Dialect | What it holds | Level |
|---|---|---|
| `toy` (or `linalg`, `tosa`) | domain ops: transpose, matmul, tensors | high |
| `tensor` | tensors as immutable **values** (no memory address) | high |
| `memref` | **buffers** in memory: `alloc`, `load`, `store`, shape + strides | mid |
| `arith` | scalar math: `addi`, `mulf`, `constant`, `cmpi` | mid |
| `affine` | loops and accesses with *analyzable* index math (below) | mid |
| `scf` | structured control flow: plain `for`, `while`, `if` with arbitrary index math | mid |
| `cf` | unstructured control flow: basic blocks, `br`, `cond_br` | low |
| `llvm` | MLIR mirror of LLVM IR: pointers, `getelementptr`, `phi`-like block args | lowest |

**Affine, explained.** "Affine" means *linear in the loop variables plus a
constant*. Loop bounds and array indices built only from that are affine:

```
a[i]            affine
a[2*i + j + 3]  affine       (linear in i and j)
a[i * j]        NOT affine   (product of two variables)
a[b[i]]         NOT affine   (index loaded from memory)
```

```mlir
affine.for %i = 0 to 3 {
  affine.for %j = 0 to 2 {
    %v = affine.load %a[%j, %i] : memref<2x3xf64>   // indices are plain i, j
    affine.store %v, %t[%i, %j] : memref<3x2xf64>
  }
}
```

Why it matters: when every index is affine, the compiler can **prove** facts
with math: two accesses never touch the same element, swapping two loops is
legal, iteration *k* doesn't depend on iteration *k-1* so the loop can be
tiled, fused or vectorized. With plain `scf.for` and arbitrary indexing
those proofs are generally impossible, so the compiler must stay
conservative. So affine is where the **loop optimizations** (fusion, tiling,
interchange, unrolling) are done safely; the code is then lowered to `scf`
(loops without the guarantees), then `cf` (blocks and branches), then `llvm`.

**Other terms in the table:**
- **`memref`**: a *reference to memory*: a pointer plus shape and strides.
  `memref<3x2xf64>` is a 3x2 buffer of doubles. Unlike a `tensor`, loads and
  stores on it have side effects, so optimizations must be more careful.
- **`arith`**: scalar arithmetic on single numbers. The "inside" of loop
  bodies.
- **`scf`** ("structured control flow"): loops and ifs that still look like
  loops and ifs (one entry, one exit). Easier to reason about than raw
  branches.
- **`cf`**: control flow as basic blocks and jumps, the CFG of
  [03-ir-and-ssa.md](03-ir-and-ssa.md). Loop structure is no longer explicit.
- **`llvm`**: the LLVM IR instruction set expressed as an MLIR dialect, so
  the last step to real LLVM IR is a mechanical translation.

### Why multiple levels instead of one jump?

Each level is the **right place** to do certain optimizations.

- Fusing two matmuls is easy on `toy.matmul`, but hard after they've become
  three nested loops each.
- Loop tiling is easy on loops, but hard on LLVM IR.

So the compiler lowers gradually, optimizing at each level.

### Legalization / conversion

- Define which ops are **legal** at the target level.
- Convert every illegal op into legal ones.
- Fail if an illegal op remains (full conversion), or allow some to remain
  (partial conversion).

**Partial lowering** is common: Toy lowers `transpose` and `matmul` to loops
but leaves `toy.print` for later, so the IR temporarily contains a mix of
dialects.

### Tensors to buffers (bufferization)

High-level IR uses **tensors**: immutable values with no memory address.
Real code needs **buffers** in memory. Converting is **bufferization**:
allocate memory (`memref.alloc`) for each tensor and turn ops into loops that
read and write it.

## The backend

The backend turns lowest-level IR into machine code for one target.

1. **Instruction selection**: map IR ops to machine instructions.
2. **Register allocation**: map the unlimited SSA values onto the finite set
   of CPU registers. Values whose lifetimes don't overlap share a register;
   if there aren't enough, the extras are **spilled** to the stack. This is
   also where phi / block arguments are turned into `mov`s (**SSA
   destruction**), as described in [03-ir-and-ssa.md](03-ir-and-ssa.md).
3. **Instruction scheduling**: reorder instructions to hide latency (e.g.,
   start a slow load early).
4. **Emission**: write out object code and link into an executable.

You rarely write this yourself: Toy stops at LLVM IR and lets LLVM do the
backend work.

### AOT vs. JIT

- **AOT** (ahead-of-time): produce a binary file; run it later.
- **JIT** (just-in-time): compile in memory and run immediately. Toy does
  this with MLIR's `ExecutionEngine` (`-emit=jit`).

### What is shared between compilers, and what differs

Compilers differ most at the **top** and share most at the **bottom**:

| Part | Shared or specific? |
|---|---|
| Source language, parser, AST | specific to each language |
| High-level IR (Rust MIR, Swift SIL, `toy`, `linalg`, Triton IR) | usually specific: it encodes that language's or domain's meaning |
| Mid-level (loops, buffers, CFG) | partly shared: ideas and passes are common (`affine`, `scf`, LLVM's loop passes), but each compiler picks which ones and in what order |
| LLVM IR and its optimizer | shared: Clang, Rust, Swift, Julia and Triton all emit LLVM IR |
| Machine-code backend (instruction selection, register allocation) | shared per **target** (x86, ARM, NVPTX, AMDGPU), not per compiler |

There are two different axes, and the answer differs for each:

- **Across compilers** (Clang vs Rust vs Triton): the backend is **shared**;
  they all hand LLVM IR to the same x86 or NVPTX backend.
- **Across hardware** (x86 vs ARM vs NVIDIA vs AMD): the backend is
  **different**. Each target has its own instruction set, registers,
  scheduling rules and calling conventions.

The overall shape is an **hourglass**: languages vary at the top, hardware
varies at the bottom, and LLVM IR is the narrow waist in the middle. That
reuse is the reason new languages can be built by writing only a frontend
and a high-level IR that lowers into LLVM or MLIR. The real differences
between competing compilers (and for ML compilers, between TVM, XLA, IREE
and Triton) are in the **high- and mid-level**: which abstractions they use
and which optimizations (fusion, tiling, layout) they apply.

**Hardware differences don't stay at the bottom.** For GPUs, tile sizes,
shared-memory use, tensor-core shapes, layouts and async-copy pipelining all
depend on the specific chip (an A100 and an H100 want different tilings). So
mid-level optimizations are hardware-aware too, which is why hardware-specific
GPU codegen is a large specialization of its own.

### Relevance to GPU / LLM kernels (this repo)

For GPUs the backend target is e.g. PTX, SPIR-V or AMDGPU. The key lowering
steps become:
- mapping loops to the thread / block / warp grid,
- staging data into fast shared memory,
- using tensor cores.

The same pipeline shape applies: high-level tensor ops -> optimize -> lower
step by step -> loops/kernels -> machine code.

## Key takeaways

- **Lowering** = high level -> lower level, step by step. Optimizations at
  each level; don't jump straight to the bottom.
- **Legalization** = convert every op not allowed at the target level.
- The **backend** does instruction selection, register allocation (SSA ->
  registers), scheduling, emission.
- **AOT** compiles ahead; **JIT** compiles on the fly.
