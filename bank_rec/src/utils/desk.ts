export function deskRoute(doctype?: string, name?: string) {
  if (!doctype || !name) {
    return "";
  }

  const slug = doctype.trim().toLowerCase().replace(/\s+/g, "-");
  return `/app/${encodeURIComponent(slug)}/${encodeURIComponent(name)}`;
}
