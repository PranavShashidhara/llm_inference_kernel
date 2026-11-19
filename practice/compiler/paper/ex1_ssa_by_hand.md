# Exercise 1: SSA by hand (paper, 30 min)

Convert each snippet to SSA form (every name assigned once). Write your answers
below each one. Do it before looking at 03-ir-and-ssa.md.

## 1a: straight line
```
x = a + b
x = x * 2
y = x + a
x = y - x
return x
```

## 1b: spot the redundancy (after SSA, which ops are duplicates?)
```
p = a * b
q = a * b + c
r = b * a + d
s = p + q
```
Which are CSE candidates? Is `b * a` one of them? What needs to be true?

## 1c: branches (this is why phi exists)
```
if (cond) { x = a + 1 } else { x = a + 2 }
y = x * 3
```
Write it as basic blocks with a phi (or a block argument, the MLIR way):
```
^entry:  cond_br %cond, ^then, ^else
^then:   %t = ...  br ^merge(%t)
^else:   ...
^merge(%x): ...
```

## 1d: a loop
```
s = 0
for i in 0..n: s = s + i
return s
```
Draw the CFG. Where does the phi (block argument) for `s` and `i` go, and
what are its two incoming values?

## 1e: think
Why can CSE in SSA skip the question "was `a` modified between these two
expressions"? Answer in two sentences.
