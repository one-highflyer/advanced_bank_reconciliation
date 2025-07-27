import { useState, useEffect } from 'react';
import { getBankTransactions, type BankTransaction } from '../../lib/services/bankReconciliationService';
import { formatCurrency } from '../../lib/utils';
import { Card, CardContent } from '../../components/ui/card';

export default function MatchedTransactions() {
  const [matchedTransactions, setMatchedTransactions] = useState<BankTransaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadMatchedTransactions();
  }, []);

  const loadMatchedTransactions = async () => {
    setLoading(true);
    setError(null);

    try {
      // TODO: Replace with actual API call for matched transactions
      // For now, using the same service but this should be updated
      const data = await getBankTransactions('', '', '');
      setMatchedTransactions(data.filter(t => t.unallocated_amount === 0));
    } catch (err) {
      console.error('Error loading matched transactions:', err);
      setError('Failed to load matched transactions');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading matched transactions...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-md">
        <p className="text-destructive">{error}</p>
        <button
          onClick={loadMatchedTransactions}
          className="mt-2 px-4 py-2 bg-destructive text-destructive-foreground rounded hover:bg-destructive/90"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="container mx-auto">

      {!matchedTransactions.length ? (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            <p>No matched transactions found</p>
            <p className="text-sm mt-2">Transactions will appear here once they are reconciled</p>
          </CardContent>
        </Card>
      ) : (
        <div className="bg-card rounded-lg shadow border">
          <div className="px-6 py-4 border-b border-border">
            <h3 className="text-lg font-semibold text-card-foreground">
              Matched Transactions ({matchedTransactions.length})
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
                    Amount
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-card divide-y divide-border">
                {matchedTransactions.map((transaction) => (
                  <tr key={transaction.name} className="hover:bg-muted/50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                      {new Date(transaction.date).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-primary">
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
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      {transaction.deposit 
                        ? formatCurrency(transaction.deposit, transaction.currency)
                        : formatCurrency(transaction.withdrawal, transaction.currency)
                      }
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        Matched
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
} 