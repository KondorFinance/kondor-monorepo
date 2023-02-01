from pyteal import *
from beaker import *
from utils.errors import InvestmentProductErrors

class Helpers:

    def commented_assert(txn, conditions: list[tuple[Expr, str]]) -> list[Expr]:
        basic_checks = [
            (
                txn.rekey_to() == Global.zero_address(), 
                InvestmentProductErrors.rekeyToInvalid
            ),
            (
                txn.close_remainder_to() == Global.zero_address(), 
                InvestmentProductErrors.rekeyToInvalid
            ),
            (
                txn.asset_close_to() == Global.zero_address(), 
                InvestmentProductErrors.rekeyToInvalid
            ),
        ]
        conditions += basic_checks
        return [Assert(cond, comment=cmt) for cond, cmt in conditions]

    

