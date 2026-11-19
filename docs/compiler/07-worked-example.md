# 7. Worked example: the entire flow, stage by stage


This is the same program the Toy tutorial uses. Watch which stage is
frontend, which is middle-end, which is backend.

**How to read this chapter**
- Read the stages in order; each one takes the output of the previous.
- Don't worry about every detail of the IR syntax. Notice instead what
  *changes* between stages: the number of ops, the types, the dialect.
- Notation: `%name` = an SSA value, `^name` = a basic block, `// ...` = a
  comment. See "How to read IR code" in [03-ir-and-ssa.md](03-ir-and-ssa.md).
- Terms you may want open in another tab: [glossary](glossary.md),
  [04-optimizations.md](04-optimizations.md) (DCE, CSE, folding, inlining).
- The IR listings are illustrative, written by hand to show the idea. Real
  compiler output differs in small details.

```
FRONTEND   : source -> tokens -> AST -> Toy IR (unoptimized)
MIDDLE-END : Toy IR -> inline -> shape inference -> canonicalize/CSE/DCE -> Toy IR (optimized)
             -> lower to Affine/Arith/MemRef (still middle-end: loops over buffers)
BACKEND    : -> LLVM dialect -> LLVM IR -> machine code -> run
```

### Stage 0: Source (Toy language)

```
def multiply_transpose(a, b) {
  return transpose(a) * transpose(b);
}

def main() {
  var a<2, 3> = [[1, 2, 3], [4, 5, 6]];
  var b<2, 3> = [1, 2, 3, 4, 5, 6];   # 6 numbers, reshaped to 2x3
  var c = multiply_transpose(a, b);   # c is never used
  var d = multiply_transpose(b, a);
  print(d);
}
```

### Stage 1 [Frontend]: Lexer -> tokens

```
DEF IDENT(multiply_transpose) ( IDENT(a) , IDENT(b) ) { RETURN IDENT(transpose) ( IDENT(a) )
* IDENT(transpose) ( IDENT(b) ) ; } DEF IDENT(main) ( ) { VAR IDENT(a) < 2 , 3 > = [ [ 1 , 2 , 3 ] ...
```

### Stage 2 [Frontend]: Parser -> AST

```
Module
├─ Function multiply_transpose(a, b)
│    └─ Return
│         └─ BinOp(*)
│              ├─ Call transpose(Var a)
│              └─ Call transpose(Var b)
└─ Function main()
     ├─ VarDecl a<2,3> = Literal [[1,2,3],[4,5,6]]
     ├─ VarDecl b<2,3> = Literal [1,2,3,4,5,6]
     ├─ VarDecl c = Call multiply_transpose(a, b)
     ├─ VarDecl d = Call multiply_transpose(b, a)
     └─ Print(Var d)
```
(`-emit=ast` in the tutorial binary shows this.) No optimization, no meaning
beyond syntax. Errors like "undeclared variable" are caught here.

### Stage 3 [Frontend]: MLIRGen -> Toy dialect IR (SSA)

Walk the AST and emit one op per node. Types of `a`/`b` inside the generic
function are unknown, written `tensor<*xf64>` (`*` = unranked).

```mlir
toy.func @multiply_transpose(%arg0: tensor<*xf64>, %arg1: tensor<*xf64>) -> tensor<*xf64> {
  %0 = toy.transpose(%arg0 : tensor<*xf64>) to tensor<*xf64>
  %1 = toy.transpose(%arg1 : tensor<*xf64>) to tensor<*xf64>
  %2 = toy.mul %0, %1 : tensor<*xf64>
  toy.return %2 : tensor<*xf64>
}

toy.func @main() {
  %0 = toy.constant dense<[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]> : tensor<2x3xf64>
  %1 = toy.reshape(%0 : tensor<2x3xf64>) to tensor<2x3xf64>          // var a<2,3>
  %2 = toy.constant dense<[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]> : tensor<6xf64>
  %3 = toy.reshape(%2 : tensor<6xf64>) to tensor<2x3xf64>            // var b<2,3>
  %4 = toy.generic_call @multiply_transpose(%1, %3) : (tensor<2x3xf64>, tensor<2x3xf64>) -> tensor<*xf64>  // c
  %5 = toy.generic_call @multiply_transpose(%3, %1) : (tensor<2x3xf64>, tensor<2x3xf64>) -> tensor<*xf64>  // d
  toy.print %5 : tensor<*xf64>
  toy.return
}
```
This is the **handoff point**: from here the compiler no longer cares about
Toy *syntax*, only this IR. Wasteful but correct.

