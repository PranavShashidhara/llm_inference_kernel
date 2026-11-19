func.func @p(%a: i32, %b: i32) -> i32 {
  %c1 = arith.constant 1 : i32
  %c0 = arith.constant 0 : i32
  %x = arith.addi %a, %b : i32
  %y = arith.addi %b, %a : i32
  %m = arith.muli %x, %c1 : i32
  %n = arith.addi %y, %c0 : i32
  %dead = arith.muli %a, %b : i32
  %r = arith.subi %m, %n : i32
  return %r : i32
}
