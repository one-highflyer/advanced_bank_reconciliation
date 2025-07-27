import { useState, useEffect } from 'react';
import { getLinkedPaymentEntries, type PaymentEntry } from '../../../lib/services/paymentEntryService';
import type { BankTransaction } from '../../../lib/services/bankReconciliationService';
import type { MatchedTransaction } from '@/lib/types';
import { DocumentList } from '@/components/DocumentList';

interface PaymentEntryTabProps {
    bankAccount: string;
    fromDate: string;
    toDate: string;
    selectedTransaction: BankTransaction;
    onTransactionSelect: (transaction: MatchedTransaction) => void;
    selectedTransactions: MatchedTransaction[];
    isTransactionSelected: (doctype: string, docname: string) => boolean;
}

export function PaymentEntryTab({ 
    fromDate, 
    toDate, 
    selectedTransaction, 
    onTransactionSelect,
    isTransactionSelected
}: PaymentEntryTabProps) {
    const [paymentEntries, setPaymentEntries] = useState<PaymentEntry[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        console.log("Loading payment entries for transaction", selectedTransaction.name, fromDate, toDate);
        loadPaymentEntries();
    }, [selectedTransaction.name, fromDate, toDate]);

    const loadPaymentEntries = async () => {
        setLoading(true);
        setError(null);

        try {
            const data = await getLinkedPaymentEntries({
                bankTransactionName: selectedTransaction.name,
                documentTypes: ['payment_entry'],
                fromDate,
                toDate,
            });
            setPaymentEntries(data);
        } catch (err) {
            console.error('Error loading payment entries:', err);
            setError('Failed to load payment entries');
        } finally {
            setLoading(false);
        }
    };

    const handleEntrySelect = (entryName: string) => {
        const selectedEntry = paymentEntries.find(entry => entry.name === entryName);
        if (selectedEntry) {
            const transactionData: MatchedTransaction = {
                doctype: selectedEntry.doctype,
                docname: selectedEntry.name,
                reference_date: selectedEntry.reference_date,
                remaining_amount: selectedEntry.paid_amount,
                reference_number: selectedEntry.reference_number,
                party: selectedEntry.party,
                currency: selectedEntry.currency,
            };
            onTransactionSelect(transactionData);
        }
    };

    const handleSelectAll = (checked: boolean) => {
        if (checked) {
            // Select all unselected entries
            paymentEntries.forEach(entry => {
                if (!isTransactionSelected(entry.doctype, entry.name)) {
                    handleEntrySelect(entry.name);
                }
            });
        } else {
            // Deselect all selected entries
            paymentEntries.forEach(entry => {
                if (isTransactionSelected(entry.doctype, entry.name)) {
                    handleEntrySelect(entry.name);
                }
            });
        }
    };

    return (
        <DocumentList
            documents={paymentEntries}
            documentType="payment entries"
            loading={loading}
            error={error}
            isTransactionSelected={isTransactionSelected}
            onDocumentSelect={handleEntrySelect}
            onSelectAll={handleSelectAll}
            onRetry={loadPaymentEntries}
        />
    );
} 