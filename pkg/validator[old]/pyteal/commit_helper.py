from ast import Assert
from pyteal import *
from pyteal_helpers import program
from pyteal.ast.bytes import Bytes

def approval():

  FEE = Int(1000)

  # Txng args: ['str:commit', 'int:asset_id', 'int:lp_asset_id', 'int:asset_amt', 'int:lp_asset_amt']

  # TODO: Verify sender and asset receiver from txn.accounts's array

  @Subroutine(TealType.none)
  def commit_assets():
    return Seq(
      InnerTxnBuilder.Begin(),
      InnerTxnBuilder.SetFields({
          TxnField.type_enum: TxnType.AssetTransfer,
          TxnField.sender: Txn.accounts[2], # pooler
          TxnField.asset_receiver: Txn.accounts[1], # pool
          TxnField.asset_amount: Btoi(Txn.application_args[3]),
          TxnField.xfer_asset: Btoi(Txn.application_args[1]),
          # TxnField.fee: FEE, # TODO: verify if this should be here
      }),
      InnerTxnBuilder.Next(),
      # transfers the LP asset to the pooler
      InnerTxnBuilder.SetFields({
          TxnField.type_enum: TxnType.AssetTransfer,
          TxnField.sender: Txn.accounts[1], # pool
          TxnField.asset_receiver: Txn.accounts[2],  # pooler
          TxnField.asset_amount: Btoi(Txn.application_args[4]),
          TxnField.xfer_asset: Btoi(Txn.application_args[2]),
          # TxnField.fee: FEE, # TODO: verify if this should be here
      }),
      InnerTxnBuilder.Submit(),
    )
  
  distribute = Seq(
    Assert(Txn.application_args[0] == Bytes("commit")),
    Assert(Txn.application_args.length() == Int(5)),
    commit_assets(),
    Approve(),
  )

  return program.event(
    init=Approve(),
    no_op=distribute,
  )
def clear():
  return Approve()

