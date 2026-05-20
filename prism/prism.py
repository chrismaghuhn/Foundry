"""
prism.py - tiny query language for structured data (dicts/lists/primitives)

vaguely jq-inspired. pipe stuff together, access fields, filter, map.

    .users | filter(.age > 18) | map(.name)
    .config.db.host
    .items[0].price * .items[0].qty
    .orders | sort(.total) | last()

Grammar (roughly):
    expr        := pipe_expr
    pipe_expr   := conditional ('|' conditional)*
    conditional := or_expr ('?' pipe_expr ':' conditional)?
    or_expr     := and_expr ('or' and_expr)*
    and_expr    := eq_expr ('and' eq_expr)*
    eq_expr     := cmp_expr (('==' | '!=') cmp_expr)?
    cmp_expr    := add_expr (('<' | '>' | '<=' | '>=') add_expr)?
    add_expr    := mul_expr (('+' | '-') mul_expr)*
    mul_expr    := unary (('*' | '/' | '%') unary)*
    unary       := ('not' | '-') unary | access
    access      := primary ('.' IDENT | '[' expr ']' | '(' args ')')*
    primary     := NUMBER | STRING | true | false | null
                 | IDENT | '.' | '@' | '$'
                 | '[' items ']' | '{' pairs '}' | '(' expr ')'
"""

from __future__ import annotations

import operator
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable


# tokens

class TT(Enum):
    """Token kinds for the Prism lexer/parser."""
    NUMBER   = auto()
    STRING   = auto()
    TRUE     = auto()
    FALSE    = auto()
    NULL     = auto()
    IDENT    = auto()
    PLUS     = auto()
    MINUS    = auto()
    STAR     = auto()
    SLASH    = auto()
    PERCENT  = auto()
    EQ       = auto()
    NE       = auto()
    LT       = auto()
    GT       = auto()
    LE       = auto()
    GE       = auto()
    AND      = auto()
    OR       = auto()
    NOT      = auto()
    DOT      = auto()
    COMMA    = auto()
    COLON    = auto()
    PIPE     = auto()
    QUESTION = auto()
    LPAREN   = auto()
    RPAREN   = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LBRACE   = auto()
    RBRACE   = auto()
    DOLLAR   = auto()
    AT       = auto()
    EOF      = auto()


@dataclass(frozen=True, slots=True)
class Token:
    type: TT
    value: Any
    line: int
    col: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r})"


# errors

class LexError(Exception):
    def __init__(self, msg, line, col):
        self.line = line
        self.col = col
        super().__init__(f"{line}:{col}: {msg}")

class ParseError(Exception):
    def __init__(self, msg, tok):
        self.token = tok
        super().__init__(f"{tok.line}:{tok.col}: {msg}")

class EvalError(Exception):
    pass


TokenType = TT
LexerError = LexError


# lexer

_KEYWORDS = {
    'true': TT.TRUE, 'false': TT.FALSE, 'null': TT.NULL,
    'and': TT.AND, 'or': TT.OR, 'not': TT.NOT,
}

_SINGLE = {
    '+': TT.PLUS, '-': TT.MINUS, '*': TT.STAR, '/': TT.SLASH,
    '%': TT.PERCENT, ',': TT.COMMA, ':': TT.COLON, '|': TT.PIPE,
    '?': TT.QUESTION, '(': TT.LPAREN, ')': TT.RPAREN,
    '[': TT.LBRACKET, ']': TT.RBRACKET, '{': TT.LBRACE, '}': TT.RBRACE,
    '$': TT.DOLLAR, '@': TT.AT,
}

_ESCAPES = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\', '"': '"', "'": "'"}


