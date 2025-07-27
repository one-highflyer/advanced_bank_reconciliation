import { useState } from 'react';
import { BankReconciliationFilters } from '../../components/BankReconciliationFilters';
import { TransactionList } from '../../components/TransactionList';
import type { BankTransaction } from '../../lib/services/bankReconciliationService';

type Filters = {
    company: string;
    bankAccount: string;
    fromDate: string;
    toDate: string;
}

export default function ReconcileTransactions() {
    const [filters, setFilters] = useState<Filters | null>(null);

    const handleFiltersChange = (newFilters: Filters) => {
        setFilters(newFilters);
    };

    const handleTransactionSelect = (transaction: BankTransaction) => {
        console.log('Selected transaction:', transaction);
        // TODO: Implement transaction selection logic
        // This could open a modal or navigate to a detail view
    };

    return (
        <div className="container mx-auto px-4">

            <BankReconciliationFilters onFiltersChange={handleFiltersChange} />

            {filters && (
                <TransactionList
                    bankAccount={filters.bankAccount}
                    fromDate={filters.fromDate}
                    toDate={filters.toDate}
                    onTransactionSelect={handleTransactionSelect}
                />
            )}
        </div>
    );
} 