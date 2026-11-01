import { describe, expect, it } from "vitest";
import { citedCelexIds, describeCelex, eurLexUrl, isCelexId, linkifyCelexCitations } from "./celex";

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

describe("linkifyCelexCitations field-name cleanup", () => {
  it("drops a leaked celex_id: prefix before a bracketed citation", () => {
    expect(linkifyCelexCitations("(celex_id: [32004R2230], σημείο 7)")).toBe(
      "([32004R2230](https://eur-lex.europa.eu/legal-content/EL/TXT/?uri=CELEX:32004R2230), σημείο 7)"
    );
  });

  it("links a bare id that follows a leaked prefix", () => {
    expect(linkifyCelexCitations("(CELEX: 32009R1168)")).toBe(
      "([32009R1168](https://eur-lex.europa.eu/legal-content/EL/TXT/?uri=CELEX:32009R1168))"
    );
  });

  it("leaves a bare id without a prefix untouched", () => {
    expect(linkifyCelexCitations("Regulation 32009R1168 applies.")).toBe(
      "Regulation 32009R1168 applies."
    );
  });
});

describe("describeCelex", () => {
  it("names the act type and year of secondary legislation", () => {
    expect(describeCelex("32004R2230")).toBe("Regulation, 2004");
    expect(describeCelex("31998L0028")).toBe("Directive, 1998");
    expect(describeCelex("32008D0486")).toBe("Decision, 2008");
  });

  it("falls back to the year for other document types", () => {
    expect(describeCelex("32019H0001")).toBe("2019");
  });

  it("returns null for anything that is not a celex id", () => {
    expect(describeCelex("32004R178")).toBeNull();
  });
});

describe("citedCelexIds", () => {
  it("lists cited ids once each, in the order first cited", () => {
    const text = "A [32004R2230], B [32009R1168], again [32004R2230] and (celex_id: 32007D0363).";
    expect(citedCelexIds(text)).toEqual(["32004R2230", "32009R1168", "32007D0363"]);
  });

  it("ignores malformed ids", () => {
    expect(citedCelexIds("see [32004R178]")).toEqual([]);
  });
});

describe("citations with extra text inside the brackets", () => {
  const url = (id: string) => `https://eur-lex.europa.eu/legal-content/EL/TXT/?uri=CELEX:${id}`;

  it("links the id and keeps a paragraph reference written inside the brackets", () => {
    expect(linkifyCelexCitations("φορείς [32004R2230 (παρ. 1, 2)].")).toBe(
      `φορείς [32004R2230](${url("32004R2230")}) (παρ. 1, 2).`
    );
  });

  it("links every id in a bracket that lists several", () => {
    expect(linkifyCelexCitations("[32016R0679, 32014L0059]")).toBe(
      `[32016R0679](${url("32016R0679")}), [32014L0059](${url("32014L0059")})`
    );
  });

  it("counts those ids as cited", () => {
    expect(citedCelexIds("a [32004R2230 (παρ. 1)] b [32016R0679, 32014L0059]")).toEqual([
      "32004R2230",
      "32016R0679",
      "32014L0059",
    ]);
  });
});
