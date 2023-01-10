from algosdk.future import transaction
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from beaker import *

from pond_V1 import Pond


# # Take first account from sandbox
# acct = get_accounts().pop()
# addr, sk, signer = acct.address, acct.private_key, acct.signer

# # get sandbox client
# client = get_algod_client()

# # Create an Application client containing both an algod client and my app
# app_client = ApplicationClient(client, ConstantProductAMM(), signer=acct.signer)


def demo():
    # Here we use `sandbox` but beaker.client.api_providers can also be used
    # with something like ``AlgoNode(Network.TestNet).algod()``
    algod_client = sandbox.get_algod_client()

    acct = sandbox.get_accounts().pop()
    addr, sk, signer = acct.address, acct.private_key, acct.signer

    # Create an Application client containing both an algod client and app
    app_client = client.ApplicationClient(
        client=algod_client, app=Pond(version=6), signer=acct.signer
    )

    # Create the application on chain, set the app id for the app client
    app_id, app_addr, txid = app_client.create()
    print(f"Created App with id: {app_id} and address addr: {app_addr} in tx: {txid}")

    # Fund App address so it can create the pool token and hold balances

    # Create assets
    asset_a = create_asset(algod_client, addr, sk, "A")
    asset_b = create_asset(algod_client, addr, sk, "B")
    print(f"Created asset a/b with ids: {asset_a}/{asset_b}")

    # Call app to create pond token
    print("Calling bootstrap")
    sp = algod_client.suggested_params()
    ptxn = TransactionWithSigner(
        txn=transaction.PaymentTxn(addr, sp, app_addr, int(1e7)), signer=signer
    )
    sp.flat_fee = True
    sp.fee = consts.milli_algo * 5
    result = app_client.call(
        Pond.bootstrap,
        seed=ptxn,
        a_asset=asset_a,
        b_asset=asset_b,
        suggested_params=sp,
    )
    pond_token = result.return_value
    print(f"Created pond token with id: {pond_token}")
    print_balances(
        algod_client,
        app_client,
        app_id, 
        app_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b
    )

    # Opt user into token
    sp = algod_client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_transaction(
        TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, addr, 0, pond_token),
            signer=signer,
        )
    )
    atc.execute(algod_client, 2)
    print_balances(
        algod_client,
        app_client,
        app_id, 
        app_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b
    )

    # Cover any fees incurred by inner transactions, maybe overpaying but 
    # thats ok
    # TODO: Review to avoid overpaying
    sp = algod_client.suggested_params()
    sp.flat_fee = True
    sp.fee = consts.milli_algo * 3

    ###
    # Fund Pool with initial liquidity commiting the 3 assets
    ###
    print("Funding")
    result = app_client.call(
        Pond.mint,
        a_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, app_addr, 3000, asset_a),
            signer=signer,
        ),
        b_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, app_addr, 3000, asset_b),
            signer=signer,
        ),
        suggested_params=sp,
    )
    print_balances(
        algod_client,
        app_client,
        app_id, 
        app_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b
    )

    ###
    # Mint pool tokens
    ###
    print("Minting")
    app_client.call(
        Pond.mint,
        a_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, app_addr, 1000, asset_a),
            signer=signer,
        ),
        b_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, app_addr, 1000, asset_b),
            signer=signer,
        ),
        suggested_params=sp,
    )
    print_balances(
        algod_client,
        app_client,
        app_id, 
        app_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b
    )

    ###
    # Swap A for B
    ###
    print("Swapping A for B")
    app_client.call(
        Pond.swap,
        swap_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, app_addr, 1000, asset_a),
            signer=signer,
        ),
    )
    print_balances(
        algod_client,
        app_client,
        app_id, 
        app_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b
    )

    ###
    # Swap B for A
    ###
    print("Swapping B for A")
    app_client.call(
        Pond.swap,
        swap_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, app_addr, 1000, asset_b),
            signer=signer,
        ),
    )
    print_balances(
        algod_client,
        app_client,
        app_id, 
        app_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b
    )

    ###
    # Burn pool tokens
    ###
    print("Burning")
    app_client.call(
        Pond.burn,
        pool_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, app_addr, 700, pond_token),
            signer=signer,
        ),
    )
    print_balances(
        algod_client,
        app_client,
        app_id, 
        app_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b
    )

    # # result = app_client.call(Pond.bootstrap, rg=12)
    # print(f"Result: {result.return_value}")

def create_asset(client, addr, pk, unitname):
    # Get suggested params from network
    sp = client.suggested_params()
    # Create the transaction
    create_txn = transaction.AssetCreateTxn(
        addr, sp, 1000000, 0, False, asset_name="asset", unit_name=unitname
    )
    # Ship it
    txid = client.send_transaction(create_txn.sign(pk))
    # Wait for the result so we can return the app id
    result = transaction.wait_for_confirmation(client, txid, 4)
    return result["asset-index"]

def print_balances(
    client,
    app_client,
    app_id: int, 
    app: str, 
    addr: str, 
    pond: int, 
    a: int, 
    b: int
):

    addrbal = client.account_info(addr)
    print("Participant: ")
    for asset in addrbal["assets"]:
        if asset["asset-id"] == pond:
            print("\tPond Balance {}".format(asset["amount"]))
        if asset["asset-id"] == a:
            print("\tAssetA Balance {}".format(asset["amount"]))
        if asset["asset-id"] == b:
            print("\tAssetB Balance {}".format(asset["amount"]))

    appbal = client.account_info(app)
    print("App: ")
    for asset in appbal["assets"]:
        if asset["asset-id"] == pond:
            print("\tPond Balance {}".format(asset["amount"]))
        if asset["asset-id"] == a:
            print("\tAssetA Balance {}".format(asset["amount"]))
        if asset["asset-id"] == b:
            print("\tAssetB Balance {}".format(asset["amount"]))

    state = app_client.get_application_state()
    state_key = Pond.ratio.str_key()
    if state_key in state:
        print(
            f"\tCurrent ratio a/b == {int(state[state_key]) / Pond._scale}"
        )
    else:
        print("\tNo ratio a/b")
    
if __name__ == "__main__":
    Pond().dump("artifacts")
    demo()