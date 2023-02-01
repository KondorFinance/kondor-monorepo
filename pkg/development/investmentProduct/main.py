from algosdk import transaction
from algosdk.atomic_transaction_composer import (
    TransactionWithSigner,
    AtomicTransactionComposer
)
from beaker import *

from investmentProduct import InvestmentProduct


def demo():
    # Here we use `sandbox` but beaker.client.api_providers can also be used
    # with something like ``AlgoNode(Network.TestNet).algod()``
    algod_client = sandbox.get_algod_client()

    acct = sandbox.get_accounts().pop()
    addr, sk, signer = acct.address, acct.private_key, acct.signer

    print(f"Creator: {addr}")


    # Create an Application client containing both an algod client and app
    app_client = client.ApplicationClient(
        client=algod_client, app=InvestmentProduct(version=8), signer=acct.signer
    )

    # Create the application on chain, set the app id for the app client
    app_id, app_addr, txid = app_client.create()
    print(f"Created App with id: {app_id} and address addr: {app_addr} in tx: {txid}")

    app_client.opt_in()
    print("Opted in")

    # Call app to fund app address
    print("Calling create nft")
    sp = algod_client.suggested_params()
    sp.flat_fee = True
    sp.fee = consts.milli_algo 
    ptxn = TransactionWithSigner(
        txn=transaction.PaymentTxn(addr, sp, app_addr, int(1e7)), signer=signer
    )
    sp.fee = consts.milli_algo * 2
    result = app_client.call(
        InvestmentProduct.create_nft,
        seed=ptxn,
        suggested_params=sp,
    )
    nft = result.return_value
    print(f"Created nft with id: {nft}")


    # Call app to recover asset id from nft
    print("Calling recover asset id")
    sp.fee = consts.milli_algo
    result = app_client.call(
        InvestmentProduct.get_asset_id_val,
        suggested_params=sp,
    )
    print(f"Recovered asset id: {result.return_value}")

    # Call app to mint nft
    print("Calling mint nft")
    sp.fee = consts.milli_algo 
    ptxn = TransactionWithSigner(
        txn=transaction.PaymentTxn(addr, sp, app_addr, int(1e7)), signer=signer
    )


    # Opt in to asset
    atc = AtomicTransactionComposer()
    atc.add_transaction(
        TransactionWithSigner(
            txn=transaction.AssetTransferTxn(addr, sp, addr, 0, nft),
            signer=signer,
        )
    )
    atc.execute(algod_client, 2)


    # App call to mint nft
    sp.fee = consts.milli_algo * 2
    result = app_client.call(
        InvestmentProduct.mint_nft,
        seed=ptxn,
        asset=nft,
        suggested_params=sp,
    )

    print(f"Minted nft with asset_id: {nft}. Tx_id: {result.tx_id}")





if __name__ == "__main__":
    InvestmentProduct().dump("artifacts")
    demo()