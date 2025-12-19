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
