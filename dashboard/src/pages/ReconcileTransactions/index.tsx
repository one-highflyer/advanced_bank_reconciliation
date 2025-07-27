import { useState } from 'react';
import { BankReconciliationFilters } from '../../components/BankReconciliationFilters';
import { TransactionList } from '../../components/TransactionList';
import { TransactionMatchingSection } from './TransactionMatchingSection';
import type { BankTransaction } from '../../lib/services/bankReconciliationService';
import type { Filters } from '../../lib/types';

export default function ReconcileTransactions() {
    const [filters, setFilters] = useState<Filters | null>(null);
    const [selectedTransaction, setSelectedTransaction] = useState<BankTransaction>();

    const handleFiltersChange = (newFilters: Filters) => {
        setFilters(newFilters);
    };

    const handleTransactionSelect = (transaction: BankTransaction) => {
        console.log('Selected transaction:', transaction);
        setSelectedTransaction(transaction);
    };

    const handleCancel = () => {
        setSelectedTransaction(undefined);
    };

    const handleSubmit = () => {
        console.log('Reconciliation completed, clearing selected transactions');
        setSelectedTransaction(undefined);
    };

    return (
        <div className="container mx-auto px-4">
            {selectedTransaction ? (
                <TransactionMatchingSection
                    bankAccount={filters!.bankAccount}
                    fromDate={filters!.fromDate}
                    toDate={filters!.toDate}
                    selectedTransaction={selectedTransaction}
                    onCancel={handleCancel}
                    onSubmit={handleSubmit}
                />
            ) : (
                <>
                    <BankReconciliationFilters onFiltersChange={handleFiltersChange} />

                    {filters && (
                        <TransactionList
                            bankAccount={filters.bankAccount}
                            fromDate={filters.fromDate}
                            toDate={filters.toDate}
                            onTransactionSelect={handleTransactionSelect}
                        />
                    )}
                </>
            )}
        </div>
    );
} 