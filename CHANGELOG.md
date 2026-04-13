## [1.7.3](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.7.2...v1.7.3) (2026-04-13)


### Bug Fixes

* **abr:** return unpaid invoices in FIFO order for partial allocation ([4b7d936](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/4b7d936b96dafe479c21e8fc44b7d9786eca4633))

## [1.7.2](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.7.1...v1.7.2) (2026-04-13)


### Bug Fixes

* **abr:** cap per-row allocation at bank transaction remaining in UI ([a7eb5a9](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/a7eb5a9196a8262d9c09b2af98ede07cd0e87c95))
* **abr:** collapse PE references to target invoice on partial allocation ([43c9041](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/43c9041d692eceb8ab910c1980c0e1062293a15d))
* **abr:** harden partial allocation cascade against silent imbalance ([956cea8](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/956cea81869be82899b0ee7ffcf8e97a7653ba16))
* **abr:** respect validate_selection_against_unallocated_amount in UI ([29a85d2](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/29a85d23a1dcdb7d1515f19b7ed3ea0e7302272a))
* **abr:** show raw selection total with cap note in reconcile dialog ([f41015b](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/f41015bce83d0acabbfad34b767c48a3748c5cb1))

## [1.7.1](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.7.0...v1.7.1) (2026-03-30)


### Bug Fixes

* exclude ABR Bank Rule from company transaction deletion ([c0c3389](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/c0c33894e3b3ffdb62d93c7e0174a5be3a55f4df))

# [1.7.0](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.6.0...v1.7.0) (2026-03-29)


### Bug Fixes

* default Particulars condition to Equals instead of Contains ([78eabb4](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/78eabb4e83c8ec8a5f21dbe38d833133e1917aa8))


### Features

* inline save-as-rule opt-in, deposit/withdrawal condition, bank party column ([0d70642](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/0d706426342ee94bc29ad4824f7d09ed9913eb40))
* prompt to save bank rule after manual voucher creation ([8eb209f](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/8eb209f1764ea47d1f016e4c53e2eaa803987240))

# [1.6.0](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.5.0...v1.6.0) (2026-03-29)


### Features

* add Accounts User role to Reconciliation Tool and Settings ([eda983d](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/eda983d61d583f1f82476ea9641750117b60f2b2))

# [1.5.0](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.4.2...v1.5.0) (2026-03-28)


### Features

* add Accounts Manager and Accounts User roles to Bank Statement Importer ([173b3bb](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/173b3bbe04087bad29035157d4713af71ed31b13))
* add create permission for ABR Bank Rule to Accounts User role ([d6b9082](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/d6b9082f549c91211960220283752b62e4c51378))

## [1.4.2](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.4.1...v1.4.2) (2026-03-26)


### Bug Fixes

* **bank-rule:** fallback to transaction name when reference_number is empty ([f920537](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/f920537829dc9d1932b99ae9d907d306eff33b0b))

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
