export function getSelectedCandidates<T extends { key: string }>(
  candidates: T[],
  selectedKeys: string[],
): T[];
