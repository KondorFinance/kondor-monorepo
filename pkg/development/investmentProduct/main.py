from algosdk import transaction
from algosdk.atomic_transaction_composer import (
    TransactionWithSigner,
)
from beaker import *

from investmentProduct import InvestmentProduct


def demo():
    # Here we use `sandbox` but beaker.client.api_providers can also be used
    # with something like ``AlgoNode(Network.TestNet).algod()``
    algod_client = sandbox.get_algod_client()

    acct = sandbox.get_accounts().pop()
    addr, sk, signer = acct.address, acct.private_key, acct.signer

    # Create an Application client containing both an algod client and app
    app_client = client.ApplicationClient(
        client=algod_client, app=InvestmentProduct(version=8), signer=acct.signer
    )

    # Create the application on chain, set the app id for the app client
    app_id, app_addr, txid = app_client.create()
    print(f"Created App with id: {app_id} and address addr: {app_addr} in tx: {txid}")

    # Call app to fund app address
    print("Calling fund")
    sp = algod_client.suggested_params()
    sp.flat_fee = True
    sp.fee = consts.milli_algo * 5
    ptxn = TransactionWithSigner(
        txn=transaction.PaymentTxn(addr, sp, app_addr, int(1e7)), signer=signer
    )
    sp.fee = consts.milli_algo * 3
    result = app_client.call(
        InvestmentProduct.fund,
        ptxn=ptxn,
        suggested_params=sp,
    )
    print(f"App address funded with 1e7 microalgos")

    result = app_client.call(
        InvestmentProduct.createNft,
        suggested_params=sp,
    )
    nft = result.return_value
    print(f"Created nft with id: {nft}")
    
if __name__ == "__main__":
    InvestmentProduct().dump("artifacts")
    demo()