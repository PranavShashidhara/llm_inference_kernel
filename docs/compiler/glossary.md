# Glossary

Alphabetical. Where a longer explanation exists, the file is given.

- **Alias analysis**: working out whether two pointers/buffers can refer to the
  same memory. Needed for memory optimizations like DSE. ([04](04-optimizations.md))
- **Aliasing**: two names referring to the same memory. Tensors avoid it;
  buffers don't.
- **AOT (ahead-of-time)**: compile first, run the binary later. ([05](05-lowering-backend.md))
- **AST (abstract syntax tree)**: the tree of the program's structure with
  punctuation removed. ([02](02-frontend.md))
- **Attribute**: compile-time constant data attached to an MLIR op. ([06](06-mlir-concepts.md))
- **Backend**: the phase that turns IR into machine code for one target. ([01](01-overview.md))
- **Basic block**: straight-line instructions, one way in, one way out (ending
  in a terminator). ([03](03-ir-and-ssa.md))
- **Block argument**: MLIR's replacement for a phi node: a block parameter that
  branches fill in. ([03](03-ir-and-ssa.md))
- **Bufferization**: converting tensors (values) into memrefs (memory). ([05](05-lowering-backend.md))
- **Canonical form**: a normalized shape so later patterns need fewer cases.
  ([04](04-optimizations.md))
- **CFG (control-flow graph)**: nodes = basic blocks, edges = jumps. ([03](03-ir-and-ssa.md))
- **Constant folding**: computing an op at compile time when its inputs are
  constants. ([04](04-optimizations.md))
- **CSE (common subexpression elimination)**: compute identical pure
  expressions once. ([04](04-optimizations.md))
- **Data-flow graph**: the graph of values feeding instructions (the use-def
  links). ([03](03-ir-and-ssa.md))
- **DCE (dead code elimination)**: delete pure ops whose results are unused.
  ([04](04-optimizations.md))
- **Def (definition)**: the one place an SSA value is created. ([03](03-ir-and-ssa.md))
- **Def-use list**: for a def, all instructions that use it. ([03](03-ir-and-ssa.md))
- **Dialect**: a namespace of ops/types/attributes; a level of abstraction.
  ([06](06-mlir-concepts.md))
- **Dominance**: block A dominates B if every path from entry to B goes through
  A. A def must dominate its uses. ([03](03-ir-and-ssa.md))
- **DRR**: declarative rewrite rules in TableGen. ([06](06-mlir-concepts.md))
- **DSE (dead store elimination)**: delete a store overwritten before being
  read. ([04](04-optimizations.md))
- **Fixed point**: the state where applying the transformations changes
  nothing.
- **Frontend**: the phase that turns source text into IR. ([01](01-overview.md), [02](02-frontend.md))
- **Inlining**: replacing a call with the callee's body. ([04](04-optimizations.md))
- **Interface (MLIR)**: lets passes work on ops generically. ([06](06-mlir-concepts.md))
- **IR (intermediate representation)**: the compiler's internal form of the
  program, between source and machine code. ([01](01-overview.md), [03](03-ir-and-ssa.md))
- **JIT (just-in-time)**: compile in memory and run immediately. ([05](05-lowering-backend.md))
- **Lexer / token**: splits text into tokens (the words of the language). ([02](02-frontend.md))
- **Location**: source file/line/column attached to every op.
- **Lowering**: translating a higher-level IR to a lower-level one.
  **Raising** is the reverse (hard). ([05](05-lowering-backend.md))
- **Legalization**: converting ops so only the allowed set remains. ([05](05-lowering-backend.md))
- **LICM (loop-invariant code motion)**: move unchanging computation out of a
  loop. ([04](04-optimizations.md))
- **Memref**: a mutable buffer type in MLIR. ([03](03-ir-and-ssa.md))
- **Middle-end**: the optimizer; works on IR independent of language and
  hardware. ([01](01-overview.md), [04](04-optimizations.md))
- **Monomorphization / specialization**: Toy clones generic functions per
  concrete argument shape so shape inference can work.
- **ODS / TableGen**: declarative definition of ops, with generated C++.
  ([06](06-mlir-concepts.md))
- **Op (operation)**: the universal unit in MLIR. ([06](06-mlir-concepts.md))
- **Operand**: an input value of an op.
- **Parser / parse tree**: builds the tree from tokens; a parse tree keeps
  all tokens, an AST drops the noise. ([02](02-frontend.md))
- **Pass / pass pipeline**: one analysis or transform over the IR; an ordered
  list of them. ([04](04-optimizations.md))
- **Pattern rewriting**: "match this subgraph, replace with that". ([04](04-optimizations.md))
- **Phi node**: at a control-flow merge, picks a value depending on which path
  was taken. ([03](03-ir-and-ssa.md))
- **Pure**: no side effects and the result depends only on the operands.
- **Region**: a list of blocks owned by an op. ([06](06-mlir-concepts.md))
- **Register allocation**: mapping unlimited SSA values to a finite set of CPU
  registers. ([05](05-lowering-backend.md))
- **Shape**: the dimensions of a tensor (`2x3`). **Shape inference**:
  computing unknown shapes.
- **Side effect**: any observable action besides producing a result (memory
  write, printing, crashing).
- **SSA (static single assignment)**: every value is defined exactly once.
  ([03](03-ir-and-ssa.md))
- **Tensor**: an immutable multi-dimensional array value (no memory address).
- **Terminator**: the last instruction of a block (branch, return).
- **Three-address code**: each instruction has one operation, at most two
  inputs and one output. ([03](03-ir-and-ssa.md))
- **Trait (MLIR)**: a property of an op (`Pure`, `Terminator`, ...).
- **Use**: an instruction that reads a value as an operand. **Use-def link**:
  from a use back to its def. ([03](03-ir-and-ssa.md))
- **Verifier**: checks the IR obeys its rules.
