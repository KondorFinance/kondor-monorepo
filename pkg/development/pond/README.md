## KoiFi Pond V1 Contract

## WARNING

This code has _not_ been audited.

## Implementation

An instance of this Contract specific to a hardcoded triad of stable assets, termed A, B and C.

A number of Pond Tokens is minted to a Liquidity Provider when they deposit some amount of one of the assets (A, B or C).
The Pond Token may be burned in exchange for a share of the pond commensurate with the number of tokens burned and balance of the assets.

A "Fixed" Swapping operation is allowed to convert some number of one token to another token in the Pond.

## Testing

A Number of tests will be implemented in `pond_test.py` for contract functionality.

There is also a `pond_amm.py` implementation in pure python to help sanity check.

## Operations

The smart contract logic contains several operations:

_Bootstrap_

Create the Pond token, fund the app account with algos, opt into the assets

_Mint_

Intial funding for the pond of asset A, B and C. First issue of pond tokens returns a number of tokens according to:

```
    sqrt(A_amt*B_amt) - scale
```

After initial funding a Liquidity Provider sends some number of the A, B or C, receives some number of Pond Tokens according to:

```
min(
    (A_amt/A_supply) * pool_issued,
    (B_amt/B_supply) * pool_issued
)
```

_Burn_

A Pond Token holder sends some number of Pond Tokens to receive assets A, B, or C according to:

```
    A_out = A_supply * (pool_amt / pool_issued)
    B_out = B_supply * (pool_amt / pool_issued)
```

_Swap_

A user sends some amount of asset A or B to swap for the other Asset in the pair and receives the other asset according to:

```
    out_amt = (in_amt * (scale-fee) * out_supply) / ((in_supply * scale) + (in_amt * (scale-fee)))
```

## To run the example

Make sure [sandbox](https://github.com/algorand/sandbox) is installed and running with a private node configuration (`./sandbox up release`)

Create a virtual environment `python -m venv .venv`

Install python requirements `pip install beaker-pyteal`

Run the demo `python main.py`

## Thank You

The equations for token operations were _heavily_ inspired by the fantastic [Tinyman docs](https://docs.tinyman.org/design-doc)
