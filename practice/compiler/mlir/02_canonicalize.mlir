func.func @g(%a: i32) -> i32 {
  %c0 = arith.constant 0 : i32
  %c1 = arith.constant 1 : i32
  %c2 = arith.constant 2 : i32
  %c3 = arith.constant 3 : i32
  %x = arith.addi %a, %c0 : i32
  %y = arith.muli %x, %c1 : i32
  %k = arith.addi %c2, %c3 : i32
  %r = arith.muli %y, %k : i32
  return %r : i32
}
