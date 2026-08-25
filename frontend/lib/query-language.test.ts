import { describe, expect, it } from "vitest";

import { gateQuery, hasGreekCharacters } from "./query-language";

describe("hasGreekCharacters", () => {
  it("accepts Greek", () => {
    expect(hasGreekCharacters("προστασία δεδομένων")).toBe(true);
  });

  it("accepts Greek Extended (polytonic)", () => {
    expect(hasGreekCharacters("ἀρχή")).toBe(true);
  });

  it("rejects Latin-only text", () => {
    expect(hasGreekCharacters("personal data protection")).toBe(false);
  });

  it("rejects Greeklish, which retrieves nothing", () => {
    expect(hasGreekCharacters("prostasia dedomenon")).toBe(false);
  });
});

describe("gateQuery", () => {
  it("passes pure Greek", () => {
    expect(gateQuery("ασφάλεια τροφίμων")).toEqual({ kind: "ok" });
  });

  it("passes mixed queries, which retrieve well", () => {
    // Measured 0.47 and 0.94 on the live corpus.
    expect(gateQuery("GDPR προστασία δεδομένων")).toEqual({ kind: "ok" });
    expect(gateQuery("de minimis κρατικές ενισχύσεις")).toEqual({ kind: "ok" });
  });

  it("routes a bare CELEX id to the source instead of searching", () => {
    expect(gateQuery("32016R0679")).toEqual({ kind: "celex", id: "32016R0679" });
  });

  it("uppercases a lowercased CELEX id", () => {
    expect(gateQuery("32016r0679")).toEqual({ kind: "celex", id: "32016R0679" });
  });

  it("blocks English", () => {
    expect(gateQuery("personal data protection")).toEqual({ kind: "not-greek" });
  });

  it("blocks Greeklish", () => {
    expect(gateQuery("asfaleia trofimon")).toEqual({ kind: "not-greek" });
  });

  it("ignores surrounding whitespace", () => {
    expect(gateQuery("   νομοθεσία  ")).toEqual({ kind: "ok" });
  });
});