### Stage 4 [Middle-end]: Inlining

`toy.generic_call` is replaced by the callee's body (needs the inliner
interface). Now `main` has no calls and the shapes of the arguments are
visible right next to the ops that use them.

```mlir
toy.func @main() {
  %0 = toy.constant dense<[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]> : tensor<2x3xf64>
  %1 = toy.reshape(%0 : tensor<2x3xf64>) to tensor<2x3xf64>
  %2 = toy.constant dense<[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]> : tensor<6xf64>
  %3 = toy.reshape(%2 : tensor<6xf64>) to tensor<2x3xf64>
  // inlined call for c
  %4 = toy.transpose(%1 : tensor<2x3xf64>) to tensor<*xf64>
  %5 = toy.transpose(%3 : tensor<2x3xf64>) to tensor<*xf64>
  %6 = toy.mul %4, %5 : tensor<*xf64>
  // inlined call for d
  %7 = toy.transpose(%3 : tensor<2x3xf64>) to tensor<*xf64>
  %8 = toy.transpose(%1 : tensor<2x3xf64>) to tensor<*xf64>
  %9 = toy.mul %7, %8 : tensor<*xf64>
  toy.print %9 : tensor<*xf64>
  toy.return
}
```

### Stage 5 [Middle-end]: Shape inference

Propagate known shapes forward: `transpose` of `2x3` gives `3x2`; `mul` of
`3x2` and `3x2` gives `3x2`. Every `tensor<*xf64>` becomes a ranked type.

```mlir
  %4 = toy.transpose(%1 : tensor<2x3xf64>) to tensor<3x2xf64>
  %5 = toy.transpose(%3 : tensor<2x3xf64>) to tensor<3x2xf64>
  %6 = toy.mul %4, %5 : tensor<3x2xf64>
  ...
  toy.print %9 : tensor<3x2xf64>
```
(Static shapes are what make the later loop bounds known at compile time.)

### Stage 6 [Middle-end]: Canonicalize + CSE + DCE

Several small rewrites, run until nothing changes (fixed point). A real
driver interleaves them, but it is easier to follow one at a time. Starting
point (the IR after shape inference, 12 ops):

```mlir
toy.func @main() {
  %0 = toy.constant dense<[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]> : tensor<2x3xf64>
  %1 = toy.reshape(%0 : tensor<2x3xf64>) to tensor<2x3xf64>
  %2 = toy.constant dense<[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]> : tensor<6xf64>
  %3 = toy.reshape(%2 : tensor<6xf64>) to tensor<2x3xf64>
  %4 = toy.transpose(%1 : tensor<2x3xf64>) to tensor<3x2xf64>   // c
  %5 = toy.transpose(%3 : tensor<2x3xf64>) to tensor<3x2xf64>
  %6 = toy.mul %4, %5 : tensor<3x2xf64>
  %7 = toy.transpose(%3 : tensor<2x3xf64>) to tensor<3x2xf64>   // d
  %8 = toy.transpose(%1 : tensor<2x3xf64>) to tensor<3x2xf64>
  %9 = toy.mul %7, %8 : tensor<3x2xf64>
  toy.print %9 : tensor<3x2xf64>
  toy.return
}
```

**6a. Reshape folding (canonicalization).** Two patterns fire:
- `reshape` to the *same* type is a no-op, so `%1` is replaced by `%0`.
- `reshape` of a constant becomes a constant of the new shape, so `%3`
  becomes `dense<[[1,2,3],[4,5,6]]> : tensor<2x3xf64>`.

The old 6-element constant `%2` is now unused (and pure), so it is deleted.
10 ops:

