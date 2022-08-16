# Validator App Specification

## Overview

The validator app is crucial on every transaction group to validate general and action-specific parameters.

Among other params, it receives a string that indicates the intended action, that way, it executes the corresponding subroutine.

Subroutines cover action-specific validations and they may or may not call other interfaces.

## Interfaces (WIP)

Some interfaces (additional contracts) the Validator may use:

- `assetRegistration.teal`

## Inner transactions

Each subroutine within the validator may need to execute inner tnxs in order to call external interfaces.

## Requirements

1. Validator Contract should be written using PyTEAL or Reach.
2. Validator should only be called from a txn group.
3. The App Call transaction for calling the validator should be `Optin`
4. When called, it most receive a string indicating the **action** as first txn arg:
   1. `'bootstrap'`
   2. `'commit'`
   3. `'redeem'`
   4. `'swap'`
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

## Proposed tasks

1. Define/Diagram validations for **bootstrap**
2. Define/Diagram validations for **commit**
3. Define/Diagram validations for **redeem**
4. Define/Diagram validations for **swap**

---

6. Write **bootstrap** flow (What happens after branching)
   1. Tests
   2. PyTEAL
7. Write **commit** flow (What happens after branching)
   1. Tests
   2. PyTEAL
8. Write **redeem** flow (What happens after branching)
   1. Tests
   2. PyTEAL
9. Write **swap** flow (What happens after branching)
   1. Tests
   2. PyTEAL
10. PoC `assetRegistration` app
11. Put together Validator contract

## Notes

Flows will be heavily influenced by the overall txn group construction. Let's keep communicated.
