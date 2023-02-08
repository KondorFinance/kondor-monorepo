from pyteal import *
from beaker import *


class Mathemagic():

    @internal(TealType.uint64)
    def tokens_to_mint_initial(self, a_amount, b_amount):
        return Sqrt(a_amount * b_amount) - self.scale

    @internal(TealType.uint64)
    def tokens_to_mint(
        self, 
        issued, 
        a_supply, 
        b_supply, 
        a_amount, 
        b_amount
    ):
        return Seq(
            (a_rat := ScratchVar()).store(
                WideRatio([a_amount, self.scale], [a_supply])
            ),
            (b_rat := ScratchVar()).store(
                WideRatio([b_amount, self.scale], [b_supply])
            ),
            WideRatio(
                [If(a_rat.load() < b_rat.load(), a_rat.load(), b_rat.load()), issued],
                [self.scale],
            ),
        )

    @internal(TealType.uint64)
    def tokens_to_burn(self, issued, supply, amount):
        return WideRatio([supply, amount], [issued])

    @internal(TealType.uint64)
    def tokens_to_swap(self, in_amount, in_supply, out_supply):
        factor = self.scale - self.fee
        return WideRatio(
            [in_amount, factor, out_supply],
            [(in_supply * self.scale) + (in_amount * factor)],
        )

    @internal(TealType.uint64)
    def compute_ratio(self):
        return Seq(
            (
                bal_a := AssetHolding.balance(
                    self.address,
                    self.asset_a
                )
            ),
            (
                bal_b := AssetHolding.balance(
                    self.address,
                    self.asset_b
                )
            ),
            Assert(
                bal_a.hasValue(),
                bal_b.hasValue(),
            ),
            WideRatio([bal_a.value(), self.scale], [bal_b.value()]),
        )

    @internal(TealType.uint64)
    def calculate_slippage(
            self, 
            expected_amt_out: abi.Uint64, 
            amt_out: ScratchVar
        ):
            return Int(1) 