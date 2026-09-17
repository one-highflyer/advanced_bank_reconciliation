import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const component = readFileSync(new URL("../bank_rec/src/components/MatchPanel.vue", import.meta.url), "utf8");
const selection = component.match(/const selectedCandidates = computed\(([\s\S]*?)\n\);/);
assert.ok(selection, "MatchPanel must define its selected candidates");
const getSelectedCandidates = new Function(
  "props", "selectedKeys", "filteredCandidates", `return (${selection[1]})();`
);

test("allocation input keeps decimal text for ordinary candidates", () => {
  const binding = component.match(/<input\s+:value="([\s\S]*?)"\s+:readonly="candidate.is_internal_transfer"/);
  assert.ok(binding, "MatchPanel must bind the allocation input");
  const inputValue = new Function("candidate", "amounts", "allocationAmount", `return (${binding[1]});`);
  const candidate = { key: "ordinary", amount: 20 };
  for (const value of ["12.", "0.0", "12.50", ""]) {
    assert.equal(inputValue(candidate, { ordinary: value }, () => Number(value)), value);
  }
  assert.equal(inputValue(candidate, {}, () => 20), 20);
  assert.equal(inputValue({ ...candidate, is_internal_transfer: true }, {}, () => 80), 80);
});

test("search filtering does not remove checked candidates from the selection", () => {
  const candidates = [
    { key: "Journal Entry::ordinary", label: "Ordinary" },
    { key: "Payment Entry::transfer", label: "Transfer" },
  ];
  const visibleCandidates = candidates.filter((candidate) => candidate.label === "Transfer");

  assert.deepEqual(
    visibleCandidates.map((candidate) => candidate.key),
    ["Payment Entry::transfer"]
  );
  assert.deepEqual(
    getSelectedCandidates(
      { candidates },
      { value: candidates.map((candidate) => candidate.key) },
      { value: visibleCandidates },
    ).map(
      (candidate) => candidate.key
    ),
    ["Journal Entry::ordinary", "Payment Entry::transfer"]
  );
});
