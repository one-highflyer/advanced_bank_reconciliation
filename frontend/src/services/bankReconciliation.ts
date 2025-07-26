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
 * Get linked vouchers for a bank transaction
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
    method: 'advanced_bank_reconciliation.advance_bank_reconciliation_tool.reconcile_vouchers',
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
 * @param {Array} invoices - Array of unpaid invoices
 * @returns {Promise<Array>} Array of created payment entries
 */
export async function createPaymentEntriesForInvoices(invoices) {
  return call({
    method: 'advanced_bank_reconciliation.advance_bank_reconciliation_tool.create_payment_entries_for_invoices',
    args: { invoices }
  }).then(r => r.message || [])
}

/**
 * Create a new payment entry
 * @param {Object} paymentData - Payment entry data
 * @returns {Promise<Object>} Created payment entry
 */
export async function createPaymentEntry(paymentData) {
  return call({
    method: 'advanced_bank_reconciliation.advance_bank_reconciliation_tool.create_payment_entry_bts',
    args: paymentData
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
 * Create a new journal entry
 * @param {Object} journalData - Journal entry data
 * @returns {Promise<Object>} Created journal entry
 */
export async function createJournalEntry(journalData) {
  return call({
    method: 'advanced_bank_reconciliation.advance_bank_reconciliation_tool.create_journal_entry_bts',
    args: journalData
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
      fieldname: ['*']
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
