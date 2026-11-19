# MLIR practice (needs `mlir-opt`)

Install options: build llvm-project with `-DLLVM_ENABLE_PROJECTS=mlir`, or
use a distro/pip package that ships `mlir-opt`. Try `mlir-opt --version`.

Run each file and compare with your prediction BEFORE running:

    mlir-opt 01_cse.mlir --cse
    mlir-opt 02_canonicalize.mlir --canonicalize
    mlir-opt 03_dce.mlir --symbol-dce        # and --canonicalize
    mlir-opt 04_scf_to_cf.mlir --convert-scf-to-cf
    mlir-opt 05_pipeline.mlir --canonicalize --cse --mlir-print-ir-after-all

Questions to answer in a notes file:
1. Which ops did `--cse` merge, and why not the `memref.load`s in 01?
2. Which canonicalization patterns fired in 02? (`--debug-only=greedy-rewriter`
   needs a debug build.) Find the matching `getCanonicalizationPatterns` or
   `fold` in `mlir/lib/Dialect/Arith/IR/ArithOps.cpp`.
3. In 04, where did the block arguments (phi equivalent) come from?
