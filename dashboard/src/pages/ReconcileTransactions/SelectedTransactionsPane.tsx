import { useState } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { formatCurrency } from '@/lib/utils';
import { reconcileVouchers, createPaymentEntriesForInvoices } from '@/lib/services/bankReconciliationService';
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
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Calculate the sum of selected transaction amounts
    const selectedAmountSum = selectedTransactions.reduce((sum, transaction) => {
        return sum + transaction.remaining_amount;
    }, 0);

    // Get the bank transaction amount (deposit or withdrawal)
    const bankTransactionAmount = selectedBankTransaction.deposit || selectedBankTransaction.withdrawal || 0;
    const bankTransactionCurrency = selectedBankTransaction.currency;

    // Check if amounts match
    const amountsMatch = Math.abs(selectedAmountSum - bankTransactionAmount) < 0.01; // Allow for small rounding differences

        // Handle reconciliation submission
    const handleSubmit = async () => {
        if (!amountsMatch || selectedTransactions.length === 0) {
            return;
        }

        setIsSubmitting(true);
        try {
            // Separate unpaid invoices from regular vouchers
            const unpaidInvoices: Array<{
                doctype: string;
                name: string;
                allocated_amount: number;
            }> = [];
            const regularVouchers: Array<{
                payment_doctype: string;
                payment_name: string;
                amount: number;
            }> = [];
            
            selectedTransactions.forEach((transaction) => {
                if (transaction.doctype === "Unpaid Sales Invoice" || transaction.doctype === "Unpaid Purchase Invoice") {
                    unpaidInvoices.push({
                        doctype: transaction.doctype,
                        name: transaction.docname,
                        allocated_amount: transaction.remaining_amount,
                    });
                } else {
                    regularVouchers.push({
                        payment_doctype: transaction.doctype,
                        payment_name: transaction.docname,
                        amount: transaction.remaining_amount,
                    });
                }
            });

            console.log('Submitting reconciliation for bank transaction:', selectedBankTransaction.name);
            console.log('Unpaid invoices to process:', unpaidInvoices);
            console.log('Regular vouchers to reconcile:', regularVouchers);

            // Process unpaid invoices first, then regular vouchers
            await processUnpaidInvoices(unpaidInvoices, regularVouchers);
            
        } catch (error) {
            console.error('Error during reconciliation:', error);
            alert(`❌ Error during reconciliation\n\n${(error as Error).message}\n\nPlease check the console for more details.`);
        } finally {
            setIsSubmitting(false);
        }
    };

    // Process unpaid invoices first, then regular vouchers (following dialog_manager.js pattern)
    const processUnpaidInvoices = async (
        unpaidInvoices: Array<{ doctype: string; name: string; allocated_amount: number }>,
        regularVouchers: Array<{ payment_doctype: string; payment_name: string; amount: number }>
    ) => {
        if (unpaidInvoices.length > 0) {
            // First, create payment entries for unpaid invoices
            // Don't auto-reconcile if we have regular vouchers to process too
            const autoReconcile = regularVouchers.length === 0;
            
            console.log('Creating payment entries for unpaid invoices, auto_reconcile:', autoReconcile);
            const response = await createPaymentEntriesForInvoices(
                selectedBankTransaction.name,
                unpaidInvoices,
                autoReconcile
            );
            
            console.log('Payment entries created for unpaid invoices:', response);
            
            if (autoReconcile) {
                // Payment entries were created and auto-reconciled, we're done
                showSuccessMessage(unpaidInvoices.length + regularVouchers.length);
                onSubmit();
            } else {
                // Payment entries created but not reconciled, now combine with regular vouchers
                const responseData = response as { vouchers?: Array<{ payment_doctype: string; payment_name: string; amount: number }> };
                const createdVouchers = responseData?.vouchers || [];
                const allVouchers = [...createdVouchers, ...regularVouchers];
                await reconcileAllVouchers(allVouchers);
            }
        } else {
            // No unpaid invoices, directly process regular vouchers
            await reconcileAllVouchers(regularVouchers);
        }
    };

    // Reconcile all vouchers (both created from unpaid invoices and regular ones)
    const reconcileAllVouchers = async (vouchers: Array<{ payment_doctype: string; payment_name: string; amount: number }>) => {
        if (vouchers.length === 0) {
            console.log('No vouchers to reconcile');
            return;
        }
        
        console.log('Reconciling all vouchers:', vouchers);
        const result = await reconcileVouchers(selectedBankTransaction.name, vouchers);
        
        console.log('Reconciliation successful:', result);
        showSuccessMessage(selectedTransactions.length);
        onSubmit();
    };

    // Show success message
    const showSuccessMessage = (transactionCount: number) => {
        alert(`✅ Reconciliation completed successfully!\n\nBank Transaction: ${selectedBankTransaction.name}\nMatched ${transactionCount} transaction(s)\nTotal Amount: ${formatCurrency(selectedAmountSum, bankTransactionCurrency)}`);
    };

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
                <div className="max-h-128 overflow-y-auto border rounded-lg">
                    <div className="space-y-2 p-3">
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
                </div>
            )}

            <div className="mt-4 pt-4 border-t space-y-2 lg:space-y-0 lg:flex lg:gap-2">
                {selectedTransactions.length > 0 && (
                    <Button
                        onClick={handleSubmit}
                        className="w-full lg:w-1/2"
                        disabled={!amountsMatch || isSubmitting}
                        title={!amountsMatch ? "Amounts must match to submit reconciliation" : ""}
                    >
                        {isSubmitting ? "Submitting..." : "Submit"}
                    </Button>
                )}
                <Button
                    variant="secondary"
                    onClick={onCancel}
                    className="w-full lg:w-1/2"
                    disabled={isSubmitting}
                >
                    Cancel
                </Button>
            </div>
        </div>
    );
} 