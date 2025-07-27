type Filters = {
    company: string;
    bankAccount: string;
    fromDate: string;
    toDate: string;
}

type MatchedTransaction = {
    doctype: string;
    docname: string;
    reference_date: string;
    remaining_amount: number;
    reference_number: string;
    party: string;
    currency: string;
}

export type { Filters, MatchedTransaction };
