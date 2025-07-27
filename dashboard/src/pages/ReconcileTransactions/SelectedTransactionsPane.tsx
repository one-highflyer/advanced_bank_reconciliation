import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { formatCurrency } from '@/lib/utils';
import type { MatchedTransaction } from '@/lib/types';
import type { BankTransaction } from '@/lib/services/bankReconciliationService';

interface SelectedTransactionsPaneProps {
    selectedTransactions: MatchedTransaction[];
    selectedBankTransaction: BankTransaction;
    onTransactionRemove: (doctype: string, docname: string) => void;
    onCancel: () => void;
    onSubmit: () => void;
}

export function SelectedTransactionsPane({
    selectedTransactions,
    selectedBankTransaction,
    onTransactionRemove,
    onCancel,
    onSubmit
}: SelectedTransactionsPaneProps) {
    // Calculate the sum of selected transaction amounts
    const selectedAmountSum = selectedTransactions.reduce((sum, transaction) => {
        return sum + transaction.remaining_amount;
    }, 0);

    // Get the bank transaction amount (deposit or withdrawal)
    const bankTransactionAmount = selectedBankTransaction.deposit || selectedBankTransaction.withdrawal || 0;
    const bankTransactionCurrency = selectedBankTransaction.currency;

    // Check if amounts match
    const amountsMatch = Math.abs(selectedAmountSum - bankTransactionAmount) < 0.01; // Allow for small rounding differences

    return (
        <div className="bg-card border rounded-lg p-4 h-fit">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Selected Transactions</h3>
                <span className="text-sm text-muted-foreground">
                    {selectedTransactions.length} selected
                </span>
            </div>

            {/* Amount Summary */}
            {selectedTransactions.length > 0 && (
                <div className="mb-4 p-3 bg-muted rounded-lg">
                    <div className="space-y-2">
                        <div className="flex justify-between items-center">
                            <span className="text-sm font-medium">Selected Amount:</span>
                            <span className={`font-semibold ${selectedAmountSum > 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {formatCurrency(selectedAmountSum, bankTransactionCurrency)}
                            </span>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="text-sm font-medium">Bank Transaction:</span>
                            <span className={`font-semibold ${bankTransactionAmount > 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {formatCurrency(bankTransactionAmount, bankTransactionCurrency)}
                            </span>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="text-sm font-medium">Difference:</span>
                            <span className={`font-semibold ${amountsMatch ? 'text-green-600' : 'text-red-600'}`}>
                                {formatCurrency(selectedAmountSum - bankTransactionAmount, bankTransactionCurrency)}
                            </span>
                        </div>
                        {amountsMatch && (
                            <div className="text-center py-2 bg-green-50 border border-green-200 rounded text-green-700 text-sm font-medium">
                                ✓ Amounts match perfectly!
                            </div>
                        )}
                        {!amountsMatch && selectedTransactions.length > 0 && (
                            <div className="text-center py-2 bg-yellow-50 border border-yellow-200 rounded text-yellow-700 text-sm font-medium">
                                ⚠ Amounts don't match
                            </div>
                        )}
                    </div>
                </div>
            )}

            {selectedTransactions.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                    <p>No transactions selected</p>
                    <p className="text-sm mt-1">
                        Select transactions from the tabs to match them
                    </p>
                </div>
            ) : (
                <div className="space-y-3">
                    {selectedTransactions.map((transaction) => (
                        <div
                            key={transaction.doctype + transaction.docname}
                            className="border rounded-lg p-3 bg-muted relative"
                        >
                            <button
                                onClick={() => onTransactionRemove(transaction.doctype, transaction.docname)}
                                className="absolute top-2 right-2 text-muted-foreground hover:text-foreground transition-colors"
                                title="Remove transaction"
                            >
                                <X size={16} />
                            </button>

                            <div className="pr-6">
                                <div className="font-medium text-sm">
                                    {transaction.doctype}: {transaction.docname}
                                </div>
                                <div className="text-xs text-muted-foreground mt-1">
                                    <div>Date: {transaction.reference_date}</div>
                                    <div>Reference: {transaction.reference_number || 'N/A'}</div>
                                    <div>Party: {transaction.party || 'N/A'}</div>
                                    <div className={`font-medium ${transaction.remaining_amount > 0 ? 'text-green-600' : 'text-red-600'}`}>
                                        Amount: {formatCurrency(transaction.remaining_amount, transaction.currency)}
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <div className="mt-4 pt-4 border-t space-y-2">
                {selectedTransactions.length > 0 && (
                    <Button
                        onClick={onSubmit}
                        className="w-full"
                        disabled={!amountsMatch}
                        title={!amountsMatch ? "Amounts must match to submit reconciliation" : ""}
                    >
                        Submit Reconciliation
                    </Button>
                )}
                <Button
                    variant="secondary"
                    onClick={onCancel}
                    className="w-full"
                >
                    Cancel
                </Button>
            </div>
        </div>
    );
} 