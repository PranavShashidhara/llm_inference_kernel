func.func @sum(%n: index) -> index {
  %c0 = arith.constant 0 : index
  %c1 = arith.constant 1 : index
  %r = scf.for %i = %c0 to %n step %c1 iter_args(%s = %c0) -> index {
    %s2 = arith.addi %s, %i : index
    scf.yield %s2 : index
  }
  return %r : index
}
