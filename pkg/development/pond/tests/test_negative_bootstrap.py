import pytest
import typing
import copy

from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    TransactionWithSigner,
    AccountTransactionSigner,
    abi,
)
from algosdk import transaction
from algosdk.v2client.algod import AlgodClient
from algosdk.encoding import decode_address
from beaker import client, sandbox, testing, consts, decorators
from beaker.client.application_client import ApplicationClient, ProgramAssertion
from beaker.client.logic_error import LogicException

from pond_V1 import Pond

accts = sandbox.get_accounts()
algod_client: AlgodClient = sandbox.get_algod_client()

TOTAL_POOL_TOKENS = 10000000000
TOTAL_ASSET_TOKENS = 10000000000

# Fixtures

AcctInfo = tuple[str, str, AccountTransactionSigner]

@pytest.fixture(scope="session")
def creator_acct() -> AcctInfo:
    return accts[0].address, accts[0].private_key, accts[0].signer

@pytest.fixture(scope="session")
def user_acct() -> AcctInfo:
    return accts[1].address, accts[1].private_key, accts[1].signer

@pytest.fixture(scope="session")
def creator_app_client(creator_acct: AcctInfo) -> client.ApplicationClient:
    _, _, signer = creator_acct
    app = Pond()
    app_client = client.ApplicationClient(algod_client, app, signer=signer)
    return app_client

@pytest.fixture(scope="session")
def assets(creator_acct: AcctInfo, user_acct: AcctInfo) -> tuple[int, int]:
    addr, sk, _ = creator_acct
    user_addr, _, user_signer = user_acct

    sp = algod_client.suggested_params()
    txns: list[transaction.Transaction] = transaction.assign_group_id(
        [
            transaction.AssetCreateTxn(
                addr,
                sp,
                TOTAL_ASSET_TOKENS,
                0,
                False,
                asset_name="asset a",
                unit_name="A",
            ),
            transaction.AssetCreateTxn(
                addr,
                sp,
                TOTAL_ASSET_TOKENS,
                0,
                False,
                asset_name="asset b",
                unit_name="B",
            ),
        ]
    )
    algod_client.send_transactions([txn.sign(sk) for txn in txns])
    results = [
        transaction.wait_for_confirmation(algod_client, txid, 4)
        for txid in [t.get_txid() for t in txns]
    ]
    a_asset, b_asset = results[0]["asset-index"], results[1]["asset-index"]

    # User account opt in to asset a and b
    _opt_in_to_token(user_addr, user_signer, a_asset)
    _opt_in_to_token(user_addr, user_signer, b_asset)

    # Fund user account with 1000 asset a and 1000 asset b
    send_to_user_txns: list[transaction.Transaction] = transaction.assign_group_id(
        [
            transaction.AssetTransferTxn(
                addr, sp, user_addr, TOTAL_ASSET_TOKENS // 10000000, a_asset
            ),
            transaction.AssetTransferTxn(
                addr, sp, user_addr, TOTAL_ASSET_TOKENS // 10000000, b_asset
            ),
        ]
    )
    algod_client.send_transactions([txn.sign(sk) for txn in send_to_user_txns])

    return (a_asset, b_asset)

# Transactions

def build_set_governor_txn_args(new_governor: str) -> dict[str, typing.Any]:
    return {"new_governor": new_governor}

def build_underfunded_bootstrap_transaction(
    app_client: client.ApplicationClient, assets: tuple[int, int]
) -> dict[str, typing.Any]:

    app_addr, addr, signer = (
        app_client.app_addr,
        app_client.sender,
        app_client.signer,
    )

    asset_a, asset_b = assets
    sp = app_client.client.suggested_params()

    return {
        "seed": TransactionWithSigner(
            txn=transaction.PaymentTxn(
                addr,
                sp,
                app_addr,
                300000, # underfunded
            ),
            signer=signer,
        ),
        "a_asset": asset_a,
        "b_asset": asset_b,
        "suggested_params": minimum_fee_for_txn_count(sp, 4),
    }

