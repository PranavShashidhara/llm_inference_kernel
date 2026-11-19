func.func @h(%a: i32, %b: i32) -> i32 {
  %dead1 = arith.muli %a, %b : i32
  %dead2 = arith.addi %dead1, %a : i32
  return %a : i32
}
func.func private @unused_helper(%x: i32) -> i32 {
  return %x : i32
}
