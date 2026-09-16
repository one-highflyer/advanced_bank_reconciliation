/**
 * Keep checked candidates selected even when the visible list is filtered.
 *
 * @template {{ key: string }} T
 * @param {T[]} candidates
 * @param {string[]} selectedKeys
 * @returns {T[]}
 */
export function getSelectedCandidates(candidates, selectedKeys) {
  const selected = new Set(selectedKeys);
  return candidates.filter((candidate) => selected.has(candidate.key));
}
