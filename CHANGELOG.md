## [1.9.2](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.9.1...v1.9.2) (2026-06-27)


### Bug Fixes

* **bank-rec:** address dimension and match search review ([29562f5](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/29562f546d3ef8e9a9c14389087abd28eb45cbf7))
* **bank-rec:** preserve bank coding redirect state ([fcac044](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/fcac04446f51fd644986e6c1d2a706d7c1b6d894))
* **bank-rec:** show dimensions and search match candidates ([22fca9d](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/22fca9d6cdf4bfd9652213399499ea745fcad1d9))
* **bank-rec:** use bank coding label ([2bfd2f0](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/2bfd2f01609bf5c73af909dbb01128213b6c3785))

## [1.9.1](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.9.0...v1.9.1) (2026-06-24)


### Bug Fixes

* **bank-rec:** align reconciliation UI to NexWave cyan/slate design system ([a78c25c](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/a78c25c39f772d1ecbf095e76c8b60f9d156c5d4))

# [1.9.0](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.8.1...v1.9.0) (2026-06-23)


### Bug Fixes

* **bank-rec:** clear cash coding dirty state ([fc8381a](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/fc8381a1097cefa50a0d7d0fb03cd190b24aa80e))
* **bank-rec:** normalize account-only route state ([a884c73](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/a884c73a0be3aa7ea5022607630152d820a0408a))


### Features

* **bank-rec:** filter bank accounts by company ([fc9bed9](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/fc9bed9cd193b83b3aec0e9f00484252f3c219f9))

## [1.8.1](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.8.0...v1.8.1) (2026-06-23)


### Bug Fixes

* **bank-rec:** build route app during deployment ([b448e37](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/b448e3724654373123dce70deec1756f855532ba))

# [1.8.0](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.7.14...v1.8.0) (2026-06-23)


### Bug Fixes

* **bank-rec:** address PR review feedback ([7bd1ae2](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/7bd1ae2a432e3c62621190a07514c28891c0351d))
* **bank-rec:** cover review follow-ups ([8677b50](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/8677b50088756c405c7375c382b768e038a75739))
* **bank-rec:** format cash coding route title ([deaff68](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/deaff689441d2ecbee0fd04878aec04c105bc757))
* **bank-rec:** harden mutation guards ([ed3d30a](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/ed3d30a0ab630612faace26123c588dd96f7ab2e))
* **bank-rec:** isolate mutation guard checks ([ca8c256](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/ca8c25663dc788acaae149e7a28f12f0285f2740))


### Features

* add modern bank rec workspace ([7a4917f](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/7a4917ff6c1639e3feeb1c08141e6c63691c6eca))
* **bank-rec:** add route APIs and tests ([e055db0](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/e055db0f7cfe010cd86494c95df5e7538fb3885d))
* **bank-rec:** add Vue reconciliation app ([b69a6bb](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/b69a6bb8afbddc63f449e0245ab23d01517becbc))
* **bank-rec:** harden matched review workflow ([906deb4](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/906deb4c15aaf2f12fcee5e68fea79f88945a226))

## [1.7.14](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.7.13...v1.7.14) (2026-06-09)


### Bug Fixes

* handle stale optional bank statement mappings ([5b2aeb6](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/5b2aeb6063c3981ba289721ed91dbea255fa15c9))

## [1.7.13](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.7.12...v1.7.13) (2026-05-29)


### Bug Fixes

* allow party references in journal entry picker ([65d2927](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/65d29270c46390855006ef1c3a04eb2cd8e6ebe1))
* guard journal entry reference query patch ([a9bc18f](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/a9bc18f028b6145b3c0dd4533b5b28a24063bb68))

## [1.7.12](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.7.11...v1.7.12) (2026-05-26)


### Bug Fixes

* **abr:** use currency-precision coverage check for clearance gating ([30c02e9](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/30c02e9f34c4ee4ab778e5aff5e4ccd44148d0f7))

## [1.7.11](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.7.10...v1.7.11) (2026-05-25)


### Bug Fixes

* **abr:** defer invoice clearance until cumulative match, plus credit-card account flip ([9d8c6b9](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/9d8c6b9b0d8742f45237c09b08df25b9edbb03fc))
* **abr:** re-evaluate PI/SI clearance on Bank Transaction cancel ([0342f82](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/0342f8271b1b47ae2066ca15856218bf24cb073d))
* **abr:** treat should_clear_invoice as coverage check, not equality ([eaee48f](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/eaee48f961e58310044db67d651ec23058633a04))

## [1.7.10](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.7.9...v1.7.10) (2026-05-25)


### Bug Fixes

* **abr:** filter unpaid invoice matching queries by bank account's company ([7db4045](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/7db40456793c6bc768525cb8b74247fe0b9b6223))

## [1.7.9](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.7.8...v1.7.9) (2026-05-24)


### Bug Fixes

* **bank-statement-importer:** handle stale and missing column mappings ([e50a4c4](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/e50a4c4f2bea56c66ec0637b62013be93e068d27)), closes [#822](https://github.com/one-highflyer/advanced_bank_reconciliation/issues/822)

## [1.7.8](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.7.7...v1.7.8) (2026-05-21)


### Bug Fixes

* **abr:** mirror magnitude comparison in bulk recon dialog (JS) ([cea1bee](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/cea1bee521fe5a28ee8f040c25f503a631477571))
* **abr:** use magnitude comparison in bulk reconciliation preflight ([0d2fafe](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/0d2fafe9d127b1b0cfd27419ffa44232fc6add76))

## [1.7.7](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.7.6...v1.7.7) (2026-05-19)


### Bug Fixes

* **abr:** gate refund matching exact-match on negative sign ([88fe93a](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/88fe93ad11876a18c7ac2ca060fd202861ba6679))
* **abr:** show paid refund invoices in bank rec and fix unallocated amount ([221cdd5](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/221cdd502790e687d9fe7577fe1ecb56346196e9))

## [1.7.6](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.7.5...v1.7.6) (2026-04-28)


### Bug Fixes

* **abr:** add FIFO toggle for unpaid invoices and cap matching dialog table ([5b296b0](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/5b296b05229a153581cfdf35e0bb89c8c9965a16))
* **abr:** gate compact matching vouchers table behind setting ([cd38e78](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/cd38e78ee6a3adedeea8b9658db2284bbb8cab25))

## [1.7.5](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.7.4...v1.7.5) (2026-04-23)


### Bug Fixes

* **abr:** prevent bulk reconcile failure on Bank Transactions with no reference ([857ee13](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/857ee13ae1baee1974089ab8370ca63406afb771))

## [1.7.4](https://github.com/one-highflyer/advanced_bank_reconciliation/compare/v1.7.3...v1.7.4) (2026-04-15)


### Bug Fixes

* **abr:** round allocated_amount to field precision in bulk reconcile ([3c115ee](https://github.com/one-highflyer/advanced_bank_reconciliation/commit/3c115ee056fed486f75f22d212baa7fb3bab6823))

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
