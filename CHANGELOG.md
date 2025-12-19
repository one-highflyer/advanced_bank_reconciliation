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
