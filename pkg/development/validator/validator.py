from pyteal import *
from beaker import *

class Validator(Application):

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
    lp_has_opted_in = optin_checker(Gtxn[2].asset_sender(), Gtxn[1].application_args[1])
    pond_has_opted_in = optin_checker(Gtxn[2].asset_receiver(), Gtxn[2].xfer_asset())
    return Seq(
      Assert(Txn.application_args[0] == Bytes("commit")),
      Assert(Global.group_size() == Int(3)),
      Assert(Txn.application_args.length() == Int(3)),
      Assert(Txn.type_enum() == TxnType.ApplicationCall),
      Assert(fee_verification(lp_txns_amount.get())), ## TODO: Refactor, verifies LP is paying for fees for all txns
      Assert(Txn.on_completion() == OnComplete.NoOp),
      Assert(Gtxn[1].sender() == Txn.sender()),
      Assert(Gtxn[1].accounts[0] != Txn.sender()),
      # call optin helper dinamically
      Assert(optin_asset(lp_has_opted_in, pond_has_opted_in, Gtxn[1].application_args[1], Gtxn[2].xfer_asset())),
      
      Assert(Gtxn[3].sender() != Txn.sender()), # pooler to pool
      Assert(Gtxn[3].asset_receiver() == Txn.sender()), # rcvr is pool
      # Assert(safety_conds()),
      commit_distributor(COMMIT_DISTRIBUTOR_APP_ID),
      Approve(),
    )

    @internal(TealType.uint64)
    def fee_verification(self, txns_amount: abi.Uint64): # TODO: rename
      pass

    @internal(TealType.uint64)
    def optin_checker(self, address: abi.Address, asset_id: abi.Uint64):
      asset_balance = AssetHolding.balance(address, asset_id)
      return asset_balance.hasValue()

    @internal
    def call_optin_helper(self, address_1: abi.Address, address_2: abi.Address, asset_id_1: abi.Uint64, asset_id_2: abi.Uint64): # call_optin_helper/5
      return Seq(
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.ApplicationCall,
                TxnField.application_id: app_id, # TODO: Get from Registry
                TxnField.on_completion: OnComplete.NoOp,
                TxnField.accounts: [address_1, address_2],
                TxnField.assets: [asset_id_1, asset_id_2]
            }),
            InnerTxnBuilder.Submit()
        )
      
    @internal
    def call_optin_helper(self, address, asset_id): # call_optin_helper/3
      pass

    @internal(TealType.none)
    def optin_asset(self, address_1: abi.Address, address_2: abi.Address, asset_id_1: abi.Uint64, asset_id_2: abi.Uint64):
      return Cond(
        [And(lp_has_opted_in != 0, pond_has_opted_in != 0), call_optin_helper(address_1, address_2, asset_id_1, asset_id_2)],
        [And(lp_has_opted_in == 0, pond_has_opted_in == 0), None],
        [And(lp_has_opted_in != 0, pond_has_opted_in == 0), call_optin_helper(address_2, asset_id_2)],
        [And(lp_has_opted_in == 0, pond_has_opted_in != 0), call_optin_helper(address_1, asset_id_1)]
      )
      # lp_has_opted_in == 1 && pond_has_opted_in == 1:
      # lp_has_opted_in == 0 && pond_has_opted_in == 0:
      # return optin_helper(lp_add, pond_add, asset_1, asset_2)
      # lp_has_opted_in == 1 && pond_has_opted_in == 0:
      # return optin_helper(pond_add, asset_1)
      # lp_has_opted_in == 0 && pond_has_opted_in == 1:
      # return optin_helper(lp_add, asset_1)

      pass

def demo():
  print("Hello beaker")
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

  result = app_client.call(Validator.bootstrap_pond, rg=12)
  print(f"Result: {result.return_value}")


if __name__ == "__main__":
  demo()