class Lexer:
    def __init__(self, src: str):
        self.src = src
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: list[Token] = []

    def tokenize(self) -> list[Token]:
        while self.pos < len(self.src):
            self._scan()
        self.tokens.append(Token(TT.EOF, None, self.line, self.col))
        return self.tokens

    def _peek(self, offset=0) -> str:
        p = self.pos + offset
        return self.src[p] if p < len(self.src) else '\0'

    def _advance(self) -> str:
        ch = self.src[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _add(self, tt: TT, val: Any = None):
        self.tokens.append(Token(tt, val, self.line, self.col))

    def _scan(self):
        ch = self._advance()

        if ch in ' \t\r\n':
            return

        if ch == '#':
            while self.pos < len(self.src) and self._peek() != '\n':
                self._advance()
            return

        if ch in _SINGLE:
            self._add(_SINGLE[ch])
            return

        if ch == '.':
            self._add(TT.DOT)
            return

        if ch == '=':
            if self._peek() == '=':
                self._advance()
                self._add(TT.EQ)
            else:
                raise LexError("expected '==' (single '=' is not valid)", self.line, self.col)
            return

        if ch == '!':
            if self._peek() == '=':
                self._advance()
                self._add(TT.NE)
            else:
                raise LexError("expected '!='", self.line, self.col)
            return

        if ch == '<':
            if self._peek() == '=':
                self._advance()
                self._add(TT.LE)
            else:
                self._add(TT.LT)
            return

        if ch == '>':
            if self._peek() == '=':
                self._advance()
                self._add(TT.GE)
            else:
                self._add(TT.GT)
            return

        if ch.isdigit():
            self._scan_number(ch)
            return

        if ch in '"\'':
            self._scan_string(ch)
            return

        if ch.isalpha() or ch == '_':
            self._scan_ident(ch)
            return

        raise LexError(f"unexpected character: {ch!r}", self.line, self.col)

    def _scan_number(self, first: str):
        parts = [first]
        while self.pos < len(self.src) and self._peek().isdigit():
            parts.append(self._advance())

        if self._peek() == '.' and self._peek(1).isdigit():
            parts.append(self._advance())
            while self.pos < len(self.src) and self._peek().isdigit():
                parts.append(self._advance())
            self._add(TT.NUMBER, float(''.join(parts)))
        else:
            self._add(TT.NUMBER, int(''.join(parts)))

    def _scan_string(self, quote: str):
        parts = []
        while self.pos < len(self.src) and self._peek() != quote:
            ch = self._advance()
            if ch == '\\':
                if self.pos >= len(self.src):
                    raise LexError("unterminated escape", self.line, self.col)
                esc = self._advance()
                if esc not in _ESCAPES:
                    raise LexError(f"unknown escape \\{esc}", self.line, self.col)
                parts.append(_ESCAPES[esc])
            else:
                parts.append(ch)

        if self.pos >= len(self.src):
            raise LexError("unterminated string", self.line, self.col)
        self._advance()  # closing quote
        self._add(TT.STRING, ''.join(parts))

    def _scan_ident(self, first: str):
        parts = [first]
        while self.pos < len(self.src) and (self._peek().isalnum() or self._peek() == '_'):
            parts.append(self._advance())
        name = ''.join(parts)
        self._add(_KEYWORDS.get(name, TT.IDENT), name)


# AST nodes

@dataclass
class Num:
    value: int | float

@dataclass
class Str:
    value: str

@dataclass
class Bool:
    value: bool

@dataclass
class Null:
    pass

@dataclass
class Ident:
    name: str

@dataclass
class Current:
    """the '.' — current value in context"""
    pass

@dataclass
class Root:
    """'$' — the root document"""
    pass

@dataclass
class Arr:
    elems: list

    @property
    def elements(self) -> list:
        return self.elems

@dataclass
class Obj:
    pairs: list  # list of (str | ASTNode, ASTNode)

@dataclass
class BinOp:
    left: Any
    op: str
    right: Any

@dataclass
class UnaryOp:
    op: str
    operand: Any

@dataclass
class PropAccess:
    obj: Any
    name: str

@dataclass
class IdxAccess:
    obj: Any
    index: Any

@dataclass
class SliceAccess:
    obj: Any
    start: Any  # can be None
    end: Any    # can be None

@dataclass
class Call:
    func: Any
    args: list

@dataclass
class Pipe:
    left: Any
    right: Any

@dataclass
class Cond:
    test: Any
    then: Any
    else_: Any

ASTNode = (
    Num | Str | Bool | Null | Ident | Current | Root |
    Arr | Obj | BinOp | UnaryOp | PropAccess | IdxAccess |
    SliceAccess | Call | Pipe | Cond
)

NumberLiteral = Num
StringLiteral = Str
BoolLiteral = Bool
NullLiteral = Null
Identifier = Ident
CurrentValue = Current
RootValue = Root
ArrayLiteral = Arr
ObjectLiteral = Obj
BinaryOp = BinOp
PropertyAccess = PropAccess
IndexAccess = IdxAccess
FunctionCall = Call
PipeExpr = Pipe
ConditionalExpr = Cond


# parser

class Parser:
    """
    Recursive descent. Precedence low->high:
      pipe -> conditional -> or -> and -> eq -> cmp -> add -> mul -> unary -> access -> primary
    """

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def parse(self) -> ASTNode:
        node = self._pipe()
        if self._peek().type != TT.EOF:
            raise ParseError(f"unexpected token '{self._peek().value}'", self._peek())
        return node

    def _peek(self, offset=0) -> Token:
        p = self.pos + offset
        return self.tokens[min(p, len(self.tokens) - 1)]

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        if self._peek().type != TT.EOF:
            self.pos += 1
        return tok

    def _check(self, *types) -> bool:
        return self._peek().type in types

    def _match(self, *types) -> Token | None:
        if self._check(*types):
            return self._advance()
        return None

    def _expect(self, tt: TT, msg: str) -> Token:
        if not self._check(tt):
            raise ParseError(msg, self._peek())
        return self._advance()

    def _pipe(self) -> ASTNode:
        left = self._conditional()
        while self._match(TT.PIPE):
            left = Pipe(left, self._conditional())
        return left

    def _conditional(self) -> ASTNode:
        expr = self._or()
        if self._match(TT.QUESTION):
            then = self._pipe()
            self._expect(TT.COLON, "expected ':' in ternary")
            else_ = self._conditional()
            return Cond(expr, then, else_)
        return expr

    def _or(self) -> ASTNode:
        left = self._and()
        while self._match(TT.OR):
            left = BinOp(left, 'or', self._and())
        return left

    def _and(self) -> ASTNode:
        left = self._eq()
        while self._match(TT.AND):
            left = BinOp(left, 'and', self._eq())
        return left

    def _eq(self) -> ASTNode:
        left = self._cmp()
        if self._match(TT.EQ):
            return BinOp(left, '==', self._cmp())
        if self._match(TT.NE):
            return BinOp(left, '!=', self._cmp())
        return left

    def _cmp(self) -> ASTNode:
        left = self._add()
        for tt, op in [(TT.LE, '<='), (TT.GE, '>='), (TT.LT, '<'), (TT.GT, '>')]:
            if self._match(tt):
                return BinOp(left, op, self._add())
        return left

    def _add(self) -> ASTNode:
        left = self._mul()
        while True:
            if self._match(TT.PLUS):
                left = BinOp(left, '+', self._mul())
            elif self._match(TT.MINUS):
                left = BinOp(left, '-', self._mul())
            else:
                break
        return left

    def _mul(self) -> ASTNode:
        left = self._unary()
        while True:
            if self._match(TT.STAR):
                left = BinOp(left, '*', self._unary())
            elif self._match(TT.SLASH):
                left = BinOp(left, '/', self._unary())
            elif self._match(TT.PERCENT):
                left = BinOp(left, '%', self._unary())
            else:
                break
        return left

    def _unary(self) -> ASTNode:
        if self._match(TT.NOT):
            return UnaryOp('not', self._unary())
        if self._match(TT.MINUS):
            return UnaryOp('-', self._unary())
        return self._access()

    def _access(self) -> ASTNode:
        expr = self._primary()
        while True:
            if self._match(TT.DOT):
                if not self._check(TT.IDENT):
                    raise ParseError("expected property name after '.'", self._peek())
                expr = PropAccess(expr, self._advance().value)

            elif self._match(TT.LBRACKET):
                if self._check(TT.COLON):
                    # [:end]
                    self._advance()
                    end = self._pipe() if not self._check(TT.RBRACKET) else None
                    self._expect(TT.RBRACKET, "expected ']'")
                    expr = SliceAccess(expr, None, end)
                else:
                    idx = self._pipe()
                    if self._match(TT.COLON):
                        end = self._pipe() if not self._check(TT.RBRACKET) else None
                        self._expect(TT.RBRACKET, "expected ']'")
                        expr = SliceAccess(expr, idx, end)
                    else:
                        self._expect(TT.RBRACKET, "expected ']'")
                        expr = IdxAccess(expr, idx)

            elif self._match(TT.LPAREN):
                args = self._args()
                self._expect(TT.RPAREN, "expected ')'")
                expr = Call(expr, args)

            else:
                break
        return expr

    def _args(self) -> list:
        args = []
        if not self._check(TT.RPAREN):
            args.append(self._pipe())
            while self._match(TT.COMMA):
                if self._check(TT.RPAREN):
                    break
                args.append(self._pipe())
        return args

    def _primary(self) -> ASTNode:
        if self._check(TT.NUMBER):
            return Num(self._advance().value)
        if self._check(TT.STRING):
            return Str(self._advance().value)
        if self._match(TT.TRUE):
            return Bool(True)
        if self._match(TT.FALSE):
            return Bool(False)
        if self._match(TT.NULL):
            return Null()
        if self._check(TT.IDENT):
            return Ident(self._advance().value)

        # '.' alone or '.prop' shorthand
        if self._match(TT.DOT):
            if self._check(TT.IDENT):
                return PropAccess(Current(), self._advance().value)
            return Current()

        if self._match(TT.AT):
            return Current()

        if self._match(TT.DOLLAR):
            return Root()

        if self._match(TT.LBRACKET):
            elems = []
            if not self._check(TT.RBRACKET):
                elems.append(self._pipe())
                while self._match(TT.COMMA):
                    if self._check(TT.RBRACKET):
                        break
                    elems.append(self._pipe())
            self._expect(TT.RBRACKET, "expected ']'")
            return Arr(elems)

        if self._match(TT.LBRACE):
            pairs = []
            if not self._check(TT.RBRACE):
                pairs.append(self._obj_pair())
                while self._match(TT.COMMA):
                    if self._check(TT.RBRACE):
                        break
                    pairs.append(self._obj_pair())
            self._expect(TT.RBRACE, "expected '}'")
            return Obj(pairs)

        if self._match(TT.LPAREN):
            expr = self._pipe()
            self._expect(TT.RPAREN, "expected ')'")
            return expr

        raise ParseError(f"unexpected {self._peek().type.name}", self._peek())

    def _obj_pair(self):
        if self._check(TT.IDENT):
            key = self._advance().value
        elif self._check(TT.STRING):
            key = self._advance().value
        elif self._match(TT.LBRACKET):
            key = self._pipe()
            self._expect(TT.RBRACKET, "expected ']'")
        else:
            raise ParseError("expected object key", self._peek())
        self._expect(TT.COLON, "expected ':'")
        return (key, self._pipe())


# evaluation context

@dataclass
class Context:
    current: Any
    root: Any
    variables: dict[str, Any] = field(default_factory=dict)

    def push(self, val: Any) -> 'Context':
        return Context(current=val, root=self.root, variables=self.variables)


# evaluator

_FUNC_SENTINEL = object()  # marker for function references


class Evaluator:
    def __init__(self):
        self.fns: dict[str, Callable] = self._builtins()

    def run(self, node: ASTNode, data: Any, variables: dict | None = None) -> Any:
        ctx = Context(current=data, root=data, variables=variables or {})
        return self._eval(node, ctx)

    def _eval(self, node: ASTNode, ctx: Context) -> Any:
        t = type(node)

        if t is Num or t is Str or t is Bool:
            return node.value
        if t is Null:
            return None
        if t is Current:
            return ctx.current
        if t is Root:
            return ctx.root

        if t is Ident:
            name = node.name
            if name in self.fns:
                return (_FUNC_SENTINEL, name)
            if name in ctx.variables:
                return ctx.variables[name]
            return self._getprop(ctx.current, name)

        if t is Arr:
            return [self._eval(e, ctx) for e in node.elems]

        if t is Obj:
            result = {}
            for k, v in node.pairs:
                key = self._eval(k, ctx) if not isinstance(k, str) else k
                result[key] = self._eval(v, ctx)
            return result

        if t is BinOp:
            return self._eval_binop(node, ctx)

        if t is UnaryOp:
            val = self._eval(node.operand, ctx)
            if node.op == '-':
                return -val
            if node.op == 'not':
                return not self._truthy(val)
            raise EvalError(f"unknown unary op: {node.op}")

        if t is PropAccess:
            obj = self._eval(node.obj, ctx)
            return self._getprop(obj, node.name)

        if t is IdxAccess:
            obj = self._eval(node.obj, ctx)
            idx = self._eval(node.index, ctx)
            if isinstance(obj, dict):
                return obj.get(idx)
            if isinstance(obj, (list, str, tuple)):
                if isinstance(idx, int) and -len(obj) <= idx < len(obj):
                    return obj[idx]
            return None

        if t is SliceAccess:
            obj = self._eval(node.obj, ctx)
            start = self._eval(node.start, ctx) if node.start is not None else None
            end = self._eval(node.end, ctx) if node.end is not None else None
            try:
                return obj[start:end]
            except TypeError:
                return None

        if t is Call:
            fn = self._eval(node.func, ctx)
            if isinstance(fn, tuple) and fn[0] is _FUNC_SENTINEL:
                name = fn[1]
                return self.fns[name](ctx, node.args)
            raise EvalError(f"not callable: {fn!r}")

        if t is Pipe:
            left_val = self._eval(node.left, ctx)
            new_ctx = ctx.push(left_val)
            result = self._eval(node.right, new_ctx)
            # allow bare function name on right side: `.items | first`
            if isinstance(result, tuple) and result[0] is _FUNC_SENTINEL:
                return self.fns[result[1]](new_ctx, [])
            return result

        if t is Cond:
            test = self._eval(node.test, ctx)
            return self._eval(node.then if self._truthy(test) else node.else_, ctx)

        raise EvalError(f"unknown AST node: {t}")

    def _eval_binop(self, node: BinOp, ctx: Context) -> Any:
        # short circuit
        if node.op == 'and':
            left = self._eval(node.left, ctx)
            return left if not self._truthy(left) else self._eval(node.right, ctx)
        if node.op == 'or':
            left = self._eval(node.left, ctx)
            return left if self._truthy(left) else self._eval(node.right, ctx)

        left = self._eval(node.left, ctx)
        right = self._eval(node.right, ctx)

        ops = {
            '+': lambda a, b: a + b,
            '-': operator.sub,
            '*': operator.mul,
            '/': lambda a, b: a / b if b != 0 else None,
            '%': operator.mod,
            '==': operator.eq,
            '!=': operator.ne,
            '<': operator.lt,
            '>': operator.gt,
            '<=': operator.le,
            '>=': operator.ge,
        }
        fn = ops.get(node.op)
        if fn is None:
            raise EvalError(f"unknown op: {node.op}")
        try:
            return fn(left, right)
        except TypeError as e:
            raise EvalError(f"type error in '{node.op}': {e}")

    def _getprop(self, obj: Any, name: str) -> Any:
        if obj is None:
            return None
        if isinstance(obj, dict):
            return obj.get(name)
        return getattr(obj, name, None)

    def _truthy(self, val: Any) -> bool:
        if val is None or val is False:
            return False
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return val != 0
        if isinstance(val, (str, list, dict)):
            return len(val) > 0
        return True

    # builtins — functions receive (ctx, ast_args) and eval args themselves
    # this lets map/filter/etc re-evaluate the expression per item

    def _builtins(self) -> dict:
        return {
            'map':          self._fn_map,
            'filter':       self._fn_filter,
            'select':       self._fn_select,
            'sort':         self._fn_sort,
            'reverse':      self._fn_reverse,
            'unique':       self._fn_unique,
            'flatten':      self._fn_flatten,
            'group':        self._fn_group,
            'first':        self._fn_first,
            'last':         self._fn_last,
            'nth':          self._fn_nth,
            'take':         self._fn_take,
            'drop':         self._fn_drop,
            'length':       self._fn_length,
            'count':        self._fn_count,
            'sum':          self._fn_sum,
            'avg':          self._fn_avg,
            'min':          self._fn_min,
            'max':          self._fn_max,
            'join':         self._fn_join,
            'split':        self._fn_split,
            'trim':         self._fn_trim,
            'upper':        self._fn_upper,
            'lower':        self._fn_lower,
            'contains':     self._fn_contains,
            'starts_with':  self._fn_starts_with,
            'ends_with':    self._fn_ends_with,
            'replace':      self._fn_replace,
            'type':         self._fn_type,
            'keys':         self._fn_keys,
            'values':       self._fn_values,
            'entries':      self._fn_entries,
            'from_entries': self._fn_from_entries,
            'default':      self._fn_default,
            'debug':        self._fn_debug,
        }

    def _require_list(self, ctx, fname):
        if not isinstance(ctx.current, list):
            raise EvalError(f"{fname}() requires an array, got {type(ctx.current).__name__}")
        return ctx.current

    def _fn_map(self, ctx, args):
        if len(args) != 1:
            raise EvalError("map() requires 1 argument")
        arr = self._require_list(ctx, 'map')
        return [self._eval(args[0], ctx.push(item)) for item in arr]

    def _fn_filter(self, ctx, args):
        if len(args) != 1:
            raise EvalError("filter() requires 1 argument")
        arr = self._require_list(ctx, 'filter')
        return [item for item in arr if self._truthy(self._eval(args[0], ctx.push(item)))]

    def _fn_select(self, ctx, args):
        def pick(item):
            item_ctx = ctx.push(item)
            result = {}
            for arg in args:
                if isinstance(arg, PropAccess):
                    result[arg.name] = self._eval(arg, item_ctx)
                else:
                    val = self._eval(arg, item_ctx)
                    if isinstance(val, dict):
                        result.update(val)
                    else:
                        result[repr(arg)] = val
            return result

        if isinstance(ctx.current, list):
            return [pick(item) for item in ctx.current]
        return pick(ctx.current)

    def _fn_sort(self, ctx, args):
        arr = self._require_list(ctx, 'sort')
        if not args:
            return sorted(arr, key=lambda x: (x is None, x))
        return sorted(arr, key=lambda x: (
            (v := self._eval(args[0], ctx.push(x))) is None, v
        ))

    def _fn_reverse(self, ctx, args):
        cur = ctx.current
        if isinstance(cur, list):
            return cur[::-1]
        if isinstance(cur, str):
            return cur[::-1]
        raise EvalError("reverse() requires a list or string")

    def _fn_unique(self, ctx, args):
        arr = self._require_list(ctx, 'unique')
        # good enough for json-ish data; doesn't handle unhashable edge cases perfectly
        seen = set()
        out = []
        for item in arr:
            k = repr(item)
            if k not in seen:
                seen.add(k)
                out.append(item)
        return out

    def _fn_flatten(self, ctx, args):
        arr = self._require_list(ctx, 'flatten')
        out = []
        for item in arr:
            if isinstance(item, list):
                out.extend(item)
            else:
                out.append(item)
        return out

    def _fn_group(self, ctx, args):
        if len(args) != 1:
            raise EvalError("group() requires 1 argument")
        arr = self._require_list(ctx, 'group')
        groups: dict = {}
        for item in arr:
            k = str(self._eval(args[0], ctx.push(item)))
            groups.setdefault(k, []).append(item)
        return groups

    def _fn_first(self, ctx, args):
        cur = ctx.current
        return cur[0] if isinstance(cur, (list, str)) and cur else None

    def _fn_last(self, ctx, args):
        cur = ctx.current
        return cur[-1] if isinstance(cur, (list, str)) and cur else None

    def _fn_nth(self, ctx, args):
        if not args:
            raise EvalError("nth() requires 1 argument")
        cur = ctx.current
        n = self._eval(args[0], ctx)
        if isinstance(cur, (list, str)) and isinstance(n, int) and 0 <= n < len(cur):
            return cur[n]
        return None

    def _fn_take(self, ctx, args):
        if not args:
            raise EvalError("take() requires 1 argument")
        n = self._eval(args[0], ctx)
        cur = ctx.current
        return cur[:n] if isinstance(cur, list) else None

    def _fn_drop(self, ctx, args):
        if not args:
            raise EvalError("drop() requires 1 argument")
        n = self._eval(args[0], ctx)
        cur = ctx.current
        return cur[n:] if isinstance(cur, list) else None

    def _fn_length(self, ctx, args):
        cur = ctx.current
        return len(cur) if isinstance(cur, (list, str, dict)) else 0

    def _fn_count(self, ctx, args):
        arr = self._require_list(ctx, 'count')
        if not args:
            return len(arr)
        return sum(1 for item in arr if self._truthy(self._eval(args[0], ctx.push(item))))

    def _fn_sum(self, ctx, args):
        arr = self._require_list(ctx, 'sum')
        vals = [self._eval(args[0], ctx.push(i)) for i in arr] if args else arr
        return sum(v for v in vals if isinstance(v, (int, float)))

    def _fn_avg(self, ctx, args):
        arr = self._require_list(ctx, 'avg')
        vals = [self._eval(args[0], ctx.push(i)) for i in arr] if args else arr
        nums = [v for v in vals if isinstance(v, (int, float))]
        return sum(nums) / len(nums) if nums else 0

    def _fn_min(self, ctx, args):
        arr = ctx.current
        if not isinstance(arr, list) or not arr:
            return None
        vals = [self._eval(args[0], ctx.push(i)) for i in arr] if args else arr
        nums = [v for v in vals if v is not None]
        return min(nums) if nums else None

    def _fn_max(self, ctx, args):
        arr = ctx.current
        if not isinstance(arr, list) or not arr:
            return None
        vals = [self._eval(args[0], ctx.push(i)) for i in arr] if args else arr
        nums = [v for v in vals if v is not None]
        return max(nums) if nums else None

    def _fn_join(self, ctx, args):
        arr = ctx.current
        sep = self._eval(args[0], ctx) if args else ','
        if isinstance(arr, list):
            return sep.join(str(x) for x in arr)
        return str(arr)

    def _fn_split(self, ctx, args):
        s = ctx.current
        sep = self._eval(args[0], ctx) if args else ' '
        return s.split(sep) if isinstance(s, str) else [s]

    def _fn_trim(self, ctx, args):
        s = ctx.current
        return s.strip() if isinstance(s, str) else s

    def _fn_upper(self, ctx, args):
        s = ctx.current
        return s.upper() if isinstance(s, str) else s

    def _fn_lower(self, ctx, args):
        s = ctx.current
        return s.lower() if isinstance(s, str) else s

    def _fn_contains(self, ctx, args):
        cur = ctx.current
        val = self._eval(args[0], ctx) if args else None
        if isinstance(cur, str):
            return str(val) in cur
        if isinstance(cur, (list, dict)):
            return val in cur
        return False

    def _fn_starts_with(self, ctx, args):
        s = ctx.current
        prefix = self._eval(args[0], ctx) if args else ''
        return s.startswith(prefix) if isinstance(s, str) else False

    def _fn_ends_with(self, ctx, args):
        s = ctx.current
        suffix = self._eval(args[0], ctx) if args else ''
        return s.endswith(suffix) if isinstance(s, str) else False

    def _fn_replace(self, ctx, args):
        if len(args) < 2:
            raise EvalError("replace() needs 2 arguments")
        s = ctx.current
        old = self._eval(args[0], ctx)
        new = self._eval(args[1], ctx)
        return s.replace(old, new) if isinstance(s, str) else s

    def _fn_type(self, ctx, args):
        v = ctx.current
        if v is None:           return 'null'
        if isinstance(v, bool): return 'boolean'
        if isinstance(v, int):  return 'integer'
        if isinstance(v, float): return 'number'
        if isinstance(v, str):  return 'string'
        if isinstance(v, list): return 'array'
        if isinstance(v, dict): return 'object'
        return 'unknown'

    def _fn_keys(self, ctx, args):
        return list(ctx.current.keys()) if isinstance(ctx.current, dict) else []

    def _fn_values(self, ctx, args):
        return list(ctx.current.values()) if isinstance(ctx.current, dict) else []

    def _fn_entries(self, ctx, args):
        if isinstance(ctx.current, dict):
            return [{'key': k, 'value': v} for k, v in ctx.current.items()]
        return []

    def _fn_from_entries(self, ctx, args):
        arr = ctx.current
        if not isinstance(arr, list):
            return {}
        result = {}
        for item in arr:
            if not isinstance(item, dict):
                continue
            # try common key names; use .get with sentinel to handle falsy values properly
            _missing = object()
            k = next((item[kn] for kn in ('key', 'k', 'name') if kn in item), _missing)
            v = next((item[vn] for vn in ('value', 'v') if vn in item), None)
            if k is not _missing:
                result[k] = v
        return result

    def _fn_default(self, ctx, args):
        if ctx.current is None and args:
            return self._eval(args[0], ctx)
        return ctx.current

    def _fn_debug(self, ctx, args):
        print(f"[prism debug] {ctx.current!r}")
        return ctx.current


# public API

class Prism:
    """compile and run prism queries against data"""

    def __init__(self):
        self._ev = Evaluator()
        self._cache: dict[str, ASTNode] = {}

    def compile(self, q: str) -> Callable[[Any], Any]:
        """parse once, run many times"""
        ast = self._parse(q)
        return lambda data, **vars: self._ev.run(ast, data, vars)

    def query(self, q: str, data: Any, **variables) -> Any:
        ast = self._parse(q)
        return self._ev.run(ast, data, variables)

    def _parse(self, q: str) -> ASTNode:
        if q not in self._cache:
            tokens = Lexer(q).tokenize()
            self._cache[q] = Parser(tokens).parse()
        return self._cache[q]


# module-level singleton so the convenience function isn't wasteful
_default = Prism()

def query(q: str, data: Any, **variables) -> Any:
    return _default.query(q, data, **variables)
