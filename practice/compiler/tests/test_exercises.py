import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "exercises")]

from mini_ir import parse, run


def count(fn, opcode):
    return sum(op.opcode == opcode for op in fn.ops)


def same_behavior(tc, before_text, after_fn, inputs=((3, 5), (0, 0), (-2, 7))):
    before = parse(before_text)
    for args in inputs:
        tc.assertEqual(run(before, list(args)), run(after_fn, list(args)))


class T2(unittest.TestCase):
    def test_fold_chain(self):
        from ex2_constant_folding import constant_fold
        src = """func @f(%a, %b) {
          %c1 = const 2
          %c2 = const 3
          %s = add %c1, %c2
          %p = mul %s, %c2
          %r = add %p, %a
          ret %r
        }"""
        out = constant_fold(parse(src))
        self.assertEqual(count(out, "add"), 1)   # only %a + const left
        self.assertEqual(count(out, "mul"), 0)
        same_behavior(self, src, out)


class T3(unittest.TestCase):
    def test_dead_chain(self):
        from ex3_dce import dce
        src = """func @f(%a, %b) {
          %x = add %a, %b
          %y = mul %x, %x
          %z = sub %y, %a
          ret %a
        }"""
        out = dce(parse(src))
        self.assertEqual(len(out.ops), 1)
        same_behavior(self, src, out)

    def test_keeps_side_effects(self):
        from ex3_dce import dce
        src = """func @f(%a, %b) {
          %x = add %a, %b
          print %x
          ret %a
        }"""
        out = dce(parse(src))
        self.assertEqual(count(out, "print"), 1)
        self.assertEqual(count(out, "add"), 1)
        same_behavior(self, src, out)


class T4(unittest.TestCase):
    def test_cse_basic(self):
        from ex4_cse import cse
        src = """func @f(%a, %b) {
          %x = add %a, %b
          %y = add %a, %b
          %r = mul %x, %y
          ret %r
        }"""
        out = cse(parse(src))
        self.assertEqual(count(out, "add"), 1)
        same_behavior(self, src, out)

    def test_cse_commutative(self):
        from ex4_cse import cse
        src = """func @f(%a, %b) {
          %x = add %a, %b
          %y = add %b, %a
          %r = sub %x, %y
          ret %r
        }"""
        out = cse(parse(src))
        self.assertEqual(count(out, "add"), 1)
        same_behavior(self, src, out)

    def test_sub_not_commutative(self):
        from ex4_cse import cse
        src = """func @f(%a, %b) {
          %x = sub %a, %b
          %y = sub %b, %a
          %r = add %x, %y
          ret %r
        }"""
        out = cse(parse(src))
        self.assertEqual(count(out, "sub"), 2)
        same_behavior(self, src, out)

    def test_never_merges_prints(self):
        from ex4_cse import cse
        src = """func @f(%a, %b) {
          print %a
          print %a
          ret %a
        }"""
        self.assertEqual(count(cse(parse(src)), "print"), 2)


class T5(unittest.TestCase):
    def test_identities(self):
        from ex5_peephole import simplify
        src = """func @f(%a, %b) {
          %one = const 1
          %zero = const 0
          %x = mul %a, %one
          %y = add %x, %zero
          %z = sub %y, %zero
          ret %z
        }"""
        out = simplify(parse(src))
        self.assertEqual(count(out, "mul") + count(out, "add") + count(out, "sub"), 0)
        same_behavior(self, src, out)

    def test_mul_zero_and_self_sub(self):
        from ex5_peephole import simplify
        src = """func @f(%a, %b) {
          %zero = const 0
          %x = mul %a, %zero
          %y = sub %b, %b
          %r = add %x, %y
          ret %r
        }"""
        out = simplify(parse(src))
        same_behavior(self, src, out)
        self.assertEqual(count(out, "mul") + count(out, "sub"), 0)


class T6(unittest.TestCase):
    def test_pipeline(self):
        from ex6_pipeline import optimize
        src = """func @f(%a, %b) {
          %one = const 1
          %zero = const 0
          %x = add %a, %b
          %y = add %b, %a
          %m = mul %x, %one
          %n = add %y, %zero
          %dead = mul %a, %b
          %r = sub %m, %n
          print %r
          ret %r
        }"""
        out = optimize(parse(src))
        same_behavior(self, src, out)
        self.assertLessEqual(len(out.ops), 3)   # print, ret and (ideally) const 0


if __name__ == "__main__":
    unittest.main()
