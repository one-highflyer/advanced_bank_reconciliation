import frappe from '../frappe';

export interface PaymentEntry {
    doctype: string;
    name: string;
    reference_date: string;
    remaining_amount: number;
    reference_number: string;
    party: string;
    currency: string;
}

export interface PaymentEntryFilters {
    bankTransactionName: string;
    documentTypes: string[];
    fromDate: string;
    toDate: string;
    filterByReferenceDate?: 0 | 1;
    fromReferenceDate?: string;
    toReferenceDate?: string;
    exactMatch?: boolean;
}

/**
 * Get linked payment entries for bank transaction reconciliation
 */
export async function getLinkedPaymentEntries(
    filters: PaymentEntryFilters
): Promise<PaymentEntry[]> {
    try {
        const response = await frappe
            .call()
            .get('advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.get_linked_payments', {
                bank_transaction_name: filters.bankTransactionName,
                document_types: filters.documentTypes,
                from_date: filters.fromDate,
                to_date: filters.toDate,
                filter_by_reference_date: filters.filterByReferenceDate || 0,
                from_reference_date: filters.fromReferenceDate,
                to_reference_date: filters.toReferenceDate,
            });

        // Transform the response to match our interface
        const data = response.message || [];
        return data.map((row: unknown[]) => ({
            doctype: row[1], // Document Type
            name: row[2], // Document Name
            reference_date: row[5] || row[8], // Reference Date (fallback to posting date)
            remaining_amount: row[3], // Remaining Amount
            reference_number: row[4], // Reference Number
            party: row[6], // Party
            currency: row[9], // Currency
        }));
    } catch (err) {
        console.error('Error getting linked payment entries:', err);
        throw err;
    }
}

/**
 * Get available document types for bank reconciliation
 */
export async function getDocumentTypesForReconciliation(): Promise<string[]> {
    try {
        const response = await frappe
            .call()
            .get('advanced_bank_reconciliation.advanced_bank_reconciliation.doctype.advance_bank_reconciliation_tool.advance_bank_reconciliation_tool.get_doctypes_for_bank_reconciliation');

        return response.message || [];
    } catch (err) {
        console.error('Error getting document types for reconciliation:', err);
        throw err;
    }
} 