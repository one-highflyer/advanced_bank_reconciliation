import { useState, useEffect } from 'react';
import { getLinkedPaymentEntries, type PaymentEntry } from '../../../lib/services/paymentEntryService';
import type { BankTransaction } from '../../../lib/services/bankReconciliationService';
import type { MatchedTransaction } from '@/lib/types';
import { DocumentList } from '@/components/DocumentList';

interface SalesInvoiceTabProps {
    bankAccount: string;
    fromDate: string;
    toDate: string;
    selectedTransaction: BankTransaction;
    onTransactionSelect: (transaction: MatchedTransaction) => void;
    isTransactionSelected: (doctype: string, docname: string) => boolean;
}

export function SalesInvoiceTab({ 
    fromDate, 
    toDate, 
    selectedTransaction, 
    onTransactionSelect,
    isTransactionSelected
}: SalesInvoiceTabProps) {
    const [salesInvoices, setSalesInvoices] = useState<PaymentEntry[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        console.log("Loading sales invoices for transaction", selectedTransaction.name, fromDate, toDate);
        loadSalesInvoices();
    }, [selectedTransaction.name, fromDate, toDate]);

    const loadSalesInvoices = async () => {
        setLoading(true);
        setError(null);

        try {
            const data = await getLinkedPaymentEntries({
                bankTransactionName: selectedTransaction.name,
                documentTypes: ['sales_invoice'],
                fromDate,
                toDate,
            });
            setSalesInvoices(data);
        } catch (err) {
            console.error('Error loading sales invoices:', err);
            setError('Failed to load sales invoices');
        } finally {
            setLoading(false);
        }
    };

    const handleInvoiceSelect = (invoiceName: string) => {
        const selectedInvoice = salesInvoices.find(invoice => invoice.name === invoiceName);
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
            salesInvoices.forEach(invoice => {
                if (!isTransactionSelected(invoice.doctype, invoice.name)) {
                    handleInvoiceSelect(invoice.name);
                }
            });
        } else {
            // Deselect all selected invoices
            salesInvoices.forEach(invoice => {
                if (isTransactionSelected(invoice.doctype, invoice.name)) {
                    handleInvoiceSelect(invoice.name);
                }
            });
        }
    };

    return (
        <DocumentList
            documents={salesInvoices}
            documentType="sales invoices"
            loading={loading}
            error={error}
            isTransactionSelected={isTransactionSelected}
            onDocumentSelect={handleInvoiceSelect}
            onSelectAll={handleSelectAll}
            onRetry={loadSalesInvoices}
        />
    );
} 