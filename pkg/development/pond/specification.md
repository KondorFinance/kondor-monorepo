# Pond App Specification

## Overview

The Kondor Pond app V1 holds 2 stable assets (USDC/USDT) and describes the logic for liquidity ins/outs and trades.

## Helpers

None

## Requirements

### Stateful Smart Contract

Basic checks:

1. `rekey to`, `close remainder to`, `asset close to` addresses are not found in the transactions.

Bootstrap

Group:

1. Payment txn to pay for fees
2. App call txn Bootstrap

Description: Bootstraps the contract by opting into the assets and creating the pond token.

1. Contract creator function
2. Prevent from calling more than once
3. Perform LP asset creation
4. Opt In asset A
5. Opt In asset B

Mint

Group:

1.
2.

Description: Handles first mint (by creator) and next mints. Transfers LP tokens to sender.

1. First mint function (contract creator)
2. Verify initialized status for subsequent mints
3. Sender must be same address than axfers from group
4. Enough LP token supply to conduct transfer
5. Verify group size == 4

Swap

Description:

1. Compare initial amounts with runtime calculations and apply slippage tolerance

Transfer

1. Enough supply to conduct axfer
2. Assets must be created before performing this function

Burn

1. Enough supply to conduct axfer
2. Transfer LP tokens to burn contract.
