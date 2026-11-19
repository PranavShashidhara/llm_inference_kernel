# 2. The frontend

The frontend turns **source text** into a **structured form the compiler can
work with**. It happens in four steps. A good analogy is reading an English
sentence:

| Step | Analogy | Input -> Output |
|---|---|---|
| Lexing | splitting text into words | characters -> **tokens** |
| Parsing | working out the grammar | tokens -> **tree (AST)** |
| Semantic analysis | checking it makes sense | AST -> same AST, or errors |
| IR generation | writing it in the compiler's own notation | AST -> **IR** |

("The cat sat." is grammatical. "The cat sat the." is not. "The idea slept
angrily." is grammatical but makes no sense. Parsing catches the second,
semantic analysis catches the third.)

---

## Lexing (tokenization)

Turns a stream of characters into **tokens**: the words of the language.

```
"var a = [1, 2, 3];"  ->  VAR  IDENT(a)  EQ  LBRACKET  NUM(1)  COMMA  NUM(2) ... SEMI
```

A lexer is a simple loop that skips whitespace and comments and groups
characters into tokens (`[0-9]+` -> NUMBER, `[a-zA-Z_]\w*` -> IDENT or a
keyword like `var`). It knows nothing about grammar yet. `1 + + 2` lexes
fine.

## Parsing

Turns tokens into a **tree** by following a **grammar** (the rules of the
language).

```
expr    := term (('+' | '-') term)*
term    := factor (('*' | '/') factor)*
factor  := NUMBER | IDENT | '(' expr ')' | IDENT '(' args ')'
```

Read the rules like this: "an `expr` is a `term`, followed by zero or more
(`+` or `-` followed by a `term`)". Because `term` (multiplication) sits
*inside* `expr` (addition), `*` binds tighter than `+`. That is how operator
precedence is encoded.

Most hand-written compilers, including Toy's, use **recursive descent**: one
function per grammar rule, each consuming tokens and calling the others.

```
parse_expr():      parse_term(), then while next token is + or -: parse_term() again
parse_term():      parse_factor(), then while next token is * or /: ...
parse_factor():    number, name, call, or '(' parse_expr() ')'
```

If the tokens don't fit the grammar, you get a **syntax error**.

## AST (Abstract Syntax Tree)

The parser's output. "Abstract" means it drops punctuation (parentheses,
semicolons) and keeps only the meaning.

```
a * b + c            Add
                    /   \
                  Mul    c
                 /   \
                a     b
```

Typical nodes: `Module`, `Function`, `VarDecl`, `BinaryExpr`, `CallExpr`,
`NumberLiteral`, `ReturnStmt`, `PrintStmt`.

### Parse tree vs. AST (one tree, not two processes)

Parsing is the *process*; the AST is its *output*.

- A strict **parse tree** (concrete syntax tree) keeps every grammar rule and
  token: parentheses, semicolons, and intermediate nodes.
- An **AST** keeps only the meaning and drops the noise.

```
source:  (a + b) * c

Parse tree (concrete)                 AST (abstract)
expr                                       Mul
└─ term                                   /   \
   ├─ factor                           Add     c
   │  ├─ '('                          /   \
   │  ├─ expr                        a     b
   │  │  └─ term ... a + b ...
   │  └─ ')'
   ├─ '*'
   └─ factor
      └─ c
```

Most hand-written parsers (including Toy's) build the AST directly and never
create the full parse tree, so in practice you only ever see the AST. Tools
that need the exact source text (formatters, IDE refactoring) keep a concrete
tree instead.

## Semantic analysis

The grammar can only say what *shape* the code has. Some rules can't be
expressed as shapes. Semantic analysis checks them:

- **Name resolution**: is every variable declared before use? Is a function
  called that doesn't exist? Is a name defined twice?
- **Type checking**: `1 + "hello"` has a perfectly valid shape but is
  invalid.
- **Arity**: does a call pass the right number of arguments?
- **Control-flow rules**: `return` outside a function, `break` outside a
  loop.

Errors are reported with **source locations** (`file:line:col`). Keeping a
location attached to every piece of the program, all the way through the
compiler, is important for good error messages. MLIR makes every operation
carry a `Location`.

**Shape checking is different per language.** Languages with static shapes in
their types (`Matrix<2,3>`) check shapes here. Toy does **not**: its functions
are generic over shapes (`def f(a, b)` works on any size), so shapes are only
known after inlining, and Toy checks them later on the IR in a *shape
inference* pass. See [04-optimizations.md](04-optimizations.md).

## IR generation (the handoff)

The last frontend step walks the AST and emits one IR operation per node. In
toy-mlir this is the `MLIRGen` code. From here on the compiler no longer
cares about the source syntax, only the IR. The IR is described in the next
file: [03-ir-and-ssa.md](03-ir-and-ssa.md).

## Key takeaways

- Lexer: characters -> tokens. Parser: tokens -> AST. Semantic analysis:
  checks meaning. IR generation: AST -> IR.
- The AST is a **tree** that mirrors the text. The IR (next chapter) mirrors
  the computation.
- Parse tree vs. AST: same thing, one with punctuation, one without.
