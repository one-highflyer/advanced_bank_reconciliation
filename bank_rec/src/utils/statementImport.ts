import type {
  ImportMapping,
  StatementPreviewRow,
} from "@/types/statementImport";

export const dateFormats = [
  { label: "Auto", value: "Auto" },
  { label: "d/m/Y (25/03/2026)", value: "d/m/Y" },
  { label: "dd/mm/YY (25/03/26)", value: "dd/mm/YY" },
  { label: "Y-m-d (2026-03-25)", value: "Y-m-d" },
  { label: "Y/m/d (2026/03/25)", value: "Y/m/d" },
  { label: "m/d/Y (03/25/2026)", value: "m/d/Y" },
  { label: "m/d/YY (03/25/26)", value: "m/d/YY" },
  { label: "m-d-Y (03-25-2026)", value: "m-d-Y" },
  { label: "m-d-YY (03-25-26)", value: "m-d-YY" },
  { label: "d-m-Y (25-03-2026)", value: "d-m-Y" },
  { label: "d-m-YY (25-03-26)", value: "d-m-YY" },
  { label: "Y/d/m (2026/25/03)", value: "Y/d/m" },
  { label: "d.m.Y (25.03.2026)", value: "d.m.Y" },
  { label: "d.m.YY (25.03.26)", value: "d.m.YY" },
  { label: "Y.m.d (2026.03.25)", value: "Y.m.d" },
  { label: "m.d.Y (03.25.2026)", value: "m.d.Y" },
  { label: "m.d.YY (03.25.26)", value: "m.d.YY" },
];

export function emptyImportMapping(): ImportMapping {
  return {
    date_select: "",
    date_format: "Auto",
    same_amount_field: true,
    amount_select: "",
    positive_field: "Deposit",
    deposit_select: "",
    withdrawal_select: "",
    description_select: "",
    reference_number_select: "",
    particulars_select: "",
    code_select: "",
    other_party_select: "",
    save_mapping_for_future_use: false,
  };
}

export function hasRequiredMapping(mapping: ImportMapping) {
  return Boolean(
    mapping.date_select &&
    mapping.date_format &&
    mapping.description_select &&
    mapping.reference_number_select &&
    (mapping.same_amount_field
      ? mapping.amount_select &&
        ["Deposit", "Withdrawal"].includes(mapping.positive_field)
      : mapping.deposit_select && mapping.withdrawal_select),
  );
}

export function hasSavedBankMapping(mapping: Record<string, string>) {
  return Object.entries(mapping).some(
    ([key, value]) => key !== "date_format" && Boolean(value),
  );
}

export function defaultSelectedRows(rows: StatementPreviewRow[]) {
  return rows
    .filter((row) => !row.is_duplicate && !row.errors.length)
    .map((row) => row.index);
}

export function selectedImportRows(
  rows: StatementPreviewRow[],
  selected: number[],
) {
  const indices = new Set(selected);
  return rows.filter((row) => indices.has(row.index) && !row.errors.length);
}

export function selectVisibleRows(
  selected: number[],
  visible: StatementPreviewRow[],
  checked: boolean,
) {
  const next = new Set(selected);
  for (const row of visible) {
    if (row.errors.length) continue;
    if (checked) next.add(row.index);
    else next.delete(row.index);
  }
  return [...next];
}

export function filterImportRows(
  rows: StatementPreviewRow[],
  filter: string,
  search: string,
) {
  const term = search.trim().toLowerCase();
  return rows.filter((row) => {
    const statusMatches =
      filter === "all" ||
      (filter === "ready" && !row.is_duplicate && !row.errors.length) ||
      (filter === "duplicates" && row.is_duplicate) ||
      (filter === "errors" && row.errors.length > 0);
    const text = [
      row.date,
      row.description,
      row.reference_number,
      row.custom_particulars,
      row.custom_code,
      row.bank_party_name,
      row.deposit,
      row.withdrawal,
      row.source_row,
      ...row.errors,
    ]
      .join(" ")
      .toLowerCase();
    return statusMatches && (!term || text.includes(term));
  });
}
