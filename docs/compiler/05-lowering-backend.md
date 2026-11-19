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
