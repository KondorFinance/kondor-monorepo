# Pond App Specification

## Overview

The Koi Pond app holds the assets and describes the logic for liquidity ins/outs and trades.

In order to update liquidity and perform trading calculations, the Pond needs to know each ASA weight, one approach implies that each asset held by the Pond should be linked to an app that keeps its weight information written in local state.

A consecuence of such approach would be having to update each assets app upon liquidity commiting.

## Helpers

Some interfaces (additional contracts) the Pond may use:

- `spot_price_calculator`: Calculates spot price for a pair of assets a trader is willing to swap.
- `balancer`: Everything related to weight balancing after liquidity commiting.
  - `update_trigger`: Gets called after a commit is performed at a certain time (how to time it?)
  - `weights_calculator`: Recalculates all the weights in the Pond based on incoming liquidity.
  - `weight_updater`: Updates all weights based on `weights_calculator`

## Requirements

1. Pond Contract should be written using PyTEAL or Reach.
2. Pond should only be called from a txn group that includes an App call to the Validator.
3. The App Call transaction for calling the Pond should be `NoOp`
4. When called, it most receive a string indicating the **action** as first txn arg:
   1. `'commit'`
   2. `'redeem'`
   3. `'swap'`
5. Other txn args will vary according to the action being validated.
6. After comparing the first txn arg with the available values, the code should be branched (`bnz`) accordingly.

   Example (pseudocode):

   ```
   txn appArgs[0] == 'bootstrap'
   bnz bootstrap
   ...
   ...
   bootstrap:
   	// action specific validations and subroutines
   ```

7. After branching, the required subroutine(s) for the current action should be called.
