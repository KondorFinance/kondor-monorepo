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


    # Fund the contract with some algos
    @external(authorize=Authorize.only(governor))
    def fund(self, ptxn: abi.PaymentTransaction):

        well_formed_fund = [
            (
                ptxn.get().receiver() == self.address,
                InvestmentProductErrors.ReceiverNotAppAddr,
            ),
            (
                ptxn.get().amount() >= consts.Algos(0.3),
                InvestmentProductErrors.AmountLessThanMinimum,
            )]

        return Seq(
            *Helpers.commented_assert(Txn, well_formed_fund)
        )

    # Only the account set in app_state.governor may call this method
    # This method is used to create a new NFT and send it to account
    @external(authorize=Authorize.only(governor))
    def createNft(self,*, output: abi.Uint64):
        return output.set(Transactions.do_create_nft(self))


