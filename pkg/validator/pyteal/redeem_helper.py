from ast import Assert
from pyteal import *
from pyteal_helpers import program
from pyteal.ast.bytes import Bytes

def approval():

  FEE = Int(1000)

  @Subroutine(TealType.none)
  def distribute_assets():
    return Seq(
      InnerTxnBuilder.Begin(),
      InnerTxnBuilder.SetFields({
          TxnField.type_enum: TxnType.AssetTransfer,
          TxnField.asset_receiver: Txn.accounts[1],
          TxnField.asset_amount: Btoi(Txn.application_args[4]),
          TxnField.xfer_asset: Btoi(Txn.application_args[1]),
              # TxnField.fee: FEE, # TODO: verify if it should be here
      }),
      InnerTxnBuilder.Next(),
      InnerTxnBuilder.SetFields({
          TxnField.type_enum: TxnType.AssetTransfer,
          TxnField.asset_receiver: Txn.accounts[1],
          TxnField.asset_amount: Btoi(Txn.application_args[5]),
          TxnField.xfer_asset: Btoi(Txn.application_args[2]),
              # TxnField.fee: FEE, # TODO: verify if it should be here
      }),
      InnerTxnBuilder.Next(),
      InnerTxnBuilder.SetFields({
          TxnField.type_enum: TxnType.AssetTransfer,
          TxnField.asset_receiver: Txn.accounts[1],
          TxnField.asset_amount: Btoi(Txn.application_args[6]),
          TxnField.xfer_asset: Btoi(Txn.application_args[3]),
          # TxnField.fee: FEE, # TODO: verify if it should be here
      }),
      InnerTxnBuilder.Submit(),
    )
  
  distribute = Seq(
    # Assert(Txn.application_args[0] == Bytes("redeem")),
    Assert(Txn.application_args.length() == Int(7)),
    distribute_assets(),
    Approve(),
  )

  return program.event(
    init=Approve(),
    no_op=distribute,
  )
def clear():
  return Approve()

