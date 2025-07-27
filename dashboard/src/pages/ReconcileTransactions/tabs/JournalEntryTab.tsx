import type { MatchedTransaction } from '@/lib/types';
import type { BankTransaction } from '../../../lib/services/bankReconciliationService';

interface JournalEntryTabProps {
    selectedTransaction: BankTransaction;
    onTransactionSelect: (transaction: MatchedTransaction) => void;
    selectedTransactions: MatchedTransaction[];
    isTransactionSelected: (doctype: string, docname: string) => boolean;
}

export function JournalEntryTab({ 
    selectedTransaction, 
    onTransactionSelect,
    selectedTransactions,
    isTransactionSelected 
}: JournalEntryTabProps) {
    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold">Journal Entries</h3>
                <div className="text-sm text-muted-foreground">
                    Matching with transaction: {selectedTransaction.description}
                </div>
            </div>
            
            <div className="bg-card border rounded-lg p-4">
                <p className="text-muted-foreground">
                    Journal Entry matching content will be implemented here.
                </p>
                <p className="text-sm text-muted-foreground mt-2">
                    This tab will show journal entries that can be matched with the selected transaction.
                </p>
            </div>
        </div>
    );
} 