import { useState, useEffect } from 'react';
import { getBankTransactions, type BankTransaction } from '../lib/services/bankReconciliationService';
import { formatCurrency } from '../lib/utils';
import { Button } from './ui/button';

interface TransactionListProps {
  bankAccount?: string;
  fromDate?: string;
  toDate?: string;
  onTransactionSelect?: (transaction: BankTransaction) => void;
}

export function TransactionList({
  bankAccount,
  fromDate,
  toDate,
  onTransactionSelect
}: TransactionListProps) {
  const [transactions, setTransactions] = useState<BankTransaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (bankAccount && fromDate && toDate) {
      loadTransactions();
    }
  }, [bankAccount, fromDate, toDate]);

  const loadTransactions = async () => {
    if (!bankAccount || !fromDate || !toDate) return;

    setLoading(true);
    setError(null);

    try {
      const data = await getBankTransactions(bankAccount, fromDate, toDate);
      setTransactions(data);
    } catch (err) {
      console.error('Error loading transactions:', err);
      setError('Failed to load transactions');
    } finally {
      setLoading(false);
    }
  };

  const handleTransactionClick = (transaction: BankTransaction) => {
    onTransactionSelect?.(transaction);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading transactions...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-md">
        <p className="text-destructive">{error}</p>
        <button
          onClick={loadTransactions}
          className="mt-2 px-4 py-2 bg-destructive text-destructive-foreground rounded hover:bg-destructive/90"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!transactions.length) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        <p>No pending transactions found</p>
        {(!bankAccount || !fromDate || !toDate) && (
          <p className="text-sm mt-2">Please select a bank account and date range</p>
        )}
      </div>
    );
  }

  return (
    <div className="bg-card rounded-lg shadow border">
      <div className="px-6 py-4 border-b border-border">
        <h3 className="text-lg font-semibold text-card-foreground">
          Pending Transactions ({transactions.length})
        </h3>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-border">
          <thead className="bg-muted">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Date
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Transaction
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Party
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Description
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Deposit
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Withdrawal
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Unallocated
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Reference
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-card divide-y divide-border">
            {transactions.map((transaction) => (
              <tr
                key={transaction.name}
                className="hover:bg-muted/50 cursor-pointer"
                onClick={() => handleTransactionClick(transaction)}
              >
                <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                  {new Date(transaction.date).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-primary hover:text-primary/80">
                  {transaction.name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                  <div>
                    <div className="text-xs text-muted-foreground">{transaction.party_type}</div>
                    <div>{transaction.party}</div>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-foreground max-w-xs truncate">
                  {transaction.description}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600 font-medium">
                  {transaction.deposit ? formatCurrency(transaction.deposit, transaction.currency) : ''}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-red-600 font-medium">
                  {transaction.withdrawal ? formatCurrency(transaction.withdrawal, transaction.currency) : ''}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-blue-600 font-medium">
                  {formatCurrency(transaction.unallocated_amount, transaction.currency)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                  {transaction.reference_number}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                  <Button variant="default" size="sm" className="cursor-pointer">
                    Actions
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
} 