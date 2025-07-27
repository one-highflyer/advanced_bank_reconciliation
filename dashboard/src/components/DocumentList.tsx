import { Checkbox } from '@/components/ui/checkbox';
import { formatCurrency } from '../lib/utils';
import type { PaymentEntry } from '../lib/services/paymentEntryService';

interface DocumentListProps {
    documents: PaymentEntry[];
    documentType: string;
    loading: boolean;
    error: string | null;
    isTransactionSelected: (doctype: string, docname: string) => boolean;
    onDocumentSelect: (documentName: string) => void;
    onSelectAll: (checked: boolean) => void;
    onRetry: () => void;
}

export function DocumentList({
    documents,
    documentType,
    loading,
    error,
    isTransactionSelected,
    onDocumentSelect,
    onSelectAll,
    onRetry
}: DocumentListProps) {
    // Check if all documents are selected
    const allSelected = documents.length > 0 && documents.every(doc => 
        isTransactionSelected(doc.doctype, doc.name)
    );

    if (loading) {
        return (
            <div className="space-y-4">
                <div className="flex items-center justify-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                    <span className="ml-2 text-muted-foreground">Loading {documentType}...</span>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="space-y-4">
                <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-md">
                    <p className="text-destructive">{error}</p>
                    <button
                        onClick={onRetry}
                        className="mt-2 px-4 py-2 bg-destructive text-destructive-foreground rounded hover:bg-destructive/90"
                    >
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {documents.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                    <p>No {documentType} found</p>
                    <p className="text-sm mt-1">
                        No matching {documentType} were found for this transaction.
                    </p>
                </div>
            ) : (
                <div className="space-y-2">
                    {/* Select All Checkbox */}
                    <div className="flex items-center space-x-2 p-3 bg-muted rounded-lg">
                        <Checkbox
                            id="select-all"
                            checked={allSelected}
                            onCheckedChange={onSelectAll}
                        />
                        <label htmlFor="select-all" className="text-sm font-medium">
                            Select All ({documents.length} {documentType})
                        </label>
                    </div>

                    {/* Scrollable Documents List */}
                    <div className="max-h-144 overflow-y-auto border rounded-lg">
                        <div className="space-y-1 p-2">
                            {documents.map((doc) => (
                                <div
                                    key={doc.name}
                                    className="flex items-center space-x-3 p-2 border rounded-md hover:bg-muted/50 transition-colors"
                                >
                                    <Checkbox
                                        id={doc.name}
                                        checked={isTransactionSelected(doc.doctype, doc.name)}
                                        onCheckedChange={() => onDocumentSelect(doc.name)}
                                    />
                                    <div className="flex-1 min-w-0">
                                        <div className="flex justify-between items-center">
                                            <div className="flex-1 min-w-0">
                                                <div className="font-medium text-sm truncate">
                                                    {doc.doctype}: {doc.name}
                                                </div>
                                                <div className="flex items-center space-x-4 text-xs text-muted-foreground mt-0.5">
                                                    <span>Ref: {doc.reference_number || 'N/A'}</span>
                                                    <span>Party: {doc.party || 'N/A'}</span>
                                                    <span>Date: {doc.reference_date}</span>
                                                </div>
                                            </div>
                                            <div className="text-right ml-4">
                                                <div className={`font-medium text-sm ${doc.paid_amount > 0 ? 'text-green-600' : 'text-red-600'}`}>
                                                    {formatCurrency(doc.paid_amount, doc.currency)}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
} 