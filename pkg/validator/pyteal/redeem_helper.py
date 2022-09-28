from ast import Assert
from pyteal import *
from pyteal_helpers import program
from pyteal.ast.bytes import Bytes

def approval():

  asset_1 = Txn.application_args[1]
  asset_2 = Txn.application_args[2]
  asset_3 = Txn.application_args[3]
  amount_1 = Txn.application_args[4]
  amount_2 = Txn.application_args[5]
  amount_3 = Txn.application_args[6]
  pooler = Txn.accounts[1],

  FEE = Int(1000)

  @Subroutine(TealType.none)
  def distribute_assets(pooler, amount_1, amount_2, amount_3, asset_1, asset_2, asset_3: Expr):
    return Seq(
      InnerTxnBuilder.Begin(),
      InnerTxnBuilder.SetFields({
          TxnField.type_enum: TxnType.AssetTransfer,
          TxnField.asset_receiver: pooler,
          TxnField.asset_amount: amount_1,
          TxnField.xfer_asset: asset_1,
              # TxnField.fee: FEE, # TODO: verify if it should be here
      }),
      InnerTxnBuilder.Next(),
      InnerTxnBuilder.SetFields({
          TxnField.type_enum: TxnType.AssetTransfer,
          TxnField.asset_receiver: pooler,
          TxnField.asset_amount: amount_2,
          TxnField.xfer_asset: asset_2,
              # TxnField.fee: FEE, # TODO: verify if it should be here
      }),
      InnerTxnBuilder.Next(),
      InnerTxnBuilder.SetFields(
          {
              TxnField.type_enum: TxnType.AssetTransfer,
              TxnField.asset_receiver: pooler,
              TxnField.asset_amount: amount_3,
              TxnField.xfer_asset: asset_3,
              # TxnField.fee: FEE, # TODO: verify if it should be here
          }
      ),
      InnerTxnBuilder.Submit(),
    )
  
  distribute = Seq(
    Assert(Txn.application_args[0] == Bytes("redeem")),
    Assert(Txn.application_args.length() == Int(7)),
    distribute_assets(Txn.accounts[1], Txn.application_args[4], Txn.application_args[5], Txn.application_args[6], Txn.application_args[1], Txn.application_args[2], Txn.application_args[3]),
    Approve(),
  )

  return program.event(
    init=Approve(),
    opt_in=Approve(),
    no_op=distribute,
  )
def clear():
  return Approve()

