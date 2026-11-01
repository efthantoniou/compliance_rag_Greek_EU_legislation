import { describe, expect, it } from "vitest";
import {
  activityMessage,
  healthSummary,
  matchesLabel,
  pageInfo,
  relevance,
  traceSummary,
} from "./display";

describe("relevance", () => {
  it("is null when there is no cross-encoder score", () => {
    expect(relevance(null)).toBeNull();
    expect(relevance(undefined)).toBeNull();
  });

  it("formats the score to two decimals", () => {
    expect(relevance(0.9412)).toBe("0.94");
  });
});

describe("pageInfo", () => {
  it("describes the range shown and the page count", () => {
    expect(pageInfo(2, 10, 37)).toEqual({ summary: "Results 11–20 of 37", pages: 4 });
  });

  it("clips the last page to the total", () => {
    expect(pageInfo(4, 10, 37)).toEqual({ summary: "Results 31–37 of 37", pages: 4 });
  });

  it("reads naturally for a single result", () => {
    expect(pageInfo(1, 10, 1)).toEqual({ summary: "1 result", pages: 1 });
  });

  it("says all results fit when there is one page", () => {
    expect(pageInfo(1, 10, 7)).toEqual({ summary: "7 results", pages: 1 });
  });
});

describe("activityMessage", () => {
  it("is silent when nothing is running", () => {
    expect(activityMessage(null, 0, false)).toBeNull();
  });

  it("says it is planning before the first search", () => {
    expect(activityMessage("thinking", 0, false)).toBe("Planning the first search…");
  });

  it("counts searches while still looking", () => {
    expect(activityMessage("thinking", 1, false)).toBe("Searching the corpus, 1 search so far…");
    expect(activityMessage("thinking", 3, false)).toBe("Searching the corpus, 3 searches so far…");
  });

  it("says it is writing once answer text arrives", () => {
    expect(activityMessage("thinking", 3, true)).toBe("Writing the answer…");
  });
});

describe("healthSummary", () => {
  it("reads as ready when both services are up", () => {
    expect(healthSummary({ surrealdb: true, llamacpp: true })).toEqual({ ok: true, text: "Ready" });
  });

  it("names what is offline", () => {
    expect(healthSummary({ surrealdb: false, llamacpp: true }).text).toBe("Database offline");
    expect(healthSummary({ surrealdb: true, llamacpp: false }).text).toBe("Model offline");
    expect(healthSummary({ surrealdb: false, llamacpp: false }).text).toBe(
      "Database and model offline"
    );
  });
});

describe("traceSummary", () => {
  const doc = (celex_id: string) => ({ celex_id, snippet: "" });

  it("counts searches and distinct documents", () => {
    expect(
      traceSummary([
        { query: "a", documents: [doc("A1"), doc("B2")] },
        { query: "b", documents: [doc("A1"), doc("C3")] },
      ])
    ).toBe("Searched 2 times, found 3 documents");
  });

  it("uses singulars and says when nothing was found", () => {
    expect(traceSummary([{ query: "a", documents: [doc("A1")] }])).toBe(
      "Searched once, found 1 document"
    );
    expect(traceSummary([{ query: "a", documents: [] }])).toBe("Searched once, found nothing");
  });
});

describe("matchesLabel", () => {
  it("says nothing when only the shown passage matched", () => {
    expect(matchesLabel(1)).toBeNull();
    expect(matchesLabel(undefined)).toBeNull();
  });

  it("counts the document's matching passages", () => {
    expect(matchesLabel(3)).toBe("3 matching passages");
  });
});
