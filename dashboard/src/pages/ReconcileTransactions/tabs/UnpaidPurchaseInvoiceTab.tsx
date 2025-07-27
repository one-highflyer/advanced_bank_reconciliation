import { useState, useEffect } from 'react';
import { getLinkedPaymentEntries, type PaymentEntry } from '../../../lib/services/paymentEntryService';
import type { BankTransaction } from '../../../lib/services/bankReconciliationService';
import type { MatchedTransaction } from '@/lib/types';
import { DocumentList } from '@/components/DocumentList';

interface UnpaidPurchaseInvoiceTabProps {
    bankAccount: string;
    fromDate: string;
    toDate: string;
    selectedTransaction: BankTransaction;
    onTransactionSelect: (transaction: MatchedTransaction) => void;
    isTransactionSelected: (doctype: string, docname: string) => boolean;
}

export function UnpaidPurchaseInvoiceTab({ 
    fromDate, 
    toDate, 
    selectedTransaction, 
    onTransactionSelect,
    isTransactionSelected
}: UnpaidPurchaseInvoiceTabProps) {
    const [unpaidPurchaseInvoices, setUnpaidPurchaseInvoices] = useState<PaymentEntry[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        console.log("Loading unpaid purchase invoices for transaction", selectedTransaction.name, fromDate, toDate);
        loadUnpaidPurchaseInvoices();
    }, [selectedTransaction.name, fromDate, toDate]);

    const loadUnpaidPurchaseInvoices = async () => {
        setLoading(true);
        setError(null);

        try {
            const data = await getLinkedPaymentEntries({
                bankTransactionName: selectedTransaction.name,
                documentTypes: ['unpaid_purchase_invoice'],
                fromDate,
                toDate,
            });
            setUnpaidPurchaseInvoices(data);
        } catch (err) {
            console.error('Error loading unpaid purchase invoices:', err);
            setError('Failed to load unpaid purchase invoices');
        } finally {
            setLoading(false);
        }
    };

    const handleInvoiceSelect = (invoiceName: string) => {
        const selectedInvoice = unpaidPurchaseInvoices.find(invoice => invoice.name === invoiceName);
        if (selectedInvoice) {
            const transactionData: MatchedTransaction = {
                doctype: selectedInvoice.doctype,
                docname: selectedInvoice.name,
                reference_date: selectedInvoice.reference_date,
                remaining_amount: selectedInvoice.paid_amount,
                reference_number: selectedInvoice.reference_number,
                party: selectedInvoice.party,
                currency: selectedInvoice.currency,
            };
            onTransactionSelect(transactionData);
        }
    };

    const handleSelectAll = (checked: boolean) => {
        if (checked) {
            // Select all unselected invoices
            unpaidPurchaseInvoices.forEach(invoice => {
                if (!isTransactionSelected(invoice.doctype, invoice.name)) {
                    handleInvoiceSelect(invoice.name);
                }
            });
        } else {
            // Deselect all selected invoices
            unpaidPurchaseInvoices.forEach(invoice => {
                if (isTransactionSelected(invoice.doctype, invoice.name)) {
                    handleInvoiceSelect(invoice.name);
                }
            });
        }
    };

    return (
        <DocumentList
            documents={unpaidPurchaseInvoices}
            documentType="unpaid purchase invoices"
            loading={loading}
            error={error}
            isTransactionSelected={isTransactionSelected}
            onDocumentSelect={handleInvoiceSelect}
            onSelectAll={handleSelectAll}
            onRetry={loadUnpaidPurchaseInvoices}
        />
    );
} 