import { describe, expect, it } from "vitest";
import { parseSse, type SseEvent } from "./sse";

function responseFromFrames(text: string): Response {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(text));
      controller.close();
    },
  });
  return new Response(stream);
}

async function collect(response: Response): Promise<SseEvent[]> {
  const events: SseEvent[] = [];
  for await (const event of parseSse(response)) {
    events.push(event);
  }
  return events;
}

describe("parseSse", () => {
  it("parses multiple event frames into typed events", async () => {
    const body =
      'event: status\ndata: {"phase":"thinking"}\n\n' +
      'event: tool\ndata: {"query":"vat"}\n\n' +
      'event: token\ndata: {"text":"Hello"}\n\n' +
      "event: done\ndata: {}\n\n";

    const events = await collect(responseFromFrames(body));

    expect(events).toEqual([
      { type: "status", data: { phase: "thinking" } },
      { type: "tool", data: { query: "vat" } },
      { type: "token", data: { text: "Hello" } },
      { type: "done", data: {} },
    ]);
  });

  it("handles a frame split across chunks", async () => {
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        const enc = new TextEncoder();
        controller.enqueue(enc.encode("event: token\nda"));
        controller.enqueue(enc.encode('ta: {"text":"hi"}\n\n'));
        controller.close();
      },
    });
    const events = await collect(new Response(stream));
    expect(events).toEqual([{ type: "token", data: { text: "hi" } }]);
  });
});
