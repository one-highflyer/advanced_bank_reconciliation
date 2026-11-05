import { call, getServerMessage } from "@/services/api";
import type {
  ImportContext,
  ImportMapping,
  PreparedStatement,
  StatementImportResult,
  StatementPreview,
  UploadedStatement,
} from "@/types/statementImport";

const apiPath =
  "/api/method/advanced_bank_reconciliation.api.statement_import.";

export function getImportContext(bank_account: string) {
  return call<ImportContext>(apiPath, "get_import_context", { bank_account });
}

export async function uploadStatementFile(file: File) {
  const body = new FormData();
  body.append("file", file);
  body.append("is_private", "1");
  const response = await fetch("/api/method/upload_file", {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-Frappe-CSRF-Token": window.csrf_token || "" },
    body,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.exc || !payload.message?.file_url) {
    throw new Error(getServerMessage(payload));
  }
  return payload.message as UploadedStatement;
}

export function prepareStatement(bank_account: string, file_url: string) {
  return call<PreparedStatement>(apiPath, "prepare_statement", {
    bank_account,
    file_url,
  });
}

export function previewStatement(
  bank_account: string,
  file_url: string,
  mapping: ImportMapping
) {
  return call<StatementPreview>(apiPath, "preview_statement", {
    bank_account,
    file_url,
    mapping,
  });
}

export function importStatement(params: {
  bank_account: string;
  file_url: string;
  mapping: ImportMapping;
  selected_rows: number[];
  include_duplicates: boolean;
  confirmed_duplicate_rows: number[];
  file_hash: string;
  request_id: string;
}) {
  return call<StatementImportResult>(apiPath, "import_statement", params);
}
