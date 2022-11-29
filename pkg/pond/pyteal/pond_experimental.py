from pyteal import *
from beaker import *

def commented_assert(conditions: list[tuple[Expr, str]]) -> list[Expr]:
    return [Assert(cond, comment=cmt) for cond, cmt in conditions]

class PondErrors:
    GroupSizeNot2 = "group size not 2"
    ReceiverNotAppAddr = "receiver not app address"
    AmountLessThanMinimum = "amount minimum not met"
    AssetIdsIncorrect = "asset a or asset b or asset c incorrect"
    AssetInIncorrect = "incoming asset incorrect"
    AssetPondIncorrect = "pond asset incorrect"
    SenderInvalid = "invalid sender"
    # MissingBalances = "missing required balances"
    # SendAmountTooLow = "outgoing amount too low"

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
    asset_c: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        key=Bytes("c"),
        static=True,
        descr="The asset id of asset B",
    )
    pond_token: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        key=Bytes("p"),
        static=True,
        descr="The asset id of the Pond Token, used to track share of pond the holder may recover",
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
        c_asset: abi.Asset,
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
            a_asset: One of the three assets this pond should allow swapping 
            between.
            b_asset: One of the three assets this pond should allow swapping 
            between.
            c_asset: One of the three assets this pond should allow swapping 
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
                And(
                    a_asset.asset_id() != b_asset.asset_id(),
                    a_asset.asset_id() != c_asset.asset_id(),
                    b_asset.asset_id() != c_asset.asset_id(),
                ),
                PondErrors.AssetIdsIncorrect,
            ),
        ]

        return Seq(
            *commented_assert(well_formed_bootstrap),
            self.asset_a.set(a_asset.asset_id()),
            self.asset_b.set(b_asset.asset_id()),
            self.asset_c.set(c_asset.asset_id()),
            self.pond_token.set(
                self.do_create_pond_token(
                    self.asset_a,
                    self.asset_b,
                    self.asset_c
                ),
            ),
            self.do_opt_in(self.asset_a),
            self.do_opt_in(self.asset_b),
            self.do_opt_in(self.asset_c),
            output.set(self.pond_token),
        )
    
    @external
    def mint(
        self,
        in_xfer: abi.AssetTransferTransaction,
        in_asset: abi.Asset,  # type: ignore[assignment]
        pond_asset: abi.Asset = pond_token,  # type: ignore[assignment]
        ):
        """mint pond tokens given some amount of in_asset on commit.

        Given some amount of stable asset in the transfer, mint some number of 
        pool tokens calculated with the pond's current balance and 
        circulating supply of pond tokens.

        Args:
            in_xfer: Asset Transfer Transaction of in_asset as a deposit to the 
            pond in exchange for pond tokens.
            in_asset: The asset ID of the incoming asset so that we may inspect 
            our balance.
            pond_asset: The asset ID of the pond token so that we may 
            distribute it.
        """

        well_formed_mint = [
            (
                Or(
                    in_asset.asset_id() == self.asset_a,
                    in_asset.asset_id() == self.asset_b,
                    in_asset.asset_id() == self.asset_c
                ),
                PondErrors.AssetInIncorrect,
            ),
            (
                pond_asset.asset_id() == self.pond_token,
                PondErrors.AssetPondIncorrect,
            ),
            (
                in_xfer.get().sender() == Txn.sender(),
                PondErrors.SenderInvalid,
            ),
        ]
        return Seq(
            # transfers asset_in from lp to pond

        )

    # @external
    # def redeem():
    #     pass

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

    @internal(TealType.none)
    def do_axfer(self, rx, aid, amt):
        return InnerTxnBuilder.Execute(
            {
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: aid,
                TxnField.asset_amount: amt,
                TxnField.asset_receiver: rx,
                TxnField.fee: Int(0),
            }
        )

    @internal(TealType.none)
    def do_opt_in(self, aid):
        return self.do_axfer(self.address, aid, Int(0))

    @internal(TealType.uint64)
    def do_create_pool_token(self, a, b):
        return Seq(
            Assert(
                AssetParam.unitName(a).hasValue(), 
                AssetParam.unitName(b).hasValue(),
                AssetParam.unitName(c).hasValue()
            ),
            InnerTxnBuilder.Execute(
                {
                    TxnField.type_enum: TxnType.AssetConfig,
                    TxnField.config_asset_name: Concat(
                        Bytes("KOIFI-POND-"), 
                        AssetParam.unitName(a).value(), 
                        Bytes("-"), 
                        AssetParam.unitName(b).value(), 
                        Bytes("-"), 
                        AssetParam.unitName(c).value()
                    ),
                    TxnField.config_asset_unit_name: Bytes("POND"),
                    TxnField.config_asset_total: self.total_supply,
                    TxnField.config_asset_decimals: Int(3),
                    TxnField.config_asset_manager: self.address,
                    TxnField.config_asset_reserve: self.address,
                    TxnField.fee: Int(0),
                }
            ),
            InnerTxn.created_asset_id(),
        )
    

    @internal(TealType.uint64)
    def calculate_lp_token_out_amt(self, amt_in: abi.Uint64):
        """
        internal method to calculate LP token out amount given an 
        in token amount
        """
        amt_out = amt_in.get() * Int(2) # placeholder calculation
        return amt_out

    @internal(TealType.uint64)
    def calculate_slippage(
        self, 
        expected_amt_out: abi.Uint64, 
        amt_out: ScratchVar):
        return Int(1)
    
def demo():
    # Here we use `sandbox` but beaker.client.api_providers can also be used
    # with something like ``AlgoNode(Network.TestNet).algod()``
    algod_client = sandbox.get_algod_client()

    acct = sandbox.get_accounts().pop()

    # Create an Application client containing both an algod client and app
    app_client = client.ApplicationClient(
        client=algod_client, app=Pond(version=6), signer=acct.signer
    )

    # Create the application on chain, set the app id for the app client
    app_id, app_addr, txid = app_client.create()
    print(f"Created App with id: {app_id} and address addr: {app_addr} in tx: {txid}")

    result = app_client.call(
        Pond.commit, 
        asset_in=1, 
        asset_out=2, 
        amt_in= 4, 
        expected_amt_out= 6, 
        max_slippage= 1
    )
    print(f"Result: {result.return_value}")

if __name__ == "__main__":
    demo()