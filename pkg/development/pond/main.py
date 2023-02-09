from algosdk import transaction
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from beaker import *

from pond_V1 import Pond
from metapool_V1 import Metapool


def demo():
    # Here we use `sandbox` but beaker.client.api_providers can also be used
    # with something like ``AlgoNode(Network.TestNet).algod()``
    algod_client = sandbox.get_algod_client()

    acct = sandbox.get_accounts().pop()
    addr, sk, signer = acct.address, acct.private_key, acct.signer

    # Create an Application client containing both an algod client and app
    pond_client = client.ApplicationClient(
        client=algod_client, app=Pond(version=8), signer=acct.signer
    )

    metapool_client = client.ApplicationClient(
        client=algod_client, app=Metapool(version=8), signer=acct.signer
    )

    # Create the pond on chain, set the app id for the app client
    pond_id, pond_addr, txid_p = pond_client.create()
    print(f"Created Pond with id: {pond_id} and address addr: {pond_addr} in tx: {txid_p}")

    # Create the metapool on chain, set the app id for the app client
    metapool_id, metapool_addr, txid_m = metapool_client.create()
    print(f"Created metapool with id: {metapool_id} and address addr: {metapool_addr} in tx: {txid_m}")

    # Fund App address so it can create the pool token and hold balances

    # Create assets
    asset_a = create_asset(algod_client, addr, sk, "A")
    asset_b = create_asset(algod_client, addr, sk, "B")
    print(f"Created asset a/b with ids: {asset_a}/{asset_b}")

    # Call app to create pond token
    print("Calling Pond's bootstrap")
    sp = algod_client.suggested_params()
    sp.flat_fee = True
    sp.fee = consts.milli_algo * 5
    ptxn = TransactionWithSigner(
        txn=transaction.PaymentTxn(addr, sp, pond_addr, int(1e7)), signer=signer
    )
    sp.fee = consts.milli_algo
    result = pond_client.call(
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
        pond_client,
        pond_id, 
        pond_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b,
        metapool_client,
        metapool_addr,
        0,
    )

    print("Calling Metapool's bootstrap")
    sp = algod_client.suggested_params()
    sp.flat_fee = True
    sp.fee = consts.milli_algo * 5
    mtxn = TransactionWithSigner(
        txn=transaction.PaymentTxn(addr, sp, metapool_addr, int(1e7)), signer=signer
    )
    result = metapool_client.call(
        Metapool.bootstrap,
        seed=mtxn,
        a_asset=pond_token,
        b_asset=asset_b,
        suggested_params=sp,
    )
    metapool_token = result.return_value
    print(f"Created metapool token with id: {metapool_token}")
    print_balances(
        algod_client,
        pond_client,
        pond_id, 
        pond_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b,
        metapool_client,
        metapool_addr,
        metapool_token,
    )

    # Opt user into tokens
    sp = algod_client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_transaction(
        TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, addr, 0, pond_token),
            signer=signer,
        )
    )
    atc.add_transaction(
        TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, addr, 0, metapool_token),
            signer=signer,
        )
    )

    atc.execute(algod_client, 2)
    print_balances(
        algod_client,
        pond_client,
        pond_id, 
        pond_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b,
        metapool_client,
        metapool_addr,
        metapool_token,
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
    print("Funding Pond")
    result = pond_client.call(
        Pond.mint,
        a_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, pond_addr, 3000, asset_a),
            signer=signer,
        ),
        b_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, pond_addr, 3000, asset_b),
            signer=signer,
        ),
        suggested_params=sp,
    )
    print_balances(
        algod_client,
        pond_client,
        pond_id, 
        pond_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b,
        metapool_client,
        metapool_addr,
        metapool_token,
    )

    ###
    # Mint pool tokens
    ###
    print("Minting Pond tokens")
    pond_client.call(
        Pond.mint,
        a_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, pond_addr, 1000, asset_a),
            signer=signer,
        ),
        b_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, pond_addr, 1000, asset_b),
            signer=signer,
        ),
        suggested_params=sp,
    )
    print_balances(
        algod_client,
        pond_client,
        pond_id, 
        pond_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b,
        metapool_client,
        metapool_addr,
        metapool_token,
    )

    ###
    # Fund Pool with initial liquidity commiting the 2 assets
    ###
    sp = algod_client.suggested_params()
    sp.flat_fee = True
    sp.fee = consts.milli_algo * 3

    print("Funding Metapool")
    result = metapool_client.call(
        Metapool.mint,
        a_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, metapool_addr, 1500, pond_token),
            signer=signer,
        ),
        b_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, metapool_addr, 1500, asset_b),
            signer=signer,
        ),
        suggested_params=sp,
    )
    print_balances(
        algod_client,
        pond_client,
        pond_id, 
        pond_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b,
        metapool_client,
        metapool_addr,
        metapool_token,
    )

    ###
    # Mint pool tokens
    ###
    print("Minting Metapool tokens")
    result = metapool_client.call(
        Metapool.mint,
        a_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, metapool_addr, 1100, pond_token),
            signer=signer,
        ),
        b_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, metapool_addr, 1100, asset_b),
            signer=signer,
        ),
        suggested_params=sp,
    )
    print_balances(
        algod_client,
        pond_client,
        pond_id, 
        pond_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b,
        metapool_client,
        metapool_addr,
        metapool_token,
    )

    ###
    # Swap A for B
    ###
    print("Swapping A for B")
    pond_client.call(
        Pond.swap,
        swap_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, pond_addr, 1000, asset_a),
            signer=signer,
        ),
    )
    print_balances(
        algod_client,
        pond_client,
        pond_id, 
        pond_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b,
        metapool_client,
        metapool_addr,
        metapool_token,
    )

    ###
    # Swap B for A
    ###
    print("Swapping B for A")
    pond_client.call(
        Pond.swap,
        swap_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, pond_addr, 1000, asset_b),
            signer=signer,
        ),
    )
    print_balances(
        algod_client,
        pond_client,
        pond_id, 
        pond_addr, 
        addr, 
        pond_token, 
        asset_a, 
        asset_b,
        metapool_client,
        metapool_addr,
        metapool_token,
    )

    ###
    # Burn pool tokens
    ###
    print("Burning")
    pond_client.call(
        Pond.burn,
        pool_xfer=TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, pond_addr, 60, pond_token),
            signer=signer,
        ),
    )
    print_balances(
        algod_client,
        pond_client,
        pond_id, 
        pond_addr, 
        addr,
        pond_token, 
        asset_a, 
        asset_b,
        metapool_client,
        metapool_addr,
        metapool_token,
    )

    # # result = pond_client.call(Pond.bootstrap, rg=12)
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
    pond_client,
    pond_id: int, 
    pond_app: str, 
    addr: str, 
    pond_token: int, 
    a: int, 
    b: int,
    metapool_client,
    metapool_app: str, 
    metapool_token: int,
):

    addrbal = client.account_info(addr)
    print("Participant: ")
    for asset in addrbal["assets"]:
        if asset["asset-id"] == pond_token:
            print("\tPond token Balance {}".format(asset["amount"]))
        if asset["asset-id"] == metapool_token:
            print("\Metapool token Balance {}".format(asset["amount"]))
        if asset["asset-id"] == a:
            print("\tAssetA Balance {}".format(asset["amount"]))
        if asset["asset-id"] == b:
            print("\tAssetB Balance {}".format(asset["amount"]))

    pondbal = client.account_info(pond_app)
    print("Pond: ")
    for asset in pondbal["assets"]:
        if asset["asset-id"] == pond_token:
            print("\tPond Balance {}".format(asset["amount"]))
        if asset["asset-id"] == a:
            print("\tAssetA Balance {}".format(asset["amount"]))
        if asset["asset-id"] == b:
            print("\tAssetB Balance {}".format(asset["amount"]))

    mpbal = client.account_info(metapool_app)
    print("Metapool: ")
    for asset in mpbal["assets"]:
        if asset["asset-id"] == metapool_token:
            print("\MetaPool Balance {}".format(asset["amount"]))
        if asset["asset-id"] == pond_token:
            print("\Pond Asset Balance {}".format(asset["amount"]))
        if asset["asset-id"] == b:
            print("\tAssetB Balance {}".format(asset["amount"]))

    state = pond_client.get_application_state()
    state_key = Pond.ratio.str_key()
    state_mp = metapool_client.get_application_state()
    state_key_mp = Metapool.ratio.str_key()
    print("Ratios: ")
    if state_key in state:
        print(
            f"\tCurrent ratio a/b == {int(state[state_key]) / Pond._scale}"
        )
        print(
            f"\tCurrent ratio pond/b == {int(state_mp[state_key_mp]) / Metapool._scale}"
        )
    else:
        print("\tNo ratio a/b")
    
if __name__ == "__main__":
    Pond().dump("artifacts")
    Metapool().dump("artifacts")
    demo()