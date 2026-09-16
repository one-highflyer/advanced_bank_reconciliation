const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const sourcePath = path.resolve(
  __dirname,
  "../advanced_bank_reconciliation/public/js/advance_bank_reconciliation_tool/dialog_manager.js"
);
const context = {
  console,
  flt: (value) => Number(value) || 0,
  frappe: { provide() {} },
  nexwave: { accounts: { bank_reconciliation: {} } },
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(sourcePath, "utf8"), context);

const prototype = context.nexwave.accounts.bank_reconciliation.DialogManager.prototype;

function allocate(rows) {
  const manager = Object.create(prototype);
  manager.bank_transaction = { unallocated_amount: 100 };
  return manager.compute_effective_allocations(rows);
}

const ordinary = [1, "Journal Entry", "JE-ORDINARY", 20];
const transfer = [3, "Payment Entry", "PE-TRANSFER", 100, null, null, null, null, null, null, null, 1];

test("ordinary allocations are reserved before a transfer in either display order", () => {
  assert.deepEqual([...allocate([ordinary, transfer]).effective], [20, 80]);
  assert.deepEqual([...allocate([transfer, ordinary]).effective], [80, 20]);
});

test("signed allocation behavior is unchanged without a transfer", () => {
  const result = allocate([
    [1, "Journal Entry", "JE-POSITIVE", 50],
    [1, "Purchase Invoice", "PI-RETURN", -20],
  ]);

  assert.deepEqual([...result.effective], [50, -20]);
  assert.equal(result.total, 30);
  assert.equal(result.has_negative_ordinary, false);
});

test("a selected row with no effective transfer allocation is reported", () => {
  const result = allocate([
    [1, "Journal Entry", "JE-FULL", 100],
    transfer,
  ]);

  assert.equal(result.zero_effective_rows.length, 1);
  assert.equal(result.zero_effective_rows[0][2], "PE-TRANSFER");
});

test("negative ordinary allocations are flagged only when mixed with a transfer", () => {
  const result = allocate([
    [1, "Purchase Invoice", "PI-RETURN", -20],
    transfer,
  ]);

  assert.equal(result.has_negative_ordinary, true);
});
