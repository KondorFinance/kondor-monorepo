from algosdk.future import transaction
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from typing import Final
from pyteal import *
from beaker import *

def commented_assert(conditions: list[tuple[Expr, str]]) -> list[Expr]:
    return [Assert(cond, comment=cmt) for cond, cmt in conditions]

class PondErrors:
    GroupSizeNot2 = "group size not 2"
    ReceiverNotAppAddr = "receiver not app address"
    AmountLessThanMinimum = "amount minimum not met"
    AssetIdsIncorrect = "Incorrect asset"
    AssetAIncorrect = "Asset A incorrect"
    AssetBIncorrect = "Asset B incorrect"
    AssetCIncorrect = "Asset C incorrect"
    AssetPondIncorrect = "pond asset incorrect"
    SenderInvalid = "invalid sender"
    # MissingBalances = "missing required balances"
    SendAmountTooLow = "outgoing amount too low"

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
            *commented_assert(well_formed_bootstrap),
            self.asset_a.set(a_asset.asset_id()),
            self.asset_b.set(b_asset.asset_id()),
            self.pond_token.set(
                self.do_create_pond_token(
                    self.asset_a,
                    self.asset_b
                ),
            ),
            self.do_opt_in(self.asset_a),
            self.do_opt_in(self.asset_b),
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
            *commented_assert(
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
                    self.tokens_to_mint_initial(
                        a_xfer.get().asset_amount(), 
                        b_xfer.get().asset_amount()
                    ),
                    # Normal mint
                    self.tokens_to_mint(
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
            self.do_axfer(Txn.sender(), self.pond_token, to_mint.load()),
            self.ratio.set(self.compute_ratio()),
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
            *commented_assert(well_formed_burn + valid_pool_xfer),
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
                self.tokens_to_burn(
                    issued.load(),
                    a_bal.value(),
                    pool_xfer.get().asset_amount(),
                )
            ),
            (b_amt := ScratchVar()).store(
                self.tokens_to_burn(
                    issued.load(),
                    b_bal.value(),
                    pool_xfer.get().asset_amount(),
                )
            ),
            # Send back commensurate amt of a
            self.do_axfer(
                Txn.sender(),
                self.asset_a,
                a_amt.load(),
            ),
            # Send back commensurate amt of b
            self.do_axfer(
                Txn.sender(),
                self.asset_b,
                b_amt.load(),
            ),
            self.ratio.set(self.compute_ratio()),
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
            *commented_assert(well_formed_swap + valid_swap_xfer),
            in_sup := AssetHolding.balance(self.address, in_id),
            out_sup := AssetHolding.balance(self.address, out_id),
            Assert(
                in_sup.hasValue(),
                out_sup.hasValue(),
            ),
            (to_swap := ScratchVar()).store(
                self.tokens_to_swap(
                    swap_xfer.get().asset_amount(),
                    in_sup.value() - swap_xfer.get().asset_amount(),
                    out_sup.value(),
                )
            ),
            Assert(
                to_swap.load() > Int(0),
                comment=PondErrors.SendAmountTooLow,
            ),
            self.do_axfer(
                Txn.sender(),
                out_id,
                to_swap.load(),
            ),
            self.ratio.set(self.compute_ratio()),
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

    ##########################
    ## Mathemagical methods ##
    ##########################

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

    ############################################
    ## Utility methods for inner transactions ##
    ############################################

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
    def do_create_pond_token(self, a, b):
        return Seq(
            (una := AssetParam.unitName(a)),
            (unb := AssetParam.unitName(b)),
            Assert(
                una.hasValue(), 
                unb.hasValue()
            ),
            InnerTxnBuilder.Execute(
                {
                    TxnField.type_enum: TxnType.AssetConfig,
                    TxnField.config_asset_name: Concat(
                        Bytes("KOIFI-V1-POND-"), 
                        una.value(), 
                        Bytes("-"), 
                        unb.value()
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
    addr, sk, signer = acct.address, acct.private_key, acct.signer

    # Create an Application client containing both an algod client and app
    app_client = client.ApplicationClient(
        client=algod_client, app=Pond(version=6), signer=acct.signer
    )

    # Create the application on chain, set the app id for the app client
    app_id, app_addr, txid = app_client.create()
    print(f"Created App with id: {app_id} and address addr: {app_addr} in tx: {txid}")

    # Fund App address so it can create the pool token and hold balances

    # Create assets
    asset_a = create_asset(algod_client, addr, sk, "A")
    asset_b = create_asset(algod_client, addr, sk, "B")
    print(f"Created asset a/b with ids: {asset_a}/{asset_b}")

    # Call app to create pond token
    print("Calling bootstrap")
    sp = algod_client.suggested_params()
    ptxn = TransactionWithSigner(
        txn=transaction.PaymentTxn(addr, sp, app_addr, int(1e7)), signer=signer
    )
    sp.flat_fee = True
    sp.fee = consts.milli_algo * 5
    result = app_client.call(
        Pond.bootstrap,
        seed=ptxn,
        a_asset=asset_a,
        b_asset=asset_b,
        suggested_params=sp,
    )
    pond_token = result.return_value
    print(f"Created pond token with id: {pond_token}")
    print_balances(
        algod_client,
        app_client,
        app_id, 
        app_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b
    )

    # Opt user into token
    sp = algod_client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_transaction(
        TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, addr, 0, pond_token),
            signer=signer,
        )
    )
    atc.execute(algod_client, 2)
    print_balances(
        algod_client,
        app_client,
        app_id, 
        app_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b
    )

    # Cover any fees incurred by inner transactions, maybe overpaying but 
    # thats ok
    # TODO: Review to avoid overpaying
    sp = algod_client.suggested_params()
    sp.flat_fee = True
    sp.fee = consts.milli_algo * 3

    ###
    # Fund Pool with initial liquidity commiting the 3 assets
    ###
    print("Funding")
    result = app_client.call(
        Pond.mint,
        a_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, app_addr, 3000, asset_a),
            signer=signer,
        ),
        b_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, app_addr, 3000, asset_b),
            signer=signer,
        ),
        suggested_params=sp,
    )
    print_balances(
        algod_client,
        app_client,
        app_id, 
        app_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b
    )

    ###
    # Mint pool tokens
    ###
    print("Minting")
    app_client.call(
        Pond.mint,
        a_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, app_addr, 1000, asset_a),
            signer=signer,
        ),
        b_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, app_addr, 1000, asset_b),
            signer=signer,
        ),
        suggested_params=sp,
    )
    print_balances(
        algod_client,
        app_client,
        app_id, 
        app_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b
    )

    ###
    # Swap A for B
    ###
    print("Swapping A for B")
    app_client.call(
        Pond.swap,
        swap_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, app_addr, 1000, asset_a),
            signer=signer,
        ),
    )
    print_balances(
        algod_client,
        app_client,
        app_id, 
        app_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b
    )

    ###
    # Swap B for A
    ###
    print("Swapping B for A")
    app_client.call(
        Pond.swap,
        swap_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, app_addr, 1000, asset_b),
            signer=signer,
        ),
    )
    print_balances(
        algod_client,
        app_client,
        app_id, 
        app_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b
    )

    ###
    # Burn pool tokens
    ###
    print("Burning")
    app_client.call(
        Pond.burn,
        pool_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, app_addr, 700, pond_token),
            signer=signer,
        ),
    )
    print_balances(
        algod_client,
        app_client,
        app_id, 
        app_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b
    )

    # # result = app_client.call(Pond.bootstrap, rg=12)
    # print(f"Result: {result.return_value}")