```mlir
toy.func @main() {
  %0 = toy.constant dense<[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]> : tensor<2x3xf64>   // a
  %1 = toy.constant dense<[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]> : tensor<2x3xf64>   // b (same value!)
  %2 = toy.transpose(%0 : tensor<2x3xf64>) to tensor<3x2xf64>
  %3 = toy.transpose(%1 : tensor<2x3xf64>) to tensor<3x2xf64>
  %4 = toy.mul %2, %3 : tensor<3x2xf64>                                          // c
  %5 = toy.transpose(%1 : tensor<2x3xf64>) to tensor<3x2xf64>
  %6 = toy.transpose(%0 : tensor<2x3xf64>) to tensor<3x2xf64>
  %7 = toy.mul %5, %6 : tensor<3x2xf64>                                          // d
  toy.print %7 : tensor<3x2xf64>
  toy.return
}
```

**6b. CSE.** Work top to bottom, merging identical pure ops (same op, same
operands, same attributes):
1. `%1` is the same constant as `%0`: merge. Uses of `%1` now point to `%0`.
2. `%3` is now `transpose(%0)`, same as `%2`: merge. Likewise `%5` and `%6`.
3. `%4` is now `mul %2, %2` and `%7` is `mul %2, %2`: merge.

5 ops:

```mlir
toy.func @main() {
  %0 = toy.constant dense<[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]> : tensor<2x3xf64>
  %1 = toy.transpose(%0 : tensor<2x3xf64>) to tensor<3x2xf64>
  %2 = toy.mul %1, %1 : tensor<3x2xf64>
  toy.print %2 : tensor<3x2xf64>
  toy.return
}
```

**6c. DCE.** Nothing left to delete here, because CSE already removed the
duplicates. If `a` and `b` had *different* values, `c` would not merge with
`d`; it would stay as an unused `mul`, and DCE would delete it (pure, no
uses). Either way the end state is the same, only the pass that gets the
credit changes.

Result: **12 ops down to 5**, from three one-line rewrite rules:

| After | Ops in `@main` |
|---|---|
| Stage 3 (MLIRGen, calls not inlined) | 8 |
| Stage 4 (inlining) | 12 |
| Stage 5 (shape inference) | 12 |
| 6a (reshape folding) | 10 |
| 6b (CSE) | 5 |

This is why the IR is high-level: these were 1-line pattern rewrites. After
loops are generated you could not easily see "this is a transpose".

### Stage 7 [Middle-end]: Lower Toy -> Affine / Arith / MemRef

Tensors (values) become memrefs (buffers). Each Toy op becomes loops that
read/write them. `toy.print` is left alone for now (**partial lowering**), so
the IR contains a mix of dialects.

```mlir
func.func @main() {
  %cst = arith.constant 1.0 : f64   // ...constants 1.0 ... 6.0
  %a = memref.alloc() : memref<2x3xf64>      // holds constant data
  affine.store %cst,   %a[0, 0] : memref<2x3xf64>
  affine.store %cst_0, %a[0, 1] : memref<2x3xf64>
  ...                                         // 6 stores total

  %t = memref.alloc() : memref<3x2xf64>      // transpose result
  affine.for %i = 0 to 3 {
    affine.for %j = 0 to 2 {
      %v = affine.load %a[%j, %i] : memref<2x3xf64>   // indices swapped = transpose
      affine.store %v, %t[%i, %j] : memref<3x2xf64>
    }
  }

  %m = memref.alloc() : memref<3x2xf64>      // mul result
  affine.for %i = 0 to 3 {
    affine.for %j = 0 to 2 {
      %x = affine.load %t[%i, %j] : memref<3x2xf64>
      %y = arith.mulf %x, %x : f64
      affine.store %y, %m[%i, %j] : memref<3x2xf64>
    }
  }

  toy.print %m : memref<3x2xf64>
  memref.dealloc %m
  memref.dealloc %t
  memref.dealloc %a
  return
}
```
Still middle-end territory: more affine passes can run here, e.g.
**loop fusion** (merge the two `3x2` nests and drop `%t`) and
**scalar replacement** (keep values in registers).

After fusion:

```mlir
affine.for %i = 0 to 3 {
  affine.for %j = 0 to 2 {
    %v = affine.load %a[%j, %i] : memref<2x3xf64>
    %y = arith.mulf %v, %v : f64
    affine.store %y, %m[%i, %j] : memref<3x2xf64>
  }
}
```
One loop nest, no intermediate buffer. This is the payoff of having
progressive levels: fusion is trivial at the loop level.

