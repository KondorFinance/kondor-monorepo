from pyteal import *
from beaker import *
# TODO: Add precompile for testing 

class AssetOptinHelperSub(Application):

    @external
    def optin_checker(self, address: abi.Address, asset_id: abi.Uint64):
        # print(If(AssetHolding.balance(address.get(), asset_id.get()).hasValue() == Int(0), self.opt_in_to_asset(address, asset_id)))
        asset_balance = ScratchVar(TealType.uint64)
        print(asset_balance.load().type_of())
        return Seq(
            asset_balance.store(AssetHolding.balance(address.get(), asset_id.get()).hasValue()),
            If(asset_balance.load() == Int(0), Assert(Int(1)))
            )
  
    @internal(TealType.none)
    def opt_in_to_asset(self, address: abi.Address, asset: abi.Uint64):
        # return InnerTxnBuilder.Execute(
        #     {
        #         TxnField.type_enum: TxnType.AssetTransfer,
        #         TxnField.xfer_asset: asset.asset_id(),
        #         TxnField.asset_receiver: self.address,
        #         TxnField.fee: Int(0),
        #         TxnField.asset_amount: Int(0),
        #     }
        #  )
        return Assert(Int(1))

class Validator(Application):
    # Specify precompiles of approval/clear program so we have the binary before we deploy
    asset_optin_helper_sub_app: precompile.AppPrecompile = precompile.AppPrecompile(AssetOptinHelperSub())

    @external
    def create_sub(self, *, output: abi.Uint64):
        return Seq(
            InnerTxnBuilder.Execute(
            {
                Txn.type_enum: TxnType.ApplicationCall,
                TxnField.approval_program: self.asset_optin_helper_sub_app.approval.binary,
                TxnField.clear_state_program: self.asset_optin_helper_sub_app.clear.binary,
            }
            ),
            output.set(InnerTxn.created_application_id()),
        )

    # How to know when to trigger the bootstrap?
    @external
    def bootstrap_pond(self, rg: abi.Uint64, *, output: abi.Uint64):
        """Receives a registry ID and validates it's type"""
        return output.set(rg.get())

    # Txng args: 
    # ['str:commit', 'int:out_id*', 'int:out_amt']

    # Txn group
    # gtxn[0]: fees_dist app call *
    # gtxn[1]: Validator app call, sndr: LP, accs[]: pond
    # gtxn[2]: in_asset transfer from LP to Pond

    @external
    def commit_pond(self, lp_txns_amount: abi.Uint64):
        # lp_has_opted_in = optin_checker(Bytes(Gtxn[2].asset_sender()), Int(Gtxn[1].application_args[1]))
        # pond_has_opted_in = optin_checker(Bytes(Gtxn[2].asset_receiver()), Int(Gtxn[2].xfer_asset()))
        lp_has_opted_in = self.optin_checker(Bytes("abcdefghi"), Int(1))
        pond_has_opted_in = self.optin_checker(Bytes("jklmnñopq"), Int(2))
        print(lp_has_opted_in)
        return Seq(
            # Assert(Txn.application_args[0] == Bytes("commit")), # FAILING
            # Assert(Global.group_size() == Int(3)), # FAILING
            # Assert(Txn.application_args.length() == Int(3)), # FAILING
            # Assert(Txn.type_enum() == TxnType.ApplicationCall), # FAILING
            # Assert(fee_verification(lp_txns_amount.get())), ## TODO: Refactor, verifies LP is paying for fees for all txns
            # Assert(Txn.on_completion() == OnComplete.NoOp), # FAILING
            # Assert(Gtxn[1].sender() == Txn.sender()), # FAILING
            # Assert(Gtxn[1].accounts[0] != Txn.sender()), # FAILING
            # call optin helper dinamically
            # Assert(optin_asset(lp_has_opted_in, pond_has_opted_in, Gtxn[1].application_args[1], Gtxn[2].xfer_asset())),
            # self.optin_asset(lp_has_opted_in, pond_has_opted_in, Int(1), Int(2)),
            
            # Assert(Gtxn[3].sender() != Txn.sender()), # pooler to pool
            # Assert(Gtxn[3].asset_receiver() == Txn.sender()), # rcvr is pool
            # Assert(safety_conds()),
            # commit_distributor(COMMIT_DISTRIBUTOR_APP_ID),
            Approve(),
        )

    @internal(TealType.uint64)
    def fee_verification(self, txns_amount: abi.Uint64): # TODO: rename
        pass

    # @internal
    # def call_optin_helper(self, address_1: abi.Address, address_2: abi.Address, asset_id_1: abi.Uint64, asset_id_2: abi.Uint64): # call_optin_helper/5
    #   return Seq(
    #         InnerTxnBuilder.Begin(),
    #         InnerTxnBuilder.SetFields({
    #             TxnField.type_enum: TxnType.ApplicationCall,
    #             TxnField.application_id: app_id, # TODO: Get from Registry
    #             TxnField.on_completion: OnComplete.NoOp,
    #             TxnField.accounts: [address_1, address_2],
    #             TxnField.assets: [asset_id_1, asset_id_2]
    #         }),
    #         InnerTxnBuilder.Submit()
    #     )



    @internal(TealType.none)
    def optin_asset(self, address_1: abi.Address, address_2: abi.Address, asset_id_1: abi.Uint64, asset_id_2: abi.Uint64):
        lp_has_opted_in(self, ScratchVar(TealType.uint64))
        # return Cond(
        #   [And(lp_has_opted_in != 0, pond_has_opted_in != 0), call_optin_helper(address_1, address_2, asset_id_1, asset_id_2)],
        #   [And(lp_has_opted_in == 0, pond_has_opted_in == 0), None],
        #   [And(lp_has_opted_in != 0, pond_has_opted_in == 0), call_optin_helper(address_2, asset_id_2)],
        #   [And(lp_has_opted_in == 0, pond_has_opted_in != 0), call_optin_helper(address_1, asset_id_1)]
        # )
        print('halo')
        return none()

def demo():
    # Here we use `sandbox` but beaker.client.api_providers can also be used
    # with something like ``AlgoNode(Network.TestNet).algod()``
    algod_client = sandbox.get_algod_client()

    acct = sandbox.get_accounts().pop()

    # Create an Application client containing both an algod client and app
    app_client = client.ApplicationClient(
        client=algod_client, app=Validator(version=6), signer=acct.signer
    )

    # Create the application on chain, set the app id for the app client
    app_id, app_addr, txid = app_client.create()
    print(f"Created App with id: {app_id} and address addr: {app_addr} in tx: {txid}")

    # Call the main app to create the sub app
    result = app_client.call(Validator.create_sub)
    sub_app_id = result.return_value
    print(f"Created sub app: {sub_app_id}")

    # result = app_client.call(Validator.bootstrap_pond, rg=12)
    # print(f"Result: {result.return_value}")

    # result = app_client.call(Validator.commit_pond, lp_txns_amount=2)
    # print(f"Result: {optin_checker(app_id)}")


if __name__ == "__main__":
    demo()
