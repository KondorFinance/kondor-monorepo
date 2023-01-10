from pyteal import *
from beaker import *

class Helpers:

    def commented_assert(conditions: list[tuple[Expr, str]]) -> list[Expr]:
        return [Assert(cond, comment=cmt) for cond, cmt in conditions]

    

