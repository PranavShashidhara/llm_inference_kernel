# 6. From LLVM to MLIR: concepts

Prerequisites: [03-ir-and-ssa.md](03-ir-and-ssa.md) (SSA, blocks) and
[05-lowering-backend.md](05-lowering-backend.md) (lowering).

## The problem MLIR solves

LLVM has **one** fixed IR with a fixed, low-level set of instructions. That's
too low-level for machine learning: by the time LLVM sees a matrix multiply,
it has already become loops and the "matmul" intent is gone.

**MLIR is a framework for defining many IRs and mixing them**, one per level
of abstraction. You write your own high-level ops (`toy.transpose`), and MLIR
gives you the infrastructure (SSA, passes, pattern rewriting, lowering) for
free.

## Core concepts

| Concept | Meaning |
|---|---|
| **Operation (Op)** | The universal unit. *Everything* is an op: `toy.transpose`, `arith.addf`, `func.func`, even a module. |
| **Value** | An SSA value (`%0`). Produced as an op's result or a block argument. |
| **Type** | Every value has one: `tensor<2x3xf64>`, `i32`, `memref<2x3xf64>`. |
| **Attribute** | Compile-time constant data attached to an op (`value = dense<[1.0, 2.0]>`, `sym_name = "main"`). Not an SSA value. |
| **Operands / Results** | Inputs and outputs of an op. |
| **Region** | A list of blocks owned by an op. Gives nesting: a `func` op contains a region, which holds blocks, which hold ops, which can hold regions... |
| **Block** | List of ops ending in a terminator; has block arguments (the phi replacement). |
| **Location** | Source file/line/column attached to every op, for error messages. |
| **Dialect** | A namespaced collection of ops, types and attributes (`toy.`, `arith.`, `affine.`, `memref.`, `llvm.`). A *dialect* = a *level of abstraction*. |
| **Symbol / SymbolTable** | Named things (functions, globals) referenced by name instead of by SSA value. |
| **Verifier** | Each op/dialect defines rules that are checked on the IR (e.g. "operand shapes must match"). |

### Operand vs. attribute

- **Operand**: a *runtime* value computed by another op (`%0`).
- **Attribute**: a *compile-time constant* written directly on the op, such
  as the data of a constant, a function name, or a loop bound.

## Reading an op

Generic textual form:

```mlir
%result = "dialect.opname"(%operand0, %operand1) {attr = 42 : i32}
          : (tensor<2x3xf64>, tensor<2x3xf64>) -> tensor<2x3xf64>   loc("file.toy":3:10)
```

| Piece | Meaning |
|---|---|
| `%result` | result value |
| `"dialect.opname"` | which op |
| `(%operand0, %operand1)` | operands |
| `{attr = 42 : i32}` | attributes |
| `: (...) -> ...` | operand types -> result types |
| `loc(...)` | source location |

Pretty (custom assembly) form, what you'll usually see:

```mlir
%2 = toy.add %0, %1 : tensor<2x3xf64>
```

## Nesting: module, region, block, op

```mlir
module {
  toy.func @main() {
    %0 = toy.constant dense<[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]> : tensor<2x3xf64>
    %1 = toy.transpose(%0 : tensor<2x3xf64>) to tensor<3x2xf64>
    toy.print %1 : tensor<3x2xf64>
    toy.return
  }
}
```

Read as: `module` (op) -> region -> block -> `toy.func` (op) -> region ->
block -> ops. Because ops own regions, you can nest a whole loop body or
function body inside a single op. This is how MLIR represents **structured**
control flow (see [03](03-ir-and-ssa.md), "Structured vs. unstructured").

## Defining ops: ODS and TableGen

Instead of hand-writing C++ for every op, MLIR uses **ODS** (Operation
Definition Specification) in `.td` files. **TableGen** (`mlir-tblgen`) reads
them and generates the C++ classes (builders, accessors, verifier hooks,
parsers/printers).

```tablegen
def TransposeOp : Toy_Op<"transpose", [Pure]> {
  let arguments = (ins F64Tensor:$input);
  let results   = (outs F64Tensor);
  let hasVerifier = 1;
}
```

- `Toy_Op<"transpose", ...>`: an op named `toy.transpose`.
- `[Pure]`: a **trait**; no side effects, so DCE and CSE may handle it freely.
- `ins` / `outs`: operands / results.
- Other traits: `Terminator`, `SameOperandsAndResultType`, ...
- `hasVerifier`: "I'll supply extra checks."

## Interfaces

An **interface** lets a pass work on ops **generically**, without knowing
every dialect. A pass asks "does this op implement interface X?" instead of
switching on op names.

Examples:
- The **inliner** only needs call ops to implement
  `CallOpInterface` / `CallableOpInterface`.
- **Shape inference** in Toy is a custom `ShapeInferenceOpInterface`: each op
  says how to compute its result shape; one pass handles all ops.

## Passes

- Run on a given op type (`OperationPass<toy::FuncOp>`) or on the whole
  module.
- Scheduled with a `PassManager`; nested pipelines run per function.
- Built-ins you'll see: `canonicalize`, `cse`, `inline`, `symbol-dce`, loop
  optimizations.

## Canonicalization and folding

- `fold()` hook: a simple local simplification of one op (e.g. constant
  folding).
- `getCanonicalizationPatterns()`: registers rewrite patterns for the op.
- The `canonicalize` pass applies all of them (plus trivial DCE) to a fixed
  point. See [04-optimizations.md](04-optimizations.md).

## Dialect conversion framework

The infrastructure for lowering ([05](05-lowering-backend.md)):

1. **ConversionTarget**: which ops/dialects are legal after conversion.
2. **RewritePatterns / ConversionPatterns**: how to turn each illegal op into
   legal ones.
3. **TypeConverter**: how types change (`tensor` -> `memref`).
4. `applyPartialConversion` (some illegal ops may remain) or
   `applyFullConversion` (all must be converted, else fail).

Partial lowering is a major MLIR strategy: Toy lowers `transpose`, `matmul`,
etc. to Affine loops but leaves `toy.print` for a later stage; the IR then
legally contains a mix of dialects.

## Key dialects Toy touches

| Dialect | What it holds |
|---|---|
| `func` | functions and calls |
| `arith` | scalar arithmetic (`arith.addf`, `arith.constant`) |
| `affine` | loops (`affine.for`) and memory access with affine index expressions (simple linear formulas of loop variables), which are amenable to polyhedral-style analysis |
| `memref` | buffers (`memref.alloc`, `memref.load/store`) |
| `scf` | structured control flow (`scf.for`, `scf.if`) |
| `cf` | unstructured branches (`cf.br`, `cf.cond_br`) |
| `llvm` | a 1:1 mirror of LLVM IR inside MLIR |

## Key takeaways

- Everything in MLIR is an **op**; ops live in **blocks**, blocks in
  **regions**, regions inside ops.
- A **dialect** is a level of abstraction; compiling = lowering between
  dialects.
- **ODS/TableGen** generate op boilerplate; **traits** (like `Pure`) and
  **interfaces** let generic passes work on any dialect.
- **Conversion** = declare what's legal, supply patterns, apply.
