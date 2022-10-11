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

  FEE = Int(1000)
  POOL_NAME = "koifi-"
  UNIT_NAME = "koifi1.0"
  total_supply = 18446744073709551615
  decimals = 6
#   name = concat(Bytes(POOL_NAME), Bytes(symbol_1), Bytes(symbol_2), Bytes(symbol_3))

  # TODO: get this apps ids from an app call to the registry contract
  REDEEM_DISTRIBUTOR_APP_ID = Int(123)
  COMMIT_DISTRIBUTOR_APP_ID = Int(456)

# TODO: add subroutine to verify application ID and txn type app call
# TODO: verify if sender is not pooler, fees not charged, verify receiver


  @Subroutine(TealType.uint64)
  def duplicated_asset():
    return And(
        asset_1 != asset_2,
        asset_1 != asset_3,
        asset_2 != asset_3,
    )

  @Subroutine(TealType.uint64)
  def fees(txn_length):
    return And(
      Gtxn[0].fee() >= FEE,
      Gtxn[0].amount() >= FEE*txn_length,
      Gtxn[0].sender() != Txn.sender(),
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

  # Calculates the total fee amount in the gtxn
  # TODO: verify when pooler is not the sender
  @Subroutine(TealType.uint64)
  def sum_fees():
    totalFees = ScratchVar(TealType.uint64)
    i = ScratchVar(TealType.uint64)

    Seq([
        totalFees.store(Int(0)),
        For(i.store(Int(0)), i.load() < Global.group_size(), i.store(i.load() + Int(1))).Do(
            totalFees.store(totalFees.load() + Gtxn[i.load()].fee())
        )
    ])

  # TODO: where and when should it be used?
  @Subroutine(TealType.uint64)
  def safety_conds():
    return And(
        Txn.type_enum() == TxnType.Payment, # TODO: not for each txn
        Txn.close_remainder_to() == Global.zero_address(),
        Txn.rekey_to() == Global.zero_address(),
    )

  # app call to distributor contract
  @Subroutine(TealType.none)
  def redeem_distributor(app_id):
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.ApplicationCall,
            TxnField.application_id: app_id,
            TxnField.on_completion: OnComplete.NoOp,
            TxnField.application_args: Txn.application_args,
        }),
        InnerTxnBuilder.Submit()
    )
  
  # app call to distributor contract
  @Subroutine(TealType.none)
  def commit_distributor(app_id):
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.ApplicationCall,
            TxnField.application_id: app_id,
            TxnField.on_completion: OnComplete.NoOp,
            TxnField.application_args: Txn.application_args,
            TxnField.accounts: [Gtxn[2].asset_receiver(), Gtxn[2].sender()] # pool, pooler
        }),
        InnerTxnBuilder.Submit()
    )


  bootstrap = Seq(
    Assert(Txn.application_args[0] == Bytes("bootstrap")),
    Assert(Global.group_size() == Int(6)),
    Assert(Txn.application_args.length() == Int(4)),
    Assert(fees(Int(6))),
    Assert(duplicated_asset()),
    Assert(lp_asset()),
    Assert(optin_asset(Int(3), asset_1)),
    Assert(optin_asset(Int(4), asset_2)),
    Assert(optin_asset(Int(5), asset_3)),
    # Assert(safety_conds()),
    Approve(),
  )

  # redeem flow, gtxn:
  # gtxn[0]: fees
  # gtxn[1]: validator app call
  # itxn: redeem distributor app call itxn
  # TODO: verify if gtxn[2] is it really necesary ?
  redeem = Seq(
    Assert(Txn.application_args[0] == Bytes("redeem")),
    Assert(Global.group_size() == Int(3)),
    Assert(Txn.application_args.length() == Int(5)),
    Assert(Txn.type_enum() == TxnType.ApplicationCall),
    Assert(fees(Int(3))),
    Assert(Txn.on_completion() == OnComplete.NoOp), 
    Assert(Gtxn[1].accounts[0] != Txn.sender()),
    Assert(Gtxn[2].sender() == Txn.sender()), # pool to pooler
    Assert(Gtxn[2].asset_receiver() == Gtxn[2].sender()),
    # Assert(safety_conds()),
    redeem_distributor(REDEEM_DISTRIBUTOR_APP_ID),
    Approve(),
  )

  # commit flow, gtxn:
  # gtxn[0]: fees
  # gtxn[1]: validator app call
  # gtxn[2]: opt in asset
  # itxn: commit distributor app call
  # TODO: verify if gtxn[3] is it really necesary ?
  commit = Seq(
    Assert(Txn.application_args[0] == Bytes("commit")),
    Assert(Global.group_size() == Int(4)),
    Assert(Txn.application_args.length() == Int(2)),
    Assert(Txn.type_enum() == TxnType.ApplicationCall),
    Assert(fees(Int(3))),
    Assert(Txn.on_completion() == OnComplete.NoOp), 
    Assert(Gtxn[1].sender() == Txn.sender()),
    Assert(Gtxn[1].accounts[0] != Txn.sender()),
    Assert(optin_asset(Int(2), Txn.application_args[1])),
    Assert(Gtxn[3].sender() != Txn.sender()), # pooler to pool
    Assert(Gtxn[3].asset_receiver() == Txn.sender()), # rcvr is pool
    # Assert(safety_conds()),
    commit_distributor(COMMIT_DISTRIBUTOR_APP_ID),
    Approve(),
  )

  return program.event(
    init=Approve(),
    opt_in=Cond(
      [Txn.application_args[0] == Bytes("bootstrap"), bootstrap],
    ),
    no_op=Cond(
      [Txn.application_args[0] == Bytes("commit"), commit],
      [Txn.application_args[0] == Bytes("redeem"), redeem],
    )
  )
def clear():
  return Approve()