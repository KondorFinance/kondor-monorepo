from typing import Final
from pyteal import *
from beaker import *

from utils.transactions import Transactions
from utils.errors import InvestmentProductErrors
from utils.helpers import Helpers

class InvestmentProduct(Application):

    # Declare Application state, marking `Final` here so the python class var 
    # doesn't get changed
    # Marking a var `Final` does _not_ change anything at the AVM level
    governor: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.bytes,
        key=Bytes("g"),
        default=Global.creator_address(),
        descr="The current governor of this contract, allowed to do admin type actions",
    )

    # Call this only on create
    @create
    def create(self):
        return self.initialize_application_state()


    # This method is used to create a NFT
    # Only the account set in app_state.governor may call this method
    @external(authorize=Authorize.only(governor))
    def create_nft(self, seed: abi.PaymentTransaction, *, output: abi.Uint64):

        well_formed_fund = [
            (
                seed.get().receiver() == self.address,
                InvestmentProductErrors.ReceiverNotAppAddr,
            ),
            (
                seed.get().amount() >= consts.Algos(0.1),
                InvestmentProductErrors.AmountLessThanMinimum,
            )]

        return Seq(
            *Helpers.commented_assert(Txn, well_formed_fund),
            output.set(Transactions.do_create_nft(self))
        )

    # Only the account set in app_state.governor may call this method
    # This method is used to send a NFT to caller's account
    @external(authorize=Authorize.only(governor))
    def mint_nft(
        self, 
        seed: abi.PaymentTransaction, 
        asset: abi.Asset
        ):
        well_formed_mint_nft = [
            (
                seed.get().receiver() == self.address,
                InvestmentProductErrors.ReceiverNotAppAddr,
            ),
            (
                seed.get().amount() >= consts.Algos(0.1),
                InvestmentProductErrors.AmountLessThanMinimum,
            )]

        return Seq(
            *Helpers.commented_assert(Txn, well_formed_mint_nft),
            Transactions.do_axfer(self, seed.get().sender(), asset.asset_id(), Int(1))
        )