def build_bootstrap_transaction(
    app_client: client.ApplicationClient, assets: tuple[int, int]
) -> dict[str, typing.Any]:

    app_addr, addr, signer = (
        app_client.app_addr,
        app_client.sender,
        app_client.signer,
    )

    asset_a, asset_b = assets
    sp = app_client.client.suggested_params()

    return {
        "seed": TransactionWithSigner(
            txn=transaction.PaymentTxn(
                addr,
                sp,
                app_addr,
                400000,
            ),
            signer=signer,
        ),
        "a_asset": asset_a,
        "b_asset": asset_b,
        "suggested_params": minimum_fee_for_txn_count(sp, 4),
    }

def build_non_creator_bootstrap_transaction(
    app_client: client.ApplicationClient, 
    assets: tuple[int, int], 
    user_acct: AcctInfo 
) -> dict[str, typing.Any]:

    app_addr = app_client.app_addr
    addr, _, signer = user_acct

    asset_a, asset_b = assets
    sp = app_client.client.suggested_params()

    return {
        "seed": TransactionWithSigner(
            txn=transaction.PaymentTxn(
                addr,
                sp,
                app_addr,
                400000,
            ),
            signer=signer,
        ),
        "a_asset": asset_a,
        "b_asset": asset_b,
        "suggested_params": minimum_fee_for_txn_count(sp, 4),
    }


# Tests

def test_app_set_illegal_governor_fails(
    creator_app_client: client.ApplicationClient, user_acct: AcctInfo
):
    creator_app_client.create()
    creator_addr, _ = creator_app_client.sender, creator_app_client.app_addr

    user_addr, _, user_signer = user_acct

    # Set the new gov
    user_client = creator_app_client.prepare(signer=user_signer)
    with pytest.raises(LogicException, match= r".* unauthorized.*"):
        user_client.call(
            Pond.set_governor,
            **build_set_governor_txn_args(user_addr),
        )

    state = creator_app_client.get_application_state()

    assert state[Pond.governor.str_key()] == _addr_to_hex(
        creator_addr
    )

def test_app_bootstrap_with_underfunded_app(
    creator_app_client: client.ApplicationClient, assets: tuple[int, int]
):

    app_addr = creator_app_client.app_addr
    asset_a, asset_b = assets
    app_balance_before = testing.get_balances(creator_app_client.client, [app_addr])

    with pytest.raises(LogicException, match= r".* amount minimum not met.*"):
        creator_app_client.call(
            Pond.bootstrap,
            **build_underfunded_bootstrap_transaction(creator_app_client, assets),
        )
    app_balance_after = testing.get_balances(creator_app_client.client, [app_addr])
    app_balance_deltas = testing.get_deltas(app_balance_before, app_balance_after)
    assert app_balance_deltas[app_addr][0] == 0

def test_app_bootstrap_with_duplicated_assets(
    creator_app_client: client.ApplicationClient, assets: tuple[int, int]
):
    # TODO: refactor using graviton
    # currently it passes after any generic LogicException
    # We need to ensure it raises the exception for duplicated assets

    app_addr = creator_app_client.app_addr

    with pytest.raises(LogicException, match= r".* Incorrect asset.*"):
        creator_app_client.call(
            Pond.bootstrap,
            **build_bootstrap_transaction(creator_app_client, (assets[0], assets[0])),
        )

def test_app_bootstrap_by_non_creator(
    creator_app_client: client.ApplicationClient, 
    assets: tuple[int, int],
    user_acct: AcctInfo
):
    # TODO: refactor using graviton
    # currently it passes after any generic LogicException
    # We need to ensure it raises the exception for non creator sender

    app_addr = creator_app_client.app_addr

    with pytest.raises(LogicException, match= 'ñ'):
        creator_app_client.call(
            Pond.bootstrap,
            **build_non_creator_bootstrap_transaction(
                creator_app_client, 
                assets,
                user_acct
            ),
        )

# Utils

def _addr_to_hex(addr: str) -> str:
    return decode_address(addr).hex()

def _opt_in_to_token(addr: str, signer: AccountTransactionSigner, id: int):
    sp = algod_client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_transaction(
        TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, addr, 0, id),
            signer=signer,
        )
    )
    atc.execute(algod_client, 2)

def minimum_fee_for_txn_count(
    sp: transaction.SuggestedParams, txn_count: int
) -> transaction.SuggestedParams:
    """
    Configures transaction fee _without_ considering network congestion.

    Since the function does not account for network congestion, do _not_ use the function as-is in a production use-case.
    """
    s = copy.deepcopy(sp)
    s.flat_fee = True
    s.fee = transaction.constants.min_txn_fee * txn_count
    return s