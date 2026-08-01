// Relies on the global `marked` and `DOMPurify` UMD builds loaded via
// <script> tags in index.html (kept as plain globals so this stays a
// dependency-free ES module).

export function renderMarkdown(mdText) {
  if (!mdText) return "";
  const rawHtml = window.marked.parse(mdText, { breaks: true });
  return window.DOMPurify.sanitize(rawHtml);
}
