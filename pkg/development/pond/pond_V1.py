from typing import Final
from pyteal import *
from beaker import *

from .utils.errors import PondErrors
from .utils.transactions import Transactions
from .utils.mathemagic import Mathemagic
from .utils.helpers import Helpers

class Pond(Application):

    # Declare Application state, marking `Final` here so the python class var 
    # doesn't get changed
    # Marking a var `Final` does _not_ change anything at the AVM level
    governor: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        key=Bytes("g"),
        default=Global.creator_address(),
        descr="The current governor of this contract, allowed to do admin type actions",
    )
    asset_a: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        key=Bytes("a"),
        static=True,
        descr="The asset id of asset A",
    )
    asset_b: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        key=Bytes("b"),
        static=True,
        descr="The asset id of asset B",
    )
    pond_token: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        key=Bytes("p"),
        static=True,
        descr="The asset id of the Pond Token, used to track share of pond the holder may recover",
    )
    ratio: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        key=Bytes("r"),
        descr="The ratio between assets (A/B/C)*Scale",
    )

    ##############
    # Constants
    ##############

    # Total supply of the pond tokens
    _total_supply: Final[int] = int(1e10)
    total_supply: Final[Expr] = Int(_total_supply)
    # scale helps with precision when doing computation for
    # the number of tokens to transfer
    _scale: Final[int] = 1000
    scale: Final[Expr] = Int(_scale)
    # Fee for swaps, 5 represents 0.5% ((fee / scale)*100)
    _fee: Final[int] = 5
    fee: Final[Expr] = Int(_fee)

    ##############
    # Administrative Actions
    ##############

    # Call this only on create
    @create
    def create(self):
        return self.initialize_application_state()

    # Only the account set in app_state.governor may call this method
    @external(authorize=Authorize.only(governor))
    def set_governor(self, new_governor: abi.Account):
        """sets the governor of the contract, may only be called by the current 
        governor"""
        return self.governor.set(new_governor.address())

    # Only the account set in app_state.governor may call this method
    @external(authorize=Authorize.only(governor))
    def bootstrap(
        self,
        seed: abi.PaymentTransaction,
        a_asset: abi.Asset,
        b_asset: abi.Asset,
        *,
        output: abi.Uint64,
    ):
        """bootstraps the contract by opting into the assets and creating the 
        pond token. Note this method will fail if it is attempted more than 
        once on the same contract since the assets and pond token application 
        state values are marked as static and cannot be overridden.
        Args:
            seed: Initial Payment transaction to the app account so it can opt 
            in to assets and create pond token.
            a_asset: One of the two assets this pond should allow swapping 
            between.
            b_asset: One of the two assets this pond should allow swapping 
            between.
        Returns:
            The asset id of the pond token created.
        """

        well_formed_bootstrap = [
            (Global.group_size() == Int(2), PondErrors.GroupSizeNot2),
            (
                seed.get().receiver() == self.address,
                PondErrors.ReceiverNotAppAddr,
            ),
            (
                seed.get().amount() >= consts.Algos(0.3),
                PondErrors.AmountLessThanMinimum,
            ),
            (
                a_asset.asset_id() != b_asset.asset_id(),
                PondErrors.AssetIdsIncorrect,
            ),
        ]

        return Seq(
            *Helpers.commented_assert(well_formed_bootstrap),
            self.asset_a.set(a_asset.asset_id()),
            self.asset_b.set(b_asset.asset_id()),
            self.pond_token.set(
                Transactions.do_create_pond_token(
                    self,
                    self.asset_a,
                    self.asset_b
                ),
            ),
            Transactions.do_opt_in(self, self.asset_a),
            Transactions.do_opt_in(self, self.asset_b),
            output.set(self.pond_token),
        )

    @external
    def mint(
        self,
        a_xfer: abi.AssetTransferTransaction,
        b_xfer: abi.AssetTransferTransaction,
        pond_asset: abi.Asset = pond_token,  # type: ignore[assignment],
        a_asset: abi.Asset = asset_a,  # type: ignore[assignment],
        b_asset: abi.Asset = asset_b,  # type: ignore[assignment],
        ):
        """mint pond tokens given some amount of a_asset and b_asset 
        on commit.

        Given some amount of stable assets in the transfer, mint some number of 
        pond tokens calculated with the pond's current balance and 
        circulating supply of pond tokens.

        Args:
            a_xfer: Asset Transfer Transaction of a_asset as a deposit to the 
            pond in exchange for pond tokens.
            b_xfer: Asset Transfer Transaction of b_asset as a deposit to the 
            pond in exchange for pond tokens.
            pond_asset: The asset ID of the pond token so that we may 
            a_asset: The asset ID of the asset A token so that we may 
            distribute it.
            b_asset: The asset ID of the asset B token so that we may 
            distribute it.
        """

        well_formed_mint = [
            (a_asset.asset_id() == self.asset_a, PondErrors.AssetAIncorrect),
            (b_asset.asset_id() == self.asset_b, PondErrors.AssetBIncorrect),
            (
                And(
                    a_xfer.get().sender() == Txn.sender(),
                    b_xfer.get().sender() == Txn.sender()
                ),
                PondErrors.SenderInvalid
            ),
        ]

        valid_asset_a_xfer = [
            (
                a_xfer.get().asset_receiver() == self.address,
                PondErrors.ReceiverNotAppAddr,
            ),
            (
                a_xfer.get().xfer_asset() == self.asset_a,
                PondErrors.AssetAIncorrect,
            ),
            (
                a_xfer.get().asset_amount() > Int(0),
                PondErrors.AmountLessThanMinimum,
            ),
        ]

        valid_asset_b_xfer = [
            (
                b_xfer.get().asset_receiver() == self.address,
                PondErrors.ReceiverNotAppAddr,
            ),
            (
                b_xfer.get().xfer_asset() == self.asset_b,
                PondErrors.AssetAIncorrect,
            ),
            (
                b_xfer.get().asset_amount() > Int(0),
                PondErrors.AmountLessThanMinimum,
            ),
        ]

        return Seq(
            # Check that the transaction is constructed correctly
            *Helpers.commented_assert(
                well_formed_mint + valid_asset_a_xfer + valid_asset_b_xfer
            ),
            # Check that we have these data to calculate pond token amt out
            (pond_bal := pond_asset.holding(self.address).balance()),
            (a_bal := a_asset.holding(self.address).balance()),
            (b_bal := b_asset.holding(self.address).balance()),
            Assert(
                pond_bal.hasValue(),
                a_bal.hasValue(),
                b_bal.hasValue(),
            ),
            (to_mint := ScratchVar()).store(
                If(
                    And(
                        a_bal.value() == a_xfer.get().asset_amount(),
                        b_bal.value() == b_xfer.get().asset_amount()
                    ),

                    # We calculate minting amt:

                    # If it is the first time we've been called
                    # we use a different formula to mint tokens
                    Mathemagic.tokens_to_mint_initial(
                        self,
                        a_xfer.get().asset_amount(), 
                        b_xfer.get().asset_amount()
                    ),
                    # Normal mint
                    Mathemagic.tokens_to_mint(
                        self,
                        self.total_supply - pond_bal.value(),
                        a_bal.value() - a_xfer.get().asset_amount(),
                        b_bal.value() - b_xfer.get().asset_amount(),
                        a_xfer.get().asset_amount(),
                        b_xfer.get().asset_amount(),
                    ),
                )
            ),
            Assert(
                to_mint.load() > Int(0),
                comment=PondErrors().SendAmountTooLow,
            ),
            # mint tokens
            Transactions.do_axfer(self, Txn.sender(), self.pond_token, to_mint.load()),
            self.ratio.set(Mathemagic.compute_ratio(self)),
        )

    @external
    def burn(
        self,
        pool_xfer: abi.AssetTransferTransaction,
        pool_asset: abi.Asset = pond_token,  # type: ignore[assignment]
        a_asset: abi.Asset = asset_a,  # type: ignore[assignment]
        b_asset: abi.Asset = asset_b,  # type: ignore[assignment]
    ):
        """burn pool tokens to get back some amount of asset A and asset B
        Args:
            pool_xfer: Asset Transfer Transaction of the pool token for the amount the sender wishes to redeem
            pool_asset: Asset ID of the pool token so we may inspect balance.
            a_asset: Asset ID of Asset A so we may inspect balance and distribute it
            b_asset: Asset ID of Asset B so we may inspect balance and distribute it
        """

        well_formed_burn = [
            (
                pool_asset.asset_id() == self.pond_token,
                PondErrors.AssetPondIncorrect,
            ),
            (
                a_asset.asset_id() == self.asset_a,
                PondErrors.AssetAIncorrect,
            ),
            (
                b_asset.asset_id() == self.asset_b,
                PondErrors.AssetBIncorrect,
            ),
        ]

        valid_pool_xfer = [
            (
                pool_xfer.get().asset_receiver() == self.address,
                PondErrors.ReceiverNotAppAddr,
            ),
            (
                pool_xfer.get().asset_amount() > Int(0),
                PondErrors.AmountLessThanMinimum,
            ),
            (
                pool_xfer.get().xfer_asset() == self.pond_token,
                PondErrors.AssetPondIncorrect,
            ),
            (
                pool_xfer.get().sender() == Txn.sender(),
                PondErrors.SenderInvalid,
            ),
        ]

        return Seq(
            *Helpers.commented_assert(well_formed_burn + valid_pool_xfer),
            pool_bal := pool_asset.holding(self.address).balance(),
            a_bal := a_asset.holding(self.address).balance(),
            b_bal := b_asset.holding(self.address).balance(),
            Assert(
                pool_bal.hasValue(),
                a_bal.hasValue(),
                b_bal.hasValue(),
            ),
            # Get the total number of tokens issued (prior to receiving the current axfer of pool tokens)
            (issued := ScratchVar()).store(
                self.total_supply - (pool_bal.value() - pool_xfer.get().asset_amount())
            ),
            (a_amt := ScratchVar()).store(
                Mathemagic.tokens_to_burn(
                    self,
                    issued.load(),
                    a_bal.value(),
                    pool_xfer.get().asset_amount(),
                )
            ),
            (b_amt := ScratchVar()).store(
                Mathemagic.tokens_to_burn(
                    self,
                    issued.load(),
                    b_bal.value(),
                    pool_xfer.get().asset_amount(),
                )
            ),
            # Send back commensurate amt of a
            Transactions.do_axfer(
                self,
                Txn.sender(),
                self.asset_a,
                a_amt.load(),
            ),
            # Send back commensurate amt of b
            Transactions.do_axfer(
                self,
                Txn.sender(),
                self.asset_b,
                b_amt.load(),
            ),
            self.ratio.set(Mathemagic.compute_ratio(self)),
        )

    @external
    def swap(
        self,
        swap_xfer: abi.AssetTransferTransaction,
        a_asset: abi.Asset = asset_a,  # type: ignore[assignment]
        b_asset: abi.Asset = asset_b,  # type: ignore[assignment]
    ):
        """Swap some amount of either asset A or asset B for the other
        Args:
            swap_xfer: Asset Transfer Transaction of either Asset A or Asset B
            a_asset: Asset ID of asset A so we may inspect balance and possibly transfer it
            b_asset: Asset ID of asset B so we may inspect balance and possibly transfer it
        """
        well_formed_swap = [
            (
                a_asset.asset_id() == self.asset_a,
                PondErrors.AssetAIncorrect,
            ),
            (
                b_asset.asset_id() == self.asset_b,
                PondErrors.AssetBIncorrect,
            ),
        ]

        valid_swap_xfer = [
            (
                Or(
                    swap_xfer.get().xfer_asset() == self.asset_a,
                    swap_xfer.get().xfer_asset() == self.asset_b,
                ),
                PondErrors.AssetIdsIncorrect,
            ),
            (
                swap_xfer.get().asset_amount() > Int(0),
                PondErrors.AmountLessThanMinimum,
            ),
            (
                swap_xfer.get().sender() == Txn.sender(),
                PondErrors.SenderInvalid,
            ),
        ]

        out_id = If(
            swap_xfer.get().xfer_asset() == self.asset_a,
            self.asset_b,
            self.asset_a,
        )
        in_id = swap_xfer.get().xfer_asset()

        return Seq(
            *Helpers.commented_assert(well_formed_swap + valid_swap_xfer),
            in_sup := AssetHolding.balance(self.address, in_id),
            out_sup := AssetHolding.balance(self.address, out_id),
            Assert(
                in_sup.hasValue(),
                out_sup.hasValue(),
            ),
            (to_swap := ScratchVar()).store(
                Mathemagic.tokens_to_swap(
                    self,
                    swap_xfer.get().asset_amount(),
                    in_sup.value() - swap_xfer.get().asset_amount(),
                    out_sup.value(),
                )
            ),
            Assert(
                to_swap.load() > Int(0),
                comment=PondErrors.SendAmountTooLow,
            ),
            Transactions.do_axfer(
                self,
                Txn.sender(),
                out_id,
                to_swap.load(),
            ),
            self.ratio.set(Mathemagic.compute_ratio(self)),
        )

    # @external
    # def swap(
    #     self,
    #     asset_in: abi.Uint64, 
    #     asset_out: abi.Uint64, 
    #     amt_in: abi.Uint64, 
    #     expected_amt_out: abi.Uint64,
    #     max_slippage: abi.Uint64
    #     ):
    #     return Seq(
    #         # Calculates amt_out
    #         (amt_out := ScratchVar()).store(
    #             self.calculate_lp_token_out_amt(amt_in)
    #         ),
    #         # Calculates actual slippage
    #         (slippage := ScratchVar()).store(
    #             self.calculate_slippage(expected_amt_out, amt_out)
    #         ),
    #         # Determines if slippage is below <= max_slippage
    #         Assert(slippage.load() <= max_slippage.get())
    #         # Transfer assets out (optin LP token)
    #     )

