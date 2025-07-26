/**
 * Bank Reconciliation API Service
 * Handles all API calls to the backend bank reconciliation endpoints
 * Following the same pattern as helpdesk app
 */

import { call, createResource, createListResource } from 'frappe-ui'

export const pendingTransactions = createResource({
  url: 'erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.get_bank_transactions',
  makeParams({ bank_account, from_date, to_date }) {
    return { bank_account, from_date, to_date }
  }
})

/**
 * Search for vouchers that can be matched against a bank transaction
 */
export async function searchVouchers({
  bankTransactionName,
  documentTypes,
  fromDate,
  toDate,
  exactMatch = false,
  filterByReferenceDate = false,
  fromReferenceDate = null,
  toReferenceDate = null
}) {
  return call(
    'advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.get_linked_payments',
    {
      bank_transaction_name: bankTransactionName,
      document_types: documentTypes,
      from_date: fromDate,
      to_date: toDate,
      filter_by_reference_date: filterByReferenceDate,
      from_reference_date: fromReferenceDate,
      to_reference_date: toReferenceDate,
      exact_match: exactMatch
    }
  )
}

/**
 * Get linked vouchers for a bank transaction (legacy function - use searchVouchers instead)
 * @param {Object} args - Arguments for voucher search
 * @returns {Promise<Object>} Object containing vouchers by type
 */
export async function getLinkedVouchers(args) {
  return call({
    method: 'advanced_bank_reconciliation.advance_bank_reconciliation_tool.get_linked_payments',
    args
  }).then(r => r.message || { payments: [], journals: [], invoices: [] })
}

/**
 * Create a resource for linked vouchers
 */
export const linkedVouchers = createResource({
  url: 'advanced_bank_reconciliation.advance_bank_reconciliation_tool.get_linked_payments',
  cache: ['LinkedVouchers'],
  makeParams(args) {
    return args
  },
  validate(args) {
    if (!args.bank_transaction_name) throw 'Bank transaction name is required'
  }
})

/**
 * Reconcile vouchers with a bank transaction
 * @param {string} bankTransactionName - Name of the bank transaction
 * @param {Array} vouchers - Array of vouchers to reconcile
 * @returns {Promise<Object>} Reconciliation result
 */
export async function reconcileVouchers(bankTransactionName, vouchers) {
  return call({
    method: 'advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.reconcile_vouchers',
    args: {
      bank_transaction_name: bankTransactionName,
      vouchers: vouchers
    }
  }).then(r => r.message)
}

/**
 * Create a resource for reconciliation
 */
export const reconcileVouchersResource = createResource({
  url: 'advanced_bank_reconciliation.advance_bank_reconciliation_tool.reconcile_vouchers',
  auto: false,
  makeParams({ bankTransactionName, vouchers }) {
    return {
      bank_transaction_name: bankTransactionName,
      vouchers: vouchers
    }
  },
  validate({ bankTransactionName, vouchers }) {
    if (!bankTransactionName) throw 'Bank transaction name is required'
    if (!vouchers || vouchers.length === 0) throw 'Vouchers are required'
  }
})

/**
 * Create payment entries for unpaid invoices
 * @param {string} bankTransactionName - Bank transaction name
 * @param {Array} invoices - Array of unpaid invoices
 * @param {boolean} autoReconcile - Whether to auto-reconcile after creation
 * @returns {Promise<Object>} Created payment entries result
 */
export async function createPaymentEntriesForInvoices(bankTransactionName, invoices, autoReconcile = false) {
  return call({
    method: 'advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.create_payment_entries_for_invoices',
    args: {
      bank_transaction_name: bankTransactionName,
      invoices: invoices,
      auto_reconcile: autoReconcile
    }
  }).then(r => r.message)
}

/**
 * Create a new payment entry for a bank transaction
 */
export async function createPaymentEntry({
  bankTransactionName,
  referenceNumber,
  referenceDate,
  partyType,
  party,
  postingDate,
  modeOfPayment,
  project = null,
  costCenter = null,
  allowEdit = false
}) {
  return call({
    method: 'advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.create_payment_entry_bts',
    args: {
      bank_transaction_name: bankTransactionName,
      reference_number: referenceNumber,
      reference_date: referenceDate,
      party_type: partyType,
      party: party,
      posting_date: postingDate,
      mode_of_payment: modeOfPayment,
      project: project,
      cost_center: costCenter,
      allow_edit: allowEdit
    }
  }).then(r => r.message)
}

