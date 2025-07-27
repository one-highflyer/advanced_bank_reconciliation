import { X } from 'lucide-react';
import type { BankTransaction } from '../../lib/services/bankReconciliationService';

interface SelectedTransactionsPaneProps {
    selectedTransactions: BankTransaction[];
    onTransactionRemove: (transactionName: string) => void;
}

export function SelectedTransactionsPane({ selectedTransactions, onTransactionRemove }: SelectedTransactionsPaneProps) {
    return (
        <div className="bg-white border rounded-lg p-4 h-fit">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Selected Transactions</h3>
                <span className="text-sm text-gray-500">
                    {selectedTransactions.length} selected
                </span>
            </div>

            {selectedTransactions.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                    <p>No transactions selected</p>
                    <p className="text-sm mt-1">
                        Select transactions from the tabs to match them
                    </p>
                </div>
            ) : (
                <div className="space-y-3">
                    {selectedTransactions.map((transaction) => (
                        <div
                            key={transaction.name}
                            className="border rounded-lg p-3 bg-gray-50 relative"
                        >
                            <button
                                onClick={() => onTransactionRemove(transaction.name)}
                                className="absolute top-2 right-2 text-gray-400 hover:text-gray-600 transition-colors"
                                title="Remove transaction"
                            >
                                <X size={16} />
                            </button>
                            
                            <div className="pr-6">
                                <div className="font-medium text-sm">
                                    {transaction.description}
                                </div>
                                <div className="text-xs text-gray-500 mt-1">
                                    <div>Date: {transaction.date}</div>
                                    <div>Deposit: {transaction.deposit}</div>
                                    <div>Withdrawal: {transaction.withdrawal}</div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {selectedTransactions.length > 0 && (
                <div className="mt-4 pt-4 border-t">
                    <button className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors">
                        Match Selected Transactions
                    </button>
                </div>
            )}
        </div>
    );
} 