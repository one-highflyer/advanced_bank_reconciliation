import type { BankTransaction } from '../../../lib/services/bankReconciliationService';

interface PurchaseInvoiceTabProps {
    selectedTransaction: BankTransaction;
    onTransactionSelect: (transaction: BankTransaction) => void;
}

export function PurchaseInvoiceTab({ selectedTransaction, onTransactionSelect }: PurchaseInvoiceTabProps) {
    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold">Purchase Invoices</h3>
                <div className="text-sm text-gray-500">
                    Matching with transaction: {selectedTransaction.description}
                </div>
            </div>
            
            <div className="bg-white border rounded-lg p-4">
                <p className="text-gray-600">
                    Purchase Invoice matching content will be implemented here.
                </p>
                <p className="text-sm text-gray-500 mt-2">
                    This tab will show purchase invoices that can be matched with the selected transaction.
                </p>
            </div>
        </div>
    );
} 