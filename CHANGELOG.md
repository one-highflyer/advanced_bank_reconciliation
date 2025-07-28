# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2025-01-28

### Added
- Date filters for unpaid invoice matching queries
  - Modified `get_unpaid_si_matching_query()` to accept `from_date` and `to_date` parameters
  - Modified `get_unpaid_pi_matching_query()` to accept `from_date` and `to_date` parameters
  - Supports all date combinations: both dates, from_date only, to_date only
  - Maintains backward compatibility when no date filters are provided
- Comprehensive support for invoice returns in bank reconciliation
  - Enable matching of negative sales invoices (returns) with withdrawal transactions
  - Enable matching of negative purchase invoices (returns) with deposit transactions
  - Improved ranking system for exact amount matches
  - Support for negative allocated amounts in payment entry creation

### Changed
- Enhanced clearance validation to support both positive and negative transaction scenarios
- Improved logging for better debugging and monitoring of reconciliation processes

### Fixed
- Payment entry creation now properly handles negative allocated amounts for return transactions

## [0.1.0] - 2025-01-27

### Added
- Customer group filtering in payment entries dialog
- Conditional display of customer group filter for customer-related document types

### Changed
- Improved dialog layout with better column distribution

## [0.0.1] - Initial Release

### Added
- Initial implementation of Advanced Bank Reconciliation Tool
- Enhanced bank transaction validation and matching capabilities