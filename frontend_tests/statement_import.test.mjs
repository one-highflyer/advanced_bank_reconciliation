import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";

const require = createRequire(
  new URL("../bank_rec/package.json", import.meta.url)
);
const ts = require("typescript");
function importUtility(name) {
  const source = readFileSync(
    new URL(`../bank_rec/src/utils/${name}.ts`, import.meta.url),
    "utf8"
  );
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  return import(
    "data:text/javascript;base64," + Buffer.from(compiled).toString("base64")
  );
}
const {
  dateFormats,
  emptyImportMapping,
  hasRequiredMapping,
  hasSavedBankMapping,
  defaultSelectedRows,
  selectedImportRows,
  selectVisibleRows,
  filterImportRows,
} = await importUtility("statementImport");
const { formatMoney } = await importUtility("format");

function row(index, values = {}) {
  return {
    index,
    source_row: index + 2,
    date: "2026-11-01",
    deposit: 10,
    withdrawal: 0,
    description: "Payment",
    reference_number: "",
    custom_particulars: "",
    custom_code: "",
    bank_party_name: "",
    is_duplicate: false,
    errors: [],
    ...values,
  };
}

test("a default date format does not imply a saved bank mapping", () => {
  assert.equal(hasSavedBankMapping({ date_format: "Auto" }), false);
  assert.equal(
    hasSavedBankMapping({ date_format: "d/m/Y", date: "Date" }),
    true
  );
});

test("the import preview can show amounts beyond currency default precision", () => {
  assert.notEqual(
    formatMoney(10.001, undefined, 3),
    formatMoney(10, undefined, 3)
  );
  assert.notEqual(formatMoney(10.001, "NZD", 3), formatMoney(10, "NZD", 3));
});

test("required mapping follows single and separate amount layouts", () => {
  const mapping = {
    ...emptyImportMapping(),
    date_select: "Date",
    description_select: "Details",
    reference_number_select: "Reference",
    amount_select: "Amount",
  };
  assert.equal(hasRequiredMapping(mapping), true);
  assert.equal(hasRequiredMapping({ ...mapping, positive_field: "" }), false);
  assert.equal(
    hasRequiredMapping({ ...mapping, same_amount_field: false }),
    false
  );
  assert.equal(
    hasRequiredMapping({
      ...mapping,
      same_amount_field: false,
      amount_select: "",
      deposit_select: "Credit",
      withdrawal_select: "Debit",
    }),
    true
  );
  assert.equal(dateFormats.length, 17);
  assert.equal(new Set(dateFormats.map((format) => format.value)).size, 17);
});

test("duplicates and invalid rows require review instead of default selection", () => {
  const rows = [
    row(0),
    row(1, { is_duplicate: true }),
    row(2, { errors: ["Invalid date"] }),
    row(3),
  ];
  assert.deepEqual(defaultSelectedRows(rows), [0, 3]);
  assert.deepEqual(
    selectedImportRows(rows, [0, 1, 2]).map((item) => item.index),
    [0, 1]
  );
});

test("page selection preserves rows checked on other pages and excludes invalid rows", () => {
  const page = [
    row(25),
    row(26, { errors: ["Amount is invalid"] }),
    row(27, { is_duplicate: true }),
  ];
  const selected = [0, 1, 25];
  assert.deepEqual(selectVisibleRows(selected, page, true), [0, 1, 25, 27]);
  assert.deepEqual(selectVisibleRows(selected, page, false), [0, 1]);
  assert.deepEqual(selected, [0, 1, 25]);
});

test("search and status filters do not remove hidden checked rows", () => {
  const rows = [
    row(0, { bank_party_name: "Sample merchant" }),
    row(1, { is_duplicate: true, custom_code: "FEE" }),
    row(2, { errors: ["Date is invalid"] }),
  ];
  assert.deepEqual(
    filterImportRows(rows, "all", "merchant").map((item) => item.index),
    [0]
  );
  assert.deepEqual(
    filterImportRows(rows, "duplicates", "fee").map((item) => item.index),
    [1]
  );
  assert.deepEqual(
    filterImportRows(rows, "errors", "date").map((item) => item.index),
    [2]
  );
  assert.deepEqual(
    selectedImportRows(rows, [0, 1]).map((item) => item.index),
    [0, 1]
  );
});