/**
 * Create a resource for payment entry creation
 */
export const createPaymentEntryResource = createResource({
  url: 'advanced_bank_reconciliation.advance_bank_reconciliation_tool.create_payment_entry_bts',
  auto: false,
  makeParams(paymentData) {
    return paymentData
  },
  validate(paymentData) {
    if (!paymentData.payment_type) throw 'Payment type is required'
    if (!paymentData.party_type) throw 'Party type is required'
    if (!paymentData.party) throw 'Party is required'
    if (!paymentData.amount) throw 'Amount is required'
  }
})

/**
 * Create a new journal entry for a bank transaction
 */
export async function createJournalEntry({
  bankTransactionName,
  referenceNumber,
  referenceDate,
  partyType = null,
  party = null,
  postingDate,
  modeOfPayment = null,
  entryType,
  secondAccount,
  allowEdit = false
}) {
  return call({
    method: 'advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.create_journal_entry_bts',
    args: {
      bank_transaction_name: bankTransactionName,
      reference_number: referenceNumber,
      reference_date: referenceDate,
      party_type: partyType,
      party: party,
      posting_date: postingDate,
      mode_of_payment: modeOfPayment,
      entry_type: entryType,
      second_account: secondAccount,
      allow_edit: allowEdit
    }
  }).then(r => r.message)
}

/**
 * Create a resource for journal entry creation
 */
export const createJournalEntryResource = createResource({
  url: 'advanced_bank_reconciliation.advance_bank_reconciliation_tool.create_journal_entry_bts',
  auto: false,
  makeParams(journalData) {
    return journalData
  },
  validate(journalData) {
    if (!journalData.posting_date) throw 'Posting date is required'
    if (!journalData.accounts || journalData.accounts.length === 0) throw 'Accounts are required'
  }
})

/**
 * Update bank transaction details
 */
export async function updateBankTransaction({
  bankTransactionName,
  referenceNumber = null,
  partyType = null,
  party = null
}) {
  return call({
    method: 'erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.update_bank_transaction',
    args: {
      bank_transaction_name: bankTransactionName,
      reference_number: referenceNumber,
      party_type: partyType,
      party: party
    }
  }).then(r => r.message)
}

/**
 * Get available document types for bank reconciliation
 */
export async function getDocumentTypesForReconciliation() {
  return call({
    method: 'advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.get_doctypes_for_bank_reconciliation'
  }).then(r => r.message || [])
}

/**
 * Validate bank transactions
 * @param {Object} filters - Validation filters
 * @returns {Promise<Object>} Validation result
 */
export async function validateBankTransactions(filters) {
  return call({
    method: 'advanced_bank_reconciliation.advance_bank_reconciliation_tool.validate_bank_transactions',
    args: filters
  }).then(r => r.message)
}

/**
 * Create a resource for validation
 */
export const validateBankTransactionsResource = createResource({
  url: 'advanced_bank_reconciliation.advance_bank_reconciliation_tool.validate_bank_transactions',
  auto: false,
  makeParams(filters) {
    return filters
  }
})

/**
 * Batch validate unvalidated transactions
 * @param {Object} filters - Validation filters
 * @returns {Promise<Object>} Batch validation result
 */
export async function batchValidateUnvalidatedTransactions(filters) {
  return call({
    method: 'advanced_bank_reconciliation.advance_bank_reconciliation_tool.batch_validate_unvalidated_transactions',
    args: filters
  }).then(r => r.message)
}

/**
 * Validate a single bank transaction asynchronously
 * @param {string} transactionName - Name of the transaction to validate
 * @returns {Promise<Object>} Validation result
 */
export async function validateBankTransactionAsync(transactionName) {
  return call({
    method: 'advanced_bank_reconciliation.advance_bank_reconciliation_tool.validate_bank_transaction_async',
    args: { transaction_name: transactionName }
  }).then(r => r.message)
}

/**
 * Get account balance
 * @param {string} bank_account - Bank account name
 * @param {string} company - Company name
 * @param {string} till_date - Till date
 * @returns {Promise<Object>} Account balance information
 */
export async function getAccountBalance(bank_account: string, company: string, till_date: string) {
  return call('erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.get_account_balance', { bank_account, company, till_date })
}