### Stage 8 [Backend]: Lower to the LLVM dialect

`affine.for` -> `scf.for` -> `cf.br` basic blocks with block arguments;
`affine.load/store` -> address arithmetic + `llvm.load/store`;
`memref` -> pointer + sizes/strides; `memref.alloc` -> `malloc`;
`toy.print` -> a loop calling `printf`.

```mlir
llvm.func @main() {
  %buf = llvm.call @malloc(...) : (i64) -> !llvm.ptr
  ...
  llvm.br ^loop_i(%c0 : i64)
^loop_i(%i: i64):                               // block argument = SSA phi
  %cond = llvm.icmp "slt" %i, %c3 : i64
  llvm.cond_br %cond, ^loop_j(%c0 : i64), ^exit
^loop_j(%j: i64):
  ...
  %p   = llvm.getelementptr %buf[%idx] : (!llvm.ptr, i64) -> !llvm.ptr
  %v   = llvm.load %p : !llvm.ptr -> f64
  %y   = llvm.fmul %v, %v : f64
  llvm.store %y, %outp : f64, !llvm.ptr
  llvm.br ...
^exit:
  llvm.return
}
```
Now it's a CFG of basic blocks, the exact thing LLVM wants.

### Stage 9 [Backend]: Translate to LLVM IR

A mechanical 1:1 translation out of MLIR into LLVM's own IR (`-emit=llvm`):

```llvm
define void @main() {
entry:
  %buf = call ptr @malloc(i64 48)
  br label %loop_i
loop_i:
  %i = phi i64 [ 0, %entry ], [ %i.next, %loop_i.latch ]   ; here is the phi
  ...
  %v = load double, ptr %p
  %y = fmul double %v, %v
  store double %y, ptr %q
  ...
}
```
LLVM's own optimizer (-O2) then runs: loop unrolling (trip count 2 and 3 are
known), vectorization, instcombine, etc. The middle-end idea repeats: LLVM
has its own middle-end.

### Stage 10 [Backend]: Machine code

LLVM does instruction selection, register allocation, scheduling, emission.
For x86-64 the hot part might look like:

```asm
movsd  xmm0, [rdi + rax*8]     ; load a[j][i]
mulsd  xmm0, xmm0              ; v * v
movsd  [rsi + rcx*8], xmm0     ; store
inc    rax
cmp    rax, 3
jl     .loop
```
Then either write an object file (AOT) or execute it in memory (JIT, `-emit=jit`).

### Stage 11: Output

```
1.000000 16.000000
4.000000 25.000000
9.000000 36.000000
```
(`transpose(a) * transpose(a)`: each element squared, in 3x2 layout.)

### Summary: who does what

| Stage | Input -> Output | Phase | Knows about |
|---|---|---|---|
| Lex | chars -> tokens | Frontend | source language |
| Parse | tokens -> AST | Frontend | source language |
| MLIRGen | AST -> Toy IR | Frontend | source language + Toy dialect |
| Inline | Toy IR -> Toy IR | Middle | Toy dialect only |
| Shape inference | Toy IR -> Toy IR | Middle | Toy dialect only |
| Canonicalize / CSE / DCE | Toy IR -> Toy IR | Middle | generic (op traits like `Pure`) |
| Lower to Affine | Toy -> Affine/Arith/MemRef | Middle (partial lowering) | loop/buffer level |
| Loop fusion etc. | Affine -> Affine | Middle | loops, memory |
| Lower to LLVM dialect | Affine/... -> LLVM dialect | Backend | LLVM-like machine model |
| Translate | LLVM dialect -> LLVM IR | Backend | LLVM |
| LLVM codegen | LLVM IR -> machine code | Backend | target ISA (x86, ARM, ...) |

Note how the early middle-end stages know *nothing* about Toy syntax and
nothing about x86. That independence is the entire point of the IR.

Same shape as every ML compiler (TensorFlow/XLA, IREE, Triton, torch-mlir):
high-level tensor ops -> optimize -> lower step by step -> loops/kernels ->
