import type { BankTransaction } from '../../../lib/services/bankReconciliationService';

interface JournalEntryTabProps {
    selectedTransaction: BankTransaction;
    onTransactionSelect: (transaction: BankTransaction) => void;
}

export function JournalEntryTab({ selectedTransaction, onTransactionSelect }: JournalEntryTabProps) {
    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold">Journal Entries</h3>
                <div className="text-sm text-gray-500">
                    Matching with transaction: {selectedTransaction.description}
                </div>
            </div>
            
            <div className="bg-white border rounded-lg p-4">
                <p className="text-gray-600">
                    Journal Entry matching content will be implemented here.
                </p>
                <p className="text-sm text-gray-500 mt-2">
                    This tab will show journal entries that can be matched with the selected transaction.
                </p>
            </div>
        </div>
    );
} 