import assert from "node:assert/strict";
import test from "node:test";

import { getSelectedCandidates } from "../bank_rec/src/utils/matchSelection.js";

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
    getSelectedCandidates(candidates, candidates.map((candidate) => candidate.key)).map(
      (candidate) => candidate.key
    ),
    ["Journal Entry::ordinary", "Payment Entry::transfer"]
  );
});
