export interface BootData {
  default_route: string;
  site_name: string;
  csrf_token: string;
  session_user: string;
  lang: string;
  dir: "ltr" | "rtl";
  allowed_roles: string[];
  settings: Record<string, unknown>;
  accounting_dimensions: Record<string, unknown>[];
}

export interface BankAccount {
  name: string;
  account_name: string;
  bank?: string;
  account: string;
  company: string;
  currency?: string;
}

export type TransactionDirection = "deposit" | "withdrawal" | "unknown";

export interface BankTransaction {
  name: string;
  date?: string;
  description?: string;
  reference_number?: string;
  bank_party_name?: string;
  custom_particulars?: string;
  custom_code?: string;
  deposit: number;
  withdrawal: number;
  amount: number;
  direction: TransactionDirection;
  currency?: string;
  bank_account: string;
  company?: string;
  unallocated_amount: number;
  party_type?: string;
  party?: string;
  party_display?: string;
  payment_document?: string;
  payment_entry?: string;
  allocated_amount: number;
  status?: string;
}

export interface LinkedPayment {
  payment_document?: string;
  payment_entry?: string;
  allocated_amount: number;
}

export interface TransactionContext {
  transaction: BankTransaction;
  bank_account: BankAccount;
  linked_payments: LinkedPayment[];
}

export interface StatementSummary {
  bank_account: string;
  from_date?: string;
  to_date?: string;
  unreconciled_count: number;
  selected_amount: number | null;
  cleared_balance: number;
  unreconciled_total: number;
}

export interface BankRule {
  name: string;
  title?: string;
  enabled?: boolean | number;
  priority?: number;
  company?: string;
  bank_account?: string;
  entry_type?: string;
  account?: string;
  party_type?: string;
  party?: string;
  modified?: string;
  desk_url: string;
}

export type TransactionStatusFilter = "unreconciled" | "reconciled" | "all";

export type MatchConfidence = "high" | "medium" | "low";

export interface MatchCandidate {
  rank: number;
  voucher_type: string;
  source_type?: string;
  voucher_name: string;
  amount: number;
  reference_number?: string;
  reference_date?: string;
  party?: string;
  party_type?: string;
  posting_date?: string;
  currency?: string;
  party_name?: string;
  key: string;
  reasons: string[];
  confidence: MatchConfidence;
}

export interface MatchCandidatesResponse {
  transaction: BankTransaction;
  candidates: MatchCandidate[];
  filters: {
    document_types: string[];
    from_date?: string;
    to_date?: string;
  };
}

export interface MatchVoucherSelection {
  voucher_type: string;
  voucher_name: string;
  amount: number;
}

export interface SubmitMatchResponse {
  status: string;
  idempotent: boolean;
  transaction: BankTransaction;
  linked_payments: LinkedPayment[];
}

export interface UpdateTransactionResponse {
  transaction: BankTransaction;
}

export interface CreateOption {
  name: string;
  account_name?: string;
  account_type?: string;
  root_type?: string;
  cost_center_name?: string;
  project_name?: string;
}

export interface CreateDefaultsResponse {
  transaction: BankTransaction;
  bank_account: BankAccount;
  settings: Record<string, unknown>;
  defaults: {
    posting_date?: string;
    reference_date?: string;
    reference_number?: string;
    party_type?: string;
    party?: string;
  };
  options: {
    accounts: CreateOption[];
    mode_of_payments: CreateOption[];
    cost_centers: CreateOption[];
    projects: CreateOption[];
  };
}

export interface CreateVoucherPayload {
  account?: string;
  party_type?: string;
  party?: string;
  mode_of_payment?: string;
  posting_date?: string;
  reference_date?: string;
  reference_number?: string;
  cost_center?: string;
  project?: string;
  dimensions?: Record<string, unknown>;
  save_as_rule?: boolean;
  rule_title?: string;
}

export interface CreateVoucherResponse {
  status: string;
  transaction: BankTransaction;
  voucher_type?: string;
  voucher_name?: string;
  desk_url?: string;
  linked_payments: LinkedPayment[];
  rule?: { name: string; title: string } | null;
}

export interface DraftVoucherResponse {
  voucher_type: string;
  voucher_name: string;
  desk_url: string;
  transaction: BankTransaction;
}

export interface CashCodingRow {
  transaction: BankTransaction;
  account: string;
  party_type: string;
  party: string;
  cost_center: string;
  project: string;
  reference_number: string;
  notes: string;
  suggested_rule?: { name: string; title: string } | null;
}

export interface CashCodingRowsResponse {
  rows: CashCodingRow[];
  options: {
    accounts: CreateOption[];
    cost_centers: CreateOption[];
    projects: CreateOption[];
  };
}

export interface CashCodingSubmitRowResult {
  bank_transaction: string;
  status: "success" | "error";
  message: string;
  voucher?: {
    voucher_type: string;
    voucher_name: string;
  } | null;
}

export interface CashCodingSubmitResponse {
  results: CashCodingSubmitRowResult[];
  summary: {
    total: number;
    success: number;
    error: number;
  };
}

export interface MatchedTransactionsResponse {
  rows: BankTransaction[];
}

export interface UnreconcileResponse {
  transaction: BankTransaction;
  linked_payments: LinkedPayment[];
  cancel_linked_documents: boolean;
}
