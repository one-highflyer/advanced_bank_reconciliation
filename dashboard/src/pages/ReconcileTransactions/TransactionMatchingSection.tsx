import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PaymentEntryTab } from './tabs/PaymentEntryTab';
import { JournalEntryTab } from './tabs/JournalEntryTab';
import { SalesInvoiceTab } from './tabs/SalesInvoiceTab';
import { PurchaseInvoiceTab } from './tabs/PurchaseInvoiceTab';
import { UnpaidPurchaseInvoiceTab } from './tabs/UnpaidPurchaseInvoiceTab';
import { UnpaidSalesInvoiceTab } from './tabs/UnpaidSalesInvoiceTab';
import { SelectedTransactionsPane } from './SelectedTransactionsPane';
import type { BankTransaction } from '../../lib/services/bankReconciliationService';
import { formatCurrency } from '../../lib/utils';

interface TransactionMatchingSectionProps {
    selectedTransaction: BankTransaction;
}

export function TransactionMatchingSection({ selectedTransaction }: TransactionMatchingSectionProps) {
    const [selectedTransactions, setSelectedTransactions] = useState<BankTransaction[]>([]);

    const handleTransactionSelect = (transaction: BankTransaction) => {
        setSelectedTransactions(prev => {
            const exists = prev.find(t => t.name === transaction.name);
            if (exists) {
                return prev.filter(t => t.name !== transaction.name);
            } else {
                return [...prev, transaction];
            }
        });
    };

    const handleTransactionRemove = (transactionName: string) => {
        setSelectedTransactions(prev => prev.filter(t => t.name !== transactionName));
    };

    return (
        <div className="container mx-auto px-4">
            {/* Transaction Summary */}
            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                <h2 className="text-xl font-semibold mb-2">Transaction Summary</h2>
                <div className="grid grid-cols-4 gap-2">
                    <div>
                        <span className="font-medium">Date:</span> {selectedTransaction.date}
                    </div>
                    {!!selectedTransaction.deposit && (
                        <div>
                            <span className="font-medium">Deposit:</span> {formatCurrency(selectedTransaction.deposit, selectedTransaction.currency)}
                        </div>
                    )}
                    {!!selectedTransaction.withdrawal && (
                        <div>
                            <span className="font-medium">Withdrawal:</span> {formatCurrency(selectedTransaction.withdrawal, selectedTransaction.currency)}
                        </div>
                    )}
                    <div>
                        <span className="font-medium">Description:</span> {selectedTransaction.description}
                    </div>
                    <div>
                        <span className="font-medium">Reference:</span> {selectedTransaction.reference_number}
                    </div>
                </div>
            </div>

            {/* Main Content with Tabs and Right Pane */}
            <div className="flex gap-6">
                {/* Left Side - Tabs (3/4 width) */}
                <div className="flex-1">
                    <Tabs defaultValue="payment-entry" className="w-full">
                        <TabsList className="grid w-full grid-cols-6">
                            <TabsTrigger value="payment-entry">Payment Entry</TabsTrigger>
                            <TabsTrigger value="journal-entry">Journal Entry</TabsTrigger>
                            <TabsTrigger value="sales-invoice">Sales Invoice</TabsTrigger>
                            <TabsTrigger value="purchase-invoice">Purchase Invoice</TabsTrigger>
                            <TabsTrigger value="unpaid-sales-invoice">Unpaid Sales Invoice</TabsTrigger>
                            <TabsTrigger value="unpaid-purchase-invoice">Unpaid Purchase Invoice</TabsTrigger>
                        </TabsList>

                        <TabsContent value="payment-entry" className="mt-4">
                            <PaymentEntryTab
                                selectedTransaction={selectedTransaction}
                                onTransactionSelect={handleTransactionSelect}
                            />
                        </TabsContent>

                        <TabsContent value="journal-entry" className="mt-4">
                            <JournalEntryTab
                                selectedTransaction={selectedTransaction}
                                onTransactionSelect={handleTransactionSelect}
                            />
                        </TabsContent>

                        <TabsContent value="sales-invoice" className="mt-4">
                            <SalesInvoiceTab
                                selectedTransaction={selectedTransaction}
                                onTransactionSelect={handleTransactionSelect}
                            />
                        </TabsContent>

                        <TabsContent value="purchase-invoice" className="mt-4">
                            <PurchaseInvoiceTab
                                selectedTransaction={selectedTransaction}
                                onTransactionSelect={handleTransactionSelect}
                            />
                        </TabsContent>

                        <TabsContent value="unpaid-sales-invoice" className="mt-4">
                            <UnpaidSalesInvoiceTab
                                selectedTransaction={selectedTransaction}
                                onTransactionSelect={handleTransactionSelect}
                            />
                        </TabsContent>

                        <TabsContent value="unpaid-purchase-invoice" className="mt-4">
                            <UnpaidPurchaseInvoiceTab
                                selectedTransaction={selectedTransaction}
                                onTransactionSelect={handleTransactionSelect}
                            />
                        </TabsContent>
                    </Tabs>
                </div>

                {/* Right Side - Selected Transactions Pane (1/4 width) */}
                <div className="w-1/4">
                    <SelectedTransactionsPane
                        selectedTransactions={selectedTransactions}
                        onTransactionRemove={handleTransactionRemove}
                    />
                </div>
            </div>
        </div>
    );
} 