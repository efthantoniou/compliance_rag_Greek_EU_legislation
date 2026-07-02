const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:9000";

export async function GET() {
  try {
    const upstream = await fetch(`${BACKEND_URL}/api/health`, {
      cache: "no-store",
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return Response.json(
      { surrealdb: false, llamacpp: false },
      { status: 200 },
    );
  }
}
