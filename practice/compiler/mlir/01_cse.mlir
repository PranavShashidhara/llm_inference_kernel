func.func @f(%a: i32, %b: i32, %m: memref<4xi32>, %i: index) -> i32 {
  %x = arith.addi %a, %b : i32
  %y = arith.addi %a, %b : i32
  %z = arith.addi %b, %a : i32      // commutative: does CSE catch it?
  %l1 = memref.load %m[%i] : memref<4xi32>
  %l2 = memref.load %m[%i] : memref<4xi32>   // why not merged (or is it)?
  %s1 = arith.addi %x, %y : i32
  %s2 = arith.addi %z, %l1 : i32
  %s3 = arith.addi %s2, %l2 : i32
  %r = arith.addi %s1, %s3 : i32
  return %r : i32
}
