from pyteal import *

def approval():

  bootstrap = Seq(
    App.globalPut(Bytes("rg"), Txn.application_args[0]),
    Approve()
  )

  commit = Seq(
    # ['str:commit', 'int:asset_id', 'int:asset_amt', 'int:lp_token_amt', 'int:slippage*', 'int:lp_token_id*']

  )

  redeem = Seq(
    # ['str:redeem', 'int:asset_id', 'int:asset_amt', 'int:lp_token_amt', 'int:slippage*', 'int:lp_token_id*']
  )

  return program.event(
    init=bootstrap(),
    no_op=Cond(
    [Txn.application_args[0] == Bytes("commit"), commit],
    [Txn.application_args[0] == Bytes("redeem"), redeem]  
    )
  )

def clear():
  return Approve()