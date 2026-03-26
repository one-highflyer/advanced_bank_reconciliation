## [1.4.1](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.4.0...v1.4.1) (2026-03-26)


### Bug Fixes

* **bank-rec:** add Employee as JE Account reference_type option ([a19d635](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/a19d63590ab9fb0726b171116617244516f297b9))

# [1.4.0](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.3.0...v1.4.0) (2026-03-23)


### Bug Fixes

* **bank-rec:** resolve JE party lookup, BSI company sync, and dimension filters ([bd812b9](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/bd812b95c7dde2c47f53de5f7172372664709707))


### Features

* **bank-rec:** improve ABR tool UX for bank reconciliation workflow ([cc4d3ac](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/cc4d3aca418ed92f66ff2d36ec320498c16b327f)), closes [#63](https://github.com/one-highflyer/advanced_bank_reconciliation/issues/63)

# [1.3.0](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.2.1...v1.3.0) (2026-03-17)


### Bug Fixes

* **bank-rec:** skip cancellation of documents still allocated to other bank transactions ([a183fc1](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/a183fc1a05847f23f16ad28ebda279362763fa6e))


### Features

* **bank-rec:** add Unreconcile button for matched transactions ([6e18fed](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/6e18fede625958c85392da9143740e7acd091778)), closes [#59](https://github.com/one-highflyer/advanced_bank_reconciliation/issues/59)

## [1.2.1](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.2.0...v1.2.1) (2026-03-14)


### Bug Fixes

* **bank-rules:** add traceability and accounting dimensions support ([2f7727d](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/2f7727d5bccc87084c766f08ad38c54a72e58c0d)), closes [#56](https://github.com/one-highflyer/advanced_bank_reconciliation/issues/56)
* **setup:** sync existing accounting dimensions to ABR Bank Rule on migrate ([40620c0](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/40620c0e662fae34e6714474edbb8eacaefea3a7))

# [1.2.0](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.1.3...v1.2.0) (2026-03-04)


### Features

* **bank-rules:** store party as reference on non-receivable/payable JE accounts ([6817385](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/681738566ad9f102a3c6cadfec76a0c83555218b))

## [1.1.3](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.1.2...v1.1.3) (2026-03-03)


### Bug Fixes

* **bank-rules:** fall back to transaction name when reference number is empty ([23ea250](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/23ea2508cf7358ada29dbc703fbe9b4011a825c5))

## [1.1.2](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.1.1...v1.1.2) (2026-03-03)


### Bug Fixes

* **bank-rules:** rename "Party Name" condition label to "Other Party" ([96001c1](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/96001c149518f71f6f0b2b843d469aeb6133369f))

## [1.1.1](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.1.0...v1.1.1) (2026-03-03)


### Bug Fixes

* **bank-importer:** address PR review feedback ([6630d3b](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/6630d3b81be33da6ca819f5f8173b3d06b9eee48))
* **bank-importer:** improve Code field import and bank mapping save reliability ([9912776](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/9912776580a0c55f6abd69d631ef2817c92a7a55))

# [1.1.0](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.0.1...v1.1.0) (2026-02-18)


### Bug Fixes

* **bank-rules:** harden validation, error handling, and condition evaluation ([435ebff](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/435ebffd1941869f0d1fa3515eb3e15eb4898b3c))


### Features

* **bank-rules:** add ABR Bank Rules for automatic transaction coding ([791c8f2](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/791c8f214a0be38175c415a1551b0bc6ce3b008a)), closes [#49](https://github.com/one-highflyer/advanced_bank_reconciliation/issues/49)

## [1.0.1](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.0.0...v1.0.1) (2026-01-01)


### Bug Fixes

* handle multi-currency in create_payment_entry_bts ([e06260f](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/e06260f908fb91f078ec6d757352dedbf83c9607))

# 1.0.0 (2025-12-19)


### Bug Fixes

* improve amount field calculations in get_pe_matching_query for accurate transaction handling ([c2d9207](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/c2d92072cc9d7ce10af6c9f4abc79e0cb5deb120))
* Update row data retrieval in dialog manager for selected transactions ([37156be](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/37156be36f1f9f56aa524264674347e84b47c93d))


### Features

* Add comprehensive support for invoice returns in bank reconciliation ([4083b53](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/4083b53b640a9387a993e8c7b882e30756821e7e))
* Add customer group filtering to bank reconciliation payment entries ([ab5474e](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/ab5474e33d30836d2b31f74526044850028d1576))
* add Particulars and Bank Party Name columns to bank transactions table ([4b3391b](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/4b3391bf298296f23d4cd4383a195d61f6ccee0d))
* Add party name to reconciliation queries and UI ([5794184](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/57941849b278aa66898269f62822561025c44cf1))
* add semantic release automation ([cc91650](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/cc91650bd86e28ff7a0855efe1e4f047baf9bcbb))
* Implement bulk bank reconciliation with background jobs ([292ca90](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/292ca90edf234259dd69fa09c456a282005fcfee))
* Initialize App ([1e71fc2](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/1e71fc24a48194ada555b4c752f70b2c12cb7f09))

# Changelog

## [1.0.0](https://github.com/one-highflyer/advanced_bank_reconciliation/releases/tag/v1.0.0) (2025-12-19)

### Features

* Initial release of Advanced Bank Reconciliation Tool
* Bank statement importer with flexible date format support and field mapping
* Multi-currency bank reconciliation with exchange rate handling
* Bulk bank reconciliation with background job processing
* Real-time progress tracking via WebSocket (frappe.realtime)
* Hook-based extensible filter system for customizations
* Invoice returns support (negative sales/purchase invoices matching)
* Customer group filtering in payment entries dialog
* Party name display in reconciliation queries and UI
* Particulars and Bank Party Name columns in bank transactions table
* Date filters for unpaid invoice matching queries
* Payment entry and journal entry creation from bank transactions
* Background/synchronous execution modes (configurable via settings)
* Rank currency-matched invoices higher in reconciliation
* Support for reconciling unpaid invoices with bank transactions
* Journal entry query enhancement with party name for clarity

### Bug Fixes

* Multi-currency amount matching and exchange rate conversion
* Bank transaction validation for foreign currency payment entries
* CSV import for amounts with comma separators
* Memory leak and lock release in bulk reconciliation
* Performance with Select All on large datasets
* Bank field showing "[object Object]" during statement upload
* Allocation validation on advance bank reconciliation tool
* Amount comparison inconsistency in reconciliation
* Row data retrieval in dialog manager for selected transactions
