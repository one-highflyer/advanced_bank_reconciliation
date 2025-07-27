import { useState, useEffect } from 'react';
import { getLinkedPaymentEntries, type PaymentEntry } from '../../../lib/services/paymentEntryService';
import type { BankTransaction } from '../../../lib/services/bankReconciliationService';
import type { MatchedTransaction } from '@/lib/types';
import { DocumentList } from '@/components/DocumentList';

interface JournalEntryTabProps {
    bankAccount: string;
    fromDate: string;
    toDate: string;
    selectedTransaction: BankTransaction;
    onTransactionSelect: (transaction: MatchedTransaction) => void;
    isTransactionSelected: (doctype: string, docname: string) => boolean;
}

export function JournalEntryTab({ 
    fromDate, 
    toDate, 
    selectedTransaction, 
    onTransactionSelect,
    isTransactionSelected
}: JournalEntryTabProps) {
    const [journalEntries, setJournalEntries] = useState<PaymentEntry[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        console.log("Loading journal entries for transaction", selectedTransaction.name, fromDate, toDate);
        loadJournalEntries();
    }, [selectedTransaction.name, fromDate, toDate]);

    const loadJournalEntries = async () => {
        setLoading(true);
        setError(null);

        try {
            const data = await getLinkedPaymentEntries({
                bankTransactionName: selectedTransaction.name,
                documentTypes: ['journal_entry'],
                fromDate,
                toDate,
            });
            setJournalEntries(data);
        } catch (err) {
            console.error('Error loading journal entries:', err);
            setError('Failed to load journal entries');
        } finally {
            setLoading(false);
        }
    };

    const handleEntrySelect = (entryName: string) => {
        const selectedEntry = journalEntries.find(entry => entry.name === entryName);
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
            journalEntries.forEach(entry => {
                if (!isTransactionSelected(entry.doctype, entry.name)) {
                    handleEntrySelect(entry.name);
                }
            });
        } else {
            // Deselect all selected entries
            journalEntries.forEach(entry => {
                if (isTransactionSelected(entry.doctype, entry.name)) {
                    handleEntrySelect(entry.name);
                }
            });
        }
    };

    return (
        <DocumentList
            documents={journalEntries}
            documentType="journal entries"
            loading={loading}
            error={error}
            isTransactionSelected={isTransactionSelected}
            onDocumentSelect={handleEntrySelect}
            onSelectAll={handleSelectAll}
            onRetry={loadJournalEntries}
        />
    );
} 