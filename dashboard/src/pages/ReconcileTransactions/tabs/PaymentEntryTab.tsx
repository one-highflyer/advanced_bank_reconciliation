import { useState, useEffect } from 'react';
import { Checkbox } from '@/components/ui/checkbox';
import { formatCurrency } from '../../../lib/utils';
import { getLinkedPaymentEntries, type PaymentEntry } from '../../../lib/services/paymentEntryService';
import type { BankTransaction } from '../../../lib/services/bankReconciliationService';
import type { MatchedTransaction } from '@/lib/types';

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
                remaining_amount: selectedEntry.remaining_amount,
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

    // Check if all entries are selected
    const allSelected = paymentEntries.length > 0 && paymentEntries.every(entry => 
        isTransactionSelected(entry.doctype, entry.name)
    );

    if (loading) {
        return (
            <div className="space-y-4">
                <div className="flex justify-between items-center">
                    <h3 className="text-lg font-semibold">Payment Entries</h3>
                    <div className="text-sm text-muted-foreground">
                        Matching with transaction: {selectedTransaction.description}
                    </div>
                </div>
                <div className="flex items-center justify-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                    <span className="ml-2 text-muted-foreground">Loading payment entries...</span>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="space-y-4">
                <div className="flex justify-between items-center">
                    <h3 className="text-lg font-semibold">Payment Entries</h3>
                    <div className="text-sm text-muted-foreground">
                        Matching with transaction: {selectedTransaction.description}
                    </div>
                </div>
                <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-md">
                    <p className="text-destructive">{error}</p>
                    <button
                        onClick={loadPaymentEntries}
                        className="mt-2 px-4 py-2 bg-destructive text-destructive-foreground rounded hover:bg-destructive/90"
                    >
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold">Payment Entries</h3>
                <div className="text-sm text-muted-foreground">
                    Matching with transaction: {selectedTransaction.description}
                </div>
            </div>

            {paymentEntries.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                    <p>No payment entries found</p>
                    <p className="text-sm mt-1">
                        No matching payment entries were found for this transaction.
                    </p>
                </div>
            ) : (
                <div className="space-y-2">
                    {/* Select All Checkbox */}
                    <div className="flex items-center space-x-2 p-3 bg-muted rounded-lg">
                        <Checkbox
                            id="select-all"
                            checked={allSelected}
                            onCheckedChange={handleSelectAll}
                        />
                        <label htmlFor="select-all" className="text-sm font-medium">
                            Select All ({paymentEntries.length} entries)
                        </label>
                    </div>

                    {/* Payment Entries List */}
                    <div className="space-y-2">
                        {paymentEntries.map((entry) => (
                            <div
                                key={entry.name}
                                className="flex items-center space-x-3 p-3 border rounded-lg hover:bg-muted/50 transition-colors"
                            >
                                <Checkbox
                                    id={entry.name}
                                    checked={isTransactionSelected(entry.doctype, entry.name)}
                                    onCheckedChange={() => handleEntrySelect(entry.name)}
                                />
                                <div className="flex-1 min-w-0">
                                    <div className="flex justify-between items-start">
                                        <div className="flex-1 min-w-0">
                                            <div className="font-medium text-sm truncate">
                                                {entry.doctype}: {entry.name}
                                            </div>
                                            <div className="text-xs text-muted-foreground mt-1">
                                                <div>Reference: {entry.reference_number || 'N/A'}</div>
                                                <div>Party: {entry.party || 'N/A'}</div>
                                                <div>Date: {entry.reference_date}</div>
                                            </div>
                                        </div>
                                        <div className="text-right ml-4">
                                            <div className={`font-medium text-sm ${entry.remaining_amount > 0 ? 'text-green-600' : 'text-red-600'
                                                }`}>
                                                {formatCurrency(entry.remaining_amount, entry.currency)}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
} 