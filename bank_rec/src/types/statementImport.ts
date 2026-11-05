import type { BankAccount } from "@/types/bankRec";

export interface ImportMapping extends Record<string, string | boolean> {
  date_select: string;
  date_format: string;
  same_amount_field: boolean;
  amount_select: string;
  positive_field: "Deposit" | "Withdrawal";
  deposit_select: string;
  withdrawal_select: string;
  description_select: string;
  reference_number_select: string;
  particulars_select: string;
  code_select: string;
  other_party_select: string;
  save_mapping_for_future_use: boolean;
}

export interface ImportContext {
  bank_account: BankAccount;
  bank: string | null;
  currency: string;
  is_credit_card: boolean;
  last_transaction: {
    name?: string;
    date: string;
    deposit: number;
    withdrawal: number;
    description?: string;
  } | null;
  bank_mapping: Record<string, string>;
  can_save_mapping: boolean;
}

export interface PreparedStatement {
  headers: string[];
  preview_rows: unknown[][];
  row_count: number;
  mapping: ImportMapping;
  stale_mappings: string[];
}

export interface StatementPreviewRow {
  index: number;
  source_row: number;
  date: string | null;
  raw_date?: string;
  deposit: number;
  withdrawal: number;
  description: string;
  reference_number: string;
  custom_particulars: string;
  custom_code: string;
  bank_party_name: string;
  is_duplicate: boolean;
  errors: string[];
}

export interface StatementPreview {
  rows: StatementPreviewRow[];
  summary: {
    total: number;
    ready: number;
    possible_duplicates: number;
    errors: number;
    money_in: number;
    money_out: number;
  };
  currency: string;
  file_hash: string;
  account_revision: string;
  amount_precision: { deposit: number; withdrawal: number };
}

export interface StatementImportResult {
  bank_account: string;
  imported_count: number;
  unselected_count: number;
  from_date: string | null;
  to_date: string | null;
  transactions: Array<{ name: string; date: string }>;
  mapping_saved: boolean;
  warnings: string[];
  idempotent: boolean;
}

export interface UploadedStatement {
  file_url: string;
  file_name: string;
  name: string;
  file_size?: number;
}
