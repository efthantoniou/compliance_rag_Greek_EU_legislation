import { describe, expect, it } from "vitest";
import { eurLexUrl, isCelexId, linkifyCelexCitations } from "./celex";

describe("isCelexId", () => {
  it("accepts a well-formed celex id", () => {
    expect(isCelexId("32016R0679")).toBe(true);
  });

  it("rejects non-celex text", () => {
    expect(isCelexId("hello")).toBe(false);
    expect(isCelexId("")).toBe(false);
  });
});

describe("eurLexUrl", () => {
  it("builds the EUR-Lex Greek-language document URL", () => {
    expect(eurLexUrl("32016R0679")).toBe(
      "https://eur-lex.europa.eu/legal-content/EL/TXT/?uri=CELEX:32016R0679"
    );
  });
});

describe("linkifyCelexCitations", () => {
  it("turns bracketed celex citations into markdown links", () => {
    const input = "See [32016R0679] and [32014L0059] for details.";
    const output = linkifyCelexCitations(input);
    expect(output).toBe(
      "See [32016R0679](https://eur-lex.europa.eu/legal-content/EL/TXT/?uri=CELEX:32016R0679) " +
        "and [32014L0059](https://eur-lex.europa.eu/legal-content/EL/TXT/?uri=CELEX:32014L0059) for details."
    );
  });

  it("leaves unrelated bracketed text untouched", () => {
    const input = "See [1] in the footnotes and [not a celex id].";
    expect(linkifyCelexCitations(input)).toBe(input);
  });

  it("passes through text with no citations unchanged", () => {
    const input = "No relevant regulation found.";
    expect(linkifyCelexCitations(input)).toBe(input);
  });
});