/**
 * Auto reconcile vouchers
 * @param {Object} filters - Auto reconciliation filters
 * @returns {Promise<Object>} Auto reconciliation result
 */
export async function autoReconcileVouchers(filters) {
  return call({
    method: 'erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.auto_reconcile_vouchers',
    args: filters
  }).then(r => r.message)
}

/**
 * Upload bank statement
 * @param {Object} uploadData - Upload data
 * @returns {Promise<Object>} Upload result
 */
export async function uploadBankStatement(uploadData) {
  return call({
    method: 'erpnext.accounts.doctype.bank_statement_import.bank_statement_import.upload_bank_statement',
    args: uploadData
  }).then(r => r.message)
}

/**
 * Get bank transaction details
 * @param {string} transactionName - Name of the transaction
 * @returns {Promise<Object>} Transaction details
 */
export async function getBankTransactionDetails(transactionName) {
  return call({
    method: 'frappe.client.get_value',
    args: {
      doctype: 'Bank Transaction',
      filters: { name: transactionName },
      fieldname: [
        'date',
        'deposit',
        'withdrawal',
        'currency',
        'description',
        'name',
        'bank_account',
        'company',
        'reference_number',
        'party_type',
        'party',
        'unallocated_amount',
        'allocated_amount',
        'transaction_type'
      ]
    }
  }).then(r => r.message)
}

/**
 * Create a resource for bank transaction details
 */
export const bankTransactionDetails = createResource({
  url: 'frappe.client.get_value',
  cache: ['BankTransactionDetails'],
  makeParams({ transactionName }) {
    return {
      doctype: 'Bank Transaction',
      filters: { name: transactionName },
      fieldname: ['*']
    }
  },
  validate({ transactionName }) {
    if (!transactionName) throw 'Transaction name is required'
  }
})

/**
 * Get companies list
 * @returns {Promise<Array>} Array of companies
 */
export async function getCompanies() {
  return call({
    method: 'frappe.client.get_list',
    args: {
      doctype: 'Company',
      fields: ['name', 'company_name'],
      order_by: 'name'
    }
  }).then(r => r.message || [])
}

/**
 * Create a resource for companies
 */
export const companies = createListResource({
  doctype: 'Company',
  fields: ['name', 'company_name'],
  order_by: 'name',
  auto: false
})

/**
 * Get bank accounts for a company
 * @param {string} company - Company name
 * @returns {Promise<Array>} Array of bank accounts
 */
export async function getBankAccounts(company) {
  return call({
    method: 'frappe.client.get_list',
    args: {
      doctype: 'Account',
      filters: {
        company: company,
        account_type: 'Bank',
        is_group: 0
      },
      fields: ['name', 'account_name', 'account', 'company'],
      order_by: 'account_name'
    }
  }).then(r => r.message || [])
}

/**
 * Create a resource for bank accounts
 */
export const bankAccounts = createListResource({
  doctype: 'Bank Account',
  fields: ['name', 'account_name', 'account', 'company'],
  order_by: 'account_name',
  auto: false,
  filters: {
    is_company_account: 1
  }
})

/**
 * Get reconciled transactions
 * @param filters - Filters for the transactions
 * @returns {Promise<Object>} Reconciled transactions
 */
export function getReconciledTransactions(filters: {
  bank_account: string
  from_date: string
  to_date: string,
  company: string
}) {
  return call('advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.get_reconciled_bank_transactions', filters)
}

/**
 * Get reconciliation report
 * @param {Object} filters - Report filters
 * @returns {Promise<Object>} Report data
 */
export async function getReconciliationReport(filters) {
  return call({
    method: 'advanced_bank_reconciliation.advance_bank_reconciliation_tool.get_reconciliation_report',
    args: filters
  }).then(r => r.message)
}

/**
 * Create a resource for reconciliation report
 */
export const reconciliationReport = createResource({
  url: 'advanced_bank_reconciliation.advance_bank_reconciliation_tool.get_reconciliation_report',
  auto: false,
  makeParams(filters) {
    return filters
  },
  validate(filters) {
    if (!filters.company) throw 'Company is required'
    if (!filters.bank_account) throw 'Bank account is required'
    if (!filters.from_date) throw 'From date is required'
    if (!filters.to_date) throw 'To date is required'
  }
})
