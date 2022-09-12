from ast import Assert
from operator import concat
from pyteal import *
from pyteal_helpers import program
from pyteal.ast.bytes import Bytes

def approval():
  asset_1 = Txn.application_args[1]
  asset_2 = Txn.application_args[2]
  asset_3 = Txn.application_args[3]

#   symbol_1 = AssetParam.unitName(asset_1)
#   symbol_2 = AssetParam.unitName(asset_2)
#   symbol_3 = AssetParam.unitName(asset_3)

  FEE = 1000
  POOL_NAME = "koifi-"
  UNIT_NAME = "koifi1.0"
  total_supply = 18446744073709551615
  decimals = 6
#   name = concat(Bytes(POOL_NAME), Bytes("-"), Bytes(symbol_1), Bytes(symbol_2), Bytes(symbol_3)) 

  @Subroutine(TealType.uint64)
  def duplicated_asset():
    return And(
        asset_1 != asset_2,
        asset_1 != asset_3,
        asset_2 != asset_3,
    )

  @Subroutine(TealType.uint64)
  def fees():
    return And(
      Gtxn[0].fee() >= Int(FEE),
      Gtxn[0].amount() >= Int(FEE*3),
      Gtxn[0].sender() == Txn.sender(),
      Gtxn[0].receiver() == Txn.sender(),
    )

  # Verifies the sender and the receiver is the pool.
  # TODO: Verify this subroutine
  @Subroutine(TealType.uint64)
  def snd_rcv(txn_index):
    return And(
      Gtxn[txn_index].sender() == Txn.sender(),
      Gtxn[txn_index].receiver() == Txn.sender(),
    )

  # Verifies correct params for asset optin.
  @Subroutine(TealType.uint64)
  def optin_asset(txn_index, asset_id):
    # If(asset_id =! Int(0))
    # .Then(
    return And(
      Gtxn[txn_index].type_enum() == TxnType.AssetTransfer,
      Gtxn[txn_index].amount() == Int(0),
      Gtxn[txn_index].xfer_asset() == asset_id,
      snd_rcv(txn_index),
    )
    # )

  # Verifies LP asset is creatd correctly.
  @Subroutine(TealType.uint64)
  def lp_asset():
    return And(
      Gtxn[2].type_enum() == TxnType.AssetConfig,
      Gtxn[2].config_asset() == Int(0),
      Gtxn[2].config_asset_total() == Int(total_supply),
      Gtxn[2].config_asset_decimals() == Int(decimals),
      Gtxn[2].config_asset_default_frozen() == Int(0),
      Gtxn[2].config_asset_unit_name() == Bytes(UNIT_NAME),
      Substring(Gtxn[2].config_asset_name(), Int(0), Int(6)) == Bytes(POOL_NAME),
      Gtxn[2].config_asset_manager() == Global.zero_address(),
      Gtxn[2].config_asset_reserve() == Global.zero_address(),
      Gtxn[2].config_asset_freeze() == Global.zero_address(),
      Gtxn[2].config_asset_clawback() == Global.zero_address(),
    )

  # TODO: where and when should it be used?
  @Subroutine(TealType.uint64)
  def safety_conds():
    return And(
        Txn.type_enum() == TxnType.Payment, # TODO: not for each txn
        Txn.close_remainder_to() == Global.zero_address(),
        Txn.rekey_to() == Global.zero_address(),
    )

  bootstrap = Seq(
    Assert(Txn.application_args[0] == Bytes("bootstrap")),
    Assert(Global.group_size() == Int(6)), # TODO: verify this
    Assert(Txn.application_args.length() == Int(4)),
    Assert(fees()),
    Assert(duplicated_asset()),
    # Assert(asset_1 == Gtxn[3].assets),
    Assert(lp_asset()),
    Assert(optin_asset(Int(3), asset_1)),
    Assert(optin_asset(Int(4), asset_2)),
    Assert(optin_asset(Int(5), asset_3)),
    # Assert(safety_conds()),
    Approve(),
  )


  return program.event(
    init=Approve(),
    opt_in=Cond(
      [Txn.application_args[0] == Bytes("bootstrap"), bootstrap],
    )
  )
def clear():
  return Approve()