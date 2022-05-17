# <img src="logo.jpg" alt="KoiFi" height="128px">

# KoiFi Monorepo

[![Docs](https://img.shields.io/badge/docs-%F0%9F%93%84-blue)](https://docs.koifi.com/)
[![License](https://img.shields.io/badge/License-GPLv3-green.svg)](https://www.gnu.org/licenses/gpl-3.0)

This repository contains the KoiFi Protocol core smart contracts, including the `Vault` and standard Pools, along with their tests, configuration, and deployment information.

<!-- For a high-level introduction to KoiFi, see [Introducing KoiFi: Generalized AMMs]. -->

## Structure

This is a Yarn 2 monorepo, with the packages meant to be published in the [`pkg`](./pkg) directory. Newly developed packages may not be published yet.

Active development occurs in this repository, which means some contracts in it might not be production-ready. Proceed with caution.

### Packages

- [`deployments`](./pkg/deployments): addresses and ABIs of all KoiFi deployed contracts, for mainnet and testnet.
- [`vault`](./pkg/vault): the [`Vault`](./pkg/vault/contracts/Vault.teal) contract and all core interfaces, including [`IVault`](./pkg/vault/contracts/interfaces/IVault.teal) and the Pool interfaces: [`IBasePool`](./pkg/vault/contracts/interfaces/IBasePool.teal), [`IGeneralPool`](./pkg/vault/contracts/interfaces/IGeneralPool.sol) and [`IMinimalSwapInfoPool`](./pkg/vault/contracts/interfaces/IMinimalSwapInfoPool.teal).
- [`pool-weighted`](./pkg/pool-weighted): the [`WeightedPool`](./pkg/pool-weighted/contracts/WeightedPool.teal) and [`WeightedPool2Tokens`](./pkg/pool-weighted/contracts/WeightedPool2Tokens.teal) contracts, along with their associated factories.
<!-- - [`pool-utils`](./pkg/pool-utils): Solidity utilities used to develop Pool contracts.
- [`solidity-utils`](./pkg/solidity-utils): miscellaneous Solidity helpers and utilities used in many different contracts.
- [`standalone-utils`](./pkg/standalone-utils): miscellaneous standalone utility contracts. -->

## Build and Test

On the project root, run:

```bash
$ yarn # install all dependencies
$ yarn build # compile all contracts
$ yarn test # run all tests
```

This will run all tests in parallel. To run a single workspace's tests, run `yarn test` from within that workspace's directory.

You can see a sample report of a test run [here](./audits/test-report.md).

## Security

Multiple independent reviews and audits will be performed. The latest reports from these engagements will be located in the [`audits`](./audits) directory.

<!-- Bug bounties apply to most of the smart contracts hosted in this repository: head to [KoiFi Bug Bounties](https://docs.koifi.com/core-concepts/security/bug-bounties) to learn more. -->

<!-- All core smart contracts are immutable, and cannot be upgraded. See page 6 of the [Trail of Bits audit](https://github.com/balancer-labs/balancer-v2-monorepo/blob/master/audits/trail-of-bits/2021-04-05.pdf): -->

<!-- > Upgradeability | Not Applicable. The system cannot be upgraded. -->

## Licensing

Most of the source code is licensed under the GNU General Public License Version 3 (GPL v3): see [`LICENSE`](./LICENSE).

### Exceptions

<!-- - All files in the `openzeppelin` directory of the [`v2-solidity-utils`](./pkg/solidity-utils) package are based on the [OpenZeppelin Contracts](https://github.com/OpenZeppelin/openzeppelin-contracts) library, and as such are licensed under the MIT License: see [LICENSE](./pkg/solidity-utils/contracts/openzeppelin/LICENSE).
- The `LogExpMath` contract from the [`v2-solidity-utils`](./pkg/solidity-utils) package is licensed under the MIT License. -->
- All other files, including tests and the [`pvt`](./pvt) directory are unlicensed.
