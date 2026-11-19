# Compiler basics (a primer before reading toy-mlir)

Goal: give you the vocabulary and mental model so that the MLIR Toy tutorial
(Toy language -> Toy dialect -> Affine/Arith/MemRef -> LLVM IR) reads naturally.

## If you are new to compilers

Read in order and don't skip chapter 3: it holds the ideas the rest builds on
(basic blocks, SSA, use-def, phi / block arguments). Each chapter ends with
"Key takeaways". If a word is unfamiliar, look it up in the
[glossary](glossary.md).

One-paragraph version of everything: the **frontend** turns text into an
**IR** (tree -> graphs), the **middle-end** optimizes the IR with small
**passes** (DCE, CSE, folding, inlining), and the **backend** lowers it to
machine code. **SSA** (every value defined once) is what makes the passes
cheap. **MLIR** lets you have many IR levels ("dialects") and lower between
them step by step.

## Reading order

1. [01-overview.md](01-overview.md): what a compiler is, frontend / middle-end / backend
2. [02-frontend.md](02-frontend.md): lexing, parsing, parse tree vs. AST, semantic analysis
3. [03-ir-and-ssa.md](03-ir-and-ssa.md): IR, SSA, use-def, phi / block arguments, CFG, types
4. [04-optimizations.md](04-optimizations.md): DCE, constant folding, CSE, inlining, DSE, pattern rewriting
5. [05-lowering-backend.md](05-lowering-backend.md): lowering, instruction selection, register allocation
6. [06-mlir-concepts.md](06-mlir-concepts.md): ops, regions, dialects, ODS, interfaces, dialect conversion
7. [07-worked-example.md](07-worked-example.md): one program followed through the entire pipeline

Reference: [glossary.md](glossary.md)

## Reading roadmap for toy-mlir


| Chapter | What it adds | Concepts used from these notes |
|---|---|---|
| 1. Toy language & AST | Lexer, recursive-descent parser, AST | [Frontend](02-frontend.md) |
| 2. Emitting basic MLIR | Toy dialect, ops, `MLIRGen` (AST -> IR) | Op, Value, Type, Attribute, Region, Location, ODS |
| 3. High-level analysis & transformation | Pattern rewriting, `canonicalize` | [Pattern rewriting](04-optimizations.md), DRR |
| 4. Generic transformations with interfaces | Inliner, shape inference | Interfaces, passes, specialization |
| 5. Partial lowering to lower-level dialects | Toy -> Affine/Arith/MemRef | Dialect conversion, bufferization, loops |
| 6. Lowering to LLVM and code generation | Affine -> LLVM dialect -> LLVM IR, JIT | [Backend](05-lowering-backend.md), ConversionTarget, TypeConverter |
| 7. Adding a composite type | Struct type | Custom types, parsing/printing |

A good reading technique for each chapter:
1. Read the `.toy` input program.
2. Read the dumped IR (`-emit=mlir`) after each stage.
3. Only then read the C++ that produced that change.

Useful flags in the tutorial binary: `-emit=ast`, `-emit=mlir`,
`-emit=mlir-affine`, `-emit=mlir-llvm`, `-emit=llvm`, `-emit=jit`,
`-opt` (enable optimizations).