def create_asset(client, addr, pk, unitname):
    # Get suggested params from network
    sp = client.suggested_params()
    # Create the transaction
    create_txn = transaction.AssetCreateTxn(
        addr, sp, 1000000, 0, False, asset_name="asset", unit_name=unitname
    )
    # Ship it
    txid = client.send_transaction(create_txn.sign(pk))
    # Wait for the result so we can return the app id
    result = transaction.wait_for_confirmation(client, txid, 4)
    return result["asset-index"]

def print_balances(
    client,
    app_client,
    app_id: int, 
    app: str, 
    addr: str, 
    pond: int, 
    a: int, 
    b: int
):

    addrbal = client.account_info(addr)
    print("Participant: ")
    for asset in addrbal["assets"]:
        if asset["asset-id"] == pond:
            print("\tPond Balance {}".format(asset["amount"]))
        if asset["asset-id"] == a:
            print("\tAssetA Balance {}".format(asset["amount"]))
        if asset["asset-id"] == b:
            print("\tAssetB Balance {}".format(asset["amount"]))

    appbal = client.account_info(app)
    print("App: ")
    for asset in appbal["assets"]:
        if asset["asset-id"] == pond:
            print("\tPond Balance {}".format(asset["amount"]))
        if asset["asset-id"] == a:
            print("\tAssetA Balance {}".format(asset["amount"]))
        if asset["asset-id"] == b:
            print("\tAssetB Balance {}".format(asset["amount"]))

    state = app_client.get_application_state()
    state_key = Pond.ratio.str_key()
    if state_key in state:
        print(
            f"\tCurrent ratio a/b == {int(state[state_key]) / Pond._scale}"
        )
    else:
        print("\tNo ratio a/b")
    
if __name__ == "__main__":
    Pond().dump("artifacts")
    demo()