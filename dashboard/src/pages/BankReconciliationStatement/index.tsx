import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { formatCurrency } from '../../lib/utils';

interface ReconciliationSummary {
  bankBalance: number;
  bookBalance: number;
  difference: number;
  matchedTransactions: number;
  pendingTransactions: number;
  currency: string;
}

export default function BankReconciliationStatement() {
  const [summary, setSummary] = useState<ReconciliationSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadReconciliationSummary();
  }, []);

  const loadReconciliationSummary = async () => {
    setLoading(true);
    setError(null);

    try {
      // TODO: Replace with actual API call for reconciliation summary
      // Mock data for now
      const mockSummary: ReconciliationSummary = {
        bankBalance: 125000.00,
        bookBalance: 124850.00,
        difference: 150.00,
        matchedTransactions: 45,
        pendingTransactions: 3,
        currency: 'USD'
      };
      
      setSummary(mockSummary);
    } catch (err) {
      console.error('Error loading reconciliation summary:', err);
      setError('Failed to load reconciliation summary');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading reconciliation statement...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-md">
        <p className="text-destructive">{error}</p>
        <button
          onClick={loadReconciliationSummary}
          className="mt-2 px-4 py-2 bg-destructive text-destructive-foreground rounded hover:bg-destructive/90"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="container mx-auto">

      {!summary ? (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            <p>No reconciliation data available</p>
            <p className="text-sm mt-2">Please complete some reconciliations to see the statement</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Bank Balance
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">
                  {formatCurrency(summary.bankBalance, summary.currency)}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Book Balance
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-blue-600">
                  {formatCurrency(summary.bookBalance, summary.currency)}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Difference
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${summary.difference === 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(summary.difference, summary.currency)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {summary.difference === 0 ? 'Reconciled' : 'Unreconciled'}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Statistics */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Transaction Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Matched Transactions</span>
                  <span className="font-medium text-green-600">{summary.matchedTransactions}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Pending Transactions</span>
                  <span className="font-medium text-orange-600">{summary.pendingTransactions}</span>
                </div>
                <div className="flex justify-between items-center border-t pt-2">
                  <span className="text-sm font-medium">Total Transactions</span>
                  <span className="font-bold">{summary.matchedTransactions + summary.pendingTransactions}</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Reconciliation Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Status</span>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      summary.difference === 0 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {summary.difference === 0 ? 'Reconciled' : 'Pending'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Last Updated</span>
                    <span className="text-sm">{new Date().toLocaleDateString()}</span>
                  </div>
                  <div className="pt-2">
                    <Button className="w-full" variant="outline">
                      Generate Report
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Detailed Statement */}
          <Card>
            <CardHeader>
              <CardTitle>Detailed Reconciliation Statement</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <h4 className="font-medium mb-2">Bank Statement Balance</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span>Opening Balance</span>
                        <span>{formatCurrency(summary.bankBalance - 5000, summary.currency)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Add: Deposits</span>
                        <span className="text-green-600">+{formatCurrency(8000, summary.currency)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Less: Withdrawals</span>
                        <span className="text-red-600">-{formatCurrency(3000, summary.currency)}</span>
                      </div>
                      <div className="flex justify-between border-t pt-1 font-medium">
                        <span>Closing Balance</span>
                        <span>{formatCurrency(summary.bankBalance, summary.currency)}</span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="font-medium mb-2">Book Balance</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span>Opening Balance</span>
                        <span>{formatCurrency(summary.bookBalance - 5000, summary.currency)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Add: Credits</span>
                        <span className="text-green-600">+{formatCurrency(8000, summary.currency)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Less: Debits</span>
                        <span className="text-red-600">-{formatCurrency(3150, summary.currency)}</span>
                      </div>
                      <div className="flex justify-between border-t pt-1 font-medium">
                        <span>Closing Balance</span>
                        <span>{formatCurrency(summary.bookBalance, summary.currency)}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="border-t pt-4">
                  <div className="flex justify-between items-center">
                    <span className="font-medium">Difference</span>
                    <span className={`font-bold ${summary.difference === 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatCurrency(summary.difference, summary.currency)}
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
} 