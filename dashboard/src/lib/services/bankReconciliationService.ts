import frappe from '../frappe';

export interface BankTransaction {
  name: string;
  date: string;
  party_type: string;
  party: string;
  description: string;
  deposit: number;
  withdrawal: number;
  unallocated_amount: number;
  reference_number: string;
  currency: string;
}

export interface ReconciledTransaction {
  name: string;
  date: string;
  deposit: number;
  withdrawal: number;
  payment_document: string;
  payment_entry: string;
  allocated_amount: number;
  currency: string;
}

export interface AccountBalance {
  balance: number;
  currency: string;
}

export interface BankAccount {
  name: string;
  account: string;
  bank: string;
  company: string;
}

export interface Company {
  name: string;
  company_name: string;
  is_group: boolean;
}

/**
 * Get bank transactions for reconciliation
 */
export async function getBankTransactions(
  bankAccount: string,
  fromDate: string,
  toDate: string
): Promise<BankTransaction[]> {
  try {
    const response = await frappe
      .call()
      .get('erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.get_bank_transactions', {
        bank_account: bankAccount,
        from_date: fromDate,
        to_date: toDate,
      });

    return response.message || [];
  } catch (err) {
    console.error('Error getting bank transactions:', err);
    throw err;
  }
}

/**
 * Get reconciled bank transactions
 */
export async function getReconciledBankTransactions(
  bankAccount: string,
  fromDate: string,
  toDate: string
): Promise<ReconciledTransaction[]> {
  try {
    const response = await frappe
      .call()
      .get('advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.get_reconciled_bank_transactions', {
        bank_account: bankAccount,
        from_date: fromDate,
        to_date: toDate,
      });

    return response.message || [];
  } catch (err) {
    console.error('Error getting reconciled bank transactions:', err);
    throw err;
  }
}

/**
 * Get account balance till a specific date
 */
export async function getAccountBalance(
  bankAccount: string,
  tillDate: string,
  company: string
): Promise<AccountBalance> {
  try {
    const response = await frappe
      .call()
      .get('erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.get_account_balance', {
        bank_account: bankAccount,
        till_date: tillDate,
        company: company,
      });

    return response.message || { balance: 0, currency: '' };
  } catch (err) {
    console.error('Error getting account balance:', err);
    throw err;
  }
}

/**
 * Validate bank transactions
 */
export async function validateBankTransactions(
  fromDate: string,
  toDate: string,
  company: string,
  bankAccount: string
): Promise<void> {
  try {
    await frappe
      .call()
      .post('advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.validate_bank_transactions', {
        from_date: fromDate,
        to_date: toDate,
        company: company,
        bank_account: bankAccount,
      });
  } catch (err) {
    console.error('Error validating bank transactions:', err);
    throw err;
  }
}

/**
 * Batch validate unvalidated transactions
 */
export async function batchValidateUnvalidatedTransactions(
  bankAccount: string,
  fromDate: string,
  toDate: string,
  limit: number = 100
): Promise<{ success: boolean; message: string }> {
  try {
    const response = await frappe
      .call()
      .post('advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.batch_validate_unvalidated_transactions', {
        bank_account: bankAccount,
        from_date: fromDate,
        to_date: toDate,
        limit: limit,
      });

    return response.message || { success: false, message: 'Failed to start batch validation' };
  } catch (err) {
    console.error('Error batch validating transactions:', err);
    throw err;
  }
}

/**
 * Create payment entries for unpaid invoices
 */
export async function createPaymentEntriesForInvoices(
  bankTransactionName: string,
  invoices: Array<{
    doctype: string;
    name: string;
    allocated_amount: number;
  }>,
  autoReconcile: boolean = false
): Promise<unknown> {
  try {
    const response = await frappe
      .call()
      .post('advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.create_payment_entries_for_invoices', {
        bank_transaction_name: bankTransactionName,
        invoices: invoices,
        auto_reconcile: autoReconcile,
      });

    return response.message;
  } catch (err) {
    console.error('Error creating payment entries for invoices:', err);
    throw err;
  }
}

/**
 * Reconcile vouchers with a bank transaction
 */
export async function reconcileVouchers(
  bankTransactionName: string,
  vouchers: Array<{
    payment_doctype: string;
    payment_name: string;
    amount: number;
  }>
): Promise<unknown> {
  try {
    const response = await frappe
      .call()
      .post('advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.reconcile_vouchers', {
        bank_transaction_name: bankTransactionName,
        vouchers: JSON.stringify(vouchers),
      });

    return response.message;
  } catch (err) {
    console.error('Error reconciling vouchers:', err);
    throw err;
  }
}

/**
 * Auto reconcile vouchers
 */
export async function autoReconcileVouchers(
  bankAccount: string,
  fromDate: string,
  toDate: string,
  filterByReferenceDate: boolean = false,
  fromReferenceDate?: string,
  toReferenceDate?: string
): Promise<void> {
  try {
    await frappe
      .call()
      .post('erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.auto_reconcile_vouchers', {
        bank_account: bankAccount,
        from_date: fromDate,
        to_date: toDate,
        filter_by_reference_date: filterByReferenceDate,
        from_reference_date: fromReferenceDate,
        to_reference_date: toReferenceDate,
      });
  } catch (err) {
    console.error('Error auto reconciling vouchers:', err);
    throw err;
  }
}

/**
 * Get bank accounts for a company
 */
export async function getBankAccounts(company: string): Promise<BankAccount[]> {
  try {
    const response = await frappe.db().getDocList('Bank Account', {
      filters: [
        ['company', '=', company],
        ['is_company_account', '=', 1],
      ],
      fields: ['name', 'account', 'bank', 'company'],
    });

    return response || [];
  } catch (err) {
    console.error('Error getting bank accounts:', err);
    throw err;
  }
}

export async function getCompanies(): Promise<Company[]> {
  try {
    const response = await frappe.db().getDocList('Company', {
      fields: ['name', 'company_name', 'is_group'],
      filters: [],
    });

    return response || [];
  } catch (err) {
    console.error('Error getting companies:', err);
    throw err;
  }
}