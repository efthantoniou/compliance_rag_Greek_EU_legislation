// CELEX ids look like `32016R0679`: a 1-digit sector, 4-digit year, 1-letter
// document type, then a 4-6 digit number.
const CELEX_ID_PATTERN = /^[0-9]{5}[A-Z][0-9]{4,6}$/;

const CELEX_IN_TEXT = /\b[0-9]{5}[A-Z][0-9]{4,6}\b/g;

// A bracketed group that is not already a markdown link. The writer is asked
// for "[32004R2230]", but also produces "[32004R2230 (παρ. 1, 2)]" and
// "[32016R0679, 32014L0059]"; every valid id inside such a group is a citation.
const BRACKET_GROUP = /\[([^[\]]+)\](?!\()/g;

// The model sometimes prefixes a citation with the field name it was given,
// e.g. "celex_id: [32004R2230]" or "CELEX: 32004R2230". Normalise those to the
// bare bracketed form before linking.
const LEAKED_PREFIX_PATTERN = /\b(?:celex_id|celex)\s*:\s*\[?([0-9]{5}[A-Z][0-9]{4,6})\]?/gi;

export function isCelexId(id: string): boolean {
  return CELEX_ID_PATTERN.test(id);
}

export function eurLexUrl(celexId: string): string {
  return `https://eur-lex.europa.eu/legal-content/EL/TXT/?uri=CELEX:${celexId}`;
}

function normalise(text: string): string {
  return text.replace(LEAKED_PREFIX_PATTERN, (_match, id: string) => `[${id}]`);
}

// Rewrites the bracketed citations the agent writes into markdown links,
// e.g. "[32016R0679]" -> "[32016R0679](https://eur-lex.europa.eu/...)", so
// react-markdown renders them as clickable EUR-Lex links. Text around the ids
// inside the brackets (paragraph references, commas) is kept.
export function linkifyCelexCitations(text: string): string {
  return normalise(text).replace(BRACKET_GROUP, (match, inner: string) => {
    const linked = inner.replace(CELEX_IN_TEXT, (id) => `[${id}](${eurLexUrl(id)})`);
    return linked === inner ? match : linked; // no id inside: leave "[1]" etc. alone
  });
}

// Sector 3 (secondary legislation) document-type letters a reader recognises.
const ACT_TYPES: Record<string, string> = { R: "Regulation", L: "Directive", D: "Decision" };

// "32004R2230" -> "Regulation, 2004". The id itself stays the citation; this is
// the plain-language reading of it.
export function describeCelex(id: string): string | null {
  if (!isCelexId(id)) return null;
  const year = id.slice(1, 5);
  const type = id[0] === "3" ? ACT_TYPES[id[5]] : undefined;
  return type ? `${type}, ${year}` : year;
}

// The ids an answer cites, once each, in the order they first appear. Uses the
// same normalisation as linkifyCelexCitations so the two always agree.
export function citedCelexIds(text: string): string[] {
  const ids = [...normalise(text).matchAll(BRACKET_GROUP)].flatMap((m) =>
    [...m[1].matchAll(CELEX_IN_TEXT)].map((id) => id[0])
  );
  return [...new Set(ids)];
}
