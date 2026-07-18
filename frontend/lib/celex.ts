// CELEX ids look like `32016R0679`: a 1-digit sector, 4-digit year, 1-letter
// document type, then a 4-6 digit number.
const CELEX_ID_PATTERN = /^[0-9]{5}[A-Z][0-9]{4,6}$/;

const CITATION_PATTERN = /\[([0-9]{5}[A-Z][0-9]{4,6})\]/g;

export function isCelexId(id: string): boolean {
  return CELEX_ID_PATTERN.test(id);
}

export function eurLexUrl(celexId: string): string {
  return `https://eur-lex.europa.eu/legal-content/EL/TXT/?uri=CELEX:${celexId}`;
}

// Rewrites the `[celex_id]` citations the agent writes into markdown links,
// e.g. "[32016R0679]" -> "[32016R0679](https://eur-lex.europa.eu/...)", so
// react-markdown renders them as clickable EUR-Lex links.
export function linkifyCelexCitations(text: string): string {
  return text.replace(CITATION_PATTERN, (_match, id: string) => `[${id}](${eurLexUrl(id)})`);
}
