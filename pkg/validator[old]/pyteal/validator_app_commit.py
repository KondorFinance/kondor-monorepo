from ast import Assert, If
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
  ASSET_TRANSFER_APP_ID = Int(890)
  REGISTRY_APP_ID = Int(890)

  lp_has_opted_in = ScratchVar(TealType.uint64)
  pond_has_opted_in = ScratchVar(TealType.uint64)

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

  # # Verifies correct params for asset optin.
  # @Subroutine(TealType.uint64)
  # def optin_asset(txn_index, asset_id):
  #   # If(asset_id =! Int(0))
  #   # .Then(
  #   return And(
  #     Gtxn[txn_index].type_enum() == TxnType.AssetTransfer,
  #     Gtxn[txn_index].amount() == Int(0),
  #     Gtxn[txn_index].xfer_asset() == asset_id,
  #     snd_rcv(txn_index),
  #   )
  #   # )

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

  # app call to opt in contract
  @Subroutine(TealType.none)
  def optin_asset_call(app_id):
    # Cond(
    #   [And(lp_has_opted_in.load(), pond_has_opted_in.load()), ]
    #   )
    # TODO: figure out the way to pass the arguments and fields dinamically to the itxn
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.ApplicationCall,
            TxnField.application_id: app_id,
            TxnField.on_completion: OnComplete.NoOp,
            TxnField.application_args: [txn_ammounts.load(), txn_ammounts2.load()], # ['10', '130']
            TxnField.accounts: [Gtxn[2].asset_receiver(), Gtxn[2].sender()], # pool, pooler
            TxnField.assets: [],
        }),
        InnerTxnBuilder.Submit()
    )

  # checks if an account has opted in an asset
  # TODO: code this! 
  @Subroutine(TealType.uint64)
  def optin_checker(address, asset_id):
    asset_balance = AssetHolding.balance(address, asset_id)
    return asset_balance.hasValue()

  # TODO: validate registry_id from global state (at REGISTRY_APP_ID)
  bootstrap = Seq(
    Assert(Txn.application_args[0] == Bytes("bootstrap")),
    Assert(Global.group_size() == Int(2)),
    Assert(Txn.application_args.length() == Int(2)),
    Assert(Txn.application_args[1] == REGISTRY_APP_ID),
    # Assert(safety_conds()),
    Approve(),
  )

  # redeem flow, gtxn:
  # gtxn[0]: fees_dist app call *
  # gtxn[1]: Validator app call
  # gtxn[2]: LP optin to asset_in ?
  # gtxn[3]: in_asset transfer from LP to Pond
  # itxn: redeem distributor app call itxn

  # TODO: Define how weights update works here

  # from: LP_address, to: Validator
  # ['str:redeem', 'int:in_id', 'int:out_id*', 'int:in_amt', 'int:out_amt']

  redeem = Seq(
    # Validate assets validator vs asset transfers (LP tokens)
    # Validate LP token is Pond's asset
    Assert(Txn.application_args[0] == Bytes("redeem")),
    Assert(Global.group_size() == Int(4)),
    Assert(Txn.application_args.length() == Int(5)),
    Assert(Txn.type_enum() == TxnType.ApplicationCall),
    # Assert(fees(Int(3))),
    Assert(Txn.on_completion() == OnComplete.NoOp), 
    Assert(Gtxn[1].accounts[0] != Txn.sender()),
    Assert(Gtxn[2].sender() == Txn.sender()), # pool to pooler
    Assert(Gtxn[2].asset_receiver() == Gtxn[2].sender()),
    # Assert(safety_conds()),
    redeem_distributor(REDEEM_DISTRIBUTOR_APP_ID),
    Approve(),
  )

  # commit flow, gtxn:
  # gtxn[0]: fees_dist app call *
  # gtxn[1]: Validator app call, sndr: LP, accs[]: pond
  
  # Potentially solved inside contract
  # ---
  # itxn: LP optin to asset_out (LP token)
  # itxn: Pond optin to asset_in (ASA)
  # ---

  # gtxn[2]: in_asset transfer from LP to Pond
  # itxn: commit distributor app call itxn
  
  # Txng args: 
  # ['str:commit', 'int:out_id*', 'int:out_amt']
  commit = Seq(
    Assert(Txn.application_args[0] == Bytes("commit")),
    Assert(Global.group_size() == Int(3)),
    Assert(Txn.application_args.length() == Int(3)),
    Assert(Txn.type_enum() == TxnType.ApplicationCall),
    Assert(fees(Int(3))), ## TODO: verify this one
    Assert(Txn.on_completion() == OnComplete.NoOp),
    Assert(Gtxn[1].sender() == Txn.sender()),
    Assert(Gtxn[1].accounts[0] != Txn.sender()),
    lp_has_opted_in.store(optin_checker(Gtxn[2].asset_sender(), Gtxn[1].application_args[1])),
    pond_has_opted_in.store(optin_checker(Gtxn[2].asset_receiver(), Gtxn[2].xfer_asset())),
    
    Assert(optin_asset(Int(2), Txn.application_args[1])),
    Assert(Gtxn[3].sender() != Txn.sender()), # pooler to pool
    Assert(Gtxn[3].asset_receiver() == Txn.sender()), # rcvr is pool
    # Assert(safety_conds()),
    commit_distributor(COMMIT_DISTRIBUTOR_APP_ID),
    Approve(),
  )

  return program.event(
    init=Approve(),
    # opt_in=Cond(
    # ),
    no_op=Cond(
      [Txn.application_args[0] == Bytes("bootstrap"), bootstrap],
      [Txn.application_args[0] == Bytes("commit"), commit],
      [Txn.application_args[0] == Bytes("redeem"), redeem],
    )
  )
def clear():
  return Approve()