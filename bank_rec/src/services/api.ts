import type {
  BankAccount,
  BankRule,
  BootData,
  CashCodingRowsResponse,
  CashCodingSubmitResponse,
  CashCodingRow,
  CreateDefaultsResponse,
  CreateVoucherPayload,
  CreateVoucherResponse,
  DraftVoucherResponse,
  MatchCandidatesResponse,
  MatchVoucherSelection,
  MatchedTransactionsResponse,
  StatementSummary,
  SubmitMatchResponse,
  TransactionContext,
  BankTransaction,
  TransactionStatusFilter,
  UnreconcileResponse,
  UpdateTransactionResponse,
} from "@/types/bankRec";

type ApiValue =
  | string
  | number
  | boolean
  | null
  | undefined
  | Record<string, unknown>
  | unknown[];

interface FrappeResponse<T> {
  message?: T;
  exc?: string;
  exc_type?: string;
  _server_messages?: string;
}

const bankRecApiPath = "/api/method/advanced_bank_reconciliation.api.bank_rec.";
const matchingApiPath = "/api/method/advanced_bank_reconciliation.api.matching.";
const createVoucherApiPath =
  "/api/method/advanced_bank_reconciliation.api.create_voucher.";
const cashCodingApiPath =
  "/api/method/advanced_bank_reconciliation.api.cash_coding.";
const matchedApiPath = "/api/method/advanced_bank_reconciliation.api.matched.";

function getCsrfToken() {
  return window.csrf_token || "";
}

function encodeParams(params: Record<string, ApiValue>) {
  const body = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }
    body.append(
      key,
      typeof value === "object" ? JSON.stringify(value) : String(value)
    );
  });

  return body;
}

function getServerMessage(payload: FrappeResponse<unknown>) {
  if (payload._server_messages) {
    try {
      const messages = JSON.parse(payload._server_messages) as string[];
      const firstMessage = messages
        .map((message) => JSON.parse(message))
        .find((message) => message?.message);
      if (firstMessage?.message) {
        return firstMessage.message as string;
      }
    } catch {
      return "The server returned an error.";
    }
  }

  if (payload.exc_type) {
    return payload.exc_type;
  }

  return "The server returned an error.";
}

async function call<T>(
  apiPath: string,
  method: string,
  params: Record<string, ApiValue> = {}
): Promise<T> {
  const response = await fetch(`${apiPath}${method}`, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
      "X-Frappe-CSRF-Token": getCsrfToken(),
    },
    body: encodeParams(params),
  });

  const payload = (await response.json().catch(() => ({}))) as FrappeResponse<T>;

  if (!response.ok || payload.exc) {
    throw new Error(getServerMessage(payload));
  }

  return payload.message as T;
}

export async function getDevBoot() {
  const response = await fetch(
    "/api/method/advanced_bank_reconciliation.www.bank_rec.index.get_context_for_dev",
    {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Frappe-CSRF-Token": getCsrfToken(),
      },
    }
  );
  const payload = (await response.json().catch(() => ({}))) as FrappeResponse<
    Record<string, unknown>
  >;
  if (!response.ok || payload.exc) {
    throw new Error(getServerMessage(payload));
  }
  return payload.message || {};
}

export function getBoot() {
  return call<BootData>(bankRecApiPath, "get_boot");
}

export function getBankAccounts(company?: string) {
  return call<BankAccount[]>(bankRecApiPath, "get_bank_accounts", { company });
}

export function getStatementSummary(params: {
  bank_account: string;
  from_date?: string;
  to_date?: string;
}) {
  return call<StatementSummary>(bankRecApiPath, "get_statement_summary", params);
}

export function getTransactions(params: {
  bank_account: string;
  from_date?: string;
  to_date?: string;
  status?: TransactionStatusFilter;
}) {
  return call<BankTransaction[]>(bankRecApiPath, "get_transactions", params);
}

export function getTransactionContext(bank_transaction_name: string) {
  return call<TransactionContext>(bankRecApiPath, "get_transaction_context", {
    bank_transaction_name,
  });
}

export function getBankRules(bank_account?: string) {
  return call<BankRule[]>(bankRecApiPath, "get_bank_rules", { bank_account });
}

export function getMatchCandidates(params: {
  bank_transaction_name: string;
  from_date?: string;
  to_date?: string;
  document_types?: string[];
  exact_match?: boolean;
}) {
  return call<MatchCandidatesResponse>(matchingApiPath, "get_match_candidates", params);
}

export function submitMatch(params: {
  bank_transaction_name: string;
  vouchers: MatchVoucherSelection[];
}) {
  return call<SubmitMatchResponse>(matchingApiPath, "submit_match", params);
}

export function updateTransactionMetadata(params: {
  bank_transaction_name: string;
  reference_number?: string;
  party_type?: string;
  party?: string;
}) {
  return call<UpdateTransactionResponse>(
    matchingApiPath,
    "update_transaction_metadata",
    params
  );
}

export function getCreateDefaults(bank_transaction_name: string) {
  return call<CreateDefaultsResponse>(
    createVoucherApiPath,
    "get_create_defaults",
    { bank_transaction_name }
  );
}

export function createVoucherFromTransaction(params: {
  bank_transaction_name: string;
  payload: CreateVoucherPayload;
}) {
  return call<CreateVoucherResponse>(
    createVoucherApiPath,
    "create_voucher_from_transaction",
    params
  );
}

export function createVoucherDraftFromTransaction(params: {
  bank_transaction_name: string;
  payload: CreateVoucherPayload;
}) {
  return call<DraftVoucherResponse>(
    createVoucherApiPath,
    "create_voucher_draft_from_transaction",
    params
  );
}

export function getCashCodingRows(params: {
  bank_account: string;
  from_date?: string;
  to_date?: string;
}) {
  return call<CashCodingRowsResponse>(
    cashCodingApiPath,
    "get_cash_coding_rows",
    params
  );
}

export function submitCashCoding(rows: Array<CashCodingRow & { bank_transaction_name: string }>) {
  return call<CashCodingSubmitResponse>(cashCodingApiPath, "submit_cash_coding", {
    rows,
  });
}

export function getMatchedTransactions(params: {
  bank_account: string;
  from_date?: string;
  to_date?: string;
}) {
  return call<MatchedTransactionsResponse>(
    matchedApiPath,
    "get_matched_transactions",
    params
  );
}

export function unreconcileTransaction(params: {
  bank_transaction_name: string;
  cancel_linked_documents?: boolean;
}) {
  return call<UnreconcileResponse>(
    matchedApiPath,
    "unreconcile_transaction",
    params
  );
}
